from __future__ import annotations

from datetime import datetime, timedelta
import os
from typing import Any

import pandas as pd

from .models import TRADE_SYMBOLS
from .mt5_client import MT5Client, TIMEFRAME_MINUTES
from .session_time import DEFAULT_DATA_TIMEZONE, now_naive
from .strategy_engine import detect_aoi, detect_bias, detect_market_structure, generate_preentry_candidate, generate_signal


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
FOREX_CURRENCIES = {"AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD"}


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_forex_pair(symbol: str) -> bool:
    upper = symbol.upper()
    return len(upper) == 6 and upper[:3] in FOREX_CURRENCIES and upper[3:] in FOREX_CURRENCIES


def _direction_matches_bias(direction: str, bias: str) -> bool:
    direction = direction.upper()
    return (direction == "BUY" and bias == "bullish") or (direction == "SELL" and bias == "bearish")


def _direction_opposes_bias(direction: str, bias: str) -> bool:
    direction = direction.upper()
    return (direction == "BUY" and bias == "bearish") or (direction == "SELL" and bias == "bullish")


def _closed_candles(candles, timeframe: str, now: datetime):
    if candles is None or len(candles) == 0:
        return candles
    minutes = TIMEFRAME_MINUTES.get(str(timeframe).upper())
    if not minutes:
        return candles
    times = pd.to_datetime(candles["time"])
    closed = candles.loc[times + timedelta(minutes=minutes) <= now].copy()
    return closed.reset_index(drop=True)


def _forex_htf_context(client: MT5Client, symbol: str, now: datetime) -> dict[str, Any]:
    biases: dict[str, str] = {}
    for timeframe in ("H1", "H4", "D1"):
        start = now - timedelta(days=LOOKBACK_DAYS.get(timeframe, 120))
        candles = client.fetch_candles(symbol, timeframe, start, now)
        if candles is None or len(candles) < 80:
            biases[timeframe] = "unavailable"
        else:
            biases[timeframe] = detect_bias(candles, timeframe)
    return {"required": True, "biases": biases}


def _forex_htf_agreement(direction: str, context: dict[str, Any]) -> tuple[bool, str]:
    biases = context.get("biases") or {}
    align_count = sum(1 for bias in biases.values() if _direction_matches_bias(direction, str(bias)))
    oppose_count = sum(1 for bias in biases.values() if _direction_opposes_bias(direction, str(bias)))
    unavailable = [timeframe for timeframe, bias in biases.items() if bias == "unavailable"]
    if unavailable:
        return False, f"Forex HTF agreement unavailable on {', '.join(unavailable)}."
    if align_count >= 2 and oppose_count == 0:
        return True, "Forex HTF agreement passed: at least two of H1/H4/D1 align and none oppose."
    return False, f"Forex HTF agreement failed: H1/H4/D1 biases are {biases}."


def scan_market(
    symbols: list[str] | tuple[str, ...] = TRADE_SYMBOLS,
    timeframes: list[str] | tuple[str, ...] = DEFAULT_SCAN_TIMEFRAMES,
    min_score: int = 90,
    preplace_min_score: int = 92,
    min_rr: float = 5.0,
    max_stale: timedelta = timedelta(days=2),
) -> dict[str, Any]:
    client = MT5Client()
    status = client.terminal_status()
    data_timezone = os.getenv("MARKET_DATA_TIMEZONE", DEFAULT_DATA_TIMEZONE)
    now = now_naive(data_timezone)
    result: dict[str, Any] = {
        "scanned_at": now.isoformat(timespec="seconds"),
        "mt5_status": status.get("message"),
        "allowed": [],
        "preplace": [],
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
        require_forex_htf = _env_bool("AUTO_FOREX_REQUIRE_HTF_AGREEMENT", True) and _is_forex_pair(symbol)
        forex_htf_context = _forex_htf_context(client, symbol, now) if require_forex_htf else None

        for timeframe in timeframes:
            start = now - timedelta(days=LOOKBACK_DAYS.get(timeframe, 90))
            candles = client.fetch_candles(symbol, timeframe, start, now)
            candles = _closed_candles(candles, timeframe, now)
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
            signal_handled = False
            if signal:
                if forex_htf_context and signal.get("direction"):
                    ok, reason = _forex_htf_agreement(str(signal["direction"]), forex_htf_context)
                    signal["higher_timeframe_agreement"] = forex_htf_context
                    signal.setdefault("reasons", []).append(reason)
                    if not ok:
                        item = {**common, **signal}
                        item["setup_score"] = min(int(item.get("setup_score") or 0), 79)
                        item["setup_grade"] = "B"
                        item["status"] = "rejected"
                        result["rejected"].append(item)
                        continue
                item = {**common, **signal}
                if signal["status"] == "allowed" and signal["setup_score"] >= min_score:
                    result["allowed"].append(item)
                    if _env_bool("AUTO_PREFER_RETEST_LIMITS", True):
                        pullback = generate_preentry_candidate(
                            candles,
                            symbol=symbol,
                            timeframe=timeframe,
                            min_score=preplace_min_score,
                            min_rr=min_rr,
                            allow_after_confirmation=True,
                            limit_only=True,
                        )
                        if pullback and pullback.get("direction") == signal.get("direction"):
                            pullback["market_confirmation_score"] = signal.get("setup_score")
                            pullback["market_confirmation_model"] = signal.get("entry_model")
                            result["preplace"].append({**common, **pullback})
                    continue
                if signal["setup_score"] >= 80:
                    result["near_misses"].append(item)
                else:
                    result["rejected"].append(item)
                signal_handled = True

            preplace = generate_preentry_candidate(
                candles,
                symbol=symbol,
                timeframe=timeframe,
                min_score=preplace_min_score,
                min_rr=min_rr,
            )
            if preplace:
                if forex_htf_context and preplace.get("direction"):
                    ok, reason = _forex_htf_agreement(str(preplace["direction"]), forex_htf_context)
                    preplace["higher_timeframe_agreement"] = forex_htf_context
                    preplace.setdefault("reasons", []).append(reason)
                    if not ok:
                        rejected = {**common, **preplace}
                        rejected["setup_score"] = min(int(rejected.get("setup_score") or 0), 79)
                        rejected["setup_grade"] = "B"
                        rejected["status"] = "rejected"
                        result["rejected"].append(rejected)
                        continue
                result["preplace"].append({**common, **preplace})
                continue
            elif signal_handled:
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

    for key in ("allowed", "preplace", "near_misses", "rejected"):
        result[key].sort(key=lambda item: item.get("setup_score", 0), reverse=True)
    return result
