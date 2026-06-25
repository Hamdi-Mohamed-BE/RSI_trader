from __future__ import annotations

from datetime import datetime, timedelta, timezone
import csv
import json
import os
from pathlib import Path
import urllib.request
from typing import Any

from .config import DATA_DIR


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


def upcoming_news_events(minutes_ahead: int = 240) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    end = now + timedelta(minutes=max(1, minutes_ahead))
    events: list[dict[str, Any]] = []
    for event in load_news_events():
        raw_time = str(event.get("time") or "")
        try:
            event_time = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
        except ValueError:
            continue
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)
        if now <= event_time <= end:
            item = dict(event)
            item["time_utc"] = event_time.isoformat()
            events.append(item)
    return sorted(events, key=lambda item: item["time_utc"])


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
