"""Edge study: is there a measurable, out-of-sample advantage — in the strategy, and in a signal filter?

STATUS: EXPERIMENTAL (``METHOD_STATUS``). Verdicts are provisional research evidence about CANDIDATE signals
simulated one by one — not a portfolio result, not a recommendation, never an order.

Pipeline (deterministic for given inputs; the bootstrap seed derives from the study id):
1. every candidate signal of the strategy is labelled (``labels.py``) and described (``features.py``);
   a label's outcome is AVAILABLE only at the close of its exit bar (``available_time``);
2. anchored walk-forward: the first ``initial_train_fraction`` of the period trains only; the rest is cut
   into ``folds`` consecutive test windows. A training row must have its outcome AVAILABLE before the
   test window starts (purge); the filter threshold is chosen on an inner, later validation slice of the
   training rows, never on test rows. Every signal therefore has a role per fold: training, validation,
   out-of-sample test — or "new" (outcome not yet known at the end of the data);
3. uncertainty: bootstrap of the out-of-sample signals (``inference.py``); multiple looks at the same
   history are counted in an append-only, hash-chained registry (``registry.py``);
4. verdict (conservative); any numerical failure of the model makes the study INVALID — a refusal;
5. the opinion is PROSPECTIVE only: it is given on a signal whose outcome is not yet known, by a model
   trained on labels available before that signal. It can never be « PRENDRE »: at best « FAVORABLE —
   EXPÉRIMENTAL » when every gate passes (edge, model's own gain, valid score, known domain, threshold).

Persisted studies use format ``ato-study/2``: canonical JSON + SHA-256 digest, verified on EVERY read
(detail, list and cache), published atomically, never overwritten (``StudyIntegrityError`` otherwise).
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
from ..storage.integrity import canonical_json
from ..strategies.base import StrategySpec
from ..strategies.registry import build_strategy
from . import inference
from .features import FEATURE_LABELS_FR, FEATURE_SET, FEATURES, signal_features
from .labels import label_signals
from .registry import StudyRegistry, family_key
from .stats import LogisticModel, ModelError, auc, brier, calibration_bins

STUDY_FORMAT = "ato-study/2"
LEGACY_FORMATS = ("ato-study/1",)
METHOD_STATUS = "experimental"  # until an independent validation of the inference: see VALIDATION_V041.md
MIN_OOS_SIGNALS = inference.MIN_OOS_SIGNALS
BASE_ALPHA = 0.05
FAVOURABLE = "FAVORABLE — EXPÉRIMENTAL"
REFUSE = "NE PAS TRADER"
IGNORE = "IGNORER"
_MODEL_FAILURES = (ArithmeticError, ValueError, np.linalg.LinAlgError)  # ModelError is an ArithmeticError


class StudyIntegrityError(RuntimeError):
    """A persisted study (or the trial registry) failed verification: it is refused, never served."""


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


def _rate(level) -> str:
    lo, hi = level
    if lo is None:
        return "indisponible"
    if lo > 0:
        return "positif"
    if hi is not None and hi < 0:
        return "négatif"
    return "non démontré"


# ---------------------------------------------------------------- supported configurations (audit I04-3)
def check_supported(meta, spec: StrategySpec, config: BacktestConfig) -> None:
    """The research labeller reproduces the engine's SL / TP / gap / horizon conventions only. Anything else
    would silently produce labels that the engine would not: it is refused, not ignored."""
    problems = []
    if spec.timeframes.execution != meta.timeframe:
        problems.append(f"la stratégie s'exécute en {spec.timeframes.execution}, les données sont en {meta.timeframe}")
    if config.trade_start is not None or config.trade_end is not None:
        problems.append("fenêtre trade_start / trade_end non prise en charge par la recherche")
    if config.max_bars_in_trade is not None:
        problems.append("sortie après N bougies (max_bars_in_trade) non modélisée par les étiquettes")
    if config.close_at_session_end:
        problems.append("clôture en fin de session non modélisée par les étiquettes")
    sym, csym = str(meta.symbol).upper(), str(config.contract.symbol or "").upper()
    if not csym or not (sym == csym or any(sym.startswith(csym + s) for s in "-._")):
        problems.append(f"contrat {csym or '?'} incompatible avec l'instrument des données {sym}")
    if problems:
        raise ValueError("Configuration non prise en charge par l'étude : " + " ; ".join(problems))


# ---------------------------------------------------------------- evaluation
def _validation_split(t_entry: np.ndarray, t_avail: np.ndarray):
    n = len(t_entry)
    cut = t_entry[int(n * 0.7)] if n else 0
    return t_avail < cut, t_entry >= cut


def _checked_proba(model: LogisticModel, X: np.ndarray) -> np.ndarray:
    p = np.asarray(model.predict_proba(X), float)
    if p.shape != (len(X),) or not (np.isfinite(p).all() and (p >= 0).all() and (p <= 1).all()):
        raise ModelError("probabilité invalide (non finie ou hors de [0, 1])")
    return p


def _choose_threshold(t_entry: np.ndarray, t_avail: np.ndarray, X: np.ndarray, r: np.ndarray,
                      l2: float, min_rows: int) -> float | None:
    """Threshold of the filter, chosen on a LATER validation slice of the training rows (purged).
    None = take every signal (whenever filtering does not help on validation). Model failures propagate."""
    fit, val = _validation_split(t_entry, t_avail)
    if fit.sum() < min_rows or val.sum() < 20 or len(set((r[fit] > 0).tolist())) < 2:
        return None
    p = _checked_proba(LogisticModel(l2=l2).fit(X[fit], r[fit] > 0), X[val])
    rv = r[val]
    best, best_thr = float(np.mean(rv)), None
    need = max(20, int(0.1 * len(rv)))
    for q in (0.25, 0.5, 0.75):
        thr = float(np.quantile(p, q))
        take = p >= thr
        if take.sum() >= need and float(np.mean(rv[take])) > best + 1e-12:
            best, best_thr = float(np.mean(rv[take])), thr
    return best_thr


def _invalid(folds: list, reason: str, alpha: float) -> dict:
    conf = f"{(1 - alpha) * 100:.1f} %".replace(".", ",")
    return {"folds": folds, "n_oos": 0, "verdict": {
        "code": "INVALID", "confidence": conf, "title": "Calcul invalide — aucune conclusion",
        "text": f"Le modèle a échoué ({reason}). L'étude est refusée : aucune conclusion, aucun avis."}}


def evaluate_signals(t_entry: np.ndarray, t_exit: np.ndarray, X: np.ndarray, r: np.ndarray,
                     settings: StudySettings, seed: int, alpha: float = BASE_ALPHA) -> dict:
    """Walk-forward evaluation on time-ordered signals (pure function — unit-tested on planted data).

    ``t_exit`` is the time at which each outcome becomes AVAILABLE (close of the exit bar)."""
    order = np.argsort(t_entry, kind="mergesort")
    t_entry, t_avail, X, r = t_entry[order], t_exit[order], X[order], r[order]
    n = len(r)
    if n == 0:
        raise ValueError("Aucun signal étiqueté : rien à évaluer.")
    t0, t1 = int(t_entry[0]), int(t_entry[-1])
    cuts = np.linspace(t0 + (t1 - t0) * settings.initial_train_fraction, t1, settings.folds + 1)
    folds, oos_idx, oos_p, oos_take, oos_ref = [], [], [], [], []
    for k in range(settings.folds):
        a, b = cuts[k], cuts[k + 1]
        test = (t_entry >= a) & ((t_entry < b) if k < settings.folds - 1 else (t_entry <= b))
        train = t_avail < a  # purged: outcome AVAILABLE before the test window opens
        _, val_part = _validation_split(t_entry[train], t_avail[train])
        info = {"fold": k + 1, "test_start": pd.Timestamp(int(a), tz="UTC").isoformat(),
                "test_end": pd.Timestamp(int(b), tz="UTC").isoformat(),
                "n_train": int(train.sum()), "n_validation": int(val_part.sum()), "n_test": int(test.sum())}
        y_train = r[train] > 0
        if train.sum() < settings.min_train or test.sum() == 0 or len(set(y_train.tolist())) < 2:
            folds.append({**info, "skipped": "pas assez de signaux d'entraînement ou de test"})
            continue
        try:
            thr = _choose_threshold(t_entry[train], t_avail[train], X[train], r[train], settings.l2,
                                    settings.min_train // 2)
            if thr is not None and not np.isfinite(thr):
                raise ModelError("seuil non fini")
            model = LogisticModel(l2=settings.l2).fit(X[train], y_train)
            p = _checked_proba(model, X[test])
        except _MODEL_FAILURES as exc:
            folds.append({**info, "invalid": f"{type(exc).__name__}: {exc}"})
            return _invalid(folds, f"fenêtre {k + 1} : {type(exc).__name__}", alpha)
        take = np.ones(len(p), bool) if thr is None else p >= thr
        rt = r[test]
        folds.append({**info, "threshold": thr, "taken": int(take.sum()),
                      "baseline_mean_r": float(rt.mean()),
                      "filtered_mean_r": float(rt[take].mean()) if take.any() else None,
                      "auc": auc(rt > 0, p)})
        oos_idx.append(np.flatnonzero(test))
        oos_p.append(p)
        oos_take.append(take)
        oos_ref.append(np.full(len(p), float(y_train.mean())))
    if not oos_idx:
        return {"folds": folds, "n_oos": 0, "verdict": _verdict(0, None, None, None, None, alpha)}

    idx = np.concatenate(oos_idx)
    p, take, ref = np.concatenate(oos_p), np.concatenate(oos_take), np.concatenate(oos_ref)
    ro, wo = r[idx], r[idx] > 0
    inf = inference.bootstrap(t_entry[idx], t_avail[idx], ro, take, settings.n_boot, np.random.default_rng(seed),
                              alpha)
    auc_samples = []
    for i in inf["draws"][: min(400, settings.n_boot)]:
        a_ = auc(wo[i], p[i])
        auc_samples.append(np.nan if a_ is None else a_)  # None = one class only; 0.0 is a valid AUC
    auc_ci = inference.lower_upper(np.array(auc_samples, float), alpha)
    base_ci, filt_ci, diff_ci = inf["baseline_ci"], inf["filtered_ci"], inf["improvement_ci"]
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
        "inference": {k: v for k, v in inf.items() if k != "draws" and not k.endswith("_ci")},
        "baseline": {"mean_r": float(ro.mean()), "ci": base_ci, "win_rate": float(wo.mean()),
                     "share_of_draws_positive": inf["baseline_share_positive"], "rating": _rate(base_ci)},
        "filtered": {"mean_r": filt_mean, "ci": filt_ci,
                     "win_rate": float(wo[take].mean()) if take.any() else None,
                     "share_of_draws_positive": inf["filtered_share_positive"], "rating": _rate(filt_ci)},
        "improvement": {"mean_r": None if filt_mean is None else filt_mean - float(ro.mean()), "ci": diff_ci,
                        "rating": _rate(diff_ci)},
        "auc": {"value": auc(wo, p), "ci": auc_ci,
                "rating": "positif" if auc_ci[0] is not None and auc_ci[0] > 0.5 else "non démontré"},
        "brier": {"model": b_model, "reference": b_ref, "skill": None if b_ref == 0 else 1 - b_model / b_ref,
                  "note": "Scores NON calibrés : classement du modèle, pas une probabilité de gain."},
        "calibration": calibration_bins(wo, p),
        "cumulative": [{"t": pd.Timestamp(int(t_entry[idx][i]), tz="UTC").isoformat(),
                        "baseline_r": float(cum_base[i]), "filtered_r": float(cum_filt[i])} for i in keep],
        "verdict": _verdict(len(ro), int(take.sum()), filt_ci, base_ci, diff_ci, alpha,
                            n_units=inf.get("n_units"), n_units_taken=inf.get("n_units_taken"),
                            one_sided=inf.get("one_sided_bound")),
    }


def evaluate_labelled(labels: pd.DataFrame, X: pd.DataFrame, settings: StudySettings, seed: int,
                      alpha: float = BASE_ALPHA) -> dict:
    """The exact evaluation ``run_edge_study`` performs on labelled signals (also used by the campaign)."""
    return evaluate_signals(labels["entry_time"].astype("int64").to_numpy(),
                            labels["available_time"].astype("int64").to_numpy(),
                            X.to_numpy(float), labels["r"].to_numpy(float), settings, seed=seed, alpha=alpha)


def _verdict(n_oos: int, n_taken, filt_ci, base_ci, diff_ci, alpha: float, n_units=None, n_units_taken=None,
             one_sided=None) -> dict:
    conf = f"{(1 - alpha) * 100:.1f} %".replace(".", ",")
    if inference.insufficient(n_oos, n_taken, n_units, n_units_taken):
        return {"code": "INSUFFICIENT", "confidence": conf, "title": "Échantillon insuffisant",
                "text": inference.INSUFFICIENT_TEXT}
    if inference.rejects(filt_ci, one_sided):
        model_part = (" Le filtre du modèle apporte un gain mesuré." if diff_ci[0] is not None and diff_ci[0] > 0
                      else " Le gain propre au filtre n'est pas démontré.")
        return {"code": "EDGE", "confidence": conf, "title": "Indice d'avantage hors échantillon — expérimental",
                "text": "La borne basse de l'espérance par signal candidat est positive, coûts supposés inclus."
                        f"{model_part} Méthode en cours de validation : ce n'est PAS une preuve de rentabilité ni une "
                        "performance de portefeuille. Étape suivante : période future jamais utilisée, puis compte démo."}
    if filt_ci[1] is not None and filt_ci[1] < 0 and base_ci[1] is not None and base_ci[1] < 0:
        return {"code": "NEGATIVE", "confidence": conf, "title": "Perte attendue mesurée",
                "text": "Avec ces coûts, les signaux candidats perdent hors échantillon, filtrés ou non. "
                        "Ne pas trader cette stratégie sous cette forme."}
    return {"code": "NO_EDGE", "confidence": conf, "title": "Aucun avantage démontré",
            "text": "L'intervalle de l'espérance contient zéro : résultat compatible avec le hasard. "
                    "Ne pas engager d'argent sur cette base."}


# ---------------------------------------------------------------- prospective opinion (audit I04-4 / B04-3 / I04-5)
def _refusal(reasons: list[str], **extra) -> dict:
    return {"score": None, **extra, "opinion": REFUSE, "reasons": reasons}


def _prospective_opinion(dataset, bars: pd.DataFrame, sig: pd.DataFrame, labels: pd.DataFrame, X: pd.DataFrame,
                         spec: StrategySpec, config: BacktestConfig, settings: StudySettings, result: dict) -> dict:
    """Opinion on the most recent signal ONLY if its outcome is not yet known (role « nouveau »)."""
    hours = config.trading_hours or spec.trading_hours
    bar = pd.Timedelta(seconds=dataset.bar_seconds)
    in_session, _ = _session_mask(bars["timestamp"] + bar, hours)
    nz = np.flatnonzero((sig["signal"].to_numpy() != 0) & in_session)
    if not len(nz):
        return _refusal(["aucun signal en session"], role=None, signal_time=None)
    j = int(nz[-1])
    base = {"signal_time": bars["timestamp"].iat[j].isoformat(),
            "direction": "BUY" if int(sig["signal"].iat[j]) == 1 else "SELL",
            "decision_time": (bars["timestamp"].iat[j] + bar).isoformat()}
    if j in set(labels["sig_idx"].tolist()):
        return _refusal(["signal déjà résolu : son résultat est connu et sert à l'apprentissage — "
                         "aucune prévision indépendante n'est possible"], role="entraînement", **base)
    remaining = len(bars) - (j + 2)  # bars after the entry bar
    if remaining >= 1:  # unlabelled: is its outcome really still unknown at the end of the data?
        probe = sig.copy()
        probe["signal"] = 0
        probe.iloc[j, probe.columns.get_loc("signal")] = int(sig["signal"].iat[j])
        partial = label_signals(dataset, spec, config, probe, remaining)
        if not len(partial):
            return _refusal(["signal non exploitable par le moteur (trou de données, stop invalide…)"],
                            role="non exploitable", **base)
        if partial["exit_reason"].iat[0] != "HORIZON":
            return _refusal(["signal déjà résolu avant la fin des données (stop ou objectif atteint)"],
                            role="résolu", **base)
    decision_ns = (bars["timestamp"].iat[j] + bar).value
    known = labels["available_time"].astype("int64").to_numpy() < decision_ns
    lab_k, X_k = labels[known].reset_index(drop=True), X[known].reset_index(drop=True)
    r_k = lab_k["r"].to_numpy(float)
    until = lab_k["available_time"].max() if len(lab_k) else None
    base = {**base, "role": "nouveau", "trained_on": int(len(lab_k)),
            "train_until": None if until is None else pd.Timestamp(until).isoformat()}
    if len(lab_k) < settings.min_train or len(set((r_k > 0).tolist())) < 2:
        return _refusal(["pas assez de résultats connus avant ce signal pour entraîner un modèle"], **base)
    one = pd.DataFrame({"sig_idx": [j], "direction": [int(sig["signal"].iat[j])],
                        "sl_distance": [float(sig["sl_distance"].iat[j])]})
    xj = signal_features(bars, one, config.costs.spread, config.costs.slippage,
                         config.costs.commission_per_lot_per_side, float(config.contract.contract_size or 0))
    if not xj.notna().all(axis=1).iat[0]:
        return _refusal(["variables du signal incomplètes (échauffement)"], **base)
    try:
        Xa = X_k.to_numpy(float)
        model = LogisticModel(l2=settings.l2).fit(Xa, r_k > 0)
        thr = _choose_threshold(lab_k["entry_time"].astype("int64").to_numpy(),
                                lab_k["available_time"].astype("int64").to_numpy(), Xa, r_k, settings.l2,
                                settings.min_train // 2)
        if thr is not None and not np.isfinite(thr):
            raise ModelError("seuil non fini")
        score = float(_checked_proba(model, xj.to_numpy(float))[0])
        ood = bool(model.out_of_domain(xj.to_numpy(float))[0])
    except _MODEL_FAILURES as exc:
        return _refusal([f"modèle invalide ({type(exc).__name__}: {exc})"], **base)
    base = {**base, "score": score, "score_kind": "score du modèle — NON calibré, pas une probabilité de gain",
            "threshold": thr, "out_of_domain": ood}
    reasons = []
    if result["verdict"]["code"] != "EDGE":
        reasons.append("aucun indice d'avantage hors échantillon")
    imp = (result.get("improvement") or {}).get("ci") or (None, None)
    if imp[0] is None or imp[0] <= 0:
        reasons.append("le gain propre au filtre du modèle n'est pas démontré")
    if thr is None:
        reasons.append("aucun seuil de filtre validé")
    if ood:
        reasons.append("signal hors du domaine des données d'entraînement")
    if reasons:
        return {**base, "opinion": REFUSE, "reasons": reasons}
    if score < thr:
        return {**base, "opinion": IGNORE, "reasons": ["score sous le seuil du filtre"]}
    return {**base, "opinion": FAVOURABLE,
            "reasons": ["toutes les conditions sont remplies — méthode EXPÉRIMENTALE, non exécutable, à confirmer "
                        "sur une période future puis en démo"]}


def _final_weights(X: pd.DataFrame, r: np.ndarray, settings: StudySettings) -> dict:
    """Descriptive model on the whole labelled history (in-sample: an explanation, never a forecast)."""
    try:
        model = LogisticModel(l2=settings.l2).fit(X.to_numpy(float), r > 0)
    except _MODEL_FAILURES as exc:
        return {"status": "invalide", "error": f"{type(exc).__name__}: {exc}", "weights": []}
    weights = sorted(({"feature": f, "label": FEATURE_LABELS_FR[f], "weight": float(w)}
                      for f, w in zip(FEATURES, model.coef_[1:], strict=True)), key=lambda x: -abs(x["weight"]))
    return {"status": "ok", "weights": weights, "scope": "descriptif, ajusté sur tout l'historique étiqueté",
            "trained_on": int(len(X)), "base_rate": float(np.mean(r > 0))}


# ---------------------------------------------------------------- persistence (audit I04-1)
def _study_id(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:16]


def studies_dir(root: Path) -> Path:
    d = Path(root) / "studies"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sanitise(v, path: str, issues: list[str]):
    """Non-finite DESCRIPTIVE numbers are stored as null and listed in ``numerical_issues`` (decisions were
    already refused upstream; a missing value is never written as a number)."""
    if isinstance(v, dict):
        return {str(k): _sanitise(x, f"{path}.{k}", issues) for k, x in v.items()}
    if isinstance(v, list | tuple):
        return [_sanitise(x, f"{path}[{i}]", issues) for i, x in enumerate(v)]
    if isinstance(v, bool | np.bool_):
        return bool(v)
    if isinstance(v, int | np.integer):
        return int(v)
    if isinstance(v, float | np.floating):
        if np.isfinite(v):
            return float(v)
        issues.append(path)
        return None
    if isinstance(v, pd.Timestamp | datetime):
        return pd.Timestamp(v).isoformat()
    return v


def _container(body: dict) -> bytes:
    digest = hashlib.sha256(canonical_json(body)).hexdigest()
    return canonical_json({"format": STUDY_FORMAT, "sha256": digest, "study": body})


def _semantic_problems(body: dict) -> list[str]:
    """Re-derive the decisions from the stored numbers: a consistent-looking but edited file is refused."""
    res, out = body.get("result") or {}, []
    v = (res.get("verdict") or {}).get("code")
    alpha = (body.get("multiple_testing") or {}).get("alpha")
    if v not in ("EDGE", "NO_EDGE", "NEGATIVE", "INSUFFICIENT", "INVALID"):
        out.append("code de verdict inconnu")
    elif v != "INVALID" and res.get("n_oos"):
        inf = res.get("inference") or {}

        def ci(k):
            return tuple((res.get(k) or {}).get("ci") or (None, None))

        expect = _verdict(res["n_oos"], res.get("n_taken"), ci("filtered"), ci("baseline"), ci("improvement"),
                          alpha if isinstance(alpha, float | int) else BASE_ALPHA,
                          n_units=inf.get("n_units"), n_units_taken=inf.get("n_units_taken"),
                          one_sided=inf.get("one_sided_bound"))["code"]
        if expect != v:
            out.append(f"verdict {v} incohérent avec les intervalles enregistrés ({expect})")
    elif v == "INVALID" and res.get("n_oos"):
        out.append("verdict INVALID avec des résultats hors échantillon")
    op = (body.get("final_model") or {}).get("opinion") or {}
    if op.get("opinion") not in (None, REFUSE, IGNORE, FAVOURABLE):
        out.append("avis inconnu")
    if op.get("opinion") in (FAVOURABLE, IGNORE):
        imp = (res.get("improvement") or {}).get("ci") or [None]
        sc, thr = op.get("score"), op.get("threshold")
        ok = (v == "EDGE" and op.get("role") == "nouveau" and imp[0] is not None and imp[0] > 0
              and isinstance(sc, float | int) and 0 <= sc <= 1 and isinstance(thr, float | int)
              and op.get("out_of_domain") is False)
        if not ok or (op["opinion"] == FAVOURABLE and sc < thr) or (op["opinion"] == IGNORE and sc >= thr):
            out.append("avis incompatible avec les conditions enregistrées")
    return out


def _verify(raw: bytes, expected_id: str) -> dict:
    try:
        doc = json.loads(raw)
    except ValueError as exc:
        raise StudyIntegrityError(f"Étude {expected_id} illisible : {exc}") from exc
    fmt = doc.get("format") if isinstance(doc, dict) else None
    if fmt in LEGACY_FORMATS:
        raise StudyIntegrityError(f"Étude {expected_id} au format {fmt} (v0.4.0) : non vérifiable, relancez-la.")
    if fmt != STUDY_FORMAT or not isinstance(doc.get("study"), dict):
        raise StudyIntegrityError(f"Étude {expected_id} : format inconnu.")
    body = doc["study"]
    try:
        canonical = _container(body)
    except ValueError as exc:
        raise StudyIntegrityError(f"Étude {expected_id} : contenu non canonique ({exc}).") from exc
    if hashlib.sha256(canonical_json(body)).hexdigest() != doc.get("sha256"):
        raise StudyIntegrityError(f"Étude {expected_id} altérée : empreinte SHA-256 différente.")
    if canonical != raw:
        raise StudyIntegrityError(f"Étude {expected_id} : octets non canoniques (fichier réécrit).")
    if body.get("study_id") != expected_id or _study_id(body.get("identity") or {}) != expected_id:
        raise StudyIntegrityError(f"Étude {expected_id} : identité incohérente avec son contenu.")
    problems = _semantic_problems(body)
    if problems:
        raise StudyIntegrityError(f"Étude {expected_id} incohérente : " + " ; ".join(problems))
    return body


def _publish(path: Path, body: dict) -> dict:
    """Atomic, create-only publication: an existing study file is verified, never replaced."""
    data = _container(body)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o444)
        try:
            os.link(tmp, path)  # fails if the file exists: no overwrite, ever
        except FileExistsError:
            pass
    finally:
        Path(tmp).unlink(missing_ok=True)
    return _verify(path.read_bytes(), path.stem)  # respond with what was PERSISTED and verified


def load_study(root: Path, study_id: str) -> dict | None:
    f = studies_dir(root) / f"{study_id}.json"
    if not f.exists():
        return None
    return _verify(f.read_bytes(), study_id)


def list_studies(root: Path) -> list[dict]:
    out = []
    for f in sorted(studies_dir(root).glob("*.json")):
        try:
            s = _verify(f.read_bytes(), f.stem)
        except StudyIntegrityError as exc:
            out.append({"study_id": f.stem, "integrity": "refusée", "integrity_error": str(exc),
                        "created_at": "", "dataset_id": None, "dataset_name": "Étude refusée (intégrité)",
                        "data_kind": None, "strategy_key": None, "verdict": None, "n_oos": None})
            continue
        out.append({"study_id": s["study_id"], "created_at": s["created_at"], "dataset_id": s["dataset"]["dataset_id"],
                    "dataset_name": s["dataset"]["name"], "data_kind": s["dataset"]["kind"],
                    "strategy_key": s["strategy"]["key"], "verdict": s["result"]["verdict"]["code"],
                    "n_oos": s["result"]["n_oos"], "integrity": "vérifiée"})
    return sorted(out, key=lambda s: s["created_at"], reverse=True)


def _legacy_count(root: Path, dataset_id: str, family: str) -> int:
    """v0.4.0 study files (unverifiable) still count as looks at the same history — conservatively."""
    n = 0
    for f in studies_dir(root).glob("*.json"):
        try:
            doc = json.loads(f.read_bytes())
        except ValueError:
            n += 1  # unreadable: assume it was a look
            continue
        if isinstance(doc, dict) and doc.get("format") in LEGACY_FORMATS:
            d = doc.get("dataset") or {}
            if d.get("dataset_id") == dataset_id or \
                    family_key(d.get("symbol"), d.get("timeframe"), d.get("kind"), d.get("dataset_id")) == family:
                n += 1
    return n


# ---------------------------------------------------------------- the study
def run_edge_study(cat, dataset_id: str, spec: StrategySpec, config: BacktestConfig,
                   settings: StudySettings | None = None) -> dict:
    settings = settings or StudySettings()
    settings.check()
    meta = cat.dataset_meta(dataset_id)
    if meta is None:
        raise ValueError(f"Jeu de données introuvable : {dataset_id}")
    check_supported(meta, spec, config)
    strategy = build_strategy(spec, config.strategy_params)
    kind = meta.kind.value if hasattr(meta.kind, "value") else str(meta.kind)
    identity = {"format": STUDY_FORMAT, "dataset": dataset_id, "strategy": spec.key, "spec_hash": spec.spec_hash(),
                "params": strategy.params, "costs": config.costs.model_dump(mode="json"),
                "contract": config.contract.model_dump(mode="json"),
                "hours": (config.trading_hours or spec.trading_hours).model_dump(mode="json"),
                "settings": asdict(settings), "code": research_code_hash()}
    identity = _sanitise(identity, "identity", [])
    study_id = _study_id(identity)
    root = Path(cat.root)
    path = studies_dir(root) / f"{study_id}.json"
    if path.exists():  # same inputs + same code = same result: verified, never recomputed into another file
        return _verify(path.read_bytes(), study_id)

    family = family_key(meta.symbol, meta.timeframe, kind, dataset_id)
    registry = StudyRegistry(studies_dir(root))
    entry = registry.reserve(study_id, dataset_id, family, legacy=lambda: _legacy_count(root, dataset_id, family))
    m, alpha = entry["m"], entry["alpha"]

    dataset = cat.load_dataset(dataset_id)
    bars = dataset.bars.reset_index(drop=True)
    sig = strategy.compute(bars)
    check_signal_contract(sig, len(bars))
    labels = label_signals(dataset, spec, config, sig, settings.horizon_bars)
    X = signal_features(bars, labels, config.costs.spread, config.costs.slippage,
                        config.costs.commission_per_lot_per_side, float(config.contract.contract_size or 0))
    ok = X.notna().all(axis=1).to_numpy()
    labels, X = labels[ok].reset_index(drop=True), X[ok].reset_index(drop=True)

    if len(labels) == 0:
        result = {"folds": [], "n_oos": 0, "verdict": _verdict(0, None, None, None, None, alpha)}
    else:
        result = evaluate_labelled(labels, X, settings, seed=int(study_id[:8], 16), alpha=alpha)

    r_all = labels["r"].to_numpy(float)
    final = {"status": "absent", "weights": []}
    if len(labels) >= settings.min_train and len(set((r_all > 0).tolist())) == 2:
        final = _final_weights(X, r_all, settings)
    if result["verdict"]["code"] == "INVALID":
        opinion = _refusal(["étude invalide : aucun avis"], role=None, signal_time=None)
    else:
        try:
            opinion = _prospective_opinion(dataset, bars, sig, labels, X, spec, config, settings, result)
        except _MODEL_FAILURES as exc:  # never a favourable answer by accident
            opinion = _refusal([f"avis impossible ({type(exc).__name__})"], role=None, signal_time=None)
    final = {**final, "opinion": opinion}

    issues: list[str] = []
    body = _sanitise({
        "study_id": study_id, "identity": identity,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "software_version": __version__, "engine_version": ENGINE_VERSION, "code_hash": identity["code"],
        "method_status": METHOD_STATUS, "execution_mode": "simulation",
        "scope": "signaux candidats simulés un par un — pas une performance de portefeuille exécutable",
        "dataset": {"dataset_id": dataset_id, "name": meta.name, "kind": kind, "symbol": meta.symbol,
                    "timeframe": meta.timeframe, "start": str(meta.start), "end": str(meta.end),
                    "raw_sha256": getattr(meta, "raw_sha256", None)},
        "strategy": {"key": spec.key, "name": spec.name, "params": strategy.params, "illustrative": spec.illustrative},
        "settings": asdict(settings), "costs": identity["costs"],
        "feature_set": FEATURE_SET, "features": [{"feature": f, "label": FEATURE_LABELS_FR[f]} for f in FEATURES],
        "signals": {"candidates": int((sig["signal"] != 0).sum()), "labelled": int(len(labels)),
                    "exit_reasons": {str(k): int(v) for k, v in labels["exit_reason"].value_counts().items()}},
        "multiple_testing": {"family": family, "studies_in_family": m, "alpha": alpha,
                             "rule": entry["rule"], "registry_entry": entry["hash"]},
        "result": result, "final_model": final,
    }, "study", issues)
    body["numerical_issues"] = issues
    return _publish(path, body)
