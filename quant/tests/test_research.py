"""Research layer: labels agree with the engine, features are causal, the evaluation finds a planted edge
and does not invent one in noise, studies are deterministic and corrected for repeated looks."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from ai_trader_optimizer.backtest.engine import run_backtest
from ai_trader_optimizer.data.synthetic import synthetic_dataset
from ai_trader_optimizer.research import StudySettings, list_studies, run_edge_study, run_robustness
from ai_trader_optimizer.research.features import FEATURES, bar_features, signal_features
from ai_trader_optimizer.research.labels import label_signals
from ai_trader_optimizer.research.stats import LogisticModel, auc, block_bootstrap_indices, calibration_bins
from ai_trader_optimizer.research.study import MIN_OOS_SIGNALS, evaluate_signals
from ai_trader_optimizer.services import default_config
from ai_trader_optimizer.storage import LabCatalog
from ai_trader_optimizer.strategies import load_catalog
from ai_trader_optimizer.strategies.registry import build_strategy

from conftest import LocalClient

BASELINE = "baseline.ema_trend_3bars@1.0.0"


@pytest.fixture
def lab(tmp_path):
    return LabCatalog(tmp_path / "lab")


@pytest.fixture
def spec():
    return load_catalog().specs[BASELINE]


# ------------------------------------------------------------------ labels
def test_labels_equal_engine_r_multiple_for_every_traded_signal(lab, spec):
    ds = synthetic_dataset(42, 10)
    cfg = default_config(lab)
    res = run_backtest(ds, spec, cfg)
    sig = build_strategy(spec, cfg.strategy_params).compute(ds.bars.reset_index(drop=True))
    lab_df = label_signals(ds, spec, cfg, sig, horizon_bars=240)
    m = res.trades.merge(lab_df, on="signal_time", how="left", suffixes=("_engine", "_label"))
    sl_tp = m[m["exit_reason_engine"].isin(["SL", "TP", "SL_GAP", "TP_GAP"])]
    assert len(res.trades) > 0 and len(sl_tp) == len(res.trades)
    assert (sl_tp["exit_reason_engine"] == sl_tp["exit_reason_label"]).all()
    assert np.allclose(sl_tp["r_multiple"], sl_tp["r"], atol=1e-12)


def test_labels_cover_many_more_signals_than_the_guarded_backtest(lab, spec):
    ds = synthetic_dataset(42, 10)
    cfg = default_config(lab)
    sig = build_strategy(spec, cfg.strategy_params).compute(ds.bars.reset_index(drop=True))
    lab_df = label_signals(ds, spec, cfg, sig)
    assert len(lab_df) > 10 * len(run_backtest(ds, spec, cfg).trades)
    assert set(lab_df["exit_reason"]) <= {"SL", "TP", "SL_GAP", "TP_GAP", "HORIZON"}
    assert (lab_df["exit_time"] >= lab_df["entry_time"]).all()


def test_horizon_exit_and_unobservable_outcomes_are_not_guessed(lab, spec):
    ds = synthetic_dataset(42, 10)
    cfg = default_config(lab)
    sig = build_strategy(spec, cfg.strategy_params).compute(ds.bars.reset_index(drop=True))
    short = label_signals(ds, spec, cfg, sig, horizon_bars=1)
    assert "HORIZON" in set(short["exit_reason"])
    assert (short["bars_held"] <= 2).all()
    n = len(ds.bars)
    assert (short["sig_idx"] + 2 < n).all()  # outcome must be observable within the data


# ------------------------------------------------------------------ features
def test_features_are_causal():
    ds = synthetic_dataset(3, 5)
    bars = ds.bars.reset_index(drop=True)
    j = 3000
    before = bar_features(bars).iloc[j]
    altered = bars.copy()
    altered.loc[j + 1:, ["open", "high", "low", "close"]] *= 1.5  # rewrite the future
    after = bar_features(altered).iloc[j]
    pd.testing.assert_series_equal(before, after)


def test_signal_features_have_the_declared_columns():
    ds = synthetic_dataset(3, 5)
    bars = ds.bars.reset_index(drop=True)
    lab_df = pd.DataFrame({"sig_idx": [2000, 2500], "direction": [1, -1], "sl_distance": [1.0, 2.0]})
    X = signal_features(bars, lab_df, 0.3, 0.05, 3.0, 100.0)
    assert list(X.columns) == FEATURES and X.notna().all().all()
    assert (X["cost_r"] > 0).all()


# ------------------------------------------------------------------ statistics
def test_logistic_recovers_a_planted_relation_and_auc_is_sane():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(3000, 3))
    y = rng.random(3000) < 1 / (1 + np.exp(-(1.5 * X[:, 0] - 1.0 * X[:, 1])))
    m = LogisticModel(l2=1.0).fit(X, y)
    assert m.coef_[1] > 1.0 and m.coef_[2] < -0.6 and abs(m.coef_[3]) < 0.2
    assert auc(y, m.predict_proba(X)) > 0.75
    assert auc(np.array([0, 0, 1, 1]), np.array([0.1, 0.2, 0.8, 0.9])) == 1.0
    assert auc(np.array([0, 1]), np.array([0.5, 0.5])) == 0.5
    assert auc(np.array([1, 1]), np.array([0.5, 0.6])) is None


def test_block_bootstrap_is_deterministic_and_contiguous():
    a = block_bootstrap_indices(100, 50, np.random.default_rng(1))
    b = block_bootstrap_indices(100, 50, np.random.default_rng(1))
    assert a.shape == (50, 100) and (a == b).all()
    assert ((np.diff(a[0]) % 100) == 1).mean() > 0.8  # mostly consecutive indices (blocks)
    assert sum(c["n"] for c in calibration_bins(np.ones(7), np.linspace(0, 1, 7))) == 7


def _signals(n, rng, edge: bool):
    t = np.sort(rng.integers(0, 10**15, n)).astype(np.int64)
    t_exit = t + 10**9
    X = rng.normal(size=(n, 4))
    p = 1 / (1 + np.exp(-(1.6 * X[:, 0]))) if edge else np.full(n, 0.4)
    win = rng.random(n) < p
    r = np.where(win, 1.5, -1.0)
    return t, t_exit, X, r


def test_evaluation_finds_a_planted_edge():
    rng = np.random.default_rng(11)
    t, te, X, r = _signals(4000, rng, edge=True)
    out = evaluate_signals(t, te, X, r, StudySettings(n_boot=500), seed=1)
    assert out["verdict"]["code"] == "EDGE"
    assert out["auc"]["rating"] == "positif" and out["improvement"]["rating"] == "positif"
    assert out["filtered"]["mean_r"] > out["baseline"]["mean_r"]


def test_evaluation_does_not_invent_an_edge_in_noise():
    """Smoke check only — the false-positive RATE is measured by the campaign (research_campaign/).
    At the app's first-study level alpha_1 = family_alpha(1) ≈ 0.0304 (one-sided), P(≥ 3 EDGE of 12) < 1 %."""
    from ai_trader_optimizer.research.registry import family_alpha
    edges = 0
    for seed in range(12):
        rng = np.random.default_rng(100 + seed)
        t, te, X, r = _signals(1500, rng, edge=False)  # expectancy 0.4*1.5 - 0.6 = 0: no edge
        out = evaluate_signals(t, te, X, r, StudySettings(n_boot=300), seed=seed, alpha=family_alpha(1))
        edges += out["verdict"]["code"] == "EDGE"
    assert edges <= 2


def test_training_rows_are_purged_before_each_test_window():
    rng = np.random.default_rng(5)
    t, te, X, r = _signals(2000, rng, edge=False)
    te = te + (t.max() - t.min()) // 20  # long labels: many would overlap the next test window
    out = evaluate_signals(t, te, X, r, StudySettings(n_boot=200), seed=0)
    for f in out["folds"]:
        start = pd.Timestamp(f["test_start"]).value
        assert f["n_train"] == int((te < start).sum())


def test_small_samples_are_reported_as_insufficient():
    rng = np.random.default_rng(2)
    t, te, X, r = _signals(150, rng, edge=True)
    out = evaluate_signals(t, te, X, r, StudySettings(n_boot=200, min_train=50), seed=0)
    assert out["n_oos"] < MIN_OOS_SIGNALS and out["verdict"]["code"] == "INSUFFICIENT"


# ------------------------------------------------------------------ studies
def test_edge_study_on_random_prices_finds_no_edge_and_refuses_an_opinion(lab, spec):
    ds = synthetic_dataset(7, 60)
    lab.save_dataset(ds)
    cfg = default_config(lab)
    s = run_edge_study(lab, ds.meta.dataset_id, spec, cfg, StudySettings(n_boot=300))
    assert s["execution_mode"] == "simulation" and s["dataset"]["kind"] == "synthetic"
    assert s["result"]["verdict"]["code"] in {"NO_EDGE", "NEGATIVE", "INSUFFICIENT"}
    opinion = (s["final_model"] or {}).get("opinion")
    assert opinion and opinion["opinion"] == "NE PAS TRADER" and opinion["reasons"]
    again = run_edge_study(lab, ds.meta.dataset_id, spec, cfg, StudySettings(n_boot=300))
    assert again == s  # same inputs and code -> the stored study, unchanged


def test_repeated_studies_on_one_dataset_tighten_the_confidence_level(lab, spec):
    ds = synthetic_dataset(7, 20)
    lab.save_dataset(ds)
    cfg = default_config(lab)
    a = run_edge_study(lab, ds.meta.dataset_id, spec, cfg, StudySettings(n_boot=200))
    b = run_edge_study(lab, ds.meta.dataset_id, spec, cfg, StudySettings(n_boot=200, horizon_bars=120))
    assert a["multiple_testing"]["studies_in_family"] == 1 and b["multiple_testing"]["studies_in_family"] == 2
    # summable spending (protocol H2): alpha_m = 0.05·6/(π²m²) -> alpha_2 = alpha_1 / 4, sum over all m ≤ 0.05
    assert a["multiple_testing"]["alpha"] == pytest.approx(0.05 * 6 / math.pi ** 2)
    assert b["multiple_testing"]["alpha"] == pytest.approx(a["multiple_testing"]["alpha"] / 4)
    assert a["multiple_testing"]["family"] == b["multiple_testing"]["family"] == "synthetic:XAUUSD:M1"
    assert len(list_studies(lab.root)) == 2


def test_invalid_settings_are_refused(lab, spec):
    ds = synthetic_dataset(7, 5)
    lab.save_dataset(ds)
    with pytest.raises(ValueError):
        run_edge_study(lab, ds.meta.dataset_id, spec, default_config(lab), StudySettings(folds=1))


# ------------------------------------------------------------------ robustness of one run
def test_robustness_is_seeded_and_brackets_the_observed_values(lab, spec):
    ds = synthetic_dataset(42, 30)
    res = run_backtest(ds, spec, default_config(lab))
    h = res.manifest["result_hash"]
    a = run_robustness(res.trades, 10_000, 10.0, h, n_boot=500)
    assert a == run_robustness(res.trades, 10_000, 10.0, h, n_boot=500)
    lo, hi = a["expectancy_r"]["ci"]
    assert lo <= a["expectancy_r"]["value"] <= hi
    dd = a["max_drawdown_pct"]
    assert dd["worst"] <= dd["p95"] <= dd["median"] <= 0 and 0 <= dd["p_breach_limit"] <= 1
    tiny = run_robustness(res.trades.head(1), 10_000, 10.0, h)
    assert tiny["sufficient"] is False and "expectancy_r" not in tiny


# ------------------------------------------------------------------ API
def test_research_api_round_trip(lab_dir):
    from ai_trader_optimizer.api.app import create_app

    client = LocalClient(create_app(LabCatalog()))
    ds = client.post("/api/v1/datasets/demo", json={"seed": 7, "days": 20}).json()["dataset"]
    r = client.post("/api/v1/research/edge-studies", json={"dataset_id": ds["dataset_id"], "strategy_key": BASELINE})
    assert r.status_code == 201, r.text
    study = r.json()
    assert client.get(f"/api/v1/research/edge-studies/{study['study_id']}").json() == study
    assert [s["study_id"] for s in client.get("/api/v1/research/edge-studies").json()] == [study["study_id"]]
    assert client.get("/api/v1/research/edge-studies/0123456789abcdef").status_code == 404
    bad = client.post("/api/v1/research/edge-studies", json={"dataset_id": ds["dataset_id"], "strategy_key": BASELINE,
                                                             "folds": 1})
    assert bad.status_code == 422
    run = client.post("/api/v1/backtests", json={"dataset_id": ds["dataset_id"], "strategy_key": BASELINE}).json()
    rob = client.get(f"/api/v1/backtests/{run['run_id']}/robustness").json()
    assert rob["n_trades"] == run["metrics"]["trades"]
    foreign = LocalClient(create_app(LabCatalog()), local_header=False)
    assert foreign.post("/api/v1/research/edge-studies", json={}).status_code == 403  # mutation guard applies
