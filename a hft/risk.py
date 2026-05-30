"""Convert USD risk/reward targets into broker SL/TP price levels."""

from __future__ import annotations

import MetaTrader5 as mt5

import config as cfg


def tp_sl_usd(symbol: str) -> tuple[float, float]:
    """Return (take_profit_usd, stop_loss_usd) for a symbol."""
    if symbol in cfg.SYMBOL_TP_SL_USD:
        tp, sl = cfg.SYMBOL_TP_SL_USD[symbol]
        return float(tp), float(sl)
    return cfg.TAKE_PROFIT_USD, cfg.STOP_LOSS_USD


def _normalize_price(symbol: str, price: float) -> float:
    info = mt5.symbol_info(symbol)
    if info is None:
        return price
    return round(price, info.digits)


def _price_for_usd(
    symbol: str,
    order_type: int,
    volume: float,
    entry: float,
    target_usd: float,
) -> float | None:
    """Find exit price where order_calc_profit ~= |target_usd|."""
    if target_usd == 0:
        return None

    info = mt5.symbol_info(symbol)
    if info is None:
        return None

    step = info.trade_tick_size or info.point or 0.01
    is_buy = order_type == mt5.ORDER_TYPE_BUY
    want_profit = target_usd
    direction = 1 if (is_buy and want_profit > 0) or (not is_buy and want_profit < 0) else -1
    goal = abs(want_profit)

    price = entry
    for _ in range(250_000):
        price += direction * step
        profit = mt5.order_calc_profit(order_type, symbol, volume, entry, price)
        if profit is None:
            return None
        if want_profit > 0 and profit >= goal - 0.05:
            return _normalize_price(symbol, price)
        if want_profit < 0 and profit <= -goal + 0.05:
            return _normalize_price(symbol, price)

    return None


def calc_sl_tp(
    symbol: str,
    side: str,
    entry: float,
    volume: float,
) -> tuple[float | None, float | None, float, float]:
    """
    Return (sl_price, tp_price, tp_usd, sl_usd).
    SL/TP prices are None if calculation fails.
    """
    tp_usd, sl_usd = tp_sl_usd(symbol)
    is_buy = side.upper() == "BUY"
    order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL

    tp_price = _price_for_usd(symbol, order_type, volume, entry, tp_usd)
    sl_price = _price_for_usd(symbol, order_type, volume, entry, -sl_usd)

    return sl_price, tp_price, tp_usd, sl_usd


def format_sl_tp(symbol: str, side: str, entry: float, volume: float) -> str:
    sl, tp, tp_usd, sl_usd = calc_sl_tp(symbol, side, entry, volume)
    if sl is None or tp is None:
        return f"TP=${tp_usd:.0f} SL=${sl_usd:.0f} (prices n/a)"
    return f"TP={tp} (~${tp_usd:.0f}) SL={sl} (~-${sl_usd:.0f})"
