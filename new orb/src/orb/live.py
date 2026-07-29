from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import time

import MetaTrader5 as mt5

from .config import Config, load_config
from .mt5 import (
    MT5Error,
    account_info,
    initialize,
    rates,
    resolve_symbol,
    shutdown,
    symbol_info,
)
from .strategy import analyze_day, atr, load_news_blackouts


def _normalize_volume(value: float, info) -> float:
    value = min(max(value, info.volume_min), info.volume_max)
    steps = math.floor((value - info.volume_min + 1e-12) / info.volume_step)
    normalized = info.volume_min + steps * info.volume_step
    digits = max(0, len(str(info.volume_step).split(".")[-1].rstrip("0")))
    return round(normalized, digits)


def _risk_volume(config: Config, symbol: str, entry: float, stop: float, info) -> float:
    if config.fixed_lot > 0:
        return _normalize_volume(config.fixed_lot, info)
    account = account_info()
    risk_cash = account.equity * config.risk_percent / 100.0
    one_lot_loss = abs(
        mt5.order_calc_profit(
            mt5.ORDER_TYPE_BUY if entry > stop else mt5.ORDER_TYPE_SELL,
            symbol,
            1.0,
            entry,
            stop,
        )
        or 0.0
    )
    if one_lot_loss <= 0:
        raise MT5Error("Could not calculate one-lot stop-loss risk.")
    raw_volume = risk_cash / one_lot_loss
    if raw_volume < info.volume_min:
        minimum_risk = one_lot_loss * info.volume_min
        raise MT5Error(
            f"Broker minimum {info.volume_min:g} lot risks about "
            f"${minimum_risk:.2f}, above the ${risk_cash:.2f} risk cap."
        )
    return _normalize_volume(raw_volume, info)


def _state_path(config: Config) -> Path:
    path = config.root / "state" / "live.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_state(config: Config) -> dict:
    path = _state_path(config)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_state(config: Config, state: dict) -> None:
    _state_path(config).write_text(json.dumps(state, indent=2), encoding="utf-8")


def _existing_magic_orders(config: Config, symbol: str):
    orders = mt5.orders_get(symbol=symbol) or []
    positions = mt5.positions_get(symbol=symbol) or []
    return (
        [item for item in orders if item.magic == config.magic],
        [item for item in positions if item.magic == config.magic],
    )


def _market_order(request: dict) -> tuple[object | None, dict]:
    last = None
    for filling in (mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN):
        candidate = {**request, "type_filling": filling}
        last = mt5.order_send(candidate)
        if last is not None and last.retcode == mt5.TRADE_RETCODE_DONE:
            return last, candidate
    return last, candidate


def _close_position(config: Config, symbol: str, position, volume: float, info) -> dict:
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return {"action": "failed", "reason": "tick_unavailable_for_close"}
    is_buy = position.type == mt5.POSITION_TYPE_BUY
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "position": position.ticket,
        "volume": _normalize_volume(volume, info),
        "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
        "price": tick.bid if is_buy else tick.ask,
        "deviation": config.deviation_points,
        "magic": config.magic,
        "comment": f"{config.comment} EXIT"[:31],
    }
    result, sent = _market_order(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        return {
            "action": "failed",
            "reason": f"close:{getattr(result, 'comment', mt5.last_error())}",
            "request": sent,
        }
    return {"action": "closed", "deal": result.deal, "volume": sent["volume"]}


def _move_to_break_even(config: Config, symbol: str, position, tp2: float, info) -> dict:
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": symbol,
        "position": position.ticket,
        "sl": round(position.price_open, info.digits),
        "tp": round(tp2, info.digits),
        "magic": config.magic,
    }
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        return {
            "action": "failed",
            "reason": f"break_even:{getattr(result, 'comment', mt5.last_error())}",
        }
    return {"action": "break_even", "sl": request["sl"], "tp": request["tp"]}


def _cancel_order(config: Config, order) -> dict:
    result = mt5.order_send(
        {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": order.ticket,
            "symbol": order.symbol,
            "magic": config.magic,
            "comment": f"{config.comment} EXPIRE"[:31],
        }
    )
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        return {
            "action": "failed",
            "reason": f"cancel:{getattr(result, 'comment', mt5.last_error())}",
        }
    return {"action": "cancelled", "ticket": order.ticket}


def _manage_existing(
    config: Config,
    symbol: str,
    orders: list,
    positions: list,
    state: dict,
    info,
) -> dict:
    now_local = datetime.now(timezone.utc).astimezone(config.timezone)
    after_flat = now_local.time() >= config.flat_time
    actions: list[dict] = []

    if after_flat:
        actions.extend(_cancel_order(config, order) for order in orders)
        actions.extend(
            _close_position(config, symbol, position, position.volume, info)
            for position in positions
        )
        return {"action": "session_flat", "details": actions}

    setup = state.get("setup") or {}
    tp1 = float(setup.get("tp1") or 0.0)
    tp2 = float(setup.get("tp2") or 0.0)
    if not positions or tp1 <= 0 or tp2 <= 0:
        return {
            "action": "monitoring",
            "pending_orders": len(orders),
            "positions": len(positions),
        }

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return {"action": "failed", "reason": "tick_unavailable_for_management"}
    for position in positions:
        key = str(position.ticket)
        managed = state.setdefault("positions", {}).setdefault(key, {})
        if managed.get("tp1_managed"):
            continue
        tp1_hit = (
            tick.bid >= tp1
            if position.type == mt5.POSITION_TYPE_BUY
            else tick.ask <= tp1
        )
        if not tp1_hit:
            continue

        refreshed = position
        if not managed.get("partial_done"):
            target_close = position.volume * config.partial_fraction
            close_volume = _normalize_volume(target_close, info)
            can_partial = (
                close_volume >= info.volume_min
                and position.volume - close_volume >= info.volume_min - 1e-12
            )
            if can_partial:
                close_result = _close_position(
                    config, symbol, position, close_volume, info
                )
                actions.append(close_result)
                if close_result.get("action") != "closed":
                    continue
                managed["partial_done"] = True
                refreshed = next(
                    (
                        item
                        for item in (mt5.positions_get(symbol=symbol) or [])
                        if item.ticket == position.ticket
                    ),
                    None,
                )
            else:
                managed["partial_done"] = True
                managed["partial_skipped"] = True
                actions.append(
                    {
                        "action": "partial_skipped",
                        "reason": (
                            "position_too_small_for_broker_minimum_remaining_volume"
                        ),
                    }
                )

        if (
            refreshed is not None
            and config.move_sl_to_be
            and not managed.get("break_even_done")
        ):
            be_result = _move_to_break_even(
                config, symbol, refreshed, tp2, info
            )
            actions.append(be_result)
            managed["break_even_done"] = be_result.get("action") == "break_even"
        managed["tp1_managed"] = managed.get("partial_done", False) and (
            managed.get("break_even_done", False) or not config.move_sl_to_be
        )
    _save_state(config, state)
    return {
        "action": "managed" if actions else "monitoring",
        "pending_orders": len(orders),
        "positions": len(positions),
        "details": actions,
    }


def _send_pending(config: Config, symbol: str, setup, info) -> dict:
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise MT5Error(f"No current tick for {symbol}.")
    if setup.direction == "buy" and tick.ask >= setup.entry:
        return {"action": "missed", "reason": "price_already_above_buy_stop"}
    if setup.direction == "sell" and tick.bid <= setup.entry:
        return {"action": "missed", "reason": "price_already_below_sell_stop"}

    volume = _risk_volume(config, symbol, setup.entry, setup.stop, info)
    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY_STOP
        if setup.direction == "buy"
        else mt5.ORDER_TYPE_SELL_STOP,
        "price": round(setup.entry, info.digits),
        "sl": round(setup.stop, info.digits),
        "tp": round(setup.tp2, info.digits),
        "deviation": config.deviation_points,
        "magic": config.magic,
        "comment": config.comment,
        "type_time": mt5.ORDER_TIME_DAY,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }
    check = mt5.order_check(request)
    if check is None or check.retcode not in (0, mt5.TRADE_RETCODE_DONE):
        return {
            "action": "blocked",
            "reason": f"order_check:{getattr(check, 'comment', mt5.last_error())}",
            "request": request,
        }
    if not (config.live_trading and config.place_trades):
        return {"action": "prepared", "request": request}
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        return {
            "action": "failed",
            "reason": f"order_send:{getattr(result, 'comment', mt5.last_error())}",
            "request": request,
        }
    return {"action": "placed", "ticket": result.order, "request": request}


def run_once(config: Config) -> dict:
    initialize(config)
    try:
        symbol = resolve_symbol(config.symbol)
        info = symbol_info(symbol)
        now = datetime.now(timezone.utc)
        m5 = rates(symbol, "M5", now - timedelta(days=12), now)
        h1 = rates(symbol, "H1", now - timedelta(days=25), now)
        m5["_atr"] = atr(m5)
        local_day = now.astimezone(config.timezone).date()
        news = load_news_blackouts(config.news_blackout_csv, config.timezone)
        analysis = analyze_day(m5, h1, local_day, config, info.point, news)
        orders, positions = _existing_magic_orders(config, symbol)
        state = _load_state(config)
        if state.get("session_date") != local_day.isoformat():
            state = {"session_date": local_day.isoformat(), "trade_used": False}
            _save_state(config, state)
        if orders or positions:
            return {
                "time": now.isoformat(),
                "symbol": symbol,
                **_manage_existing(config, symbol, orders, positions, state, info),
            }
        if state.get("session_date") == local_day.isoformat() and state.get("trade_used"):
            return {
                "time": now.isoformat(),
                "symbol": symbol,
                "action": "blocked",
                "reason": "one_trade_per_session_already_used",
            }
        if analysis.setup is None:
            return {
                "time": now.isoformat(),
                "symbol": symbol,
                "action": analysis.status,
                "reason": analysis.reason,
            }
        result = _send_pending(config, symbol, analysis.setup, info)
        if result["action"] in {"placed", "prepared"}:
            state.update(
                {
                    "session_date": local_day.isoformat(),
                    "trade_used": result["action"] == "placed",
                    "setup": analysis.setup.to_dict(),
                    "ticket": result.get("ticket"),
                }
            )
            _save_state(config, state)
        return {"time": now.isoformat(), "symbol": symbol, **result}
    finally:
        shutdown()


def main() -> None:
    config = load_config()
    print(
        f"ORB bot | {config.symbol} | live={config.live_trading} "
        f"place={config.place_trades} | risk={config.risk_percent:.2f}%"
    )
    print("Press Ctrl+C to stop.")
    try:
        while True:
            started = time.perf_counter()
            try:
                result = run_once(config)
                print(json.dumps(result, default=str))
            except Exception as exc:
                print(json.dumps({"action": "error", "reason": str(exc)}))
            elapsed = time.perf_counter() - started
            time.sleep(max(config.poll_seconds - elapsed, 1.0))
    except KeyboardInterrupt:
        print("ORB bot stopped.")


if __name__ == "__main__":
    main()
