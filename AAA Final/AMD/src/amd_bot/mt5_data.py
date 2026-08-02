from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import re
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd


class MT5Error(RuntimeError):
    pass


SYMBOL_ALIASES: dict[str, tuple[str, ...]] = {
    "US100": ("US100", "NAS100", "USTEC", "NDX100", "NASDAQ100"),
    "US30": ("US30", "DJ30", "DJI30", "DOW30", "WS30"),
}


def normalize(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


@contextmanager
def connection():
    if not mt5.initialize():
        raise MT5Error(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        if account is None:
            raise MT5Error(f"No connected MT5 account: {mt5.last_error()}")
        yield account
    finally:
        mt5.shutdown()


def discover_symbols(instruments: tuple[str, ...]) -> dict[str, str]:
    available = mt5.symbols_get()
    if not available:
        raise MT5Error(f"Cannot read broker symbols: {mt5.last_error()}")
    result: dict[str, str] = {}
    for requested in instruments:
        wanted = normalize(requested)
        aliases = tuple(
            normalize(alias)
            for alias in SYMBOL_ALIASES.get(wanted, (wanted,))
        )
        choices: list[tuple[tuple[int, int, int, int], str]] = []
        for item in available:
            candidate = normalize(item.name)
            match_scores = []
            for alias in aliases:
                if candidate == alias:
                    match_scores.append(3)
                elif candidate.startswith(alias):
                    match_scores.append(2)
                elif alias in candidate:
                    match_scores.append(1)
            if not match_scores:
                continue
            score = max(match_scores)
            choices.append(
                (
                    (
                        int(item.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED),
                        score,
                        int(bool(item.visible)),
                        -len(item.name),
                    ),
                    item.name,
                )
            )
        if not choices:
            raise MT5Error(f"No broker symbol matches {requested}")
        symbol = max(choices, key=lambda row: row[0])[1]
        if not mt5.symbol_select(symbol, True):
            raise MT5Error(f"Cannot select {symbol}: {mt5.last_error()}")
        result[requested] = symbol
    return result


def symbol_metadata(symbol: str) -> dict[str, float | int]:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise MT5Error(f"Cannot read {symbol}: {mt5.last_error()}")
    return {
        "point": float(info.point),
        "digits": int(info.digits),
        "volume_min": float(info.volume_min),
        "volume_max": float(info.volume_max),
        "volume_step": float(info.volume_step),
        "filling_mode": int(info.filling_mode),
        "stops_level": int(info.trade_stops_level),
    }


def cache_path(cache_dir: Path, symbol: str, start: datetime, end: datetime) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", symbol)
    return cache_dir / f"{safe}_{start:%Y%m%d}_{end:%Y%m%d}_M1.csv.gz"


def load_m1(
    symbol: str,
    start: datetime,
    end: datetime,
    cache_dir: Path,
    refresh: bool = False,
) -> pd.DataFrame:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_path(cache_dir, symbol, start, end)
    if path.exists() and not refresh:
        frame = pd.read_csv(path)
        frame["time"] = pd.to_datetime(frame["time"], utc=True)
        return frame
    chunks = []
    chunk_end = end.astimezone(timezone.utc)
    utc_start = start.astimezone(timezone.utc)
    # Large M1 requests are rejected by some terminals/brokers. Work backwards
    # in bounded windows and keep the history the broker actually provides.
    while chunk_end > utc_start:
        chunk_start = max(utc_start, chunk_end - timedelta(days=14))
        rates = mt5.copy_rates_range(
            symbol,
            mt5.TIMEFRAME_M1,
            chunk_start,
            chunk_end,
        )
        if rates is not None and len(rates):
            chunks.append(pd.DataFrame(rates))
        chunk_end = chunk_start
    if not chunks:
        raise MT5Error(f"No M1 history for {symbol}: {mt5.last_error()}")
    frame = pd.concat(reversed(chunks), ignore_index=True)
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    frame = frame.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    frame.to_csv(path, index=False, compression="gzip")
    return frame
