from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import requests


EVENT_ALIASES = {
    "non farm payrolls": "NFP",
    "nonfarm payrolls": "NFP",
    "consumer price index": "CPI",
    "core inflation rate": "CPI",
    "producer price": "PPI",
    "gdp growth rate": "GDP",
    "gross domestic product": "GDP",
    "fed interest rate decision": "FOMC",
    "fomc": "FOMC",
}


def normalized_event(name: str) -> str | None:
    lowered = name.lower()
    for fragment, event in EVENT_ALIASES.items():
        if fragment in lowered:
            return event
    return None


def upcoming_us_events(days: int = 7) -> dict:
    api_key = os.getenv("TRADING_ECONOMICS_API_KEY", "").strip()
    if not api_key:
        return {
            "status": "provider_not_configured",
            "events": [],
            "message": (
                "Set TRADING_ECONOMICS_API_KEY to enable automatic upcoming-event discovery. "
                "Manual event and UTC release-time input remains available."
            ),
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
                "importance": item.get("Importance"),
                "currency": item.get("Currency") or "USD",
            }
        )
    return {"status": "ok", "events": events, "provider": "Trading Economics"}
