from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import joblib
import MetaTrader5 as mt5
import numpy as np

from news_core import EVENTS, ROOT, complete_sides, extract_features, normalize_rows


PREDICTION_DIR = ROOT / "predictions"


def load_env() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def compact(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def discover_gold() -> str:
    wanted = compact(os.getenv("XAU_SYMBOL", "XAUUSD"))
    symbols = mt5.symbols_get()
    if not symbols:
        raise RuntimeError(f"MT5 returned no symbols: {mt5.last_error()}")
    names = [item.name for item in symbols]
    ranked = sorted(
        names,
        key=lambda name: (
            compact(name) != wanted,
            not compact(name).startswith(wanted),
            len(name),
        ),
    )
    for name in ranked:
        if wanted in compact(name) and mt5.symbol_select(name, True):
            return name
    raise RuntimeError("Could not discover an XAUUSD broker symbol.")


def bars_for_prediction(symbol: str, release_utc: datetime) -> tuple[dict, dict]:
    now = datetime.now(timezone.utc)
    last_complete = now.replace(second=0, microsecond=0) - timedelta(minutes=1)
    start = release_utc.replace(tzinfo=timezone.utc).timestamp() - 5 * 60 * 60
    rates = mt5.copy_rates_range(
        symbol,
        mt5.TIMEFRAME_M1,
        datetime.fromtimestamp(start, timezone.utc),
        min(last_complete, release_utc),
    )
    if rates is None or len(rates) < 150:
        raise RuntimeError(f"Insufficient MT5 M1 history for {symbol}: {mt5.last_error()}")
    rows = normalize_rows(
        [
            {
                "time": int(row["time"]),
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "tick_volume": row["tick_volume"],
            }
            for row in rates
        ]
    )
    bid = {round(row["timestamp"] / 60_000) * 60_000: row for row in rows}
    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    spread = (
        float(tick.ask - tick.bid)
        if tick is not None and tick.ask > tick.bid
        else float(info.spread * info.point)
    )
    _, ask, _ = complete_sides(bid, {}, spread)
    return bid, ask


def choose_lead(minutes_before: float) -> int:
    return 15 if abs(minutes_before - 15) <= abs(minutes_before - 30) else 30


def reason_lines(context: dict, event: str) -> list[str]:
    reasons = []
    momentum = context["momentum_15_atr"]
    if momentum > 0.25:
        reasons.append("Gold has bullish pre-release 15-minute momentum.")
    elif momentum < -0.25:
        reasons.append("Gold has bearish pre-release 15-minute momentum.")
    else:
        reasons.append("Gold pre-release momentum is neutral.")
    if abs(context["volume_z"]) > 1:
        reasons.append("Pre-release tick volume is unusually elevated.")
    reasons.append(f"The model uses the historical {event} reaction profile.")
    return reasons


def make_prediction(event: str, release_utc: datetime) -> dict:
    event = event.upper()
    now = datetime.now(timezone.utc)
    minutes_before = (release_utc - now).total_seconds() / 60
    if event not in EVENTS:
        return {
            "event": event,
            "release_time_utc": release_utc.isoformat(),
            "prediction": "NO TRADE",
            "confidence_pct": 0.0,
            "data_quality": "unsupported event",
            "reason": f"The trained archive does not yet cover {event}.",
        }
    if minutes_before <= 0:
        raise RuntimeError("Pre-release predictions cannot be generated after the event has started.")
    if not 8 <= minutes_before <= 40:
        raise RuntimeError(
            f"Query is {minutes_before:.1f} minutes before release; the supported window is 8-40 minutes."
        )

    lead = choose_lead(minutes_before)
    artifact = joblib.load(ROOT / "models" / f"gold_news_impulse_{lead}m.joblib")
    terminal = os.getenv("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
    if not mt5.initialize(path=terminal):
        raise RuntimeError(f"Could not initialize MT5: {mt5.last_error()}")
    try:
        symbol = discover_gold()
        bid, ask = bars_for_prediction(symbol, release_utc)
        feature_cutoff = now.replace(second=0, microsecond=0) - timedelta(minutes=1)
        feature_anchor = feature_cutoff + timedelta(minutes=lead)
        extracted = extract_features(event, feature_anchor, bid, ask, lead)
        if extracted is None:
            raise RuntimeError("The required pre-release M1 feature window is incomplete.")
        features, context = extracted
        probabilities = artifact["model"].predict_proba(np.asarray([features], dtype=float))[0]
        probability_map = {
            label: float(value)
            for label, value in zip(artifact["model"].classes_, probabilities)
        }
        buy = probability_map.get("BUY", 0.0)
        sell = probability_map.get("SELL", 0.0)
        uncertain = probability_map.get("UNCERTAIN", 0.0)
        direction = "BUY" if buy >= sell else "SELL"
        confidence = max(buy, sell)
        prediction = (
            direction
            if confidence >= artifact["threshold"] and confidence > uncertain
            else "NO TRADE"
        )
        expected = artifact["expected_ranges"].get(event, {})
        invalidation = (
            "A materially stronger-than-forecast USD release invalidates a Gold BUY bias."
            if direction == "BUY"
            else "A materially weaker-than-forecast USD release invalidates a Gold SELL bias."
        )
        result = {
            "generated_at_utc": now.isoformat(),
            "event": event,
            "release_time_utc": release_utc.isoformat(),
            "minutes_before_release": round(minutes_before, 2),
            "symbol": symbol,
            "prediction": prediction,
            "directional_model_bias": direction,
            "confidence_pct": round(100 * confidence, 2),
            "probabilities": {key: round(100 * value, 2) for key, value in probability_map.items()},
            "expected_impulse_range_usd": {
                "median": expected.get("median_usd"),
                "upper_typical_p75": expected.get("p75_usd"),
            },
            "expected_reaction_window": "release minute; sub-minute timing unavailable from M1 training data",
            "main_reasons": reason_lines(context, event),
            "key_invalidation_condition": invalidation,
            "alternative_scenario": "Use the opposite direction only when the actual-versus-forecast surprise clearly contradicts the model bias.",
            "data_quality": "partial: live XAUUSD M1 available; consensus, DXY, yields, and sub-minute ticks unavailable",
            "model": {
                "name": artifact["model_name"],
                "lead_minutes": lead,
                "threshold": artifact["threshold"],
                "trained_through": artifact["trained_through"],
            },
            "market_context": context,
            "execution_capability": False,
        }
    finally:
        mt5.shutdown()

    PREDICTION_DIR.mkdir(exist_ok=True)
    filename = f"{release_utc.strftime('%Y%m%dT%H%M%SZ')}-{event.lower()}.json"
    path = PREDICTION_DIR / filename
    if path.exists():
        raise RuntimeError(f"A prediction is already permanently saved for this event: {path}")
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    result["saved_to"] = str(path)
    return result


def parse_release(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("Release time must include a timezone or Z.")
    return parsed.astimezone(timezone.utc)


def main() -> None:
    load_env()
    parser = argparse.ArgumentParser(description="Predict the immediate XAUUSD news impulse.")
    parser.add_argument("--event", required=True, help="NFP, GDP, CPI, PPI, or FOMC")
    parser.add_argument("--release", required=True, type=parse_release, help="ISO-8601 release time")
    args = parser.parse_args()
    print(json.dumps(make_prediction(args.event, args.release), indent=2))


if __name__ == "__main__":
    main()
