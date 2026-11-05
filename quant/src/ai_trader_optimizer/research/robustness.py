"""Robustness of ONE stored backtest: how much of its result could be luck?

* block bootstrap of the trades (in time order) -> confidence intervals of the expectancy (R and money)
  and of the win rate, and the probability that the true expectancy is positive;
* Monte Carlo on the ORDER of the same trades -> distribution of the maximum drawdown and the probability
  of breaching the Risk Guardian's drawdown limit with the same trades in another order.
Seeded by the run's result hash: the same run always gives the same answer.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .stats import block_bootstrap_indices, interval

MIN_TRADES = 30


def _max_dd_pct(pnl_paths: np.ndarray, initial: float) -> np.ndarray:
    eq = initial + np.cumsum(pnl_paths, axis=1)
    eq = np.c_[np.full(len(eq), initial), eq]
    peak = np.maximum.accumulate(eq, axis=1)
    return ((eq - peak) / peak * 100).min(axis=1)


def run_robustness(trades: pd.DataFrame, initial_equity: float, max_drawdown_pct: float, result_hash: str,
                   n_boot: int = 2000, alpha: float = 0.05) -> dict:
    n = len(trades)
    out = {"n_trades": int(n), "min_trades": MIN_TRADES, "confidence": 1 - alpha, "n_boot": n_boot,
           "sufficient": n >= MIN_TRADES,
           "assumptions": "Mesures CONDITIONNELLES : bootstrap par blocs des trades observés ; drawdowns sous "
                          "réordonnancement échangeable (montants fixes, Risk Guardian non rejoué, séries de pertes "
                          "détruites). « p_positive » et « p_breach_limit » sont des parts de tirages, pas des "
                          "probabilités d'événements futurs."}
    if n < 2:
        out["note"] = "Moins de 2 trades : aucune mesure d'incertitude possible."
        return out
    rng = np.random.default_rng(int(result_hash[:8], 16))
    r = trades["r_multiple"].to_numpy(float)
    pnl = trades["net_pnl"].to_numpy(float)
    B = block_bootstrap_indices(n, n_boot, rng)
    mean_r_b, pnl_b, win_b = r[B].mean(axis=1), pnl[B].mean(axis=1), (r[B] > 0).mean(axis=1)
    out["expectancy_r"] = {"value": float(r.mean()), "ci": interval(mean_r_b, alpha), "p_positive": float(np.mean(mean_r_b > 0))}
    out["expectancy_money"] = {"value": float(pnl.mean()), "ci": interval(pnl_b, alpha)}
    out["win_rate"] = {"value": float((r > 0).mean()), "ci": interval(win_b, alpha)}
    perms = np.argsort(rng.random((n_boot, n)), axis=1)
    dd = _max_dd_pct(pnl[perms], float(initial_equity))
    actual = float(_max_dd_pct(pnl[None, :], float(initial_equity))[0])
    out["max_drawdown_pct"] = {"actual": actual, "median": float(np.median(dd)), "p95": float(np.quantile(dd, 0.05)),
                               "worst": float(dd.min()), "limit": -abs(float(max_drawdown_pct)),
                               "p_breach_limit": float(np.mean(dd <= -abs(float(max_drawdown_pct))))}
    lo = out["expectancy_r"]["ci"][0]
    hi = out["expectancy_r"]["ci"][1]
    out["rating"] = ("insuffisant" if n < MIN_TRADES else "positif" if lo is not None and lo > 0
                     else "négatif" if hi is not None and hi < 0 else "non démontré")
    return out
