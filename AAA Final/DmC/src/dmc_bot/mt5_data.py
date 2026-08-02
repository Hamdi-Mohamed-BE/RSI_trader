from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import math
from pathlib import Path
import re

import MetaTrader5 as mt5
import pandas as pd


class MT5Error(RuntimeError):
    pass


@contextmanager
def connection():
    """Use the account already connected in the open MT5 terminal."""
    if not mt5.initialize():
        raise MT5Error(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        yield
    finally:
        mt5.shutdown()


def account_summary() -> dict[str, object]:
    info = mt5.account_info()
    if info is None:
        raise MT5Error(f"Cannot read MT5 account: {mt5.last_error()}")
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
    }


def _clean(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def _score(name: str, hint: str) -> tuple[int, int, str]:
    clean = _clean(name)
    requested = _clean(hint)
    exact = {
        "US100": 1000,
        "NAS100": 990,
        "USTEC": 980,
        "NASDAQ100": 970,
        "NDX100": 960,
        "NQ100": 950,
        "TECH100": 940,
    }
    score = exact.get(clean, 0)
    aliases = ("US100", "NAS100", "USTEC", "NASDAQ", "TECH100", "NDX", "NQ100")
    for index, alias in enumerate(aliases):
        if alias in clean:
            score = max(score, 900 - index * 10)
    if requested and requested != "AUTO":
        if clean == requested:
            score += 1200
        elif requested in clean:
            score += 100
    if re.search(r"[HMUZ]\d{1,2}$", clean):
        score -= 20
    return score, -len(name), name


def _select(name: str) -> str | None:
    info = mt5.symbol_info(name)
    if info is None or not mt5.symbol_select(name, True):
        return None
    info = mt5.symbol_info(name)
    if info is None or info.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
        return None
    return str(info.name)


def discover_symbol(hint: str = "US100") -> str:
    requested = hint.strip()
    direct = _select(requested) if requested else None
    if direct:
        return direct
    catalogue = tuple(mt5.symbols_get() or ())
    for item in catalogue:
        if requested and item.name.casefold() == requested.casefold():
            selected = _select(item.name)
            if selected:
                return selected
    candidates = [(_score(item.name, requested), item.name) for item in catalogue]
    candidates = [item for item in candidates if item[0][0] > 0]
    candidates.sort(reverse=True)
    for _, name in candidates:
        selected = _select(name)
        if selected:
            return selected
    raise MT5Error(
        f"No tradeable broker symbol found for {requested!r}. Checked exact "
        "names, normalized broker suffixes, and Nasdaq aliases."
    )


def _rates_to_frame(rates) -> pd.DataFrame:
    if rates is None or len(rates) == 0:
        return pd.DataFrame()
    frame = pd.DataFrame(rates)
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    keep = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
    frame = frame[keep].sort_values("time").drop_duplicates("time")
    numeric = [name for name in keep if name != "time"]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors="coerce")
    return frame.dropna(subset=["open", "high", "low", "close"])


def fetch_m1(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, end)
    frame = _rates_to_frame(rates)
    if frame.empty:
        raise MT5Error(f"No M1 history returned for {symbol}: {mt5.last_error()}")
    return frame


def load_or_fetch_m1(
    symbol: str,
    start: datetime,
    end: datetime,
    cache_dir: Path,
    *,
    refresh: bool = True,
) -> pd.DataFrame:
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", symbol)
    path = cache_dir / f"{safe}_M1.csv"
    cached = pd.DataFrame()
    if path.exists():
        cached = pd.read_csv(path, parse_dates=["time"])
        cached["time"] = pd.to_datetime(cached["time"], utc=True)
    need = refresh or cached.empty
    if not cached.empty:
        need = need or cached.time.min().to_pydatetime() > start or cached.time.max().to_pydatetime() < end
    if need:
        fresh = fetch_m1(symbol, start, end)
        cached = pd.concat([cached, fresh], ignore_index=True)
    cached = cached.sort_values("time").drop_duplicates("time")
    cached.to_csv(path, index=False)
    mask = (cached.time >= pd.Timestamp(start)) & (cached.time <= pd.Timestamp(end))
    return cached.loc[mask].reset_index(drop=True)


def normalize_price(symbol: str, value: float) -> float:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise MT5Error(f"Cannot read metadata for {symbol}")
    tick = float(info.trade_tick_size or info.point)
    return round(round(value / tick) * tick, int(info.digits))


def volume_for_risk(symbol: str, side: int, entry: float, stop: float, cash: float) -> float:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise MT5Error(f"Cannot read metadata for {symbol}")
    order_type = mt5.ORDER_TYPE_BUY if side > 0 else mt5.ORDER_TYPE_SELL
    loss = mt5.order_calc_profit(order_type, symbol, 1.0, entry, stop)
    if loss is None or abs(loss) < 1e-9:
        tick_size = float(info.trade_tick_size or info.point)
        tick_value = float(info.trade_tick_value)
        if tick_size <= 0 or tick_value <= 0:
            raise MT5Error(f"Cannot calculate one-lot risk for {symbol}")
        loss = -abs(entry - stop) / tick_size * tick_value
    raw = cash / abs(float(loss))
    step = float(info.volume_step or 0.01)
    volume = math.floor(raw / step + 1e-9) * step
    if volume < float(info.volume_min):
        raise MT5Error(
            f"Minimum {symbol} volume {info.volume_min:g} exceeds the configured cash risk"
        )
    volume = min(volume, float(info.volume_max))
    precision = max(0, len(f"{step:.10f}".rstrip("0").split(".")[-1]))
    return round(volume, precision)


def strategy_orders(symbol: str, magic: int):
    return tuple(order for order in (mt5.orders_get(symbol=symbol) or ()) if int(order.magic) == magic)


def strategy_positions(symbol: str, magic: int):
    return tuple(position for position in (mt5.positions_get(symbol=symbol) or ()) if int(position.magic) == magic)
