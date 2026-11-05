"""Small, dependency-free statistics for research (numpy only — the dependency lock stays unchanged).

* ``LogisticModel``: L2-regularised logistic regression fitted by Newton/IRLS on standardised features
  (the scaler is fitted on the training rows only).
* ``auc``: Mann-Whitney AUC (ties counted half). ``brier``: mean squared error of probabilities.
* ``block_bootstrap_indices``: moving-block bootstrap — signals are serially dependent (they cluster in
  time), so resampling single signals would understate the uncertainty.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class LogisticModel:
    l2: float = 1.0
    max_iter: int = 50
    mean_: np.ndarray | None = None
    scale_: np.ndarray | None = None
    coef_: np.ndarray | None = None  # [intercept, w_1..w_p] in standardised units

    def fit(self, X: np.ndarray, y: np.ndarray) -> LogisticModel:
        X = np.asarray(X, float)
        y = np.asarray(y, float)
        if len(X) == 0 or not np.isfinite(X).all():
            raise ValueError("données d'entraînement vides ou non finies")
        self.mean_ = X.mean(axis=0)
        sd = X.std(axis=0)
        self.scale_ = np.where(sd > 1e-12, sd, 1.0)
        Z = np.c_[np.ones(len(X)), (X - self.mean_) / self.scale_]
        w = np.zeros(Z.shape[1])
        penalty = np.full(Z.shape[1], self.l2)
        penalty[0] = 0.0  # the intercept is not shrunk
        for _ in range(self.max_iter):
            p = 1.0 / (1.0 + np.exp(-np.clip(Z @ w, -35, 35)))
            grad = Z.T @ (p - y) + penalty * w
            hess = (Z * (p * (1 - p))[:, None]).T @ Z + np.diag(penalty + 1e-9)
            step = np.linalg.solve(hess, grad)
            w -= step
            if np.max(np.abs(step)) < 1e-8:
                break
        self.coef_ = w
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self.coef_ is None:
            raise RuntimeError("modèle non entraîné")
        Z = np.c_[np.ones(len(X)), (np.asarray(X, float) - self.mean_) / self.scale_]
        return 1.0 / (1.0 + np.exp(-np.clip(Z @ self.coef_, -35, 35)))


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
