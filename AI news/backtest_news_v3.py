from __future__ import annotations

import csv
import json
import math
import warnings
from datetime import date

import joblib

from backtest_max_walkforward import (
    END_DATE,
    POLICY_START_DATE,
    START_DATE,
    _summary,
)
from backtest_recent_walkforward import executable_pips
from news_core import EVENTS, ROOT, annual_spreads, build_samples
from news_ensemble import select_event_policies
from news_v3 import (
    HybridPolicy,
    TwoStagePolicy,
    expanding_oof_two_stage,
    fit_two_stage,
    hybrid_policy_to_dict,
    policy_to_dict,
    predict_with_hybrid_policy,
    predict_with_policy,
    select_hybrid_policies,
    select_two_stage_policies,
    two_stage_components,
)


warnings.filterwarnings("ignore", category=RuntimeWarning)
OUTPUT_JSON = ROOT / "news_v3_results.json"
OUTPUT_CSV = ROOT / "news_v3_results.csv"
OUTPUT_MD = ROOT / "NEWS_V3_RESULTS.md"
MODEL_PATH = ROOT / "models" / "gold_news_v3_candidate.joblib"
LEADS = (15, 30)


def _date(row: dict) -> date:
    return date.fromisoformat(row["release_utc"][:10])


def _prepare_lead(lead: int) -> dict:
    rows, audit = build_samples(lead)
    rows = sorted(rows, key=lambda row: row["release_utc"])
    development = [row for row in rows if _date(row) < START_DATE]
    all_oof = expanding_oof_two_stage(development)
    selection_oof = [
        row
        for row in all_oof
        if POLICY_START_DATE <= _date(row) < START_DATE
    ]
    policies = select_two_stage_policies(selection_oof)
    direction_oof = [
        {
            "release_utc": row["release_utc"],
            "event": row["event"],
            "target": row["target"],
            "components": row["components"]["direction"],
        }
        for row in selection_oof
    ]
    direction_policies = select_event_policies(direction_oof)
    hybrid_policies = select_hybrid_policies(
        selection_oof,
        direction_policies,
    )
    return {
        "lead": lead,
        "rows": rows,
        "audit": audit,
        "development": development,
        "selection_oof": selection_oof,
        "policies": policies,
        "direction_policies": direction_policies,
        "hybrid_policies": hybrid_policies,
    }


def _walk_forward(payload: dict) -> dict[str, dict]:
    outputs = {}
    rows = payload["rows"]
    policies: dict[str, HybridPolicy] = payload["hybrid_policies"]
    test = [row for row in rows if START_DATE <= _date(row) < END_DATE]
    for row in test:
        training = [item for item in rows if _date(item) < _date(row)]
        fitted = fit_two_stage(training)
        components = two_stage_components(fitted, [row])[0]
        prediction = predict_with_hybrid_policy(
            components,
            policies[row["event"]],
        )
        pure_prediction = predict_with_policy(
            components,
            payload["policies"][row["event"]],
        )
        outputs[row["release_utc"]] = {
            "release_utc": row["release_utc"],
            "event": row["event"],
            "target": row["target"],
            "reaction": row["reaction"],
            "training_samples": len(training),
            "pure_two_stage": pure_prediction,
            **prediction,
        }
    return outputs


def _format_prediction(row: dict) -> str:
    if row["prediction"] == "NO TRADE":
        confidence = 100 * row["direction_confidence"]
        return f"NO TRADE, {row['bias']} {confidence:.1f}%"
    return f"{row['prediction']} {100 * row['direction_confidence']:.1f}%"


def _horizon_outcome(reaction: dict, horizon: str) -> str:
    value = reaction.get("sustained", {}).get(horizon, "UNAVAILABLE")
    return value if value in {"BUY", "SELL", "UNCERTAIN"} else "UNAVAILABLE"


def _load_v2_rows() -> list[dict]:
    path = ROOT / "max_2m_walkforward.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("events", [])


def _summary_from_predictions(
    rows: list[dict],
    prediction_key: str,
    pips_key: str | None = None,
) -> dict:
    converted = []
    for row in rows:
        converted.append(
            {
                "prediction": row[prediction_key],
                "actual_outcome": row["actual_outcome"],
                "captured_or_lost_pips": (
                    row[pips_key or "captured_or_lost_pips"]
                    if row[prediction_key] in {"BUY", "SELL"}
                    else 0.0
                ),
            }
        )
    return _summary(converted)


def _validation_summary(
    payload: dict,
    policies: dict[str, HybridPolicy],
) -> dict:
    rows = []
    for row in payload["selection_oof"]:
        prediction = predict_with_hybrid_policy(
            row["components"],
            policies[row["event"]],
        )["prediction"]
        rows.append(
            {
                "prediction": prediction,
                "actual_outcome": row["target"],
                "captured_or_lost_pips": (
                    1.0 if prediction == row["target"] else -1.0
                )
                if prediction in {"BUY", "SELL"}
                else 0.0,
            }
        )
    return _summary(rows)


def run() -> dict:
    prepared = {lead: _prepare_lead(lead) for lead in LEADS}
    walk_forward = {
        lead: _walk_forward(payload)
        for lead, payload in prepared.items()
    }
    rows_by_release = {
        row["release_utc"]: row
        for row in prepared[15]["rows"]
        if START_DATE <= _date(row) < END_DATE
    }
    all_days = sorted(
        {
            row["release_utc"][:10]
            for payload in prepared.values()
            for row in payload["rows"]
        }
    )
    spreads = annual_spreads(all_days)
    results = []
    for release in sorted(set(walk_forward[15]) & set(walk_forward[30])):
        row = rows_by_release[release]
        final_15 = walk_forward[15][release]
        context_30 = walk_forward[30][release]
        execution = executable_pips(
            row,
            final_15["prediction"],
            final_15["bias"],
            spreads,
        )
        pure_execution = executable_pips(
            row,
            final_15["pure_two_stage"]["prediction"],
            final_15["pure_two_stage"]["bias"],
            spreads,
        )
        results.append(
            {
                "date": release[:10],
                "release_utc": release,
                "event": row["event"],
                "prediction_30m": context_30["prediction"],
                "display_30m": _format_prediction(context_30),
                "prediction_15m": final_15["prediction"],
                "display_15m": _format_prediction(final_15),
                "prediction": final_15["prediction"],
                "model_bias": final_15["bias"],
                "confidence_pct": round(
                    100 * final_15["direction_confidence"],
                    2,
                ),
                "impulse_probability_pct": round(
                    100 * final_15["impulse_probability"],
                    2,
                ),
                "ood_ratio": round(final_15["ood_ratio"], 3),
                "failed_gates": final_15["failed_gates"],
                "pure_two_stage_prediction": final_15[
                    "pure_two_stage"
                ]["prediction"],
                "pure_two_stage_pips": pure_execution[
                    "captured_or_lost_pips"
                ],
                "actual_outcome": row["target"],
                "actual_5m": _horizon_outcome(row["reaction"], "5"),
                "actual_15m": _horizon_outcome(row["reaction"], "15"),
                **execution,
            }
        )

    v3_summary = _summary(results)
    pure_two_stage_summary = _summary_from_predictions(
        results,
        "pure_two_stage_prediction",
        "pure_two_stage_pips",
    )
    v2_rows = _load_v2_rows()
    report = {
        "candidate_status": "research_only",
        "methodology": {
            "window": (
                f"{START_DATE.isoformat()} through "
                f"{END_DATE.isoformat()} exclusive"
            ),
            "architecture": (
                "The validated V2 direction engine makes the directional call. "
                "Stage A learns IMPULSE versus NO IMPULSE from every release and "
                "may only veto that call; it can never manufacture one."
            ),
            "selection": (
                "All event thresholds and gates use expanding chronological "
                "OOF predictions before the frozen two-month test."
            ),
            "final_decision": (
                "T-15 is final. T-30 is context only and cannot manufacture a call."
            ),
            "regime_guard": (
                "Distance from the historical feature distribution can force "
                "NO TRADE. It is selected using pre-test data only."
            ),
            "multi_horizon": (
                "The release-minute impulse is the primary target. Five- and "
                "fifteen-minute outcomes are retained as shadow diagnostics."
            ),
        },
        "policies": {
            str(lead): {
                event: hybrid_policy_to_dict(policy)
                for event, policy in prepared[lead][
                    "hybrid_policies"
                ].items()
            }
            for lead in LEADS
        },
        "pure_two_stage_shadow_policies": {
            str(lead): {
                event: policy_to_dict(policy)
                for event, policy in prepared[lead]["policies"].items()
            }
            for lead in LEADS
        },
        "selection_oof_summary": {
            str(lead): _validation_summary(
                prepared[lead],
                prepared[lead]["hybrid_policies"],
            )
            for lead in LEADS
        },
        "v3_summary": v3_summary,
        "pure_two_stage_shadow_summary": pure_two_stage_summary,
        "v2_cached_summary": (
            _summary(v2_rows) if v2_rows else None
        ),
        "events": results,
    }

    v2 = report["v2_cached_summary"]
    non_degrading = bool(
        v2
        and v3_summary["called_trades"] >= 2
        and v3_summary["win_rate_pct"] >= v2["win_rate_pct"]
        and v3_summary["net_pips"] >= v2["net_pips"]
        and v3_summary["called_trades"] >= v2["called_trades"]
    )
    improved = bool(
        non_degrading
        and (
            v3_summary["win_rate_pct"] > v2["win_rate_pct"]
            or v3_summary["net_pips"] > v2["net_pips"]
            or v3_summary["called_trades"] > v2["called_trades"]
        )
    )
    report["candidate_status"] = (
        "validated_for_promotion"
        if improved
        else (
            "validated_non_degrading_not_promoted"
            if non_degrading
            else "research_only_not_promoted"
        )
    )
    report["promotion_rule"] = (
        "Promote only when the frozen test has at least two calls, does not "
        "trail V2 on win rate, net pips, or call count, and strictly improves "
        "at least one of those metrics."
    )

    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    lines = [
        "# Gold News V3 Two-Stage Validation",
        "",
        f"Candidate status: **{report['candidate_status']}**",
        "",
        "| Date | Event | T-30 | Final T-15 | Actual | 5m | 15m | Captured |",
        "|---|---|---|---|---|---|---|---:|",
    ]
    for row in results:
        lines.append(
            f"| {row['date']} | {row['event']} | {row['display_30m']} | "
            f"{row['display_15m']} | {row['actual_outcome']} | "
            f"{row['actual_5m']} | {row['actual_15m']} | "
            f"{row['captured_or_lost_pips']:+.1f} pips |"
        )
    lines.extend(
        [
            "",
            "## Frozen Test",
            "",
            f"- V3: {v3_summary['called_trades']}/{v3_summary['events']} calls, "
            f"{v3_summary['win_rate_pct']:.2f}% win rate, "
            f"{v3_summary['net_pips']:+.1f} pips.",
            f"- Strict two-stage shadow: "
            f"{pure_two_stage_summary['called_trades']}/"
            f"{pure_two_stage_summary['events']} calls, "
            f"{pure_two_stage_summary['win_rate_pct']:.2f}% win rate, "
            f"{pure_two_stage_summary['net_pips']:+.1f} pips.",
        ]
    )
    if v2:
        lines.append(
            f"- V2: {v2['called_trades']}/{v2['events']} calls, "
            f"{v2['win_rate_pct']:.2f}% win rate, "
            f"{v2['net_pips']:+.1f} pips."
        )
    lines.extend(
        [
            "",
            "The 5m and 15m columns are diagnostic outcomes, not alternate "
            "targets selected after seeing the release.",
        ]
    )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    artifact = {
        "artifact_version": 4,
        "candidate_status": report["candidate_status"],
        "prediction_only": True,
        "execution_capability": False,
        "trained_through": {
            str(lead): prepared[lead]["rows"][-1]["release_utc"]
            for lead in LEADS
        },
        "models": {
            str(lead): fit_two_stage(prepared[lead]["rows"])
            for lead in LEADS
        },
        "policies": report["policies"],
        "supported_events": list(EVENTS),
    }
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(artifact, MODEL_PATH)
    return report


if __name__ == "__main__":
    result = run()
    print(
        json.dumps(
            {
                "candidate_status": result["candidate_status"],
                "v3_summary": result["v3_summary"],
                "v2_cached_summary": result["v2_cached_summary"],
            },
            indent=2,
        )
    )
