"""Higher-timeframe bars and causal alignment (e.g. M15 context for M1 entries).

Conventions: ``timestamp`` = bar OPEN time. A bar becomes known at
``available_at = timestamp + timeframe`` (its close). A lower-timeframe bar
opened at t is decided at its close t + tf_low; it may only see higher bars
with ``available_at <= t + tf_low``. Incomplete higher bars (missing lower
bars inside) are flagged and, by default, not exposed.
"""

from __future__ import annotations

import pandas as pd

from .models import TIMEFRAME_SECONDS


def resample_ohlc(bars: pd.DataFrame, source_tf: str, target_tf: str) -> pd.DataFrame:
    src, dst = TIMEFRAME_SECONDS[source_tf], TIMEFRAME_SECONDS[target_tf]
    if dst <= src or dst % src:
        raise ValueError(f"Cannot resample {source_tf} to {target_tf}")
    g = bars.set_index("timestamp").resample(f"{dst}s", label="left", closed="left")
    out = pd.DataFrame({
        "open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
        "close": g["close"].last(), "n_bars": g["close"].count(),
    }).dropna(subset=["close"]).reset_index()
    out["complete"] = out["n_bars"] == dst // src
    out["available_at"] = out["timestamp"] + pd.Timedelta(seconds=dst)
    return out


def align_higher_timeframe(lower: pd.DataFrame, lower_tf: str, higher: pd.DataFrame,
                           columns: list[str], *, prefix: str, complete_only: bool = True) -> pd.DataFrame:
    """Attach the last CLOSED higher-timeframe values to each lower bar (no look-ahead)."""
    hi = higher[higher["complete"]] if complete_only else higher
    hi = hi[["available_at", *columns]].rename(columns={c: f"{prefix}{c}" for c in columns})
    left = lower.copy()
    left["_decision_time"] = left["timestamp"] + pd.Timedelta(seconds=TIMEFRAME_SECONDS[lower_tf])
    merged = pd.merge_asof(left.sort_values("_decision_time"), hi.sort_values("available_at"),
                           left_on="_decision_time", right_on="available_at", direction="backward")
    merged = merged.rename(columns={"available_at": f"{prefix}available_at"})
    return merged.drop(columns=["_decision_time"]).sort_values("timestamp").reset_index(drop=True)
