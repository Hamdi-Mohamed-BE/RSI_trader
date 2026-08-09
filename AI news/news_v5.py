from __future__ import annotations

from collections import Counter

from news_v4 import (
    SUPPORTED_EVENTS,
    artifact_prediction as v4_artifact_prediction,
    fit_live_artifact as fit_v4_artifact,
)


CPI_POLICY = {
    "direction": "BUY",
    "minimum_history": 36,
    "minimum_long_run_buy_rate": 0.58,
    "recent_window": 12,
    "minimum_recent_buy_rate": 0.55,
    "confidence_cap": 0.68,
}


def _side(label: str) -> str:
    normalized = str(label).upper()
    if normalized in {"BUY", "POSITIVE"}:
        return "BUY"
    if normalized in {"SELL", "NEGATIVE"}:
        return "SELL"
    raise ValueError(f"Unsupported direction: {label}")


def cpi_regime_prediction(history_labels: list[str]) -> dict:
    history = [_side(label) for label in history_labels]
    recent = history[-CPI_POLICY["recent_window"] :]
    long_counts = Counter(history)
    recent_counts = Counter(recent)
    long_rate = (long_counts["BUY"] + 1) / (len(history) + 2)
    recent_rate = (recent_counts["BUY"] + 1) / (len(recent) + 2)
    gates = {
        "minimum_history": len(history) >= CPI_POLICY["minimum_history"],
        "long_run_regime": long_rate >= CPI_POLICY["minimum_long_run_buy_rate"],
        "recent_regime": recent_rate >= CPI_POLICY["minimum_recent_buy_rate"],
    }
    active = all(gates.values())
    probability_buy = min(
        CPI_POLICY["confidence_cap"],
        0.45 * long_rate + 0.55 * recent_rate,
    )
    probability_sell = 1.0 - probability_buy
    return {
        "prediction": "BUY" if active else "NO CALL",
        "bias": "BUY",
        "confidence": probability_buy,
        "probability_buy": probability_buy,
        "probability_sell": probability_sell,
        "probability_positive": probability_buy,
        "probability_negative": probability_sell,
        "history_bias": "BUY",
        "strategy": "cpi_positive_regime",
        "threshold": CPI_POLICY["minimum_long_run_buy_rate"],
        "gates": gates,
        "failed_gates": [name for name, passed in gates.items() if not passed],
        "history_samples": len(history),
        "long_run_positive_rate": long_rate,
        "recent_positive_rate": recent_rate,
    }


def fit_live_artifact(
    rows_by_lead: dict[int, list[dict]],
    policies_by_lead: dict,
) -> dict:
    artifact = fit_v4_artifact(rows_by_lead, policies_by_lead)
    artifact.update(
        {
            "artifact_version": 5,
            "cpi_regime_policy": dict(CPI_POLICY),
            "nfp_pre_release_calls_enabled": False,
            "policy_note": (
                "CPI may call POSITIVE only while its preselected long-run and recent "
                "positive regimes remain active. FOMC retains the frozen history/model "
                "agreement gate. NFP has no active pre-release direction because its "
                "historical edge was not stable enough. T-30 remains preliminary only."
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
    if event not in SUPPORTED_EVENTS:
        raise ValueError(f"V5 supports only {', '.join(SUPPORTED_EVENTS)}.")

    if event == "CPI" and lead == 15:
        decision = cpi_regime_prediction(
            artifact["event_history"].get("CPI", [])
        )
        mapping = {"BUY": "POSITIVE", "SELL": "NEGATIVE", "NO CALL": "NO CALL"}
        return {
            **decision,
            "prediction": mapping[decision["prediction"]],
            "bias": mapping[decision["bias"]],
        }

    base = v4_artifact_prediction(
        artifact,
        event,
        lead,
        features,
        features_30,
    )

    if event == "NFP":
        base["prediction"] = "NO CALL"
        base["gates"]["nfp_pre_release_edge"] = False
        if "nfp_pre_release_edge" not in base["failed_gates"]:
            base["failed_gates"].append("nfp_pre_release_edge")
        base["strategy"] = "nfp_shadow_bias_only"
    return base
