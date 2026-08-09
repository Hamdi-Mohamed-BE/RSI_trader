from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import asdict, dataclass

import numpy as np
from sklearn.model_selection import TimeSeriesSplit

from fomc_pipeline import fit_fomc_model, model_probability_positive
from news_ensemble import (
    component_probabilities,
    fit_components,
    strategy_names,
    strategy_probability,
)
from news_core import event_history_features


SUPPORTED_EVENTS = ("NFP", "CPI", "FOMC")
SELECTIVE_EVENTS = ("NFP", "CPI")
POLICY_THRESHOLDS = (0.50, 0.525, 0.55, 0.575, 0.60, 0.625, 0.65, 0.675, 0.70)
HISTORY_RULES = (
    "none",
    "last",
    "inverse_last",
    "majority_3",
    "inverse_majority_3",
    "majority_5",
    "inverse_majority_5",
    "event_history",
    "inverse_event_history",
)
DEFAULT_GUARD_START = "2023-01-01T00:00:00+00:00"


@dataclass(frozen=True)
class SelectivePolicy:
    event: str
    strategy: str
    invert_probability: bool
    threshold: float
    history_rule: str
    require_history_agreement: bool
    development_samples: int
    development_calls: int
    development_wins: int
    development_accuracy_pct: float
    guard_samples: int
    guard_calls: int
    guard_wins: int
    guard_accuracy_pct: float
    selection_score: float


def _side(label: str) -> str:
    normalized = str(label).upper()
    if normalized in {"BUY", "POSITIVE"}:
        return "BUY"
    if normalized in {"SELL", "NEGATIVE"}:
        return "SELL"
    raise ValueError(f"Unsupported directional label: {label}")


def _opposite(label: str) -> str:
    return "SELL" if label == "BUY" else "BUY"


def history_direction(rule: str, labels: list[str]) -> str | None:
    history = [_side(label) for label in labels]
    if rule == "none":
        return None
    if not history:
        return None
    if rule == "last":
        return history[-1]
    if rule == "inverse_last":
        return _opposite(history[-1])
    if rule in {"event_history", "inverse_event_history"}:
        buys = sum(label == "BUY" for label in history)
        direction = "BUY" if (buys + 2) / (len(history) + 4) >= 0.5 else "SELL"
        return _opposite(direction) if rule.startswith("inverse_") else direction
    inverse = rule.startswith("inverse_majority_")
    if inverse or rule.startswith("majority_"):
        window = int(rule.rsplit("_", 1)[-1])
        recent = history[-window:]
        buys = sum(label == "BUY" for label in recent)
        direction = "BUY" if buys >= len(recent) / 2 else "SELL"
        return _opposite(direction) if inverse else direction
    raise ValueError(f"Unknown V4 history rule: {rule}")


def selective_prediction(
    components: dict[str, float],
    policy: SelectivePolicy,
    history_labels: list[str],
) -> dict:
    probability_buy = strategy_probability(components, policy.strategy)
    if policy.invert_probability:
        probability_buy = 1.0 - probability_buy
    probability_sell = 1.0 - probability_buy
    bias = "BUY" if probability_buy >= 0.5 else "SELL"
    confidence = max(probability_buy, probability_sell)
    history_bias = history_direction(policy.history_rule, history_labels)
    gates = {
        "confidence": confidence >= policy.threshold,
        "history_agreement": (
            not policy.require_history_agreement or history_bias == bias
        ),
    }
    prediction = bias if all(gates.values()) else "NO CALL"
    return {
        "prediction": prediction,
        "bias": bias,
        "confidence": confidence,
        "probability_buy": probability_buy,
        "probability_sell": probability_sell,
        "history_bias": history_bias,
        "strategy": policy.strategy,
        "threshold": policy.threshold,
        "gates": gates,
        "failed_gates": [name for name, passed in gates.items() if not passed],
    }


def fomc_agreement_prediction(
    history_labels: list[str],
    model_probability_buy: float,
) -> dict:
    history_bias = history_direction("inverse_majority_5", history_labels)
    model_bias = "BUY" if model_probability_buy >= 0.5 else "SELL"
    agrees = history_bias == model_bias
    return {
        "prediction": model_bias if agrees else "NO CALL",
        "bias": model_bias,
        "confidence": 0.65 if agrees else max(model_probability_buy, 1 - model_probability_buy),
        "probability_buy": model_probability_buy,
        "probability_sell": 1.0 - model_probability_buy,
        "history_bias": history_bias,
        "strategy": "fomc_history_model_agreement",
        "threshold": None,
        "gates": {"history_model_agreement": agrees},
        "failed_gates": [] if agrees else ["history_model_agreement"],
    }


def binary_rows(rows: list[dict]) -> list[dict]:
    output = []
    for row in rows:
        if row["event"] not in SUPPORTED_EVENTS:
            continue
        converted = dict(row)
        converted["target"] = (
            "BUY" if float(row["reaction"]["release_move"]) >= 0 else "SELL"
        )
        output.append(converted)
    return sorted(output, key=lambda row: row["release_utc"])


def expanding_oof_components_safe(rows: list[dict], n_splits: int = 10) -> list[dict]:
    ordered = sorted(rows, key=lambda row: row["release_utc"])
    indices = np.arange(len(ordered))
    output: list[dict] = []
    for fit_indices, validation_indices in TimeSeriesSplit(n_splits=n_splits).split(indices):
        training = [ordered[int(index)] for index in fit_indices]
        if len(training) < 40:
            continue
        validation = [ordered[int(index)] for index in validation_indices]
        fitted = fit_components(training)
        components = component_probabilities(fitted, validation)
        for row, values in zip(validation, components):
            output.append({**row, "components": values})
    return sorted(output, key=lambda row: row["release_utc"])


def _prior_history(rows: list[dict]) -> dict[str, list[str]]:
    history: dict[str, list[str]] = defaultdict(list)
    snapshots: dict[str, list[str]] = {}
    for row in sorted(rows, key=lambda item: item["release_utc"]):
        snapshots[row["release_utc"]] = list(history[row["event"]])
        history[row["event"]].append(row["target"])
    return snapshots


def _candidate_metrics(
    rows: list[dict],
    *,
    strategy: str,
    invert_probability: bool,
    threshold: float,
    history_rule: str,
    prior_by_release: dict[str, list[str]],
) -> tuple[int, int, float]:
    calls = 0
    wins = 0
    for row in rows:
        probability_buy = strategy_probability(row["components"], strategy)
        if invert_probability:
            probability_buy = 1.0 - probability_buy
        confidence = max(probability_buy, 1.0 - probability_buy)
        bias = "BUY" if probability_buy >= 0.5 else "SELL"
        history_bias = history_direction(
            history_rule,
            prior_by_release[row["release_utc"]],
        )
        if confidence < threshold:
            continue
        if history_rule != "none" and history_bias != bias:
            continue
        calls += 1
        wins += int(bias == row["target"])
    return calls, wins, wins / calls if calls else 0.0


def select_policies(
    oof_rows: list[dict],
    training_rows: list[dict],
    guard_start: str = DEFAULT_GUARD_START,
) -> dict[str, SelectivePolicy]:
    prior_by_release = _prior_history(training_rows)
    policies: dict[str, SelectivePolicy] = {}
    for event in SELECTIVE_EVENTS:
        development = [
            row
            for row in oof_rows
            if row["event"] == event and row["release_utc"] < guard_start
        ]
        guard = [
            row
            for row in oof_rows
            if row["event"] == event and row["release_utc"] >= guard_start
        ]
        best: tuple[float, tuple, tuple, tuple] | None = None
        for strategy in strategy_names():
            for invert_probability in (False, True):
                for threshold in POLICY_THRESHOLDS:
                    for history_rule in HISTORY_RULES:
                        development_metrics = _candidate_metrics(
                            development,
                            strategy=strategy,
                            invert_probability=invert_probability,
                            threshold=threshold,
                            history_rule=history_rule,
                            prior_by_release=prior_by_release,
                        )
                        guard_metrics = _candidate_metrics(
                            guard,
                            strategy=strategy,
                            invert_probability=invert_probability,
                            threshold=threshold,
                            history_rule=history_rule,
                            prior_by_release=prior_by_release,
                        )
                        development_calls, _, development_accuracy = development_metrics
                        guard_calls, _, guard_accuracy = guard_metrics
                        minimum_development_calls = max(10, round(0.12 * len(development)))
                        minimum_guard_calls = max(3, round(0.15 * len(guard)))
                        if (
                            development_calls < minimum_development_calls
                            or guard_calls < minimum_guard_calls
                            or development_accuracy < 0.55
                            or guard_accuracy < 0.55
                        ):
                            continue
                        coverage = (development_calls + guard_calls) / max(
                            len(development) + len(guard), 1
                        )
                        score = (
                            min(development_accuracy, guard_accuracy)
                            + 0.08 * math.sqrt(coverage)
                            - 0.02 * abs(development_accuracy - guard_accuracy)
                        )
                        candidate = (
                            score,
                            (strategy, invert_probability, threshold, history_rule),
                            development_metrics,
                            guard_metrics,
                        )
                        if best is None or candidate[0] > best[0]:
                            best = candidate
        if best is None:
            policies[event] = SelectivePolicy(
                event=event,
                strategy="global_tree",
                invert_probability=False,
                threshold=1.0,
                history_rule="none",
                require_history_agreement=False,
                development_samples=len(development),
                development_calls=0,
                development_wins=0,
                development_accuracy_pct=0.0,
                guard_samples=len(guard),
                guard_calls=0,
                guard_wins=0,
                guard_accuracy_pct=0.0,
                selection_score=-1.0,
            )
            continue
        score, settings, development_metrics, guard_metrics = best
        strategy, invert_probability, threshold, history_rule = settings
        development_calls, development_wins, development_accuracy = development_metrics
        guard_calls, guard_wins, guard_accuracy = guard_metrics
        policies[event] = SelectivePolicy(
            event=event,
            strategy=strategy,
            invert_probability=invert_probability,
            threshold=threshold,
            history_rule=history_rule,
            require_history_agreement=history_rule != "none",
            development_samples=len(development),
            development_calls=development_calls,
            development_wins=development_wins,
            development_accuracy_pct=round(100 * development_accuracy, 2),
            guard_samples=len(guard),
            guard_calls=guard_calls,
            guard_wins=guard_wins,
            guard_accuracy_pct=round(100 * guard_accuracy, 2),
            selection_score=round(score, 6),
        )
    return policies


def fit_live_artifact(
    rows_by_lead: dict[int, list[dict]],
    policies_by_lead: dict[int, dict[str, SelectivePolicy]],
) -> dict:
    rows_15 = binary_rows(rows_by_lead[15])
    rows_30 = binary_rows(rows_by_lead[30])
    history: dict[str, list[str]] = defaultdict(list)
    global_history: list[str] = []
    for row in rows_15:
        history[row["event"]].append(row["target"])
        global_history.append(row["target"])
    final_history_features = {
        event: event_history_features(event, history, global_history)
        for event in SUPPORTED_EVENTS
    }
    release_ranges: dict[str, dict[str, float]] = {}
    for event in SUPPORTED_EVENTS:
        values = [
            abs(float(row["reaction"]["release_move"]))
            for row in rows_15
            if row["event"] == event
        ]
        release_ranges[event] = {
            "median_usd": round(float(np.median(values)), 4),
            "p75_usd": round(float(np.quantile(values, 0.75)), 4),
            "samples": len(values),
        }
    return {
        "artifact_version": 4,
        "supported_events": list(SUPPORTED_EVENTS),
        "trained_through": rows_15[-1]["release_utc"],
        "feature_leads": [15, 30],
        "preliminary_only_leads": [30],
        "models_by_lead": {
            15: fit_components(rows_15),
            30: fit_components(rows_30),
        },
        "policies_by_lead": {
            lead: {
                event: asdict(policy)
                for event, policy in policies.items()
            }
            for lead, policies in policies_by_lead.items()
        },
        "fomc_model": fit_fomc_model(rows_30),
        "event_history": dict(history),
        "history_features": final_history_features,
        "expected_release_range_by_event": release_ranges,
        "policy_note": (
            "NFP/CPI calls require a confidence threshold selected before the "
            "May-August 2026 holdout and, when configured, agreement with a "
            "history component. FOMC calls require history/model agreement."
        ),
    }


def artifact_prediction(
    artifact: dict,
    event: str,
    lead: int,
    features: list[float],
    features_30: list[float],
) -> dict:
    event = event.upper()
    if event not in SUPPORTED_EVENTS:
        raise ValueError(f"V4 supports only {', '.join(SUPPORTED_EVENTS)}.")
    history = artifact["event_history"].get(event, [])
    if event == "FOMC":
        probability_buy = model_probability_positive(
            artifact["fomc_model"],
            features_30,
        )
        result = fomc_agreement_prediction(history, probability_buy)
    else:
        model = artifact["models_by_lead"][lead]
        components = component_probabilities(
            model,
            [{"event": event, "features": features, "target": "BUY"}],
        )[0]
        policy = SelectivePolicy(**artifact["policies_by_lead"][lead][event])
        result = selective_prediction(components, policy, history)
        result["components"] = components
    if lead in artifact.get("preliminary_only_leads", []):
        result["prediction"] = "NO CALL"
        result["gates"]["final_t15_required"] = False
        if "final_t15_required" not in result["failed_gates"]:
            result["failed_gates"].append("final_t15_required")
    mapping = {"BUY": "POSITIVE", "SELL": "NEGATIVE", "NO CALL": "NO CALL"}
    return {
        **result,
        "prediction": mapping[result["prediction"]],
        "bias": mapping[result["bias"]],
        "probability_positive": result["probability_buy"],
        "probability_negative": result["probability_sell"],
    }
