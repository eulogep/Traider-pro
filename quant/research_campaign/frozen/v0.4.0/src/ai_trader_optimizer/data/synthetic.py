"""FAKE prices for software checks. Never present them as gold history."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..safety import DataKind
from .models import Dataset
from .validation import dataset_from_frame

SYNTHETIC_NAME = "DÉMO — prix synthétiques (fausses cotations)"


def synthetic_m1_frame(seed: int = 42, days: int = 10, start: str = "2026-09-07T00:00:00Z",
                       base_price: float = 3900.0) -> pd.DataFrame:
    """Same generator as v0.1 ``core.synthetic_m1`` (identical output for identical args)."""
    rng = np.random.default_rng(seed)
    timeidx = pd.date_range(start, periods=days * 24 * 60, freq="min")
    timeidx = timeidx[timeidx.dayofweek < 5]
    if len(timeidx) < 120:
        raise ValueError("Not enough weekdays in synthetic sample")
    changes = rng.normal(0, 0.8, size=len(timeidx)) + np.sin(np.arange(len(timeidx)) / 200) * 0.10
    op = base_price + np.cumsum(np.r_[0, changes[:-1]])
    cl = op + changes
    hi = np.maximum(op, cl) + rng.random(len(timeidx)) * 0.35
    lo = np.minimum(op, cl) - rng.random(len(timeidx)) * 0.35
    return pd.DataFrame({"timestamp": timeidx, "open": op, "high": hi, "low": lo, "close": cl})


def synthetic_dataset(seed: int = 42, days: int = 10) -> Dataset:
    return dataset_from_frame(
        synthetic_m1_frame(seed=seed, days=days), name=f"{SYNTHETIC_NAME} · seed {seed} · {days} j",
        symbol="XAUUSD-DEMO", source_label="générateur synthétique (marche aléatoire)",
        kind=DataKind.SYNTHETIC, notes="Données fictives : uniquement pour tester le logiciel.",
    )
