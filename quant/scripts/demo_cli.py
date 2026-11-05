"""Command-line backtest on FAKE (synthetic) prices — smoke test of the whole pipeline.

Usage: python scripts/demo_cli.py [--legacy-rules] [--days 10] [--seed 42]
"""

import argparse
import json

from ai_trader_optimizer.backtest import BacktestConfig, run_backtest
from ai_trader_optimizer.data import synthetic_dataset
from ai_trader_optimizer.risk import LEGACY_V01_RISK, RiskConfig
from ai_trader_optimizer.strategies import load_catalog

KEYS = ("trades", "net_pnl", "win_rate_pct", "profit_factor", "expectancy", "expectancy_r", "max_dd_closed_pct",
        "max_dd_mtm_pct", "total_costs", "signals", "signals_entered", "rejection_reasons")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--legacy-rules", action="store_true", help="explicit v0.1 risk rules")
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    ds = synthetic_dataset(seed=a.seed, days=a.days)
    spec = load_catalog().specs["baseline.ema_trend_3bars@1.0.0"]
    res = run_backtest(ds, spec, BacktestConfig(risk=LEGACY_V01_RISK if a.legacy_rules else RiskConfig()))
    print("DEMONSTRATION AVEC DONNEES SYNTHETIQUES : aucune performance de marche reelle")
    print(f"run_id={res.run_id} result_hash={res.manifest['result_hash']} dataset={ds.meta.dataset_id}")
    print(json.dumps({k: res.metrics.get(k) for k in KEYS}, indent=2, default=str, ensure_ascii=False))
