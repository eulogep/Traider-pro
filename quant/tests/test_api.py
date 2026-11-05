"""HTTP API v1: it only exposes the engine (no own maths), validates inputs, never orders."""

import io

import pandas as pd
import pytest

from ai_trader_optimizer.api import create_app
from ai_trader_optimizer.backtest import BacktestConfig, run_backtest
from ai_trader_optimizer.storage import LabCatalog
from ai_trader_optimizer.strategies import load_catalog

from conftest import LocalClient, flat_bar, make_bars

BASELINE = "baseline.ema_trend_3bars@1.0.0"
ALLOWED_ROUTES = {
    ("GET", "/api/v1/health"), ("GET", "/api/v1/datasets"), ("GET", "/api/v1/datasets/{dataset_id}"),
    ("POST", "/api/v1/datasets/demo"), ("POST", "/api/v1/datasets/import"), ("GET", "/api/v1/strategies"),
    ("GET", "/api/v1/settings/defaults"), ("GET", "/api/v1/settings/risk-policy"),
    ("GET", "/api/v1/reference/rejection-reasons"),
    ("POST", "/api/v1/backtests"), ("GET", "/api/v1/backtests"), ("GET", "/api/v1/backtests/{run_id}"),
    ("GET", "/api/v1/backtests/{run_id}/trades"), ("GET", "/api/v1/backtests/{run_id}/decisions"),
    ("GET", "/api/v1/backtests/{run_id}/equity"), ("POST", "/api/v1/backtests/{run_id}/reproduce"),
    ("GET", "/api/v1/backtests/{run_id}/export/{name}"), ("GET", "/api/v1/backtests/{run_id}/robustness"),
    # research layer (v0.4): evidence only — studies are read-only computations, no order, no position
    ("POST", "/api/v1/research/edge-studies"), ("GET", "/api/v1/research/edge-studies"),
    ("GET", "/api/v1/research/edge-studies/{study_id}"),
    ("POST", "/api/v1/ea-reports/analyze"),
    ("GET", "/api/v1/mt5/local-files"), ("POST", "/api/v1/mt5/local-files/{file_id}/analyze"),
    # external bot lab (v0.5): imported MT5 simulations as data — no execution, no broker
    ("POST", "/api/v1/external-sims"), ("POST", "/api/v1/external-sims/from-mt5/{file_id}"),
    ("GET", "/api/v1/external-sims"), ("GET", "/api/v1/external-sims/what-if-rules"),
    ("GET", "/api/v1/external-sims/{sim_id}"), ("GET", "/api/v1/external-sims/{sim_id}/what-if"),
}


@pytest.fixture
def client(lab_dir):
    return LocalClient(create_app(LabCatalog()))


@pytest.fixture
def demo(client):
    r = client.post("/api/v1/datasets/demo", json={"seed": 42, "days": 10})
    assert r.status_code == 201, r.text
    return r.json()["dataset"]


def run(client, dataset_id, config=None, **kw):
    body = {"dataset_id": dataset_id, "strategy_key": BASELINE, **kw}
    if config is not None:
        body["config"] = config
    return client.post("/api/v1/backtests", json=body)


def csv_upload(df: pd.DataFrame, name="xau.csv"):
    out = df.copy()
    out["timestamp"] = out["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"file": (name, out.to_csv(index=False).encode(), "text/csv")}


FORM = {"name": "XAU test", "symbol": "XAUUSD", "source": "unit-test broker", "kind": "historical"}


# ---------------------------------------------------------------- safety
def test_health_reports_simulation_only(client):
    h = client.get("/api/v1/health").json()
    assert h["execution_mode"] == "simulation" and h["live_trading_enabled"] is False
    assert h["demo_trading_enabled"] is False and h["order_routes"] == 0


def test_no_order_route_and_only_allowlisted_routes():
    app = create_app(LabCatalog.__new__(LabCatalog))
    exposed = {(m, r.path) for r in app.routes if hasattr(r, "methods") and r.path.startswith("/api/")
               for m in r.methods if m not in ("HEAD", "OPTIONS")}
    assert exposed == ALLOWED_ROUTES
    # Owner authorisation 2026-11-05: read-only access to the LOCAL MT5 terminal's files. Exactly these two routes
    # may mention mt5; every other mt5 route — and any order / execution / position / broker / login route — stays
    # forbidden.
    mt5_read_only = {("GET", "/api/v1/mt5/local-files"), ("POST", "/api/v1/mt5/local-files/{file_id}/analyze"),
                     ("POST", "/api/v1/external-sims/from-mt5/{file_id}")}
    for method, path in exposed:
        assert not any(w in path.lower() for w in ("order", "execute", "position", "broker", "login"))
        assert "mt5" not in path.lower() or (method, path) in mt5_read_only


def test_wildcard_cors_refused(monkeypatch):
    monkeypatch.setenv("ATO_CORS_ORIGINS", "*")
    with pytest.raises(RuntimeError):
        create_app()


def test_cors_only_for_listed_local_origins(client):
    ok = client.get("/api/v1/health", headers={"Origin": "http://localhost:8080"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:8080"
    bad = client.get("/api/v1/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in bad.headers


# ---------------------------------------------------------------- datasets
def test_demo_dataset_is_deterministic_and_labelled(client, demo):
    again = client.post("/api/v1/datasets/demo", json={"seed": 42, "days": 10}).json()["dataset"]
    assert again["dataset_id"] == demo["dataset_id"] and demo["kind"] == "synthetic"
    assert "synthétiques" in demo["name"]
    listed = client.get("/api/v1/datasets").json()
    assert [d["dataset_id"] for d in listed] == [demo["dataset_id"]]


def test_import_valid_csv(client):
    bars = make_bars([flat_bar(100 + i * 0.01) for i in range(600)])
    r = client.post("/api/v1/datasets/import", data=FORM, files=csv_upload(bars))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["dataset"]["kind"] == "historical" and body["dataset"]["rows"] == 600 and body["quality"]["ok"]


def test_invalid_csv_rejected_and_nothing_stored(client):
    bars = make_bars([flat_bar()] * 50)
    bars.loc[10, "timestamp"] = bars.loc[9, "timestamp"]  # duplicate
    r = client.post("/api/v1/datasets/import", data=FORM, files=csv_upload(bars))
    assert r.status_code == 422
    assert any(i["code"] == "DUPLICATED_TIMESTAMP" for i in r.json()["detail"]["issues"])
    assert client.get("/api/v1/datasets").json() == []


def test_synthetic_file_cannot_be_declared_historical(client):
    bars = make_bars([flat_bar()] * 50)
    r = client.post("/api/v1/datasets/import", data=FORM, files=csv_upload(bars, "SYNTHETIQUE_demo.csv"))
    assert r.status_code == 422


def test_upload_size_limit_and_extension(client, monkeypatch):
    monkeypatch.setenv("ATO_MAX_UPLOAD_MB", "0.001")  # ~1 KB
    bars = make_bars([flat_bar()] * 200)
    assert client.post("/api/v1/datasets/import", data=FORM, files=csv_upload(bars)).status_code == 413
    files = {"file": ("x.exe", b"timestamp,open\n", "application/octet-stream")}
    assert client.post("/api/v1/datasets/import", data=FORM, files=files).status_code == 415


def test_bad_form_fields_rejected(client):
    bars = make_bars([flat_bar()] * 50)
    bad = {**FORM, "symbol": "../etc"}
    assert client.post("/api/v1/datasets/import", data=bad, files=csv_upload(bars)).status_code == 422
    bad = {**FORM, "kind": "demo_account"}
    assert client.post("/api/v1/datasets/import", data=bad, files=csv_upload(bars)).status_code == 422


# ---------------------------------------------------------------- strategies & defaults
def test_strategies_listing(client):
    items = {s["key"]: s for s in client.get("/api/v1/strategies").json()["strategies"]}
    assert items[BASELINE]["runnable"] and items[BASELINE]["spec"]["illustrative"] is True
    assert not items["pilot.macd_m15_m1@0.1.0"]["runnable"]
    assert client.get("/api/v1/settings/defaults").json()["contract"]["contract_size"] == 100.0


# ---------------------------------------------------------------- backtests
def test_backtest_uses_the_engine_and_is_persisted(client, demo):
    r = run(client, demo["dataset_id"])
    assert r.status_code == 201, r.text
    body = r.json()
    direct = run_backtest(LabCatalog().load_dataset(demo["dataset_id"]), load_catalog().specs[BASELINE],
                          BacktestConfig())
    assert body["run_id"] == direct.run_id
    assert body["manifest"]["result_hash"] == direct.manifest["result_hash"]
    assert body["metrics"]["net_pnl"] == pytest.approx(direct.metrics["net_pnl"])
    assert body["manifest"]["data_kind"] == "synthetic"


def test_displayed_metrics_match_returned_trades_and_equity(client, demo):
    body = run(client, demo["dataset_id"]).json()
    rid, m = body["run_id"], body["metrics"]
    trades = client.get(f"/api/v1/backtests/{rid}/trades").json()
    eq = client.get(f"/api/v1/backtests/{rid}/equity?max_points=50").json()
    assert m["trades"] == len(trades) > 0
    assert m["net_pnl"] == pytest.approx(sum(t["net_pnl"] for t in trades))
    assert m["win_rate_pct"] == pytest.approx(100 * sum(t["net_pnl"] > 0 for t in trades) / len(trades))
    assert eq["points"][-1]["closed_equity"] == pytest.approx(m["final_equity"])
    assert len(eq["points"]) <= 52 and eq["total_points"] > 1000  # max_points + last + worst-drawdown point
    dec = client.get(f"/api/v1/backtests/{rid}/decisions").json()
    assert dec["total"] == m["signals"]
    entered = client.get(f"/api/v1/backtests/{rid}/decisions?outcome=ENTERED").json()["items"]
    assert {d["trade_id"] for d in entered} == {t["trade_id"] for t in trades}


def test_same_request_is_reproducible_and_idempotent(client, demo):
    a, b = run(client, demo["dataset_id"]).json(), run(client, demo["dataset_id"]).json()
    assert a["run_id"] == b["run_id"] and a["manifest"]["result_hash"] == b["manifest"]["result_hash"]
    rep = client.post(f"/api/v1/backtests/{a['run_id']}/reproduce").json()
    assert rep["identical"] is True and rep["stored_hash"] == rep["new_hash"]
    assert len(client.get("/api/v1/backtests").json()) == 1


def test_risk_rules_hold_on_api_results(client, demo):
    cfg = client.get("/api/v1/settings/defaults").json()
    cfg["risk"].update(risk_per_trade_pct=0.5, max_trades_per_day=1)
    cfg["strategy_params"] = {"rr": 1.0}
    body = run(client, demo["dataset_id"], cfg).json()
    trades = pd.DataFrame(client.get(f"/api/v1/backtests/{body['run_id']}/trades").json())
    assert len(trades) > 0
    equity_before = trades["equity_after"].shift(1, fill_value=cfg["initial_equity"])
    assert (trades["planned_risk"] <= equity_before * 0.005 + 1e-9).all()
    assert pd.to_datetime(trades["entry_time"]).dt.date.value_counts().max() == 1


@pytest.mark.parametrize("mutate,status", [
    (lambda c: c["strategy_params"].update(rr=99), 422),           # outside declared bounds
    (lambda c: c["strategy_params"].update(ema_fast=60), 422),     # ema_fast >= ema_slow
    (lambda c: c["strategy_params"].update(unknown=1), 422),       # undeclared parameter
    (lambda c: c["costs"].update(spread=-1), 422),                 # negative cost
    (lambda c: c.update(initial_equity=0), 422),
    (lambda c: c["risk"].update(risk_per_trade_pct=50), 422),      # > 5 % per trade
    (lambda c: c["risk"].update(allow_martingale=True), 422),
    (lambda c: c.update(leverage=100), 422),                       # extra field refused
])
def test_invalid_user_parameters_rejected(client, demo, mutate, status):
    cfg = client.get("/api/v1/settings/defaults").json()
    mutate(cfg)
    r = run(client, demo["dataset_id"], cfg)
    assert r.status_code == status, r.text
    assert "error" in r.json()
    assert client.get("/api/v1/backtests").json() == []  # no partial / fake result stored


def test_unknown_or_non_runnable_strategy_and_dataset(client, demo):
    r = client.post("/api/v1/backtests", json={"dataset_id": demo["dataset_id"], "strategy_key": "nope@1.0.0"})
    assert r.status_code == 404
    r = client.post("/api/v1/backtests", json={"dataset_id": demo["dataset_id"],
                                               "strategy_key": "pilot.macd_m15_m1@0.1.0"})
    assert r.status_code == 422 and "draft" in r.json()["error"]
    assert run(client, "0" * 16).status_code == 404
    assert run(client, "../../etc/passwd").status_code == 422


def test_unknown_contract_yields_zero_trades_not_fake_results(client, demo):
    cfg = client.get("/api/v1/settings/defaults").json()
    cfg["contract"]["contract_size"] = None
    body = run(client, demo["dataset_id"], cfg).json()
    assert body["metrics"]["trades"] == 0 and body["metrics"]["win_rate_pct"] is None
    assert "CONTRACT_UNKNOWN" in body["metrics"]["rejection_reasons"]


def test_exports_and_path_protection(client, demo):
    rid = run(client, demo["dataset_id"]).json()["run_id"]
    csv = client.get(f"/api/v1/backtests/{rid}/export/trades.csv")
    assert csv.status_code == 200 and "attachment" in csv.headers["content-disposition"]
    trades = pd.read_csv(io.BytesIO(csv.content))
    assert len(trades) == len(client.get(f"/api/v1/backtests/{rid}/trades").json())
    assert client.get(f"/api/v1/backtests/{rid}/export/manifest.json").json()["run_id"] == rid
    assert client.get(f"/api/v1/backtests/{rid}/export/lab.db").status_code == 422
    assert client.get(f"/api/v1/backtests/{rid}/export/..%2F..%2Flab.db").status_code in (404, 422)
    assert client.get("/api/v1/backtests/..%2F..%2Fx/trades").status_code in (404, 422)
    assert client.get(f"/api/v1/backtests/{'f' * 16}").status_code == 404


def test_unexpected_errors_are_generic_500(client, demo, monkeypatch):
    import ai_trader_optimizer.api.app as api_app

    def boom(*a, **k):
        raise RuntimeError("secret internal detail")
    monkeypatch.setattr(api_app, "run_and_store", boom)
    c = LocalClient(api_app.create_app(LabCatalog()), raise_server_exceptions=False)
    r = c.post("/api/v1/backtests", json={"dataset_id": demo["dataset_id"], "strategy_key": BASELINE})
    assert r.status_code == 500 and "secret" not in r.text


def test_equity_drawdown_series_matches_metrics_even_when_thinned(client, demo):
    body = run(client, demo["dataset_id"]).json()
    m = body["metrics"]
    full = client.get(f"/api/v1/backtests/{body['run_id']}/equity?max_points=20000").json()["points"]
    assert min(p["drawdown_mtm_pct"] for p in full) == pytest.approx(m["max_dd_mtm_pct"])
    thin = client.get(f"/api/v1/backtests/{body['run_id']}/equity?max_points=10").json()["points"]
    assert len(thin) <= 12  # display only
    assert min(p["drawdown_mtm_pct"] for p in thin) == pytest.approx(m["max_dd_mtm_pct"])  # worst point kept
    assert all(p["drawdown_mtm_pct"] <= 0 for p in full)
