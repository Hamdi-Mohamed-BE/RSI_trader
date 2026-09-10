from __future__ import annotations

from collections import defaultdict
from datetime import date

import numpy as np

from gold_direction_rules import rule_direction
from news_core import EVENTS, event_history_features
from news_ensemble import component_probabilities, fit_components, strategy_probability
from news_v4 import binary_rows


SUPPORTED_EVENTS = ("NFP", "CPI", "FOMC")
FULL_COVERAGE_POLICY = {
    "NFP": "inverse_last",
    "CPI": "event_history",
    "FOMC": "inverse_majority_5",
}
VALIDATION_START = date(2021, 7, 30)
CONFIDENCE_FLOOR = 0.50
CONFIDENCE_CAP = 0.68
CONFIRMATION_STRATEGY = "balanced_ensemble"


def _impact(label: str) -> str:
    normalized = str(label).upper()
    if normalized in {"BUY", "POSITIVE"}:
        return "POSITIVE"
    if normalized in {"SELL", "NEGATIVE"}:
        return "NEGATIVE"
    raise ValueError(f"Unsupported direction label: {label}")


def _trade_label(label: str) -> str:
    return "BUY" if _impact(label) == "POSITIVE" else "SELL"


def validation_reliability(
    rows: list[dict],
    *,
    start: date = VALIDATION_START,
    end: date | None = None,
) -> dict[str, dict]:
    history: dict[str, list[str]] = defaultdict(list)
    scores = {event: {"events": 0, "wins": 0} for event in SUPPORTED_EVENTS}
    for row in sorted(rows, key=lambda item: item["release_utc"]):
        event = row["event"]
        if event not in SUPPORTED_EVENTS:
            continue
        released = date.fromisoformat(row["release_utc"][:10])
        actual = _impact(row["target"])
        prediction = rule_direction(FULL_COVERAGE_POLICY[event], history[event])
        if released >= start and (end is None or released < end):
            scores[event]["events"] += 1
            scores[event]["wins"] += int(prediction == actual)
        history[event].append(actual)

    for event, values in scores.items():
        events = values["events"]
        wins = values["wins"]
        values["losses"] = events - wins
        values["accuracy_pct"] = round(100 * wins / events, 2) if events else 0.0
        values["smoothed_reliability"] = (wins + 2) / (events + 4) if events else 0.5
    return scores


def full_coverage_decision(
    event: str,
    history_labels: list[str],
    reliability: float,
    model_votes: list[dict] | None = None,
) -> dict:
    event = event.upper()
    if event not in SUPPORTED_EVENTS:
        raise ValueError(f"V7 supports only {', '.join(SUPPORTED_EVENTS)}.")
    history = [_impact(label) for label in history_labels]
    direction = rule_direction(FULL_COVERAGE_POLICY[event], history)
    votes = model_votes or []
    agreeing = sum(vote["direction"] == direction for vote in votes)

    confidence = min(CONFIDENCE_CAP, max(CONFIDENCE_FLOOR, float(reliability)))
    if votes and agreeing == len(votes):
        confidence = min(CONFIDENCE_CAP, confidence + 0.02)
    elif votes and agreeing == 0:
        confidence = max(CONFIDENCE_FLOOR, confidence - 0.03)

    if confidence >= 0.64 and (not votes or agreeing == len(votes)):
        tier = "HIGH"
    elif confidence >= 0.58:
        tier = "STANDARD"
    else:
        tier = "LOW"
    probability_positive = confidence if direction == "POSITIVE" else 1 - confidence
    return {
        "prediction": direction,
        "bias": direction,
        "confidence": confidence,
        "probability_positive": probability_positive,
        "probability_negative": 1 - probability_positive,
        "history_bias": _trade_label(direction),
        "strategy": f"full_coverage_{FULL_COVERAGE_POLICY[event]}",
        "confidence_tier": tier,
        "coverage_mode": "FULL",
        "gates": {"full_coverage_direction": True},
        "failed_gates": [],
        "confirmation": {
            "strategy": CONFIRMATION_STRATEGY,
            "votes": votes,
            "agreeing_votes": agreeing,
            "total_votes": len(votes),
            "changes_primary_direction": False,
        },
    }


def _direction_histories(rows: list[dict]) -> dict[str, list[str]]:
    history: dict[str, list[str]] = defaultdict(list)
    for row in sorted(rows, key=lambda item: item["release_utc"]):
        if row["event"] in SUPPORTED_EVENTS:
            history[row["event"]].append(_impact(row["target"]))
    return dict(history)


def fit_live_artifact(rows_by_lead: dict[int, list[dict]]) -> dict:
    rows_15 = binary_rows(rows_by_lead[15])
    rows_30 = binary_rows(rows_by_lead[30])
    reliability = validation_reliability(rows_15)
    trade_history: dict[str, list[str]] = defaultdict(list)
    global_history: list[str] = []
    for row in rows_15:
        trade_history[row["event"]].append(row["target"])
        global_history.append(row["target"])

    ranges = {}
    for event in SUPPORTED_EVENTS:
        values = [
            abs(float(row["reaction"]["release_move"]))
            for row in rows_15
            if row["event"] == event
        ]
        ranges[event] = {
            "median_usd": round(float(np.median(values)), 4),
            "p75_usd": round(float(np.quantile(values, 0.75)), 4),
            "samples": len(values),
        }

    return {
        "artifact_version": 7,
        "supported_events": list(SUPPORTED_EVENTS),
        "trained_through": rows_15[-1]["release_utc"],
        "coverage_mode": "FULL",
        "direction_policy": dict(FULL_COVERAGE_POLICY),
        "validation_start": VALIDATION_START.isoformat(),
        "validation_reliability": reliability,
        "event_history": _direction_histories(rows_15),
        "history_features": {
            event: event_history_features(event, trade_history, global_history)
            for event in SUPPORTED_EVENTS
        },
        "models_by_lead": {
            15: fit_components(rows_15),
            30: fit_components(rows_30),
        },
        "expected_release_range_by_event": ranges,
        "policy_note": (
            "Every supported release gets a direction. NFP uses inverse-last, CPI uses "
            "expanding event history, and FOMC uses inverse-majority-5. T-15/T-30 "
            "ensembles confirm confidence but never rewrite the validated primary rule."
        ),
    }


def _model_vote(artifact: dict, lead: int, event: str, features: list[float]) -> dict:
    components = component_probabilities(
        artifact["models_by_lead"][lead],
        [{"event": event, "features": features, "target": "BUY"}],
    )[0]
    probability_positive = strategy_probability(components, CONFIRMATION_STRATEGY)
    return {
        "lead_minutes": lead,
        "direction": "POSITIVE" if probability_positive >= 0.5 else "NEGATIVE",
        "probability_positive": probability_positive,
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
        raise ValueError(f"V7 supports only {', '.join(SUPPORTED_EVENTS)}.")
    votes = [_model_vote(artifact, lead, event, features)]
    if lead != 30:
        votes.append(_model_vote(artifact, 30, event, features_30))
    reliability = artifact["validation_reliability"][event]["smoothed_reliability"]
    return full_coverage_decision(
        event,
        artifact["event_history"].get(event, []),
        reliability,
        votes,
    )
