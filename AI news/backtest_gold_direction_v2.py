from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import date

import joblib
import numpy as np

from gold_direction_rules import (
    RULES,
    prediction_rows,
    rule_direction,
    score,
    target_direction,
)
from news_core import EVENTS, ROOT, build_samples


SELECTION_START = date(2016, 7, 30)
BROAD_START = date(2021, 7, 30)
RECENT_START = date(2024, 7, 30)
RECENT_TWO_MONTH_START = date(2026, 5, 30)
END_DATE = date(2026, 7, 30)
OUTPUT_JSON = ROOT / "gold_direction_v2.json"
OUTPUT_CSV = ROOT / "gold_direction_v2.csv"
OUTPUT_MD = ROOT / "GOLD_DIRECTION_V2.md"
MODEL_PATH = ROOT / "models" / "gold_news_direction.joblib"


def _wilson(correct: int, total: int) -> list[float]:
    if total == 0:
        return [0.0, 0.0]
    z = 1.96
    p = correct / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(
        p * (1 - p) / total + z * z / (4 * total * total)
    ) / denominator
    return [
        round(100 * max(0.0, center - margin), 2),
        round(100 * min(1.0, center + margin), 2),
    ]


def _summary(rows: list[dict]) -> dict:
    correct, total = score(rows)
    return {
        "events": total,
        "correct": correct,
        "wrong": total - correct,
        "accuracy_pct": round(100 * correct / total, 2) if total else 0.0,
        "wilson_95_pct": _wilson(correct, total),
    }


def _by_event(rows: list[dict]) -> dict[str, dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["event"]].append(row)
    return {event: _summary(grouped[event]) for event in EVENTS if grouped[event]}


def _source_rows() -> tuple[list[dict], dict]:
    samples, audit = build_samples(15)
    rows = []
    for row in samples:
        move_5m = row["reaction"]["moves"].get("5")
        rows.append(
            {
                "release_utc": row["release_utc"],
                "event": row["event"],
                "target": target_direction(
                    float(row["reaction"]["release_move"])
                ),
                "target_5m": (
                    target_direction(float(move_5m))
                    if move_5m is not None
                    else "UNAVAILABLE"
                ),
                "move_usd": round(
                    float(row["reaction"]["release_move"]),
                    6,
                ),
            }
        )
    return rows, audit


def _event_score(
    rows: list[dict],
    event: str,
    rule: str,
    start: date,
    end: date,
) -> dict:
    policy = {name: "event_history" for name in EVENTS}
    policy[event] = rule
    selected = [
        row
        for row in prediction_rows(rows, policy, start, end)
        if row["event"] == event
    ]
    return _summary(selected)


def _select_candidates(rows: list[dict]) -> tuple[dict[str, str], dict]:
    policy = {}
    audit = {}
    for event in EVENTS:
        comparisons = []
        for index, rule in enumerate(RULES):
            metrics = _event_score(
                rows,
                event,
                rule,
                SELECTION_START,
                BROAD_START,
            )
            comparisons.append({"rule": rule, **metrics, "order": index})
        best = max(
            comparisons,
            key=lambda item: (
                item["accuracy_pct"],
                item["correct"],
                -item["order"],
            ),
        )
        policy[event] = best["rule"]
        audit[event] = comparisons
    return policy, audit


def _apply_broad_guard(
    rows: list[dict],
    candidates: dict[str, str],
) -> tuple[dict[str, str], dict]:
    policy = {}
    audit = {}
    for event in EVENTS:
        candidate = candidates[event]
        baseline = _event_score(
            rows,
            event,
            "event_history",
            BROAD_START,
            RECENT_START,
        )
        challenger = _event_score(
            rows,
            event,
            candidate,
            BROAD_START,
            RECENT_START,
        )
        accepted = (
            candidate != "event_history"
            and challenger["correct"] > baseline["correct"]
        )
        policy[event] = candidate if accepted else "event_history"
        audit[event] = {
            "candidate": candidate,
            "accepted": accepted,
            "baseline": baseline,
            "challenger": challenger,
            "reason": (
                "candidate beat event-history on the broad guard"
                if accepted
                else "event-history retained; candidate did not strictly improve"
            ),
        }
    return policy, audit


def _reliability(rows: list[dict], policy: dict[str, str]) -> dict[str, float]:
    evaluated = prediction_rows(rows, policy, BROAD_START, END_DATE)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in evaluated:
        grouped[row["event"]].append(row)
    output = {}
    for event in EVENTS:
        correct, total = score(grouped[event])
        output[event] = float((correct + 2) / (total + 4))
    return output


def _update_artifact(
    rows: list[dict],
    policy: dict[str, str],
    report: dict,
) -> None:
    if not MODEL_PATH.exists():
        return
    artifact = joblib.load(MODEL_PATH)
    artifact["artifact_version"] = max(
        2,
        int(artifact.get("artifact_version", 1)),
    )
    artifact["direction_rule_policy"] = {
        "rules": policy,
        "reliability": _reliability(rows, policy),
        "selection_window": (
            f"{SELECTION_START.isoformat()} through "
            f"{BROAD_START.isoformat()} exclusive"
        ),
        "broad_guard_window": (
            f"{BROAD_START.isoformat()} through "
            f"{RECENT_START.isoformat()} exclusive"
        ),
        "recent_test_window": (
            f"{RECENT_START.isoformat()} through "
            f"{END_DATE.isoformat()} exclusive"
        ),
        "five_year_accuracy_pct": report["five_year"]["accuracy_pct"],
    }
    artifact["event_direction_history"] = {
        event: [
            row["target"]
            for row in rows
            if row["event"] == event
        ]
        for event in EVENTS
    }
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(artifact, MODEL_PATH)


def run() -> dict:
    rows, source_audit = _source_rows()
    candidates, candidate_audit = _select_candidates(rows)
    policy, guard_audit = _apply_broad_guard(rows, candidates)
    baseline_policy = {event: "event_history" for event in EVENTS}

    five_year = prediction_rows(rows, policy, BROAD_START, END_DATE)
    five_year_baseline = prediction_rows(
        rows,
        baseline_policy,
        BROAD_START,
        END_DATE,
    )
    broad = prediction_rows(rows, policy, BROAD_START, RECENT_START)
    recent = prediction_rows(rows, policy, RECENT_START, END_DATE)
    recent_baseline = prediction_rows(
        rows,
        baseline_policy,
        RECENT_START,
        END_DATE,
    )
    recent_two_month = prediction_rows(
        rows,
        policy,
        RECENT_TWO_MONTH_START,
        END_DATE,
    )
    sustained_5m = prediction_rows(
        rows,
        policy,
        BROAD_START,
        END_DATE,
        target_key="target_5m",
    )

    report = {
        "methodology": {
            "target": (
                "Binary sign of the XAUUSD release-minute midpoint move."
            ),
            "selection": (
                "Choose one of four simple event rules on the pre-2021 "
                "development window only."
            ),
            "deployment_guard": (
                "A non-baseline event rule is promoted only if it strictly "
                "beats event-history on the 2021-2024 broad guard."
            ),
            "final_test": (
                "The 2024-2026 recent window is not used by selection or the "
                "broad deployment guard."
            ),
            "source_audit": source_audit,
        },
        "production_policy": policy,
        "selected_candidates": candidates,
        "candidate_validation": candidate_audit,
        "broad_guard": guard_audit,
        "five_year": {
            **_summary(five_year),
            "by_event": _by_event(five_year),
        },
        "five_year_baseline": _summary(five_year_baseline),
        "broad_2021_2024": _summary(broad),
        "recent_2024_2026": {
            **_summary(recent),
            "by_event": _by_event(recent),
        },
        "recent_baseline": _summary(recent_baseline),
        "recent_two_month": _summary(recent_two_month),
        "five_minute_follow_through": _summary(sustained_5m),
        "events": five_year,
    }
    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(five_year[0]))
        writer.writeheader()
        writer.writerows(five_year)

    overall = report["five_year"]
    baseline = report["five_year_baseline"]
    lines = [
        "# Gold Direction Model V2",
        "",
        "This predicts information only: **POSITIVE** or **NEGATIVE** "
        "immediate impact on gold. It does not generate trades.",
        "",
        "## Validated result",
        "",
        f"- V2: **{overall['correct']}/{overall['events']} "
        f"({overall['accuracy_pct']:.2f}%)**",
        f"- Previous event-history baseline: **{baseline['correct']}/"
        f"{baseline['events']} ({baseline['accuracy_pct']:.2f}%)**",
        f"- V2 95% interval: **{overall['wilson_95_pct'][0]:.2f}% to "
        f"{overall['wilson_95_pct'][1]:.2f}%**",
        f"- Broad guard 2021-2024: **"
        f"{report['broad_2021_2024']['accuracy_pct']:.2f}%**",
        f"- Untouched recent test 2024-2026: **"
        f"{report['recent_2024_2026']['accuracy_pct']:.2f}%**",
        f"- Last two months: **"
        f"{report['recent_two_month']['accuracy_pct']:.2f}%**",
        "",
        "## Production policy",
        "",
        "| Event | Rule | Events | Correct | Accuracy |",
        "|---|---|---:|---:|---:|",
    ]
    for event in EVENTS:
        item = overall["by_event"][event]
        lines.append(
            f"| {event} | {policy[event]} | {item['events']} | "
            f"{item['correct']} | {item['accuracy_pct']:.2f}% |"
        )
    lines.extend(
        (
            "",
            "## Interpretation",
            "",
            "NFP uses the opposite of its previous release-minute direction. "
            "FOMC uses the opposite of the majority of its last five releases. "
            "GDP, CPI, and PPI retain their expanding event-history bias.",
            "",
            "The five-minute follow-through score is reported separately and "
            "does not alter the immediate-direction target.",
        )
    )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _update_artifact(rows, policy, report)
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
