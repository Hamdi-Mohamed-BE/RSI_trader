from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import date

import numpy as np

from backtest_gold_direction import prior_probability
from news_core import EVENTS, ROOT, build_samples


START_DATE = date(2021, 7, 30)
END_DATE = date(2026, 7, 30)
OUTPUT_JSON = ROOT / "gold_direction_5y.json"
OUTPUT_CSV = ROOT / "gold_direction_5y.csv"
OUTPUT_MD = ROOT / "GOLD_DIRECTION_5Y.md"


def _date(row: dict) -> date:
    return date.fromisoformat(row["release_utc"][:10])


def _target(row: dict) -> str:
    return "POSITIVE" if row["reaction"]["release_move"] >= 0 else "NEGATIVE"


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


def summarize(rows: list[dict]) -> dict:
    events = len(rows)
    correct = sum(row["correct"] for row in rows)
    moves = [abs(row["actual_move_usd"]) for row in rows]
    return {
        "events": events,
        "correct": correct,
        "wrong": events - correct,
        "accuracy_pct": round(100 * correct / events, 2) if events else 0.0,
        "wilson_95_pct": _wilson(correct, events),
        "predicted_positive": sum(
            row["predicted_gold_impact"] == "POSITIVE" for row in rows
        ),
        "predicted_negative": sum(
            row["predicted_gold_impact"] == "NEGATIVE" for row in rows
        ),
        "actual_positive": sum(
            row["actual_gold_impact"] == "POSITIVE" for row in rows
        ),
        "actual_negative": sum(
            row["actual_gold_impact"] == "NEGATIVE" for row in rows
        ),
        "median_abs_move_usd": round(float(np.median(moves)), 3) if moves else 0.0,
        "mean_abs_move_usd": round(float(np.mean(moves)), 3) if moves else 0.0,
    }


def grouped(rows: list[dict], key) -> dict[str, dict]:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        buckets[str(key(row))].append(row)
    return {
        name: summarize(values)
        for name, values in sorted(buckets.items())
    }


def run() -> dict:
    samples, audit = build_samples(15)
    source = [
        {
            **row,
            "target_direction": _target(row),
        }
        for row in samples
    ]
    results = []
    for row in source:
        released = _date(row)
        if not START_DATE <= released < END_DATE:
            continue
        history = [
            {
                "event": prior["event"],
                "target": prior["target_direction"],
            }
            for prior in source
            if _date(prior) < released
        ]
        probability_positive = prior_probability(history, row["event"])
        predicted = (
            "POSITIVE" if probability_positive >= 0.5 else "NEGATIVE"
        )
        actual = row["target_direction"]
        move_usd = float(row["reaction"]["release_move"])
        results.append(
            {
                "release_utc": row["release_utc"],
                "month": row["release_utc"][:7],
                "year": row["release_utc"][:4],
                "event": row["event"],
                "predicted_gold_impact": predicted,
                "historical_probability_positive_pct": round(
                    100 * probability_positive,
                    2,
                ),
                "actual_gold_impact": actual,
                "actual_move_usd": round(move_usd, 3),
                "actual_move_pips": round(100 * move_usd, 1),
                "correct": predicted == actual,
            }
        )

    by_month = grouped(results, lambda row: row["month"])
    by_year = grouped(results, lambda row: row["year"])
    by_event = grouped(results, lambda row: row["event"])
    by_calendar_month = grouped(
        results,
        lambda row: date.fromisoformat(row["release_utc"][:10]).strftime("%b"),
    )
    event_month_matrix = {}
    for month in sorted(by_month):
        event_month_matrix[month] = {}
        for event in EVENTS:
            selected = [
                row
                for row in results
                if row["month"] == month and row["event"] == event
            ]
            event_month_matrix[month][event] = (
                summarize(selected) if selected else None
            )

    report = {
        "methodology": {
            "window": (
                f"{START_DATE.isoformat()} through "
                f"{END_DATE.isoformat()} exclusive"
            ),
            "target": (
                "Sign of the XAUUSD release-minute midpoint move: "
                "POSITIVE or NEGATIVE."
            ),
            "prediction_rule": (
                "For each event, use the Laplace-shrunk positive/negative rate "
                "from releases strictly before that release date."
            ),
            "leakage_control": (
                "No result from the evaluated release or a later release enters "
                "its prediction."
            ),
            "source_audit": audit,
        },
        "overall": summarize(results),
        "by_year": by_year,
        "by_month": by_month,
        "by_calendar_month": by_calendar_month,
        "by_event": by_event,
        "event_month_matrix": event_month_matrix,
        "events": results,
    }
    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    overall = report["overall"]
    lines = [
        "# Five-Year Gold Direction Replay",
        "",
        "Every release is predicted as **POSITIVE** or **NEGATIVE** for gold. "
        "This is a direction-information test, not a trading backtest.",
        "",
        "## Overall",
        "",
        f"- Events: **{overall['events']}**",
        f"- Correct: **{overall['correct']}**",
        f"- Wrong: **{overall['wrong']}**",
        f"- Accuracy: **{overall['accuracy_pct']:.2f}%**",
        f"- 95% interval: **{overall['wilson_95_pct'][0]:.2f}% to "
        f"{overall['wilson_95_pct'][1]:.2f}%**",
        "",
        "## By event",
        "",
        "| Event | Events | Correct | Accuracy | 95% interval | Median absolute move |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for event in EVENTS:
        item = by_event.get(event)
        if item:
            lines.append(
                f"| {event} | {item['events']} | {item['correct']} | "
                f"{item['accuracy_pct']:.2f}% | "
                f"{item['wilson_95_pct'][0]:.2f}-{item['wilson_95_pct'][1]:.2f}% | "
                f"${item['median_abs_move_usd']:.3f} |"
            )
    lines.extend(
        (
            "",
            "## By year",
            "",
            "| Year | Events | Correct | Accuracy |",
            "|---|---:|---:|---:|",
        )
    )
    for year, item in by_year.items():
        lines.append(
            f"| {year} | {item['events']} | {item['correct']} | "
            f"{item['accuracy_pct']:.2f}% |"
        )
    lines.extend(
        (
            "",
            "## By month",
            "",
            "| Month | Events | Correct | Accuracy | "
            "NFP | GDP | CPI | PPI | FOMC |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        )
    )
    for month, item in by_month.items():
        cells = []
        for event in EVENTS:
            event_item = event_month_matrix[month][event]
            cells.append(
                "-"
                if event_item is None
                else (
                    f"{event_item['correct']}/{event_item['events']} "
                    f"({event_item['accuracy_pct']:.0f}%)"
                )
            )
        lines.append(
            f"| {month} | {item['events']} | {item['correct']} | "
            f"{item['accuracy_pct']:.2f}% | {' | '.join(cells)} |"
        )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
