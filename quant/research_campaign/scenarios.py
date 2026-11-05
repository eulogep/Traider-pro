"""Scenario generators for the v0.4 → v0.4.1 statistical campaign (see PROTOCOL.md).

Independent of the method under test: this module only builds prices and signals. It uses the application's
public data/strategy primitives (``dataset_from_frame``, the baseline spec, ``build_strategy``), never the
research module, so the same scenarios can be fed to the old and the new inference code.

Exact null by construction
--------------------------
Prices follow a symmetric LATTICE random walk: every elementary step is ±DELTA (DELTA = 0.125, exactly
representable in binary floating point), price = BASE + DELTA × integer. The number of steps per minute
(n_t) sets the volatility; it may vary in time (volatility regimes) without breaking the martingale property.
Bars are contiguous (open = previous close) and high/low are the true extremes of the path inside the bar.
Stop and target distances are integer multiples of DELTA, so a barrier is hit EXACTLY at its level (no
overshoot). With zero costs, the labelled R of every signal therefore has expectation exactly 0
(optional stopping of a bounded martingale), whatever the direction rule, as long as it is causal.

Two documented exceptions, both measured by pooling in the campaign instead of being assumed:
* when stop and target are both touched inside the same minute, the labeller assumes "stop first"
  (engine convention) — a small PESSIMISTIC bias (it can only lower false positives);
* the real baseline strategy computes ATR stops that are NOT lattice multiples (overshoot of < DELTA).

Correlated-outcome nulls add a hidden drift regime M_t ∈ {−1, +1} (step probability 0.5 + EPS × M_t) and
draw signal directions from an INDEPENDENT regime D_t; with symmetric barriers (rr = 1) the reflection
symmetry of the walk keeps E[R] = 0 exactly while outcomes become serially correlated.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from ai_trader_optimizer.data.validation import dataset_from_frame
from ai_trader_optimizer.safety import DataKind
from ai_trader_optimizer.strategies import load_catalog
from ai_trader_optimizer.strategies.registry import build_strategy

DELTA = 0.125
BASE_PRICE = 3900.0
BASE_STEPS = 40  # 0.125 × √40 ≈ 0.79 price units per minute (≈ the demo generator's 0.8)
START = "2026-01-05T00:00:00Z"  # a Monday
SESSION = (12 * 60, 17 * 60)  # baseline spec: 12:00-17:00 UTC, Mon-Fri


@dataclass(frozen=True)
class Scenario:
    key: str
    family: str  # "codex" | "null" | "e2e_null" | "search" | "power"
    description: str
    days: int = 120  # calendar days (weekends removed)
    vol: str = "const"  # const | switch | stoch
    drift: str = "none"  # none | regime
    drift_duration_min: float = 120.0
    eps: float = 0.01
    signals: str = "rand"  # rand | burst | rule | baseline
    density: float = 0.05  # expected signals per in-session bar
    burst_len: int = 1
    rr: float = 1.5
    q: float = 0.5  # P(direction == drift regime) ; 0.5 = no information (null)
    q_hours: tuple[int, int] | None = None  # informative only inside these UTC hours (conditional edge)
    dir_duration_min: float = 0.0  # >0: directions follow an independent persistent regime D_t
    # function-level (Codex) scenarios
    codex_n: int = 0
    codex_cluster: int = 1
    codex_p: float = 0.4
    extra: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["q_hours"] = list(self.q_hours) if self.q_hours else None
        return d


def _markov_sign(rng: np.random.Generator, n: int, mean_duration: float) -> np.ndarray:
    """±1 regime that flips with probability 1/mean_duration per minute (starts at random)."""
    flips = rng.random(n) < (1.0 / mean_duration)
    flips[0] = False
    s0 = 1 if rng.random() < 0.5 else -1
    return s0 * np.where(np.cumsum(flips) % 2 == 0, 1, -1).astype(np.int8)


def _steps_per_minute(rng: np.random.Generator, n: int, vol: str) -> np.ndarray:
    if vol == "const":
        return np.full(n, BASE_STEPS, dtype=np.int64)
    if vol == "switch":  # 2-state Markov volatility: calm (σ/2) vs. stressed (2σ), mean duration 1 day
        hi = _markov_sign(rng, n, 1440.0) > 0
        return np.where(hi, BASE_STEPS * 4, BASE_STEPS // 4).astype(np.int64)
    if vol == "stoch":  # log-volatility AR(1), half-life ≈ 8 h, stationary sd 0.9 on log(n)
        phi = np.exp(-np.log(2) / 480.0)
        e = rng.normal(0, 0.9 * np.sqrt(1 - phi**2), n)
        h = np.empty(n)
        h[0] = rng.normal(0, 0.9)
        for i in range(1, n):  # small loop (n ≈ 1.2e5) — fine
            h[i] = phi * h[i - 1] + e[i]
        return np.maximum(1, np.round(BASE_STEPS * np.exp(h))).astype(np.int64)
    raise ValueError(vol)


def lattice_bars(sc: Scenario, rng: np.random.Generator) -> tuple[pd.DataFrame, np.ndarray]:
    """M1 bars of a lattice walk (weekdays only, 24 h a day) and the drift regime per minute."""
    idx = pd.date_range(START, periods=sc.days * 1440, freq="min")
    idx = idx[idx.dayofweek < 5]
    n = len(idx)
    n_t = _steps_per_minute(rng, n, sc.vol)
    m_t = _markov_sign(rng, n, sc.drift_duration_min) if sc.drift == "regime" else np.zeros(n, np.int8)
    p_up = 0.5 + sc.eps * np.repeat(m_t.astype(float), n_t)
    steps = np.where(rng.random(int(n_t.sum())) < p_up, 1, -1).astype(np.int32)
    path = np.cumsum(steps, dtype=np.int64)
    ends = np.cumsum(n_t) - 1
    starts = ends - n_t + 1
    close = path[ends]
    open_ = np.r_[0, close[:-1]]
    high = np.maximum(open_, np.maximum.reduceat(path, starts))
    low = np.minimum(open_, np.minimum.reduceat(path, starts))
    to_px = lambda a: BASE_PRICE + DELTA * a.astype(float)  # noqa: E731 — exact in binary
    frame = pd.DataFrame({"timestamp": idx, "open": to_px(open_), "high": to_px(high), "low": to_px(low),
                          "close": to_px(close)})
    return frame, m_t


def make_dataset(sc: Scenario, frame: pd.DataFrame, seed_tag: str):
    return dataset_from_frame(frame, name=f"CAMPAGNE {sc.key} {seed_tag}", symbol="XAUUSD-NULL",
                              source_label="campagne v0.4.1 — marche aléatoire sur réseau (nul exact)",
                              kind=DataKind.SYNTHETIC, notes="Données fictives de validation statistique.")


def _atr_lattice(frame: pd.DataFrame, rr: float) -> tuple[np.ndarray, np.ndarray]:
    """Stop = DELTA × max(4, round(1.5 × ATR14 / DELTA)) on CLOSED bars; target = DELTA × round(rr × k)."""
    h, lo, c = frame["high"].to_numpy(), frame["low"].to_numpy(), frame["close"].to_numpy()
    prev = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - lo, np.maximum(np.abs(h - prev), np.abs(lo - prev)))
    atr = pd.Series(tr).rolling(14, min_periods=14).mean().to_numpy()
    k = np.where(np.isfinite(atr), np.maximum(4, np.round(1.5 * atr / DELTA)), np.nan)
    return DELTA * k, DELTA * np.round(rr * k)


def make_signals(sc: Scenario, frame: pd.DataFrame, m_t: np.ndarray, rng: np.random.Generator) -> pd.DataFrame:
    """Causal signal frame in the engine's contract (signal, reason, sl_distance, tp_distance)."""
    n = len(frame)
    ts = frame["timestamp"]
    minute = (ts.dt.hour * 60 + ts.dt.minute).to_numpy()
    session = (minute >= SESSION[0]) & (minute < SESSION[1] - 1)  # entry bar (next one) also in session
    sl, tp = _atr_lattice(frame, sc.rr)
    fire = np.zeros(n, bool)
    if sc.signals == "rand":
        fire = session & (rng.random(n) < sc.density)
    elif sc.signals == "burst":  # bursts of burst_len consecutive in-session bars, one direction each
        starts = np.flatnonzero(session & (rng.random(n) < sc.density / sc.burst_len))
        burst_id = np.full(n, -1)
        for b, s in enumerate(starts):
            burst_id[s:s + sc.burst_len] = np.where(burst_id[s:s + sc.burst_len] < 0, b, burst_id[s:s + sc.burst_len])
        fire = session & (burst_id >= 0)
    elif sc.signals == "rule":  # momentum rule: |15-bar move| > 2 ATR, causal, naturally bursty
        c = frame["close"].to_numpy()
        mom = c - np.r_[np.full(15, np.nan), c[:-15]]
        with np.errstate(invalid="ignore"):
            fire = session & np.isfinite(mom) & (np.abs(mom) > 2 * sl / 1.5)
    else:
        raise ValueError(sc.signals)
    fire &= np.isfinite(sl)
    # direction: informative (drift regime with prob q), independent persistent regime, or fair coin
    if sc.signals == "rule":
        base_dir = np.sign(np.nan_to_num(mom)).astype(int)
    elif sc.dir_duration_min > 0:
        base_dir = _markov_sign(rng, n, sc.dir_duration_min).astype(int)
    else:
        base_dir = np.where(rng.random(n) < 0.5, 1, -1)
    aligned = rng.random(n) < sc.q
    regime = m_t.astype(int)
    if sc.signals == "burst" and len(starts):  # one direction (and one alignment draw) per burst
        bid = np.clip(burst_id, 0, None)
        bdir = np.where(rng.random(len(starts)) < 0.5, 1, -1)
        balign = rng.random(len(starts)) < sc.q
        base_dir = np.where(burst_id >= 0, bdir[bid], base_dir)
        aligned = np.where(burst_id >= 0, balign[bid], aligned)
        regime = np.where(burst_id >= 0, regime[starts][bid], regime)  # regime at the burst's first bar
    direction = base_dir
    if sc.q != 0.5:
        informative = np.ones(n, bool)
        if sc.q_hours:
            hr = ts.dt.hour.to_numpy()
            informative = (hr >= sc.q_hours[0]) & (hr < sc.q_hours[1])
        direction = np.where(informative, np.where(aligned, regime, -regime), base_dir)
    sig = np.where(fire, direction, 0).astype(int)
    return pd.DataFrame({"signal": sig, "reason": np.where(sig != 0, "campagne", ""),
                         "sl_distance": np.where(sig != 0, sl, np.nan), "tp_distance": np.where(sig != 0, tp, np.nan)})


def baseline_spec():
    return [s for s in load_catalog().specs.values() if s.status == "active" and s.key.startswith("baseline.")][0]


def baseline_signals(frame: pd.DataFrame, params: dict | None = None) -> pd.DataFrame:
    spec = baseline_spec()
    return build_strategy(spec, params or {}).compute(frame.reset_index(drop=True))


def codex_signals(sc: Scenario, rng: np.random.Generator):
    """Exact generator of Codex's statistical_probes.py::experiment (function-level null)."""
    import math
    n, cluster, p = sc.codex_n, sc.codex_cluster, sc.codex_p
    t = np.arange(n, dtype=np.int64) * 60 * 10**9
    X = rng.normal(size=(n, 4))
    wins = np.repeat(rng.random(math.ceil(n / cluster)) < p, cluster)[:n]
    r = np.where(wins, 1.5, -1.0)
    end = np.minimum((np.arange(n) // cluster + 1) * cluster, n) * 60 * 10**9
    return t, end, X, r


def frame_sha256(frame: pd.DataFrame) -> str:
    h = hashlib.sha256()
    for col in ("open", "high", "low", "close"):
        h.update(np.ascontiguousarray(frame[col].to_numpy(float)).tobytes())
    h.update(frame["timestamp"].astype("int64").to_numpy().tobytes())
    return h.hexdigest()


# --------------------------------------------------------------------------------------------- registry
# Pre-registered before any verdict was observed (see PROTOCOL.md). Do not edit after the "before" phase.
SEARCH_VARIANTS = [  # a researcher "fishing" on ONE history: 10 analyses of the same data
    {"params": {}, "horizon_bars": 240},
    {"params": {"ema_fast": 10, "ema_slow": 30}, "horizon_bars": 240},
    {"params": {"ema_fast": 30, "ema_slow": 100}, "horizon_bars": 240},
    {"params": {"sl_atr_mult": 1.0}, "horizon_bars": 240},
    {"params": {"sl_atr_mult": 2.5}, "horizon_bars": 240},
    {"params": {"rr": 1.0}, "horizon_bars": 240},
    {"params": {"rr": 2.5}, "horizon_bars": 240},
    {"params": {}, "horizon_bars": 60},
    {"params": {}, "horizon_bars": 30},
    {"params": {"ema_fast": 10, "ema_slow": 30, "rr": 2.5}, "horizon_bars": 60},
]

SCENARIOS: list[Scenario] = [
    # Codex's function-level populations, reproduced exactly (signals given, not prices)
    Scenario("C0_codex_indep", "codex", "Codex : Bernoulli p=0,40 indépendant, 1 500 signaux", codex_n=1500),
    Scenario("C1_codex_cluster100", "codex", "Codex : résultat commun par groupe de 100, 3 000 signaux",
             codex_n=3000, codex_cluster=100),
    # Full chain (prices → signals → labels → features → walk-forward → verdict), exact nulls
    Scenario("N1_rand_sparse", "null", "Vol. constante, signaux aléatoires rares (ρ=0,01)", density=0.01),
    Scenario("N2_rand_mid", "null", "Vol. constante, signaux aléatoires (ρ=0,05)", density=0.05),
    Scenario("N3_rand_dense", "null", "Vol. constante, signaux aléatoires denses (ρ=0,2)", density=0.2),
    Scenario("N4_burst10", "null", "Rafales de 10 signaux consécutifs même sens", signals="burst", density=0.05,
             burst_len=10),
    Scenario("N5_burst60", "null", "Rafales de 60 signaux consécutifs même sens", signals="burst", density=0.1,
             burst_len=60),
    Scenario("N6_rule_momentum", "null", "Règle causale de momentum (rafales naturelles)", signals="rule"),
    Scenario("N7_volswitch", "null", "Régimes de volatilité calme/stress (Markov, ~1 j)", vol="switch"),
    Scenario("N8_stochvol", "null", "Volatilité stochastique (log-AR(1), demi-vie 8 h)", vol="stoch"),
    Scenario("N9_stochvol_burst30", "null", "Vol. stochastique + rafales de 30", vol="stoch", signals="burst",
             density=0.1, burst_len=30),
    Scenario("N10_corr_2h", "null", "Résultats corrélés : régimes de tendance et de sens indépendants (~2 h)",
             drift="regime", drift_duration_min=120, dir_duration_min=120, rr=1.0),
    Scenario("N11_corr_1d", "null", "Résultats corrélés : régimes ~1 jour (mémoire longue)", drift="regime",
             drift_duration_min=1440, dir_duration_min=1440, rr=1.0),
    # End-to-end through run_edge_study (catalogue, real baseline strategy, persistence, alpha rule)
    Scenario("E1_e2e_baseline_stochvol", "e2e_null", "Chaîne applicative complète, stratégie baseline réelle, "
             "vol. stochastique, coûts nuls", vol="stoch", signals="baseline"),
    # Repeated analyses of the same history (multiplicity)
    Scenario("S1_search_10_variants", "search", "10 analyses du même historique nul (paramètres/horizons)",
             vol="stoch", signals="baseline"),
    # Power: informative directions (edge injected through the drift regime), effect = pooled true mean R
    Scenario("P1_edge_005", "power", "Avantage injecté ≈ +0,05 R, régimes 60 min", drift="regime",
             drift_duration_min=60, rr=1.0, extra={"target_r": 0.05}),
    Scenario("P2_edge_010", "power", "Avantage injecté ≈ +0,10 R, régimes 60 min", drift="regime",
             drift_duration_min=60, rr=1.0, extra={"target_r": 0.10}),
    Scenario("P3_edge_020", "power", "Avantage injecté ≈ +0,20 R, régimes 60 min", drift="regime",
             drift_duration_min=60, rr=1.0, extra={"target_r": 0.20}),
    Scenario("P4_edge_010_burst20", "power", "≈ +0,10 R, signaux en rafales de 20", drift="regime",
             drift_duration_min=60, rr=1.0, signals="burst", density=0.05, burst_len=20, extra={"target_r": 0.10}),
    Scenario("P5_edge_020_stochvol", "power", "≈ +0,20 R, volatilité stochastique", drift="regime",
             drift_duration_min=60, rr=1.0, vol="stoch", extra={"target_r": 0.20}),
    Scenario("P6_edge_010_sparse", "power", "≈ +0,10 R, signaux rares (ρ=0,01)", drift="regime",
             drift_duration_min=60, rr=1.0, density=0.01, extra={"target_r": 0.10}),
    Scenario("P7_conditional_hours", "power", "Avantage conditionnel (12-14 h UTC seulement) — filtre utile",
             drift="regime", drift_duration_min=60, rr=1.0, q_hours=(12, 14), extra={"target_r_informative": 0.30}),
]
BY_KEY = {s.key: s for s in SCENARIOS}
