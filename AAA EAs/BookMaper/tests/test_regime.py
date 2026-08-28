from __future__ import annotations

import numpy as np
import pandas as pd

from bookmaper.regime import build_transition_matrix, label_regimes, walk_forward_signals


def test_transition_rows_are_probabilities() -> None:
    labels = pd.Series([0, 1, 2, 2, 1, 0, 0, 2])
    matrix = build_transition_matrix(labels)
    assert matrix.shape == (3, 3)
    assert np.allclose(matrix.sum(axis=1), 1.0)


def test_regime_labels_follow_threshold_rule() -> None:
    close = pd.Series([100.0, 110.0, 90.0, 100.0])
    labels = label_regimes(close, window=1, threshold=0.05)
    assert labels.tolist() == [2, 0, 2]


def test_walk_forward_has_no_early_signal() -> None:
    close = pd.Series(
        np.linspace(100.0, 150.0, 40),
        index=pd.date_range("2024-01-01", periods=40),
    )
    signals = walk_forward_signals(close, window=2, threshold=0.01, min_train=10)
    assert signals["signal"].notna().sum() == len(close) - 2 - 10
