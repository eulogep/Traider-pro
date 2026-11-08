#!/usr/bin/env python3
"""Independent check: same strategy, same real bars, two engines (Python engine vs MT5 Strategy Tester).

    cd quant && .venv/bin/python ../mt5/compare_engines.py --model 1

Compares signals (same bar, same side), entries, then trade by trade (entry, exit, lots, net). Nothing is traded.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ai_trader_optimizer.backtest.engine import run_backtest
from ai_trader_optimizer.backtest.models import BacktestConfig, ExecutionCosts
from ai_trader_optimizer.data import import_csv
from ai_trader_optimizer.external_lab.mt5_report import read_members
from ai_trader_optimizer.external_lab.reconstruct import deal_metrics, reconstruct
from ai_trader_optimizer.safety import DataKind
from ai_trader_optimizer.strategies import load_catalog

RES = Path(__file__).resolve().parent / "results"


def load_bars(tag: str):
    raw = (RES / f"export_{tag}.csv").read_bytes()
    _, ds = import_csv(raw, name=f"XAUUSD M1 MetaQuotes-Demo ({tag})", symbol="XAUUSD",
                       source_label="Strategy Tester MT5, serveur MetaQuotes-Demo (export ATO_ExportBars)", price_side="bid",
                       source_timezone="Europe/Athens", expected_timeframe="M1", kind=DataKind.HISTORICAL,
                       notes="Fuseau du serveur mesuré sur la pause quotidienne (voir mt5/README.md).")
    return ds


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=int, default=1)
    ap.add_argument("--tag", default="XAUUSD_M1_20260101_20261031")
    a = ap.parse_args()
    name = f"baseline_{a.tag}_model{a.model}"
    ds = load_bars(a.tag)
    spec = next(s for s in load_catalog().specs.values() if s.key.startswith("baseline."))

    mt = pd.read_csv(RES / f"{name}_decisions.csv")
    mt["t"] = pd.to_datetime(mt["signal_bar_utc"], format="%Y.%m.%d %H:%M:%S", utc=True)
    entered = mt[mt["outcome"] == "ENTERED"]
    mean_spread = float(entered["spread"].mean())
    rep = max(read_members(f"{name}.htm", (RES / f"{name}.htm").read_bytes())[0], key=lambda r: len(r.deals))
    m5 = deal_metrics(rep.deals)
    tr5 = pd.DataFrame(reconstruct(rep.deals, 100.0)["trades"])

    out = {"model": a.model, "bars": int(ds.meta.rows), "dataset_id": ds.meta.dataset_id,
           "mt5": {k: m5[k] for k in ("net_profit", "total_trades", "profit_trades_pct", "profit_factor", "balance_dd_maximal",
                                      "balance_dd_maximal_pct", "final_balance", "gross_profit", "gross_loss")},
           "mt5_mean_spread_at_entry": mean_spread, "mt5_median_spread_at_entry": float(entered["spread"].median())}

    configs = {"couts_mt5": ExecutionCosts(spread=round(mean_spread, 4), slippage=0.0, commission_per_lot_per_side=0.0),
               "couts_prudents": ExecutionCosts()}
    for label, costs in configs.items():
        r = run_backtest(ds, spec, BacktestConfig(costs=costs))
        met = r.metrics
        rec = {"costs": costs.model_dump(), "net_pnl": met["net_pnl"], "trades": met["trades"], "win_rate_pct": met["win_rate_pct"],
               "profit_factor": met.get("profit_factor"), "max_dd_closed_pct": met["max_dd_closed_pct"], "expectancy_r": met["expectancy_r"],
               "final_equity": met["final_equity"], "rejections": met["rejection_reasons"], "run_id": r.run_id}
        if label == "couts_mt5":
            sig = r.signals.assign(t=pd.to_datetime(ds.bars["timestamp"].to_numpy(), utc=True))
            sig = sig[sig["signal"] != 0]
            py = dict(zip(sig["t"], sig["signal"], strict=True))
            mts = dict(zip(mt["t"], np.where(mt["direction"] == "BUY", 1, -1), strict=True))
            both = set(py) & set(mts)
            same = sum(py[k] == mts[k] for k in both)
            common_start = max(min(py), min(mts))
            only_py = [k for k in py if k not in mts and k >= common_start]
            only_mt = [k for k in mts if k not in py and k >= common_start]
            rec["signals"] = {"python": len(py), "mt5": len(mts), "common": len(both), "same_direction": int(same),
                              "only_python": len(only_py), "only_mt5": len(only_mt),
                              "examples_only_python": [str(x) for x in sorted(only_py)[:5]],
                              "examples_only_mt5": [str(x) for x in sorted(only_mt)[:5]]}
            tp = r.trades.copy()
            tp["k"] = pd.to_datetime(tp["signal_time"], utc=True)
            t5 = entered.assign(k=entered["t"]).reset_index(drop=True)
            common = sorted(set(tp["k"]) & set(t5["k"]))
            rec["entries"] = {"python": len(tp), "mt5": len(t5), "same_signal_bar": len(common),
                              "only_python": len(set(tp["k"]) - set(t5["k"])), "only_mt5": len(set(t5["k"]) - set(tp["k"]))}
            # trade by trade, on entries present in both engines
            tr5 = tr5.sort_values("entry_seq").reset_index(drop=True)
            t5["net"] = tr5["net"].to_numpy()[: len(t5)] if len(tr5) >= len(t5) else np.nan
            t5["exit_reason5"] = tr5["close_reason"].to_numpy()[: len(t5)] if len(tr5) >= len(t5) else None
            j = tp.merge(t5, on="k", suffixes=("_py", "_mt"))
            same_sign = (np.sign(j["net_pnl"]) == np.sign(j["net"]))
            rec["trade_by_trade"] = {"compared": len(j), "same_outcome_sign": int(same_sign.sum()),
                                     "net_python_on_common": float(j["net_pnl"].sum()), "net_mt5_on_common": float(j["net"].sum()),
                                     "median_abs_net_diff": float((j["net_pnl"] - j["net"]).abs().median())}
        out[label] = rec
    path = RES / f"comparison_model{a.model}.json"
    path.write_text(json.dumps(out, indent=1, default=str, ensure_ascii=False))
    print(json.dumps(out, indent=1, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
