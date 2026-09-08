from __future__ import annotations

import math
import re
from typing import Any

try:
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover
    mt5 = None


ALIASES = {
    "XAUUSD": ("XAUUSD", "GOLD"), "US100": ("USTEC", "US100", "NAS100", "NASDAQ"),
    "NQ": ("USTEC", "US100", "NAS100", "NASDAQ"), "GC": ("XAUUSD", "GOLD"),
}


def connect() -> bool:
    return bool(mt5 and mt5.initialize())


def account_summary() -> dict[str, Any]:
    if not connect():
        return {"connected": False, "error": "MT5 terminal is unavailable"}
    info = mt5.account_info()
    if info is None:
        return {"connected": False, "error": str(mt5.last_error())}
    return {
        "connected": True, "login": info.login, "server": info.server, "currency": info.currency,
        "balance": info.balance, "equity": info.equity, "trade_mode": info.trade_mode,
    }


def discover_symbol(canonical: str) -> str | None:
    if not connect():
        return None
    symbols = mt5.symbols_get() or []
    candidates = ALIASES.get(canonical.upper(), (canonical.upper(),))
    def score(name: str) -> tuple[int, int]:
        upper = name.upper()
        exact = 0 if upper in candidates else 1
        match = 0 if any(re.search(re.escape(alias), upper) for alias in candidates) else 1
        return exact + match, len(name)
    matches = [item.name for item in symbols if any(alias in item.name.upper() for alias in candidates)]
    return sorted(matches, key=score)[0] if matches else None


def current_price(symbol: str, side: str) -> dict[str, Any]:
    """Return a read-only executable quote for paper mirroring."""
    broker_symbol = discover_symbol(symbol)
    if not broker_symbol:
        raise ValueError(f"No broker symbol found for {symbol}")
    if not mt5.symbol_select(broker_symbol, True):
        raise ValueError(f"Could not select {broker_symbol}: {mt5.last_error()}")
    tick = mt5.symbol_info_tick(broker_symbol)
    if tick is None:
        raise ValueError(f"No live quote for {broker_symbol}: {mt5.last_error()}")
    price = tick.ask if side.lower() == "buy" else tick.bid
    return {"broker_symbol": broker_symbol, "entry": float(price)}


def size_for_risk(symbol: str, side: str, entry: float, stop_loss: float, risk_percent: float) -> dict[str, Any]:
    account = account_summary()
    if not account.get("connected"):
        raise RuntimeError(account.get("error", "MT5 unavailable"))
    broker_symbol = discover_symbol(symbol)
    if not broker_symbol:
        raise ValueError(f"No broker symbol found for {symbol}")
    info = mt5.symbol_info(broker_symbol)
    if info is None:
        raise ValueError(f"No contract details for {broker_symbol}")
    if not info.visible:
        mt5.symbol_select(broker_symbol, True)
    action = mt5.ORDER_TYPE_BUY if side.lower() == "buy" else mt5.ORDER_TYPE_SELL
    loss_one_lot = mt5.order_calc_profit(action, broker_symbol, 1.0, float(entry), float(stop_loss))
    if loss_one_lot is None or loss_one_lot == 0:
        raise ValueError(f"MT5 could not calculate risk: {mt5.last_error()}")
    risk_cash = float(account["equity"]) * risk_percent / 100.0
    raw = risk_cash / abs(loss_one_lot)
    steps = math.floor((raw + 1e-12) / info.volume_step)
    volume = round(steps * info.volume_step, 8)
    if volume < info.volume_min:
        raise ValueError(f"Minimum {info.volume_min} lot exceeds the {risk_percent:g}% risk budget")
    volume = min(volume, info.volume_max)
    actual_risk = abs(mt5.order_calc_profit(action, broker_symbol, volume, float(entry), float(stop_loss)))
    return {"broker_symbol": broker_symbol, "risk_cash": round(actual_risk, 2), "risk_budget": round(risk_cash, 2), "volume": volume}
