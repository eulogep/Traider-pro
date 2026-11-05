"""Outcome of EVERY candidate signal, as if it had been taken alone ("triple barrier" labelling).

Why: a backtest only trades the few signals the Risk Guardian lets through (one position, N trades a day),
far too few to learn anything. Here each signal is simulated independently with the ENGINE's conventions,
so the label of a signal the engine did trade equals that trade's ``r_multiple`` (tested):

* entry at the OPEN of the bar after the signal bar (BUY at ask + slippage, SELL at bid − slippage);
* stop / target from the strategy's distances; invalid prices, gap before entry, non-trading day or
  outside the session -> the signal is not labelled (the engine would not have taken it either);
* entry bar: intrabar check only; later bars: gap at the open first, then stop before target (stop first);
* not exited after ``horizon_bars`` bars -> market exit at that bar's close (reason ``HORIZON``);
  end of data before that -> unlabelled (outcome unknown, never guessed).

R = (direction × (exit − entry) × contract − 2 × commission) / ((stop distance + slippage) × contract
+ 2 × commission) per lot — the engine's ``net_pnl / planned_risk`` (lots cancel out).

Time contract (v0.4.1, audits N9 / I04-4): ``exit_time`` is the OPEN of the bar in which the trade is
resolved (engine convention, unchanged); the outcome is only KNOWN at that bar's close, recorded as
``available_time = exit_time + one bar``. Purging and the prospective opinion use ``available_time``.
``horizon_bars = h`` observes up to h + 1 bars (the entry bar plus h later bars).
Labels are research data, not P&L: the engine remains the only source of reported results.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..backtest.engine import _session_mask
from ..backtest.models import BacktestConfig
from ..data.models import Dataset
from ..strategies.base import StrategySpec

LABEL_COLUMNS = ["sig_idx", "signal_time", "entry_time", "exit_time", "direction", "r", "win", "exit_reason",
                 "bars_held", "sl_distance", "available_time"]


def _first(mask: np.ndarray) -> int:
    """Index of the first True, or len(mask) if none."""
    return int(mask.argmax()) if mask.any() else len(mask)


def label_signals(dataset: Dataset, spec: StrategySpec, config: BacktestConfig, signals: pd.DataFrame,
                  horizon_bars: int = 240) -> pd.DataFrame:
    if horizon_bars < 1:
        raise ValueError("horizon_bars doit être ≥ 1")
    bars = dataset.bars.reset_index(drop=True)
    n = len(bars)
    costs, cs = config.costs, float(config.contract.contract_size or 0.0)
    if cs <= 0:
        raise ValueError("Taille de contrat inconnue : impossible d'exprimer un résultat en R.")
    spread, slip, comm = costs.spread, costs.slippage, costs.commission_per_lot_per_side
    shift = 0.0 if dataset.meta.price_side == "bid" else -spread / 2
    o = bars["open"].to_numpy(float) + shift
    h = bars["high"].to_numpy(float) + shift
    lo = bars["low"].to_numpy(float) + shift
    c = bars["close"].to_numpy(float) + shift
    ts = bars["timestamp"]
    t_ns = ts.astype("int64").to_numpy()
    tf = dataset.bar_seconds
    one_bar = pd.Timedelta(seconds=tf)
    gap_before = np.r_[True, np.diff(t_ns) != tf * 1_000_000_000]
    in_session, weekday_ok = _session_mask(ts, config.trading_hours or spec.trading_hours)

    sig = signals["signal"].astype(int).to_numpy()
    sl_d = signals["sl_distance"].astype(float).to_numpy()
    tp_d = signals["tp_distance"].astype(float).to_numpy()
    rows = []
    for j in np.flatnonzero(sig != 0):
        i = j + 1  # entry bar
        if i >= n or gap_before[i] or not weekday_ok[i] or not in_session[i]:
            continue
        d, sl_dist, tp_dist = int(sig[j]), sl_d[j], tp_d[j]
        if not (np.isfinite(sl_dist) and sl_dist > 0):
            continue
        entry = o[i] + spread + slip if d == 1 else o[i] - slip
        stop = entry - d * sl_dist
        target = entry + d * tp_dist if np.isfinite(tp_dist) and tp_dist > 0 else None
        if not (stop > 0 and (target is None or target > 0)):
            continue
        last = i + horizon_bars
        if last >= n:
            continue  # outcome not observable within the horizon
        k = np.arange(i, last + 1)
        oo, hh, ll = o[k], h[k], lo[k]
        if d == 1:
            px_open = oo
            open_sl, open_tp = px_open <= stop, (px_open >= target) if target is not None else np.zeros(len(k), bool)
            bar_sl, bar_tp = ll <= stop, (hh >= target) if target is not None else np.zeros(len(k), bool)
        else:
            px_open = oo + spread
            open_sl, open_tp = px_open >= stop, (px_open <= target) if target is not None else np.zeros(len(k), bool)
            bar_sl, bar_tp = hh + spread >= stop, (ll + spread <= target) if target is not None else np.zeros(len(k), bool)
        open_sl[0] = open_tp[0] = False  # no open-gap check on the entry bar (the engine enters at that open)
        firsts = [_first(open_sl), _first(open_tp), _first(bar_sl), _first(bar_tp)]
        b = min(firsts)
        if b == len(k):  # horizon reached: market exit at the close of the last bar
            exit_px, reason, b = (c[last] - slip if d == 1 else c[last] + spread + slip), "HORIZON", len(k) - 1
        else:
            # priority inside one bar = engine order: open gap (stop, then target), then intrabar stop, then target
            ev = [x == b for x in firsts].index(True)
            if ev == 0:
                exit_px, reason = (px_open[b] - slip if d == 1 else px_open[b] + slip), "SL_GAP"
            elif ev == 1:
                exit_px, reason = (target - slip if d == 1 else target + slip), "TP_GAP"
            elif ev == 2:
                exit_px = min(stop, oo[b]) - slip if d == 1 else max(stop, oo[b] + spread) + slip
                reason = "SL"
            else:
                exit_px, reason = (target - slip if d == 1 else target + slip), "TP"
        risk_per_lot = (sl_dist + slip) * cs + 2 * comm
        r = (d * (exit_px - entry) * cs - 2 * comm) / risk_per_lot
        rows.append((int(j), ts.iat[j], ts.iat[i], ts.iat[i + b], d, float(r), bool(r > 0), reason, b + 1, float(sl_dist),
                     ts.iat[i + b] + one_bar))
    return pd.DataFrame(rows, columns=LABEL_COLUMNS)
