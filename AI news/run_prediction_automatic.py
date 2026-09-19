from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ea_file_bridge import next_event_payload
from news_core import ROOT
from predict_news import load_env, make_prediction


LOG_DIR = ROOT / "logs"
RUN_LOG = LOG_DIR / "prediction-runner.log"
RESULTS_CSV = LOG_DIR / "prediction-results.csv"
RESULTS_JSONL = LOG_DIR / "prediction-results.jsonl"
LATEST_REPORT = LOG_DIR / "latest-prediction.txt"
TARGET_LEAD_SECONDS = 15 * 60
MINIMUM_LEAD_SECONDS = 8 * 60

RESULT_FIELDS = (
    "logged_at_utc",
    "generated_at_utc",
    "event",
    "release_time_utc",
    "provider_name",
    "forecast",
    "previous",
    "direction",
    "confidence_pct",
    "action_tier",
    "expected_min_abs_usd",
    "expected_median_abs_usd",
    "expected_max_abs_usd",
    "artifact_version",
    "result_status",
    "prediction_file",
)


def log(message: str, *, level: str = "INFO") -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    line = f"{stamp} [{level}] {message}"
    print(line, flush=True)
    with RUN_LOG.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def parse_release(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
        timezone.utc
    )


def prediction_path(event: str, release: datetime) -> Path:
    return ROOT / "predictions" / (
        f"{release.strftime('%Y%m%dT%H%M%SZ')}-{event.lower()}.json"
    )


def load_locked_prediction(event: str, release: datetime) -> dict[str, Any] | None:
    path = prediction_path(event, release)
    if not path.exists():
        return None
    prediction = json.loads(path.read_text(encoding="utf-8"))
    if (
        prediction.get("event") != event
        or prediction.get("release_time_utc") != release.isoformat()
    ):
        raise RuntimeError(f"Locked prediction identity mismatch: {path}")
    prediction["saved_to"] = str(path)
    prediction["reused_locked_prediction"] = True
    return prediction


def discover_event(days: int) -> dict[str, Any]:
    payload = next_event_payload(days)
    if payload.get("status") != "OK":
        message = payload.get("message") or "No supported event was found."
        raise RuntimeError(message)
    return payload


def wait_for_prediction_window(days: int, no_wait: bool) -> dict[str, Any]:
    announced_identity: tuple[str, str] | None = None
    while True:
        payload = discover_event(days)
        event = str(payload["event"])
        release = parse_release(str(payload["release_utc"]))
        now = datetime.now(timezone.utc)
        seconds_before = (release - now).total_seconds()
        if seconds_before <= 0:
            raise RuntimeError(f"The discovered {event} release has already started.")

        identity = (event, release.isoformat())
        if identity != announced_identity:
            log(
                f"Next event: {event} at {release.isoformat()} | "
                f"forecast={payload.get('forecast') or 'n/a'} | "
                f"previous={payload.get('previous') or 'n/a'}"
            )
            announced_identity = identity

        if seconds_before <= TARGET_LEAD_SECONDS:
            return payload
        if no_wait:
            raise RuntimeError(
                f"{event} is {seconds_before / 60:.1f} minutes away. "
                "Run again at T-15 or omit --no-wait to wait automatically."
            )

        target = release - timedelta(seconds=TARGET_LEAD_SECONDS - 2)
        remaining = max(1.0, (target - now).total_seconds())
        sleep_seconds = min(300.0, remaining)
        log(
            f"Waiting for T-15. Calendar refresh in "
            f"{sleep_seconds / 60:.1f} minute(s)."
        )
        time.sleep(sleep_seconds)


def result_row(
    prediction: dict[str, Any],
    event_payload: dict[str, Any],
) -> dict[str, Any]:
    expected = prediction.get("expected_impulse_range_usd") or {}
    model = prediction.get("model") or {}
    reused = bool(prediction.get("reused_locked_prediction"))
    return {
        "logged_at_utc": datetime.now(timezone.utc).isoformat(),
        "generated_at_utc": prediction.get("generated_at_utc"),
        "event": prediction.get("event"),
        "release_time_utc": prediction.get("release_time_utc"),
        "provider_name": event_payload.get("provider_name"),
        "forecast": event_payload.get("forecast"),
        "previous": event_payload.get("previous"),
        "direction": prediction.get("gold_impact"),
        "confidence_pct": prediction.get("confidence_pct"),
        "action_tier": prediction.get("action_tier"),
        "expected_min_abs_usd": expected.get("minimum_absolute_move"),
        "expected_median_abs_usd": expected.get("median_absolute_move"),
        "expected_max_abs_usd": expected.get("maximum_absolute_move"),
        "artifact_version": model.get("artifact_version"),
        "result_status": "REUSED_LOCKED" if reused else "CREATED",
        "prediction_file": prediction.get("saved_to"),
    }


def write_result(row: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    if RESULTS_CSV.exists():
        with RESULTS_CSV.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

    key = (str(row["event"]), str(row["release_time_utc"]))
    rows = [
        existing
        for existing in rows
        if (existing.get("event"), existing.get("release_time_utc")) != key
    ]
    rows.append(row)
    rows.sort(key=lambda item: str(item.get("release_time_utc") or ""))
    temporary = RESULTS_CSV.with_suffix(".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(RESULTS_CSV)

    with RESULTS_JSONL.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def render_report(row: dict[str, Any]) -> str:
    direction = str(row["direction"] or "UNKNOWN")
    confidence = float(row["confidence_pct"] or 0.0)
    minimum = float(row["expected_min_abs_usd"] or 0.0)
    median = float(row["expected_median_abs_usd"] or 0.0)
    maximum = float(row["expected_max_abs_usd"] or 0.0)
    return "\n".join(
        (
            "=" * 62,
            "GOLD NEWS V9 AUTOMATIC PREDICTION",
            "=" * 62,
            f"Event:       {row['event']}",
            f"Release UTC: {row['release_time_utc']}",
            f"Forecast:    {row['forecast'] or 'n/a'}",
            f"Previous:    {row['previous'] or 'n/a'}",
            f"Gold call:   {direction}",
            f"Confidence:  {confidence:.2f}%",
            f"Action tier: {row['action_tier'] or 'n/a'}",
            f"Move range:  ${minimum:.2f} to ${maximum:.2f}",
            f"Median move: ${median:.2f}",
            f"Status:      {row['result_status']}",
            f"Full JSON:   {row['prediction_file']}",
            f"CSV log:     {RESULTS_CSV}",
            "=" * 62,
        )
    )


def run(days: int, no_wait: bool) -> dict[str, Any]:
    load_env()
    payload = wait_for_prediction_window(days, no_wait)
    event = str(payload["event"])
    release = parse_release(str(payload["release_utc"]))
    seconds_before = (release - datetime.now(timezone.utc)).total_seconds()

    locked = load_locked_prediction(event, release)
    if locked is not None:
        prediction = locked
        log(f"Reusing the locked {event} prediction.")
    elif seconds_before < MINIMUM_LEAD_SECONDS:
        raise RuntimeError(
            f"Only {seconds_before / 60:.1f} minutes remain before {event}; "
            "the safe T-30 to T-8 prediction window was missed."
        )
    else:
        log(f"Running V9 for {event} at {seconds_before / 60:.1f} minutes before release.")
        prediction = make_prediction(
            event,
            release,
            forecast=payload.get("forecast"),
            previous=payload.get("previous"),
        )

    row = result_row(prediction, payload)
    write_result(row)
    report = render_report(row)
    LATEST_REPORT.write_text(report + "\n", encoding="utf-8")
    print("\n" + report, flush=True)
    log(
        f"Prediction complete: {row['event']} {row['direction']} "
        f"at {float(row['confidence_pct'] or 0.0):.2f}%."
    )
    return row


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Automatically discover and run the next Gold News V9 prediction."
    )
    parser.add_argument("--days", type=int, default=30, help="Calendar look-ahead, 1-30 days.")
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Exit instead of waiting when the next event is more than 15 minutes away.",
    )
    args = parser.parse_args()
    try:
        run(max(1, min(args.days, 30)), args.no_wait)
        return 0
    except KeyboardInterrupt:
        log("Prediction runner stopped by the user.", level="WARNING")
        return 130
    except Exception as error:
        log(f"Prediction failed: {error}", level="ERROR")
        traceback.print_exc()
        with RUN_LOG.open("a", encoding="utf-8") as handle:
            traceback.print_exc(file=handle)
        return 1


if __name__ == "__main__":
    sys.exit(main())
