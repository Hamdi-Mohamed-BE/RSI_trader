from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

import numpy as np
from sklearn.ensemble import ExtraTreesClassifier

from gold_direction_rules import rule_direction


FOMC_HISTORY_RULE = "inverse_majority_5"
FOMC_MODEL_FEATURE_COUNT = 18
FOMC_AGREEMENT_CONFIDENCE = 0.65
FOMC_CONFLICT_CONFIDENCE = 0.52


def binary_gold_direction(move_usd: float) -> str:
    return "POSITIVE" if move_usd >= 0 else "NEGATIVE"


def make_fomc_model() -> ExtraTreesClassifier:
    return ExtraTreesClassifier(
        n_estimators=500,
        min_samples_leaf=8,
        max_features=0.75,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )


def fomc_model_vector(features_30: Iterable[float]) -> np.ndarray:
    values = np.asarray(list(features_30), dtype=float)
    if len(values) < FOMC_MODEL_FEATURE_COUNT:
        raise ValueError(
            f"FOMC T-30 model needs at least {FOMC_MODEL_FEATURE_COUNT} features."
        )
    return values[:FOMC_MODEL_FEATURE_COUNT]


def fit_fomc_model(rows: list[dict]) -> ExtraTreesClassifier:
    selected = [row for row in rows if row["event"] == "FOMC"]
    if len(selected) < 20:
        raise ValueError("At least 20 historical FOMC samples are required.")
    x = np.asarray(
        [fomc_model_vector(row["features"]) for row in selected],
        dtype=float,
    )
    y = np.asarray(
        [
            row.get("binary_target")
            or binary_gold_direction(float(row["reaction"]["release_move"]))
            for row in selected
        ]
    )
    return make_fomc_model().fit(x, y)


def model_probability_positive(
    model: ExtraTreesClassifier,
    features_30: Iterable[float],
) -> float:
    vector = fomc_model_vector(features_30).reshape(1, -1)
    probabilities = model.predict_proba(vector)[0]
    by_class = {
        str(label): float(probability)
        for label, probability in zip(model.classes_, probabilities)
    }
    return by_class["POSITIVE"]


def pricing_context(
    *,
    current_lower: float | None,
    current_upper: float | None,
    cut_25_probability: float | None,
    hold_probability: float | None,
    hike_25_probability: float | None,
    cut_50_probability: float | None = None,
    hike_50_probability: float | None = None,
) -> dict | None:
    values = (
        current_lower,
        current_upper,
        cut_25_probability,
        hold_probability,
        hike_25_probability,
        cut_50_probability,
        hike_50_probability,
    )
    if all(value is None for value in values):
        return None
    if current_lower is None or current_upper is None:
        raise ValueError(
            "FOMC current target lower and upper bounds are both required."
        )
    if current_lower >= current_upper:
        raise ValueError("FOMC target lower bound must be below the upper bound.")

    raw = {
        "cut_50bp": float(cut_50_probability or 0.0),
        "cut_25bp": float(cut_25_probability or 0.0),
        "hold": float(hold_probability or 0.0),
        "hike_25bp": float(hike_25_probability or 0.0),
        "hike_50bp": float(hike_50_probability or 0.0),
    }
    if any(value < 0 for value in raw.values()):
        raise ValueError("FedWatch probabilities cannot be negative.")
    total = sum(raw.values())
    if total <= 0:
        raise ValueError("At least one FedWatch probability must be greater than zero.")
    normalized = {name: value / total for name, value in raw.items()}
    midpoint = (float(current_lower) + float(current_upper)) / 2
    outcomes = {
        "cut_50bp": midpoint - 0.50,
        "cut_25bp": midpoint - 0.25,
        "hold": midpoint,
        "hike_25bp": midpoint + 0.25,
        "hike_50bp": midpoint + 0.50,
    }
    modal_name = max(normalized, key=normalized.get)
    ranked_probabilities = sorted(normalized.values(), reverse=True)
    modal_gap = ranked_probabilities[0] - ranked_probabilities[1]
    modal_probability = normalized[modal_name]
    modal_midpoint = outcomes[modal_name]
    weighted_midpoint = sum(
        normalized[name] * outcomes[name]
        for name in normalized
    )
    surprise_bps = 100 * (modal_midpoint - weighted_midpoint)

    if abs(surprise_bps) < 1.0 or modal_gap < 0.05:
        direction = None
        confidence = 0.50
    else:
        direction = "POSITIVE" if surprise_bps < 0 else "NEGATIVE"
        confidence = min(
            0.60,
            0.50
            + 0.06 * modal_probability
            + 0.008 * abs(surprise_bps),
        )

    return {
        "probabilities_pct": {
            name: round(100 * probability, 3)
            for name, probability in normalized.items()
        },
        "current_target_range_pct": [
            float(current_lower),
            float(current_upper),
        ],
        "modal_outcome": modal_name,
        "modal_probability_pct": round(100 * modal_probability, 3),
        "modal_probability_gap_pct": round(100 * modal_gap, 3),
        "modal_midpoint_pct": round(modal_midpoint, 4),
        "weighted_midpoint_pct": round(weighted_midpoint, 4),
        "modal_surprise_bps": round(surprise_bps, 3),
        "gold_direction": direction,
        "confidence": confidence,
        "interpretation": (
            "The modal outcome is dovish relative to the probability-weighted "
            "target and is therefore positive for gold."
            if direction == "POSITIVE"
            else (
                "The modal outcome is hawkish relative to the probability-weighted "
                "target and is therefore negative for gold."
                if direction == "NEGATIVE"
                else (
                    "The modal outcome is too close to the weighted target or "
                    "too closely tied with another outcome to resolve direction."
                )
            )
        ),
    }


def combine_fomc_decision(
    *,
    history_labels: Iterable[str],
    model_probability_positive_value: float,
    pricing: dict | None = None,
) -> dict:
    labels = list(history_labels)
    history_direction = rule_direction(FOMC_HISTORY_RULE, labels)
    model_direction = (
        "POSITIVE"
        if model_probability_positive_value >= 0.5
        else "NEGATIVE"
    )
    components_agree = history_direction == model_direction

    if components_agree:
        direction = history_direction
        if (
            pricing
            and pricing.get("gold_direction")
            and pricing["gold_direction"] != direction
        ):
            confidence = 0.55
            tier = "LOW"
            resolver = "agreement_downgraded_by_fedwatch_conflict"
        else:
            confidence = FOMC_AGREEMENT_CONFIDENCE
            tier = "HIGH"
            resolver = "history_model_agreement"
    elif pricing and pricing.get("gold_direction"):
        direction = str(pricing["gold_direction"])
        confidence = float(pricing["confidence"])
        tier = "LOW"
        resolver = "fedwatch_modal_vs_weighted_conflict_resolver"
    else:
        direction = history_direction
        confidence = FOMC_CONFLICT_CONFIDENCE
        tier = "LOW"
        resolver = "unresolved_conflict_history_fallback"

    probability_positive = (
        confidence if direction == "POSITIVE" else 1 - confidence
    )
    return {
        "gold_impact": direction,
        "confidence": confidence,
        "probability_positive": probability_positive,
        "probability_negative": 1 - probability_positive,
        "direction_rule": "fomc_leakage_safe_ensemble_v1",
        "confidence_tier": tier,
        "resolver": resolver,
        "components_agree": components_agree,
        "history_direction": history_direction,
        "model_direction": model_direction,
        "model_probability_positive": float(
            model_probability_positive_value
        ),
        "fedwatch_pricing": pricing,
    }


def fomc_release_phases(release_utc: datetime) -> list[dict]:
    statement = release_utc.astimezone(timezone.utc)
    press = statement + timedelta(minutes=30)
    return [
        {
            "phase": "statement",
            "starts_at_utc": statement.isoformat(),
            "purpose": (
                "Score the rate decision, vote, statement wording, and dot plot "
                "when one is published."
            ),
        },
        {
            "phase": "press_conference",
            "starts_at_utc": press.isoformat(),
            "purpose": (
                "Treat the Chair's opening remarks and answers as a new shock. "
                "Do not carry statement confidence into this phase."
            ),
        },
    ]
