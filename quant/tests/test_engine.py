"""Backtest engine: fills, P&L with costs, chronology, look-ahead, reproducibility."""

import numpy as np
import pandas as pd
import pytest

from ai_trader_optimizer import core as legacy
from ai_trader_optimizer.backtest import BacktestConfig, run_backtest
from ai_trader_optimizer.data import synthetic_dataset
from ai_trader_optimizer.risk import LEGACY_V01_RISK
from ai_trader_optimizer.strategies import load_catalog

from conftest import base_config, flat_bar, make_bars, make_dataset, scripted

BASELINE = "baseline.ema_trend_3bars@1.0.0"


def run(ohlc, script, cfg=None, **kw):
    spec, strat = scripted(script)
    return run_backtest(make_dataset(ohlc, **kw), spec, cfg or base_config(), strategy=strat)


# Hand-computed reference (spread 0.30, slip 0.05, commission 3/lot/side, 100 oz/lot, 10 000 USD, 0.25 %):
# risk/lot = (2.00 + 0.05) * 100 + 2*3 = 211  -> lots = floor(25 / 211, 0.01) = 0.11 ; planned = 23.21


def test_buy_take_profit_pnl_exact():
    r = run([flat_bar(), (100, 101, 99.5, 100.5), (100.5, 104, 100, 103), flat_bar(103)], {0: (1, 2.0, 3.0)})
    t = r.trades.iloc[0]
    assert t["entry_time"] == pd.Timestamp("2026-09-07T12:01Z")  # bar AFTER the signal bar
    assert t["entry_price"] == pytest.approx(100.35)  # ask + slippage
    assert t["stop_loss"] == pytest.approx(98.35) and t["take_profit"] == pytest.approx(103.35)
    assert t["lots"] == pytest.approx(0.11)
    assert t["planned_risk"] == pytest.approx(23.21)
    assert t["exit_reason"] == "TP" and t["exit_price"] == pytest.approx(103.30)
    assert t["price_pnl"] == pytest.approx(32.45)
    assert t["commission"] == pytest.approx(0.66)
    assert t["net_pnl"] == pytest.approx(31.79)
    assert t["spread_cost"] == pytest.approx(3.30) and t["slippage_cost"] == pytest.approx(1.10)
    assert r.metrics["final_equity"] == pytest.approx(10_031.79)


def test_sell_stop_loss_uses_ask_and_equals_planned_risk():
    r = run([flat_bar(), (100, 101.8, 99.9, 100.2), flat_bar()], {0: (-1, 2.0, 3.0)})
    t = r.trades.iloc[0]
    assert t["entry_price"] == pytest.approx(99.95)  # bid - slippage
    assert t["exit_reason"] == "SL"  # ask high = 101.8 + 0.3 >= 101.95
    assert t["exit_price"] == pytest.approx(102.00)
    assert t["net_pnl"] == pytest.approx(-23.21)
    assert t["net_pnl"] == pytest.approx(-t["planned_risk"])


def test_stop_has_priority_when_sl_and_tp_in_same_bar():
    r = run([flat_bar(), (100, 104, 98, 101), flat_bar()], {0: (1, 2.0, 3.0)})
    t = r.trades.iloc[0]
    assert t["exit_reason"] == "SL" and t["exit_price"] == pytest.approx(98.30)


def test_gap_through_stop_fills_at_open_and_loss_exceeds_plan():
    r = run([flat_bar(), (100, 100.5, 99.8, 100), (97, 97.2, 96.5, 97), flat_bar(97)], {0: (1, 2.0, 3.0)})
    t = r.trades.iloc[0]
    assert t["exit_reason"] == "SL_GAP" and t["exit_price"] == pytest.approx(96.95)
    assert t["net_pnl"] == pytest.approx((96.95 - 100.35) * 11 - 0.66)
    assert r.metrics["losses_beyond_planned_risk"] == 1


def test_end_of_data_closes_at_last_close():
    r = run([flat_bar(), flat_bar(), (100, 101.2, 99.9, 101)], {0: (1, 2.0, 3.0)})
    t = r.trades.iloc[0]
    assert t["exit_reason"] == "END_OF_DATA" and t["exit_price"] == pytest.approx(100.95)


def test_no_entry_across_missing_bar():
    times = pd.DatetimeIndex(["2026-09-07T12:00Z", "2026-09-07T12:02Z", "2026-09-07T12:03Z"])
    r = run([flat_bar()] * 3, {0: (1, 2.0, 3.0)}, times=times)
    assert r.trades.empty
    assert "DATA_INVALID" in r.decisions.iloc[0]["reasons"]


def test_no_reentry_in_exit_bar_and_one_position_at_a_time():
    ohlc = [flat_bar(), flat_bar(), (100, 104, 99.9, 103), flat_bar(103), flat_bar(103)]
    r = run(ohlc, {0: (1, 2.0, 3.0), 1: (1, 2.0, 3.0), 2: (1, 2.0, 50.0), 3: (1, 2.0, 3.0)})
    reasons = r.decisions.set_index("decision_id")["reasons"]
    assert r.trades.iloc[0]["exit_time"] == pd.Timestamp("2026-09-07T12:02Z")
    assert reasons[2] == "EXITED_THIS_BAR"  # trade 1 exits in bar 2, where signal of bar 1 would enter
    assert reasons[3] == ""  # entered at bar 3
    assert "MAX_OPEN_POSITIONS" in reasons[4]
    assert (r.trades["entry_time"].diff().dropna() > pd.Timedelta(0)).all()


def test_signal_on_last_bar_is_never_executed():
    r = run([flat_bar()] * 3, {2: (1, 2.0, 3.0)})
    assert r.trades.empty and r.decisions.empty


def test_time_exit_after_max_bars():
    ohlc = [flat_bar()] * 6
    r = run(ohlc, {0: (1, 2.0, 30.0)}, cfg=base_config(max_bars_in_trade=2))
    assert r.trades.iloc[0]["exit_reason"] == "TIME_EXIT"
    assert r.trades.iloc[0]["exit_time"] == pd.Timestamp("2026-09-07T12:03Z")


def test_session_end_exit_at_first_bar_outside_session():
    from conftest import scripted_spec
    spec = scripted_spec(trading_hours={"timezone": "UTC", "sessions": ["12:00-12:03"], "weekdays": [0]})
    spec, strat = scripted({0: (1, 2.0, 30.0)}, spec=spec)
    r = run_backtest(make_dataset([flat_bar()] * 6), spec, base_config(close_at_session_end=True), strategy=strat)
    t = r.trades.iloc[0]
    assert t["exit_reason"] == "SESSION_END" and t["exit_time"] == pd.Timestamp("2026-09-07T12:03Z")
    assert t["exit_price"] == pytest.approx(100 - 0.05)


def test_outside_window_and_trade_end_truncate_data():
    ohlc = [flat_bar()] * 10
    cfg = base_config(trade_start="2026-09-07T12:05:00Z", trade_end="2026-09-07T12:08:00Z")
    r = run(ohlc, {0: (1, 2.0, 3.0), 5: (1, 2.0, 3.0)}, cfg=cfg)
    assert r.decisions.iloc[0]["reasons"] == "OUTSIDE_TEST_WINDOW"
    # B3 (V0.3.1): trade_end bounds bar CLOSES. The 12:08 bar closes at 12:09 > 12:08, so the last
    # evaluated bar is 12:07 (V0.3 wrongly used the whole 12:08 bar, which leaked past the cut).
    assert len(r.trades) == 1 and r.trades.iloc[0]["exit_time"] == pd.Timestamp("2026-09-07T12:07Z")
    assert r.equity["timestamp"].min() == pd.Timestamp("2026-09-07T12:05Z")


def test_no_signal_market_produces_no_trade_and_honest_metrics():
    # Strictly rising green candles: the R-V-V pattern never occurs.
    ohlc = [(100 + i * 0.1, 100 + i * 0.1 + 0.15, 100 + i * 0.1 - 0.02, 100 + i * 0.1 + 0.1) for i in range(300)]
    spec = load_catalog().specs[BASELINE]
    r = run_backtest(make_dataset(ohlc), spec, BacktestConfig())
    assert r.trades.empty and r.metrics["trades"] == 0
    assert r.metrics["win_rate_pct"] is None and "profit_factor" in r.metrics["unavailable"]
    assert r.metrics["net_pnl"] == 0


def test_strategy_signals_are_causal_prefix_invariant():
    ds = synthetic_dataset(seed=3, days=3)
    spec = load_catalog().specs[BASELINE]
    from ai_trader_optimizer.strategies import build_strategy
    for method in ("sma", "wilder"):
        strat = build_strategy(spec, {"atr_method": method})
        full = strat.compute(ds.bars)
        for k in (60, 777, 2500):
            part = strat.compute(ds.bars.iloc[:k])
            pd.testing.assert_frame_equal(part, full.iloc[:k])


def test_future_prices_cannot_change_past_decisions():
    ds = synthetic_dataset(seed=11, days=5)
    spec = load_catalog().specs[BASELINE]
    cfg = BacktestConfig()
    ref = run_backtest(ds, spec, cfg)
    cut = ds.bars["timestamp"].iloc[3000]
    bars = ds.bars.copy()
    rng = np.random.default_rng(0)
    after = bars["timestamp"] > cut
    noise = rng.normal(0, 3, after.sum())
    for col in ("open", "high", "low", "close"):
        bars.loc[after, col] = bars.loc[after, col] + noise
    bars.loc[after, "high"] = bars.loc[after, ["open", "high", "low", "close"]].max(axis=1) + 0.1
    bars.loc[after, "low"] = bars.loc[after, ["open", "high", "low", "close"]].min(axis=1) - 0.1
    alt = run_backtest(make_dataset(frame=bars), spec, cfg)
    closed_before = lambda r: r.trades[r.trades["exit_time"] <= cut].drop(columns=["equity_after"])  # noqa: E731
    pd.testing.assert_frame_equal(closed_before(ref), closed_before(alt))
    dec = lambda r: r.decisions[r.decisions["entry_bar_time"] <= cut]  # noqa: E731
    pd.testing.assert_frame_equal(dec(ref), dec(alt))


def test_reproducible_same_config_same_hash():
    ds = synthetic_dataset()
    spec = load_catalog().specs[BASELINE]
    a = run_backtest(ds, spec, BacktestConfig())
    b = run_backtest(synthetic_dataset(), spec, BacktestConfig())
    assert a.manifest["run_id"] == b.manifest["run_id"]
    assert a.manifest["result_hash"] == b.manifest["result_hash"]
    c = run_backtest(ds, spec, BacktestConfig(strategy_params={"rr": 2.0}))
    assert c.manifest["run_id"] != a.manifest["run_id"]


def test_manifest_links_data_strategy_and_config():
    ds = synthetic_dataset()
    spec = load_catalog().specs[BASELINE]
    r = run_backtest(ds, spec, BacktestConfig())
    m = r.manifest
    assert m["dataset"]["dataset_id"] == ds.meta.dataset_id
    assert m["strategy"]["version"] == "1.0.0" and m["strategy"]["spec_hash"] == spec.spec_hash()
    assert m["config"]["costs"]["spread"] == 0.30
    assert m["data_kind"] == "synthetic" and m["execution_mode"] == "simulation"


@pytest.mark.parametrize("seed,days", [(42, 10), (7, 30)])
def test_matches_frozen_v01_engine_with_explicit_legacy_rules(seed, days):
    ds = synthetic_dataset(seed=seed, days=days)
    old, _, _ = legacy.run_backtest(ds.bars, legacy.TestConfig())
    new = run_backtest(ds, load_catalog().specs[BASELINE], BacktestConfig(risk=LEGACY_V01_RISK)).trades
    assert len(old) == len(new) > 0
    assert (old["entry_time"].values == new["entry_time"].values).all()
    assert (old["exit_time"].values == new["exit_time"].values).all()
    assert (old["direction"].values == new["direction"].values).all()
    assert np.allclose(old["lots"], new["lots"])
    assert np.allclose(old["net_pnl_usd"], new["net_pnl"].round(2), atol=0.011)


def test_decision_journal_explains_every_signal():
    ds = synthetic_dataset()
    r = run_backtest(ds, load_catalog().specs[BASELINE], BacktestConfig())
    assert r.metrics["signals"] == len(r.decisions)
    assert (r.decisions["outcome"] == "ENTERED").sum() == len(r.trades)
    rejected = r.decisions[r.decisions["outcome"] == "REJECTED"]
    assert rejected["reasons"].str.len().gt(0).all()
    assert {"f_ema_fast", "f_ema_slow", "f_atr"} <= set(r.decisions.columns)
    # entry strictly after the decision time, which is the close of the signal bar
    entered = r.decisions[r.decisions["outcome"] == "ENTERED"]
    assert (entered["entry_bar_time"] >= entered["decision_time"]).all()
    assert (entered["decision_time"] == entered["signal_time"] + pd.Timedelta(minutes=1)).all()


def test_timeframe_mismatch_refused():
    bars = make_bars([flat_bar()] * 5, times=pd.date_range("2026-09-07T12:00Z", periods=5, freq="5min"))
    spec, strat = scripted({})
    with pytest.raises(ValueError, match="M1"):
        run_backtest(make_dataset(frame=bars), spec, base_config(), strategy=strat)
