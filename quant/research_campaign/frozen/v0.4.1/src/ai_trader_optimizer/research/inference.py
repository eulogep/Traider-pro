"""Uncertainty of the out-of-sample result (bootstrap) and the decision rule of the verdict.

Isolated so that the statistical method changes only through the pre-registered campaign
(quant/research_campaign/PROTOCOL.md). Two methods are implemented; ``ACTIVE`` selects one.

``legacy-index-blocks`` (v0.4.0): moving blocks of length round(2·n^(1/3)) over the INDEX of the
out-of-sample signals; percentile interval at level 1 − alpha; EDGE when its lower bound is > 0, i.e. a
one-sided test at alpha / 2. Ignores how long outcomes overlap in time.

``overlap-clusters-pw`` (protocol H1 + H2, written before the "before" results were read):
1. inference UNITS = overlap clusters: OOS signals sorted by entry; a signal opens a new unit when it
   enters at or after the instant the outcomes of every earlier signal of the current unit are AVAILABLE
   (close of their exit bar): the outcome windows then touch but do not overlap. Under a martingale-difference null, distinct units are uncorrelated;
2. circular moving-block bootstrap over the SEQUENCE of units; block length chosen automatically by
   Politis & White (2004) with the Patton, Politis & White (2009) correction (flat-top lag window,
   M chosen by the White rule), bounded to [1, min(3·√n, n/3)] — residual dependence between units
   (regimes) is absorbed by the blocks;
3. statistics aggregated per unit (sums of R and of taken signals): the filtered mean is a ratio
   estimator; the AUC uses the same draws, expanded to the signals of the drawn units;
4. minimum sample in INDEPENDENT units: ≥ 100 OOS units and ≥ 50 units with a taken signal;
5. decision: EDGE when the alpha-quantile of the bootstrap distribution of the filtered mean is > 0
   (one-sided test at alpha, alpha from the summable spending rule of ``registry.py``); reported
   intervals stay two-sided at 1 − alpha.
"""

from __future__ import annotations

import math

import numpy as np

from .stats import block_bootstrap_indices

LEGACY = "legacy-index-blocks"
CLUSTERS = "overlap-clusters-pw"
ACTIVE = CLUSTERS  # protocol H1, activated after the "before" diagnosis (C1: 17.6 % EDGE under a null)
METHOD = ACTIVE
MIN_OOS_SIGNALS = 100
MIN_UNITS = 100
MIN_UNITS_TAKEN = 50
INSUFFICIENT_TEXT = (f"Moins de {MIN_OOS_SIGNALS} signaux (ou unités indépendantes) hors échantillon : aucune "
                     "conclusion possible. Importez un historique plus long.")


def lower_upper(samples: np.ndarray, alpha: float) -> tuple[float | None, float | None]:
    s = np.asarray(samples, float)
    s = s[np.isfinite(s)]
    if len(s) == 0:
        return None, None
    return float(np.quantile(s, alpha / 2)), float(np.quantile(s, 1 - alpha / 2))


def insufficient(n_oos: int, n_taken, n_units=None, n_units_taken=None) -> bool:
    if n_oos < MIN_OOS_SIGNALS or (n_taken or 0) < MIN_OOS_SIGNALS // 2:
        return True
    if n_units is not None and (n_units < MIN_UNITS or (n_units_taken or 0) < MIN_UNITS_TAKEN):
        return True
    return False


def rejects(filt_ci, one_sided_bound=None) -> bool:
    """EDGE decision. Legacy: lower bound of the two-sided interval > 0. Cluster method: the stored
    one-sided bound (alpha-quantile) > 0 — passed explicitly by the caller."""
    if one_sided_bound is not None:
        return one_sided_bound > 0
    return filt_ci[0] is not None and filt_ci[0] > 0


# ---------------------------------------------------------------- units and block length
def overlap_units(t_entry: np.ndarray, t_avail: np.ndarray) -> np.ndarray:
    """Unit id of each signal (signals already sorted by entry time)."""
    n = len(t_entry)
    uid = np.zeros(n, dtype=np.int64)
    cur, known_at = 0, -np.inf
    for i in range(n):
        if i > 0 and t_entry[i] >= known_at:
            cur += 1
            known_at = -np.inf
        uid[i] = cur
        known_at = max(known_at, t_avail[i])
    return uid


def _flat_top(t: np.ndarray) -> np.ndarray:
    a = np.abs(t)
    return np.where(a <= 0.5, 1.0, np.where(a <= 1.0, 2.0 * (1.0 - a), 0.0))


def politis_white_block(x: np.ndarray) -> int:
    """Optimal block length of the circular block bootstrap for the mean of ``x`` (PW 2004 / PPW 2009)."""
    x = np.asarray(x, float)
    n = len(x)
    if n < 8:
        return 1
    b_max = max(1, int(math.ceil(min(3 * math.sqrt(n), n / 3))))
    xc = x - x.mean()
    var = float(np.dot(xc, xc) / n)
    if var <= 0:
        return 1
    k_n = max(5, int(math.ceil(math.sqrt(math.log10(n)))))
    m_max = int(math.ceil(math.sqrt(n))) + k_n
    m_max = min(m_max, n - 1)
    acov = np.array([np.dot(xc[: n - k], xc[k:]) / n for k in range(m_max + 1)])
    rho = acov[1:] / acov[0]
    thr = 2.0 * math.sqrt(math.log10(n) / n)
    insignificant = np.abs(rho) < thr
    m_hat = None
    for m in range(0, max(1, m_max - k_n + 1)):
        if insignificant[m: m + k_n].all():
            m_hat = m
            break
    if m_hat is None:
        m_hat = m_max
    M = min(2 * max(m_hat, 1), m_max)
    k = np.arange(-M, M + 1)
    lam = _flat_top(k / M)
    R = acov[np.abs(k)]
    G = float(np.sum(lam * np.abs(k) * R))
    g0 = float(np.sum(lam * R))
    if g0 <= 0 or G == 0:
        return 1
    d_cb = (4.0 / 3.0) * g0 ** 2
    b = (2.0 * G ** 2 / d_cb) ** (1.0 / 3.0) * n ** (1.0 / 3.0)
    return int(min(max(1, round(b)), b_max))


# ---------------------------------------------------------------- bootstrap
def bootstrap(t_entry: np.ndarray, t_avail: np.ndarray, r: np.ndarray, take: np.ndarray, n_boot: int,
              rng: np.random.Generator, alpha: float, method: str | None = None) -> dict:
    """Bootstrap distribution of the baseline mean, the filtered mean and their difference (OOS signals,
    already in time order). ``draws`` are signal-index arrays, so the AUC uses the same resamples."""
    method = method or ACTIVE
    if method == LEGACY:
        B = block_bootstrap_indices(len(r), n_boot, rng)
        Rb, Tb = r[B], take[B]
        base_b = Rb.mean(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            filt_b = (Rb * Tb).sum(axis=1) / Tb.sum(axis=1)
        diff_b = filt_b - base_b
        return {"method": LEGACY, "draws": B, "n_units": None, "n_units_taken": None, "block_length": None,
                "decision": "la borne basse de l'intervalle bilatéral de la moyenne filtrée est > 0 (test unilatéral à alpha/2)",
                "one_sided_bound": None,
                "baseline_ci": lower_upper(base_b, alpha), "filtered_ci": lower_upper(filt_b, alpha),
                "improvement_ci": lower_upper(diff_b, alpha),
                "baseline_share_positive": float(np.mean(base_b > 0)),
                "filtered_share_positive": float(np.mean(filt_b > 0))}
    if method != CLUSTERS:
        raise ValueError(f"méthode d'inférence inconnue : {method}")
    uid = overlap_units(t_entry, t_avail)
    nu = int(uid[-1]) + 1 if len(uid) else 0
    S = np.bincount(uid, weights=r, minlength=nu)
    N = np.bincount(uid, minlength=nu).astype(float)
    ST = np.bincount(uid, weights=r * take, minlength=nu)
    NT = np.bincount(uid, weights=take.astype(float), minlength=nu)
    theta = ST.sum() / NT.sum() if NT.sum() > 0 else S.sum() / N.sum()
    z = (ST - theta * NT) if NT.sum() > 0 else (S - theta * N)
    b = politis_white_block(z)
    U = block_bootstrap_indices(nu, n_boot, rng, block=b)
    with np.errstate(invalid="ignore", divide="ignore"):
        base_b = S[U].sum(axis=1) / N[U].sum(axis=1)
        filt_b = ST[U].sum(axis=1) / NT[U].sum(axis=1)
    diff_b = filt_b - base_b
    starts = np.r_[0, np.cumsum(N.astype(int))[:-1]]
    sizes = N.astype(int)
    draws = [np.concatenate([np.arange(starts[u], starts[u] + sizes[u]) for u in row]) for row in U[:400]]
    fb = filt_b[np.isfinite(filt_b)]
    one_sided = float(np.quantile(fb, alpha)) if len(fb) else None
    return {"method": CLUSTERS, "draws": draws, "n_units": nu, "n_units_taken": int((NT > 0).sum()),
            "block_length": int(b), "mean_signals_per_unit": float(N.mean()) if nu else None,
            "decision": "le quantile unilatéral alpha de la distribution bootstrap de la moyenne filtrée est > 0",
            "one_sided_bound": one_sided,
            "baseline_ci": lower_upper(base_b, alpha), "filtered_ci": lower_upper(filt_b, alpha),
            "improvement_ci": lower_upper(diff_b, alpha),
            "baseline_share_positive": float(np.mean(base_b > 0)),
            "filtered_share_positive": float(np.mean(filt_b[np.isfinite(filt_b)] > 0)) if len(fb) else None}
