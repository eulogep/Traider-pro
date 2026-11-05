"""Bar-by-bar backtest engine (single position, no look-ahead, full decision journal).

Timeline for bar i (timestamp = bar OPEN time):
  1. open of bar i: manage the open position (time / session exits at the open,
     then stop/target checks on the bar's high/low, stop first);
  2. open of bar i: act on the signal computed at the CLOSE of bar i-1 — engine
     checks (window, session, data gap, exit in this bar) + Risk Guardian;
     a new position can already hit its SL/TP inside bar i;
  3. close of bar i: record closed and mark-to-market equity.
Only ``signals[i-1]`` is read when deciding at bar i.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .. import ENGINE_VERSION, __version__
from ..analytics.metrics import compute_metrics
from ..data.models import Dataset
from ..numeric import require_finite
from ..risk.guardian import RiskGuardian, TradeProposal
from ..safety import LIVE_TRADING_ENABLED, ExecutionMode
from ..storage.integrity import result_fingerprint
from ..strategies.base import Strategy, StrategySpec
from ..strategies.registry import StrategyNotRunnableError, build_strategy
from .codehash import code_fingerprint
from .models import FILL_ASSUMPTIONS_FR, BacktestConfig, BacktestResult


class SignalContractError(ValueError):
    pass


def _to_utc(value: str | None) -> pd.Timestamp | None:
    if not value:
        return None
    ts = pd.Timestamp(value)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def _session_mask(ts: pd.Series, hours) -> np.ndarray:
    local = ts.dt.tz_convert(ZoneInfo(hours.timezone))
    minutes = (local.dt.hour * 60 + local.dt.minute).to_numpy()
    ok = np.zeros(len(ts), dtype=bool)
    for start, end in hours.parsed():
        a, b = start.hour * 60 + start.minute, end.hour * 60 + end.minute
        ok |= ((minutes >= a) & (minutes < b)) if a <= b else ((minutes >= a) | (minutes < b))
    weekday_ok = local.dt.weekday.isin(hours.weekdays).to_numpy()
    return ok & weekday_ok, weekday_ok


def check_signal_contract(sig: pd.DataFrame, n: int) -> None:
    missing = {"signal", "reason", "sl_distance", "tp_distance"} - set(sig.columns)
    if missing:
        raise SignalContractError(f"strategy output lacks columns {sorted(missing)}")
    if len(sig) != n:
        raise SignalContractError("strategy output length differs from input bars")
    if not sig["signal"].isin([-1, 0, 1]).all():
        raise SignalContractError("signal must be -1, 0 or 1")


def run_backtest(dataset: Dataset, spec: StrategySpec, config: BacktestConfig,
                 strategy: Strategy | None = None) -> BacktestResult:
    assert not LIVE_TRADING_ENABLED  # this engine never talks to a broker
    if spec.timeframes.execution != dataset.meta.timeframe:
        raise ValueError(f"La stratégie s'exécute en {spec.timeframes.execution}, "
                         f"le jeu de données est en {dataset.meta.timeframe}.")
    if strategy is None:
        strategy = build_strategy(spec, config.strategy_params)
    else:  # an injected strategy object must not bypass the runnable checks of its spec
        if strategy.spec.key != spec.key:
            raise StrategyNotRunnableError("La stratégie fournie ne correspond pas à la spécification.")
        problems = spec.runnable_problems()
        if problems:
            raise StrategyNotRunnableError(f"{spec.key} non exécutable : " + " ; ".join(problems))
    params = strategy.params
    hours = config.trading_hours or spec.trading_hours
    costs, contract = config.costs, config.contract
    tf = dataset.bar_seconds

    # Evaluation window (B3). A bar opened at t is closed — and its information available — at t + tf.
    #   trade_end   = E: only bars whose CLOSE is <= E are loaded (nothing observed after E is used);
    #                    a position still open is closed at the close of the last such bar.
    #   trade_start = S: orders are executed only at bar OPENS >= S, and the evaluated equity starts there;
    #                    bars before S are used for indicator warm-up only (no result is counted).
    # With the same cut C for IS (E = C) and OOS (S = C), no bar contributes results to both.
    bars = dataset.bars
    t_end, t_start = _to_utc(config.trade_end), _to_utc(config.trade_start)
    if t_end is not None:
        bars = bars[bars["timestamp"] + pd.Timedelta(seconds=tf) <= t_end]
    bars = bars.reset_index(drop=True)
    n = len(bars)
    if n < 2:
        raise ValueError("Pas assez de bougies dans la fenêtre demandée.")

    sig = strategy.compute(bars)
    check_signal_contract(sig, n)

    ts = bars["timestamp"]
    t_ns = ts.astype("int64").to_numpy()
    in_session, weekday_ok = _session_mask(ts, hours)
    days = ts.dt.tz_convert(ZoneInfo(config.risk.day_timezone)).dt.date.tolist()
    in_window = np.ones(n, dtype=bool) if t_start is None else (ts >= t_start).to_numpy()

    # Bid-side price arrays; ask = bid + spread.
    shift = 0.0 if dataset.meta.price_side == "bid" else -costs.spread / 2
    o = (bars["open"].to_numpy(float) + shift).tolist()
    h = (bars["high"].to_numpy(float) + shift).tolist()
    lo = (bars["low"].to_numpy(float) + shift).tolist()
    c = (bars["close"].to_numpy(float) + shift).tolist()
    spread, slip, comm = costs.spread, costs.slippage, costs.commission_per_lot_per_side
    cs = contract.contract_size or 0.0
    s_sig = sig["signal"].astype(int).tolist()
    s_sl = sig["sl_distance"].astype(float).tolist()
    s_tp = sig["tp_distance"].astype(float).tolist()
    gap_before = np.r_[True, np.diff(t_ns) != tf * 1_000_000_000].tolist()

    guardian = RiskGuardian(config.risk, contract, config.initial_equity, config.account_currency,
                            instrument_symbol=dataset.meta.symbol)
    equity = float(config.initial_equity)
    trades: list[dict] = []
    decisions: list[dict] = []
    curve_t, curve_closed, curve_mtm, curve_pos = [], [], [], []
    pos: dict | None = None
    cur_day = None

    def close_position(i: int, price: float, reason: str) -> None:
        nonlocal equity, pos
        d, lots = pos["dir"], pos["lots"]
        require_finite(price, "prix de sortie")
        price_pnl = d * (price - pos["entry"]) * lots * cs
        commission = 2 * comm * lots
        net = require_finite(price_pnl - commission, "P&L net d'un trade")
        equity = require_finite(equity + net, "capital")
        guardian.on_position_closed(net)
        risk = pos["planned_risk"]
        trades.append({
            "trade_id": pos["trade_id"], "decision_id": pos["decision_id"],
            "direction": "BUY" if d == 1 else "SELL",
            "signal_time": ts.iloc[pos["entry_idx"] - 1], "entry_time": ts.iloc[pos["entry_idx"]],
            "exit_time": ts.iloc[i], "bars_held": i - pos["entry_idx"] + 1,
            "lots": lots, "entry_price": pos["entry"], "exit_price": price,
            "stop_loss": pos["sl"], "take_profit": pos["tp"],
            "planned_risk": risk, "price_pnl": price_pnl, "commission": commission, "net_pnl": net,
            "r_multiple": net / risk if risk > 0 else np.nan,
            "spread_cost": spread * cs * lots, "slippage_cost": 2 * slip * cs * lots,
            "mae_price": pos["mae"], "mfe_price": pos["mfe"],
            "mae_r": pos["mae"] / pos["sl_dist"] if pos["sl_dist"] else np.nan,
            "mfe_r": pos["mfe"] / pos["sl_dist"] if pos["sl_dist"] else np.nan,
            "excursion_basis": "lower_bound_ohlc",
            "exit_reason": reason, "gap_during_trade": pos["gap"], "equity_after": equity,
        })
        pos = None

    def note(adverse: float, favorable: float) -> None:
        pos["mae"] = max(pos["mae"], adverse)
        pos["mfe"] = max(pos["mfe"], favorable)

    def open_gap_exit(i: int) -> bool:
        """I8: a level already crossed AT THE OPEN has a known chronology (the open is the first price of
        the bar): it is executed before any intrabar touch. Stop gapped -> filled at the open (worse than
        the stop); target gapped -> filled at the target (conservative: the favourable gap is not credited)."""
        d = pos["dir"]
        px = o[i] if d == 1 else o[i] + spread  # exit-side price at the open: BID for longs, ASK for shorts
        note(d * (pos["entry"] - px), d * (px - pos["entry"]))
        if (px <= pos["sl"]) if d == 1 else (px >= pos["sl"]):
            close_position(i, px - slip if d == 1 else px + slip, "SL_GAP")
            return True
        if pos["tp"] is not None and ((px >= pos["tp"]) if d == 1 else (px <= pos["tp"])):
            close_position(i, pos["tp"] - slip if d == 1 else pos["tp"] + slip, "TP_GAP")
            return True
        return False

    def intrabar(i: int) -> bool:
        """SL/TP touched INSIDE bar i (order of high/low unknown). Returns True if the position closed.

        Both touched -> stop first (conservative). Excursions (M4) are proven lower bounds: a bar is
        counted whole only if the position survived it; in an exit bar only the reached level is known."""
        d = pos["dir"]
        if d == 1:
            stop_hit, tp_hit = lo[i] <= pos["sl"], pos["tp"] is not None and h[i] >= pos["tp"]
            stop_fill, tp_fill = min(pos["sl"], o[i]) - slip, (pos["tp"] or 0) - slip
            adverse, favorable = pos["entry"] - lo[i], h[i] - pos["entry"]
        else:
            stop_hit, tp_hit = h[i] + spread >= pos["sl"], pos["tp"] is not None and lo[i] + spread <= pos["tp"]
            stop_fill, tp_fill = max(pos["sl"], o[i] + spread) + slip, (pos["tp"] or 0) + slip
            adverse, favorable = h[i] + spread - pos["entry"], pos["entry"] - (lo[i] + spread)
        if stop_hit:
            note(d * (pos["entry"] - pos["sl"]), 0.0)
            close_position(i, stop_fill, "SL")
            return True
        if tp_hit:
            note(0.0, d * (pos["tp"] - pos["entry"]))
            close_position(i, tp_fill, "TP")
            return True
        note(adverse, favorable)  # no exit: the whole bar was observed while holding
        return False

    def market_exit_price(i: int, d: int, at_close: bool = False) -> float:
        px = c[i] if at_close else o[i]
        return px - slip if d == 1 else px + spread + slip

    for i in range(n):
        if days[i] != cur_day:
            cur_day = days[i]
            guardian.on_new_day(cur_day)
        exited = False

        # 1. manage the open position
        if pos is not None:
            if gap_before[i]:
                pos["gap"] = True
            if open_gap_exit(i):  # known chronology first (I8)
                exited = True
            elif config.max_bars_in_trade and i - pos["entry_idx"] >= config.max_bars_in_trade:
                close_position(i, market_exit_price(i, pos["dir"]), "TIME_EXIT")
                exited = True
            elif config.close_at_session_end and not in_session[i]:
                close_position(i, market_exit_price(i, pos["dir"]), "SESSION_END")
                exited = True
            else:
                exited = intrabar(i)

        # 2. act on the signal of the last CLOSED bar (i-1)
        if i >= 1 and s_sig[i - 1] != 0:
            d = s_sig[i - 1]
            engine_reasons = []
            if not in_window[i]:
                engine_reasons.append("OUTSIDE_TEST_WINDOW")
            if exited:
                engine_reasons.append("EXITED_THIS_BAR")
            if not weekday_ok[i]:
                engine_reasons.append("NON_TRADING_DAY")
            elif not in_session[i]:
                engine_reasons.append("OUTSIDE_SESSION")
            sl_dist, tp_dist = s_sl[i - 1], s_tp[i - 1]
            entry = o[i] + spread + slip if d == 1 else o[i] - slip
            stop = entry - d * sl_dist if np.isfinite(sl_dist) else np.nan
            target = entry + d * tp_dist if np.isfinite(tp_dist) and tp_dist > 0 else None
            if not (np.isfinite(stop) and stop > 0 and (target is None or target > 0)):
                engine_reasons.append("INVALID_PRICES")
            decision = {"decision_id": len(decisions) + 1, "_sig_idx": i - 1, "signal_time": ts.iloc[i - 1],
                        "decision_time": ts.iloc[i - 1] + pd.Timedelta(seconds=tf), "entry_bar_time": ts.iloc[i],
                        "direction": "BUY" if d == 1 else "SELL", "strategy_reason": sig["reason"].iat[i - 1]}
            if engine_reasons and "OUTSIDE_TEST_WINDOW" in engine_reasons:
                risk_dec = None  # nothing evaluated outside the window
            else:
                risk_dec = guardian.evaluate(TradeProposal(
                    direction=d, stop_distance=sl_dist, stop_slippage=slip, commission_per_lot_per_side=comm,
                    data_ok=not gap_before[i], position_scaling=spec.position_scaling, spread=spread))
            reasons = engine_reasons + ([] if risk_dec is None else risk_dec.reasons)
            if gap_before[i] and "DATA_INVALID" not in reasons:
                reasons.append("DATA_INVALID")
            if not reasons and risk_dec is not None and risk_dec.approved:
                require_finite(risk_dec.lots, "taille de position")
                require_finite(risk_dec.planned_risk, "risque prévu")
                pos = {"dir": d, "entry": entry, "sl": stop, "tp": target, "lots": risk_dec.lots,
                       "planned_risk": risk_dec.planned_risk, "entry_idx": i, "sl_dist": sl_dist,
                       "mae": 0.0, "mfe": 0.0, "gap": False, "trade_id": len(trades) + 1,
                       "decision_id": decision["decision_id"]}
                guardian.on_position_opened(risk_dec.planned_risk)
                decision.update(outcome="ENTERED", reasons="", lots=risk_dec.lots,
                                planned_risk=risk_dec.planned_risk, trade_id=pos["trade_id"],
                                entry_price=entry, stop_loss=stop, take_profit=target)
                decisions.append(decision)
                intrabar(i)  # the new position may already exit inside its entry bar
            else:
                decision.update(outcome="REJECTED", reasons=";".join(reasons), lots=0.0, planned_risk=0.0,
                                trade_id=None, entry_price=entry, stop_loss=stop, take_profit=target)
                decisions.append(decision)

        # 3. equity at the close of bar i
        if in_window[i]:
            mtm = equity
            if pos is not None:
                d = pos["dir"]
                exit_px = c[i] if d == 1 else c[i] + spread
                mtm += d * (exit_px - pos["entry"]) * pos["lots"] * cs - 2 * comm * pos["lots"]
            curve_t.append(ts.iloc[i])
            curve_closed.append(equity)
            curve_mtm.append(mtm)
            curve_pos.append(0 if pos is None else pos["dir"])

    if pos is not None:
        close_position(n - 1, market_exit_price(n - 1, pos["dir"], at_close=True), "END_OF_DATA")
        if curve_closed:
            curve_closed[-1] = equity
            curve_mtm[-1] = equity

    trades_df = pd.DataFrame(trades)
    decisions_df = pd.DataFrame(decisions)
    feature_cols = [col for col in strategy.feature_columns if col in sig.columns]
    if len(decisions_df):
        feats = sig.iloc[decisions_df["_sig_idx"].to_numpy()][feature_cols].reset_index(drop=True).add_prefix("f_")
        decisions_df = pd.concat([decisions_df.drop(columns=["_sig_idx"]).reset_index(drop=True), feats], axis=1)
    equity_df = pd.DataFrame({"timestamp": curve_t, "closed_equity": curve_closed, "mtm_equity": curve_mtm,
                              "position": curve_pos})

    metrics = compute_metrics(trades_df, equity_df, config.initial_equity, decisions_df)
    metrics["wait_reasons"] = sig.loc[sig["signal"] == 0, "reason"].value_counts().to_dict()
    metrics["guardian_rejections"] = dict(guardian.rejections)
    metrics["data_kind"] = dataset.meta.kind.value

    config_json = config.canonical_json()
    run_key = json.dumps({"dataset": dataset.meta.dataset_id, "strategy": spec.key, "spec_hash": spec.spec_hash(),
                          "params": params, "config": json.loads(config_json), "engine": ENGINE_VERSION,
                          "code": code_fingerprint()},
                         sort_keys=True, default=str)
    run_id = hashlib.sha256(run_key.encode()).hexdigest()[:16]
    manifest = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "software_version": __version__, "engine_version": ENGINE_VERSION, "code_hash": code_fingerprint(),
        "execution_mode": ExecutionMode.SIMULATION.value,
        "dataset": dataset.meta.model_dump(mode="json", exclude={"quality"}),
        "data_kind": dataset.meta.kind.value,
        "strategy": {"key": spec.key, "id": spec.id, "version": spec.version, "name": spec.name,
                     "spec_hash": spec.spec_hash(), "category": spec.category, "illustrative": spec.illustrative,
                     "params": params},
        "trading_hours": hours.model_dump(mode="json"),
        "config": json.loads(config_json),
        "fill_assumptions": FILL_ASSUMPTIONS_FR,
        "result_hash": result_fingerprint(trades_df, decisions_df, equity_df, metrics),
        "evaluation_window": {
            "trade_start": None if t_start is None else t_start.isoformat(),
            "trade_end": None if t_end is None else t_end.isoformat(),
            "first_evaluated_bar_open": equity_df["timestamp"].iloc[0].isoformat() if len(equity_df) else None,
            "last_evaluated_bar_close": (equity_df["timestamp"].iloc[-1] + pd.Timedelta(seconds=tf)).isoformat()
            if len(equity_df) else None,
        },
    }
    return BacktestResult(trades_df, decisions_df, equity_df, metrics, manifest, signals=sig)
