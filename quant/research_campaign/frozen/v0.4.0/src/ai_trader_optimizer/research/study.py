"""Edge study: is there a measurable, out-of-sample advantage — in the strategy, and in a signal filter?

Pipeline (all deterministic for given inputs; the bootstrap seed derives from the study id):
1. every candidate signal of the strategy is labelled (``labels.py``) and described (``features.py``);
2. anchored walk-forward: the first ``initial_train_fraction`` of the period trains only; the rest is cut
   into ``folds`` consecutive test windows. A training row must have its OUTCOME known before the test
   window starts (purging — no label overlaps the test period); the threshold of the filter is chosen on
   an inner, later validation slice of the training rows, never on the test rows;
3. every test prediction is therefore out of sample. Uncertainty: moving-block bootstrap of the
   out-of-sample signals; confidence level corrected for the number of studies already run on the same
   dataset (Bonferroni: each extra look at the same history raises the chance of a lucky false edge);
4. verdict (conservative): "edge" only if the lower bound of the filtered mean R is > 0 with enough
   out-of-sample signals. Otherwise the answer is "not demonstrated" — which is a result, not a failure.

Nothing here sends an order or sizes a position: the output is evidence and, at most, an opinion on the
latest signal, to be checked by a human and by the Risk Guardian.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .. import ENGINE_VERSION, __version__
from ..backtest.codehash import code_fingerprint
from ..backtest.engine import _session_mask, check_signal_contract
from ..backtest.models import BacktestConfig
from ..strategies.base import StrategySpec
from ..strategies.registry import build_strategy
from .features import FEATURE_LABELS_FR, FEATURE_SET, FEATURES, signal_features
from .labels import label_signals
from .stats import LogisticModel, auc, block_bootstrap_indices, brier, calibration_bins, interval

STUDY_FORMAT = "ato-study/1"
MIN_OOS_SIGNALS = 100
BASE_ALPHA = 0.05


@dataclass(frozen=True)
class StudySettings:
    horizon_bars: int = 240
    folds: int = 4
    initial_train_fraction: float = 0.5
    l2: float = 1.0
    n_boot: int = 2000
    min_train: int = 100

    def check(self) -> None:
        if not 1 <= self.horizon_bars <= 5000:
            raise ValueError("horizon_bars doit être entre 1 et 5000")
        if not 2 <= self.folds <= 12:
            raise ValueError("folds doit être entre 2 et 12")
        if not 0.2 <= self.initial_train_fraction <= 0.8:
            raise ValueError("initial_train_fraction doit être entre 0,2 et 0,8")
        if not 0 < self.l2 <= 1000:
            raise ValueError("l2 doit être > 0")
        if not 200 <= self.n_boot <= 10000:
            raise ValueError("n_boot doit être entre 200 et 10000")


def research_code_hash() -> str:
    h = hashlib.sha256(code_fingerprint().encode())
    for path in sorted(Path(__file__).resolve().parent.glob("*.py")):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()[:16]


def _rate(level: tuple[float | None, float | None]) -> str:
    lo, hi = level
    if lo is None:
        return "indisponible"
    if lo > 0:
        return "positif"
    if hi is not None and hi < 0:
        return "négatif"
    return "non démontré"


def _choose_threshold(t_entry: np.ndarray, t_exit: np.ndarray, X: np.ndarray, r: np.ndarray,
                      l2: float, min_rows: int) -> float | None:
    """Threshold of the filter, chosen on a LATER validation slice of the training rows (purged).
    None = take every signal (the default whenever filtering does not help on validation)."""
    n = len(r)
    cut = t_entry[int(n * 0.7)] if n else 0
    fit = t_exit < cut
    val = t_entry >= cut
    if fit.sum() < min_rows or val.sum() < 20 or len(set((r[fit] > 0).tolist())) < 2:
        return None
    p = LogisticModel(l2=l2).fit(X[fit], r[fit] > 0).predict_proba(X[val])
    rv = r[val]
    best, best_thr = float(np.mean(rv)), None
    need = max(20, int(0.1 * len(rv)))
    for q in (0.25, 0.5, 0.75):
        thr = float(np.quantile(p, q))
        take = p >= thr
        if take.sum() >= need and float(np.mean(rv[take])) > best + 1e-12:
            best, best_thr = float(np.mean(rv[take])), thr
    return best_thr


def evaluate_signals(t_entry: np.ndarray, t_exit: np.ndarray, X: np.ndarray, r: np.ndarray,
                     settings: StudySettings, seed: int, alpha: float = BASE_ALPHA) -> dict:
    """Walk-forward evaluation on time-ordered signals (pure function — unit-tested on planted data)."""
    order = np.argsort(t_entry, kind="mergesort")
    t_entry, t_exit, X, r = t_entry[order], t_exit[order], X[order], r[order]
    n = len(r)
    if n == 0:
        raise ValueError("Aucun signal étiqueté : rien à évaluer.")
    t0, t1 = int(t_entry[0]), int(t_entry[-1])
    cuts = np.linspace(t0 + (t1 - t0) * settings.initial_train_fraction, t1, settings.folds + 1)
    folds, oos_idx, oos_p, oos_take, oos_ref = [], [], [], [], []
    for k in range(settings.folds):
        a, b = cuts[k], cuts[k + 1]
        test = (t_entry >= a) & ((t_entry < b) if k < settings.folds - 1 else (t_entry <= b))
        train = t_exit < a  # purged: outcome known before the test window opens
        info = {"fold": k + 1, "test_start": pd.Timestamp(int(a), tz="UTC").isoformat(),
                "test_end": pd.Timestamp(int(b), tz="UTC").isoformat(),
                "n_train": int(train.sum()), "n_test": int(test.sum())}
        y_train = r[train] > 0
        if train.sum() < settings.min_train or test.sum() == 0 or len(set(y_train.tolist())) < 2:
            folds.append({**info, "skipped": "pas assez de signaux d'entraînement ou de test"})
            continue
        thr = _choose_threshold(t_entry[train], t_exit[train], X[train], r[train], settings.l2, settings.min_train // 2)
        model = LogisticModel(l2=settings.l2).fit(X[train], y_train)
        p = model.predict_proba(X[test])
        take = np.ones(len(p), bool) if thr is None else p >= thr
        rt = r[test]
        folds.append({**info, "threshold": thr, "taken": int(take.sum()),
                      "baseline_mean_r": float(rt.mean()),
                      "filtered_mean_r": float(rt[take].mean()) if take.any() else None,
                      "auc": auc(rt > 0, p)})
        idx = np.flatnonzero(test)
        oos_idx.append(idx)
        oos_p.append(p)
        oos_take.append(take)
        oos_ref.append(np.full(len(p), float(y_train.mean())))
    if not oos_idx:
        return {"folds": folds, "n_oos": 0, "verdict": _verdict(0, None, None, None, None, alpha)}

    idx = np.concatenate(oos_idx)
    p, take, ref = np.concatenate(oos_p), np.concatenate(oos_take), np.concatenate(oos_ref)
    ro, wo = r[idx], r[idx] > 0
    rng = np.random.default_rng(seed)
    B = block_bootstrap_indices(len(ro), settings.n_boot, rng)
    Rb, Tb = ro[B], take[B]
    base_b = Rb.mean(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        filt_b = (Rb * Tb).sum(axis=1) / Tb.sum(axis=1)
    diff_b = filt_b - base_b
    auc_b = np.array([auc(wo[i], p[i]) or np.nan for i in B[: min(400, settings.n_boot)]])
    base_ci, filt_ci, diff_ci, auc_ci = (interval(base_b, alpha), interval(filt_b, alpha),
                                         interval(diff_b, alpha), interval(auc_b, alpha))
    filt_mean = float(ro[take].mean()) if take.any() else None
    b_model, b_ref = brier(wo, p), brier(wo, ref)
    cum_base, cum_filt = np.cumsum(ro), np.cumsum(np.where(take, ro, 0.0))
    step = max(1, -(-len(ro) // 400))
    keep = sorted(set(range(0, len(ro), step)) | {len(ro) - 1})
    return {
        "folds": folds,
        "n_oos": int(len(ro)),
        "n_taken": int(take.sum()),
        "coverage": float(take.mean()),
        "baseline": {"mean_r": float(ro.mean()), "ci": base_ci, "win_rate": float(wo.mean()),
                     "p_positive": float(np.mean(base_b > 0)), "rating": _rate(base_ci)},
        "filtered": {"mean_r": filt_mean, "ci": filt_ci,
                     "win_rate": float(wo[take].mean()) if take.any() else None,
                     "p_positive": float(np.mean(filt_b > 0)), "rating": _rate(filt_ci)},
        "improvement": {"mean_r": None if filt_mean is None else filt_mean - float(ro.mean()), "ci": diff_ci,
                        "rating": _rate(diff_ci)},
        "auc": {"value": auc(wo, p), "ci": auc_ci,
                "rating": "positif" if auc_ci[0] is not None and auc_ci[0] > 0.5 else "non démontré"},
        "brier": {"model": b_model, "reference": b_ref, "skill": None if b_ref == 0 else 1 - b_model / b_ref},
        "calibration": calibration_bins(wo, p),
        "cumulative": [{"t": pd.Timestamp(int(t_entry[idx][i]), tz="UTC").isoformat(),
                        "baseline_r": float(cum_base[i]), "filtered_r": float(cum_filt[i])} for i in keep],
        "verdict": _verdict(len(ro), take.sum(), filt_ci, base_ci, diff_ci, alpha),
    }


def _verdict(n_oos: int, n_taken, filt_ci, base_ci, diff_ci, alpha: float) -> dict:
    conf = f"{(1 - alpha) * 100:.1f} %".replace(".", ",")
    if n_oos < MIN_OOS_SIGNALS or (n_taken or 0) < MIN_OOS_SIGNALS // 2:
        return {"code": "INSUFFICIENT", "confidence": conf,
                "title": "Échantillon insuffisant",
                "text": f"Moins de {MIN_OOS_SIGNALS} signaux hors échantillon : aucune conclusion possible. "
                        "Importez un historique plus long."}
    if filt_ci[0] is not None and filt_ci[0] > 0:
        model_part = (" Le filtre du modèle apporte un gain démontré." if diff_ci[0] is not None and diff_ci[0] > 0
                      else " Le gain propre au filtre n'est pas démontré.")
        return {"code": "EDGE", "confidence": conf, "title": "Avantage hors échantillon démontré",
                "text": f"La borne basse de l'espérance (au niveau {conf}) est positive, coûts supposés inclus."
                        f"{model_part} Étape suivante : confirmer sur une période future jamais utilisée, puis "
                        "en compte démo — un historique ne garantit rien."}
    if filt_ci[1] is not None and filt_ci[1] < 0 and base_ci[1] is not None and base_ci[1] < 0:
        return {"code": "NEGATIVE", "confidence": conf, "title": "Perte attendue démontrée",
                "text": "Avec ces coûts, la stratégie perd de l'argent hors échantillon, filtrée ou non. "
                        "Ne pas la trader sous cette forme."}
    return {"code": "NO_EDGE", "confidence": conf, "title": "Aucun avantage démontré",
            "text": "L'intervalle de confiance de l'espérance contient zéro : le résultat est compatible avec le "
                    "hasard. Ne pas engager d'argent sur cette base."}


def _study_id(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:16]


def studies_dir(root: Path) -> Path:
    d = Path(root) / "studies"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_studies(root: Path) -> list[dict]:
    out = []
    for f in sorted(studies_dir(root).glob("*.json")):
        try:
            s = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        out.append({"study_id": s["study_id"], "created_at": s["created_at"], "dataset_id": s["dataset"]["dataset_id"],
                    "dataset_name": s["dataset"]["name"], "data_kind": s["dataset"]["kind"],
                    "strategy_key": s["strategy"]["key"], "verdict": s["result"]["verdict"]["code"],
                    "n_oos": s["result"]["n_oos"]})
    return sorted(out, key=lambda s: s["created_at"], reverse=True)


def load_study(root: Path, study_id: str) -> dict | None:
    f = studies_dir(root) / f"{study_id}.json"
    return json.loads(f.read_text()) if f.exists() else None


def run_edge_study(cat, dataset_id: str, spec: StrategySpec, config: BacktestConfig,
                   settings: StudySettings | None = None) -> dict:
    settings = settings or StudySettings()
    settings.check()
    meta = cat.dataset_meta(dataset_id)
    if meta is None:
        raise ValueError(f"Jeu de données introuvable : {dataset_id}")
    strategy = build_strategy(spec, config.strategy_params)
    identity = {"format": STUDY_FORMAT, "dataset": dataset_id, "strategy": spec.key, "spec_hash": spec.spec_hash(),
                "params": strategy.params, "costs": config.costs.model_dump(mode="json"),
                "contract": config.contract.model_dump(mode="json"),
                "hours": (config.trading_hours or spec.trading_hours).model_dump(mode="json"),
                "settings": asdict(settings), "code": research_code_hash()}
    study_id = _study_id(identity)
    root = Path(cat.root)
    existing = load_study(root, study_id)
    if existing is not None:
        return existing  # same inputs + same code = same result: never recomputed into a different file

    dataset = cat.load_dataset(dataset_id)
    bars = dataset.bars.reset_index(drop=True)
    sig = strategy.compute(bars)
    check_signal_contract(sig, len(bars))
    labels = label_signals(dataset, spec, config, sig, settings.horizon_bars)
    X = signal_features(bars, labels, config.costs.spread, config.costs.slippage,
                        config.costs.commission_per_lot_per_side, float(config.contract.contract_size or 0))
    ok = X.notna().all(axis=1).to_numpy()
    labels, X = labels[ok].reset_index(drop=True), X[ok].reset_index(drop=True)

    prior = [s for s in list_studies(root) if s["dataset_id"] == dataset_id]
    m = len(prior) + 1
    alpha = BASE_ALPHA / m
    t_entry = labels["entry_time"].astype("int64").to_numpy() if len(labels) else np.zeros(0, np.int64)
    t_exit = labels["exit_time"].astype("int64").to_numpy() if len(labels) else np.zeros(0, np.int64)
    if len(labels) == 0:
        result = {"folds": [], "n_oos": 0, "verdict": _verdict(0, None, None, None, None, alpha)}
    else:
        result = evaluate_signals(t_entry, t_exit, X.to_numpy(float), labels["r"].to_numpy(float), settings,
                                  seed=int(study_id[:8], 16), alpha=alpha)

    # Final model on all labelled signals: interpretable weights + an opinion on the LATEST signal.
    final = None
    r_all = labels["r"].to_numpy(float)
    if len(labels) >= settings.min_train and len(set((r_all > 0).tolist())) == 2:
        Xa = X.to_numpy(float)
        model = LogisticModel(l2=settings.l2).fit(Xa, r_all > 0)
        thr = _choose_threshold(t_entry, t_exit, Xa, r_all, settings.l2, settings.min_train // 2)
        weights = sorted(({"feature": f, "label": FEATURE_LABELS_FR[f], "weight": float(w)}
                          for f, w in zip(FEATURES, model.coef_[1:], strict=True)), key=lambda x: -abs(x["weight"]))
        final = {"trained_on": int(len(labels)), "threshold": thr, "weights": weights,
                 "base_rate": float(np.mean(r_all > 0)),
                 "latest_signal": _latest_opinion(bars, sig, config, model, thr, config.trading_hours or spec.trading_hours,
                                                  dataset.bar_seconds)}

    if final and final["latest_signal"] and result["verdict"]["code"] != "EDGE":
        # an opinion is only allowed once an out-of-sample edge is demonstrated
        final["latest_signal"]["opinion"] = "NE PAS TRADER"
        final["latest_signal"]["why"] = "Aucun avantage démontré hors échantillon : la probabilité est indicative."
    study = {
        "format": STUDY_FORMAT, "study_id": study_id,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "software_version": __version__, "engine_version": ENGINE_VERSION, "code_hash": identity["code"],
        "execution_mode": "simulation",
        "dataset": {"dataset_id": dataset_id, "name": meta.name, "kind": meta.kind.value if hasattr(meta.kind, "value") else str(meta.kind),
                    "symbol": meta.symbol, "timeframe": meta.timeframe, "start": str(meta.start), "end": str(meta.end)},
        "strategy": {"key": spec.key, "name": spec.name, "params": strategy.params, "illustrative": spec.illustrative},
        "settings": asdict(settings), "costs": identity["costs"],
        "feature_set": FEATURE_SET, "features": [{"feature": f, "label": FEATURE_LABELS_FR[f]} for f in FEATURES],
        "signals": {"candidates": int((sig["signal"] != 0).sum()), "labelled": int(len(labels)),
                    "exit_reasons": {str(k): int(v) for k, v in labels["exit_reason"].value_counts().items()}},
        "multiple_testing": {"studies_on_dataset": m, "alpha": alpha},
        "result": result, "final_model": final,
    }
    path = studies_dir(root) / f"{study_id}.json"
    _write_atomic(path, study)
    return json.loads(path.read_text())  # respond with what was PERSISTED


def _latest_opinion(bars: pd.DataFrame, sig: pd.DataFrame, config: BacktestConfig, model: LogisticModel,
                    thr: float | None, hours, bar_seconds: int) -> dict | None:
    """Opinion on the most recent signal the engine could act on (entry bar inside the trading session):
    a signal outside the session was never seen in training and would be an extrapolation."""
    entry_ts = bars["timestamp"] + pd.Timedelta(seconds=bar_seconds)
    in_session, _ = _session_mask(entry_ts, hours)
    nz = np.flatnonzero((sig["signal"].to_numpy() != 0) & in_session)
    if not len(nz):
        return None
    j = int(nz[-1])
    lab = pd.DataFrame({"sig_idx": [j], "direction": [int(sig["signal"].iat[j])],
                        "sl_distance": [float(sig["sl_distance"].iat[j])]})
    X = signal_features(bars, lab, config.costs.spread, config.costs.slippage,
                        config.costs.commission_per_lot_per_side, float(config.contract.contract_size or 0))
    if not X.notna().all(axis=1).iat[0]:
        return None
    p = float(model.predict_proba(X.to_numpy(float))[0])
    return {"signal_time": bars["timestamp"].iat[j].isoformat(), "direction": "BUY" if lab["direction"].iat[0] == 1 else "SELL",
            "probability_win": p, "threshold": thr,
            "opinion": "PRENDRE" if thr is None or p >= thr else "IGNORER"}


def _finite(v):
    """NaN / ±inf are stored as null: a missing value is never written as a number."""
    if isinstance(v, dict):
        return {str(k): _finite(x) for k, x in v.items()}
    if isinstance(v, list | tuple):
        return [_finite(x) for x in v]
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, float | np.floating):
        return float(v) if np.isfinite(v) else None
    return v


def _write_atomic(path: Path, data: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(_finite(data), f, ensure_ascii=False, indent=1, default=str, allow_nan=False)
    os.replace(tmp, path)
