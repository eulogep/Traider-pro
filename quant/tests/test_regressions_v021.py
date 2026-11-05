"""Non-regression tests for defects confirmed during the 2026-11-03 consolidation audit.

Each defect was reproduced by a probe on v0.2.0 (outputs recorded in docs/CODEX_REVIEW_HANDOFF.md);
these tests encode the corrected behaviour (they were not re-run against the v0.2.0 code).
"""

import numpy as np
import pytest

from ai_trader_optimizer.backtest import BacktestConfig, ExecutionCosts, run_backtest
from ai_trader_optimizer.backtest.codehash import code_fingerprint
from ai_trader_optimizer.data import dataset_from_frame, synthetic_dataset
from ai_trader_optimizer.safety import DataKind
from ai_trader_optimizer.storage import LabCatalog, ReproducibilityError
from ai_trader_optimizer.strategies import StrategyNotRunnableError, load_catalog

from conftest import base_config, flat_bar, make_bars, make_dataset, scripted, scripted_spec

BASELINE = "baseline.ema_trend_3bars@1.0.0"


# R1 — v0.2.0: a stop closer than spread+slippage was hit at once; loss 54.74 for a planned risk of 24.99.
def test_r1_stop_inside_spread_is_refused():
    spec, strat = scripted({0: (1, 0.1, 1.0)})
    r = run_backtest(make_dataset([flat_bar()] * 4), spec, base_config(), strategy=strat)
    assert r.trades.empty
    assert "STOP_INSIDE_SPREAD" in r.decisions.iloc[0]["reasons"]


def test_r1_stop_just_outside_spread_is_accepted_and_bounded():
    spec, strat = scripted({0: (-1, 0.36, 5.0)})  # spread 0.30 + slippage 0.05 = 0.35
    r = run_backtest(make_dataset([flat_bar()] * 4), spec, base_config(), strategy=strat)
    t = r.trades.iloc[0]
    assert t["exit_reason"] == "SL"
    assert -t["net_pnl"] <= t["planned_risk"] + 1e-9  # no gap here: realised loss within plan


# R2 — v0.2.0: EURUSD data sized with the XAUUSD (100 oz) contract -> 50 lots.
def test_r2_contract_symbol_must_match_dataset():
    fx = make_bars([(1.10, 1.1002, 1.0998, 1.10)] * 5)
    ds = dataset_from_frame(fx, name="eur", symbol="EURUSD", source_label="t", kind=DataKind.HISTORICAL)
    spec, strat = scripted({0: (1, 0.0010, 0.002)})
    cfg = base_config().model_copy(update={"costs": ExecutionCosts(spread=0.00002, slippage=0, commission_per_lot_per_side=0)})
    r = run_backtest(ds, spec, cfg, strategy=strat)
    assert r.trades.empty and "CONTRACT_SYMBOL_MISMATCH" in r.decisions.iloc[0]["reasons"]
    # with the right contract (100 000 units/lot) the size becomes sane
    eur = cfg.contract.model_copy(update={"symbol": "EURUSD", "contract_size": 100_000, "max_lot": 50})
    r = run_backtest(ds, spec, cfg.model_copy(update={"contract": eur}), strategy=strat)
    assert r.trades.iloc[0]["lots"] == pytest.approx(0.25)  # 25 USD / (0.0010 * 100 000)
    assert r.trades.iloc[0]["planned_risk"] <= 25.0


def test_r2_broker_suffixes_and_demo_symbol_still_match():
    from ai_trader_optimizer.risk import XAUUSD_HYPOTHETICAL
    assert XAUUSD_HYPOTHETICAL.matches("XAUUSD.m") and XAUUSD_HYPOTHETICAL.matches("XAUUSD-DEMO")
    assert not XAUUSD_HYPOTHETICAL.matches("GOLD") and not XAUUSD_HYPOTHETICAL.matches("EURUSD")


# R3 — v0.2.0: a draft spec ran when a strategy object was passed directly.
@pytest.mark.parametrize("overrides", [{"status": "draft"}, {"category": "third_party", "usage_rights": "unclear"},
                                       {"position_scaling": "martingale"}])
def test_r3_injected_strategy_cannot_bypass_spec_checks(overrides):
    spec, strat = scripted({0: (1, 2.0, 3.0)}, spec=scripted_spec(**overrides))
    with pytest.raises(StrategyNotRunnableError):
        run_backtest(make_dataset([flat_bar()] * 4), spec, base_config(), strategy=strat)


def test_r3_strategy_spec_mismatch_refused():
    _, strat = scripted({0: (1, 2.0, 3.0)})
    other = scripted_spec(id="test.other")
    with pytest.raises(StrategyNotRunnableError):
        run_backtest(make_dataset([flat_bar()] * 4), other, base_config(), strategy=strat)


# R4 — v0.2.0: save_run silently overwrote a run with the same id and different results;
#               run_id ignored the code version.
def test_r4_catalog_never_overwrites_different_results(lab_dir):
    cat = LabCatalog()
    ds = synthetic_dataset(days=3)
    cat.save_dataset(ds)
    res = run_backtest(ds, load_catalog().specs[BASELINE], BacktestConfig())
    cat.save_run(res)
    cat.save_run(res)  # identical: idempotent
    original = res.manifest["result_hash"]
    res.manifest["result_hash"] = "different"
    with pytest.raises(ReproducibilityError):
        cat.save_run(res)
    assert cat.load_run(res.run_id).manifest["result_hash"] == original


def test_r4_run_id_and_manifest_include_code_fingerprint():
    ds = synthetic_dataset(days=3)
    res = run_backtest(ds, load_catalog().specs[BASELINE], BacktestConfig())
    assert res.manifest["code_hash"] == code_fingerprint() and len(code_fingerprint()) == 16


# Accounting identities (SELL sign, bid/mid, metrics = trades = equity curve) — checked on many runs.
@pytest.mark.parametrize("seed", range(4))
@pytest.mark.parametrize("side", ["bid", "mid"])
def test_accounting_identities_hold(seed, side):
    d = synthetic_dataset(seed=seed, days=6)
    if side == "mid":
        d = dataset_from_frame(d.bars, name="m", symbol="XAUUSD", source_label="t", kind=DataKind.SYNTHETIC,
                               price_side="mid")
    cfg = BacktestConfig(strategy_params={"rr": 1.0})
    r = run_backtest(d, load_catalog().specs[BASELINE], cfg)
    t = r.trades
    assert len(t) > 0 and (t["direction"] == "SELL").any()
    sign = np.where(t["direction"] == "BUY", 1, -1)
    cs = cfg.contract.contract_size
    assert np.allclose(t["price_pnl"], sign * (t["exit_price"] - t["entry_price"]) * t["lots"] * cs)
    assert np.allclose(t["net_pnl"], t["price_pnl"] - 2 * cfg.costs.commission_per_lot_per_side * t["lots"])
    assert r.metrics["net_pnl"] == pytest.approx(t["net_pnl"].sum())
    assert r.metrics["final_equity"] == pytest.approx(r.equity["closed_equity"].iloc[-1])
    assert r.metrics["final_equity"] == pytest.approx(cfg.initial_equity + t["net_pnl"].sum())
    # every fill pays the spread: BUY enters above the bar's bid open, SELL exits at bid + spread
    side_shift = 0.0 if side == "bid" else -cfg.costs.spread / 2
    bars = d.bars.set_index("timestamp")
    buys, sells = t[t["direction"] == "BUY"], t[t["direction"] == "SELL"]
    assert np.allclose(buys["entry_price"], bars.loc[buys["entry_time"], "open"].to_numpy() + side_shift
                       + cfg.costs.spread + cfg.costs.slippage)
    assert np.allclose(sells["entry_price"], bars.loc[sells["entry_time"], "open"].to_numpy() + side_shift
                       - cfg.costs.slippage)
