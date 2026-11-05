"""Small, dependency-free statistics for research (numpy only — the dependency lock stays unchanged).

* ``LogisticModel``: L2-regularised logistic regression fitted by Newton/IRLS on standardised features
  (the scaler is fitted on the training rows only).
* ``auc``: Mann-Whitney AUC (ties counted half). ``brier``: mean squared error of probabilities.
* ``block_bootstrap_indices``: moving-block bootstrap — signals are serially dependent (they cluster in
  time), so resampling single signals would understate the uncertainty.

Numerical safety (v0.4.1, audit B04-3): every fit and every prediction is checked; a non-finite value, a
probability outside [0, 1], a singular system or a fit that did not converge raises ``ModelError``.
Callers must turn that into a REFUSAL — an invalid model is never a neutral or a favourable answer.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


class ModelError(ArithmeticError):
    """The model could not be fitted or evaluated reliably (non-finite numbers, divergence, bad input)."""


def _require_finite(name: str, a: np.ndarray) -> None:
    if not np.isfinite(a).all():
        raise ModelError(f"{name} : valeurs non finies")


@dataclass
class LogisticModel:
    l2: float = 1.0
    max_iter: int = 50
    mean_: np.ndarray | None = None
    scale_: np.ndarray | None = None
    coef_: np.ndarray | None = None  # [intercept, w_1..w_p] in standardised units
    converged_: bool = False
    n_iter_: int = 0
    train_min_: np.ndarray | None = None  # domain of the training features (standardised units)
    train_max_: np.ndarray | None = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> LogisticModel:
        X = np.asarray(X, float)
        y = np.asarray(y, float)
        if X.ndim != 2 or len(X) == 0 or len(X) != len(y):
            raise ModelError("données d'entraînement vides ou de formes incohérentes")
        _require_finite("données d'entraînement", X)
        if not np.isin(y, (0.0, 1.0)).all() or len(np.unique(y)) < 2:
            raise ModelError("étiquettes d'entraînement invalides (deux classes 0/1 requises)")
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            try:
                mean = X.mean(axis=0)
                sd = X.std(axis=0)
            except FloatingPointError as exc:
                raise ModelError(f"standardisation impossible : {exc}") from exc
        _require_finite("moyennes d'entraînement", mean)
        _require_finite("écarts-types d'entraînement", sd)
        self.mean_ = mean
        self.scale_ = np.where(sd > 1e-12, sd, 1.0)
        Zx = (X - self.mean_) / self.scale_
        _require_finite("variables standardisées", Zx)
        self.train_min_, self.train_max_ = Zx.min(axis=0), Zx.max(axis=0)
        Z = np.c_[np.ones(len(X)), Zx]
        w = np.zeros(Z.shape[1])
        penalty = np.full(Z.shape[1], self.l2)
        penalty[0] = 0.0  # the intercept is not shrunk
        self.converged_ = False
        for it in range(self.max_iter):
            p = 1.0 / (1.0 + np.exp(-np.clip(Z @ w, -35, 35)))
            grad = Z.T @ (p - y) + penalty * w
            hess = (Z * (p * (1 - p))[:, None]).T @ Z + np.diag(penalty + 1e-9)
            try:
                step = np.linalg.solve(hess, grad)
            except np.linalg.LinAlgError as exc:
                raise ModelError(f"système singulier pendant l'ajustement : {exc}") from exc
            _require_finite("pas de Newton", step)
            w = w - step
            _require_finite("coefficients", w)
            self.n_iter_ = it + 1
            if np.max(np.abs(step)) < 1e-8:
                self.converged_ = True
                break
        if not self.converged_:
            raise ModelError(f"l'ajustement n'a pas convergé en {self.max_iter} itérations")
        self.coef_ = w
        return self

    def standardise(self, X: np.ndarray) -> np.ndarray:
        if self.coef_ is None or self.mean_ is None:
            raise ModelError("modèle non entraîné")
        X = np.asarray(X, float)
        if X.ndim != 2 or X.shape[1] != len(self.mean_):
            raise ModelError("variables de forme incohérente avec le modèle")
        _require_finite("variables à évaluer", X)
        Zx = (X - self.mean_) / self.scale_
        _require_finite("variables standardisées", Zx)
        return Zx

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        Z = np.c_[np.ones(len(X)), self.standardise(X)]
        _require_finite("coefficients", self.coef_)
        p = 1.0 / (1.0 + np.exp(-np.clip(Z @ self.coef_, -35, 35)))
        if not (np.isfinite(p).all() and (p >= 0).all() and (p <= 1).all()):
            raise ModelError("probabilité invalide")
        return p

    def out_of_domain(self, X: np.ndarray, margin: float = 0.5) -> np.ndarray:
        """True where a row lies outside the training range of ANY feature (by more than ``margin`` standard
        deviations): the model never saw such a case, its score is an extrapolation."""
        Zx = self.standardise(X)
        return ((Zx < self.train_min_ - margin) | (Zx > self.train_max_ + margin)).any(axis=1)


def auc(y: np.ndarray, p: np.ndarray) -> float | None:
    y = np.asarray(y, bool)
    pos, neg = int(y.sum()), int((~y).sum())
    if pos == 0 or neg == 0:
        return None
    order = np.argsort(p, kind="mergesort")
    ranks = np.empty(len(p))
    sp = np.asarray(p)[order]
    i = 0
    while i < len(sp):  # average ranks for ties
        j = i
        while j + 1 < len(sp) and sp[j + 1] == sp[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return float((ranks[y].sum() - pos * (pos + 1) / 2) / (pos * neg))


def brier(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def block_length(n: int) -> int:
    return max(1, min(n, int(round(n ** (1 / 3) * 2))))


def block_bootstrap_indices(n: int, n_boot: int, rng: np.random.Generator, block: int | None = None) -> np.ndarray:
    """(n_boot, n) index matrix built from contiguous blocks (circular), preserving local dependence."""
    if n <= 0:
        return np.zeros((n_boot, 0), dtype=int)
    b = block or block_length(n)
    n_blocks = -(-n // b)
    starts = rng.integers(0, n, size=(n_boot, n_blocks))
    idx = (starts[:, :, None] + np.arange(b)[None, None, :]) % n
    return idx.reshape(n_boot, -1)[:, :n]


def interval(samples: np.ndarray, alpha: float) -> tuple[float | None, float | None]:
    s = np.asarray(samples, float)
    s = s[np.isfinite(s)]
    if len(s) == 0:
        return None, None
    return float(np.quantile(s, alpha / 2)), float(np.quantile(s, 1 - alpha / 2))


def calibration_bins(y: np.ndarray, p: np.ndarray, n_bins: int = 5) -> list[dict]:
    """Equal-count bins of predicted probability: mean prediction vs observed frequency."""
    if len(p) == 0:
        return []
    order = np.argsort(p, kind="mergesort")
    out = []
    for chunk in np.array_split(order, min(n_bins, len(p))):
        if len(chunk):
            out.append({"n": int(len(chunk)), "mean_predicted": float(np.mean(p[chunk])),
                        "observed_rate": float(np.mean(np.asarray(y, float)[chunk]))})
    return out
