"""Risk Guardian: sizing, limits, fail-closed behaviour."""

import pandas as pd
import pytest

from ai_trader_optimizer.backtest import run_backtest
from ai_trader_optimizer.risk import (
    ContractSpec,
    RiskConfig,
    RiskGuardian,
    TradeProposal,
    floor_to_step,
    position_size,
)
from ai_trader_optimizer.risk import guardian as guardian_mod
from ai_trader_optimizer.strategies import StrategyNotRunnableError, build_strategy

from conftest import base_config, flat_bar, make_dataset, scripted, scripted_spec

GOLD = ContractSpec(symbol="XAUUSD", contract_size=100, min_lot=0.01, lot_step=0.01, max_lot=50, quote_currency="USD")


def losing_series(n_signals, gap=3):
    """BUY signals every `gap` bars; each one is stopped out on its entry bar (loss = planned risk)."""
    ohlc, script = [], {}
    for k in range(n_signals):
        ohlc += [flat_bar(), (100, 100.2, 97.0, 98.0)] + [flat_bar()] * (gap - 2)
        script[k * gap] = (1, 2.0, 3.0)
    return ohlc, script


def run(ohlc, script, risk, contract=GOLD, **kw):
    spec, strat = scripted(script, spec=kw.pop("spec", None))
    cfg = base_config(risk=risk)
    cfg = cfg.model_copy(update={"contract": contract, **kw})
    return run_backtest(make_dataset(ohlc), spec, cfg, strategy=strat)


def test_position_size_formula():
    lots, per_lot = position_size(10_000, 0.25, 2.0, 0.05, 3.0, GOLD)
    assert per_lot == pytest.approx(211.0) and lots == pytest.approx(0.11)
    assert lots * per_lot <= 25.0
    # size scales with equity and inversely with stop distance — never a universal constant
    assert position_size(20_000, 0.25, 2.0, 0.05, 3.0, GOLD)[0] == pytest.approx(0.23)
    assert position_size(10_000, 0.25, 4.0, 0.05, 3.0, GOLD)[0] == pytest.approx(0.06)
    mini = GOLD.model_copy(update={"contract_size": 10.0})
    assert position_size(10_000, 0.25, 2.0, 0.05, 3.0, mini)[0] == pytest.approx(0.94)


def test_floor_never_rounds_up_and_max_lot_cap():
    assert floor_to_step(0.1199999, 0.01) == pytest.approx(0.11)
    capped = GOLD.model_copy(update={"max_lot": 0.05})
    assert position_size(1_000_000, 1, 2.0, 0.05, 3.0, capped)[0] == pytest.approx(0.05)


def test_size_below_min_lot_rejected():
    g = RiskGuardian(RiskConfig(), GOLD, initial_equity=100)
    d = g.evaluate(TradeProposal(1, 2.0, 0.05, 3.0))
    assert not d.approved and "SIZE_BELOW_MIN_LOT" in d.reasons


@pytest.mark.parametrize("contract,code", [
    (ContractSpec(symbol="XAUUSD"), "CONTRACT_UNKNOWN"),
    (GOLD.model_copy(update={"lot_step": 0}), "CONTRACT_UNKNOWN"),
    (GOLD.model_copy(update={"quote_currency": "EUR"}), "CONTRACT_UNKNOWN"),  # XAUUSD cannot be quoted in EUR
])
def test_unknown_or_unconvertible_contract_blocks_every_trade(contract, code):
    ohlc, script = losing_series(3)
    r = run(ohlc, script, RiskConfig(), contract=contract)
    assert r.trades.empty
    assert r.decisions["reasons"].str.contains(code).all()


def test_daily_loss_limit_includes_planned_risk():
    ohlc, script = losing_series(6)
    risk = RiskConfig(risk_per_trade_pct=0.25, max_daily_loss_pct=0.6, max_trades_per_day=50, max_losses_per_day=None)
    r = run(ohlc, script, risk)
    assert len(r.trades) == 2  # a 3rd loss of ~0.23 % would breach 0.6 %
    assert r.trades["net_pnl"].sum() >= -0.006 * 10_000
    assert "DAILY_LOSS_BUDGET_INSUFFICIENT" in r.metrics["rejection_reasons"]


def test_v01_daily_check_overshoots_limit_documented_defect():
    ohlc, script = losing_series(6)
    risk = RiskConfig(risk_per_trade_pct=0.25, max_daily_loss_pct=0.6, max_trades_per_day=50, max_losses_per_day=None,
                      daily_limit_includes_planned_risk=False)
    r = run(ohlc, script, risk)
    assert len(r.trades) == 3
    assert r.trades["net_pnl"].sum() < -0.006 * 10_000  # the realised-only rule lets the day exceed its cap
    assert "DAILY_LOSS_LIMIT" in r.metrics["rejection_reasons"]


def test_max_drawdown_halts_for_the_rest_of_the_run():
    ohlc, script = losing_series(8)
    risk = RiskConfig(max_drawdown_pct=0.5, max_daily_loss_pct=50, max_trades_per_day=50, max_losses_per_day=None,
                      drawdown_limit_includes_planned_risk=False)
    r = run(ohlc, script, risk)
    assert len(r.trades) == 3  # 3 x 0.232 % >= 0.5 % -> halted
    assert r.metrics["rejection_reasons"]["MAX_DRAWDOWN_HALT"] == 5


def test_consecutive_losses_stop():
    ohlc, script = losing_series(5)
    risk = RiskConfig(max_consecutive_losses=2, consecutive_loss_scope="run", max_daily_loss_pct=50,
                      max_trades_per_day=50, max_losses_per_day=None)
    r = run(ohlc, script, risk)
    assert len(r.trades) == 2 and r.metrics["rejection_reasons"]["MAX_CONSECUTIVE_LOSSES"] == 3


def test_max_trades_per_day_and_losses_per_day():
    ohlc, script = losing_series(4)
    r = run(ohlc, script, RiskConfig(max_trades_per_day=1, max_daily_loss_pct=50, max_losses_per_day=None))
    assert len(r.trades) == 1
    r = run(ohlc, script, RiskConfig(max_trades_per_day=50, max_daily_loss_pct=50, max_losses_per_day=2))
    assert len(r.trades) == 2


def test_daily_counters_reset_in_configured_timezone():
    # 21:30 UTC and 22:30 UTC on 2026-09-07 = same UTC day, but 23:30 / 00:30 in Paris (CEST).
    times = pd.date_range("2026-09-07T21:28Z", periods=70, freq="min")
    ohlc = [flat_bar()] * 70
    script = {2: (1, 0.4, 1.0), 62: (1, 0.4, 1.0)}  # stopped out on entry bar
    for tz, expected in (("UTC", 1), ("Europe/Paris", 2)):
        spec, strat = scripted(script)
        cfg = base_config(risk=RiskConfig(max_trades_per_day=1, day_timezone=tz, max_daily_loss_pct=50))
        r = run_backtest(make_dataset(ohlc, times=times), spec, cfg, strategy=strat)
        assert len(r.trades) == expected, tz


def test_session_hours_in_strategy_timezone():
    spec = scripted_spec(trading_hours={"timezone": "Europe/Paris", "sessions": ["14:00-15:00"], "weekdays": [0]})
    times = pd.date_range("2026-09-07T12:28Z", periods=70, freq="min")  # Paris = UTC+2 in September
    spec, strat = scripted({1: (1, 0.4, 1.0), 61: (1, 0.4, 1.0)}, spec=spec)
    r = run_backtest(make_dataset([flat_bar()] * 70, times=times), spec, base_config(), strategy=strat)
    assert len(r.trades) == 1 and r.trades.iloc[0]["entry_time"] == pd.Timestamp("2026-09-07T12:30Z")
    assert r.decisions.iloc[1]["reasons"] == "OUTSIDE_SESSION"


def test_martingale_strategies_refused():
    spec = scripted_spec(position_scaling="martingale")
    with pytest.raises(StrategyNotRunnableError, match="martingale"):
        build_strategy(spec)
    g = RiskGuardian(RiskConfig(), GOLD, 10_000)
    assert "MARTINGALE_FORBIDDEN" in g.evaluate(TradeProposal(1, 2.0, 0.05, 3.0, position_scaling="grid")).reasons
    with pytest.raises(ValueError):
        RiskConfig(allow_martingale=True)


def test_risk_never_grows_after_losses():
    ohlc, script = losing_series(5)
    r = run(ohlc, script, RiskConfig(max_daily_loss_pct=50, max_trades_per_day=50, max_losses_per_day=None))
    assert r.trades["planned_risk"].is_monotonic_decreasing
    eq_before = r.trades["equity_after"].shift(1, fill_value=10_000)
    assert (r.trades["planned_risk"] <= eq_before * 0.0025 + 1e-9).all()


def test_invalid_data_and_invalid_stop_fail_closed():
    g = RiskGuardian(RiskConfig(), GOLD, 10_000)
    assert "DATA_INVALID" in g.evaluate(TradeProposal(1, 2.0, 0.05, 3.0, data_ok=False)).reasons
    for bad in (0.0, -1.0, float("nan"), float("inf")):
        d = g.evaluate(TradeProposal(1, bad, 0.05, 3.0))
        assert not d.approved and "INVALID_STOP" in d.reasons


def test_internal_error_fails_closed(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("bug")
    monkeypatch.setattr(guardian_mod, "position_size", boom)
    d = RiskGuardian(RiskConfig(), GOLD, 10_000).evaluate(TradeProposal(1, 2.0, 0.05, 3.0))
    assert not d.approved and d.reasons == ["GUARDIAN_ERROR"]


def test_quote_currency_different_from_account_is_refused():
    xaueur = GOLD.model_copy(update={"symbol": "XAUEUR", "quote_currency": "EUR"})
    g = RiskGuardian(RiskConfig(), xaueur, 10_000, account_currency="USD", instrument_symbol="XAUEUR")
    d = g.evaluate(TradeProposal(1, 2.0, 0.05, 3.0))
    assert not d.approved and d.reasons == ["CONTRACT_CURRENCY_MISMATCH"]
