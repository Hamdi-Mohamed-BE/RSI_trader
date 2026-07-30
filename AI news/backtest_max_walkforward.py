from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import date

import joblib
import numpy as np

from backtest_recent_walkforward import (
    END_DATE,
START_DATE,
    executable_pips,
)
from news_core import (
    EVENTS,
    ROOT,
    annual_spreads,
    build_samples,
    history_snapshot,
)
from news_ensemble import (
    EventPolicy,
    component_probabilities,
    expanding_oof_components,
    fit_components,
    policy_from_dict,
    policy_prediction,
    policy_to_dict,
    select_event_policies,
)


LEADS = (15, 30)
POLICY_START_DATE = date(2021, 5, 30)
GOLD_PIP_SIZE = 0.01
OUTPUT_JSON = ROOT / "max_2m_walkforward.json"
OUTPUT_CSV = ROOT / "max_2m_walkforward.csv"
OUTPUT_MD = ROOT / "MAX_2M_WALKFORWARD.md"
MODEL_PATH = ROOT / "models" / "gold_news_max_ensemble.joblib"


@dataclass(frozen=True)
class DualPolicy:
    event: str
    weight_15m: float
    threshold: float
    require_agreement: bool
    selection_samples: int
    selected_calls: int
    selected_accuracy_pct: float
    selected_coverage_pct: float
    selected_score: float


def _date(row: dict) -> date:
    return date.fromisoformat(row["release_utc"][:10])


def _selection_score(correct: int, calls: int, total: int) -> float:
    if calls <= 0 or total <= 0:
        return -1.0
    accuracy = correct / calls
    coverage = calls / total
    return float((accuracy - 0.5) * math.sqrt(calls) + 0.08 * math.sqrt(coverage))


def prepared_lead(lead: int) -> dict:
    rows, audit = build_samples(lead)
    rows = sorted(rows, key=lambda row: row["release_utc"])
    selection_rows = [row for row in rows if _date(row) < START_DATE]
    all_oof = expanding_oof_components(selection_rows)
    oof = [row for row in all_oof if _date(row) >= POLICY_START_DATE]
    policies = select_event_policies(oof)
    oof_predictions = []
    for row in oof:
        policy = policies[row["event"]]
        prediction = policy_prediction(row["components"], policy)
        oof_predictions.append({**row, **prediction})
    return {
        "lead": lead,
        "rows": rows,
        "audit": audit,
        "selection_rows": selection_rows,
        "oof": oof_predictions,
        "policies": policies,
    }


def _joined_oof(prepared: dict[int, dict]) -> list[dict]:
    by_lead = {
        lead: {row["release_utc"]: row for row in payload["oof"]}
        for lead, payload in prepared.items()
    }
    joined = []
    for release in sorted(set(by_lead[15]) & set(by_lead[30])):
        row_15 = by_lead[15][release]
        row_30 = by_lead[30][release]
        if row_15["event"] != row_30["event"]:
            continue
        joined.append(
            {
                "release_utc": release,
                "event": row_15["event"],
                "target": row_15["target"],
                "probability_buy_15": row_15["probability_buy"],
                "probability_buy_30": row_30["probability_buy"],
            }
        )
    return joined


def select_dual_policies(joined: list[dict]) -> dict[str, DualPolicy]:
    policies = {}
    for event in EVENTS:
        rows = [row for row in joined if row["event"] == event]
        best = None
        for weight_15 in (0.25, 0.50, 0.75):
            for threshold in (0.55, 0.575, 0.60, 0.625, 0.65, 0.675, 0.70, 0.725):
                for require_agreement in (False, True):
                    calls = 0
                    correct = 0
                    for row in rows:
                        p15 = row["probability_buy_15"]
                        p30 = row["probability_buy_30"]
                        direction_15 = "BUY" if p15 >= 0.5 else "SELL"
                        direction_30 = "BUY" if p30 >= 0.5 else "SELL"
                        if require_agreement and direction_15 != direction_30:
                            continue
                        probability_buy = weight_15 * p15 + (1 - weight_15) * p30
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
                        correct / calls,
                        calls,
                        weight_15,
                        threshold,
                        require_agreement,
                    )
                    if best is None or candidate[:3] > best[:3]:
                        best = candidate
        if best is None:
            policies[event] = DualPolicy(
                event=event,
                weight_15m=0.5,
                threshold=1.0,
                require_agreement=True,
                selection_samples=len(rows),
                selected_calls=0,
                selected_accuracy_pct=0.0,
                selected_coverage_pct=0.0,
                selected_score=-1.0,
            )
            continue
        score, accuracy, calls, weight_15, threshold, require_agreement = best
        if accuracy < 0.55:
            threshold = 1.0
            calls = 0
        policies[event] = DualPolicy(
            event=event,
            weight_15m=weight_15,
            threshold=threshold,
            require_agreement=require_agreement,
            selection_samples=len(rows),
            selected_calls=calls,
            selected_accuracy_pct=round(100 * accuracy, 2),
            selected_coverage_pct=round(100 * calls / max(len(rows), 1), 2),
            selected_score=round(score, 6),
        )
    return policies


def dual_prediction(
    prediction_15: dict,
    prediction_30: dict,
    policy: DualPolicy,
) -> dict:
    p15 = prediction_15["probability_buy"]
    p30 = prediction_30["probability_buy"]
    direction_15 = "BUY" if p15 >= 0.5 else "SELL"
    direction_30 = "BUY" if p30 >= 0.5 else "SELL"
    probability_buy = policy.weight_15m * p15 + (1 - policy.weight_15m) * p30
    probability_sell = 1 - probability_buy
    direction = "BUY" if probability_buy >= 0.5 else "SELL"
    confidence = max(probability_buy, probability_sell)
    agreement = direction_15 == direction_30
    # The blend is diagnostic only. It must never manufacture a call when the
    # independently selected T-15 policy abstains.
    prediction = prediction_15["prediction"]
    return {
        "prediction": prediction,
        "model_bias": prediction_15["bias"],
        "confidence_pct": round(100 * prediction_15["confidence"], 2),
        "probability_buy_pct": round(100 * prediction_15["probability_buy"], 2),
        "probability_sell_pct": round(100 * prediction_15["probability_sell"], 2),
        "lead_agreement": agreement,
        "initial_30m_bias": direction_30,
        "refresh_15m_bias": direction_15,
        "policy_threshold": prediction_15["threshold"],
        "policy_weight_15m": 1.0,
        "policy_require_agreement": False,
        "shadow_blend_bias": direction,
        "shadow_blend_confidence_pct": round(100 * confidence, 2),
        "shadow_blend_threshold": policy.threshold,
    }


def walk_forward_lead(payload: dict) -> list[dict]:
    rows = payload["rows"]
    policies: dict[str, EventPolicy] = payload["policies"]
    test = [row for row in rows if START_DATE <= _date(row) < END_DATE]
    outputs = []
    for row in test:
        training = [item for item in rows if _date(item) < _date(row)]
        fitted = fit_components(training)
        components = component_probabilities(fitted, [row])[0]
        prediction = policy_prediction(components, policies[row["event"]])
        outputs.append(
            {
                "release_utc": row["release_utc"],
                "event": row["event"],
                "target": row["target"],
                "training_samples": fitted["training_samples"],
                **prediction,
            }
        )
    return outputs


def _summary(rows: list[dict]) -> dict:
    called = [row for row in rows if row["prediction"] in {"BUY", "SELL"}]
    wins = [row for row in called if row["captured_or_lost_pips"] > 0]
    losses = [row for row in called if row["captured_or_lost_pips"] < 0]
    gross_win = sum(row["captured_or_lost_pips"] for row in wins)
    gross_loss = -sum(row["captured_or_lost_pips"] for row in losses)
    win_rate = len(wins) / len(called) if called else 0.0
    if called:
        z = 1.96
        denominator = 1 + z * z / len(called)
        center = (win_rate + z * z / (2 * len(called))) / denominator
        margin = (
            z
            * math.sqrt(
                win_rate * (1 - win_rate) / len(called)
                + z * z / (4 * len(called) ** 2)
            )
            / denominator
        )
        win_rate_interval = [
            round(100 * max(0.0, center - margin), 2),
            round(100 * min(1.0, center + margin), 2),
        ]
    else:
        win_rate_interval = None
    directional = [
        row for row in called if row["actual_outcome"] in {"BUY", "SELL"}
    ]
    return {
        "events": len(rows),
        "called_trades": len(called),
        "no_trades": len(rows) - len(called),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(100 * win_rate, 2),
        "win_rate_wilson_95_pct": win_rate_interval,
        "direction_accuracy_pct": (
            round(
                100
                * sum(row["prediction"] == row["actual_outcome"] for row in directional)
                / len(directional),
                2,
            )
            if directional
            else 0.0
        ),
        "coverage_pct": round(100 * len(called) / max(len(rows), 1), 2),
        "net_pips": round(
            sum(row["captured_or_lost_pips"] for row in called),
            1,
        ),
        "gross_win_pips": round(gross_win, 1),
        "gross_loss_pips": round(gross_loss, 1),
        "profit_factor_pips": (
            round(gross_win / gross_loss, 3)
            if gross_loss > 0
            else None
        ),
        "profit_factor_note": (
            "Undefined because the test contains no losing called prediction."
            if called and gross_loss == 0
            else None
        ),
    }


def _serialize_dual(policy: DualPolicy) -> dict:
    return {
        field: getattr(policy, field)
        for field in policy.__dataclass_fields__
    }


def _production_artifact(
    prepared: dict[int, dict],
    dual_policies: dict[str, DualPolicy],
) -> dict:
    leads = {}
    for lead, payload in prepared.items():
        all_rows = payload["rows"]
        expected_ranges = {}
        for event in EVENTS:
            ranges = [
                row["reaction"]["range"]
                for row in all_rows
                if row["event"] == event
            ]
            expected_ranges[event] = {
                "median_usd": round(float(np.median(ranges)), 3) if ranges else None,
                "p75_usd": round(float(np.percentile(ranges, 75)), 3) if ranges else None,
                "samples": len(ranges),
            }
        leads[lead] = {
            "components": fit_components(all_rows),
            "policies": {
                event: policy_to_dict(policy)
                for event, policy in payload["policies"].items()
            },
            "event_history_features": {
                event: history_snapshot(all_rows, event)
                for event in EVENTS
            },
            "trained_through": all_rows[-1]["release_utc"],
            "expected_ranges": expected_ranges,
        }
    return {
        "artifact_version": 3,
        "prediction_only": True,
        "execution_capability": False,
        "leads": leads,
        "dual_policies": {
            event: _serialize_dual(policy)
            for event, policy in dual_policies.items()
        },
        "final_decision_rule": (
            "Use the event-specific T-15 decision. The T-30 model is an earlier "
            "forecast and the cross-horizon blend is diagnostic only."
        ),
        "selection_window_end_exclusive": START_DATE.isoformat(),
        "supported_events": list(EVENTS),
        "external_context_rule": (
            "Point-in-time macro/cross-market context may be displayed but is not used by "
            "the fitted model until a sufficiently complete historical archive exists."
        ),
    }


def run() -> dict:
    prepared = {lead: prepared_lead(lead) for lead in LEADS}
    dual_policies = select_dual_policies(_joined_oof(prepared))
    test_by_lead = {
        lead: {
            row["release_utc"]: row
            for row in walk_forward_lead(payload)
        }
        for lead, payload in prepared.items()
    }
    days = sorted(
        {
            row["release_utc"][:10]
            for payload in prepared.values()
            for row in payload["rows"]
        }
    )
    spreads = annual_spreads(days)
    rows_by_release = {
        row["release_utc"]: row
        for row in prepared[30]["rows"]
        if START_DATE <= _date(row) < END_DATE
    }
    results = []
    for release in sorted(set(test_by_lead[15]) & set(test_by_lead[30])):
        prediction_15 = test_by_lead[15][release]
        prediction_30 = test_by_lead[30][release]
        row = rows_by_release[release]
        combined = dual_prediction(
            prediction_15,
            prediction_30,
            dual_policies[row["event"]],
        )
        execution = executable_pips(
            row,
            combined["prediction"],
            combined["model_bias"],
            spreads,
        )
        results.append(
            {
                "date": release[:10],
                "release_utc": release,
                "event": row["event"],
                **combined,
                "prediction_30m": prediction_30["prediction"],
                "confidence_30m_pct": round(100 * prediction_30["confidence"], 2),
                "prediction_15m": prediction_15["prediction"],
                "confidence_15m_pct": round(100 * prediction_15["confidence"], 2),
                "actual_outcome": row["target"],
                **execution,
            }
        )

    lead_summaries = {}
    for lead in LEADS:
        lead_rows = []
        for release, prediction in test_by_lead[lead].items():
            row = rows_by_release[release]
            execution = executable_pips(
                row,
                prediction["prediction"],
                prediction["bias"],
                spreads,
            )
            lead_rows.append(
                {
                    "prediction": prediction["prediction"],
                    "actual_outcome": row["target"],
                    **execution,
                }
            )
        lead_summaries[str(lead)] = _summary(lead_rows)

    report = {
        "methodology": {
            "window": f"{START_DATE.isoformat()} through {END_DATE.isoformat()} exclusive",
            "selection_data": (
                "All policy, blend, calibration, and threshold choices use only releases "
                f"from {POLICY_START_DATE.isoformat()} through {START_DATE.isoformat()} exclusive."
            ),
            "test_method": (
                "For every test event, component models are refit using only earlier releases. "
                "The T-15/T-30 policy remains frozen."
            ),
            "models": (
                "Global ExtraTrees and logistic models blended with event-specific "
                "ExtraTrees and logistic specialists."
            ),
            "final_decision": (
                "The event-specific T-15 refresh is final. T-30 and the cross-horizon "
                "blend are displayed as context but cannot manufacture a call."
            ),
            "calibration": "Per-event Platt calibration fitted only on expanding pre-test OOF predictions.",
            "execution": (
                "Enter at the final pre-release M1 bid/ask close and exit at the release "
                "M1 bid/ask close. One XAUUSD pip is $0.01."
            ),
            "external_data": (
                "No unavailable consensus, Treasury, DXY, order-book, or statement data is "
                "fabricated. Point-in-time stores are present but empty records do not become features."
            ),
        },
        "policies": {
            "15": {
                event: policy_to_dict(policy)
                for event, policy in prepared[15]["policies"].items()
            },
            "30": {
                event: policy_to_dict(policy)
                for event, policy in prepared[30]["policies"].items()
            },
            "shadow_dual_not_deployed": {
                event: _serialize_dual(policy)
                for event, policy in dual_policies.items()
            },
        },
        "lead_summaries": lead_summaries,
        "summary": _summary(results),
        "events": results,
    }
    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    lines = [
        "# Maximum Two-Month Walk-Forward",
        "",
        "All model, calibration, blend, and threshold choices were frozen using only "
        f"releases from {POLICY_START_DATE.isoformat()} through {START_DATE.isoformat()} exclusive.",
        "",
        "| Date | Event | T-30 | T-15 | Final | Buy | Sell | Agreement | Actual | Captured/lost |",
        "|---|---|---|---|---|---:|---:|---|---|---:|",
    ]
    for row in results:
        lines.append(
            f"| {row['date']} | {row['event']} | "
            f"{row['prediction_30m']} ({row['confidence_30m_pct']:.1f}%) | "
            f"{row['prediction_15m']} ({row['confidence_15m_pct']:.1f}%) | "
            f"{row['prediction']} ({row['confidence_pct']:.1f}%) | "
            f"{row['probability_buy_pct']:.1f}% | {row['probability_sell_pct']:.1f}% | "
            f"{'YES' if row['lead_agreement'] else 'NO'} | {row['actual_outcome']} | "
            f"{row['captured_or_lost_pips']:+.1f} pips |"
        )
    summary = report["summary"]
    lines.extend(
        [
            "",
            f"Final calls: **{summary['called_trades']} / {summary['events']}**; "
            f"win rate **{summary['win_rate_pct']:.2f}%**; "
            f"net **{summary['net_pips']:+.1f} pips**; "
            f"coverage **{summary['coverage_pct']:.2f}%**.",
            "",
            "The final result is the event-specific T-15 refresh. T-30 remains an "
            "earlier forecast and context check. A `NO TRADE` prediction captures zero pips.",
        ]
    )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(_production_artifact(prepared, dual_policies), MODEL_PATH)
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
