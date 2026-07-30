from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from news_core import EVENTS, FEATURE_NAMES


CLEAR_LABELS = ("BUY", "SELL")
LEGACY_FEATURE_INDICES = list(range(18))
ENHANCED_FEATURE_INDICES = list(range(len(FEATURE_NAMES)))
EVENT_FEATURE_INDICES = [
    *range(13),
    *range(18, len(FEATURE_NAMES)),
]
POLICY_THRESHOLDS = (0.55, 0.575, 0.60, 0.625, 0.65, 0.675, 0.70, 0.725, 0.75)
MIN_EVENT_TRAINING_SAMPLES = 24


@dataclass(frozen=True)
class EventPolicy:
    event: str
    strategy: str
    threshold: float
    calibration_slope: float
    calibration_intercept: float
    calibration_samples: int
    selection_samples: int
    selected_calls: int
    selected_accuracy_pct: float
    selected_coverage_pct: float
    selected_score: float

    def calibrate(self, probability_buy: float) -> float:
        clipped = min(max(probability_buy, 1e-5), 1 - 1e-5)
        logit = math.log(clipped / (1 - clipped))
        value = self.calibration_slope * logit + self.calibration_intercept
        return float(1 / (1 + math.exp(-max(min(value, 30), -30))))


def global_tree() -> ExtraTreesClassifier:
    return ExtraTreesClassifier(
        n_estimators=500,
        min_samples_leaf=8,
        max_features=0.75,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )


def global_logistic() -> Pipeline:
    return Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=0.08,
                    class_weight="balanced",
                    max_iter=3_000,
                    random_state=42,
                ),
            ),
        ]
    )


def event_tree() -> ExtraTreesClassifier:
    return ExtraTreesClassifier(
        n_estimators=600,
        min_samples_leaf=5,
        max_depth=9,
        max_features=0.55,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )


def event_logistic() -> Pipeline:
    return Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=0.05,
                    class_weight="balanced",
                    max_iter=3_000,
                    random_state=42,
                ),
            ),
        ]
    )


def _matrix(rows: list[dict], feature_indices: list[int]) -> np.ndarray:
    return np.asarray(
        [[row["features"][index] for index in feature_indices] for row in rows],
        dtype=float,
    )


def _buy_probability(model: object, values: np.ndarray) -> np.ndarray:
    probabilities = model.predict_proba(values)
    classes = list(model.classes_)
    if "BUY" not in classes:
        return np.zeros(len(values), dtype=float)
    return probabilities[:, classes.index("BUY")].astype(float)


def fit_components(rows: list[dict]) -> dict:
    clear = [row for row in rows if row["target"] in CLEAR_LABELS]
    if len(clear) < 40:
        raise ValueError("At least 40 clear historical releases are required.")
    labels = np.asarray([row["target"] for row in clear])
    global_models = {
        "global_tree": clone(global_tree()).fit(
            _matrix(clear, LEGACY_FEATURE_INDICES),
            labels,
        ),
        "global_logistic": clone(global_logistic()).fit(
            _matrix(clear, ENHANCED_FEATURE_INDICES),
            labels,
        ),
    }
    event_models: dict[str, dict[str, object]] = {}
    for event in EVENTS:
        event_rows = [row for row in clear if row["event"] == event]
        event_labels = np.asarray([row["target"] for row in event_rows])
        if (
            len(event_rows) < MIN_EVENT_TRAINING_SAMPLES
            or len(set(event_labels)) < 2
        ):
            continue
        event_models[event] = {
            "event_tree": clone(event_tree()).fit(
                _matrix(event_rows, EVENT_FEATURE_INDICES),
                event_labels,
            ),
            "event_logistic": clone(event_logistic()).fit(
                _matrix(event_rows, EVENT_FEATURE_INDICES),
                event_labels,
            ),
        }
    return {
        "global_models": global_models,
        "event_models": event_models,
        "training_samples": len(clear),
    }


def component_probabilities(fitted: dict, rows: list[dict]) -> list[dict[str, float]]:
    if not rows:
        return []
    global_models = fitted["global_models"]
    global_tree_probabilities = _buy_probability(
        global_models["global_tree"],
        _matrix(rows, LEGACY_FEATURE_INDICES),
    )
    global_logistic_probabilities = _buy_probability(
        global_models["global_logistic"],
        _matrix(rows, ENHANCED_FEATURE_INDICES),
    )
    outputs: list[dict[str, float]] = []
    for index, row in enumerate(rows):
        event_models = fitted["event_models"].get(row["event"])
        global_tree_probability = float(global_tree_probabilities[index])
        global_logistic_probability = float(global_logistic_probabilities[index])
        if event_models:
            event_values = _matrix([row], EVENT_FEATURE_INDICES)
            event_tree_probability = float(
                _buy_probability(event_models["event_tree"], event_values)[0]
            )
            event_logistic_probability = float(
                _buy_probability(event_models["event_logistic"], event_values)[0]
            )
        else:
            event_tree_probability = global_tree_probability
            event_logistic_probability = global_logistic_probability
        outputs.append(
            {
                "global_tree": global_tree_probability,
                "global_logistic": global_logistic_probability,
                "event_tree": event_tree_probability,
                "event_logistic": event_logistic_probability,
            }
        )
    return outputs


def strategy_probability(components: dict[str, float], strategy: str) -> float:
    if strategy in components:
        return float(components[strategy])
    if strategy == "global_mix":
        return float(
            0.70 * components["global_tree"]
            + 0.30 * components["global_logistic"]
        )
    if strategy == "tree_mix":
        return float(
            0.55 * components["global_tree"]
            + 0.45 * components["event_tree"]
        )
    if strategy == "specialist_mix":
        return float(
            0.50 * components["global_tree"]
            + 0.30 * components["event_tree"]
            + 0.20 * components["event_logistic"]
        )
    if strategy == "balanced_ensemble":
        return float(
            0.40 * components["global_tree"]
            + 0.20 * components["global_logistic"]
            + 0.25 * components["event_tree"]
            + 0.15 * components["event_logistic"]
        )
    raise KeyError(f"Unknown probability strategy: {strategy}")


def strategy_names() -> tuple[str, ...]:
    return (
        "global_tree",
        "global_logistic",
        "global_mix",
        "event_tree",
        "event_logistic",
        "tree_mix",
        "specialist_mix",
        "balanced_ensemble",
    )


def expanding_oof_components(
    rows: list[dict],
    n_splits: int = 6,
) -> list[dict]:
    ordered = sorted(rows, key=lambda row: row["release_utc"])
    splitter = TimeSeriesSplit(n_splits=n_splits)
    outputs: list[dict] = []
    indices = np.arange(len(ordered))
    for fit_indices, validation_indices in splitter.split(indices):
        fitted = fit_components([ordered[int(index)] for index in fit_indices])
        validation_rows = [ordered[int(index)] for index in validation_indices]
        probabilities = component_probabilities(fitted, validation_rows)
        for row, components in zip(validation_rows, probabilities):
            outputs.append(
                {
                    "release_utc": row["release_utc"],
                    "event": row["event"],
                    "target": row["target"],
                    "components": components,
                }
            )
    return sorted(outputs, key=lambda row: row["release_utc"])


def _fit_platt(probabilities: Iterable[float], targets: Iterable[str]) -> tuple[float, float]:
    values = np.asarray(list(probabilities), dtype=float)
    labels = np.asarray([1 if target == "BUY" else 0 for target in targets], dtype=int)
    if len(values) < 20 or len(set(labels)) < 2:
        return 1.0, 0.0
    clipped = np.clip(values, 1e-5, 1 - 1e-5)
    logits = np.log(clipped / (1 - clipped)).reshape(-1, 1)
    model = LogisticRegression(C=0.35, max_iter=2_000, random_state=42)
    model.fit(logits, labels)
    return float(model.coef_[0, 0]), float(model.intercept_[0])


def _calibrate(probability: float, slope: float, intercept: float) -> float:
    clipped = min(max(probability, 1e-5), 1 - 1e-5)
    value = slope * math.log(clipped / (1 - clipped)) + intercept
    return float(1 / (1 + math.exp(-max(min(value, 30), -30))))


def _selection_score(correct: int, calls: int, total: int) -> float:
    if calls <= 0 or total <= 0:
        return -1.0
    accuracy = correct / calls
    coverage = calls / total
    return float((accuracy - 0.5) * math.sqrt(calls) + 0.08 * math.sqrt(coverage))


def select_event_policies(oof_rows: list[dict]) -> dict[str, EventPolicy]:
    policies: dict[str, EventPolicy] = {}
    for event in EVENTS:
        rows = [row for row in oof_rows if row["event"] == event]
        clear_rows = [row for row in rows if row["target"] in CLEAR_LABELS]
        if len(clear_rows) < 20:
            policies[event] = EventPolicy(
                event=event,
                strategy="global_tree",
                threshold=1.0,
                calibration_slope=1.0,
                calibration_intercept=0.0,
                calibration_samples=len(clear_rows),
                selection_samples=len(rows),
                selected_calls=0,
                selected_accuracy_pct=0.0,
                selected_coverage_pct=0.0,
                selected_score=-1.0,
            )
            continue
        best: tuple[float, str, float, float, float, int, int] | None = None
        for strategy in strategy_names():
            raw_clear = [
                strategy_probability(row["components"], strategy)
                for row in clear_rows
            ]
            slope, intercept = _fit_platt(
                raw_clear,
                [row["target"] for row in clear_rows],
            )
            calibrated = [
                _calibrate(
                    strategy_probability(row["components"], strategy),
                    slope,
                    intercept,
                )
                for row in rows
            ]
            for threshold in POLICY_THRESHOLDS:
                calls = 0
                correct = 0
                for row, probability_buy in zip(rows, calibrated):
                    confidence = max(probability_buy, 1 - probability_buy)
                    if confidence < threshold:
                        continue
                    calls += 1
                    direction = "BUY" if probability_buy >= 0.5 else "SELL"
                    correct += int(direction == row["target"])
                minimum_calls = max(5, round(0.12 * len(rows)))
                if calls < minimum_calls:
                    continue
                score = _selection_score(correct, calls, len(rows))
                candidate = (
                    score,
                    strategy,
                    threshold,
                    slope,
                    intercept,
                    calls,
                    correct,
                )
                if best is None or candidate[0] > best[0]:
                    best = candidate
        if best is None:
            policies[event] = EventPolicy(
                event=event,
                strategy="global_tree",
                threshold=1.0,
                calibration_slope=1.0,
                calibration_intercept=0.0,
                calibration_samples=len(clear_rows),
                selection_samples=len(rows),
                selected_calls=0,
                selected_accuracy_pct=0.0,
                selected_coverage_pct=0.0,
                selected_score=-1.0,
            )
            continue
        score, strategy, threshold, slope, intercept, calls, correct = best
        accuracy = 100 * correct / calls
        # A policy without a demonstrated pre-test edge remains in abstention mode.
        if accuracy < 55:
            threshold = 1.0
            calls = 0
            correct = 0
        policies[event] = EventPolicy(
            event=event,
            strategy=strategy,
            threshold=float(threshold),
            calibration_slope=float(slope),
            calibration_intercept=float(intercept),
            calibration_samples=len(clear_rows),
            selection_samples=len(rows),
            selected_calls=int(calls),
            selected_accuracy_pct=round(accuracy, 2),
            selected_coverage_pct=round(100 * calls / max(len(rows), 1), 2),
            selected_score=round(float(score), 6),
        )
    return policies


def policy_prediction(
    components: dict[str, float],
    policy: EventPolicy,
) -> dict:
    raw_probability_buy = strategy_probability(components, policy.strategy)
    probability_buy = policy.calibrate(raw_probability_buy)
    probability_sell = 1 - probability_buy
    direction = "BUY" if probability_buy >= probability_sell else "SELL"
    confidence = max(probability_buy, probability_sell)
    prediction = direction if confidence >= policy.threshold else "NO TRADE"
    return {
        "prediction": prediction,
        "bias": direction,
        "confidence": confidence,
        "probability_buy": probability_buy,
        "probability_sell": probability_sell,
        "raw_probability_buy": raw_probability_buy,
        "strategy": policy.strategy,
        "threshold": policy.threshold,
        "components": components,
    }


def policy_to_dict(policy: EventPolicy) -> dict:
    return {
        field: getattr(policy, field)
        for field in policy.__dataclass_fields__
    }


def policy_from_dict(payload: dict) -> EventPolicy:
    return EventPolicy(**payload)
