from __future__ import annotations

from datetime import datetime, timedelta, timezone
import csv
import json
import os
from pathlib import Path
import urllib.request
from typing import Any

from .config import DATA_DIR
from .session_time import DEFAULT_SESSION_TIMEZONE, zone


NEWS_EVENTS_PATH = DATA_DIR / "news_events.csv"


def load_news_events(path: Path = NEWS_EVENTS_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not row.get("time"):
                continue
            rows.append({key: (value or "").strip() for key, value in row.items()})
    return rows


def parse_news_time(raw_time: Any) -> datetime | None:
    try:
        event_time = datetime.fromisoformat(str(raw_time or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=timezone.utc)
    return event_time.astimezone(timezone.utc)


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _csv_items(value: str) -> list[str]:
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def _scheduled_event_time_events(now: datetime, end: datetime) -> list[dict[str, Any]]:
    raw_times = os.getenv("NEWS_EVENT_TIMES", "").strip()
    if not raw_times:
        return []
    session_timezone = os.getenv("NEWS_SESSION_TIMEZONE", DEFAULT_SESSION_TIMEZONE)
    session_zone = zone(session_timezone, DEFAULT_SESSION_TIMEZONE)
    local_now = now.astimezone(session_zone)
    symbols = ",".join(_csv_items(os.getenv("NEWS_SYMBOLS", "XAUUSD,XAGUSD,BTCUSD,US30")))
    events: list[dict[str, Any]] = []
    for day_offset in (0, 1):
        session_day = local_now.date() + timedelta(days=day_offset)
        for raw_item in raw_times.split(","):
            item = raw_item.strip()
            if not item:
                continue
            try:
                hour, minute = item.split(":", 1)
                local_event = datetime(
                    session_day.year,
                    session_day.month,
                    session_day.day,
                    int(hour),
                    int(minute),
                    tzinfo=session_zone,
                )
            except ValueError:
                continue
            event_time = local_event.astimezone(timezone.utc)
            if now <= event_time <= end:
                events.append(
                    {
                        "time": event_time.isoformat(),
                        "time_utc": event_time.isoformat(),
                        "title": f"Scheduled news window {item} {session_timezone}",
                        "currency": "USD",
                        "impact": "scheduled",
                        "symbols": symbols,
                        "notes": "Generated from NEWS_EVENT_TIMES fallback.",
                        "source": "NEWS_EVENT_TIMES",
                    }
                )
    return events


def upcoming_news_events(minutes_ahead: int = 240, include_scheduled_fallback: bool | None = None) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    end = now + timedelta(minutes=max(1, minutes_ahead))
    events: list[dict[str, Any]] = []
    for event in load_news_events():
        raw_time = str(event.get("time") or "")
        event_time = parse_news_time(raw_time)
        if event_time is None:
            continue
        if now <= event_time <= end:
            item = dict(event)
            item["time_utc"] = event_time.isoformat()
            item.setdefault("source", "news_events.csv")
            events.append(item)
    if include_scheduled_fallback is None:
        include_scheduled_fallback = _bool_env("NEWS_USE_EVENT_TIME_FALLBACK", True)
    if include_scheduled_fallback:
        events.extend(_scheduled_event_time_events(now, end))

    deduped: dict[tuple[str, str], dict[str, Any]] = {}
    for item in events:
        key = (str(item.get("time_utc") or item.get("time") or ""), str(item.get("title") or item.get("event") or ""))
        deduped[key] = item
    return sorted(deduped.values(), key=lambda item: item["time_utc"])


def openai_news_bias(event: dict[str, Any], symbols: tuple[str, ...]) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return {"ok": False, "bias": "STRADDLE", "confidence": 0.0, "reason": "OPENAI_API_KEY is not set."}
    model = os.getenv("NEWS_OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
    prompt = (
        "You are a conservative market-news impact classifier for a MetaTrader bot. "
        "Return compact JSON only with keys: bias, confidence, affected_symbols, reason. "
        "bias must be one of BUY, SELL, STRADDLE, SKIP. "
        "Use STRADDLE when direction is uncertain but volatility is likely. "
        f"Symbols: {', '.join(symbols)}. Event: {json.dumps(event, ensure_ascii=True)}"
    )
    payload = {
        "model": model,
        "input": prompt,
        "text": {"format": {"type": "json_object"}},
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"ok": False, "bias": "STRADDLE", "confidence": 0.0, "reason": f"OpenAI request failed: {exc}"}

    text = ""
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                text += str(content.get("text") or "")
    try:
        parsed = json.loads(text) if text else {}
    except ValueError:
        parsed = {}
    bias = str(parsed.get("bias") or "STRADDLE").upper()
    if bias not in {"BUY", "SELL", "STRADDLE", "SKIP"}:
        bias = "STRADDLE"
    return {
        "ok": True,
        "bias": bias,
        "confidence": float(parsed.get("confidence") or 0.0),
        "affected_symbols": parsed.get("affected_symbols") or list(symbols),
        "reason": parsed.get("reason") or "OpenAI news impact classification complete.",
        "raw": parsed,
    }
