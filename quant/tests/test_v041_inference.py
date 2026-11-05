"""Unit tests of the inference methods of research/inference.py (protocol H1/H2)."""

from __future__ import annotations

import numpy as np

from ai_trader_optimizer.research import inference as I


def test_overlap_units_split_only_when_every_earlier_outcome_is_known():
    t = np.array([0, 1, 2, 10, 11, 30])
    avail = np.array([5, 3, 4, 12, 20, 31])
    assert I.overlap_units(t, avail).tolist() == [0, 0, 0, 1, 1, 2]
    # entering exactly when the previous outcome becomes known: windows touch, do not overlap -> new unit
    assert I.overlap_units(np.array([0, 5]), np.array([5, 6])).tolist() == [0, 1]
    assert I.overlap_units(np.array([0, 4]), np.array([5, 6])).tolist() == [0, 0]


def test_politis_white_block_is_one_for_independent_data_and_grows_with_persistence():
    rng = np.random.default_rng(0)
    assert I.politis_white_block(rng.normal(size=2000)) <= 2
    e = rng.normal(size=3000)
    x = np.zeros(3000)
    for i in range(1, 3000):
        x[i] = 0.9 * x[i - 1] + e[i]
    assert I.politis_white_block(x) >= 10
    assert I.politis_white_block(np.ones(50)) == 1  # constant series: no dependence to model


def test_cluster_bootstrap_counts_copies_of_one_outcome_as_one_unit():
    """Codex counter-example: groups of 100 signals sharing one outcome known at the group's end."""
    rng = np.random.default_rng(3)
    n, g = 3000, 100
    t = np.arange(n, dtype=np.int64)
    end = np.minimum((np.arange(n) // g + 1) * g, n)
    r = np.repeat(np.where(rng.random(n // g) < 0.4, 1.5, -1.0), g)
    take = np.ones(n, bool)
    cl = I.bootstrap(t, end, r, take, 500, np.random.default_rng(0), 0.05, method=I.CLUSTERS)
    lg = I.bootstrap(t, end, r, take, 500, np.random.default_rng(0), 0.05, method=I.LEGACY)
    assert cl["n_units"] == n // g
    w = lambda ci: ci[1] - ci[0]  # noqa: E731
    assert w(cl["filtered_ci"]) > w(lg["filtered_ci"])  # honest (wider) uncertainty
    assert I.insufficient(n, n, cl["n_units"], cl["n_units_taken"])  # 30 independent outcomes: not enough


def test_cluster_bootstrap_on_independent_signals_matches_the_signal_count():
    rng = np.random.default_rng(5)
    n = 1500
    t = np.arange(n, dtype=np.int64) * 10
    r = np.where(rng.random(n) < 0.4, 1.5, -1.0)
    out = I.bootstrap(t, t + 1, r, np.ones(n, bool), 400, np.random.default_rng(1), 0.05, method=I.CLUSTERS)
    assert out["n_units"] == n and out["block_length"] <= 3
    assert out["one_sided_bound"] is not None and out["one_sided_bound"] < out["filtered_ci"][1]
