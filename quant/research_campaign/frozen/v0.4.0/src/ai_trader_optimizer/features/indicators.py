"""Causal technical indicators: value at row i depends only on rows <= i.

Warm-up rows are NaN where the definition needs more history (SMA, ATR).
EMAs are seeded on the first close (``adjust=False``, as MT5/TradingView do
once warmed up); strategies must discard a warm-up period (>= 3x the period
is advisable for the EMA to forget its seed).
"""

from __future__ import annotations

from typing import Literal

import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    if period < 1:
        raise ValueError("period must be >= 1")
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    if period < 1:
        raise ValueError("period must be >= 1")
    return series.rolling(period, min_periods=period).mean()


def true_range(bars: pd.DataFrame) -> pd.Series:
    prev = bars["close"].shift(1)
    return pd.concat([bars["high"] - bars["low"], (bars["high"] - prev).abs(), (bars["low"] - prev).abs()],
                     axis=1).max(axis=1)


def atr(bars: pd.DataFrame, period: int = 14, method: Literal["wilder", "sma"] = "wilder") -> pd.Series:
    """ATR. ``wilder`` = RMA seeded with the SMA of the first ``period`` TRs (MT5-like);
    ``sma`` = simple moving average of TR (what v0.1 called ATR14)."""
    tr = true_range(bars)
    if method == "sma":
        return sma(tr, period)
    if method != "wilder":
        raise ValueError(f"unknown ATR method {method!r}")
    values = tr.to_numpy(dtype=float)
    out = [float("nan")] * len(values)
    if len(values) >= period:
        prev = values[:period].mean()
        out[period - 1] = prev
        for i in range(period, len(values)):
            prev = (prev * (period - 1) + values[i]) / period
            out[i] = prev
    return pd.Series(out, index=bars.index, dtype=float)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    if not fast < slow:
        raise ValueError("MACD requires fast < slow")
    line = ema(close, fast) - ema(close, slow)
    sig = line.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame({"macd": line, "macd_signal": sig, "macd_hist": line - sig}, index=close.index)


def candle_color(bars: pd.DataFrame) -> pd.Series:
    """+1 green (close > open), -1 red (close < open), 0 doji."""
    return (bars["close"] > bars["open"]).astype(int) - (bars["close"] < bars["open"]).astype(int)
