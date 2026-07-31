from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
import re

import MetaTrader5 as mt5
import pandas as pd


class MT5Error(RuntimeError):
    pass


@contextmanager
def connection():
    if not mt5.initialize():
        raise MT5Error(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        if account is None:
            raise MT5Error(f"No connected MT5 account: {mt5.last_error()}")
        yield
    finally:
        mt5.shutdown()


def account_summary() -> dict[str, object]:
    info = mt5.account_info()
    terminal = mt5.terminal_info()
    if info is None:
        raise MT5Error(f"No account information: {mt5.last_error()}")
    return {
        "login": int(info.login),
        "server": str(info.server),
        "company": str(info.company),
        "currency": str(info.currency),
        "balance": float(info.balance),
        "equity": float(info.equity),
        "free_margin": float(info.margin_free),
        "leverage": int(info.leverage),
        "trade_allowed": bool(info.trade_allowed),
        "terminal_trade_allowed": bool(getattr(terminal, "trade_allowed", False)),
    }


def _normalized(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def discover_symbol(canonical: str) -> str:
    canonical_n = _normalized(canonical)
    symbols = mt5.symbols_get()
    if symbols is None:
        raise MT5Error(f"Cannot read symbol catalogue: {mt5.last_error()}")
    candidates: list[tuple[tuple[int, int, int, int], str]] = []
    aliases = {
        "XAUUSD": ("XAUUSD", "GOLD"),
        "BTCUSD": ("BTCUSD", "BITCOIN"),
        "ETHUSD": ("ETHUSD", "ETHEREUM"),
        "US100": ("US100", "NAS100", "USTEC", "NASDAQ"),
        "US30": ("US30", "DJ30", "DOW"),
    }
    expected = aliases.get(canonical_n, (canonical_n,))
    for item in symbols:
        name_n = _normalized(item.name)
        alias_match = max(
            (len(alias) for alias in expected if alias in name_n),
            default=0,
        )
        if alias_match == 0:
            continue
        if int(item.trade_mode) == int(mt5.SYMBOL_TRADE_MODE_DISABLED):
            continue
        exact = int(name_n == canonical_n)
        visible = int(bool(item.visible))
        shortest = -len(item.name)
        candidates.append(((exact, alias_match, visible, shortest), item.name))
    if not candidates:
        raise MT5Error(f"No broker symbol matches {canonical}")
    symbol = max(candidates, key=lambda value: value[0])[1]
    if not mt5.symbol_select(symbol, True):
        raise MT5Error(f"Cannot select {symbol}: {mt5.last_error()}")
    return symbol


def symbol_info(symbol: str) -> dict[str, float | int | str]:
    if not mt5.symbol_select(symbol, True):
        raise MT5Error(f"Cannot select {symbol}: {mt5.last_error()}")
    info = mt5.symbol_info(symbol)
    if info is None:
        raise MT5Error(f"No symbol information for {symbol}")
    return {
        "name": symbol,
        "digits": int(info.digits),
        "point": float(info.point),
        "tick_size": float(info.trade_tick_size or info.point),
        "tick_value": float(info.trade_tick_value),
        "contract_size": float(info.trade_contract_size),
        "volume_min": float(info.volume_min),
        "volume_max": float(info.volume_max),
        "volume_step": float(info.volume_step),
    }


def fetch_m1(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("start and end must be timezone-aware")
    rates = mt5.copy_rates_range(
        symbol,
        mt5.TIMEFRAME_M1,
        start.astimezone(timezone.utc),
        end.astimezone(timezone.utc),
    )
    if rates is None or len(rates) == 0:
        raise MT5Error(f"No M1 history for {symbol}: {mt5.last_error()}")
    frame = pd.DataFrame(rates)
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    return frame.drop_duplicates("time").sort_values("time").reset_index(drop=True)


def load_or_fetch_m1(
    symbol: str,
    start: datetime,
    end: datetime,
    cache_dir: Path,
    refresh: bool = False,
) -> pd.DataFrame:
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", symbol)
    path = cache_dir / f"{safe}_{start:%Y%m%d}_{end:%Y%m%d}_M1.csv.gz"
    if path.exists() and not refresh:
        frame = pd.read_csv(path)
        frame["time"] = pd.to_datetime(frame["time"], utc=True)
        return frame
    frame = fetch_m1(symbol, start, end)
    frame.to_csv(path, index=False, compression="gzip")
    return frame


def volume_for_risk(
    symbol: str,
    direction: str,
    entry: float,
    stop: float,
    cash_at_risk: float,
) -> float:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise MT5Error(f"No symbol information for {symbol}")
    order_type = mt5.ORDER_TYPE_BUY if direction == "buy" else mt5.ORDER_TYPE_SELL
    one_lot = mt5.order_calc_profit(order_type, symbol, 1.0, entry, stop)
    if one_lot is None or float(one_lot) == 0:
        raise MT5Error(f"Cannot calculate position risk: {mt5.last_error()}")
    raw = cash_at_risk / abs(float(one_lot))
    minimum = Decimal(str(info.volume_min))
    maximum = Decimal(str(info.volume_max))
    step = Decimal(str(info.volume_step))
    value = max(minimum, min(maximum, Decimal(str(raw))))
    steps = (value / step).quantize(Decimal("1"), rounding=ROUND_DOWN)
    return float(steps * step)
