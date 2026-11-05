"""v0.4.1 — reproduction tests of the Codex V0.4.0 audit findings (B04-3, I04-1, I04-3, I04-4, I04-8, minor AUC).

Written BEFORE the fixes and run first against the frozen v0.4.0 sources (they failed there — see
quant/docs/VALIDATION_V041.md §3). Assertions describe the required behaviour, not an implementation:
an invalid computation must end in a refusal, a stored study must be verified before being served, and an
opinion may never be given on a signal whose outcome the model has already learned.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from ai_trader_optimizer.backtest.models import BacktestConfig
from ai_trader_optimizer.data.synthetic import synthetic_dataset, synthetic_m1_frame
from ai_trader_optimizer.data.validation import dataset_from_frame
from ai_trader_optimizer.research import StudySettings, list_studies, load_study, run_edge_study
from ai_trader_optimizer.research import study as study_mod
from ai_trader_optimizer.research.labels import label_signals
from ai_trader_optimizer.research.stats import LogisticModel
from ai_trader_optimizer.safety import DataKind
from ai_trader_optimizer.services import default_config
from ai_trader_optimizer.storage import LabCatalog
from ai_trader_optimizer.strategies import load_catalog
from ai_trader_optimizer.strategies.registry import build_strategy

from conftest import LocalClient

BASELINE = "baseline.ema_trend_3bars@1.0.0"
FAVOURABLE = {"PRENDRE", "FAVORABLE — EXPÉRIMENTAL"}


@pytest.fixture
def lab(tmp_path):
    return LabCatalog(tmp_path / "lab")


@pytest.fixture
def spec():
    return load_catalog().specs[BASELINE]


def _study(lab, spec, days=20, seed=7, settings=None):
    ds = synthetic_dataset(seed, days)
    lab.save_dataset(ds)
    return ds, run_edge_study(lab, ds.meta.dataset_id, spec, default_config(lab), settings or StudySettings(n_boot=200))


def _opinion(st):
    fm = st.get("final_model") or {}
    return fm.get("latest_signal") or fm.get("opinion") or {}


def _study_file(lab, study_id):
    return next(p for p in (lab.root / "studies").glob(f"{study_id}*.json"))


# ------------------------------------------------------------------ B04-3: invalid numbers never favour a trade
def test_logistic_model_overflow_is_detected_not_silently_propagated():
    X = np.full((200, 12), 1e308)
    y = np.r_[np.zeros(100), np.ones(100)]
    try:
        m = LogisticModel().fit(X, y)
    except (ValueError, ArithmeticError):
        return  # refusing is correct
    assert np.isfinite(m.coef_).all(), "fit returned non-finite coefficients without raising"


def test_predict_proba_refuses_non_finite_inputs():
    rng = np.random.default_rng(0)
    m = LogisticModel().fit(rng.normal(size=(200, 3)), rng.random(200) < 0.5)
    with pytest.raises((ValueError, ArithmeticError)):
        m.predict_proba(np.array([[np.nan, 0.0, 0.0]]))


def test_a_nan_producing_model_with_an_edge_verdict_never_yields_a_favourable_opinion(lab, spec, monkeypatch):
    """Codex B04-3 reproduction: thr=None + NaN probability gave « PRENDRE » even with a forced EDGE."""
    monkeypatch.setattr(study_mod, "_choose_threshold", lambda *a, **k: None)
    real_verdict = study_mod._verdict

    def always_edge(*a, **k):
        v = real_verdict(*a, **k)
        return {**v, "code": "EDGE"}

    monkeypatch.setattr(study_mod, "_verdict", always_edge)
    monkeypatch.setattr(LogisticModel, "predict_proba", lambda self, X: np.full(len(X), np.nan))
    _, st = _study(lab, spec)
    op = _opinion(st)
    assert op.get("opinion") not in FAVOURABLE
    assert op.get("opinion") in (None, "NE PAS TRADER")


def test_an_exception_inside_the_model_is_a_refusal_not_a_signal(lab, spec, monkeypatch):
    def boom(self, X, y):
        raise FloatingPointError("simulated numerical failure")

    monkeypatch.setattr(LogisticModel, "fit", boom)
    _, st = _study(lab, spec)
    assert st["result"]["verdict"]["code"] != "EDGE"
    assert _opinion(st).get("opinion") not in FAVOURABLE


# ------------------------------------------------------------------ I04-1: persisted studies are verified
def test_a_tampered_study_is_refused_by_the_api_and_never_reused(lab_dir, spec):
    from ai_trader_optimizer.api import create_app
    c = LabCatalog(lab_dir)
    ds = synthetic_dataset(7, 20)
    c.save_dataset(ds)
    client = LocalClient(create_app(c))
    body = {"dataset_id": ds.meta.dataset_id, "strategy_key": BASELINE, "horizon_bars": 240, "folds": 4}
    r = client.post("/api/v1/research/edge-studies", json=body)
    assert r.status_code == 201
    sid = r.json()["study_id"]
    path = _study_file(c, sid)
    raw = json.loads(path.read_text())
    target = raw.get("study", raw)
    target["result"]["verdict"]["code"] = "EDGE"
    path.chmod(0o644)  # published read-only since v0.4.1: simulate a writer that bypasses it
    path.write_text(json.dumps(raw))
    got = client.get(f"/api/v1/research/edge-studies/{sid}")
    assert got.status_code == 409, got.text
    again = client.post("/api/v1/research/edge-studies", json=body)
    assert again.status_code == 409 or again.json()["result"]["verdict"]["code"] != "EDGE"
    listed = client.get("/api/v1/research/edge-studies").json()
    assert all(s.get("verdict") != "EDGE" for s in listed if s["study_id"] == sid)


def test_a_consistently_re_hashed_forgery_is_still_refused_by_the_semantic_check(lab, spec):
    """A forger who recomputes the SHA-256 after editing the verdict is caught by re-deriving the verdict."""
    import hashlib

    from ai_trader_optimizer.storage.integrity import canonical_json
    _, st = _study(lab, spec)
    path = _study_file(lab, st["study_id"])
    doc = json.loads(path.read_bytes())
    if doc.get("format") != "ato-study/2":
        pytest.fail("persisted study has no verifiable format")
    doc["study"]["result"]["verdict"]["code"] = "EDGE"
    doc["sha256"] = hashlib.sha256(canonical_json(doc["study"])).hexdigest()
    path.chmod(0o644)
    path.write_bytes(canonical_json(doc))
    with pytest.raises(Exception, match="incohérent"):
        load_study(lab.root, st["study_id"])


def test_a_broken_trial_registry_blocks_new_studies(lab, spec):
    from ai_trader_optimizer.research import RegistryIntegrityError
    ds, _ = _study(lab, spec)
    reg = lab.root / "studies" / "registry.jsonl"
    reg.write_bytes(reg.read_bytes().replace(b'"m":1', b'"m":0'))
    with pytest.raises(RegistryIntegrityError):
        run_edge_study(lab, ds.meta.dataset_id, spec, default_config(lab), StudySettings(n_boot=202))


def test_a_published_study_file_is_never_rewritten(lab, spec):
    _, st = _study(lab, spec)
    path = _study_file(lab, st["study_id"])
    before = path.read_bytes()
    st2 = run_edge_study(lab, st["dataset"]["dataset_id"], load_catalog().specs[BASELINE], default_config(lab),
                         StudySettings(n_boot=200))
    assert st2["study_id"] == st["study_id"]
    assert path.read_bytes() == before


def test_deleting_a_study_does_not_reset_the_multiple_testing_count(lab, spec):
    ds, st = _study(lab, spec)
    _study_file(lab, st["study_id"]).unlink()
    st2 = run_edge_study(lab, ds.meta.dataset_id, spec, default_config(lab), StudySettings(n_boot=201))
    assert st2["multiple_testing"]["alpha"] < st["multiple_testing"]["alpha"]


def test_reading_a_missing_study_returns_none_and_listing_skips_nothing_silently(lab, spec):
    assert load_study(lab.root, "0" * 16) is None
    _, st = _study(lab, spec)
    assert [s["study_id"] for s in list_studies(lab.root)] == [st["study_id"]]


# ------------------------------------------------------------------ I04-4 / N9: time separation of the opinion
def test_the_opinion_never_scores_a_signal_already_used_for_training(lab, spec):
    """Codex I04-4: seed 7 / 20 days — the latest opinion was on a labelled (training) signal."""
    ds, st = _study(lab, spec)
    op = _opinion(st)
    if not op or op.get("signal_time") is None:
        return  # no opinion at all is acceptable
    cfg = default_config(lab)
    sig = build_strategy(spec, cfg.strategy_params).compute(ds.bars.reset_index(drop=True))
    labels = label_signals(ds, spec, cfg, sig, 240)
    labelled = set(pd.to_datetime(labels["signal_time"]).map(pd.Timestamp.isoformat))
    if op.get("opinion") in FAVOURABLE or op.get("probability_win") is not None:
        assert op["signal_time"] not in labelled, "probability given on a signal whose outcome was learned"


def test_label_outcomes_are_available_only_at_the_close_of_the_exit_bar(lab, spec):
    ds = synthetic_dataset(7, 20)
    cfg = default_config(lab)
    sig = build_strategy(spec, cfg.strategy_params).compute(ds.bars.reset_index(drop=True))
    labels = label_signals(ds, spec, cfg, sig, 240)
    assert "available_time" in labels.columns
    bar = pd.Timedelta(seconds=ds.bar_seconds)
    assert (labels["available_time"] == labels["exit_time"] + bar).all()
    assert (labels["available_time"] > labels["entry_time"]).all()


# ------------------------------------------------------------------ I04-3: research refuses unsupported configs
def _m5_dataset():
    f = synthetic_m1_frame(seed=3, days=30)
    f = f.set_index("timestamp").resample("5min").agg({"open": "first", "high": "max", "low": "min",
                                                        "close": "last"}).dropna().reset_index()
    return dataset_from_frame(f, name="M5", symbol="XAUUSD-DEMO", source_label="t", kind=DataKind.SYNTHETIC)


@pytest.mark.parametrize("change", ["timeframe", "trade_start", "max_bars", "session_end", "contract"])
def test_research_refuses_configurations_it_does_not_model(lab, spec, change):
    ds = _m5_dataset() if change == "timeframe" else synthetic_dataset(7, 20)
    lab.save_dataset(ds)
    cfg = default_config(lab).model_dump(mode="json")
    if change == "trade_start":
        cfg["trade_start"] = ds.meta.end
    elif change == "max_bars":
        cfg["max_bars_in_trade"] = 1
    elif change == "session_end":
        cfg["close_at_session_end"] = True
    elif change == "contract":
        cfg["contract"] = {**cfg["contract"], "symbol": "EURUSD"}
    with pytest.raises(ValueError):
        run_edge_study(lab, ds.meta.dataset_id, spec, BacktestConfig.model_validate(cfg), StudySettings(n_boot=200))


# ------------------------------------------------------------------ minor: AUC = 0 is a valid value
def test_a_zero_auc_is_kept_in_the_bootstrap_interval(monkeypatch):
    monkeypatch.setattr(study_mod, "auc", lambda y, p: 0.0)
    rng = np.random.default_rng(1)
    n = 600
    t = np.arange(n, dtype=np.int64) * 60 * 10**9
    out = study_mod.evaluate_signals(t, t + 10**9, rng.normal(size=(n, 3)), np.where(rng.random(n) < 0.4, 1.5, -1.0),
                                     StudySettings(n_boot=200), seed=0)
    assert out["auc"]["ci"][0] == 0.0 and out["auc"]["ci"][1] == 0.0


# ------------------------------------------------------------------ I04-8: robustness GET is a bounded heavy job
def test_robustness_is_refused_with_429_when_all_job_slots_are_busy(lab_dir, monkeypatch):
    from ai_trader_optimizer.api import create_app
    c = LabCatalog(lab_dir)
    ds = synthetic_dataset(42, 10)
    c.save_dataset(ds)
    monkeypatch.setenv("ATO_MAX_CONCURRENT_JOBS", "1")
    app = create_app(c)
    client = LocalClient(app)
    run = client.post("/api/v1/backtests", json={"dataset_id": ds.meta.dataset_id, "strategy_key": BASELINE})
    assert run.status_code == 201
    import threading
    gate = threading.Event()
    release = threading.Event()
    real = study_mod.__dict__.get("run_robustness")  # noqa: F841 — keep module import side effects

    import ai_trader_optimizer.api.app as app_mod
    orig = app_mod.run_robustness

    def slow(*a, **k):
        gate.set()
        release.wait(10)
        return orig(*a, **k)

    monkeypatch.setattr(app_mod, "run_robustness", slow)
    url = f"/api/v1/backtests/{run.json()['run_id']}/robustness"
    t = threading.Thread(target=lambda: client.get(url))
    t.start()
    assert gate.wait(10)
    try:
        assert client.get(url).status_code == 429
    finally:
        release.set()
        t.join()
