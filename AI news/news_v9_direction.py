from __future__ import annotations

from news_v5 import (
    SUPPORTED_EVENTS as V5_SUPPORTED_EVENTS,
    artifact_prediction as v5_artifact_prediction,
    fit_live_artifact as fit_v5_artifact,
)


ARTIFACT_VERSION = 9
SUPPORTED_EVENTS = tuple(V5_SUPPORTED_EVENTS)


def fit_live_artifact(rows_by_lead: dict[int, list[dict]], policies_by_lead: dict) -> dict:
    artifact = fit_v5_artifact(rows_by_lead, policies_by_lead)
    artifact.update(
        {
            "artifact_version": ARTIFACT_VERSION,
            "supported_events": list(SUPPORTED_EVENTS),
            "extended_event_rules": {},
            "coverage_mode": "FULL_DIRECTION_WITH_ACTION_TIER",
            "direction_source": "validated_v5_bias",
            "policy_note": (
                "Every NFP, CPI, and FOMC release receives a direction. "
                "The original V5 gate is retained as TRADE versus LOW_CONFIDENCE; "
                "missing point-in-time consensus never receives directional weight."
            ),
        }
    )
    return artifact


def artifact_prediction(
    artifact: dict,
    event: str,
    lead: int,
    features: list[float],
    features_30: list[float],
) -> dict:
    event = event.upper()
    base = v5_artifact_prediction(
        artifact,
        event,
        lead,
        features,
        features_30,
    )
    direction = base["bias"]
    if direction not in {"POSITIVE", "NEGATIVE"}:
        raise ValueError(f"V9 received an invalid directional bias: {direction}")

    active = base["prediction"] == direction
    action_tier = "TRADE" if active else "LOW_CONFIDENCE"
    confidence = float(base["confidence"])
    return {
        **base,
        "prediction": direction,
        "bias": direction,
        "confidence": confidence,
        "confidence_tier": "STANDARD" if active else "LOW",
        "coverage_mode": "FULL_DIRECTION_WITH_ACTION_TIER",
        "action_tier": action_tier,
        "active_call_allowed": active,
        "strategy": f"v9_{base['strategy']}",
        "confirmation": {
            "agreeing_votes": 2 if active else 1,
            "total_votes": 2,
            "changes_primary_direction": True,
        },
    }
