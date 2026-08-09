from __future__ import annotations

import csv
import json
import math
import warnings
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import joblib

from fomc_pipeline import fit_fomc_model, model_probability_positive
from gold_direction_rules import rule_direction
from news_core import FEATURE_NAMES, ROOT, build_samples, label_reaction, load_day
from news_ensemble import component_probabilities, fit_components
from news_v4 import (
    SUPPORTED_EVENTS,
    SelectivePolicy,
    binary_rows,
    expanding_oof_components_safe,
    fit_live_artifact,
    fomc_agreement_prediction,
    select_policies,
    selective_prediction,
)


HOLDOUT_START = "2026-05-08T00:00:00+00:00"
HOLDOUT_END = "2026-08-08T00:00:00+00:00"
MODEL_PATH = ROOT / "models" / "gold_news_v4.joblib"
OUTPUT_JSON = ROOT / "news_v4_3m_results.json"
OUTPUT_CSV = ROOT / "news_v4_3m_results.csv"
OUTPUT_MD = ROOT / "NEWS_V4_3M_RESULTS.md"
LEGACY_RULES = {
    "NFP": "inverse_last",
    "CPI": "event_history",
    "FOMC": "inverse_majority_5",
}

warnings.filterwarnings(
    "ignore",
    message="`sklearn.utils.parallel.delayed` should be used.*",
    category=UserWarning,
)


def _positive(label: str) -> str:
    return "POSITIVE" if label == "BUY" else "NEGATIVE"


def _augment_august_nfp(rows_15: list[dict]) -> tuple[list[dict], dict]:
    prediction_path = ROOT / "predictions" / "20260807T123000Z-nfp.json"
    if not prediction_path.exists():
        raise FileNotFoundError(
            "The saved August 7 point-in-time NFP prediction is required."
        )
    release = datetime(2026, 8, 7, 12, 30, tzinfo=timezone.utc)
    saved = json.loads(prediction_path.read_text(encoding="utf-8"))
    observed_at = datetime.fromisoformat(saved["generated_at_utc"])
    if observed_at >= release:
        raise ValueError("August 7 feature snapshot was not captured before release.")
    feature_values = saved["market_context"]["feature_values"]
    missing = [name for name in FEATURE_NAMES if name not in feature_values]
    if missing:
        raise ValueError(f"August 7 snapshot is missing features: {missing}")
    reaction = label_reaction(
        release,
        load_day("2026-08-07", "bid"),
        load_day("2026-08-07", "ask"),
        float(saved["market_context"]["atr_30m"]),
    )
    if reaction is None:
        raise RuntimeError("August 7 NFP reaction data is incomplete.")
    row = {
        "event": "NFP",
        "release_utc": release.isoformat(),
        "features": [float(feature_values[name]) for name in FEATURE_NAMES],
        "target": "BUY" if reaction["release_move"] >= 0 else "SELL",
        "reaction": reaction,
        "context": saved["market_context"],
        "point_in_time_source": str(prediction_path),
    }
    combined = [
        row
        for row in rows_15
        if row["release_utc"] != release.isoformat()
    ]
    combined.append(row)
    return sorted(combined, key=lambda item: item["release_utc"]), saved


def _wilson(wins: int, calls: int) -> list[float]:
    if calls == 0:
        return [0.0, 0.0]
    z = 1.959963984540054
    p = wins / calls
    denominator = 1 + z * z / calls
    center = (p + z * z / (2 * calls)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * calls)) / calls) / denominator
    return [round(100 * max(0.0, center - margin), 2), round(100 * min(1.0, center + margin), 2)]


def _metrics(rows: list[dict], prediction_key: str, actual_key: str = "actual") -> dict:
    called = [row for row in rows if row.get(prediction_key) not in {None, "NO CALL"}]
    wins = sum(row[prediction_key] == row[actual_key] for row in called)
    return {
        "events": len(rows),
        "calls": len(called),
        "wins": wins,
        "losses": len(called) - wins,
        "accuracy_pct": round(100 * wins / len(called), 2) if called else 0.0,
        "coverage_pct": round(100 * len(called) / len(rows), 2) if rows else 0.0,
        "wilson_95_pct": _wilson(wins, len(called)),
    }


def _frozen_predictions(
    training_15: list[dict],
    training_30: list[dict],
    holdout_15: list[dict],
    holdout_30: list[dict],
    policies_by_lead: dict[int, dict[str, SelectivePolicy]],
) -> list[dict]:
    models = {
        15: fit_components(training_15),
        30: fit_components(training_30),
    }
    fomc_model = fit_fomc_model(training_30)
    holdout_by_lead = {
        15: {row["release_utc"]: row for row in holdout_15},
        30: {row["release_utc"]: row for row in holdout_30},
    }
    history: dict[str, list[str]] = defaultdict(list)
    for row in training_15:
        history[row["event"]].append(row["target"])

    output = []
    for row in holdout_15:
        event = row["event"]
        actual = _positive(row["target"])
        legacy_labels = [_positive(label) for label in history[event]]
        legacy = rule_direction(LEGACY_RULES[event], legacy_labels)
        result = {
            "release_utc": row["release_utc"],
            "event": event,
            "actual": actual,
            "release_move_usd": round(float(row["reaction"]["release_move"]), 4),
            "t_plus_2_move_usd": row["reaction"].get("moves", {}).get("2"),
            "legacy_prediction": legacy,
            "legacy_correct": legacy == actual,
            "point_in_time_macro_available": bool(row.get("point_in_time_source")),
        }
        for lead in (30, 15):
            lead_row = holdout_by_lead[lead].get(row["release_utc"])
            prefix = f"t{lead}"
            if lead_row is None:
                result.update(
                    {
                        f"{prefix}_prediction": None,
                        f"{prefix}_bias": None,
                        f"{prefix}_confidence_pct": None,
                        f"{prefix}_history_bias": None,
                        f"{prefix}_failed_gates": ["point_in_time_snapshot_missing"],
                    }
                )
                continue
            if event == "FOMC":
                probability_buy = model_probability_positive(
                    fomc_model,
                    holdout_by_lead[30][row["release_utc"]]["features"],
                )
                decision = fomc_agreement_prediction(history[event], probability_buy)
            else:
                components = component_probabilities(
                    models[lead],
                    [lead_row],
                )[0]
                decision = selective_prediction(
                    components,
                    policies_by_lead[lead][event],
                    history[event],
                )
            prediction = (
                _positive(decision["prediction"])
                if decision["prediction"] != "NO CALL"
                else "NO CALL"
            )
            result.update(
                {
                    f"{prefix}_prediction": prediction,
                    f"{prefix}_bias": _positive(decision["bias"]),
                    f"{prefix}_confidence_pct": round(100 * decision["confidence"], 2),
                    f"{prefix}_history_bias": (
                        _positive(decision["history_bias"])
                        if decision["history_bias"]
                        else None
                    ),
                    f"{prefix}_failed_gates": decision["failed_gates"],
                }
            )
        output.append(result)
        history[event].append(row["target"])
    return output


def _policy_payload(policies_by_lead: dict[int, dict[str, SelectivePolicy]]) -> dict:
    return {
        f"t{lead}": {
            event: asdict(policy)
            for event, policy in policies.items()
        }
        for lead, policies in policies_by_lead.items()
    }


def _markdown(report: dict) -> str:
    metrics = report["holdout_metrics"]
    lines = [
        "# Gold News Direction V4 - Frozen Three-Month Replay",
        "",
        "Only NFP, CPI, and FOMC are supported. PPI and GDP are excluded from the live V4 pipeline.",
        "",
        "The model and all gates were selected using data before May 8, 2026. The evaluation window is May 8 through August 7, 2026. August 7 uses the exact T-15 feature snapshot saved before NFP.",
        "",
        "## Summary",
        "",
        "| Measure | Legacy forced direction | V4 final call | V4 shadow bias |",
        "|---|---:|---:|---:|",
        (
            f"| Accuracy | {metrics['legacy']['accuracy_pct']:.2f}% | "
            f"{metrics['t15_calls']['accuracy_pct']:.2f}% | "
            f"{metrics['t15_bias']['accuracy_pct']:.2f}% |"
        ),
        (
            f"| Calls / events | {metrics['legacy']['calls']} / {metrics['legacy']['events']} | "
            f"{metrics['t15_calls']['calls']} / {metrics['t15_calls']['events']} | "
            f"{metrics['t15_bias']['calls']} / {metrics['t15_bias']['events']} |"
        ),
        (
            f"| Coverage | {metrics['legacy']['coverage_pct']:.2f}% | "
            f"{metrics['t15_calls']['coverage_pct']:.2f}% | "
            f"{metrics['t15_bias']['coverage_pct']:.2f}% |"
        ),
        "",
        "## Event Replay",
        "",
        "| Date | Event | Legacy | V4 T-30 | V4 final T-15 | Shadow bias | Actual | Move |",
        "|---|---|---|---|---|---|---|---:|",
    ]
    for row in report["events"]:
        lines.append(
            f"| {row['release_utc'][:10]} | {row['event']} | "
            f"{row['legacy_prediction']} | {row['t30_prediction'] or 'N/A'} | "
            f"{row['t15_prediction']} | {row['t15_bias']} | {row['actual']} | "
            f"{row['release_move_usd']:+.3f} USD |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                f"V4 made {metrics['t15_calls']['calls']} active final call(s). "
                f"Its 95% Wilson interval is {metrics['t15_calls']['wilson_95_pct'][0]:.2f}% "
                f"to {metrics['t15_calls']['wilson_95_pct'][1]:.2f}%, so the tiny holdout cannot prove stability."
            ),
            "",
            "A no-call is intentional. The shadow bias is informational and must not be presented as a validated directional call.",
            "",
            "The T-30 candidate made three calls, won one, and is not promoted. Live T-30 output is preliminary bias only; the final T-15 gate is required for an active direction.",
            "",
            "Historical point-in-time consensus/revision data is not available locally. Forecast and previous values remain context-only until a licensed archive passes chronological validation.",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> dict:
    raw_15, audit_15 = build_samples(15)
    raw_30, audit_30 = build_samples(30)
    rows_15 = binary_rows(raw_15)
    rows_30 = binary_rows(raw_30)
    rows_15, august_snapshot = _augment_august_nfp(rows_15)

    training_15 = [row for row in rows_15 if row["release_utc"] < HOLDOUT_START]
    training_30 = [row for row in rows_30 if row["release_utc"] < HOLDOUT_START]
    holdout_15 = [
        row for row in rows_15 if HOLDOUT_START <= row["release_utc"] < HOLDOUT_END
    ]
    holdout_30 = [
        row for row in rows_30 if HOLDOUT_START <= row["release_utc"] < HOLDOUT_END
    ]
    expected_counts = {"NFP": 4, "CPI": 3, "FOMC": 2}
    actual_counts = Counter(row["event"] for row in holdout_15)
    if dict(actual_counts) != expected_counts:
        raise RuntimeError(
            f"Incomplete three-month holdout: expected {expected_counts}, got {dict(actual_counts)}."
        )

    policies_by_lead = {}
    for lead, training in ((15, training_15), (30, training_30)):
        oof = expanding_oof_components_safe(training)
        policies_by_lead[lead] = select_policies(oof, training)

    events = _frozen_predictions(
        training_15,
        training_30,
        holdout_15,
        holdout_30,
        policies_by_lead,
    )
    bias_rows = [
        {**row, "t15_bias_prediction": row["t15_bias"]}
        for row in events
    ]
    report = {
        "methodology": {
            "supported_events": list(SUPPORTED_EVENTS),
            "excluded_events": ["PPI", "GDP"],
            "holdout_start_utc": HOLDOUT_START,
            "holdout_end_utc_exclusive": HOLDOUT_END,
            "target": "Sign of the XAUUSD release-minute bid/ask midpoint move.",
            "selection": (
                "NFP/CPI model, polarity, confidence threshold, and optional history "
                "agreement were selected on expanding out-of-fold predictions before "
                "the holdout, with separate pre-2023 development and 2023-2026 guard blocks."
            ),
            "fomc": (
                "A direction is called only when the FOMC-only T-30 model agrees "
                "with the leakage-safe inverse-majority-five history component."
            ),
            "abstention": "Failed confidence or agreement gates produce NO CALL.",
            "production_promotion": (
                "The frozen T-30 candidate scored 1/3 in this holdout and is not "
                "promoted. Live T-30 output is preliminary bias only; an active "
                "direction requires the final T-15 gate."
            ),
            "macro_archive_limit": (
                "No historical point-in-time consensus/revision archive is available. "
                "Macro values are context-only and were not backfilled from post-release data."
            ),
            "august_7_snapshot_generated_at_utc": august_snapshot["generated_at_utc"],
        },
        "data_audit": {"t15": audit_15, "t30": audit_30},
        "selected_policies": _policy_payload(policies_by_lead),
        "holdout_metrics": {
            "legacy": _metrics(events, "legacy_prediction"),
            "t30_calls": _metrics(events, "t30_prediction"),
            "t15_calls": _metrics(events, "t15_prediction"),
            "t15_bias": _metrics(bias_rows, "t15_bias_prediction"),
        },
        "event_metrics": {
            event: {
                "legacy": _metrics(
                    [row for row in events if row["event"] == event],
                    "legacy_prediction",
                ),
                "t15_calls": _metrics(
                    [row for row in events if row["event"] == event],
                    "t15_prediction",
                ),
            }
            for event in SUPPORTED_EVENTS
        },
        "events": events,
    }

    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(events[0]))
        writer.writeheader()
        writer.writerows(events)
    OUTPUT_MD.write_text(_markdown(report), encoding="utf-8")

    production_artifact = fit_live_artifact(
        {15: rows_15, 30: rows_30},
        policies_by_lead,
    )
    production_artifact["frozen_holdout_report"] = {
        "path": str(OUTPUT_JSON),
        "metrics": report["holdout_metrics"],
    }
    joblib.dump(production_artifact, MODEL_PATH)
    return report


if __name__ == "__main__":
    result = run()
    print(json.dumps(result["holdout_metrics"], indent=2))
    print(f"Saved {OUTPUT_MD}")
    print(f"Saved {MODEL_PATH}")
