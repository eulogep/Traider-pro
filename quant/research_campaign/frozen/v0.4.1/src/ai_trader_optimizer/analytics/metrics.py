"""Performance metrics. A metric that cannot be computed honestly is None,
with the reason in ``metrics["unavailable"]``."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

MIN_TRADES_FOR_CONCLUSION = 30


def drawdown_series_pct(values: np.ndarray, initial: float) -> np.ndarray:
    """Drawdown (%, <= 0) of each point vs the running peak, the initial equity counting as first peak.
    Same definition as ``max_dd_*_pct``: ``drawdown_series_pct(v, x).min() == _max_drawdown(v, x)[0]``."""
    if len(values) == 0:
        return np.array([])
    series = np.r_[initial, values]
    peak = np.maximum.accumulate(series)
    return np.where(peak > 0, (series - peak) / peak * 100, 0.0)[1:]


def _max_drawdown(values: np.ndarray, initial: float) -> tuple[float, float]:
    """Return (max drawdown %, max drawdown amount), both <= 0."""
    if len(values) == 0:
        return 0.0, 0.0
    series = np.r_[initial, values]
    peak = np.maximum.accumulate(series)
    dd = series - peak
    pct = np.where(peak > 0, dd / peak * 100, 0.0)
    return float(pct.min()), float(dd.min())


def _max_streak(losses: pd.Series) -> int:
    best = cur = 0
    for v in losses:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best


def compute_metrics(trades: pd.DataFrame, equity: pd.DataFrame, initial_equity: float,
                    decisions: pd.DataFrame | None = None) -> dict:
    m: dict = {"initial_equity": float(initial_equity)}
    unavailable: dict[str, str] = {}
    n = int(len(trades))
    final = float(trades["equity_after"].iloc[-1]) if n else float(initial_equity)
    m.update(final_equity=final, net_pnl=final - initial_equity,
             return_pct=(final - initial_equity) / initial_equity * 100, trades=n)

    if n:
        net = trades["net_pnl"]
        wins = net > 0
        gp, gl = float(net[wins].sum()), float(-net[~wins].sum())
        m.update(
            wins=int(wins.sum()), non_wins=int((~wins).sum()),
            win_rate_pct=float(wins.mean() * 100),
            gross_profit=gp, gross_loss=gl,
            expectancy=float(net.mean()),
            expectancy_r=float(trades["r_multiple"].mean()) if trades["r_multiple"].notna().any() else None,
            avg_win=float(net[wins].mean()) if wins.any() else None,
            avg_loss=float(net[~wins].mean()) if (~wins).any() else None,
            largest_win=float(net.max()), largest_loss=float(net.min()),
            max_consecutive_losses=_max_streak(~wins),
            avg_bars_held=float(trades["bars_held"].mean()),
            commission_total=float(trades["commission"].sum()),
            spread_cost_total=float(trades["spread_cost"].sum()),
            slippage_cost_total=float(trades["slippage_cost"].sum()),
            exit_reasons=trades["exit_reason"].value_counts().to_dict(),
            by_direction={d: {"trades": int(len(g)), "net_pnl": float(g["net_pnl"].sum()),
                              "win_rate_pct": float((g["net_pnl"] > 0).mean() * 100)}
                          for d, g in trades.groupby("direction")},
            trades_with_data_gap=int(trades["gap_during_trade"].sum()),
            losses_beyond_planned_risk=int((trades["net_pnl"] < -trades["planned_risk"] - 1e-9).sum()),
        )
        m["total_costs"] = m["commission_total"] + m["spread_cost_total"] + m["slippage_cost_total"]
        m["pnl_before_costs"] = m["net_pnl"] + m["total_costs"]
        if gl > 0:
            m["profit_factor"] = gp / gl
        else:
            m["profit_factor"] = None
            unavailable["profit_factor"] = "aucune perte : ratio non défini (division par zéro)"
        if m["avg_win"] is not None and m["avg_loss"] not in (None, 0):
            m["payoff_ratio"] = m["avg_win"] / abs(m["avg_loss"])
        else:
            m["payoff_ratio"] = None
            unavailable["payoff_ratio"] = "il faut au moins un trade gagnant et un perdant"
    else:
        for k in ("win_rate_pct", "profit_factor", "expectancy", "expectancy_r", "payoff_ratio"):
            m[k] = None
            unavailable[k] = "aucune transaction simulée"
        m.update(total_costs=0.0, commission_total=0.0, spread_cost_total=0.0, slippage_cost_total=0.0,
                 exit_reasons={}, by_direction={})

    closed = equity["closed_equity"].to_numpy(float) if len(equity) else np.array([])
    mtm = equity["mtm_equity"].to_numpy(float) if len(equity) else np.array([])
    m["max_dd_closed_pct"], m["max_dd_closed"] = _max_drawdown(closed, initial_equity)
    m["max_dd_mtm_pct"], m["max_dd_mtm"] = _max_drawdown(mtm, initial_equity)
    m["drawdown_note"] = ("Drawdown sur equity clôturée et mark-to-market aux clôtures de bougies : "
                          "le drawdown intrabougie réel peut être plus profond.")

    if decisions is not None and len(decisions):
        m["signals"] = int(len(decisions))
        m["signals_entered"] = int((decisions["outcome"] == "ENTERED").sum())
        m["signals_rejected"] = int((decisions["outcome"] == "REJECTED").sum())
        reasons = decisions.loc[decisions["outcome"] == "REJECTED", "reasons"].str.split(";").explode()
        m["rejection_reasons"] = reasons[reasons.astype(bool)].value_counts().to_dict()
    else:
        m.update(signals=0, signals_entered=0, signals_rejected=0, rejection_reasons={})

    unavailable["sharpe_sortino"] = ("non calculés en v0.2 : nécessitent une série de rendements périodiques "
                                     "sur données réelles et un échantillon suffisant")
    m["sample_sufficient"] = n >= MIN_TRADES_FOR_CONCLUSION
    if not m["sample_sufficient"]:
        m["sample_note"] = (f"{n} trade(s) < {MIN_TRADES_FOR_CONCLUSION} : échantillon insuffisant, "
                            "conclusion « non démontré ».")
    m["unavailable"] = unavailable
    return {k: (None if isinstance(v, float) and not math.isfinite(v) else v) for k, v in m.items()}


def results_by_period(trades: pd.DataFrame, freq: str = "M") -> pd.DataFrame:
    """freq: 'D' day, 'W' week, 'M' month, 'H' hour-of-day (UTC), 'DOW' weekday."""
    cols = ["period", "trades", "net_pnl", "win_rate_pct", "avg_r"]
    if trades.empty:
        return pd.DataFrame(columns=cols)
    t = trades.copy()
    et = pd.to_datetime(t["entry_time"], utc=True)
    if freq == "H":
        key = et.dt.hour.map(lambda x: f"{x:02d}h UTC")
    elif freq == "DOW":
        names = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        key = et.dt.weekday.map(lambda x: f"{x} {names[x]}")
    else:
        alias = {"D": "D", "W": "W", "M": "M"}[freq]
        key = et.dt.tz_localize(None).dt.to_period(alias).astype(str)
    g = t.assign(period=key.values).groupby("period", sort=True)
    out = pd.DataFrame({
        "trades": g.size(), "net_pnl": g["net_pnl"].sum(),
        "win_rate_pct": g["net_pnl"].apply(lambda s: float((s > 0).mean() * 100)),
        "avg_r": g["r_multiple"].mean(),
    }).reset_index()
    return out[cols]
