from __future__ import annotations

import csv
import json
import math
import warnings
from collections import defaultdict

from backtest_news_v4 import (
    LEGACY_RULES,
    _augment_august_nfp,
    _frozen_predictions,
)
from gold_direction_rules import rule_direction
from news_core import ROOT, build_samples
from news_v4 import binary_rows, expanding_oof_components_safe, select_policies


START = "2025-09-10T00:00:00+00:00"
END = "2026-09-10T00:00:00+00:00"
V7_REPORT = ROOT / "news_v7_full_coverage_results.json"
V6_REPORT = ROOT / "news_v6_fxmacro_1y_results.json"
OUTPUT_JSON = ROOT / "news_v9_direction_1y_results.json"
OUTPUT_CSV = ROOT / "news_v9_direction_1y_results.csv"
OUTPUT_MD = ROOT / "NEWS_V9_DIRECTION_1Y_RESULTS.md"

warnings.filterwarnings(
    "ignore",
    message="`sklearn.utils.parallel.delayed` should be used.*",
    category=UserWarning,
)


def _positive(label: str) -> str:
    return "POSITIVE" if label in {"BUY", "POSITIVE"} else "NEGATIVE"


def _wilson(wins: int, calls: int) -> list[float]:
    if calls == 0:
        return [0.0, 0.0]
    z = 1.959963984540054
    p = wins / calls
    denominator = 1 + z * z / calls
    center = (p + z * z / (2 * calls)) / denominator
    margin = z * math.sqrt(
        (p * (1 - p) + z * z / (4 * calls)) / calls
    ) / denominator
    return [
        round(100 * max(0.0, center - margin), 2),
        round(100 * min(1.0, center + margin), 2),
    ]


def _score(rows: list[dict], prediction_key: str) -> dict:
    called = [
        row
        for row in rows
        if row.get(prediction_key) not in {None, "NO CALL", "NO TRADE"}
    ]
    wins = sum(row[prediction_key] == row["actual"] for row in called)
    return {
        "events": len(rows),
        "calls": len(called),
        "wins": wins,
        "losses": len(called) - wins,
        "accuracy_pct": round(100 * wins / len(called), 2) if called else 0.0,
        "coverage_pct": round(100 * len(called) / len(rows), 2) if rows else 0.0,
        "wilson_95_pct": _wilson(wins, len(called)),
    }


def _policy_metrics(rows: list[dict]) -> dict:
    keys = {
        "v1_event_history": "v1_direction",
        "v2_event_rules": "v2_direction",
        "v4_active": "v4_active",
        "v4_shadow": "v4_shadow",
        "v5_v6_active": "v5_active",
        "v7_v8_full": "v7_direction",
        "v9_full": "v9_direction",
        "v9_trade_tier": "v9_trade_direction",
        "v9_low_confidence_tier": "v9_low_confidence_direction",
    }
    return {name: _score(rows, key) for name, key in keys.items()}


def _event_metrics(rows: list[dict]) -> dict:
    return {
        event: {
            "v7_v8_full": _score(
                [row for row in rows if row["event"] == event],
                "v7_direction",
            ),
            "v9_full": _score(
                [row for row in rows if row["event"] == event],
                "v9_direction",
            ),
            "v9_trade_tier": _score(
                [row for row in rows if row["event"] == event],
                "v9_trade_direction",
            ),
        }
        for event in ("NFP", "CPI", "FOMC")
    }


def _build_events() -> tuple[list[dict], dict]:
    raw_15, audit_15 = build_samples(15)
    raw_30, audit_30 = build_samples(30)
    rows_15 = binary_rows(raw_15)
    rows_30 = binary_rows(raw_30)
    rows_15, august_snapshot = _augment_august_nfp(rows_15)

    training_15 = [row for row in rows_15 if row["release_utc"] < START]
    training_30 = [row for row in rows_30 if row["release_utc"] < START]
    test_15 = [row for row in rows_15 if START <= row["release_utc"] < END]
    test_30 = [row for row in rows_30 if START <= row["release_utc"] < END]

    policies = {}
    for lead, training in ((15, training_15), (30, training_30)):
        policies[lead] = select_policies(
            expanding_oof_components_safe(training),
            training,
        )

    base = _frozen_predictions(
        training_15,
        training_30,
        test_15,
        test_30,
        policies,
    )

    v7 = json.loads(V7_REPORT.read_text(encoding="utf-8"))
    v7_by_release = {
        row["release_utc"]: row
        for row in v7["events"]
        if START <= row["release_utc"] < END
    }
    v6 = json.loads(V6_REPORT.read_text(encoding="utf-8"))
    v6_by_release = {
        row["release_utc"]: row
        for row in v6["events"]
        if START <= row["release_utc"] < END
    }

    history: dict[str, list[str]] = defaultdict(list)
    for row in training_15:
        history[row["event"]].append(_positive(row["target"]))

    events = []
    for row in base:
        event = row["event"]
        actual = row["actual"]
        event_history = history[event]
        v1_direction = rule_direction("event_history", event_history)
        v2_direction = rule_direction(LEGACY_RULES[event], event_history)

        if event == "CPI":
            v9_direction = "POSITIVE"
            confidence_pct = 68.0
        elif event == "NFP":
            v9_direction = row["t15_bias"]
            confidence_pct = float(row["t15_confidence_pct"])
        else:
            v9_direction = row["t15_bias"]
            confidence_pct = float(row["t15_confidence_pct"])

        v6_row = v6_by_release.get(row["release_utc"])
        if v6_row is None:
            raise RuntimeError(f"V6 comparison is missing {row['release_utc']}.")
        v5_active = v6_row["prediction"]
        action_tier = "TRADE" if v5_active == v9_direction else "LOW_CONFIDENCE"
        v7_row = v7_by_release.get(row["release_utc"])
        if v7_row is None:
            raise RuntimeError(f"V7 comparison is missing {row['release_utc']}.")

        events.append(
            {
                "release_utc": row["release_utc"],
                "event": event,
                "actual": actual,
                "release_move_usd": row["release_move_usd"],
                "v1_direction": v1_direction,
                "v2_direction": v2_direction,
                "v4_active": row["t15_prediction"],
                "v4_shadow": row["t15_bias"],
                "v5_active": v5_active,
                "v7_direction": v7_row["prediction"],
                "v9_direction": v9_direction,
                "action_tier": action_tier,
                "v9_trade_direction": (
                    v9_direction if action_tier == "TRADE" else "NO CALL"
                ),
                "v9_low_confidence_direction": (
                    v9_direction
                    if action_tier == "LOW_CONFIDENCE"
                    else "NO CALL"
                ),
                "confidence_pct": confidence_pct,
            }
        )
        event_history.append(actual)

    if len(events) != 29:
        raise RuntimeError(f"Expected 29 one-year events, found {len(events)}.")
    return events, {
        "t15": audit_15,
        "t30": audit_30,
        "august_7_snapshot_generated_at_utc": august_snapshot["generated_at_utc"],
    }


def _markdown(report: dict) -> str:
    metrics = report["direction_metrics"]
    lines = [
        "# Gold News V9 - One-Year Direction Replay",
        "",
        "> Window: September 10, 2025 through September 9, 2026. NFP, CPI, and FOMC only. All release features are fitted using data before the test window.",
        "",
        "## Version Comparison",
        "",
        "| Version | Calls | Wins | Win rate | Coverage |",
        "|---|---:|---:|---:|---:|",
    ]
    labels = (
        ("V1 event history", "v1_event_history"),
        ("V2 event rules", "v2_event_rules"),
        ("V4 active gate", "v4_active"),
        ("V4 shadow direction", "v4_shadow"),
        ("V5/V6 active", "v5_v6_active"),
        ("V7/V8 full direction", "v7_v8_full"),
        ("V9 full direction", "v9_full"),
        ("V9 TRADE tier", "v9_trade_tier"),
        ("V9 LOW_CONFIDENCE tier", "v9_low_confidence_tier"),
    )
    for label, key in labels:
        item = metrics[key]
        lines.append(
            f"| {label} | {item['calls']} | {item['wins']} | "
            f"{item['accuracy_pct']:.2f}% | {item['coverage_pct']:.2f}% |"
        )

    lines.extend(
        [
            "",
            "## V9 Event Breakdown",
            "",
            "| Event | Releases | Wins | Accuracy | Coverage | TRADE-tier accuracy | TRADE-tier coverage |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for event, values in report["event_metrics"].items():
        full = values["v9_full"]
        active = values["v9_trade_tier"]
        lines.append(
            f"| {event} | {full['events']} | {full['wins']} | "
            f"{full['accuracy_pct']:.2f}% | {full['coverage_pct']:.2f}% | "
            f"{active['accuracy_pct']:.2f}% | {active['coverage_pct']:.2f}% |"
        )

    lines.extend(
        [
            "",
            "## Event Replay",
            "",
            "| Date | Event | V7/V8 | V9 | Tier | Actual | Result | Gold move |",
            "|---|---|---|---|---|---|---|---:|",
        ]
    )
    for row in report["events"]:
        result = "WIN" if row["v9_direction"] == row["actual"] else "LOSS"
        lines.append(
            f"| {row['release_utc'][:10]} | {row['event']} | "
            f"{row['v7_direction']} | {row['v9_direction']} | "
            f"{row['action_tier']} | {row['actual']} | {result} | "
            f"{row['release_move_usd']:+.3f} USD |"
        )

    lines.extend(
        [
            "",
            "## Limits",
            "",
            "- April 3, 2026 NFP is excluded because the XAUUSD archive has no tradable release session for that market holiday.",
            "- This is a chronological replay: model fitting uses only data before the one-year window and event-history inputs update only after each release.",
            "- V9's architecture was designed after some displayed outcomes were known, so this is not a pristine untouched test of the design choice.",
            "- V3 is omitted from the one-year comparison because it was a rejected research candidate and has no frozen one-year production policy.",
            "- Direction accuracy measures the sign of the release-minute XAUUSD midpoint move. It is not a simulated trading return.",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> dict:
    for path in (V6_REPORT, V7_REPORT):
        if not path.exists():
            raise FileNotFoundError(f"Required comparison report is missing: {path}")
    events, data_audit = _build_events()
    report = {
        "status": "v9_one_year_chronological_replay",
        "window": {"start": START, "end_exclusive": END},
        "methodology": {
            "target": "Sign of the XAUUSD release-minute bid/ask midpoint move.",
            "events": ["NFP", "CPI", "FOMC"],
            "prediction_cutoff": "T-15 minutes",
            "training": "Models and policy selection use samples before the one-year window.",
            "v9_direction": "V5 event-specific bias promoted to a full direction.",
            "action_tier": "The V5 active gate is retained as TRADE versus LOW_CONFIDENCE.",
        },
        "data_audit": data_audit,
        "direction_metrics": _policy_metrics(events),
        "event_metrics": _event_metrics(events),
        "events": events,
    }
    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(events[0]))
        writer.writeheader()
        writer.writerows(events)
    OUTPUT_MD.write_text(_markdown(report), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = run()
    print(json.dumps(result["direction_metrics"], indent=2))
    print(f"Saved {OUTPUT_MD}")
