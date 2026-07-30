from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "news-event-days"
CALENDAR_PATH = ROOT / "news_15y_calendar.csv"
EVENTS = ("NFP", "GDP", "CPI", "PPI", "FOMC")
LEADS = (15, 30)
LABELS = ("BUY", "SELL", "UNCERTAIN")
FEATURE_NAMES = (
    "ret_5_atr",
    "ret_15_atr",
    "ret_30_atr",
    "ret_60_atr",
    "range_5_atr",
    "range_15_atr",
    "range_30_atr",
    "body_5_atr",
    "body_15_atr",
    "volume_z",
    "distance_3h_open_atr",
    "spread_atr",
    "atr_pct",
    *tuple(f"event_{event}" for event in EVENTS),
)


@dataclass(frozen=True)
class Event:
    event: str
    release_utc: datetime
    title: str
    source: str


def load_calendar() -> list[Event]:
    with CALENDAR_PATH.open(newline="", encoding="utf-8") as handle:
        events = [
            Event(
                event=row["event"].upper(),
                release_utc=datetime.fromisoformat(row["release_utc"]).astimezone(timezone.utc),
                title=row["title"],
                source=row["source"],
            )
            for row in csv.DictReader(handle)
        ]
    return sorted(events, key=lambda item: item.release_utc)


def normalize_rows(raw: object) -> list[dict[str, float]]:
    if isinstance(raw, dict):
        for key in ("data", "rates", "items"):
            if isinstance(raw.get(key), list):
                raw = raw[key]
                break
    if not isinstance(raw, list):
        return []
    rows = []
    for item in raw:
        if isinstance(item, list) and len(item) >= 5:
            timestamp, open_, high, low, close = item[:5]
            volume = item[5] if len(item) > 5 else 0.0
        elif isinstance(item, dict):
            timestamp = item.get("timestamp") or item.get("time")
            open_, high, low, close = (item.get(key) for key in ("open", "high", "low", "close"))
            volume = item.get("volume") or item.get("tick_volume") or 0.0
        else:
            continue
        if timestamp is None or close is None:
            continue
        if isinstance(timestamp, str):
            stamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp() * 1000
        else:
            stamp = float(timestamp)
            if stamp < 10_000_000_000:
                stamp *= 1000
        rows.append(
            {
                "timestamp": float(stamp),
                "open": float(open_),
                "high": float(high),
                "low": float(low),
                "close": float(close),
                "volume": float(volume or 0),
            }
        )
    return rows


def load_day(day: str, side: str) -> dict[int, dict[str, float]]:
    path = DATA_DIR / f"xauusd-m1-{side}-{day}.json"
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        round(row["timestamp"] / 60_000) * 60_000: row
        for row in normalize_rows(raw)
    }


def annual_spreads(days: list[str]) -> dict[int, float]:
    by_year: dict[int, list[float]] = defaultdict(list)
    for day in days:
        bid = load_day(day, "bid")
        ask = load_day(day, "ask")
        for stamp in sorted(set(bid) & set(ask))[::60]:
            spread = ask[stamp]["close"] - bid[stamp]["close"]
            if 0 < spread < 20:
                by_year[int(day[:4])].append(spread)
    all_values = [value for values in by_year.values() for value in values]
    global_median = float(np.median(all_values)) if all_values else 0.3
    return {
        year: float(np.median(values)) if values else global_median
        for year, values in by_year.items()
    }


def complete_sides(
    bid: dict[int, dict[str, float]],
    ask: dict[int, dict[str, float]],
    spread: float,
) -> tuple[dict[int, dict[str, float]], dict[int, dict[str, float]], str | None]:
    if bid and ask:
        return bid, ask, None
    if not bid and not ask:
        return bid, ask, None
    source = ask if ask else bid
    offset = -spread if ask else spread
    synthetic = {
        stamp: {
            **row,
            **{key: row[key] + offset for key in ("open", "high", "low", "close")},
        }
        for stamp, row in source.items()
    }
    return (synthetic, ask, "bid") if ask else (bid, synthetic, "ask")


def nearest(
    data: dict[int, dict[str, float]],
    stamp: int,
    tolerance_minutes: int = 2,
) -> dict[str, float] | None:
    for offset in range(tolerance_minutes + 1):
        candidates = (stamp,) if offset == 0 else (stamp - offset * 60_000, stamp + offset * 60_000)
        for candidate in candidates:
            if candidate in data:
                return data[candidate]
    return None


def extract_features(
    event_name: str,
    release_utc: datetime,
    bid: dict[int, dict[str, float]],
    ask: dict[int, dict[str, float]],
    lead_minutes: int,
) -> tuple[list[float], dict] | None:
    release_ms = int(release_utc.timestamp() * 1000)
    cutoff_ms = release_ms - lead_minutes * 60_000
    cutoff_bid = nearest(bid, cutoff_ms)
    cutoff_ask = nearest(ask, cutoff_ms)
    if not cutoff_bid or not cutoff_ask:
        return None

    history = []
    for minutes in range(181, -1, -1):
        row = nearest(bid, cutoff_ms - minutes * 60_000, tolerance_minutes=0)
        if row:
            history.append(row)
    if len(history) < 150:
        return None

    closes = np.asarray([row["close"] for row in history], dtype=float)
    highs = np.asarray([row["high"] for row in history], dtype=float)
    lows = np.asarray([row["low"] for row in history], dtype=float)
    opens = np.asarray([row["open"] for row in history], dtype=float)
    volumes = np.asarray([row["volume"] for row in history], dtype=float)
    true_ranges = np.maximum(
        highs[1:] - lows[1:],
        np.maximum(np.abs(highs[1:] - closes[:-1]), np.abs(lows[1:] - closes[:-1])),
    )
    atr = float(np.mean(true_ranges[-30:]))
    if not math.isfinite(atr) or atr <= 0:
        return None

    def ret(minutes: int) -> float:
        return float((closes[-1] - closes[-1 - minutes]) / atr)

    def price_range(minutes: int) -> float:
        return float((np.max(highs[-minutes:]) - np.min(lows[-minutes:])) / atr)

    volume_std = float(np.std(volumes[-60:]))
    spread = cutoff_ask["close"] - cutoff_bid["close"]
    features = [
        ret(5),
        ret(15),
        ret(30),
        ret(60),
        price_range(5),
        price_range(15),
        price_range(30),
        float((closes[-1] - opens[-5]) / atr),
        float((closes[-1] - opens[-15]) / atr),
        0.0 if volume_std == 0 else float((np.mean(volumes[-5:]) - np.mean(volumes[-60:])) / volume_std),
        float((closes[-1] - opens[0]) / atr),
        float(spread / atr),
        float(atr / closes[-1]),
        *[1.0 if event_name == event else 0.0 for event in EVENTS],
    ]
    context = {
        "cutoff_utc": datetime.fromtimestamp(cutoff_ms / 1000, timezone.utc).isoformat(),
        "cutoff_price": round((cutoff_bid["close"] + cutoff_ask["close"]) / 2, 3),
        "atr_30m": round(atr, 4),
        "spread": round(spread, 4),
        "momentum_15_atr": round(features[1], 4),
        "momentum_30_atr": round(features[2], 4),
        "volume_z": round(features[9], 4),
        "feature_values": {name: round(value, 7) for name, value in zip(FEATURE_NAMES, features)},
    }
    return features, context


def label_reaction(
    release_utc: datetime,
    bid: dict[int, dict[str, float]],
    ask: dict[int, dict[str, float]],
    atr: float,
) -> dict | None:
    release_ms = int(release_utc.timestamp() * 1000)
    before_bid = nearest(bid, release_ms - 60_000)
    before_ask = nearest(ask, release_ms - 60_000)
    release_bid = nearest(bid, release_ms)
    release_ask = nearest(ask, release_ms)
    if not all((before_bid, before_ask, release_bid, release_ask)):
        return None

    base_mid = (before_bid["close"] + before_ask["close"]) / 2
    spread = before_ask["close"] - before_bid["close"]
    up_excursion = release_bid["high"] - before_ask["close"]
    down_excursion = before_bid["close"] - release_ask["low"]
    release_mid = (release_bid["close"] + release_ask["close"]) / 2
    release_move = release_mid - base_mid
    threshold = max(0.15 * atr, 2 * spread)
    if abs(release_move) < threshold:
        impulse = "UNCERTAIN"
    elif release_move > 0:
        impulse = "BUY"
    else:
        impulse = "SELL"

    sustained = {}
    prices = {}
    for horizon in (1, 5, 15):
        stamp = release_ms + (horizon - 1) * 60_000
        horizon_bid = nearest(bid, stamp)
        horizon_ask = nearest(ask, stamp)
        if not horizon_bid or not horizon_ask:
            sustained[str(horizon)] = "UNAVAILABLE"
            continue
        mid = (horizon_bid["close"] + horizon_ask["close"]) / 2
        move = mid - base_mid
        sustained[str(horizon)] = (
            "BUY" if move >= threshold else "SELL" if move <= -threshold else "UNCERTAIN"
        )
        prices[str(horizon)] = round(move, 3)

    return {
        "impulse": impulse,
        "threshold": threshold,
        "up_excursion": up_excursion,
        "down_excursion": down_excursion,
        "release_move": release_move,
        "range": release_bid["high"] - release_ask["low"],
        "base_mid": base_mid,
        "sustained": sustained,
        "moves": prices,
    }


def build_samples(lead_minutes: int) -> tuple[list[dict], dict]:
    events = load_calendar()
    days = sorted({event.release_utc.date().isoformat() for event in events})
    spreads = annual_spreads(days)
    global_spread = float(np.median(list(spreads.values()))) if spreads else 0.3
    samples = []
    skipped = []
    imputed = []
    cache: dict[tuple[str, str], dict[int, dict[str, float]]] = {}

    for event in events:
        day = event.release_utc.date().isoformat()
        for side in ("bid", "ask"):
            key = (day, side)
            if key not in cache:
                cache[key] = load_day(day, side)
        bid, ask, imputed_side = complete_sides(
            cache[(day, "bid")],
            cache[(day, "ask")],
            spreads.get(event.release_utc.year, global_spread),
        )
        extracted = extract_features(event.event, event.release_utc, bid, ask, lead_minutes)
        if extracted is None:
            skipped.append({"event": event.event, "release_utc": event.release_utc.isoformat()})
            continue
        features, context = extracted
        reaction = label_reaction(event.release_utc, bid, ask, context["atr_30m"])
        if reaction is None:
            skipped.append({"event": event.event, "release_utc": event.release_utc.isoformat()})
            continue
        if imputed_side:
            imputed.append({"date": day, "side": imputed_side})
        samples.append(
            {
                "event": event.event,
                "release_utc": event.release_utc.isoformat(),
                "features": features,
                "target": reaction["impulse"],
                "reaction": reaction,
                "context": context,
            }
        )
    return samples, {
        "calendar_events": len(events),
        "usable_samples": len(samples),
        "skipped": len(skipped),
        "imputed_sides": len(imputed),
        "skipped_examples": skipped[:20],
    }
