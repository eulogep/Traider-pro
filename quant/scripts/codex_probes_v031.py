"""Codex V0.3 adversarial probes, adapted to the V0.3.1 interfaces (same intent, same attacks).

Original probes: docs/audits/codex-v03-2026-11-04/probes.py. Each probe prints the observed
behaviour and PASS (defect no longer reproducible) or FAIL. Uses only temporary catalogs.
Usage (from quant/):  .venv/bin/python scripts/codex_probes_v031.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tests"))
os.environ["ATO_DATA_DIR"] = tempfile.mkdtemp(prefix="ato-probes-")

import pandas as pd  # noqa: E402

from ai_trader_optimizer.ai.validation import chronological_split  # noqa: E402
from ai_trader_optimizer.api.app import create_app  # noqa: E402
from ai_trader_optimizer.backtest import BacktestConfig, run_backtest  # noqa: E402
from ai_trader_optimizer.data import dataset_from_frame, fingerprint, synthetic_dataset  # noqa: E402
from ai_trader_optimizer.risk import RiskConfig  # noqa: E402
from ai_trader_optimizer.safety import DataKind  # noqa: E402
from ai_trader_optimizer.services import save_risk  # noqa: E402
from ai_trader_optimizer.storage import CorruptRunError, LabCatalog, ReproducibilityError  # noqa: E402
from ai_trader_optimizer.strategies import load_catalog  # noqa: E402

from conftest import LocalClient, base_config, flat_bar, make_bars, make_dataset, scripted  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def probe(defect: str, ok: bool, observed) -> None:
    RESULTS.append((defect, ok, json.dumps(observed, default=str, ensure_ascii=False)[:180]))


cat = LabCatalog()
client = LocalClient(create_app(cat), raise_server_exceptions=False)
spec = load_catalog().specs["baseline.ema_trend_3bars@1.0.0"]
ds = synthetic_dataset(days=3)
cat.save_dataset(ds)
r = run_backtest(ds, spec, BacktestConfig())
cat.save_run(r)

# B1 — data package ignored by Git
repo = HERE.parent
ignored = subprocess.run(["git", "check-ignore", "-v", "quant/src/ai_trader_optimizer/data/__init__.py"],
                         cwd=repo, capture_output=True, text=True).stdout.strip()
probe("B1", ignored == "", {"check_ignore": ignored or "not ignored"})

# B2 — tampered metrics must not be served nor "reproduced identical"
p = cat.run_dir(r.run_id) / "metrics.json"
original = p.read_bytes()
m = json.loads(original)
m["net_pnl"] = 987654321
p.write_text(json.dumps(m))
got, rep = client.get(f"/api/v1/backtests/{r.run_id}"), client.post(f"/api/v1/backtests/{r.run_id}/reproduce")
probe("B2", got.status_code == 409 and rep.status_code == 409 and "987654321" not in got.text,
      {"get": got.status_code, "reproduce": rep.status_code})
p.write_bytes(original)
r.equity.loc[:, "mtm_equity"] = 1
r.metrics["net_pnl"] = 123456
try:
    cat.save_run(r)
    probe("B2-overwrite", False, {"accepted": True})
except (ReproducibilityError, CorruptRunError) as exc:
    probe("B2-overwrite", True, {"refused": type(exc).__name__})

# B3 — same bar in IS and OOS
bars = [flat_bar()] * 11
bars[5] = (100, 104, 99.8, 103)
d = make_dataset(bars)
sp, st = scripted({4: (1, 2, 3)})
cut = chronological_split(d.bars.timestamp.iloc[0], d.bars.timestamp.iloc[-1], 0.5)
seg = {name: run_backtest(d, sp, cfg, strategy=st).trades for name, cfg in
       [("IS", base_config(trade_end=cut.train_end.isoformat())),
        ("OOS", base_config(trade_start=cut.test_start.isoformat()))]}
probe("B3", len(seg["IS"]) + len(seg["OOS"]) == 1, {k: len(v) for k, v in seg.items()} | {"cut": cut.train_end})

# I1 — infinity through standard JSON
payload = json.dumps({"dataset_id": ds.meta.dataset_id, "strategy_key": spec.key,
                      "config": {"initial_equity": "R"}}).replace('"R"', "1e309")
resp = client.post("/api/v1/backtests", content=payload, headers={"Content-Type": "application/json"})
probe("I1", resp.status_code == 422, {"status": resp.status_code})

# I2 — saved profile loosened by the caller: explicit research mode, enforced in supervised mode
save_risk(cat, RiskConfig(max_trades_per_day=1))
loose = BacktestConfig(risk=RiskConfig(max_trades_per_day=100, max_losses_per_day=None, max_daily_loss_pct=100,
                                       max_drawdown_pct=100)).model_dump(mode="json")
res_mode = client.post("/api/v1/backtests", json={"dataset_id": ds.meta.dataset_id, "strategy_key": spec.key,
                                                  "config": loose}).json()["manifest"]["risk_policy"]
os.environ["ATO_RISK_POLICY"] = "supervised"
sup = LocalClient(create_app(cat)).post("/api/v1/backtests", json={"dataset_id": ds.meta.dataset_id,
                                                                    "strategy_key": spec.key, "config": loose})
os.environ.pop("ATO_RISK_POLICY")
probe("I2", res_mode["enforced"] is False and res_mode["mode"] == "research" and sup.status_code == 403,
      {"research": res_mode["mode"], "supervised_status": sup.status_code})

# I3 — bytes received before the size check
import ai_trader_optimizer.api.security as sec  # noqa: E402

seen = {"bytes": 0}
os.environ["ATO_MAX_UPLOAD_MB"] = str(1024 / (1024 * 1024))
app = create_app(cat)


async def observed(scope, receive, send):
    async def recv():
        msg = await receive()
        seen["bytes"] += len(msg.get("body", b""))
        return msg
    await app(scope, recv, send)
big = LocalClient(observed).post("/api/v1/datasets/import", files={"file": ("big.csv", b"x" * (2 * 1024 * 1024))},
                                  data={"name": "t", "symbol": "XAUUSD", "source": "t", "kind": "historical"})
os.environ.pop("ATO_MAX_UPLOAD_MB")
probe("I3", big.status_code == 413 and seen["bytes"] <= sec.max_upload_bytes(),
      {"status": big.status_code, "received_before_refusal": seen["bytes"]})

# I4 — foreign-origin write
raw = ds.bars.copy()
raw["timestamp"] = raw["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
raw = raw.to_csv(index=False).encode()
n0 = len(cat.list_datasets())
evil = LocalClient(create_app(cat)).post("/api/v1/datasets/import", headers={"Origin": "https://evil.example"},
                                         files={"file": ("neutral.csv", raw)},
                                         data={"name": "x", "symbol": "XAUUSD", "source": "t", "kind": "synthetic"})
probe("I4", evil.status_code == 403 and len(cat.list_datasets()) == n0, {"status": evil.status_code})

# I5 — lowercase import then load
low = client.post("/api/v1/datasets/import", files={"file": ("prices.csv", raw)},
                  data={"name": "lc", "symbol": "xauusd", "source": "t", "kind": "synthetic"})
err = None
try:
    cat.load_dataset(low.json()["dataset"]["dataset_id"])
except Exception as exc:
    err = str(exc)
probe("I5", low.status_code == 201 and err is None, {"status": low.status_code, "load_error": err})

# I6 — sub-second truncation and price-precision collision
frame = make_bars([flat_bar()] * 3)
frame["timestamp"] += pd.Timedelta(milliseconds=500)
try:
    dataset_from_frame(frame, name="f", symbol="XAUUSD", source_label="t", kind=DataKind.SYNTHETIC)
    sub = "accepted"
except ValueError:
    sub = "refused"
f = make_bars([flat_bar()] * 3)
f2 = f.copy()
f2.loc[0, "close"] += 1e-8
coll = fingerprint(f, "XAUUSD", "M1", "bid") == fingerprint(f2, "XAUUSD", "M1", "bid")
probe("I6", sub == "refused" and not coll, {"fractional": sub, "collision": coll})

# I7 — same bytes, contradictory provenance
kinds = [client.post("/api/v1/datasets/import", files={"file": ("neutral.csv", raw)},
                     data={"name": "n", "symbol": "XAUUSD", "source": k, "kind": k}).status_code
         for k in ("synthetic", "historical")]
probe("I7", kinds[1] == 409, {"synthetic": kinds[0], "historical": kinds[1]})

# I8 — open already beyond TP, low later touches SL
sp, st = scripted({0: (1, 2, 3)})
g = run_backtest(make_dataset([flat_bar(), flat_bar(), (105, 106, 97, 99), flat_bar(99)]), sp, base_config(),
                 strategy=st).trades.iloc[0]
probe("I8", g["exit_reason"] == "TP_GAP" and abs(g["net_pnl"] - 31.79) < 1e-9,
      {"exit": g["exit_reason"], "net_pnl": round(g["net_pnl"], 2)})

# M3 — invalid time zone
cfg = BacktestConfig().model_dump(mode="json")
cfg["risk"]["day_timezone"] = "Not/AZone"
bad = client.post("/api/v1/backtests", json={"dataset_id": ds.meta.dataset_id, "strategy_key": spec.key,
                                             "config": cfg})
probe("M3", bad.status_code == 422, {"status": bad.status_code})

# M4 — excursions after exit
sp, st = scripted({0: (1, 2, 3)})
e = run_backtest(make_dataset([flat_bar(), (100, 1000, 98, 100), flat_bar()]), sp, base_config(),
                 strategy=st).trades.iloc[0]
probe("M4", e["mfe_r"] == 0.0 and e["excursion_basis"] == "lower_bound_ohlc",
      {"mfe_r": e["mfe_r"], "basis": e["excursion_basis"]})

width = max(len(d) for d, _, _ in RESULTS)
for defect, ok, obs in RESULTS:
    print(f"{'PASS' if ok else 'FAIL'}  {defect:<{width}}  {obs}")
failed = sum(not ok for _, ok, _ in RESULTS)
print(f"\n{len(RESULTS) - failed}/{len(RESULTS)} probes: defect no longer reproducible")
sys.exit(1 if failed else 0)
