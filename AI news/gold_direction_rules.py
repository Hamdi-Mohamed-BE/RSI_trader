from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Iterable


RULES = (
    "event_history",
    "inverse_last",
    "inverse_majority_3",
    "inverse_majority_5",
)


def target_direction(move: float) -> str:
    return "POSITIVE" if move >= 0 else "NEGATIVE"


def _binary(label: str) -> int:
    return 1 if label == "POSITIVE" else 0


def rule_direction(rule: str, labels: Iterable[str]) -> str:
    history = list(labels)
    if not history:
        return "POSITIVE"
    if rule == "event_history":
        positives = sum(_binary(label) for label in history)
        probability = (positives + 2) / (len(history) + 4)
        return "POSITIVE" if probability >= 0.5 else "NEGATIVE"
    if rule == "inverse_last":
        return "NEGATIVE" if history[-1] == "POSITIVE" else "POSITIVE"
    if rule.startswith("inverse_majority_"):
        window = int(rule.rsplit("_", 1)[-1])
        recent = history[-window:]
        positives = sum(_binary(label) for label in recent)
        return "POSITIVE" if positives < len(recent) / 2 else "NEGATIVE"
    raise ValueError(f"Unknown gold-direction rule: {rule}")


def event_history_probability(labels: Iterable[str]) -> float:
    history = list(labels)
    positives = sum(_binary(label) for label in history)
    return float((positives + 2) / (len(history) + 4))


def live_rule_probability(
    rule: str,
    labels: Iterable[str],
    reliability: float,
) -> float:
    history = list(labels)
    if rule == "event_history":
        return event_history_probability(history)
    predicted = rule_direction(rule, history)
    bounded = min(0.75, max(0.5, float(reliability)))
    return bounded if predicted == "POSITIVE" else 1 - bounded


def prediction_rows(
    rows: list[dict],
    policy: dict[str, str],
    start: date,
    end: date,
    target_key: str = "target",
) -> list[dict]:
    event_history: dict[str, list[str]] = defaultdict(list)
    output = []
    for row in rows:
        released = date.fromisoformat(row["release_utc"][:10])
        labels = event_history[row["event"]]
        predicted = rule_direction(policy[row["event"]], labels)
        actual = row[target_key]
        if start <= released < end and actual in {"POSITIVE", "NEGATIVE"}:
            output.append(
                {
                    "release_utc": row["release_utc"],
                    "event": row["event"],
                    "rule": policy[row["event"]],
                    "predicted_gold_impact": predicted,
                    "actual_gold_impact": actual,
                    "correct": predicted == actual,
                    "actual_move_usd": row.get("move_usd"),
                }
            )
        if row["target"] in {"POSITIVE", "NEGATIVE"}:
            labels.append(row["target"])
    return output


def score(rows: list[dict]) -> tuple[int, int]:
    return sum(bool(row["correct"]) for row in rows), len(rows)
