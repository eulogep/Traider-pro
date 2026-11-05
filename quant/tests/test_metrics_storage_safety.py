"""Metrics on known trades, catalog persistence, safety scans, chronological splits."""

import re
from pathlib import Path

import pandas as pd
import pytest

from ai_trader_optimizer.ai import chronological_split, walk_forward_splits
from ai_trader_optimizer.analytics import compute_metrics, results_by_period
from ai_trader_optimizer.backtest import BacktestConfig, run_backtest
from ai_trader_optimizer.data import synthetic_dataset
from ai_trader_optimizer.execution import (
    DemoAccountAdapter,
    LiveAccountAdapter,
    OrderIntent,
    SimulationAdapter,
)
from ai_trader_optimizer.safety import DEMO_TRADING_ENABLED, LIVE_TRADING_ENABLED, ExecutionDisabledError
from ai_trader_optimizer.storage import LabCatalog
from ai_trader_optimizer.strategies import load_catalog

PKG = Path(__file__).resolve().parents[1] / "src" / "ai_trader_optimizer"


def trades_frame(pnls, risk=10.0):
    n = len(pnls)
    eq = 1000 + pd.Series(pnls).cumsum()
    return pd.DataFrame({
        "net_pnl": pnls, "r_multiple": [p / risk for p in pnls], "planned_risk": [risk] * n,
        "equity_after": eq, "bars_held": [3] * n, "commission": [1.0] * n, "spread_cost": [2.0] * n,
        "slippage_cost": [0.5] * n, "exit_reason": ["TP" if p > 0 else "SL" for p in pnls],
        "direction": ["BUY"] * n, "gap_during_trade": [False] * n,
        "entry_time": pd.date_range("2026-09-07T12:00Z", periods=n, freq="D"),
    })


def test_metrics_on_known_trades():
    t = trades_frame([20.0, -10.0, 15.0, -10.0, -10.0])
    eq = pd.DataFrame({"closed_equity": t["equity_after"], "mtm_equity": t["equity_after"]})
    m = compute_metrics(t, eq, 1000)
    assert m["net_pnl"] == pytest.approx(5.0) and m["trades"] == 5
    assert m["win_rate_pct"] == pytest.approx(40.0)
    assert m["profit_factor"] == pytest.approx(35 / 30)
    assert m["expectancy"] == pytest.approx(1.0) and m["expectancy_r"] == pytest.approx(0.1)
    assert m["payoff_ratio"] == pytest.approx(17.5 / 10)
    assert m["max_consecutive_losses"] == 2
    assert m["max_dd_closed"] == pytest.approx(-20.0)  # equity 1020,1010,1025,1015,1005: peak 1025 -> 1005
    assert m["max_dd_closed_pct"] == pytest.approx(-20 / 1025 * 100)
    assert m["total_costs"] == pytest.approx(17.5) and m["pnl_before_costs"] == pytest.approx(22.5)
    assert not m["sample_sufficient"]


def test_profit_factor_unavailable_without_losses():
    t = trades_frame([5.0, 6.0])
    m = compute_metrics(t, pd.DataFrame({"closed_equity": t["equity_after"], "mtm_equity": t["equity_after"]}), 1000)
    assert m["profit_factor"] is None and "profit_factor" in m["unavailable"]


def test_results_by_period():
    t = trades_frame([1.0, -2.0, 3.0])
    by_day = results_by_period(t, "D")
    assert by_day["trades"].tolist() == [1, 1, 1] and by_day["net_pnl"].tolist() == [1.0, -2.0, 3.0]
    assert results_by_period(t.iloc[0:0], "M").empty


def test_catalog_roundtrip_and_tamper_detection(lab_dir):
    cat = LabCatalog()
    ds = synthetic_dataset(days=3)
    cat.save_dataset(ds)
    loaded = cat.load_dataset(ds.meta.dataset_id)
    assert loaded.meta == ds.meta
    spec = load_catalog().specs["baseline.ema_trend_3bars@1.0.0"]
    a = run_backtest(ds, spec, BacktestConfig())
    b = run_backtest(loaded, spec, BacktestConfig())
    assert a.manifest["result_hash"] == b.manifest["result_hash"]
    run_id = cat.save_run(a, label="test")
    back = cat.load_run(run_id)
    assert back.manifest["result_hash"] == a.manifest["result_hash"] and len(back.trades) == len(a.trades)
    assert cat.list_runs().iloc[0]["run_id"] == run_id
    cat.set_setting("k", {"x": 1})
    assert cat.get_setting("k") == {"x": 1}
    path = lab_dir / "datasets" / f"{ds.meta.dataset_id}.csv.gz"
    df = pd.read_csv(path)
    df.loc[5, "close"] += 1
    df.to_csv(path, index=False, compression="gzip")
    with pytest.raises(ValueError, match="altéré"):
        cat.load_dataset(ds.meta.dataset_id)


def test_no_broker_order_path_in_sources():
    forbidden = re.compile(r"order_send|import\s+MetaTrader5|from\s+MetaTrader5|mt5\.initialize|mt5\.login",
                           re.IGNORECASE)
    hits = [str(p) for p in PKG.rglob("*.py") if p.name != "core.py" and forbidden.search(p.read_text())]
    assert hits == []
    assert LIVE_TRADING_ENABLED is False and DEMO_TRADING_ENABLED is False


def test_non_simulation_adapters_refuse():
    intent = OrderIntent("XAUUSD", 1, 0.01, 3800.0, None, "x@1.0.0", 1)
    for adapter in (DemoAccountAdapter(), LiveAccountAdapter()):
        with pytest.raises(ExecutionDisabledError):
            adapter.submit(intent)
    sim = SimulationAdapter()
    assert sim.submit(intent) == "SIM-1" and sim.journal == [intent]


def test_walk_forward_has_no_overlap_or_leak():
    start, end = pd.Timestamp("2026-01-01", tz="UTC"), pd.Timestamp("2026-07-01", tz="UTC")
    splits = walk_forward_splits(start, end, pd.Timedelta(days=60), pd.Timedelta(days=20), pd.Timedelta(days=1))
    assert len(splits) >= 5
    for s in splits:
        assert s.train_start < s.train_end <= s.test_start - pd.Timedelta(days=1) < s.test_end <= end
    for a, b in zip(splits, splits[1:], strict=False):
        assert a.test_end <= b.test_start
    anchored = walk_forward_splits(start, end, pd.Timedelta(days=60), pd.Timedelta(days=20), anchored=True)
    assert all(s.train_start == start for s in anchored)
    cs = chronological_split(start, end, 0.7, pd.Timedelta(days=2))
    assert cs.train_end < cs.test_start
