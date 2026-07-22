from __future__ import annotations

import argparse
import json
import math
import os
import time
from dataclasses import dataclass, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import MetaTrader5 as mt5


ROOT = Path(__file__).resolve().parent
TERMINAL_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"


@dataclass
class BotConfig:
    symbol: str = "XAUUSDm"
    news_timezone: str = "America/New_York"
    buffer_points: float = 2.0
    sl_extra_points: float = 2.0
    tp_r: float | None = 3.0
    be_at_r: float | None = 1.0
    fixed_volume: float | None = None
    trail_start_r: float | None = None
    trail_distance_r: float = 1.0
    trigger_window_minutes: int = 3
    max_hold_minutes: int = 60
    max_setup_range_points: float = 12.0
    max_spread_points: float = 4.0
    risk_usd: float = 10.0
    close_on_max_hold: bool = True
    magic: int = 8302026
    dry_run: bool = True


def load_config(path: Path) -> BotConfig:
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
    else:
        raw = {}
    raw.update(load_env_overrides(ROOT / ".env"))
    allowed = set(BotConfig.__dataclass_fields__)
    return BotConfig(**{k: v for k, v in raw.items() if k in allowed})


def parse_env_value(value: str):
    clean = value.strip().strip('"').strip("'")
    if clean.lower() in {"none", "null", ""}:
        return None
    if clean.lower() in {"true", "yes", "on"}:
        return True
    if clean.lower() in {"false", "no", "off"}:
        return False
    try:
        if "." in clean:
            return float(clean)
        return int(clean)
    except ValueError:
        return clean


def load_env_overrides(path: Path) -> dict:
    if not path.exists():
        return {}

    aliases = {
        field.name.upper(): field.name
        for field in fields(BotConfig)
    }
    aliases.update({
        "ENTRY_BUFFER": "buffer_points",
        "BUFFER": "buffer_points",
        "SL_ROOM": "sl_extra_points",
        "STOP_ROOM": "sl_extra_points",
        "FIXED_LOT": "fixed_volume",
        "LOT": "fixed_volume",
        "TRAIL_START": "trail_start_r",
        "TRAIL_DISTANCE": "trail_distance_r",
        "MAX_HOLD": "max_hold_minutes",
        "MAX_SETUP_RANGE": "max_setup_range_points",
        "MAX_SPREAD": "max_spread_points",
        "NEWS_TZ": "news_timezone",
        "TIMEZONE": "news_timezone",
    })

    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        config_key = aliases.get(key.strip().upper())
        if config_key:
            values[config_key] = parse_env_value(value)
            os.environ[key.strip()] = value.strip()
    return values


def get_timezone(name: str):
    if name.upper() == "UTC":
        return timezone.utc
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError(
            f"Timezone '{name}' is not available. Use UTC or install tzdata: python -m pip install tzdata"
        ) from exc


def parse_news_time(value: str, timezone_name: str) -> datetime:
    # Expected local news time, e.g. "2026-07-15 08:30" for New York.
    dt = datetime.strptime(value, "%Y-%m-%d %H:%M")
    local_dt = dt.replace(tzinfo=get_timezone(timezone_name))
    return local_dt.astimezone(timezone.utc)


def wait_until_setup_ready(news_time: datetime, execute: bool) -> None:
    setup_ready_at = news_time - timedelta(minutes=1) + timedelta(seconds=2)
    now = datetime.now(timezone.utc)
    if now >= setup_ready_at:
        return

    wait_seconds = int((setup_ready_at - now).total_seconds())
    mode = "execute" if execute else "dry-run"
    print(f"Watching news in {mode} mode.")
    print(f"Waiting until setup candle is closed: {setup_ready_at.isoformat()} UTC")
    print(f"Approx wait: {wait_seconds} seconds")

    while datetime.now(timezone.utc) < setup_ready_at:
        remaining = int((setup_ready_at - datetime.now(timezone.utc)).total_seconds())
        if remaining <= 0:
            break
        if remaining % 60 == 0 or remaining <= 10:
            print(f"Waiting... {remaining}s")
        time.sleep(min(10, max(1, remaining)))


def connect() -> None:
    if not mt5.initialize(path=TERMINAL_PATH):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")


def get_last_closed_m1(symbol: str, news_time: datetime):
    setup_start = news_time - timedelta(minutes=2)
    setup_end = news_time - timedelta(minutes=1)
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, setup_start, setup_end)
    if rates is None or len(rates) == 0:
        raise RuntimeError("Could not read last closed M1 setup candle.")
    return rates[-1]


def current_spread_points(symbol: str) -> float:
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"No tick for {symbol}")
    return abs(tick.ask - tick.bid)


def calc_volume_for_risk(symbol: str, side: str, entry: float, sl: float, risk_usd: float) -> float:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"No symbol info for {symbol}")
    order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
    min_vol = info.volume_min
    max_vol = info.volume_max
    step = info.volume_step

    def loss_for(vol: float) -> float:
        profit = mt5.order_calc_profit(order_type, symbol, vol, entry, sl)
        if profit is None:
            return float("inf")
        return abs(float(profit))

    lo, hi = min_vol, max_vol
    for _ in range(40):
        mid = (lo + hi) / 2
        if loss_for(mid) > risk_usd:
            hi = mid
        else:
            lo = mid
    vol = math.floor(lo / step) * step
    return max(min_vol, round(vol, 2))


def normalize_volume(symbol: str, volume: float) -> float:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"No symbol info for {symbol}")
    stepped = math.floor(volume / info.volume_step) * info.volume_step
    stepped = min(max(stepped, info.volume_min), info.volume_max)
    return round(stepped, 2)


def calc_order_volume(symbol: str, side: str, entry: float, sl: float, config: BotConfig) -> float:
    if config.fixed_volume is not None:
        return normalize_volume(symbol, config.fixed_volume)
    return calc_volume_for_risk(symbol, side, entry, sl, config.risk_usd)


def send_pending(symbol: str, side: str, volume: float, entry: float, sl: float, tp: float, config: BotConfig, execute: bool):
    order_type = mt5.ORDER_TYPE_BUY_STOP if side == "buy" else mt5.ORDER_TYPE_SELL_STOP
    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": entry,
        "sl": sl,
        "deviation": 30,
        "magic": config.magic,
        "comment": f"NEWS_STRADDLE_{side.upper()}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }
    if tp and tp > 0:
        request["tp"] = tp
    check = mt5.order_check(request)
    if check is None:
        raise RuntimeError(f"order_check failed: {mt5.last_error()}")
    if not execute:
        print("[DRY RUN]", request, "check=", check)
        return None
    result = mt5.order_send(request)
    print("[SENT]", side, result)
    return result


def cancel_order(ticket: int) -> None:
    mt5.order_send({"action": mt5.TRADE_ACTION_REMOVE, "order": ticket})


def modify_position_sl_tp(position, sl: float, tp: float | None) -> None:
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": position.ticket,
        "symbol": position.symbol,
        "sl": sl,
        "tp": tp if tp and tp > 0 else 0.0,
        "magic": position.magic,
        "comment": "NEWS_STRADDLE_TRAIL",
    }
    result = mt5.order_send(request)
    print("[TRAIL UPDATE]", result)


def close_position(position) -> None:
    tick = mt5.symbol_info_tick(position.symbol)
    if tick is None:
        print("Could not close: no tick.")
        return
    is_buy = position.type == mt5.POSITION_TYPE_BUY
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": position.ticket,
        "symbol": position.symbol,
        "volume": position.volume,
        "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
        "price": tick.bid if is_buy else tick.ask,
        "deviation": 50,
        "magic": position.magic,
        "comment": "NEWS_STRADDLE_MAX_HOLD_CLOSE",
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    print("[MAX HOLD CLOSE]", result)


def manage_triggered_position(symbol: str, config: BotConfig, news_time: datetime) -> None:
    if config.trail_start_r is None and not config.close_on_max_hold:
        return

    manage_until = news_time + timedelta(minutes=config.max_hold_minutes)
    best_r = 0.0
    last_sl_update = 0.0
    original_risk: float | None = None

    while datetime.now(timezone.utc) < manage_until:
        positions = [p for p in (mt5.positions_get(symbol=symbol) or []) if p.magic == config.magic]
        if not positions:
            print("No active news position to manage.")
            return
        position = positions[0]
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            time.sleep(1)
            continue

        is_buy = position.type == mt5.POSITION_TYPE_BUY
        entry = float(position.price_open)
        current_sl = float(position.sl)
        if current_sl <= 0:
            print("Position has no SL; trailing disabled for safety.")
            return

        if original_risk is None:
            original_risk = abs(entry - current_sl)
        if original_risk <= 0:
            print("Bad risk distance; trailing disabled.")
            return

        close_price = float(tick.bid if is_buy else tick.ask)
        current_r = (close_price - entry) / original_risk if is_buy else (entry - close_price) / original_risk
        best_r = max(best_r, current_r)

        if config.trail_start_r is not None and best_r >= config.trail_start_r:
            if is_buy:
                desired_sl = max(entry, close_price - config.trail_distance_r * original_risk)
                should_update = desired_sl > current_sl and abs(desired_sl - last_sl_update) >= 0.5
            else:
                desired_sl = min(entry, close_price + config.trail_distance_r * original_risk)
                should_update = desired_sl < current_sl and abs(desired_sl - last_sl_update) >= 0.5
            if should_update:
                modify_position_sl_tp(position, round(desired_sl, 3), position.tp)
                last_sl_update = desired_sl

        time.sleep(2)

    positions = [p for p in (mt5.positions_get(symbol=symbol) or []) if p.magic == config.magic]
    if positions and config.close_on_max_hold:
        close_position(positions[0])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--news-time", required=True, help='News time in configured timezone, e.g. "2026-07-15 08:30" for New York')
    parser.add_argument("--timezone", default=None, help='Timezone for --news-time. Default from .env: America/New_York')
    parser.add_argument("--no-wait", action="store_true", help="Do not wait for the setup candle; try immediately.")
    parser.add_argument("--config", default=str(ROOT / "config.best.json"))
    parser.add_argument("--risk-usd", type=float, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    if args.risk_usd is not None:
        config.risk_usd = args.risk_usd
    if args.timezone:
        config.news_timezone = args.timezone
    execute = bool(args.execute and not args.dry_run)

    connect()
    symbol = config.symbol
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"Could not select {symbol}")

    news_time = parse_news_time(args.news_time, config.news_timezone)
    print(f"Input news time: {args.news_time} ({config.news_timezone})")
    print(f"Converted UTC: {news_time.isoformat()}")

    if not args.no_wait:
        wait_until_setup_ready(news_time, execute)

    spread = current_spread_points(symbol)
    if spread > config.max_spread_points:
        print(f"NO TRADE: spread too wide ({spread:.2f} > {config.max_spread_points:.2f})")
        return

    candle = get_last_closed_m1(symbol, news_time)
    high = float(candle["high"])
    low = float(candle["low"])
    rng = high - low
    if rng > config.max_setup_range_points:
        print(f"NO TRADE: setup candle too large ({rng:.2f} > {config.max_setup_range_points:.2f})")
        return

    buy_entry = high + config.buffer_points
    sell_entry = low - config.buffer_points
    buy_sl = low - config.sl_extra_points
    sell_sl = high + config.sl_extra_points
    buy_risk = buy_entry - buy_sl
    sell_risk = sell_sl - sell_entry
    buy_tp = buy_entry + config.tp_r * buy_risk if config.tp_r and config.tp_r > 0 else 0.0
    sell_tp = sell_entry - config.tp_r * sell_risk if config.tp_r and config.tp_r > 0 else 0.0

    buy_vol = calc_order_volume(symbol, "buy", buy_entry, buy_sl, config)
    sell_vol = calc_order_volume(symbol, "sell", sell_entry, sell_sl, config)

    print("NEWS STRADDLE SETUP")
    print(f"symbol={symbol} news_utc={news_time.isoformat()} execute={execute}")
    print(f"setup_m1 high={high:.3f} low={low:.3f} range={rng:.3f} spread={spread:.3f}")
    tp_label = "none/trailing runner" if not config.tp_r or config.tp_r <= 0 else f"{config.tp_r}R"
    print(f"runner tp={tp_label} trail_start={config.trail_start_r}R trail_distance={config.trail_distance_r}R max_hold={config.max_hold_minutes}m")
    print(f"BUY STOP {buy_entry:.3f} SL {buy_sl:.3f} TP {buy_tp if buy_tp else 'none'} vol {buy_vol}")
    print(f"SELL STOP {sell_entry:.3f} SL {sell_sl:.3f} TP {sell_tp if sell_tp else 'none'} vol {sell_vol}")

    buy_result = send_pending(symbol, "buy", buy_vol, buy_entry, buy_sl, buy_tp, config, execute)
    sell_result = send_pending(symbol, "sell", sell_vol, sell_entry, sell_sl, sell_tp, config, execute)

    if not execute:
        print("Dry run complete. No orders placed.")
        return

    buy_ticket = getattr(buy_result, "order", None)
    sell_ticket = getattr(sell_result, "order", None)
    expire_at = news_time + timedelta(minutes=config.trigger_window_minutes)

    while datetime.now(timezone.utc) < expire_at:
        positions = mt5.positions_get(symbol=symbol) or []
        if positions:
            comments = {p.comment for p in positions}
            if buy_ticket and any("BUY" in c for c in comments):
                cancel_order(sell_ticket)
            if sell_ticket and any("SELL" in c for c in comments):
                cancel_order(buy_ticket)
            print("Triggered. Opposite pending cancelled.")
            manage_triggered_position(symbol, config, news_time)
            break
        time.sleep(0.5)

    for order in mt5.orders_get(symbol=symbol) or []:
        if order.magic == config.magic:
            cancel_order(order.ticket)
    print("Expired remaining news straddle pendings.")


if __name__ == "__main__":
    main()
