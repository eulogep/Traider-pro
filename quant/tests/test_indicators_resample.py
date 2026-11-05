"""Indicators against hand-computed values; higher-timeframe alignment without look-ahead."""

import math

import numpy as np
import pandas as pd
import pytest

from ai_trader_optimizer.data.resample import align_higher_timeframe, resample_ohlc
from ai_trader_optimizer.features.indicators import atr, candle_color, ema, macd, sma, true_range

from conftest import make_bars


def test_ema_recursion():
    # span 3 -> alpha 0.5: 1, 1.5, 2.25, 3.125
    assert ema(pd.Series([1.0, 2, 3, 4]), 3).tolist() == [1.0, 1.5, 2.25, 3.125]


def test_sma_warmup_is_nan():
    s = sma(pd.Series([1.0, 2, 3, 4]), 3)
    assert math.isnan(s[0]) and math.isnan(s[1]) and s[2:].tolist() == [2.0, 3.0]


BARS = make_bars([(10, 11, 9, 10.5), (10.5, 12, 10, 11.5), (11.5, 11.8, 10.2, 10.4), (10.4, 13, 10.3, 12.9)])


def test_true_range_uses_previous_close():
    # TR: 2 ; max(2, 1.5, 0.5)=2 ; max(1.6, 0.3, 1.3)=1.6 ; max(2.7, 2.6, 0.1)=2.7
    assert true_range(BARS).tolist() == pytest.approx([2.0, 2.0, 1.6, 2.7])


def test_atr_wilder_and_sma():
    w = atr(BARS, 3, "wilder")
    assert math.isnan(w[1]) and w[2] == pytest.approx((2 + 2 + 1.6) / 3)
    assert w[3] == pytest.approx((w[2] * 2 + 2.7) / 3)
    assert atr(BARS, 3, "sma")[3] == pytest.approx((2 + 1.6 + 2.7) / 3)
    with pytest.raises(ValueError):
        atr(BARS, 3, "magic")


def test_macd_definition():
    close = pd.Series(np.linspace(100, 110, 60))
    m = macd(close, 12, 26, 9)
    assert np.allclose(m["macd"], ema(close, 12) - ema(close, 26))
    assert np.allclose(m["macd_hist"], m["macd"] - m["macd_signal"])


def test_candle_color():
    assert candle_color(make_bars([(1, 2, 0.5, 1.5), (1.5, 2, 1, 1), (1, 1, 1, 1)])).tolist() == [1, -1, 0]


def test_m15_alignment_only_uses_closed_bars():
    m1 = make_bars([(100 + i, 100 + i + 0.5, 100 + i - 0.5, 100 + i + 0.2) for i in range(45)],
                   start=pd.Timestamp("2026-09-07T12:00Z"))
    m15 = resample_ohlc(m1, "M1", "M15")
    assert m15["complete"].all() and m15["n_bars"].tolist() == [15, 15, 15]
    assert m15.loc[0, "close"] == m1.loc[14, "close"] and m15.loc[0, "high"] == m1.loc[:14, "high"].max()
    al = align_higher_timeframe(m1, "M1", m15, ["close"], prefix="m15_")
    # M1 bar 12:13 closes 12:14 -> the 12:00 M15 bar (closes 12:15) is NOT yet known
    assert math.isnan(al.loc[13, "m15_close"])
    # M1 bar 12:14 closes 12:15 -> 12:00 M15 bar just closed
    assert al.loc[14, "m15_close"] == m15.loc[0, "close"]
    assert al.loc[29, "m15_close"] == m15.loc[1, "close"]
    assert (al["m15_available_at"].dropna() <= al.loc[al["m15_available_at"].notna(), "timestamp"]
            + pd.Timedelta(minutes=1)).all()


def test_incomplete_higher_bar_not_exposed():
    m1 = make_bars([(100, 100.5, 99.5, 100.2)] * 30, start=pd.Timestamp("2026-09-07T12:00Z")).drop(index=[20])
    m15 = resample_ohlc(m1.reset_index(drop=True), "M1", "M15")
    assert m15["complete"].tolist() == [True, False]
    al = align_higher_timeframe(m1.reset_index(drop=True), "M1", m15, ["close"], prefix="h_")
    assert al["h_available_at"].dropna().max() == pd.Timestamp("2026-09-07T12:15Z")
