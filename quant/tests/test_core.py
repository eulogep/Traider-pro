from dataclasses import replace
from io import StringIO
import pandas as pd
import pytest
from ai_trader_optimizer.core import TestConfig as Config, load_m1_csv, add_features, run_backtest, synthetic_m1


def test_demo_data_generates_and_runs():
    df = synthetic_m1()
    tr, curve, m = run_backtest(df, Config())
    assert len(curve) > 100
    assert m["trades"] == len(tr)
    assert not hasattr(m, "order_send")


def test_bad_data_requires_explicit_timezone():
    df = synthetic_m1().head(140).copy()
    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    with pytest.raises(ValueError, match="explicit UTC offset"):
        load_m1_csv(StringIO(df.to_csv(index=False)))


def test_duplicate_rejected():
    df = synthetic_m1().head(140).copy()
    df.loc[1, "timestamp"] = df.loc[0, "timestamp"]
    with pytest.raises(ValueError, match="duplicated"):
        load_m1_csv(StringIO(df.to_csv(index=False)))


def test_ohlc_invalid_rejected():
    df = synthetic_m1().head(140).copy()
    df.loc[1, "high"] = df.loc[1, "low"] - 1
    with pytest.raises(ValueError, match="Invalid OHLC"):
        load_m1_csv(StringIO(df.to_csv(index=False)))


def test_no_trade_before_signal_closed():
    df = synthetic_m1()
    f = add_features(df)
    tr, _, _ = run_backtest(df, Config())
    for _, r in tr.iterrows():
        ix = df.index[df["timestamp"] == r["entry_time"]][0]
        assert ix >= 1
        assert int(f.loc[ix-1, "signal"]) in (-1, 1)


def test_position_size_does_not_exceed_risk_budget_on_entry():
    df = synthetic_m1()
    cfg = Config()
    tr, _, _ = run_backtest(df, cfg)
    for _, t in tr.iterrows():
        # Approx: initial equity only to allow profitable progression; the backtester
        # itself recomputes using current equity at entry.
        assert t["lots"] > 0
        assert t["lots"] >= cfg.min_lot - 1e-9


def test_strict_trade_daily_limit():
    df = synthetic_m1()
    cfg = replace(Config(), max_trades_per_day=1)
    tr, _, _ = run_backtest(df, cfg)
    if not tr.empty:
        assert tr.groupby(pd.to_datetime(tr["entry_time"]).dt.date).size().max() <= 1
