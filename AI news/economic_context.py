from __future__ import annotations

import argparse
import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

from calendar_provider import normalized_event
from news_core import EVENTS, ROOT


CACHE_DIR = ROOT / "data" / "economic-context"
CACHE_PATH = CACHE_DIR / "trading_economics_calendar.json"


def load_env() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(
                key.strip(),
                value.strip().strip('"').strip("'"),
            )


def parse_numeric(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text or text.lower() in {"null", "none", "n/a"}:
        return None
    multiplier = 1.0
    if text[-1:].upper() in {"K", "M", "B", "T"}:
        multiplier = {
            "K": 1_000.0,
            "M": 1_000_000.0,
            "B": 1_000_000_000.0,
            "T": 1_000_000_000_000.0,
        }[text[-1].upper()]
        text = text[:-1]
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    return float(match.group()) * multiplier if match else None


def _event_record(item: dict) -> dict | None:
    event = normalized_event(
        str(item.get("Event") or item.get("Category") or "")
    )
    if event not in EVENTS:
        return None
    return {
        "calendar_id": str(item.get("CalendarId") or ""),
        "release_utc": str(item.get("Date") or ""),
        "event": event,
        "provider_event": item.get("Event"),
        "actual": item.get("Actual"),
        "previous": item.get("Previous"),
        "forecast": item.get("Forecast"),
        "te_forecast": item.get("TEForecast"),
        "revised": item.get("Revised"),
        "importance": int(item.get("Importance") or 0),
        "last_update": item.get("LastUpdate"),
        "source": item.get("Source"),
        "source_url": item.get("SourceURL"),
        "unit": item.get("Unit"),
    }


def refresh_consensus_history(
    start: date = date(2011, 1, 1),
    end: date | None = None,
) -> dict:
    load_env()
    key = os.getenv("TRADING_ECONOMICS_API_KEY", "").strip()
    if not key:
        return {
            "status": "not_configured",
            "message": (
                "TRADING_ECONOMICS_API_KEY is empty; no historical "
                "consensus data was downloaded."
            ),
        }
    stop = end or datetime.now(timezone.utc).date()
    rows = []
    cursor = start
    while cursor <= stop:
        chunk_end = min(
            date(cursor.year, 12, 31),
            stop,
        )
        url = (
            "https://api.tradingeconomics.com/calendar/country/"
            f"united%20states/{cursor.isoformat()}/{chunk_end.isoformat()}"
        )
        response = requests.get(url, params={"c": key}, timeout=60)
        response.raise_for_status()
        for item in response.json():
            record = _event_record(item)
            if record and record["importance"] >= 3:
                rows.append(record)
        cursor = chunk_end + timedelta(days=1)
    deduplicated = {
        (
            row["calendar_id"],
            row["release_utc"],
            row["event"],
        ): row
        for row in rows
    }
    payload = {
        "status": "ok",
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "point_in_time_warning": (
            "Forecast and previous fields may be used as pre-release "
            "features. Actual and revised fields are outcome/history only."
        ),
        "events": sorted(
            deduplicated.values(),
            key=lambda row: row["release_utc"],
        ),
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {
        "status": "ok",
        "events": len(payload["events"]),
        "cache": str(CACHE_PATH),
    }


class EconomicContextStore:
    def __init__(self) -> None:
        if CACHE_PATH.exists():
            self.payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        else:
            self.payload = {"events": []}

    def context(
        self,
        event: str,
        release_utc: datetime,
        forecast: object = None,
        previous: object = None,
    ) -> dict:
        event = event.upper()
        current_forecast = parse_numeric(forecast)
        current_previous = parse_numeric(previous)
        history = [
            row
            for row in self.payload.get("events", [])
            if row["event"] == event
            and row["release_utc"] < release_utc.isoformat()
        ]
        prior_surprises = []
        for row in history:
            actual_value = parse_numeric(row.get("actual"))
            forecast_value = parse_numeric(row.get("forecast"))
            if actual_value is not None and forecast_value is not None:
                prior_surprises.append(actual_value - forecast_value)
        recent = prior_surprises[-6:]
        return {
            "event": event,
            "forecast": current_forecast,
            "previous": current_previous,
            "forecast_minus_previous": (
                current_forecast - current_previous
                if current_forecast is not None
                and current_previous is not None
                else None
            ),
            "prior_six_mean_surprise": (
                sum(recent) / len(recent) if recent else None
            ),
            "historical_consensus_samples": len(prior_surprises),
            "decision_weight": 0.0,
            "note": (
                "The consensus layer remains context-only until its "
                "point-in-time history passes the frozen promotion test."
            ),
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh point-in-time economic consensus history."
    )
    parser.add_argument("--start", type=date.fromisoformat, default=date(2011, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat)
    args = parser.parse_args()
    print(
        json.dumps(
            refresh_consensus_history(args.start, args.end),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
