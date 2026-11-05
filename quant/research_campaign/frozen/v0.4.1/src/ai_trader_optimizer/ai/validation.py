"""Chronological validation splits (no shuffling, no temporal leakage)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

NO_EMBARGO = pd.Timedelta(0)


@dataclass(frozen=True)
class Split:
    """Time boundaries, in *availability* time (a bar opened at t is available at t + timeframe).

    train = bars whose CLOSE <= train_end (pass as ``trade_end``);
    test  = executions at bar OPENS >= test_start (pass as ``trade_start``), bars whose close <= test_end.
    With test_start >= train_end, no bar's results are used by both segments; the test segment may still
    read earlier bars to warm up indicators (observations, never results).
    """

    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


def _check(split: Split) -> Split:
    """Invariant of every split (audit N3): train_start < train_end <= test_start < test_end."""
    if not (split.train_start < split.train_end <= split.test_start < split.test_end):
        raise ValueError(f"découpage temporel invalide : {split}")
    return split


def _check_embargo(embargo: pd.Timedelta) -> None:
    if pd.isna(embargo) or embargo < pd.Timedelta(0):
        raise ValueError("l'embargo doit être positif ou nul (un embargo négatif ferait chevaucher IS et OOS)")


def chronological_split(start: pd.Timestamp, end: pd.Timestamp, train_fraction: float = 0.7,
                        embargo: pd.Timedelta = NO_EMBARGO) -> Split:
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be in (0, 1)")
    _check_embargo(embargo)
    if not start < end:
        raise ValueError("intervalle inversé ou vide")
    cut = start + (end - start) * train_fraction
    return _check(Split(start, cut, cut + embargo, end))


def walk_forward_splits(start: pd.Timestamp, end: pd.Timestamp, train: pd.Timedelta, test: pd.Timedelta,
                        embargo: pd.Timedelta = NO_EMBARGO, anchored: bool = False) -> list[Split]:
    """Rolling (or anchored) train windows, each followed by an embargo then a test window.
    Test windows never overlap and always start after their train window ends."""
    if train <= pd.Timedelta(0) or test <= pd.Timedelta(0):
        raise ValueError("train and test must be positive")
    _check_embargo(embargo)
    out, train_start = [], start
    while True:
        train_end = train_start + train if not anchored else start + train + test * len(out)
        test_start = train_end + embargo
        test_end = test_start + test
        if test_end > end:
            break
        out.append(_check(Split(start if anchored else train_start, train_end, test_start, test_end)))
        train_start = train_start + test
    return out
