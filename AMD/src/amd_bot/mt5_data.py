from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import re
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd


class MT5Error(RuntimeError):
    pass


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
        choices: list[tuple[tuple[int, int, int, int], str]] = []
        for item in available:
            candidate = normalize(item.name)
            if candidate == wanted:
                score = 3
            elif candidate.startswith(wanted):
                score = 2
            elif wanted in candidate:
                score = 1
            else:
                continue
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
    rates = mt5.copy_rates_range(
        symbol,
        mt5.TIMEFRAME_M1,
        start.astimezone(timezone.utc),
        end.astimezone(timezone.utc),
    )
    if rates is None or not len(rates):
        raise MT5Error(f"No M1 history for {symbol}: {mt5.last_error()}")
    frame = pd.DataFrame(rates)
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    frame = frame.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    frame.to_csv(path, index=False, compression="gzip")
    return frame
