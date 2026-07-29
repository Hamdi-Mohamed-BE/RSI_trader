from __future__ import annotations

from datetime import datetime
import re

import MetaTrader5 as mt5
import pandas as pd

from .config import Config


TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "H1": mt5.TIMEFRAME_H1,
}


class MT5Error(RuntimeError):
    pass


def initialize(config: Config) -> None:
    ok = mt5.initialize(config.mt5_path) if config.mt5_path else mt5.initialize()
    if not ok:
        raise MT5Error(f"MT5 initialization failed: {mt5.last_error()}")


def shutdown() -> None:
    mt5.shutdown()


def _normalized(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def resolve_symbol(requested: str) -> str:
    requested_norm = _normalized(requested)
    aliases = {
        "US100": ("NAS100", "USTEC", "NDX100", "NASDAQ100"),
        "US30": ("US30", "DJ30", "WS30", "DOW30"),
        "XAUUSD": ("XAUUSD", "GOLD"),
    }
    requested_aliases = aliases.get(requested_norm, (requested_norm,))
    symbols = list(mt5.symbols_get() or [])
    if not symbols:
        raise MT5Error("MT5 returned no broker symbols.")

    ranked: list[tuple[int, int, str]] = []
    for item in symbols:
        normalized = _normalized(item.name)
        score = -1
        if item.name.upper() == requested.upper():
            score = 100
        elif normalized == requested_norm:
            score = 95
        elif normalized.startswith(requested_norm):
            score = 85
        elif requested_norm in normalized:
            score = 70
        else:
            for rank, alias in enumerate(requested_aliases):
                if normalized == alias:
                    score = max(score, 80 - rank)
                elif normalized.startswith(alias):
                    score = max(score, 75 - rank)
                elif alias in normalized:
                    score = max(score, 65 - rank)
        if score >= 0:
            ranked.append((score, int(bool(item.visible)), item.name))

    if not ranked:
        raise MT5Error(f"Could not map {requested} to a broker symbol.")
    ranked.sort(reverse=True)
    resolved = ranked[0][2]
    if not mt5.symbol_select(resolved, True):
        raise MT5Error(f"Broker symbol {resolved} exists but could not be selected.")
    return resolved


def symbol_info(symbol: str):
    info = mt5.symbol_info(symbol)
    if info is None:
        raise MT5Error(f"No symbol information for {symbol}.")
    return info


def rates(symbol: str, timeframe: str, start: datetime, end: datetime) -> pd.DataFrame:
    raw = mt5.copy_rates_range(symbol, TIMEFRAMES[timeframe], start, end)
    if raw is None:
        raise MT5Error(
            f"MT5 returned no {timeframe} data for {symbol}: {mt5.last_error()}"
        )
    frame = pd.DataFrame(raw)
    if frame.empty:
        return frame
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    frame = frame.set_index("time").sort_index()
    for column in ("open", "high", "low", "close", "tick_volume", "spread"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def account_info():
    info = mt5.account_info()
    if info is None:
        raise MT5Error(f"MT5 account information unavailable: {mt5.last_error()}")
    return info
