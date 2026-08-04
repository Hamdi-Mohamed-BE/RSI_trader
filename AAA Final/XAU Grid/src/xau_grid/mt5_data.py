from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re

import MetaTrader5 as mt5
import pandas as pd


class MT5Error(RuntimeError):
    pass


@dataclass(frozen=True)
class SymbolSpec:
    symbol: str
    point: float
    tick_size: float
    tick_value: float
    contract_size: float
    volume_min: float
    volume_step: float
    volume_max: float
    digits: int


@contextmanager
def connected():
    if not mt5.initialize():
        raise MT5Error(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        yield
    finally:
        mt5.shutdown()


def _normalized(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def discover_xau(canonical: str = "XAUUSD") -> str:
    symbols = mt5.symbols_get()
    if not symbols:
        raise MT5Error(f"MT5 returned no symbols: {mt5.last_error()}")
    target = _normalized(canonical)
    candidates = []
    for item in symbols:
        normalized = _normalized(item.name)
        if target not in normalized and not ("GOLD" in normalized and target == "XAUUSD"):
            continue
        tradable = int(getattr(item, "trade_mode", 0)) != int(mt5.SYMBOL_TRADE_MODE_DISABLED)
        exact = normalized == target
        starts = normalized.startswith(target)
        candidates.append((tradable, exact, starts, -len(item.name), item.name))
    if not candidates:
        raise MT5Error(f"No tradable XAUUSD broker alias found for {canonical!r}")
    candidates.sort(reverse=True)
    symbol = candidates[0][-1]
    if not mt5.symbol_select(symbol, True):
        raise MT5Error(f"Could not select {symbol}: {mt5.last_error()}")
    return symbol


def symbol_spec(symbol: str) -> SymbolSpec:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise MT5Error(f"No symbol metadata for {symbol}")
    tick_size = float(info.trade_tick_size or info.point)
    tick_value = float(info.trade_tick_value_loss or info.trade_tick_value or 0.0)
    contract_size = float(info.trade_contract_size or 100.0)
    return SymbolSpec(
        symbol=symbol,
        point=float(info.point),
        tick_size=tick_size,
        tick_value=tick_value,
        contract_size=contract_size,
        volume_min=float(info.volume_min),
        volume_step=float(info.volume_step),
        volume_max=float(info.volume_max),
        digits=int(info.digits),
    )


def account_snapshot() -> dict[str, object]:
    account = mt5.account_info()
    if account is None:
        raise MT5Error(f"No connected MT5 account: {mt5.last_error()}")
    return {
        "login": int(account.login),
        "server": account.server,
        "currency": account.currency,
        "balance": float(account.balance),
        "equity": float(account.equity),
        "margin_free": float(account.margin_free),
        "margin_level": float(account.margin_level or 0.0),
        "leverage": int(account.leverage),
        "trade_allowed": bool(account.trade_allowed),
    }


def fetch_m5(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    start = start.astimezone(timezone.utc)
    end = end.astimezone(timezone.utc)
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, start, end)
    if rates is None or len(rates) == 0:
        raise MT5Error(f"No M5 data for {symbol}: {mt5.last_error()}")
    frame = pd.DataFrame(rates)
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    frame = frame.set_index("time").sort_index()
    frame = frame[~frame.index.duplicated(keep="last")]
    return frame


def load_history(
    symbol: str,
    start: datetime,
    end: datetime,
    cache_path: Path | None = None,
    refresh: bool = False,
) -> pd.DataFrame:
    if cache_path and cache_path.exists() and not refresh:
        frame = pd.read_csv(cache_path, parse_dates=["time"]).set_index("time")
        frame.index = pd.to_datetime(frame.index, utc=True)
        if frame.index.min() <= pd.Timestamp(start) and frame.index.max() >= pd.Timestamp(end) - pd.Timedelta(days=1):
            return frame.loc[pd.Timestamp(start):pd.Timestamp(end)].copy()
    frame = fetch_m5(symbol, start, end)
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        frame.reset_index().to_csv(cache_path, index=False)
    return frame


def round_price(price: float, spec: SymbolSpec) -> float:
    steps = round(price / spec.tick_size)
    return round(steps * spec.tick_size, spec.digits)

