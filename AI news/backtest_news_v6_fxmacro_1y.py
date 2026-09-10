from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fxmacrodata import FXMacroDataClient
from news_core import ROOT
from news_v5 import cpi_regime_prediction


START = datetime(2025, 9, 10, tzinfo=timezone.utc)
END = datetime(2026, 9, 10, tzinfo=timezone.utc)
HISTORY_PATH = ROOT / "gold_direction_5y.json"
FOMC_PATH = ROOT / "fomc_frozen_holdout.json"
RECENT_PATH = ROOT / "news_v6_fxmacro_3m_results.json"
OUTPUT_JSON = ROOT / "news_v6_fxmacro_1y_results.json"
OUTPUT_CSV = ROOT / "news_v6_fxmacro_1y_results.csv"
OUTPUT_MD = ROOT / "NEWS_V6_FXMACRO_1Y_RESULTS.md"


def _wilson(wins: int, calls: int) -> list[float]:
    if not calls:
        return [0.0, 0.0]
    z = 1.959963984540054
    p = wins / calls
    denominator = 1 + z * z / calls
    center = (p + z * z / (2 * calls)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * calls)) / calls) / denominator
    return [round(100 * (center - margin), 2), round(100 * (center + margin), 2)]


def _metrics(rows: list[dict]) -> dict:
    called = [row for row in rows if row["prediction"] != "NO CALL"]
    wins = sum(row["prediction"] == row["actual"] for row in called)
    return {
        "events": len(rows),
        "calls": len(called),
        "wins": wins,
        "losses": len(called) - wins,
        "accuracy_pct": round(100 * wins / len(called), 2) if called else 0.0,
        "coverage_pct": round(100 * len(called) / len(rows), 2) if rows else 0.0,
        "wilson_95_pct": _wilson(wins, len(called)),
    }


def _load_actuals() -> list[dict]:
    history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))["events"]
    rows = [
        {
            "release_utc": row["release_utc"],
            "event": row["event"],
            "actual": row["actual_gold_impact"],
            "release_move_usd": float(row["actual_move_usd"]),
        }
        for row in history
        if row["event"] in {"NFP", "CPI", "FOMC"}
    ]
    recent = json.loads(RECENT_PATH.read_text(encoding="utf-8"))["events"]
    existing = {row["release_utc"] for row in rows}
    for row in recent:
        if row["release_utc"] not in existing:
            rows.append(
                {
                    "release_utc": row["release_utc"],
                    "event": row["event"],
                    "actual": row["actual"],
                    "release_move_usd": float(row["release_move_usd"]),
                }
            )
    return sorted(rows, key=lambda row: row["release_utc"])


def _fomc_decisions() -> dict[str, dict]:
    payload = json.loads(FOMC_PATH.read_text(encoding="utf-8"))
    return {row["release_utc"]: row for row in payload["events"]}


def _predict(actuals: list[dict]) -> list[dict]:
    fomc = _fomc_decisions()
    history: dict[str, list[str]] = defaultdict(list)
    output = []
    for source in actuals:
        release = datetime.fromisoformat(source["release_utc"]).astimezone(timezone.utc)
        event = source["event"]
        if event == "CPI":
            decision = cpi_regime_prediction(history[event])
            prediction = "POSITIVE" if decision["prediction"] == "BUY" else "NO CALL"
            confidence = round(100 * float(decision["confidence"]), 2)
            strategy = decision["strategy"]
        elif event == "FOMC":
            saved = fomc.get(source["release_utc"], {})
            prediction = saved.get("agreement_prediction") or "NO CALL"
            model_probability = float(saved.get("model_probability_positive_pct", 50.0))
            confidence = 65.0 if prediction != "NO CALL" else max(model_probability, 100 - model_probability)
            strategy = "fomc_chronological_agreement"
        else:
            prediction = "NO CALL"
            confidence = 0.0
            strategy = "nfp_shadow_only"

        if START <= release < END:
            output.append(
                {
                    **source,
                    "prediction": prediction,
                    "confidence_pct": round(confidence, 2),
                    "strategy": strategy,
                }
            )
        history[event].append("BUY" if source["actual"] == "POSITIVE" else "SELL")
    return output


def _markdown(report: dict) -> str:
    metrics = report["metrics"]["overall"]
    lines = [
        "# Gold News Direction V6 - FXMacroData One-Year Retrospective",
        "",
        "> Window: September 10, 2025 through September 9, 2026. The CPI V5 policy was designed after part of this period, so this is a retrospective policy replay, not a pristine unseen holdout.",
        "",
        "## Summary",
        "",
        "| Measure | Result |",
        "|---|---:|",
        f"| Scorable events | {metrics['events']} |",
        f"| Active calls | {metrics['calls']} |",
        f"| Wins / losses | {metrics['wins']} / {metrics['losses']} |",
        f"| Active-call accuracy | {metrics['accuracy_pct']:.2f}% |",
        f"| Coverage | {metrics['coverage_pct']:.2f}% |",
        f"| 95% Wilson interval | {metrics['wilson_95_pct'][0]:.2f}-{metrics['wilson_95_pct'][1]:.2f}% |",
        f"| FXMacroData times verified | {report['fxmacrodata_audit']['verified_event_times']} / {metrics['events']} |",
        "",
        "## Event Replay",
        "",
        "| Date | Event | Final T-15 | Confidence | Actual | Result | Gold move | FXMacroData |",
        "|---|---|---|---:|---|---|---:|---|",
    ]
    for row in report["events"]:
        result = "ABSTAIN" if row["prediction"] == "NO CALL" else (
            "WIN" if row["prediction"] == row["actual"] else "LOSS"
        )
        lines.append(
            f"| {row['release_utc'][:10]} | {row['event']} | {row['prediction']} | "
            f"{row['confidence_pct']:.2f}% | {row['actual']} | {result} | "
            f"{row['release_move_usd']:+.3f} USD | "
            f"{row['fxmacrodata'].get('event_time_verification', 'unavailable')} |"
        )
    lines.extend(
        [
            "",
            "## Event Breakdown",
            "",
            "| Event | Events | Calls | Wins | Accuracy | Coverage |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for event, values in report["metrics"]["by_event"].items():
        lines.append(
            f"| {event} | {values['events']} | {values['calls']} | {values['wins']} | "
            f"{values['accuracy_pct']:.2f}% | {values['coverage_pct']:.2f}% |"
        )
    lines.extend(
        [
            "",
            "## Limits",
            "",
            "- The April 3, 2026 NFP is excluded because the XAUUSD M1 archive contains no tradable release session for that market holiday.",
            "- NFP remains an intentional no-call because its pre-release directional edge did not survive validation.",
            "- Anonymous FXMacroData history covers only the recent 90-day window; older event timestamps remain sourced from the existing official/local calendar archive.",
            "- No stored-at-generation FXMacroData forecasts were available, so FXMacroData has zero directional weight in this report.",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> dict:
    for path in (HISTORY_PATH, FOMC_PATH, RECENT_PATH):
        if not path.exists():
            raise FileNotFoundError(f"Required input is missing: {path}")
    events = _predict(_load_actuals())
    client = FXMacroDataClient.from_env()
    for row in events:
        release = datetime.fromisoformat(row["release_utc"]).astimezone(timezone.utc)
        row["fxmacrodata"] = client.context(
            row["event"],
            release,
            release - timedelta(minutes=15),
        )
    by_event = {
        event: _metrics([row for row in events if row["event"] == event])
        for event in ("NFP", "CPI", "FOMC")
    }
    report = {
        "status": "retrospective_policy_replay",
        "methodology": {
            "window_start_utc": START.isoformat(),
            "window_end_utc_exclusive": END.isoformat(),
            "target": "Sign of the XAUUSD release-minute bid/ask midpoint move.",
            "prediction_cutoff": "T-15 minutes",
            "cpi": "V5 positive-regime policy replayed sequentially using only prior outcomes.",
            "fomc": "Saved chronological model/history agreement decisions.",
            "nfp": "No active pre-release call.",
            "researcher_warning": (
                "The CPI V5 policy was designed after part of this period. Results are "
                "retrospective and must not be presented as a pristine unseen test."
            ),
        },
        "metrics": {"overall": _metrics(events), "by_event": by_event},
        "fxmacrodata_audit": {
            "verified_event_times": sum(
                row["fxmacrodata"].get("event_time_verification") == "verified"
                for row in events
            ),
            "stored_pre_release_forecasts": sum(
                row["fxmacrodata"].get("stored_pre_release_forecast") is not None
                for row in events
            ),
        },
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
        fields = [
            "release_utc",
            "event",
            "prediction",
            "confidence_pct",
            "actual",
            "release_move_usd",
            "result",
            "fxmacrodata_time_verification",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in events:
            writer.writerow(
                {
                    "release_utc": row["release_utc"],
                    "event": row["event"],
                    "prediction": row["prediction"],
                    "confidence_pct": row["confidence_pct"],
                    "actual": row["actual"],
                    "release_move_usd": row["release_move_usd"],
                    "result": "ABSTAIN" if row["prediction"] == "NO CALL" else (
                        "WIN" if row["prediction"] == row["actual"] else "LOSS"
                    ),
                    "fxmacrodata_time_verification": row["fxmacrodata"].get("event_time_verification"),
                }
            )
    OUTPUT_MD.write_text(_markdown(report), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = run()
    print(json.dumps(result["metrics"], indent=2))
    print(f"Saved {OUTPUT_MD}")

