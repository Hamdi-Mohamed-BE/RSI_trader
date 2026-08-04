from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import time

import MetaTrader5 as mt5

from .config import LiveConfig, ROOT
from .engine import build_plan, planned_loss, prepare_features, signal_from_row
from .mt5_data import MT5Error, account_snapshot, connected, discover_xau, fetch_m5, round_price, symbol_spec


LOGGER = logging.getLogger("xau_grid.live")


def _configure_logging() -> None:
    (ROOT / "logs").mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)sZ | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(), logging.FileHandler(ROOT / "logs" / "xau-grid.log", encoding="utf-8")],
        force=True,
    )
    logging.Formatter.converter = time.gmtime


def _own_orders(symbol: str, magic: int):
    return [item for item in (mt5.orders_get(symbol=symbol) or ()) if int(item.magic) == magic]


def _own_positions(symbol: str, magic: int):
    return [item for item in (mt5.positions_get(symbol=symbol) or ()) if int(item.magic) == magic]


def _cancel_order(ticket: int) -> None:
    result = mt5.order_send({"action": mt5.TRADE_ACTION_REMOVE, "order": ticket})
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        LOGGER.error("Could not cancel order %s: %s", ticket, result)


def _cancel_stale_orders(symbol: str, config: LiveConfig, now: datetime) -> None:
    max_age = timedelta(minutes=5 * config.strategy.pending_expiry_bars)
    for order in _own_orders(symbol, config.magic):
        created = datetime.fromtimestamp(order.time_setup, tz=timezone.utc)
        if now - created >= max_age:
            LOGGER.info("Canceling expired grid leg %s", order.ticket)
            _cancel_order(order.ticket)


def _filling_modes() -> tuple[int, ...]:
    return (mt5.ORDER_FILLING_RETURN, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK)


def _send_pending(request: dict) -> object:
    last = None
    for filling in _filling_modes():
        candidate = {**request, "type_filling": filling}
        check = mt5.order_check(candidate)
        last = check
        if check is None or check.retcode not in (0, mt5.TRADE_RETCODE_DONE):
            continue
        result = mt5.order_send(candidate)
        last = result
        if result is not None and result.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
            return result
    raise MT5Error(f"Pending order rejected by all filling modes: {last}")


def _place_plan(symbol: str, config: LiveConfig, plan) -> None:
    spec = symbol_spec(symbol)
    average = sum(plan.entries) / len(plan.entries)
    if plan.mode == "momentum":
        extreme = max(plan.entries) if plan.side == 1 else min(plan.entries)
        target = extreme + plan.side * config.strategy.target_atr * plan.atr
        order_type = mt5.ORDER_TYPE_BUY_STOP if plan.side == 1 else mt5.ORDER_TYPE_SELL_STOP
    else:
        target = average + plan.side * config.strategy.target_atr * plan.atr
        order_type = mt5.ORDER_TYPE_BUY_LIMIT if plan.side == 1 else mt5.ORDER_TYPE_SELL_LIMIT
    placed: list[int] = []
    try:
        for index, entry in enumerate(plan.entries, 1):
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": plan.lot_each,
                "type": order_type,
                "price": round_price(entry, spec),
                "sl": round_price(plan.stop, spec),
                "tp": round_price(target, spec),
                "deviation": 30,
                "magic": config.magic,
                "type_time": mt5.ORDER_TIME_GTC,
                "comment": f"XAUGRID A {plan.mode[:5].upper()} L{index}",
            }
            receipt = _send_pending(request)
            placed.append(int(receipt.order))
            LOGGER.info(
                "Placed %s %s L%s | %.2f lots | entry %.2f | SL %.2f | TP %.2f",
                "BUY" if plan.side == 1 else "SELL",
                "STOP" if plan.mode == "momentum" else "LIMIT",
                index, plan.lot_each, entry, plan.stop, target,
            )
    except Exception:
        for ticket in placed:
            _cancel_order(ticket)
        raise


def _state(path: Path, balance: float) -> dict[str, object]:
    today = datetime.now(timezone.utc).date().isoformat()
    if path.exists():
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            value = {}
    else:
        value = {}
    if value.get("day") != today:
        value = {
            "day": today, "day_start_balance": balance, "peak_equity": balance,
            "last_signal": "", "basket_active": False,
        }
    value["peak_equity"] = max(float(value.get("peak_equity", balance)), balance)
    return value


def _save_state(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def _close_position(symbol: str, position, config: LiveConfig, reason: str) -> None:
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return
    side = 1 if position.type == mt5.POSITION_TYPE_BUY else -1
    request = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "position": position.ticket,
        "volume": position.volume, "type": mt5.ORDER_TYPE_SELL if side == 1 else mt5.ORDER_TYPE_BUY,
        "price": tick.bid if side == 1 else tick.ask, "deviation": 30,
        "magic": config.magic, "comment": f"XAUGRID EXIT {reason}"[:31],
    }
    for filling in _filling_modes():
        result = mt5.order_send({**request, "type_filling": filling})
        if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
            LOGGER.info("Closed position %s: %s", position.ticket, reason)
            return
    LOGGER.error("Failed to close position %s: %s", position.ticket, result)


def _manage_positions(symbol: str, config: LiveConfig, atr_value: float, now: datetime) -> None:
    spec = symbol_spec(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return
    for position in _own_positions(symbol, config.magic):
        opened = datetime.fromtimestamp(position.time, tz=timezone.utc)
        if now - opened >= timedelta(minutes=5 * config.strategy.max_hold_bars):
            _close_position(symbol, position, config, "TIME")
            continue
        side = 1 if position.type == mt5.POSITION_TYPE_BUY else -1
        market = tick.bid if side == 1 else tick.ask
        initial_risk = abs(position.price_open - position.sl) if position.sl else 0.0
        if initial_risk <= 0:
            continue
        favorable = (market - position.price_open) * side
        proposed = position.sl
        if config.strategy.be_trigger_r > 0 and favorable >= config.strategy.be_trigger_r * initial_risk:
            lock = position.price_open + side * config.strategy.be_lock_r * initial_risk
            proposed = max(proposed, lock) if side == 1 else min(proposed, lock)
        if config.strategy.trail_start_r > 0 and favorable >= config.strategy.trail_start_r * initial_risk:
            trail = market - side * config.strategy.trail_distance_atr * atr_value
            proposed = max(proposed, trail) if side == 1 else min(proposed, trail)
        proposed = round_price(proposed, spec)
        improved = proposed > position.sl + spec.tick_size if side == 1 else proposed < position.sl - spec.tick_size
        if improved:
            result = mt5.order_send({
                "action": mt5.TRADE_ACTION_SLTP, "symbol": symbol, "position": position.ticket,
                "sl": proposed, "tp": position.tp, "magic": config.magic,
            })
            if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
                LOGGER.info("Moved position %s stop to %.2f", position.ticket, proposed)
            else:
                LOGGER.error("Stop modification failed for %s: %s", position.ticket, result)


def run_live(config: LiveConfig) -> None:
    _configure_logging()
    with connected():
        symbol = discover_xau(config.canonical_symbol)
        spec = symbol_spec(symbol)
        account = account_snapshot()
        print("=" * 86)
        print("XAU SAFE GRID — LIVE BOARD")
        print(
            f"Account {account['login']} | {account['server']} | {account['currency']} | "
            f"Balance ${account['balance']:,.2f} | Equity ${account['equity']:,.2f} | 1:{account['leverage']}"
        )
        print(
            f"Symbol {symbol} | {config.strategy.mode.upper()} | {config.strategy.grid_levels} equal legs | "
            f"basket risk {config.strategy.risk_pct:.2f}% | daily stop {config.strategy.max_daily_loss_pct:.2f}%"
        )
        print(f"Execution: {'LIVE UNLOCKED' if config.unlocked else 'MONITOR ONLY (execution lock not satisfied)'}")
        print("=" * 86)
        state_path = ROOT / "runtime" / "state.json"
        last_bar = None
        while True:
            try:
                now = datetime.now(timezone.utc)
                snapshot = account_snapshot()
                state = _state(state_path, float(snapshot["balance"]))
                state["peak_equity"] = max(float(state["peak_equity"]), float(snapshot["equity"]))
                daily_loss = max(0.0, (float(state["day_start_balance"]) - float(snapshot["equity"])) / float(state["day_start_balance"]) * 100)
                equity_dd = max(0.0, (float(state["peak_equity"]) - float(snapshot["equity"])) / float(state["peak_equity"]) * 100)
                _cancel_stale_orders(symbol, config, now)
                raw = fetch_m5(symbol, now - timedelta(days=30), now)
                feature = prepare_features(raw)
                row = feature.iloc[-1]
                bar_time = feature.index[-1]
                _manage_positions(symbol, config, float(row["m15_atr"]), now)
                positions = _own_positions(symbol, config.magic)
                orders = _own_orders(symbol, config.magic)
                if positions:
                    state["basket_active"] = True
                elif bool(state.get("basket_active")):
                    LOGGER.info("Basket finished; canceling %s unfilled legs", len(orders))
                    for order in orders:
                        _cancel_order(order.ticket)
                    state["basket_active"] = False
                if bar_time != last_bar:
                    last_bar = bar_time
                    LOGGER.info(
                        "Heartbeat | %s | equity $%.2f | daily %.2f%% | peak DD %.2f%% | orders %s | positions %s",
                        bar_time, snapshot["equity"], daily_loss, equity_dd,
                        len(_own_orders(symbol, config.magic)), len(_own_positions(symbol, config.magic)),
                    )
                    side = signal_from_row(row, config.strategy)
                    signal_key = f"{bar_time}:{side}"
                    safe = (
                        daily_loss < config.strategy.max_daily_loss_pct
                        and equity_dd < config.max_equity_dd_pct
                        and (float(snapshot["margin_level"]) == 0 or float(snapshot["margin_level"]) >= config.min_margin_level_pct)
                    )
                    if side and safe and not _own_orders(symbol, config.magic) and not _own_positions(symbol, config.magic) and state.get("last_signal") != signal_key:
                        anchor = float(row["close"])
                        if config.strategy.mode == "breakout":
                            anchor = float(row["m15_break_high"] if side == 1 else row["m15_break_low"])
                        plan = build_plan(bar_time, anchor, side, float(row["m15_atr"]), float(snapshot["balance"]), config.strategy, spec)
                        state["last_signal"] = signal_key
                        if plan is None:
                            LOGGER.warning("Signal skipped: broker minimum lot would exceed the basket risk cap")
                        else:
                            LOGGER.info("Confirmed %s %s grid | planned worst loss $%.2f", config.strategy.mode, "BUY" if side == 1 else "SELL", planned_loss(plan, spec))
                            if config.unlocked:
                                _place_plan(symbol, config, plan)
                            else:
                                LOGGER.info("Monitor-only: no orders submitted")
                    elif side and not safe:
                        LOGGER.warning("Signal blocked by daily/equity/margin circuit breaker")
                _save_state(state_path, state)
            except Exception:
                LOGGER.exception("Live cycle failed")
            time.sleep(config.poll_seconds)
