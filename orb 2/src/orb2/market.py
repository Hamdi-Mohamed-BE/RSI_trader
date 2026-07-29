from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re

import MetaTrader5 as mt5
import pandas as pd

from .config import RuntimeConfig


ALIASES = {
    "XAUUSD": ("XAUUSD", "GOLD"),
    "XAGUSD": ("XAGUSD", "SILVER"),
    "US100": ("US100", "NAS100", "USTEC", "NDX100", "NASDAQ100"),
    "US30": ("US30", "DJ30", "WS30", "DOW30"),
    "ETHUSD": ("ETHUSD", "ETHUSDT"),
    "BTCUSD": ("BTCUSD", "BTCUSDT"),
}


class MarketError(RuntimeError):
    pass


def initialize(runtime: RuntimeConfig) -> None:
    if not mt5.initialize(path=runtime.mt5_path, timeout=30_000):
        raise MarketError(f"MT5 initialization failed: {mt5.last_error()}")


def shutdown() -> None:
    mt5.shutdown()


def _normalized(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def resolve_symbol(requested: str) -> str:
    requested_key = _normalized(requested)
    aliases = ALIASES.get(requested_key, (requested_key,))
    ranked: list[tuple[int, int, str]] = []
    for item in mt5.symbols_get() or []:
        normalized = _normalized(item.name)
        score = -1
        if normalized == requested_key:
            score = 100
        elif normalized.startswith(requested_key):
            score = 95
        else:
            for index, alias in enumerate(aliases):
                if normalized == alias:
                    score = max(score, 90 - index)
                elif normalized.startswith(alias):
                    score = max(score, 85 - index)
                elif alias in normalized:
                    score = max(score, 70 - index)
        if score >= 0:
            ranked.append((score, int(bool(item.visible)), item.name))
    if not ranked:
        raise MarketError(f"Could not map {requested} to a broker symbol.")
    ranked.sort(reverse=True)
    selected = ranked[0][2]
    if not mt5.symbol_select(selected, True):
        raise MarketError(f"Could not select broker symbol {selected}.")
    return selected


def symbol_info(symbol: str):
    info = mt5.symbol_info(symbol)
    if info is None:
        raise MarketError(f"No symbol metadata for {symbol}.")
    return info


def _cache_path(runtime: RuntimeConfig, symbol: str, start: datetime, end: datetime) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", symbol)
    return (
        runtime.root
        / ".cache"
        / f"{safe}_M5_{start.date().isoformat()}_{end.date().isoformat()}.pkl"
    )


def fetch_m5(
    runtime: RuntimeConfig, symbol: str, start: datetime, end: datetime
) -> pd.DataFrame:
    cache = _cache_path(runtime, symbol, start, end)
    cache_is_final = end < datetime.now(timezone.utc) - timedelta(minutes=15)
    if runtime.cache_data and cache.exists() and cache_is_final:
        frame = pd.read_pickle(cache)
        if not frame.empty:
            return frame
    raw = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, start, end)
    if raw is None:
        raise MarketError(f"MT5 M5 request failed for {symbol}: {mt5.last_error()}")
    frame = pd.DataFrame(raw)
    if frame.empty:
        raise MarketError(f"MT5 returned no M5 history for {symbol}.")
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    frame = frame.set_index("time").sort_index()
    numeric = (
        "open",
        "high",
        "low",
        "close",
        "tick_volume",
        "spread",
        "real_volume",
    )
    for column in numeric:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if runtime.cache_data:
        cache.parent.mkdir(parents=True, exist_ok=True)
        frame.to_pickle(cache)
    return frame
