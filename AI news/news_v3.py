from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from news_core import EVENTS
from news_ensemble import (
    EventPolicy,
    LEGACY_FEATURE_INDICES,
    component_probabilities,
    fit_components,
    strategy_names,
    strategy_probability,
)


IMPULSE_STRATEGIES = ("impulse_tree", "impulse_logistic", "impulse_blend")
IMPULSE_THRESHOLDS = (0.45, 0.50, 0.55, 0.60, 0.65, 0.70)
DIRECTION_THRESHOLDS = (0.55, 0.575, 0.60, 0.625, 0.65, 0.675, 0.70)
OOD_LIMITS = (1.0, 1.25, math.inf)
VETO_THRESHOLDS = (0.0, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55)
MIN_TRAINING_SAMPLES = 80


@dataclass(frozen=True)
class TwoStagePolicy:
    event: str
    impulse_strategy: str
    impulse_threshold: float
    direction_strategy: str
    direction_threshold: float
    require_impulse_agreement: bool
    max_ood_ratio: float
    selection_samples: int
    selected_calls: int
    selected_wins: int
    selected_accuracy_pct: float
    selected_coverage_pct: float
    selected_false_impulses: int
    selected_score: float


@dataclass(frozen=True)
class HybridPolicy:
    event: str
    direction_policy: EventPolicy
    impulse_strategy: str
    veto_threshold: float
    require_impulse_agreement: bool
    max_ood_ratio: float
    selection_samples: int
    baseline_calls: int
    baseline_wins: int
    selected_calls: int
    selected_wins: int
    selected_accuracy_pct: float
    selected_coverage_pct: float
    selected_false_impulses: int
    selected_score: float


def _matrix(rows: list[dict]) -> np.ndarray:
    return np.asarray(
        [
            [row["features"][index] for index in LEGACY_FEATURE_INDICES]
            for row in rows
        ],
        dtype=float,
    )


def _impulse_tree() -> ExtraTreesClassifier:
    return ExtraTreesClassifier(
        n_estimators=350,
        max_depth=8,
        min_samples_leaf=10,
        max_features=0.55,
        class_weight="balanced",
        random_state=73,
        n_jobs=-1,
    )


def _impulse_logistic() -> Pipeline:
    return Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=0.05,
                    class_weight="balanced",
                    max_iter=3_000,
                    random_state=73,
                ),
            ),
        ]
    )


def _positive_probability(model: object, values: np.ndarray) -> np.ndarray:
    probabilities = model.predict_proba(values)
    classes = list(model.classes_)
    if 1 not in classes:
        return np.zeros(len(values), dtype=float)
    return probabilities[:, classes.index(1)].astype(float)


def fit_two_stage(rows: list[dict]) -> dict:
    ordered = sorted(rows, key=lambda row: row["release_utc"])
    if len(ordered) < MIN_TRAINING_SAMPLES:
        raise ValueError(
            f"At least {MIN_TRAINING_SAMPLES} historical releases are required."
        )
    values = _matrix(ordered)
    impulse_labels = np.asarray(
        [int(row["target"] != "UNCERTAIN") for row in ordered],
        dtype=int,
    )
    impulse_models = {
        "impulse_tree": clone(_impulse_tree()).fit(values, impulse_labels),
        "impulse_logistic": clone(_impulse_logistic()).fit(
            values,
            impulse_labels,
        ),
    }

    scaler = StandardScaler().fit(values)
    standardized = np.clip(scaler.transform(values), -6.0, 6.0)
    neighbor_count = min(6, len(ordered))
    neighbors = NearestNeighbors(n_neighbors=neighbor_count).fit(standardized)
    training_distances = neighbors.kneighbors(standardized)[0][:, -1]
    ood_reference = max(float(np.quantile(training_distances, 0.95)), 1e-6)

    return {
        "impulse_models": impulse_models,
        "direction_models": fit_components(ordered),
        "ood_scaler": scaler,
        "ood_neighbors": neighbors,
        "ood_reference": ood_reference,
        "training_samples": len(ordered),
        "impulse_training_samples": len(ordered),
        "direction_training_samples": sum(
            row["target"] in {"BUY", "SELL"} for row in ordered
        ),
    }


def two_stage_components(fitted: dict, rows: list[dict]) -> list[dict]:
    if not rows:
        return []
    values = _matrix(rows)
    tree = _positive_probability(
        fitted["impulse_models"]["impulse_tree"],
        values,
    )
    logistic = _positive_probability(
        fitted["impulse_models"]["impulse_logistic"],
        values,
    )
    direction = component_probabilities(fitted["direction_models"], rows)
    standardized = np.clip(
        fitted["ood_scaler"].transform(values),
        -6.0,
        6.0,
    )
    query_neighbors = min(5, fitted["training_samples"])
    distances = fitted["ood_neighbors"].kneighbors(
        standardized,
        n_neighbors=query_neighbors,
    )[0][:, -1]
    outputs = []
    for index, direction_components in enumerate(direction):
        outputs.append(
            {
                "impulse_tree": float(tree[index]),
                "impulse_logistic": float(logistic[index]),
                "impulse_blend": float(
                    0.60 * tree[index] + 0.40 * logistic[index]
                ),
                "impulse_agreement": bool(
                    (tree[index] >= 0.5) == (logistic[index] >= 0.5)
                ),
                "ood_ratio": float(
                    distances[index] / fitted["ood_reference"]
                ),
                "direction": direction_components,
            }
        )
    return outputs


def predict_with_policy(
    components: dict,
    policy: TwoStagePolicy,
) -> dict:
    impulse_probability = float(components[policy.impulse_strategy])
    impulse_agreement = bool(components["impulse_agreement"])
    ood_ratio = float(components["ood_ratio"])
    probability_buy = strategy_probability(
        components["direction"],
        policy.direction_strategy,
    )
    probability_sell = 1.0 - probability_buy
    bias = "BUY" if probability_buy >= probability_sell else "SELL"
    direction_confidence = max(probability_buy, probability_sell)

    gates = {
        "impulse": impulse_probability >= policy.impulse_threshold,
        "direction": direction_confidence >= policy.direction_threshold,
        "impulse_agreement": (
            impulse_agreement or not policy.require_impulse_agreement
        ),
        "in_distribution": (
            ood_ratio <= policy.max_ood_ratio
            if math.isfinite(policy.max_ood_ratio)
            else True
        ),
    }
    prediction = bias if all(gates.values()) else "NO TRADE"
    failed_gates = [name for name, passed in gates.items() if not passed]
    return {
        "prediction": prediction,
        "bias": bias,
        "impulse_probability": impulse_probability,
        "direction_confidence": direction_confidence,
        "probability_buy": probability_buy,
        "probability_sell": probability_sell,
        "impulse_agreement": impulse_agreement,
        "ood_ratio": ood_ratio,
        "gates": gates,
        "failed_gates": failed_gates,
    }


def predict_with_hybrid_policy(
    components: dict,
    policy: HybridPolicy,
) -> dict:
    from news_ensemble import policy_prediction

    direction = policy_prediction(
        components["direction"],
        policy.direction_policy,
    )
    impulse_probability = float(components[policy.impulse_strategy])
    impulse_agreement = bool(components["impulse_agreement"])
    ood_ratio = float(components["ood_ratio"])
    gates = {
        "direction": direction["prediction"] in {"BUY", "SELL"},
        "impulse_veto": (
            impulse_probability >= policy.veto_threshold
            if policy.veto_threshold > 0
            else True
        ),
        "impulse_agreement": (
            impulse_agreement
            or not policy.require_impulse_agreement
            or policy.veto_threshold <= 0
        ),
        "in_distribution": (
            ood_ratio <= policy.max_ood_ratio
            if math.isfinite(policy.max_ood_ratio)
            else True
        ),
    }
    prediction = (
        direction["prediction"]
        if all(gates.values())
        else "NO TRADE"
    )
    return {
        "prediction": prediction,
        "bias": direction["bias"],
        "impulse_probability": impulse_probability,
        "direction_confidence": direction["confidence"],
        "probability_buy": direction["probability_buy"],
        "probability_sell": direction["probability_sell"],
        "impulse_agreement": impulse_agreement,
        "ood_ratio": ood_ratio,
        "gates": gates,
        "failed_gates": [
            name for name, passed in gates.items() if not passed
        ],
    }


def expanding_oof_two_stage(
    rows: list[dict],
    n_splits: int = 6,
) -> list[dict]:
    ordered = sorted(rows, key=lambda row: row["release_utc"])
    splitter = TimeSeriesSplit(n_splits=n_splits)
    indices = np.arange(len(ordered))
    outputs = []
    for fit_indices, validation_indices in splitter.split(indices):
        training = [ordered[int(index)] for index in fit_indices]
        if len(training) < MIN_TRAINING_SAMPLES:
            continue
        validation = [ordered[int(index)] for index in validation_indices]
        fitted = fit_two_stage(training)
        components = two_stage_components(fitted, validation)
        for row, payload in zip(validation, components):
            outputs.append(
                {
                    "release_utc": row["release_utc"],
                    "event": row["event"],
                    "target": row["target"],
                    "reaction": row["reaction"],
                    "components": payload,
                }
            )
    return sorted(outputs, key=lambda row: row["release_utc"])


def _selection_score(
    wins: int,
    calls: int,
    total: int,
    false_impulses: int,
) -> float:
    if calls <= 0 or total <= 0:
        return -1.0
    accuracy = wins / calls
    coverage = calls / total
    false_rate = false_impulses / calls
    return float(
        (accuracy - 0.5) * math.sqrt(calls)
        + 0.06 * math.sqrt(coverage)
        - 0.12 * false_rate
    )


def _default_policy(event: str, sample_count: int) -> TwoStagePolicy:
    return TwoStagePolicy(
        event=event,
        impulse_strategy="impulse_blend",
        impulse_threshold=1.0,
        direction_strategy="global_tree",
        direction_threshold=1.0,
        require_impulse_agreement=True,
        max_ood_ratio=1.0,
        selection_samples=sample_count,
        selected_calls=0,
        selected_wins=0,
        selected_accuracy_pct=0.0,
        selected_coverage_pct=0.0,
        selected_false_impulses=0,
        selected_score=-1.0,
    )


def select_two_stage_policies(
    oof_rows: list[dict],
) -> dict[str, TwoStagePolicy]:
    policies = {}
    for event in EVENTS:
        rows = [row for row in oof_rows if row["event"] == event]
        if len(rows) < 24:
            policies[event] = _default_policy(event, len(rows))
            continue
        minimum_calls = max(6, round(0.10 * len(rows)))
        best = None
        for impulse_strategy in IMPULSE_STRATEGIES:
            for impulse_threshold in IMPULSE_THRESHOLDS:
                for direction_strategy in strategy_names():
                    for direction_threshold in DIRECTION_THRESHOLDS:
                        for require_agreement in (False, True):
                            for max_ood_ratio in OOD_LIMITS:
                                calls = 0
                                wins = 0
                                false_impulses = 0
                                for row in rows:
                                    policy = TwoStagePolicy(
                                        event=event,
                                        impulse_strategy=impulse_strategy,
                                        impulse_threshold=impulse_threshold,
                                        direction_strategy=direction_strategy,
                                        direction_threshold=direction_threshold,
                                        require_impulse_agreement=require_agreement,
                                        max_ood_ratio=max_ood_ratio,
                                        selection_samples=len(rows),
                                        selected_calls=0,
                                        selected_wins=0,
                                        selected_accuracy_pct=0.0,
                                        selected_coverage_pct=0.0,
                                        selected_false_impulses=0,
                                        selected_score=0.0,
                                    )
                                    prediction = predict_with_policy(
                                        row["components"],
                                        policy,
                                    )["prediction"]
                                    if prediction == "NO TRADE":
                                        continue
                                    calls += 1
                                    wins += int(prediction == row["target"])
                                    false_impulses += int(
                                        row["target"] == "UNCERTAIN"
                                    )
                                if calls < minimum_calls:
                                    continue
                                accuracy = wins / calls
                                score = _selection_score(
                                    wins,
                                    calls,
                                    len(rows),
                                    false_impulses,
                                )
                                candidate = (
                                    score,
                                    accuracy,
                                    calls,
                                    -false_impulses,
                                    impulse_strategy,
                                    impulse_threshold,
                                    direction_strategy,
                                    direction_threshold,
                                    require_agreement,
                                    max_ood_ratio,
                                    wins,
                                    false_impulses,
                                )
                                if best is None or candidate[:4] > best[:4]:
                                    best = candidate
        if best is None or best[1] < 0.58:
            policies[event] = _default_policy(event, len(rows))
            continue
        (
            score,
            accuracy,
            calls,
            _,
            impulse_strategy,
            impulse_threshold,
            direction_strategy,
            direction_threshold,
            require_agreement,
            max_ood_ratio,
            wins,
            false_impulses,
        ) = best
        policies[event] = TwoStagePolicy(
            event=event,
            impulse_strategy=impulse_strategy,
            impulse_threshold=impulse_threshold,
            direction_strategy=direction_strategy,
            direction_threshold=direction_threshold,
            require_impulse_agreement=require_agreement,
            max_ood_ratio=max_ood_ratio,
            selection_samples=len(rows),
            selected_calls=calls,
            selected_wins=wins,
            selected_accuracy_pct=round(100 * accuracy, 2),
            selected_coverage_pct=round(100 * calls / len(rows), 2),
            selected_false_impulses=false_impulses,
            selected_score=round(score, 6),
        )
    return policies


def select_hybrid_policies(
    oof_rows: list[dict],
    direction_policies: dict[str, EventPolicy],
) -> dict[str, HybridPolicy]:
    policies = {}
    for event in EVENTS:
        rows = [row for row in oof_rows if row["event"] == event]
        direction_policy = direction_policies[event]
        baseline_predictions = []
        for row in rows:
            from news_ensemble import policy_prediction

            prediction = policy_prediction(
                row["components"]["direction"],
                direction_policy,
            )["prediction"]
            if prediction in {"BUY", "SELL"}:
                baseline_predictions.append((row, prediction))
        baseline_calls = len(baseline_predictions)
        baseline_wins = sum(
            prediction == row["target"]
            for row, prediction in baseline_predictions
        )
        if baseline_calls == 0:
            policies[event] = HybridPolicy(
                event=event,
                direction_policy=direction_policy,
                impulse_strategy="impulse_blend",
                veto_threshold=0.0,
                require_impulse_agreement=False,
                max_ood_ratio=math.inf,
                selection_samples=len(rows),
                baseline_calls=0,
                baseline_wins=0,
                selected_calls=0,
                selected_wins=0,
                selected_accuracy_pct=0.0,
                selected_coverage_pct=0.0,
                selected_false_impulses=0,
                selected_score=-1.0,
            )
            continue

        minimum_calls = max(4, math.ceil(0.90 * baseline_calls))
        best = None
        for impulse_strategy in IMPULSE_STRATEGIES:
            for veto_threshold in VETO_THRESHOLDS:
                agreement_options = (
                    (False,)
                    if veto_threshold <= 0
                    else (False, True)
                )
                ood_options = (
                    (math.inf,)
                    if veto_threshold <= 0
                    else OOD_LIMITS
                )
                for require_agreement in agreement_options:
                    for max_ood_ratio in ood_options:
                        calls = 0
                        wins = 0
                        false_impulses = 0
                        for row in rows:
                            candidate_policy = HybridPolicy(
                                event=event,
                                direction_policy=direction_policy,
                                impulse_strategy=impulse_strategy,
                                veto_threshold=veto_threshold,
                                require_impulse_agreement=require_agreement,
                                max_ood_ratio=max_ood_ratio,
                                selection_samples=len(rows),
                                baseline_calls=baseline_calls,
                                baseline_wins=baseline_wins,
                                selected_calls=0,
                                selected_wins=0,
                                selected_accuracy_pct=0.0,
                                selected_coverage_pct=0.0,
                                selected_false_impulses=0,
                                selected_score=0.0,
                            )
                            prediction = predict_with_hybrid_policy(
                                row["components"],
                                candidate_policy,
                            )["prediction"]
                            if prediction == "NO TRADE":
                                continue
                            calls += 1
                            wins += int(prediction == row["target"])
                            false_impulses += int(
                                row["target"] == "UNCERTAIN"
                            )
                        if calls < minimum_calls:
                            continue
                        score = _selection_score(
                            wins,
                            calls,
                            len(rows),
                            false_impulses,
                        )
                        candidate = (
                            score,
                            wins / calls,
                            calls,
                            -false_impulses,
                            impulse_strategy,
                            veto_threshold,
                            require_agreement,
                            max_ood_ratio,
                            wins,
                            false_impulses,
                        )
                        if best is None or candidate[:4] > best[:4]:
                            best = candidate
        if best is None:
            raise RuntimeError(f"No hybrid policy candidate for {event}.")
        (
            score,
            accuracy,
            calls,
            _,
            impulse_strategy,
            veto_threshold,
            require_agreement,
            max_ood_ratio,
            wins,
            false_impulses,
        ) = best
        baseline_accuracy = baseline_wins / baseline_calls
        # The impulse layer is a veto, never permission to create a new call.
        # Keep it inactive unless it improves pre-test accuracy without cutting
        # more than 20% of the direction engine's calls.
        if (
            veto_threshold > 0
            and (
                baseline_calls < 20
                or accuracy < baseline_accuracy + 0.075
            )
        ):
            impulse_strategy = "impulse_blend"
            veto_threshold = 0.0
            require_agreement = False
            max_ood_ratio = math.inf
            calls = baseline_calls
            wins = baseline_wins
            false_impulses = sum(
                row["target"] == "UNCERTAIN"
                for row, _ in baseline_predictions
            )
            accuracy = wins / calls
            score = _selection_score(
                wins,
                calls,
                len(rows),
                false_impulses,
            )
        policies[event] = HybridPolicy(
            event=event,
            direction_policy=direction_policy,
            impulse_strategy=impulse_strategy,
            veto_threshold=veto_threshold,
            require_impulse_agreement=require_agreement,
            max_ood_ratio=max_ood_ratio,
            selection_samples=len(rows),
            baseline_calls=baseline_calls,
            baseline_wins=baseline_wins,
            selected_calls=calls,
            selected_wins=wins,
            selected_accuracy_pct=round(100 * accuracy, 2),
            selected_coverage_pct=round(
                100 * calls / max(len(rows), 1),
                2,
            ),
            selected_false_impulses=false_impulses,
            selected_score=round(score, 6),
        )
    return policies


def policy_to_dict(policy: TwoStagePolicy) -> dict:
    payload = asdict(policy)
    if not math.isfinite(payload["max_ood_ratio"]):
        payload["max_ood_ratio"] = None
    return payload


def hybrid_policy_to_dict(policy: HybridPolicy) -> dict:
    from news_ensemble import policy_to_dict as direction_policy_to_dict

    payload = asdict(policy)
    payload["direction_policy"] = direction_policy_to_dict(
        policy.direction_policy
    )
    if not math.isfinite(payload["max_ood_ratio"]):
        payload["max_ood_ratio"] = None
    return payload
