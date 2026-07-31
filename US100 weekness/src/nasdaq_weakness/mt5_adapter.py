from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import math
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
        yield
    finally:
        mt5.shutdown()


def account_summary() -> dict[str, object]:
    info = mt5.account_info()
    if info is None:
        raise MT5Error(f"Cannot read MT5 account: {mt5.last_error()}")
    return {
        "login": info.login,
        "server": info.server,
        "company": info.company,
        "currency": info.currency,
        "balance": float(info.balance),
        "equity": float(info.equity),
        "margin_free": float(info.margin_free),
        "leverage": int(info.leverage),
        "trade_allowed": bool(info.trade_allowed),
    }


def symbol_score(name: str, canonical: str = "US100") -> tuple[int, int, str]:
    upper = name.upper()
    clean = re.sub(r"[^A-Z0-9]", "", upper)
    exacts = {
        "US100": 1000,
        "NAS100": 990,
        "USTEC": 980,
        "NASDAQ100": 970,
        "NDX100": 960,
        "NQ100": 950,
    }
    score = exacts.get(clean, 0)
    aliases = ("US100", "NAS100", "USTEC", "NASDAQ", "NDX", "NQ")
    for rank, alias in enumerate(aliases):
        if alias in clean:
            score = max(score, 900 - rank * 10)
    if canonical and re.sub(r"[^A-Z0-9]", "", canonical.upper()) in clean:
        score += 100
    if re.search(r"[HMUZ]\d{1,2}$", clean):
        score -= 20
    return score, -len(name), name


def discover_symbol(canonical: str = "US100") -> str:
    candidates: list[tuple[tuple[int, int, str], str]] = []
    for item in mt5.symbols_get() or ():
        score = symbol_score(item.name, canonical)
        if score[0] <= 0:
            continue
        info = mt5.symbol_info(item.name)
        if info is None or info.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
            continue
        candidates.append((score, item.name))
    if not candidates:
        raise MT5Error(
            "No tradeable Nasdaq-100 symbol found. Expected a broker alias "
            "such as US100, NAS100, USTEC, NDX, or NASDAQ."
        )
    candidates.sort(reverse=True)
    symbol = candidates[0][1]
    if not mt5.symbol_select(symbol, True):
        raise MT5Error(f"Could not select {symbol}: {mt5.last_error()}")
    return symbol


def symbol_metadata(symbol: str) -> dict[str, object]:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise MT5Error(f"Cannot read symbol metadata for {symbol}")
    return {
        "name": symbol,
        "digits": int(info.digits),
        "point": float(info.point),
        "trade_tick_size": float(info.trade_tick_size),
        "trade_tick_value": float(info.trade_tick_value),
        "contract_size": float(info.trade_contract_size),
        "volume_min": float(info.volume_min),
        "volume_max": float(info.volume_max),
        "volume_step": float(info.volume_step),
        "filling_mode": int(info.filling_mode),
        "trade_mode": int(info.trade_mode),
    }


def _rates_to_frame(rates) -> pd.DataFrame:
    if rates is None or len(rates) == 0:
        return pd.DataFrame()
    frame = pd.DataFrame(rates)
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    keep = [
        "time",
        "open",
        "high",
        "low",
        "close",
        "tick_volume",
        "spread",
        "real_volume",
    ]
    frame = frame[keep].sort_values("time").drop_duplicates("time")
    numeric = [column for column in keep if column != "time"]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors="coerce")
    return frame.dropna(subset=["open", "high", "low", "close"])


def fetch_m1(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, end)
    frame = _rates_to_frame(rates)
    if frame.empty:
        raise MT5Error(
            f"No M1 history returned for {symbol}: {mt5.last_error()}"
        )
    return frame


def load_or_fetch_m1(
    symbol: str,
    start: datetime,
    end: datetime,
    cache_dir: Path,
    refresh: bool = True,
) -> pd.DataFrame:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", symbol)
    path = cache_dir / f"{safe}_M1.csv"
    cached = pd.DataFrame()
    if path.exists():
        cached = pd.read_csv(path, parse_dates=["time"])
        cached["time"] = pd.to_datetime(cached["time"], utc=True)
    need_fetch = refresh or cached.empty
    if not cached.empty:
        first = cached["time"].min().to_pydatetime()
        last = cached["time"].max().to_pydatetime()
        need_fetch = need_fetch or first > start or last < end
    if need_fetch:
        fresh = fetch_m1(symbol, start, end)
        frame = pd.concat([cached, fresh], ignore_index=True)
    else:
        frame = cached
    frame = frame.sort_values("time").drop_duplicates("time")
    frame.to_csv(path, index=False)
    mask = (frame["time"] >= pd.Timestamp(start)) & (
        frame["time"] <= pd.Timestamp(end)
    )
    return frame.loc[mask].reset_index(drop=True)


def volume_for_cash_risk(
    symbol: str,
    entry: float,
    stop: float,
    risk_cash: float,
) -> float:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise MT5Error(f"Cannot read {symbol} for risk sizing")
    one_lot = mt5.order_calc_profit(
        mt5.ORDER_TYPE_SELL, symbol, 1.0, entry, stop
    )
    if one_lot is None or one_lot == 0:
        tick_size = float(info.trade_tick_size or info.point)
        tick_value = float(info.trade_tick_value)
        if tick_size <= 0 or tick_value <= 0:
            raise MT5Error(f"Cannot calculate risk value for {symbol}")
        one_lot = -abs(stop - entry) / tick_size * tick_value
    raw = risk_cash / abs(float(one_lot))
    step = float(info.volume_step or 0.01)
    volume = math.floor(raw / step + 1e-9) * step
    volume = max(float(info.volume_min), min(float(info.volume_max), volume))
    decimals = max(0, len(f"{step:.10f}".rstrip("0").split(".")[-1]))
    return round(volume, decimals)


def normalized_price(symbol: str, value: float) -> float:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise MT5Error(f"Cannot normalize price for {symbol}")
    tick = float(info.trade_tick_size or info.point)
    ticks = round(value / tick)
    return round(ticks * tick, int(info.digits))


def send_sell_order(
    *,
    symbol: str,
    kind: str,
    volume: float,
    entry: float,
    stop: float,
    target: float | None,
    magic: int,
    comment: str,
):
    type_map = {
        "MARKET": mt5.ORDER_TYPE_SELL,
        "SELL_LIMIT": mt5.ORDER_TYPE_SELL_LIMIT,
        "SELL_STOP": mt5.ORDER_TYPE_SELL_STOP,
    }
    order_type = type_map[kind]
    action = (
        mt5.TRADE_ACTION_DEAL
        if kind == "MARKET"
        else mt5.TRADE_ACTION_PENDING
    )
    tick = mt5.symbol_info_tick(symbol)
    price = float(tick.bid) if kind == "MARKET" else entry
    base = {
        "action": action,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": normalized_price(symbol, price),
        "sl": normalized_price(symbol, stop),
        "tp": normalized_price(symbol, target) if target is not None else 0.0,
        "deviation": 30,
        "magic": magic,
        "comment": comment[:31],
        "type_time": mt5.ORDER_TIME_GTC,
    }
    modes = (
        mt5.ORDER_FILLING_IOC,
        mt5.ORDER_FILLING_FOK,
        mt5.ORDER_FILLING_RETURN,
    )
    last = None
    for mode in modes:
        request = {**base, "type_filling": mode}
        check = mt5.order_check(request)
        if check is None or check.retcode not in {
            mt5.TRADE_RETCODE_DONE,
            0,
        }:
            last = check
            continue
        result = mt5.order_send(request)
        if result is not None and result.retcode in {
            mt5.TRADE_RETCODE_DONE,
            mt5.TRADE_RETCODE_PLACED,
        }:
            return result
        last = result
    raise MT5Error(f"Order rejected for {symbol}: {last}")


def strategy_orders(symbol: str, magic: int):
    return tuple(
        item
        for item in (mt5.orders_get(symbol=symbol) or ())
        if int(item.magic) == magic
    )


def strategy_positions(symbol: str, magic: int):
    return tuple(
        item
        for item in (mt5.positions_get(symbol=symbol) or ())
        if int(item.magic) == magic
    )


def cancel_order(ticket: int) -> None:
    result = mt5.order_send(
        {"action": mt5.TRADE_ACTION_REMOVE, "order": int(ticket)}
    )
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        raise MT5Error(f"Failed to cancel order {ticket}: {result}")


def modify_position_stop(
    symbol: str, ticket: int, stop: float, target: float
) -> None:
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": symbol,
        "position": int(ticket),
        "sl": normalized_price(symbol, stop),
        "tp": normalized_price(symbol, target) if target else 0.0,
    }
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        raise MT5Error(f"Failed to modify position {ticket}: {result}")


def close_position(symbol: str, position, comment: str) -> None:
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise MT5Error(f"No tick available to close {symbol}")
    base = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "position": int(position.ticket),
        "volume": float(position.volume),
        "type": mt5.ORDER_TYPE_BUY,
        "price": float(tick.ask),
        "deviation": 30,
        "magic": int(position.magic),
        "comment": comment[:31],
        "type_time": mt5.ORDER_TIME_GTC,
    }
    last = None
    for mode in (
        mt5.ORDER_FILLING_IOC,
        mt5.ORDER_FILLING_FOK,
        mt5.ORDER_FILLING_RETURN,
    ):
        result = mt5.order_send({**base, "type_filling": mode})
        if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
            return
        last = result
    raise MT5Error(f"Failed to close position {position.ticket}: {last}")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
