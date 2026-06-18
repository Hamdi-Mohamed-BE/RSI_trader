from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .models import TRADE_SYMBOLS
from .mt5_client import MT5Client
from .strategy_engine import detect_aoi, detect_bias, detect_market_structure, generate_signal


DEFAULT_SCAN_TIMEFRAMES: tuple[str, ...] = ("M5", "M15", "M30", "H1", "H4", "D1", "W1")
LOOKBACK_DAYS: dict[str, int] = {
    "M1": 14,
    "M5": 45,
    "M15": 60,
    "M30": 90,
    "H1": 120,
    "H4": 240,
    "D1": 720,
    "W1": 3650,
}
STALE_LIMITS: dict[str, timedelta] = {
    "D1": timedelta(days=4),
    "W1": timedelta(days=10),
}


def scan_market(
    symbols: list[str] | tuple[str, ...] = TRADE_SYMBOLS,
    timeframes: list[str] | tuple[str, ...] = DEFAULT_SCAN_TIMEFRAMES,
    min_score: int = 90,
    min_rr: float = 5.0,
    max_stale: timedelta = timedelta(days=2),
) -> dict[str, Any]:
    client = MT5Client()
    status = client.terminal_status()
    now = datetime.now()
    result: dict[str, Any] = {
        "scanned_at": now.isoformat(timespec="seconds"),
        "mt5_status": status.get("message"),
        "allowed": [],
        "near_misses": [],
        "rejected": [],
        "stale": [],
        "errors": [],
    }

    if not status.get("connected"):
        result["errors"].append({"error": "MT5 is not connected."})
        return result

    for symbol in symbols:
        resolved = client.resolve_symbol(symbol)
        quote = client.current_quote(symbol)
        if not resolved:
            result["errors"].append({"symbol": symbol, "error": "Symbol not found or not available in MT5."})
            continue

        for timeframe in timeframes:
            start = now - timedelta(days=LOOKBACK_DAYS.get(timeframe, 90))
            candles = client.fetch_candles(symbol, timeframe, start, now)
            if candles is None or len(candles) < 120:
                result["errors"].append(
                    {
                        "symbol": symbol,
                        "broker_symbol": resolved,
                        "timeframe": timeframe,
                        "error": f"Not enough candles: {0 if candles is None else len(candles)}",
                    }
                )
                continue

            last = candles.iloc[-1]
            last_time = last["time"].to_pydatetime() if hasattr(last["time"], "to_pydatetime") else last["time"]
            common = {
                "symbol": symbol,
                "broker_symbol": resolved,
                "timeframe": timeframe,
                "last_candle_time": str(last["time"]),
                "last_close": round(float(last["close"]), 5),
                "bid": round(float(quote["bid"]), 5) if quote else None,
                "ask": round(float(quote["ask"]), 5) if quote else None,
                "spread": round(float(quote["spread"]), 5) if quote and quote.get("spread") is not None else None,
                "spread_points": round(float(quote["spread_points"]), 1)
                if quote and quote.get("spread_points") is not None
                else None,
                "candles": int(len(candles)),
            }

            stale_limit = STALE_LIMITS.get(timeframe, max_stale)
            if now - last_time > stale_limit:
                result["stale"].append({**common, "reason": "Latest candle is stale, ignored for live scan."})
                continue

            signal = generate_signal(candles, symbol=symbol, timeframe=timeframe, min_score=min_score, min_rr=min_rr)
            if signal:
                item = {**common, **signal}
                if signal["status"] == "allowed" and signal["setup_score"] >= min_score:
                    result["allowed"].append(item)
                elif signal["setup_score"] >= 80:
                    result["near_misses"].append(item)
                else:
                    result["rejected"].append(item)
                continue

            aoi = detect_aoi(candles)
            if aoi:
                result["rejected"].append(
                    {
                        **common,
                        "setup_score": 0,
                        "setup_grade": "NO SIGNAL",
                        "status": "rejected",
                        "bias": detect_bias(candles, timeframe),
                        "structure": detect_market_structure(candles).get("structure"),
                        "key_level": aoi.get("key_level"),
                        "profile_type": aoi.get("profile_type"),
                        "reasons": [
                            "Near an LTA level, but no official entry model confirmed on the latest candle."
                        ],
                    }
                )

    for key in ("allowed", "near_misses", "rejected"):
        result[key].sort(key=lambda item: item.get("setup_score", 0), reverse=True)
    return result
