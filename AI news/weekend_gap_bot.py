from __future__ import annotations

import argparse
import json
import math
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5

from backtest_weekend_gap_bot import discover_gold_symbol
from weekend_gap_strategy import find_weekend_windows


ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env.weekend-gap"
STATE_PATH = ROOT / "weekend_gap_state.json"


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    symbol_hint: str
    offset_usd: float
    placement_lead_minutes: int
    stop_usd: float
    reward_risk: float
    max_hold_market_minutes: int
    lot_mode: str
    fixed_lot: float
    risk_percent: float
    poll_seconds: float
    magic: int
    deviation_points: int
    live_trading: bool
    place_orders: bool

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            symbol_hint=os.getenv("WEEKEND_GAP_SYMBOL", "XAUUSD"),
            offset_usd=float(os.getenv("WEEKEND_GAP_OFFSET_USD", "1.5")),
            placement_lead_minutes=int(os.getenv("WEEKEND_GAP_PLACEMENT_LEAD_MINUTES", "5")),
            stop_usd=float(os.getenv("WEEKEND_GAP_STOP_USD", "20.0")),
            reward_risk=float(os.getenv("WEEKEND_GAP_REWARD_RISK", "4.0")),
            max_hold_market_minutes=int(os.getenv("WEEKEND_GAP_MAX_HOLD_MARKET_MINUTES", "720")),
            lot_mode=os.getenv("WEEKEND_GAP_LOT_MODE", "fixed").strip().lower(),
            fixed_lot=float(os.getenv("WEEKEND_GAP_FIXED_LOT", "0.01")),
            risk_percent=float(os.getenv("WEEKEND_GAP_RISK_PERCENT", "1.0")),
            poll_seconds=max(0.25, float(os.getenv("WEEKEND_GAP_POLL_SECONDS", "1"))),
            magic=int(os.getenv("WEEKEND_GAP_MAGIC", "26080231")),
            deviation_points=int(os.getenv("WEEKEND_GAP_DEVIATION_POINTS", "50")),
            live_trading=env_bool("WEEKEND_GAP_LIVE_TRADING"),
            place_orders=env_bool("WEEKEND_GAP_PLACE_ORDERS"),
        )


def initialize_mt5() -> None:
    path = os.getenv("MT5_PATH", "").strip()
    initialized = mt5.initialize(path=path) if path else mt5.initialize()
    if not initialized:
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")


def normalize_price(value: float, digits: int) -> float:
    return round(value, digits)


def normalize_lot(value: float, info) -> float:
    minimum = float(info.volume_min)
    maximum = float(info.volume_max)
    step = float(info.volume_step or minimum)
    clipped = min(maximum, max(minimum, value))
    steps = math.floor((clipped - minimum + 1e-12) / step)
    normalized = minimum + steps * step
    precision = max(0, len(f"{step:.10f}".rstrip("0").split(".")[-1]))
    return round(min(maximum, max(minimum, normalized)), precision)


def risk_lot(symbol: str, entry: float, stop: float, settings: Settings, info) -> float:
    if settings.lot_mode != "risk_percent":
        return normalize_lot(settings.fixed_lot, info)
    account = mt5.account_info()
    if account is None:
        raise RuntimeError(f"Could not read MT5 account information: {mt5.last_error()}")
    budget = float(account.balance) * settings.risk_percent / 100.0
    loss = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, symbol, 1.0, entry, stop)
    if loss is None or abs(loss) < 1e-9:
        raise RuntimeError(f"Could not calculate risk for {symbol}: {mt5.last_error()}")
    raw = budget / abs(float(loss))
    if raw < float(info.volume_min):
        raise RuntimeError(
            f"Risk-sized lot {raw:.4f} is below broker minimum {info.volume_min}; "
            "use fixed mode explicitly if accepting the excess risk."
        )
    return normalize_lot(raw, info)


def recent_rows(symbol: str, days: int = 100) -> list[dict]:
    end = datetime.now(timezone.utc)
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, end - timedelta(days=days), end)
    if rates is None or len(rates) < 1_000:
        raise RuntimeError(f"Could not load enough M1 history for {symbol}: {mt5.last_error()}")
    return [
        {
            "time": int(item["time"]),
            "open": float(item["open"]),
            "high": float(item["high"]),
            "low": float(item["low"]),
            "close": float(item["close"]),
            "spread": int(item["spread"]),
        }
        for item in rates
    ]


def infer_schedule(rows: list[dict], now: datetime) -> tuple[datetime, datetime]:
    windows = find_weekend_windows(rows)
    if not windows:
        raise RuntimeError("Could not infer the broker's Friday close and weekly reopen schedule.")
    latest = windows[-1]
    old_close_bar = datetime.fromtimestamp(rows[latest.close_index]["time"], timezone.utc)
    old_reopen = datetime.fromtimestamp(rows[latest.reopen_index]["time"], timezone.utc)
    close_weekday = old_close_bar.weekday()
    days_to_close = (close_weekday - now.weekday()) % 7
    close_date = (now + timedelta(days=days_to_close)).date()
    expected_close = datetime.combine(
        close_date,
        (old_close_bar + timedelta(minutes=1)).timetz(),
    ).astimezone(timezone.utc)
    if expected_close <= now - timedelta(minutes=1):
        expected_close += timedelta(days=7)
    reopen_days = (old_reopen.weekday() - close_weekday) % 7 or 7
    reopen_date = (expected_close + timedelta(days=reopen_days)).date()
    expected_reopen = datetime.combine(reopen_date, old_reopen.timetz()).astimezone(timezone.utc)
    return expected_close, expected_reopen


def own_orders(symbol: str, magic: int):
    return [order for order in (mt5.orders_get(symbol=symbol) or []) if int(order.magic) == magic]


def own_positions(symbol: str, magic: int):
    return [position for position in (mt5.positions_get(symbol=symbol) or []) if int(position.magic) == magic]


def cancel_order(ticket: int) -> tuple[bool, str]:
    result = mt5.order_send({"action": mt5.TRADE_ACTION_REMOVE, "order": int(ticket)})
    if result is None:
        return False, f"order_send returned None: {mt5.last_error()}"
    ok = result.retcode == mt5.TRADE_RETCODE_DONE
    return ok, f"retcode={result.retcode} {result.comment}"


def place_pending(symbol: str, side: str, entry: float, lot: float, settings: Settings, info, expiration: datetime) -> tuple[bool, str, int | None]:
    if side == "buy":
        order_type = mt5.ORDER_TYPE_BUY_STOP
        stop = entry - settings.stop_usd
        target = entry + settings.stop_usd * settings.reward_risk
    else:
        order_type = mt5.ORDER_TYPE_SELL_STOP
        stop = entry + settings.stop_usd
        target = entry - settings.stop_usd * settings.reward_risk
    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "price": normalize_price(entry, info.digits),
        "sl": normalize_price(stop, info.digits),
        "tp": normalize_price(target, info.digits),
        "deviation": settings.deviation_points,
        "magic": settings.magic,
        "comment": f"WGAP {side.upper()} S{settings.stop_usd:g} R{settings.reward_risk:g}"[:31],
        "type_time": mt5.ORDER_TIME_SPECIFIED,
        "expiration": int(expiration.timestamp()),
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }
    result = mt5.order_send(request)
    if result is not None and result.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
        return True, f"retcode={result.retcode} {result.comment}", int(result.order)
    # A few CFD brokers reject explicit expiration. Retry as GTC; the worker
    # still removes the order on the first weekly-reopen tick.
    request["type_time"] = mt5.ORDER_TIME_GTC
    request.pop("expiration", None)
    result = mt5.order_send(request)
    if result is None:
        return False, f"order_send returned None: {mt5.last_error()}", None
    ok = result.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED)
    return ok, f"retcode={result.retcode} {result.comment}", int(result.order) if ok else None


def close_position(position, settings: Settings) -> tuple[bool, str]:
    tick = mt5.symbol_info_tick(position.symbol)
    if tick is None:
        return False, f"No tick for {position.symbol}: {mt5.last_error()}"
    is_buy = position.type == mt5.POSITION_TYPE_BUY
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": position.symbol,
        "position": int(position.ticket),
        "volume": float(position.volume),
        "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
        "price": float(tick.bid if is_buy else tick.ask),
        "deviation": settings.deviation_points,
        "magic": settings.magic,
        "comment": "WGAP timed exit",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result is None:
        return False, f"close returned None: {mt5.last_error()}"
    return result.retcode == mt5.TRADE_RETCODE_DONE, f"retcode={result.retcode} {result.comment}"


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def status_line(now: datetime, symbol: str, settings: Settings, close: datetime, reopen: datetime) -> str:
    account = mt5.account_info()
    mode = "LIVE" if settings.live_trading and settings.place_orders else "DRY"
    return (
        f"[{now:%Y-%m-%d %H:%M:%S} UTC] {mode} {symbol} "
        f"account={getattr(account, 'login', '?')} orders={len(own_orders(symbol, settings.magic))} "
        f"positions={len(own_positions(symbol, settings.magic))} close={close:%a %H:%M} reopen={reopen:%a %H:%M}"
    )


def cycle(settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    symbol = discover_gold_symbol()
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"Could not select {symbol}: {mt5.last_error()}")
    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if info is None or tick is None:
        raise RuntimeError(f"No symbol info/tick for {symbol}: {mt5.last_error()}")
    rows = recent_rows(symbol)
    expected_close, expected_reopen = infer_schedule(rows, now)
    orders = own_orders(symbol, settings.magic)
    positions = own_positions(symbol, settings.magic)

    if positions and orders:
        messages = []
        for order in orders:
            ok, detail = cancel_order(order.ticket) if settings.live_trading and settings.place_orders else (True, "dry-run")
            messages.append(f"OCO cancel {order.ticket}: {ok} {detail}")
        return "; ".join(messages)

    for position in positions:
        opened = datetime.fromtimestamp(int(position.time), timezone.utc)
        position_rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, opened, now)
        completed_bars = max(0, len(position_rates) - 1) if position_rates is not None else 0
        if completed_bars >= settings.max_hold_market_minutes:
            if settings.live_trading and settings.place_orders:
                ok, detail = close_position(position, settings)
            else:
                ok, detail = True, "dry-run"
            return f"Timed exit position {position.ticket}: {ok} {detail}"

    # Recover safely after a restart: stale bot pendings older than a day are
    # removed as soon as the market provides a fresh reopening tick.
    stale_orders = [order for order in orders if now - datetime.fromtimestamp(int(order.time_setup), timezone.utc) > timedelta(hours=24)]
    if stale_orders and int(tick.time) >= int((now - timedelta(minutes=5)).timestamp()):
        messages = []
        for order in stale_orders:
            ok, detail = cancel_order(order.ticket) if settings.live_trading and settings.place_orders else (True, "dry-run")
            messages.append(f"Reopen cancel {order.ticket}: {ok} {detail}")
        return "; ".join(messages)

    placement_time = expected_close - timedelta(minutes=settings.placement_lead_minutes)
    if not (placement_time <= now < expected_close):
        return status_line(now, symbol, settings, expected_close, expected_reopen)
    if orders or positions:
        return f"Weekend idea already active: orders={len(orders)} positions={len(positions)}"

    current_week = f"{expected_close:%G-W%V}"
    state = load_state()
    if state.get("placed_week") == current_week:
        return f"Weekend {current_week} already processed; duplicate placement blocked."

    completed = [row for row in rows if int(row["time"]) + 60 <= int(tick.time)]
    if not completed:
        raise RuntimeError("No fully completed M1 candle is available.")
    reference = completed[-1]
    buy_entry = normalize_price(float(reference["high"]) + settings.offset_usd, info.digits)
    sell_entry = normalize_price(float(reference["low"]) - settings.offset_usd, info.digits)
    minimum_distance = float(info.trade_stops_level) * float(info.point)
    if buy_entry <= float(tick.ask) + minimum_distance or sell_entry >= float(tick.bid) - minimum_distance:
        raise RuntimeError(
            f"Pending prices violate broker distance: bid={tick.bid} ask={tick.ask} "
            f"buy={buy_entry} sell={sell_entry} minimum={minimum_distance}."
        )
    lot = min(
        risk_lot(symbol, buy_entry, buy_entry - settings.stop_usd, settings, info),
        risk_lot(symbol, sell_entry, sell_entry + settings.stop_usd, settings, info),
    )
    preview = (
        f"reference={datetime.fromtimestamp(reference['time'], timezone.utc):%H:%M} "
        f"H/L={reference['high']}/{reference['low']} buy_stop={buy_entry} sell_stop={sell_entry} "
        f"SL=${settings.stop_usd:g} RR={settings.reward_risk:g} lot={lot}"
    )
    if not settings.live_trading or not settings.place_orders:
        return f"DRY prepared only: {preview}"

    expiration = expected_reopen + timedelta(minutes=1)
    buy_ok, buy_detail, buy_ticket = place_pending(symbol, "buy", buy_entry, lot, settings, info, expiration)
    sell_ok, sell_detail, sell_ticket = place_pending(symbol, "sell", sell_entry, lot, settings, info, expiration)
    if buy_ok or sell_ok:
        state.update(
            {
                "placed_week": current_week,
                "placed_utc": now.isoformat(),
                "symbol": symbol,
                "buy_ticket": buy_ticket,
                "sell_ticket": sell_ticket,
                "reference": reference,
                "config": asdict(settings),
            }
        )
        save_state(state)
    if buy_ok != sell_ok:
        successful = buy_ticket if buy_ok else sell_ticket
        if successful is not None:
            cancel_order(successful)
        return f"Atomic placement failed; surviving order cancelled. BUY {buy_detail}; SELL {sell_detail}"
    return f"Placed weekend OCO pair. {preview}; BUY {buy_ticket} {buy_detail}; SELL {sell_ticket} {sell_detail}"


def main() -> None:
    parser = argparse.ArgumentParser(description="XAUUSD Friday weekend-gap straddle worker")
    parser.add_argument("--once", action="store_true", help="Run one scan cycle and stop.")
    args = parser.parse_args()
    load_env(ENV_PATH)
    settings = Settings.from_env()
    initialize_mt5()
    try:
        account = mt5.account_info()
        print("XAUUSD weekend-gap worker")
        print(f"Account: {getattr(account, 'login', '?')} / {getattr(account, 'server', '?')}")
        print(f"Mode: {'LIVE' if settings.live_trading and settings.place_orders else 'DRY'}")
        print(
            f"Offset=${settings.offset_usd:g}, lead={settings.placement_lead_minutes}m, "
            f"SL=${settings.stop_usd:g}, RR={settings.reward_risk:g}, hold={settings.max_hold_market_minutes} market minutes"
        )
        last_message = ""
        last_print = 0.0
        while True:
            try:
                message = cycle(settings)
            except Exception as exc:
                message = f"ERROR {type(exc).__name__}: {exc}"
            current = time.monotonic()
            if message != last_message or current - last_print >= 60:
                print(message, flush=True)
                last_message, last_print = message, current
            if args.once:
                break
            time.sleep(settings.poll_seconds)
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
