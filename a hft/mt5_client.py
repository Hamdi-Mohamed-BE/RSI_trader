"""Thin MetaTrader5 wrapper for the HFT scalper."""

from __future__ import annotations

import time
from typing import Any

import MetaTrader5 as mt5

import config as cfg
from risk import calc_sl_tp, format_sl_tp, tp_sl_usd


def log(msg: str) -> None:
    if cfg.VERBOSE:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def lot_size(symbol: str) -> float:
    return cfg.SYMBOL_LOTS.get(symbol, cfg.LOT_SIZE)


def tick_min_points(symbol: str) -> int:
    return cfg.SYMBOL_TICK_MIN_POINTS.get(symbol, cfg.TICK_MIN_MOVE_POINTS)


def initialize() -> list[str]:
    """Connect to MT5 and enable all configured symbols. Returns active symbol list."""
    kwargs: dict[str, Any] = {}
    if cfg.MT5_TERMINAL_PATH:
        kwargs["path"] = cfg.MT5_TERMINAL_PATH
    if cfg.MT5_LOGIN is not None:
        kwargs["login"] = cfg.MT5_LOGIN
    if cfg.MT5_PASSWORD is not None:
        kwargs["password"] = cfg.MT5_PASSWORD
    if cfg.MT5_SERVER is not None:
        kwargs["server"] = cfg.MT5_SERVER

    if not mt5.initialize(**kwargs):
        raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")

    account = mt5.account_info()
    terminal = mt5.terminal_info()
    active: list[str] = []

    for symbol in cfg.SYMBOLS:
        if not mt5.symbol_select(symbol, True):
            log(f"SKIP {symbol} — not available on this broker")
            continue
        info = mt5.symbol_info(symbol)
        if info is None or not info.visible:
            log(f"SKIP {symbol} — not visible")
            continue
        lot = lot_size(symbol)
        if lot < info.volume_min:
            log(f"SKIP {symbol} — lot {lot} below min {info.volume_min}")
            continue
        spread = spread_points(symbol)
        log(
            f"  + {symbol} lot={lot} min={info.volume_min} "
            f"spread={spread:.0f}pt filling={info.filling_mode}"
        )
        active.append(symbol)

    if not active:
        raise RuntimeError("No symbols from SYMBOLS list are available — check config.py")

    log(f"Connected | account={account.login} balance={account.balance:.2f} | {len(active)} symbols")

    if terminal and not terminal.trade_allowed:
        log("WARNING: Terminal trading disabled — enable Algo Trading button in MT5 toolbar")
    if account and not account.trade_allowed:
        log("WARNING: Account trade_allowed=False — check broker / account settings")

    return active


def shutdown() -> None:
    mt5.shutdown()


def spread_points(symbol: str) -> float:
    tick = mt5.symbol_info_tick(symbol)
    info = mt5.symbol_info(symbol)
    if tick is None or info is None or info.point == 0:
        return float("inf")
    return (tick.ask - tick.bid) / info.point


def effective_deviation(symbol: str) -> int:
    spread = spread_points(symbol)
    if spread == float("inf"):
        return cfg.DEVIATION_POINTS
    return max(cfg.DEVIATION_POINTS, int(spread * 1.5) + 10)


def _filling_mode(symbol: str) -> int:
    info = mt5.symbol_info(symbol)
    if info is None:
        return mt5.ORDER_FILLING_RETURN
    filling = info.filling_mode
    if filling & 2:
        return mt5.ORDER_FILLING_IOC
    if filling & 1:
        return mt5.ORDER_FILLING_FOK
    return mt5.ORDER_FILLING_RETURN


def open_market(symbol: str, side: str) -> bool:
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        log(f"{symbol} open failed: no tick ({mt5.last_error()})")
        return False

    lot = lot_size(symbol)
    is_buy = side.upper() == "BUY"
    entry = tick.ask if is_buy else tick.bid
    order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL

    sl_price, tp_price, tp_usd, sl_usd = calc_sl_tp(symbol, side, entry, lot)

    request: dict[str, Any] = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "price": entry,
        "deviation": effective_deviation(symbol),
        "magic": cfg.MAGIC_NUMBER,
        "comment": cfg.ORDER_COMMENT[:31],
        "type_filling": _filling_mode(symbol),
    }

    if cfg.PLACE_BROKER_SLTP and sl_price is not None and tp_price is not None:
        request["sl"] = sl_price
        request["tp"] = tp_price

    result = mt5.order_send(request)
    if result is None:
        log(f"{symbol} open failed: {mt5.last_error()}")
        return False

    # Retry without SL/TP if broker rejects distance/mode, then modify
    if result.retcode != mt5.TRADE_RETCODE_DONE and cfg.PLACE_BROKER_SLTP:
        if "sl" in request:
            log(f"{symbol} SL/TP rejected ({result.comment}) — retrying without, will modify")
            request.pop("sl", None)
            request.pop("tp", None)
            result = mt5.order_send(request)

    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        code = result.retcode if result else mt5.last_error()
        comment = result.comment if result else ""
        log(f"{symbol} open rejected retcode={code} comment={comment}")
        return False

    sl_tp_msg = format_sl_tp(symbol, side, result.price, lot)
    log(f"OPEN {symbol} {side} lot={lot} @ {result.price} | {sl_tp_msg}")

    if cfg.PLACE_BROKER_SLTP and sl_price and tp_price:
        _ensure_position_sltp(symbol, result.order, sl_price, tp_price)

    return True


def _ensure_position_sltp(symbol: str, order_ticket: int, sl: float, tp: float) -> None:
    """Set SL/TP on position if not attached on entry."""
    time.sleep(0.1)
    positions = mt5.positions_get(ticket=order_ticket)
    if not positions:
        positions = [p for p in (mt5.positions_get(symbol=symbol) or []) if p.magic == cfg.MAGIC_NUMBER]
    if not positions:
        return

    pos = positions[-1]
    if pos.sl and pos.tp:
        return

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": symbol,
        "position": pos.ticket,
        "sl": sl,
        "tp": tp,
    }
    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        log(f"  SL/TP set on {symbol} ticket={pos.ticket} SL={sl} TP={tp}")
    elif result:
        log(f"  SL/TP modify failed: {result.comment}")


def close_position(position) -> bool:
    symbol = position.symbol
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return False

    is_buy = position.type == mt5.POSITION_TYPE_BUY
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": position.volume,
        "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
        "position": position.ticket,
        "price": tick.bid if is_buy else tick.ask,
        "deviation": effective_deviation(symbol),
        "magic": cfg.MAGIC_NUMBER,
        "comment": "hft-close",
        "type_filling": _filling_mode(symbol),
    }

    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        code = result.retcode if result else mt5.last_error()
        log(f"{symbol} close failed ticket={position.ticket} retcode={code}")
        return False

    log(f"CLOSE {symbol} ticket={position.ticket} pnl={position.profit:.2f}")
    return True


def bot_positions(symbols: list[str] | None = None):
    positions = mt5.positions_get()
    if not positions:
        return []
    allowed = set(symbols or cfg.SYMBOLS)
    return [
        p for p in positions
        if p.magic == cfg.MAGIC_NUMBER and p.symbol in allowed
    ]


def positions_for_symbol(symbol: str):
    return [p for p in bot_positions() if p.symbol == symbol]


def free_margin() -> float:
    account = mt5.account_info()
    return account.margin_free if account else 0.0


def trading_hours_ok() -> bool:
    if cfg.TRADING_HOURS_UTC is None:
        return True
    start, end = cfg.TRADING_HOURS_UTC
    hour = time.gmtime().tm_hour
    if start <= end:
        return start <= hour < end
    return hour >= start or hour < end


def entry_block_reason(symbol: str) -> str | None:
    """Why a new entry on this symbol is blocked, or None if OK."""
    if len(bot_positions()) >= cfg.MAX_OPEN_POSITIONS:
        return f"max total positions ({cfg.MAX_OPEN_POSITIONS})"
    if len(positions_for_symbol(symbol)) >= cfg.MAX_OPEN_POSITIONS_PER_SYMBOL:
        return f"max positions on {symbol}"
    spread = spread_points(symbol)
    if spread > cfg.MAX_SPREAD_POINTS:
        return f"{symbol} spread too wide ({spread:.0f} > {cfg.MAX_SPREAD_POINTS})"
    margin = free_margin()
    if margin < cfg.MIN_FREE_MARGIN_USD:
        return f"low margin (${margin:.2f} < ${cfg.MIN_FREE_MARGIN_USD})"
    if not trading_hours_ok():
        return "outside trading hours"
    terminal = mt5.terminal_info()
    if terminal and not terminal.trade_allowed:
        return "Algo Trading OFF in MT5 — click the button in toolbar"
    account = mt5.account_info()
    if account and not account.trade_allowed:
        return "account trade_allowed=False"
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return f"{symbol} no live tick / quotes"
    return None
