"""v0.4.1 — reproduction tests of the Codex V0.3.1 counter-audit findings that were still open (N1–N8).

Written before the fixes and run first against the frozen v0.4.0 sources (see VALIDATION_V041.md §5).
N9 (engine exit_time = bar open) is handled on the consumer side (labels.available_time, tested in
test_v041_research_safety.py); N10 (Express mutations) is tested in server/localGuard.spec.ts.
"""

from __future__ import annotations

import json
import sqlite3

import pandas as pd
import pytest

from ai_trader_optimizer.ai.validation import chronological_split, walk_forward_splits
from ai_trader_optimizer.backtest.engine import run_backtest
from ai_trader_optimizer.data.synthetic import synthetic_dataset, synthetic_m1_frame
from ai_trader_optimizer.data.validation import import_csv
from ai_trader_optimizer.services import default_config, run_and_store
from ai_trader_optimizer.storage import LabCatalog
from ai_trader_optimizer.storage import integrity as integ
from ai_trader_optimizer.strategies import load_catalog

from conftest import LocalClient

BASELINE = "baseline.ema_trend_3bars@1.0.0"


@pytest.fixture
def lab(tmp_path):
    return LabCatalog(tmp_path / "lab")


@pytest.fixture
def spec():
    return load_catalog().specs[BASELINE]


def _run(lab, spec):
    ds = synthetic_dataset(42, 10)
    lab.save_dataset(ds)
    return run_and_store(lab, ds.meta.dataset_id, spec, default_config(lab))


# ------------------------------------------------------------------ N1 (blocking): the collection is verified
def test_n1_a_forged_sqlite_metric_is_never_served_by_the_collection(lab, spec):
    res = _run(lab, spec)
    with sqlite3.connect(lab.root / "lab.db") as con:
        m = json.loads(con.execute("SELECT metrics_json FROM runs WHERE run_id=?", (res.run_id,)).fetchone()[0])
        m["net_pnl"] = 987654321
        con.execute("UPDATE runs SET metrics_json=? WHERE run_id=?", (json.dumps(m), res.run_id))
    listed = lab.list_runs()
    assert 987654321 not in listed["net_pnl"].tolist()
    assert listed.loc[listed["run_id"] == res.run_id, "net_pnl"].iloc[0] == pytest.approx(res.metrics["net_pnl"])


def test_n1_a_run_with_a_corrupted_artifact_is_listed_as_refused_without_figures(lab, spec):
    res = _run(lab, spec)
    trades = lab.root / "runs" / res.run_id / "trades.csv"
    trades.chmod(0o644)
    trades.write_bytes(trades.read_bytes().replace(b"BUY", b"SELL", 1))
    row = lab.list_runs().set_index("run_id").loc[res.run_id]
    assert row["integrity"] != "vérifiée"
    assert pd.isna(row["net_pnl"])


# ------------------------------------------------------------------ N2: per-trade economics are re-derived
def test_n2_an_exit_price_inconsistent_with_the_pnl_is_detected(lab, spec):
    res = run_backtest(synthetic_dataset(42, 10), spec, default_config(lab))
    trades = res.trades.copy()
    assert len(trades)
    trades.loc[trades.index[0], "exit_price"] += 100
    problems = integ.check_consistency(trades, res.decisions, res.equity, res.metrics, res.manifest)
    assert problems, "a P&L that does not follow from the prices was accepted"


# ------------------------------------------------------------------ N3: split helpers keep their invariant
def test_n3_negative_embargo_is_refused():
    a, b = pd.Timestamp("2026-01-01 12:00", tz="UTC"), pd.Timestamp("2026-01-01 12:10", tz="UTC")
    with pytest.raises(ValueError):
        chronological_split(a, b, 0.5, embargo=pd.Timedelta(minutes=-1))
    with pytest.raises(ValueError):
        walk_forward_splits(a, b + pd.Timedelta(hours=1), pd.Timedelta(minutes=10), pd.Timedelta(minutes=5),
                            embargo=pd.Timedelta(minutes=-1))


# ------------------------------------------------------------------ N4: row limit counts records like the parser
def test_n4_carriage_return_files_cannot_bypass_the_row_limit(lab_dir, monkeypatch):
    from ai_trader_optimizer.api import create_app
    monkeypatch.setenv("ATO_MAX_ROWS", "10")
    client = LocalClient(create_app(LabCatalog(lab_dir)))
    f = synthetic_m1_frame(seed=1, days=1).head(30).copy()
    f["timestamp"] = f["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    body = f.to_csv(index=False, lineterminator="\r").encode()
    r = client.post("/api/v1/datasets/import", files={"file": ("xau.csv", body, "text/csv")},
                    data={"name": "cr", "symbol": "XAUUSD", "source": "probe", "kind": "historical"})
    assert r.status_code == 413, r.text


# ------------------------------------------------------------------ N5: the policy attestation is per request
def test_n5_a_supervised_request_is_attested_even_when_the_run_already_exists(lab_dir, monkeypatch):
    from ai_trader_optimizer.api import create_app
    c = LabCatalog(lab_dir)
    ds = synthetic_dataset(42, 10)
    c.save_dataset(ds)
    client = LocalClient(create_app(c))
    body = {"dataset_id": ds.meta.dataset_id, "strategy_key": BASELINE}
    first = client.post("/api/v1/backtests", json=body).json()
    assert first["manifest"]["risk_policy"]["mode"] == "research"
    monkeypatch.setenv("ATO_RISK_POLICY", "supervised")
    again = client.post("/api/v1/backtests", json=body)
    assert again.status_code == 201
    assert again.json()["request_policy"]["mode"] == "supervised"
    assert "coûts" in again.json()["request_policy"]["scope"]


# ------------------------------------------------------------------ N6: validation code is fingerprinted
def test_n6_published_runs_record_a_validation_fingerprint_covering_storage(lab, spec):
    from ai_trader_optimizer.backtest import codehash
    res = _run(lab, spec)
    integrity = json.loads((lab.root / "runs" / res.run_id / "integrity.json").read_bytes())
    assert integrity.get("validation_fingerprint") == codehash.validation_fingerprint()
    covered = codehash.validation_paths()
    assert any(p.startswith("storage/") for p in covered) and "numeric.py" in covered and "services.py" in covered


# ------------------------------------------------------------------ N7: raw evidence must match its declared SHA
def test_n7_raw_bytes_that_do_not_match_the_declared_sha_are_refused(lab):
    f = synthetic_m1_frame(seed=2, days=2)
    f["timestamp"] = f["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    raw = f.to_csv(index=False).encode()
    _, ds = import_csv(raw, name="n7", symbol="XAUUSD", source_label="probe")
    assert ds is not None and ds.meta.raw_sha256
    with pytest.raises(ValueError):
        lab.save_dataset(ds, b"wrong raw bytes")


# ------------------------------------------------------------------ N8: the import response is what was persisted
def test_n8_second_import_returns_the_persisted_provenance(lab_dir):
    from ai_trader_optimizer.api import create_app
    client = LocalClient(create_app(LabCatalog(lab_dir)))
    f = synthetic_m1_frame(seed=4, days=2)
    f["timestamp"] = f["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    raw = f.to_csv(index=False).encode()
    form = {"name": "first", "symbol": "XAUUSD", "kind": "historical"}
    a = client.post("/api/v1/datasets/import", files={"file": ("x.csv", raw, "text/csv")}, data={**form, "source": "probe"})
    b = client.post("/api/v1/datasets/import", files={"file": ("x.csv", raw, "text/csv")},
                    data={**form, "name": "second", "source": "new source"})
    assert a.status_code == b.status_code == 201
    stored = client.get(f"/api/v1/datasets/{b.json()['dataset']['dataset_id']}").json()
    assert b.json()["dataset"]["source"] == stored["source"] == "probe"
    assert b.json()["dataset"]["name"] == stored["name"] == "first"
    assert b.json()["declaration"]["source"] == "new source"
