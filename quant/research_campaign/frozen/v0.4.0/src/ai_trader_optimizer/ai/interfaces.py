"""Interfaces for the FUTURE AI module. No model is trained in v0.2.

Protocol (see docs/ARCHITECTURE.md §AI):
* features are extracted from the strategy's signal frame at decision time only;
* a SignalScorer outputs a calibrated probability that a BASELINE signal is worth
  taking; it filters signals, it never sizes positions nor bypasses the Risk Guardian;
* every model is compared to the deterministic baseline on the same data and costs,
  with chronological / walk-forward splits; the final test set is never used for fitting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import pandas as pd


class FeatureExtractor(Protocol):
    name: str
    version: str

    def transform(self, signals: pd.DataFrame) -> pd.DataFrame:
        """Row i may only use information available at the close of bar i."""


class SignalScorer(Protocol):
    model_id: str

    def fit(self, X: pd.DataFrame, y: pd.Series) -> SignalScorer: ...

    def predict_proba(self, X: pd.DataFrame) -> pd.Series:
        """Calibrated probability in [0, 1] for each candidate signal."""


@dataclass(frozen=True)
class ModelCard:
    model_id: str
    version: str
    algorithm: str  # e.g. "logistic_regression", "xgboost" — simple models first
    feature_set: str
    dataset_ids: tuple[str, ...]
    train_period: tuple[str, str]
    validation_period: tuple[str, str]
    test_period: tuple[str, str]
    baseline_run_id: str
    metrics: dict = field(default_factory=dict)
    calibration: str = "not calibrated"
    notes: str = ""
