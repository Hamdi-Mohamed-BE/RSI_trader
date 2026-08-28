from __future__ import annotations

import numpy as np
import pandas as pd


STATES = ("Bear", "Sideways", "Bull")


def label_regimes(close: pd.Series, window: int, threshold: float) -> pd.Series:
    """Literal repository rule: rolling-return Bull/Bear/Sideways labels."""
    rolling_return = close.pct_change(window)
    labels = pd.Series(1, index=close.index, dtype="int64")
    labels.loc[rolling_return > threshold] = 2
    labels.loc[rolling_return < -threshold] = 0
    return labels.loc[rolling_return.notna()]


def build_transition_matrix(labels: pd.Series) -> np.ndarray:
    counts = np.zeros((3, 3), dtype=float)
    values = labels.to_numpy(dtype=int)
    for index in range(len(values) - 1):
        counts[values[index], values[index + 1]] += 1.0
    row_sums = counts.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    return counts / row_sums


def stationary_distribution(matrix: np.ndarray) -> np.ndarray:
    values, vectors = np.linalg.eig(matrix.T)
    index = int(np.argmin(np.abs(values - 1.0)))
    vector = np.abs(np.real(vectors[:, index]))
    total = vector.sum()
    return vector / total if total else np.array([0.0, 1.0, 0.0])


def walk_forward_signals(
    close: pd.Series,
    *,
    window: int,
    threshold: float,
    min_train: int = 252,
) -> pd.DataFrame:
    """No-lookahead signals matching the supplied repository's count logic."""
    labels = label_regimes(close, window=window, threshold=threshold)
    result = pd.DataFrame(index=close.index, columns=["state", "signal"], dtype=float)
    if len(labels) < min_train + 2:
        return result

    values = labels.to_numpy(dtype=int)
    counts = np.zeros((3, 3), dtype=float)
    for index in range(min_train - 1):
        counts[values[index], values[index + 1]] += 1.0

    for position in range(min_train, len(values)):
        row_sums = counts.sum(axis=1, keepdims=True)
        matrix = counts / np.where(row_sums == 0, 1.0, row_sums)
        state = int(values[position])
        when = labels.index[position]
        result.loc[when, "state"] = state
        result.loc[when, "signal"] = matrix[state, 2] - matrix[state, 0]
        counts[values[position - 1], values[position]] += 1.0
    return result


def current_snapshot(close: pd.Series, window: int, threshold: float) -> dict:
    labels = label_regimes(close, window=window, threshold=threshold)
    matrix = build_transition_matrix(labels)
    stationary = stationary_distribution(matrix)
    state = int(labels.iloc[-1])
    probabilities = matrix[state]
    return {
        "current_regime": STATES[state],
        "signal": float(probabilities[2] - probabilities[0]),
        "next_probabilities": {
            "bear": float(probabilities[0]),
            "sideways": float(probabilities[1]),
            "bull": float(probabilities[2]),
        },
        "transition_matrix": matrix.tolist(),
        "stationary_distribution": {
            "bear": float(stationary[0]),
            "sideways": float(stationary[1]),
            "bull": float(stationary[2]),
        },
    }

