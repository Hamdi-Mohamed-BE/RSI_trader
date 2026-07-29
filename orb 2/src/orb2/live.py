from __future__ import annotations

from dataclasses import fields
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_DOWN
import json
import math
import signal
import time as clock

import MetaTrader5 as mt5
import pandas as pd

from .config import StrategyConfig, load_runtime
from .engine import find_day_signals, prepare_frame
from .market import fetch_m5, initialize, resolve_symbol, shutdown, symbol_info


RUNNING = True


def _stop(*_args) -> None:
    global RUNNING
    RUNNING = False


def _load_defaults(runtime) -> dict:
    path = runtime.root / "optimized_configs.json"
    if not path.exists():
        raise RuntimeError(
            "optimized_configs.json is missing. Run backtest.bat first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _strategy(raw: dict) -> StrategyConfig:
    allowed = {field.name for field in fields(StrategyConfig)}
    values = {key: value for key, value in raw.items() if key in allowed}
    values["models"] = tuple(values.get("models", ("retest",)))
    return StrategyConfig(**values)


def _load_state(runtime) -> dict:
    path = runtime.root / "state" / "live.json"
    if not path.exists():
        return {"traded": {}, "positions": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"traded": {}, "positions": {}}


def _save_state(runtime, state: dict) -> None:
    directory = runtime.root / "state"
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / "live.json.tmp"
    temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temporary.replace(directory / "live.json")


def _volume_floor(value: float, minimum: float, step: float, maximum: float) -> float:
    if value < minimum:
        return 0.0
    units = (
        Decimal(str(value)) / Decimal(str(step))
    ).to_integral_value(rounding=ROUND_DOWN)
    return float(min(maximum, units * Decimal(str(step))))


def _risk_volume(symbol: str, side: str, entry: float, stop: float, risk_cash: float, info) -> float:
    order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
    loss_one_lot = mt5.order_calc_profit(order_type, symbol, 1.0, entry, stop)
    if loss_one_lot is None or loss_one_lot >= 0:
        return 0.0
    raw = risk_cash / abs(loss_one_lot)
    return _volume_floor(raw, info.volume_min, info.volume_step, info.volume_max)


def _modify_position(position, stop: float, target: float) -> tuple[bool, str]:
    result = mt5.order_send(
        {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": position.ticket,
            "symbol": position.symbol,
            "sl": stop,
            "tp": target,
        }
    )
    if result is None:
        return False, f"no MT5 result ({mt5.last_error()})"
    return result.retcode == mt5.TRADE_RETCODE_DONE, (
        f"{result.retcode} {result.comment}"
    )


def _close_position(position, volume: float, runtime) -> tuple[bool, str]:
    tick = mt5.symbol_info_tick(position.symbol)
    if tick is None:
        return False, "no current tick"
    is_buy = position.type == mt5.POSITION_TYPE_BUY
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": position.ticket,
        "symbol": position.symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
        "price": tick.bid if is_buy else tick.ask,
        "deviation": runtime.deviation_points,
        "magic": runtime.magic,
        "comment": f"{runtime.comment} EXIT"[:31],
        "type_time": mt5.ORDER_TIME_GTC,
    }
    return _send_deal(request, position.symbol)


def _send_deal(request: dict, symbol: str) -> tuple[bool, str]:
    info = symbol_info(symbol)
    modes = []
    for mode in (
        int(info.filling_mode),
        mt5.ORDER_FILLING_IOC,
        mt5.ORDER_FILLING_FOK,
        mt5.ORDER_FILLING_RETURN,
    ):
        if mode not in modes:
            modes.append(mode)
    last = "not sent"
    for mode in modes:
        candidate = {**request, "type_filling": mode}
        result = mt5.order_send(candidate)
        if result is None:
            return False, f"no MT5 result ({mt5.last_error()})"
        last = f"{result.retcode} {result.comment}"
        if result.retcode in (
            mt5.TRADE_RETCODE_DONE,
            mt5.TRADE_RETCODE_PLACED,
            mt5.TRADE_RETCODE_DONE_PARTIAL,
        ):
            ticket = int(result.order or result.deal)
            return True, f"ticket={ticket} {last}"
        if result.retcode != mt5.TRADE_RETCODE_INVALID_FILL:
            break
    return False, last


def _losses_today(runtime, now: datetime) -> int:
    start = datetime.combine(now.date(), time.min, tzinfo=runtime.timezone)
    deals = mt5.history_deals_get(start.astimezone(timezone.utc), now.astimezone(timezone.utc))
    losses = 0
    for deal in deals or ():
        if deal.magic != runtime.magic or deal.entry != mt5.DEAL_ENTRY_OUT:
            continue
        net = (
            deal.profit
            + deal.commission
            + deal.swap
            + getattr(deal, "fee", 0.0)
        )
        if net < 0:
            losses += 1
    return losses


def _today_context(frame: pd.DataFrame, runtime, today: date):
    prepared = prepare_frame(frame).tz_convert(runtime.timezone)
    grouped = {
        item: day for item, day in prepared.groupby(prepared.index.date, sort=True)
    }
    day = grouped.get(today)
    if day is None:
        return None, None
    keys = sorted(grouped)
    previous = None
    position = keys.index(today)
    if position:
        previous_day = grouped[keys[position - 1]]
        previous_start = pd.Timestamp(
            datetime.combine(keys[position - 1], runtime.range_start),
            tz=runtime.timezone,
        )
        previous_end = pd.Timestamp(
            datetime.combine(keys[position - 1], runtime.flat_time),
            tz=runtime.timezone,
        )
        cash = previous_day[
            (previous_day.index >= previous_start)
            & (previous_day.index <= previous_end)
        ]
        if not cash.empty:
            previous = (float(cash.high.max()), float(cash.low.min()))
    return day, previous


def _manage(runtime, defaults: dict, state: dict, now: datetime) -> None:
    for position in mt5.positions_get() or ():
        if position.magic != runtime.magic:
            continue
        ticket = str(position.ticket)
        saved = state["positions"].get(ticket)
        if not saved:
            risk = abs(position.price_open - position.sl)
            if risk <= 0:
                continue
            saved = {
                "entry": position.price_open,
                "initial_stop": position.sl,
                "target": position.tp,
                "be_done": False,
                "partial_done": False,
                "partial_at_r": 2.0,
                "partial_fraction": 0.0,
            }
            state["positions"][ticket] = saved
        entry = float(saved["entry"])
        initial_stop = float(saved["initial_stop"])
        risk = abs(entry - initial_stop)
        if risk <= 0:
            continue
        tick = mt5.symbol_info_tick(position.symbol)
        if tick is None:
            continue
        is_buy = position.type == mt5.POSITION_TYPE_BUY
        price = tick.bid if is_buy else tick.ask
        r_now = (price - entry) / risk if is_buy else (entry - price) / risk
        if now.time() >= runtime.flat_time:
            ok, detail = _close_position(position, position.volume, runtime)
            print(f"FLAT {position.symbol} #{position.ticket}: {ok} {detail}", flush=True)
            continue
        if r_now >= 1.0 and not saved.get("be_done"):
            ok, detail = _modify_position(position, entry, position.tp)
            print(f"BE {position.symbol} #{position.ticket}: {ok} {detail}", flush=True)
            if ok:
                saved["be_done"] = True
        fraction = float(saved.get("partial_fraction", 0.0))
        if (
            fraction > 0
            and r_now >= float(saved.get("partial_at_r", 2.0))
            and not saved.get("partial_done")
        ):
            info = symbol_info(position.symbol)
            close_volume = _volume_floor(
                position.volume * fraction,
                info.volume_min,
                info.volume_step,
                info.volume_max,
            )
            if close_volume and position.volume - close_volume >= info.volume_min:
                ok, detail = _close_position(position, close_volume, runtime)
                print(
                    f"PARTIAL {position.symbol} #{position.ticket}: {ok} {detail}",
                    flush=True,
                )
                if ok:
                    saved["partial_done"] = True
    live_tickets = {
        str(item.ticket)
        for item in mt5.positions_get() or ()
        if item.magic == runtime.magic
    }
    state["positions"] = {
        ticket: value
        for ticket, value in state["positions"].items()
        if ticket in live_tickets
    }


def _scan(runtime, defaults: dict, state: dict, now: datetime) -> None:
    if now.weekday() >= 5 or now.time() > runtime.last_entry:
        return
    if _losses_today(runtime, now) >= runtime.max_daily_losses:
        print("ENTRY BLOCK: daily loss limit reached.", flush=True)
        return
    start = now.astimezone(timezone.utc) - timedelta(days=12)
    end = now.astimezone(timezone.utc)
    for requested, selection in defaults.items():
        if not selection.get("enabled"):
            continue
        trade_key = f"{now.date().isoformat()}:{requested}"
        if trade_key in state["traded"]:
            continue
        broker_symbol = resolve_symbol(requested)
        if any(
            item.magic == runtime.magic
            for item in mt5.positions_get(symbol=broker_symbol) or ()
        ):
            continue
        frame = fetch_m5(runtime, broker_symbol, start, end)
        day, previous = _today_context(frame, runtime, now.date())
        if day is None:
            continue
        config = _strategy(selection["config"])
        signals, reason = find_day_signals(
            broker_symbol, day, now.date(), previous, runtime, config
        )
        fresh = [
            item
            for item in signals
            if now - timedelta(minutes=10)
            <= datetime.fromisoformat(item.signal_time)
            <= now
        ]
        if not fresh:
            print(f"SCAN {requested}: {reason}, no fresh setup.", flush=True)
            continue
        setup = fresh[0]
        tick = mt5.symbol_info_tick(broker_symbol)
        info = symbol_info(broker_symbol)
        if tick is None:
            print(f"BLOCK {requested}: no tick.", flush=True)
            continue
        entry = tick.ask if setup.direction == "buy" else tick.bid
        stop = setup.stop_reference
        risk = entry - stop if setup.direction == "buy" else stop - entry
        if risk <= info.point:
            print(f"BLOCK {requested}: invalid structural stop.", flush=True)
            continue
        fixed_target = (
            entry + config.target_rr * risk
            if setup.direction == "buy"
            else entry - config.target_rr * risk
        )
        target = setup.target_reference or fixed_target
        reward = target - entry if setup.direction == "buy" else entry - target
        if reward / risk < 2.0:
            print(f"BLOCK {requested}: target below 2R.", flush=True)
            continue
        risk_cash = (mt5.account_info().balance * runtime.risk_percent / 100.0)
        risk_volume = _risk_volume(
            broker_symbol, setup.direction, entry, stop, risk_cash, info
        )
        volume = (
            min(runtime.fixed_lot, risk_volume)
            if runtime.fixed_lot > 0
            else risk_volume
        )
        volume = _volume_floor(
            volume, info.volume_min, info.volume_step, info.volume_max
        )
        if volume <= 0:
            print(
                f"BLOCK {requested}: broker minimum lot exceeds ${risk_cash:.2f} risk cap.",
                flush=True,
            )
            continue
        print(
            f"SETUP {requested} {setup.model} {setup.direction.upper()} "
            f"entry={entry:.{info.digits}f} sl={stop:.{info.digits}f} "
            f"tp={target:.{info.digits}f} lot={volume:g}",
            flush=True,
        )
        if not (runtime.live_trading and runtime.place_trades):
            print("DRY RUN: live switches are disabled.", flush=True)
            continue
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": broker_symbol,
            "volume": volume,
            "type": (
                mt5.ORDER_TYPE_BUY
                if setup.direction == "buy"
                else mt5.ORDER_TYPE_SELL
            ),
            "price": entry,
            "sl": round(stop, info.digits),
            "tp": round(target, info.digits),
            "deviation": runtime.deviation_points,
            "magic": runtime.magic,
            "comment": f"{runtime.comment} {setup.model}"[:31],
            "type_time": mt5.ORDER_TIME_GTC,
        }
        ok, detail = _send_deal(request, broker_symbol)
        print(f"ORDER {requested}: {ok} {detail}", flush=True)
        if ok:
            state["traded"][trade_key] = detail
            positions = [
                item
                for item in mt5.positions_get(symbol=broker_symbol) or ()
                if item.magic == runtime.magic
            ]
            if positions:
                opened = max(positions, key=lambda item: item.time_msc)
                state["positions"][str(opened.ticket)] = {
                    "entry": opened.price_open,
                    "initial_stop": stop,
                    "target": target,
                    "be_done": False,
                    "partial_done": False,
                    "partial_at_r": config.partial_at_r,
                    "partial_fraction": config.partial_fraction,
                }


def main() -> None:
    runtime = load_runtime()
    defaults = _load_defaults(runtime)
    state = _load_state(runtime)
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    print(
        f"ORB2 live worker | symbols={','.join(runtime.symbols)} | "
        f"risk={runtime.risk_percent:g}% | fixed_lot={runtime.fixed_lot:g} | "
        f"live={runtime.live_trading and runtime.place_trades}",
        flush=True,
    )
    initialize(runtime)
    try:
        while RUNNING:
            started = clock.perf_counter()
            now = datetime.now(runtime.timezone)
            try:
                _manage(runtime, defaults, state, now)
                _scan(runtime, defaults, state, now)
                _save_state(runtime, state)
            except Exception as exc:
                print(f"ERROR: {type(exc).__name__}: {exc}", flush=True)
            elapsed = clock.perf_counter() - started
            print(
                f"CYCLE {now.isoformat(timespec='seconds')} {elapsed:.2f}s",
                flush=True,
            )
            clock.sleep(runtime.poll_seconds)
    finally:
        _save_state(runtime, state)
        shutdown()


if __name__ == "__main__":
    main()
