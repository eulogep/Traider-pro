"""Pre-compute the read-only SHOWCASE of the platform (static site, no server).

Runs the REAL FastAPI app on a temporary lab (nothing of the owner's data is read or written), creates:
  * a SYNTHETIC demo dataset (labelled as such) + a backtest of the illustrative baseline + its robustness,
  * an out-of-sample edge study (experimental method) on that synthetic data,
  * the import of the REAL MT5 Strategy Tester report of « Gold Grid Strategy V3.70 EA » (HTML + XLSX fixtures),
then saves every GET response the React client asks for as a static JSON file, with the same naming rule as
``showcaseFile()`` in ``client/lib/quantApi.ts``. Nothing here sends an order or contacts a broker.

    cd quant && .venv/bin/python scripts/export_showcase.py ../showcase/data
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE.parent / "tests" / "fixtures" / "mt5"
CHARS = {"/": "__", "?": "--", "&": "_", "=": "-"}
EXPORT_NAMES = ["trades.csv", "decisions.csv", "equity.csv.gz", "metrics.json", "manifest.json"]


def showcase_file(path: str) -> str:
    """Must stay identical to showcaseFile() in client/lib/quantApi.ts."""
    return re.sub(r"[/?&=]", lambda m: CHARS[m.group(0)], path.lstrip("/")) + ".json"


def main(out_dir: str) -> None:
    out = Path(out_dir).resolve()
    tmp = Path(tempfile.mkdtemp(prefix="ato-showcase-"))
    os.environ["ATO_DATA_DIR"] = str(tmp / "lab")
    os.environ["ATO_MT5_DIR"] = str(tmp / "no-mt5-terminal")  # never read the owner's MT5 folder
    from fastapi.testclient import TestClient

    from ai_trader_optimizer.api.app import create_app
    from ai_trader_optimizer.external_lab.whatif import RULES
    from ai_trader_optimizer.storage import LabCatalog

    client = TestClient(create_app(LabCatalog()), base_url="http://localhost", headers={"X-ATO-Request": "1"})

    def post(path: str, **kw) -> dict:
        r = client.post(f"/api/v1{path}", **kw)
        if r.status_code >= 300:
            raise SystemExit(f"POST {path} → {r.status_code} {r.text[:300]}")
        return r.json()

    # ---- compute (real engine, temporary lab)
    ds = post("/datasets/demo", json={"seed": 42, "days": 60})["dataset"]
    strategies = client.get("/api/v1/strategies").json()["strategies"]
    strategy = next(s for s in strategies if s["runnable"])
    run = post("/backtests", json={"dataset_id": ds["dataset_id"], "strategy_key": strategy["key"]})
    study = post("/research/edge-studies", json={"dataset_id": ds["dataset_id"], "strategy_key": strategy["key"]})
    sims = []
    for name in ("Gold_Grid_V370_MT5_Baseline_2026.html", "Gold_Grid_V370_MT5_Baseline_2026.xlsx"):
        raw = (FIXTURES / name).read_bytes()
        sims.append(post("/external-sims", files={"file": (name, raw, "application/octet-stream")})["sim_id"])

    run_id, study_id = run["run_id"], study["study_id"]
    gets = ["/health", "/datasets", f"/datasets/{ds['dataset_id']}", "/strategies", "/settings/defaults",
            "/settings/risk-policy", "/reference/rejection-reasons", "/backtests", f"/backtests/{run_id}",
            f"/backtests/{run_id}/trades",  # (the decision log is not read by the UI: downloadable as decisions.csv)
            f"/backtests/{run_id}/equity?max_points=1500", f"/backtests/{run_id}/equity?max_points=400",
            f"/backtests/{run_id}/robustness", "/research/edge-studies", f"/research/edge-studies/{study_id}",
            "/mt5/local-files", "/external-sims", "/external-sims/what-if-rules"]
    gets += [f"/external-sims/{s}" for s in sims]
    gets += [f"/external-sims/{s}/what-if?rule={rule}" for s in sims for rule in RULES]

    # ---- write (replace only the generated folder)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    files = {}
    for path in gets:
        r = client.get(f"/api/v1{path}")
        if r.status_code != 200:
            raise SystemExit(f"GET {path} → {r.status_code} {r.text[:300]}")
        body = r.json()
        if path == "/mt5/local-files":
            body = {"available": False, "root": None, "files": [],
                    "note": "Vitrine : aucun terminal MT5 n'est relié au site public."}
        data = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
        (out / showcase_file(path)).write_bytes(data)
        files[showcase_file(path)] = hashlib.sha256(data).hexdigest()
    exp = out / "exports" / run_id
    exp.mkdir(parents=True)
    for name in EXPORT_NAMES:
        r = client.get(f"/api/v1/backtests/{run_id}/export/{name}")
        if r.status_code != 200:
            raise SystemExit(f"export {name} → {r.status_code}")
        (exp / name).write_bytes(r.content)
    health = client.get("/api/v1/health").json()
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "software_version": health["software_version"], "engine_version": health["engine_version"],
        "code_hash": health["code_hash"], "execution_mode": health["execution_mode"],
        "content": {"synthetic_dataset": ds["dataset_id"], "backtest": run_id, "edge_study": study_id,
                    "external_simulations": sims},
        "mt5_reference_sha256": {n: hashlib.sha256((FIXTURES / n).read_bytes()).hexdigest()
                                 for n in ("Gold_Grid_V370_MT5_Baseline_2026.html", "Gold_Grid_V370_MT5_Baseline_2026.xlsx")},
        "files_sha256": files,
        "note": "Réponses de l'API pré-calculées par le moteur Python ; vitrine en lecture seule, aucun ordre.",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    shutil.rmtree(tmp, ignore_errors=True)
    total = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"{len(files)} réponses + {len(EXPORT_NAMES)} exports → {out} ({total / 1024:.0f} Ko)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(HERE.parent.parent / "showcase" / "data"))
