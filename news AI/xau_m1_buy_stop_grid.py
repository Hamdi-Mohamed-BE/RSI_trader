from __future__ import annotations

import os
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"


def now_local() -> str:
    return datetime.now().isoformat(timespec="seconds")


def log(message: str) -> None:
    print(f"[{now_local()}] {message}")


def load_env_file(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def env_bool(key: str, default: bool = False) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_float(key: str, default: float) -> float:
    value = os.getenv(key, "").strip()
    if not value:
        return default
    return float(value)


def env_lot(key: str, default: float) -> float | str:
    value = os.getenv(key, "").strip()
    if not value:
        return default
    if value.lower() == "max":
        return "max"
    return float(value)


def env_int(key: str, default: int) -> int:
    value = os.getenv(key, "").strip()
    if not value:
        return default
    return int(value)


def clean_symbol(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())


def allows_opening(symbol_info: Any) -> bool:
    trade_mode = getattr(symbol_info, "trade_mode", None)
    if isinstance(trade_mode, int):
        return trade_mode not in {0, 3}
    return True


def select_symbol(name: str) -> bool:
    return bool(mt5.symbol_select(name, True))


def discover_xau_symbol(wanted: str) -> str:
    candidates: list[tuple[int, str]] = []
    wanted_clean = clean_symbol(wanted)
    aliases = [wanted_clean, "XAUUSD", "GOLD"]

    direct = mt5.symbol_info(wanted)
    if direct and allows_opening(direct) and select_symbol(wanted):
        return wanted

    symbols = mt5.symbols_get()
    if not symbols:
        raise RuntimeError(f"MT5 returned no symbols; cannot resolve {wanted}.")

    for item in symbols:
        info = mt5.symbol_info(item.name)
        if info is not None and not allows_opening(info):
            continue
        name_clean = clean_symbol(item.name)
        score = 0
        for index, alias in enumerate(aliases):
            if name_clean == alias:
                score = max(score, 100 - index)
            elif name_clean.startswith(alias):
                score = max(score, 90 - index)
            elif alias in name_clean:
                score = max(score, 70 - index)
        if score:
            candidates.append((score, item.name))

    for _, name in sorted(candidates, reverse=True):
        if select_symbol(name):
            return name

    raise RuntimeError(f"Could not resolve broker symbol for {wanted}.")


def normalize_lot(symbol: str, lot: float) -> float:
    info = mt5.symbol_info(symbol)
    if info is None:
        return lot
    min_lot = float(info.volume_min or 0.01)
    max_lot = float(info.volume_max or lot)
    step = float(info.volume_step or 0.01)
    lot = max(min_lot, min(max_lot, lot))
    steps = math.floor((lot - min_lot) / step + 1e-9)
    normalized = min_lot + steps * step
    return round(max(min_lot, min(max_lot, normalized)), 8)


def max_allowed_lot(symbol: str, side: str, price: float) -> float:
    info = mt5.symbol_info(symbol)
    account = mt5.account_info()
    if info is None or account is None:
        raise RuntimeError(f"Cannot calculate max lot for {symbol}: missing symbol/account info.")

    min_lot = float(info.volume_min or 0.01)
    max_lot = float(info.volume_max or min_lot)
    step = float(info.volume_step or 0.01)
    free_margin = float(account.margin_free)
    if free_margin <= 0:
        raise RuntimeError("Cannot calculate max lot: account free margin is zero.")

    margin_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL

    def margin_ok(lot: float) -> bool:
        normalized = normalize_lot(symbol, lot)
        margin = mt5.order_calc_margin(margin_type, symbol, normalized, price)
        if margin is None:
            return False
        return float(margin) <= free_margin

    if margin_ok(max_lot):
        return normalize_lot(symbol, max_lot)

    if not margin_ok(min_lot):
        return normalize_lot(symbol, min_lot)

    low = min_lot
    high = max_lot
    for _ in range(40):
        mid = normalize_lot(symbol, (low + high) / 2.0)
        if mid <= low:
            break
        if margin_ok(mid):
            low = mid
        else:
            high = mid

    steps = math.floor((low - min_lot) / step + 1e-9)
    return round(min_lot + steps * step, 8)


def normalize_price(symbol: str, price: float) -> float:
    info = mt5.symbol_info(symbol)
    digits = int(info.digits if info else 2)
    return round(price, digits)


def latest_closed_m1(symbol: str) -> dict[str, float]:
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 1, 1)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"No closed M1 candle data returned for {symbol}.")
    row = rates[0]
    return {
        "time": float(row["time"]),
        "open": float(row["open"]),
        "high": float(row["high"]),
        "low": float(row["low"]),
        "close": float(row["close"]),
    }


def broker_stop_limits(symbol: str) -> tuple[float, float]:
    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if info is None or tick is None:
        raise RuntimeError(f"Missing symbol info/tick for {symbol}.")
    point = float(info.point or 0.01)
    stops_level = int(getattr(info, "trade_stops_level", 0) or 0)
    min_buy_stop = float(tick.ask) + stops_level * point
    max_sell_stop = float(tick.bid) - stops_level * point
    return min_buy_stop, max_sell_stop


def broker_time(symbol: str) -> int:
    """Return the broker server epoch used for pending-order expiration."""
    tick = mt5.symbol_info_tick(symbol)
    if tick is not None and int(getattr(tick, "time", 0) or 0) > 0:
        return int(tick.time)
    return int(time.time())


def existing_pending_prices(symbol: str, magic: int, order_type: int) -> list[float]:
    orders = mt5.orders_get(symbol=symbol)
    if not orders:
        return []
    prices: list[float] = []
    for order in orders:
        if int(getattr(order, "magic", 0) or 0) != magic:
            continue
        if int(order.type) == order_type:
            prices.append(float(order.price_open))
    return prices


def cancel_pending_order(order: Any) -> bool:
    request = {
        "action": mt5.TRADE_ACTION_REMOVE,
        "order": int(order.ticket),
        "symbol": order.symbol,
        "magic": int(getattr(order, "magic", 0) or 0),
        "comment": "cancel opposite grid",
    }
    result = mt5.order_send(request)
    return bool(result is not None and result.retcode == mt5.TRADE_RETCODE_DONE)


def cancel_opposite_pending(symbol: str, magic: int, triggered_side: str) -> int:
    orders = mt5.orders_get(symbol=symbol)
    if not orders:
        return 0
    opposite_type = mt5.ORDER_TYPE_SELL_STOP if triggered_side == "BUY" else mt5.ORDER_TYPE_BUY_STOP
    cancelled = 0
    for order in orders:
        if int(getattr(order, "magic", 0) or 0) != magic:
            continue
        if int(order.type) != opposite_type:
            continue
        if cancel_pending_order(order):
            cancelled += 1
    return cancelled


def active_grid_positions(symbol: str, magic: int) -> list[Any]:
    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        return []
    return [p for p in positions if int(getattr(p, "magic", 0) or 0) == magic]


def improve_position_sl(symbol: str, position: Any, new_sl: float, deviation_points: int) -> bool:
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": symbol,
        "position": int(position.ticket),
        "sl": normalize_price(symbol, new_sl),
        "tp": float(position.tp or 0.0),
        "deviation": deviation_points,
        "magic": int(getattr(position, "magic", 0) or 0),
        "comment": "runner trail",
    }
    result = mt5.order_send(request)
    return bool(result is not None and result.retcode == mt5.TRADE_RETCODE_DONE)


def manage_runner_positions(symbol: str, config: GridConfig) -> None:
    if not config.manage_runner or config.runner_monitor_minutes <= 0:
        return

    log(
        f"Runner manager active: trail starts at +{config.runner_trail_start_r:g}R, "
        f"distance={config.runner_trail_distance_r:g}R, monitor={config.runner_monitor_minutes}m"
    )
    end_at = time.time() + config.runner_monitor_minutes * 60
    last_triggered_side: str | None = None
    original_risk_by_ticket: dict[int, float] = {}

    while time.time() <= end_at:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            time.sleep(1)
            continue

        positions = active_grid_positions(symbol, config.magic)
        if positions:
            triggered_side = "BUY" if int(positions[0].type) == mt5.POSITION_TYPE_BUY else "SELL"
            if config.cancel_opposite_on_trigger and triggered_side != last_triggered_side:
                cancelled = cancel_opposite_pending(symbol, config.magic, triggered_side)
                if cancelled:
                    log(f"Triggered {triggered_side}; cancelled {cancelled} opposite pending orders.")
                last_triggered_side = triggered_side

        for position in positions:
            ticket = int(position.ticket)
            is_buy = int(position.type) == mt5.POSITION_TYPE_BUY
            entry = float(position.price_open)
            old_sl = float(position.sl or 0.0)
            if old_sl <= 0:
                continue

            if ticket not in original_risk_by_ticket:
                original_risk_by_ticket[ticket] = entry - old_sl if is_buy else old_sl - entry
            risk = original_risk_by_ticket[ticket]
            if risk <= 0:
                continue

            live_price = float(tick.bid if is_buy else tick.ask)
            current_r = (live_price - entry) / risk if is_buy else (entry - live_price) / risk
            if current_r < config.runner_trail_start_r:
                continue

            new_sl = live_price - config.runner_trail_distance_r * risk if is_buy else live_price + config.runner_trail_distance_r * risk
            improves = new_sl > old_sl if is_buy else new_sl < old_sl
            if improves and improve_position_sl(symbol, position, new_sl, config.deviation_points):
                log(
                    f"Trail updated ticket={ticket} side={'BUY' if is_buy else 'SELL'} "
                    f"R={current_r:.2f} SL {old_sl:.3f} -> {normalize_price(symbol, new_sl):.3f}"
                )

        if not positions and last_triggered_side is not None:
            log("No active grid positions left; runner manager stopped.")
            return
        time.sleep(1)

    log("Runner monitor time ended.")


@dataclass(frozen=True)
class GridConfig:
    wanted_symbol: str
    place_orders: bool
    order_side: str
    order_count: int
    buy_order_count: int
    sell_order_count: int
    fixed_lot: float | str
    price_diff_usd: float
    first_offset_usd: float
    buy_price_diff_usd: float
    sell_price_diff_usd: float
    buy_first_offset_usd: float
    sell_first_offset_usd: float
    sl_mode: str
    sl_room_usd: float
    sl_distance_usd: float
    tp_distance_usd: float
    manage_runner: bool
    runner_trail_start_r: float
    runner_trail_distance_r: float
    runner_monitor_minutes: int
    cancel_opposite_on_trigger: bool
    magic: int
    deviation_points: int
    expiration_minutes: int
    skip_duplicate_pending: bool
    duplicate_tolerance_usd: float
    respect_broker_min_distance: bool


def load_config() -> GridConfig:
    step = env_float("PRICE_DIFF_USD", 1.0)
    first_offset = env_float("FIRST_OFFSET_USD", step)
    order_count = max(1, env_int("ORDER_COUNT", 1))
    order_side = os.getenv("ORDER_SIDE", "both").strip().lower()
    if order_side not in {"buy", "sell", "both"}:
        raise ValueError("ORDER_SIDE must be buy, sell, or both.")
    sl_mode = os.getenv("SL_MODE", "opposite_candle").strip().lower()
    if sl_mode not in {"fixed", "opposite_candle"}:
        raise ValueError("SL_MODE must be fixed or opposite_candle.")
    return GridConfig(
        wanted_symbol=os.getenv("XAU_SYMBOL", "XAUUSD").strip() or "XAUUSD",
        place_orders=env_bool("PLACE_ORDERS", False),
        order_side=order_side,
        order_count=order_count,
        buy_order_count=max(0, env_int("BUY_ORDER_COUNT", order_count)),
        sell_order_count=max(0, env_int("SELL_ORDER_COUNT", order_count)),
        fixed_lot=env_lot("FIXED_LOT", 0.01),
        price_diff_usd=step,
        first_offset_usd=first_offset,
        buy_price_diff_usd=env_float("BUY_PRICE_DIFF_USD", step),
        sell_price_diff_usd=env_float("SELL_PRICE_DIFF_USD", step),
        buy_first_offset_usd=env_float("BUY_FIRST_OFFSET_USD", first_offset),
        sell_first_offset_usd=env_float("SELL_FIRST_OFFSET_USD", first_offset),
        sl_mode=sl_mode,
        sl_room_usd=max(0.0, env_float("SL_ROOM_USD", 20.0)),
        sl_distance_usd=max(0.0, env_float("SL_DISTANCE_USD", 0.0)),
        tp_distance_usd=max(0.0, env_float("TP_DISTANCE_USD", 0.0)),
        manage_runner=env_bool("MANAGE_RUNNER", True),
        runner_trail_start_r=max(0.1, env_float("RUNNER_TRAIL_START_R", 7.0)),
        runner_trail_distance_r=max(0.1, env_float("RUNNER_TRAIL_DISTANCE_R", 1.0)),
        runner_monitor_minutes=max(0, env_int("RUNNER_MONITOR_MINUTES", 120)),
        cancel_opposite_on_trigger=env_bool("CANCEL_OPPOSITE_ON_TRIGGER", True),
        magic=env_int("MAGIC", 7143001),
        deviation_points=env_int("DEVIATION_POINTS", 30),
        expiration_minutes=max(0, env_int("EXPIRATION_MINUTES", 0)),
        skip_duplicate_pending=env_bool("SKIP_DUPLICATE_PENDING", True),
        duplicate_tolerance_usd=max(0.0, env_float("DUPLICATE_PRICE_TOLERANCE_USD", 0.10)),
        respect_broker_min_distance=env_bool("RESPECT_BROKER_MIN_DISTANCE", True),
    )


def build_request(
    symbol: str,
    side: str,
    price: float,
    lot: float,
    config: GridConfig,
    index: int,
    candle: dict[str, float],
) -> dict[str, Any]:
    is_buy = side == "BUY"
    request: dict[str, Any] = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY_STOP if is_buy else mt5.ORDER_TYPE_SELL_STOP,
        "price": normalize_price(symbol, price),
        "deviation": config.deviation_points,
        "magic": config.magic,
        "comment": f"XAU M1 {side.lower()} grid {index}"[:31],
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }
    if config.sl_mode == "opposite_candle":
        sl = candle["low"] - config.sl_room_usd if is_buy else candle["high"] + config.sl_room_usd
        request["sl"] = normalize_price(symbol, sl)
    elif config.sl_distance_usd > 0:
        sl = price - config.sl_distance_usd if is_buy else price + config.sl_distance_usd
        request["sl"] = normalize_price(symbol, sl)
    if config.tp_distance_usd > 0:
        tp = price + config.tp_distance_usd if is_buy else price - config.tp_distance_usd
        request["tp"] = normalize_price(symbol, tp)
    if config.expiration_minutes > 0:
        request["type_time"] = mt5.ORDER_TIME_SPECIFIED
        # Some brokers expose server-local epoch values through MT5. Using the
        # computer clock can therefore create an expiration already in the past
        # from the trade server's perspective.
        request["expiration"] = broker_time(symbol) + config.expiration_minutes * 60
    return request


def handle_ladder(
    symbol: str,
    side: str,
    base_price: float,
    count: int,
    price_diff: float,
    lot: float,
    config: GridConfig,
    candle: dict[str, float],
) -> tuple[int, int, int]:
    placed = 0
    blocked = 0
    skipped = 0
    if count <= 0:
        print(f"{side}: disabled count={count}")
        return placed, blocked, skipped

    mt5_type = mt5.ORDER_TYPE_BUY_STOP if side == "BUY" else mt5.ORDER_TYPE_SELL_STOP
    existing_prices = existing_pending_prices(symbol, config.magic, mt5_type)
    same_price_mode = price_diff == 0
    if same_price_mode:
        print(f"{side}: same-price mode enabled; all {count} orders target {normalize_price(symbol, base_price)}")
    dynamic_lot = config.fixed_lot == "max"
    print(f"{side}: using lot={'max dynamic' if dynamic_lot else f'{lot:g}'}")

    for index in range(1, count + 1):
        price = base_price + (index - 1) * price_diff if side == "BUY" else base_price - (index - 1) * price_diff
        request_price_preview = normalize_price(symbol, price)
        order_lot = max_allowed_lot(symbol, side, request_price_preview) if dynamic_lot else lot
        request = build_request(symbol, side, price, order_lot, config, index, candle)
        request_price = float(request["price"])
        duplicate = any(abs(request_price - old_price) <= config.duplicate_tolerance_usd for old_price in existing_prices)
        if config.skip_duplicate_pending and duplicate:
            print(f"{side} L{index}: skipped duplicate stop near {request_price}")
            skipped += 1
            continue

        check = mt5.order_check(request)
        if check is None:
            print(f"{side} L{index}: order_check failed: {mt5.last_error()} | request={request}")
            blocked += 1
            continue
        if check.retcode not in {0, mt5.TRADE_RETCODE_DONE}:
            print(f"{side} L{index}: check blocked {check.retcode} {check.comment} | request={request}")
            blocked += 1
            continue

        if not config.place_orders:
            print(f"{side} L{index}: dry-run STOP @ {request_price} lot={order_lot:g} request={request}")
            continue

        result = mt5.order_send(request)
        if result is None:
            print(f"{side} L{index}: send failed: {mt5.last_error()} | request={request}")
            blocked += 1
        elif result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"{side} L{index}: placed STOP ticket={result.order} @ {request_price} lot={order_lot:g}")
            placed += 1
            if config.skip_duplicate_pending:
                existing_prices.append(request_price)
        else:
            print(
                f"{side} L{index}: send blocked {result.retcode} {result.comment} "
                f"| last_error={mt5.last_error()} | request={request}"
            )
            blocked += 1
    return placed, blocked, skipped


def main() -> int:
    started_at = time.perf_counter()
    started_wall = now_local()
    load_env_file()
    config = load_config()
    mt5_path = os.getenv("MT5_PATH", "").strip()

    try:
        log(f"Run started at {started_wall}")
        log("Initializing MT5 connection...")
        initialized = mt5.initialize(path=mt5_path) if mt5_path else mt5.initialize()
        if not initialized:
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
        log("MT5 initialized.")

        account = mt5.account_info()
        if account is None:
            raise RuntimeError("MT5 account is not connected.")

        log("Discovering broker XAU symbol...")
        symbol = discover_xau_symbol(config.wanted_symbol)
        log(f"Resolved symbol {config.wanted_symbol} -> {symbol}")
        log("Reading latest closed M1 candle...")
        candle = latest_closed_m1(symbol)
        candle_time = datetime.fromtimestamp(candle["time"], tz=timezone.utc).isoformat()
        min_buy_price, max_sell_price = broker_stop_limits(symbol) if config.respect_broker_min_distance else (0.0, float("inf"))
        buy_base_price = max(candle["high"] + config.buy_first_offset_usd, min_buy_price)
        sell_base_price = min(candle["low"] - config.sell_first_offset_usd, max_sell_price)
        if config.fixed_lot == "max":
            buy_lot = max_allowed_lot(symbol, "BUY", normalize_price(symbol, buy_base_price))
            sell_lot = max_allowed_lot(symbol, "SELL", normalize_price(symbol, sell_base_price))
            lot_label = f"max dynamic (buy={buy_lot:g}, sell={sell_lot:g})"
        else:
            buy_lot = normalize_lot(symbol, float(config.fixed_lot))
            sell_lot = buy_lot
            lot_label = f"{buy_lot:g}"

        print("============================================================")
        print("XAU M1 Buy-Stop Grid")
        print("============================================================")
        print(f"Account: {account.login} | {account.server} | equity={account.equity:.2f}")
        print(f"Symbol: {config.wanted_symbol} -> {symbol}")
        print(f"Latest closed M1 candle: {candle_time}")
        print(f"High={candle['high']:.3f} Low={candle['low']:.3f} Close={candle['close']:.3f}")
        print(f"Side={config.order_side} Lot={lot_label}")
        print(
            f"BuyStops={config.buy_order_count} above high, firstOffset=${config.buy_first_offset_usd:g}, "
            f"step=${config.buy_price_diff_usd:g}"
        )
        print(
            f"SellStops={config.sell_order_count} below low, firstOffset=${config.sell_first_offset_usd:g}, "
            f"step=${config.sell_price_diff_usd:g}"
        )
        print(
            f"SL mode={config.sl_mode} "
            f"SL room=${config.sl_room_usd:g} fixed SL distance=${config.sl_distance_usd:g} "
            f"TP distance=${config.tp_distance_usd:g}"
        )
        print(
            f"Runner manager={config.manage_runner} trailStart={config.runner_trail_start_r:g}R "
            f"trailDistance={config.runner_trail_distance_r:g}R cancelOpposite={config.cancel_opposite_on_trigger}"
        )
        print(f"PLACE_ORDERS={config.place_orders}")
        print("")

        placed = blocked = skipped = 0
        if config.order_side in {"buy", "both"}:
            outcome = handle_ladder(
                symbol,
                "BUY",
                buy_base_price,
                config.buy_order_count,
                config.buy_price_diff_usd,
                buy_lot,
                config,
                candle,
            )
            placed += outcome[0]
            blocked += outcome[1]
            skipped += outcome[2]
        if config.order_side in {"sell", "both"}:
            outcome = handle_ladder(
                symbol,
                "SELL",
                sell_base_price,
                config.sell_order_count,
                config.sell_price_diff_usd,
                sell_lot,
                config,
                candle,
            )
            placed += outcome[0]
            blocked += outcome[1]
            skipped += outcome[2]
        print("")
        print(f"Order summary: placed={placed} blocked={blocked} skipped={skipped}")
        if config.place_orders and placed == 0 and blocked > 0:
            log("ERROR: no pending orders were placed.")
            return 2
        if config.place_orders:
            manage_runner_positions(symbol, config)
        return 0
    finally:
        try:
            mt5.shutdown()
        finally:
            elapsed = time.perf_counter() - started_at
            log(f"Run finished. Total elapsed: {elapsed:.3f}s")


if __name__ == "__main__":
    raise SystemExit(main())
