from __future__ import annotations

import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


EVENT_ALIASES = {
    "non farm payrolls": "NFP",
    "nonfarm payrolls": "NFP",
    "non-farm employment change": "NFP",
    "nonfarm employment change": "NFP",
    "consumer price index": "CPI",
    "core inflation rate": "CPI",
    "cpi m/m": "CPI",
    "cpi y/y": "CPI",
    "producer price": "PPI",
    "ppi m/m": "PPI",
    "ppi y/y": "PPI",
    "gdp growth rate": "GDP",
    "gross domestic product": "GDP",
    "advance gdp": "GDP",
    "fed interest rate decision": "FOMC",
    "federal funds rate": "FOMC",
    "fomc statement": "FOMC",
    "fomc": "FOMC",
}
FOREX_FACTORY_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CACHE_PATH = Path(__file__).resolve().parent / "data" / "forex-factory-week.json"


def normalized_event(name: str) -> str | None:
    lowered = name.lower()
    for fragment, event in EVENT_ALIASES.items():
        if fragment in lowered:
            return event
    return None


def _clean_number(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def forex_factory_events(days: int = 7) -> dict:
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)
    payload = None
    if CACHE_PATH.exists():
        age = now.timestamp() - CACHE_PATH.stat().st_mtime
        if age < 15 * 60:
            payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    if payload is None:
        try:
            response = requests.get(
                FOREX_FACTORY_URL,
                headers={"User-Agent": "Gold-News-AI/0.2"},
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            CACHE_PATH.write_text(json.dumps(payload), encoding="utf-8")
        except requests.RequestException:
            if not CACHE_PATH.exists():
                raise
            payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    events = []
    for item in payload:
        if str(item.get("country") or "").upper() != "USD":
            continue
        if str(item.get("impact") or "").lower() != "high":
            continue
        event = normalized_event(str(item.get("title") or ""))
        if not event:
            continue
        try:
            release = datetime.fromisoformat(str(item["date"])).astimezone(timezone.utc)
        except (KeyError, TypeError, ValueError):
            continue
        if not now - timedelta(hours=1) <= release <= end:
            continue
        events.append(
            {
                "event": event,
                "provider_name": item.get("title"),
                "release_time": release.isoformat(),
                "forecast": _clean_number(item.get("forecast")),
                "previous": _clean_number(item.get("previous")),
                "actual": _clean_number(item.get("actual")),
                "importance": 3,
                "currency": "USD",
                "source_url": None,
            }
        )
    return {
        "status": "ok",
        "events": events,
        "provider": "Forex Factory weekly JSON",
        "timing_warning": "Calendar times can change; verify against the official publisher.",
    }


def upcoming_us_events(days: int = 7) -> dict:
    api_key = os.getenv("TRADING_ECONOMICS_API_KEY", "").strip()
    if not api_key:
        try:
            result = forex_factory_events(days)
            result["message"] = (
                "Using the free Forex Factory weekly schedule. Configure "
                "TRADING_ECONOMICS_API_KEY for actual, revision, and source metadata."
            )
            return result
        except requests.RequestException as error:
            return {
                "status": "provider_unavailable",
                "events": [],
                "message": f"Calendar lookup failed: {error}",
            }
    start = datetime.now(timezone.utc).date()
    end = start + timedelta(days=days)
    url = (
        "https://api.tradingeconomics.com/calendar/country/united states/"
        f"{start.isoformat()}/{end.isoformat()}"
    )
    response = requests.get(url, params={"c": api_key}, timeout=30)
    response.raise_for_status()
    events = []
    for item in response.json():
        event = normalized_event(str(item.get("Event") or item.get("Category") or ""))
        if not event or int(item.get("Importance") or 0) < 3:
            continue
        events.append(
            {
                "event": event,
                "provider_name": item.get("Event"),
                "release_time": item.get("Date"),
                "forecast": item.get("Forecast"),
                "previous": item.get("Previous"),
                "actual": item.get("Actual"),
                "revised": item.get("Revised"),
                "importance": item.get("Importance"),
                "currency": item.get("Currency") or "USD",
                "source_url": item.get("SourceURL"),
                "last_update": item.get("LastUpdate"),
            }
        )
    return {"status": "ok", "events": events, "provider": "Trading Economics"}
