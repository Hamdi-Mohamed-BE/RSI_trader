from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import date, datetime, timezone

import joblib

from news_core import ROOT, build_samples
from news_v7_full_coverage import (
    FULL_COVERAGE_POLICY,
    SUPPORTED_EVENTS,
    fit_live_artifact,
    full_coverage_decision,
    validation_reliability,
)


START = date(2025, 9, 10)
END = date(2026, 9, 10)
RECENT_START = date(2026, 6, 10)
MODEL_PATH = ROOT / "models" / "gold_news_v7_full_coverage.joblib"
OUTPUT_JSON = ROOT / "news_v7_full_coverage_results.json"
OUTPUT_CSV = ROOT / "news_v7_full_coverage_results.csv"
OUTPUT_MD = ROOT / "NEWS_V7_FULL_COVERAGE_RESULTS.md"
V6_ONE_YEAR = ROOT / "news_v6_fxmacro_1y_results.json"
V6_THREE_MONTH = ROOT / "news_v6_fxmacro_3m_results.json"


def _wilson(wins: int, events: int) -> list[float]:
    if not events:
        return [0.0, 0.0]
    z = 1.959963984540054
    p = wins / events
    denominator = 1 + z * z / events
    center = (p + z * z / (2 * events)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * events)) / events) / denominator
    return [round(100 * (center - margin), 2), round(100 * (center + margin), 2)]


def _metrics(rows: list[dict]) -> dict:
    wins = sum(row["correct"] for row in rows)
    return {
        "events": len(rows),
        "directions": len(rows),
        "wins": wins,
        "losses": len(rows) - wins,
        "accuracy_pct": round(100 * wins / len(rows), 2) if rows else 0.0,
        "coverage_pct": 100.0 if rows else 0.0,
        "wilson_95_pct": _wilson(wins, len(rows)),
    }


def _utc(value: str) -> str:
    parsed = datetime.fromisoformat(value).astimezone(timezone.utc)
    return parsed.isoformat()


def _source_rows(samples: list[dict]) -> list[dict]:
    rows = [
        {
            "release_utc": _utc(row["release_utc"]),
            "event": row["event"],
            "target": "POSITIVE" if float(row["reaction"]["release_move"]) >= 0 else "NEGATIVE",
            "move_usd": round(float(row["reaction"]["release_move"]), 4),
        }
        for row in samples
        if row["event"] in SUPPORTED_EVENTS
    ]
    unique = {row["release_utc"]: row for row in rows}
    return sorted(unique.values(), key=lambda row: row["release_utc"])


def _replay(
    rows: list[dict],
    reliability: dict[str, dict],
    *,
    start: date = START,
    end: date = END,
) -> list[dict]:
    history: dict[str, list[str]] = defaultdict(list)
    output = []
    for row in rows:
        event = row["event"]
        decision = full_coverage_decision(
            event,
            history[event],
            reliability[event]["smoothed_reliability"],
        )
        released = date.fromisoformat(row["release_utc"][:10])
        if start <= released < end:
            output.append(
                {
                    "release_utc": row["release_utc"],
                    "event": event,
                    "prediction": decision["prediction"],
                    "confidence_pct": round(100 * decision["confidence"], 2),
                    "confidence_tier": decision["confidence_tier"],
                    "strategy": decision["strategy"],
                    "actual": row["target"],
                    "correct": decision["prediction"] == row["target"],
                    "release_move_usd": row["move_usd"],
                }
            )
        history[event].append(row["target"])
    return output


def _markdown(report: dict) -> str:
    five_year = report["five_year_diagnostic"]
    one_year = report["one_year"]
    recent = report["recent_three_months"]
    lines = [
        "# Gold News Direction V7 - Full Coverage",
        "",
        "> Informational XAUUSD release-minute direction only. Every scorable NFP, CPI, and FOMC receives POSITIVE or NEGATIVE; confidence is not a guarantee.",
        "",
        "## Results",
        "",
        "| Window | Events | Wins | Losses | Accuracy | Coverage | 95% interval |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| Five-year diagnostic | {five_year['overall']['events']} | {five_year['overall']['wins']} | {five_year['overall']['losses']} | {five_year['overall']['accuracy_pct']:.2f}% | 100.00% | {five_year['overall']['wilson_95_pct'][0]:.2f}-{five_year['overall']['wilson_95_pct'][1]:.2f}% |",
        f"| One year | {one_year['overall']['events']} | {one_year['overall']['wins']} | {one_year['overall']['losses']} | {one_year['overall']['accuracy_pct']:.2f}% | 100.00% | {one_year['overall']['wilson_95_pct'][0]:.2f}-{one_year['overall']['wilson_95_pct'][1]:.2f}% |",
        f"| Last three months | {recent['overall']['events']} | {recent['overall']['wins']} | {recent['overall']['losses']} | {recent['overall']['accuracy_pct']:.2f}% | 100.00% | {recent['overall']['wilson_95_pct'][0]:.2f}-{recent['overall']['wilson_95_pct'][1]:.2f}% |",
        "",
        "## Coverage Tradeoff",
        "",
        "| Version | Window | Directions | Accuracy | Coverage |",
        "|---|---|---:|---:|---:|",
        f"| V6 selective | One year | {report['comparison']['v6_one_year']['calls']} / {report['comparison']['v6_one_year']['events']} | {report['comparison']['v6_one_year']['accuracy_pct']:.2f}% | {report['comparison']['v6_one_year']['coverage_pct']:.2f}% |",
        f"| V7 full | One year | {one_year['overall']['directions']} / {one_year['overall']['events']} | {one_year['overall']['accuracy_pct']:.2f}% | 100.00% |",
        f"| V6 selective | Three months | {report['comparison']['v6_three_months']['calls']} / {report['comparison']['v6_three_months']['events']} | {report['comparison']['v6_three_months']['accuracy_pct']:.2f}% | {report['comparison']['v6_three_months']['coverage_pct']:.2f}% |",
        f"| V7 full | Three months | {recent['overall']['directions']} / {recent['overall']['events']} | {recent['overall']['accuracy_pct']:.2f}% | 100.00% |",
        "",
        "## One-Year Event Breakdown",
        "",
        "| Event | Rule | Events | Wins | Accuracy | Coverage |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for event in SUPPORTED_EVENTS:
        item = one_year["by_event"][event]
        lines.append(
            f"| {event} | {FULL_COVERAGE_POLICY[event]} | {item['events']} | {item['wins']} | {item['accuracy_pct']:.2f}% | 100.00% |"
        )
    lines.extend(
        [
            "",
            "## Full One-Year Replay",
            "",
            "| Date | Event | T-15 direction | Confidence | Actual | Result | Gold move |",
            "|---|---|---|---:|---|---|---:|",
        ]
    )
    for row in report["events"]:
        lines.append(
            f"| {row['release_utc'][:10]} | {row['event']} | {row['prediction']} | {row['confidence_pct']:.2f}% | {row['actual']} | {'WIN' if row['correct'] else 'LOSS'} | {row['release_move_usd']:+.3f} USD |"
        )
    lines.extend(
        [
            "",
            "## Integrity Notes",
            "",
            "- Direction rules were selected in the earlier V2 development and 2021-2024 guard process; this report does not optimize them on the displayed year.",
            "- The five-year diagnostic overlaps that guard period and is context, not a pristine holdout.",
            "- The final combined V7 package was assembled after these outcomes existed, so the next releases remain the true prospective test.",
            "- April 3, 2026 NFP is excluded because gold had no tradable release-minute session in the archive. Coverage is 100% of scorable releases, not calendar closures.",
            "- T-15/T-30 price ensembles are live confirmation diagnostics only. They cannot alter the validated full-coverage direction.",
            "- FXMacroData timing and provenance remain active, but unavailable stored pre-release forecasts contribute zero directional weight.",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> dict:
    samples_15, audit_15 = build_samples(15)
    samples_30, audit_30 = build_samples(30)
    rows = _source_rows(samples_15)
    pretest = [row for row in rows if date.fromisoformat(row["release_utc"][:10]) < START]
    reliability = validation_reliability(pretest, end=START)
    events = _replay(rows, reliability)
    five_year_events = _replay(
        rows,
        reliability,
        start=date(2021, 7, 30),
        end=END,
    )
    recent_events = [
        row for row in events if date.fromisoformat(row["release_utc"][:10]) >= RECENT_START
    ]

    def section(selected: list[dict]) -> dict:
        return {
            "overall": _metrics(selected),
            "by_event": {
                event: _metrics([row for row in selected if row["event"] == event])
                for event in SUPPORTED_EVENTS
            },
        }

    v6_one_year = json.loads(V6_ONE_YEAR.read_text(encoding="utf-8"))["metrics"]["overall"]
    v6_three_months = json.loads(V6_THREE_MONTH.read_text(encoding="utf-8"))["metrics"]["active_calls"]
    report = {
        "status": "full_coverage_retrospective_replay",
        "methodology": {
            "target": "Sign of the XAUUSD release-minute bid/ask midpoint move.",
            "prediction_cutoff": "T-15 minutes; the primary rule is also available at T-30.",
            "test_window": f"{START.isoformat()} through {END.isoformat()} exclusive",
            "recent_window": f"{RECENT_START.isoformat()} through {END.isoformat()} exclusive",
            "policy": dict(FULL_COVERAGE_POLICY),
            "selection": "Rules were frozen by the earlier V2 development and broad-guard workflow.",
            "coverage_definition": "100% of releases with a tradable XAUUSD M1 target.",
            "source_audit": {"t15": audit_15, "t30": audit_30},
        },
        "pretest_validation": reliability,
        "comparison": {
            "v6_one_year": v6_one_year,
            "v6_three_months": v6_three_months,
        },
        "five_year_diagnostic": section(five_year_events),
        "one_year": section(events),
        "recent_three_months": section(recent_events),
        "excluded_events": [
            {
                "release_utc": "2026-04-03T12:30:00+00:00",
                "event": "NFP",
                "reason": "No tradable XAUUSD M1 release session in the archive.",
            }
        ],
        "events": events,
    }

    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(events[0]))
        writer.writeheader()
        writer.writerows(events)
    OUTPUT_MD.write_text(_markdown(report), encoding="utf-8")

    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(fit_live_artifact({15: samples_15, 30: samples_30}), MODEL_PATH)
    return report


if __name__ == "__main__":
    result = run()
    print(json.dumps({
        "five_year_diagnostic": result["five_year_diagnostic"],
        "one_year": result["one_year"],
        "recent_three_months": result["recent_three_months"],
        "model": str(MODEL_PATH),
    }, indent=2))
