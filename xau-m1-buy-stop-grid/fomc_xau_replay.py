from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import MetaTrader5 as mt5

from xau_m1_buy_stop_grid import (
    discover_xau_symbol,
    load_config,
    load_env_file,
    normalize_price,
)


@dataclass
class ReplayPosition:
    level: int
    side: str
    stop_price: float
    entry_time: str
    entry: float
    initial_sl: float
    exit_time: str | None = None
    exit: float | None = None
    exit_reason: str | None = None
    pnl_usd: float | None = None
    max_r: float = 0.0
    max_floating_pnl_usd: float = 0.0
    max_floating_time: str | None = None
    final_sl: float = 0.0


def utc_text(timestamp: float, history_offset_hours: float) -> str:
    adjusted = timestamp - history_offset_hours * 3600.0
    return datetime.fromtimestamp(adjusted, tz=UTC).isoformat()


def rates_for_window(symbol: str, start: datetime, end: datetime) -> list[dict[str, Any]]:
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, end)
    if rates is None:
        raise RuntimeError(f"MT5 rate request failed: {mt5.last_error()}")
    return [{name: row[name].item() for name in rates.dtype.names} for row in rates]


def ticks_for_window(symbol: str, start: datetime, end: datetime) -> list[dict[str, Any]]:
    ticks = mt5.copy_ticks_range(symbol, start, end, mt5.COPY_TICKS_ALL)
    if ticks is None:
        raise RuntimeError(f"MT5 tick request failed: {mt5.last_error()}")
    return [{name: row[name].item() for name in ticks.dtype.names} for row in ticks]


def choose_history_clock(
    symbol: str,
    event_utc: datetime,
    preferred_offset_hours: float,
) -> tuple[float, float, list[dict[str, Any]], list[dict[str, Any]]]:
    candidates = [preferred_offset_hours]
    if preferred_offset_hours != 0:
        candidates.append(0.0)

    best: tuple[int, float, float, list[dict[str, Any]], list[dict[str, Any]]] | None = None
    for offset in candidates:
        broker_event = event_utc + timedelta(hours=offset)
        rates = rates_for_window(
            symbol,
            broker_event - timedelta(minutes=3),
            broker_event + timedelta(minutes=2),
        )
        ticks = ticks_for_window(
            symbol,
            broker_event - timedelta(seconds=5),
            broker_event + timedelta(minutes=121),
        )
        score = len(ticks)
        if rates:
            score += 1_000_000
        if best is None or score > best[0]:
            best = (score, offset, broker_event.timestamp(), rates, ticks)

    if best is None or not best[3] or not best[4]:
        raise RuntimeError("No XAUUSD M1/tick history was available around the FOMC release.")
    return best[1], best[2], best[3], best[4]


def tick_profit(symbol: str, side: str, lot: float, entry: float, exit_price: float) -> float:
    order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
    value = mt5.order_calc_profit(order_type, symbol, lot, entry, exit_price)
    if value is None:
        multiplier = 1.0 if side == "BUY" else -1.0
        return multiplier * (exit_price - entry) * lot * 100.0
    return float(value)


def margin_required(symbol: str, side: str, lot: float, entry: float) -> float | None:
    order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
    value = mt5.order_calc_margin(order_type, symbol, lot, entry)
    return None if value is None else float(value)


def replay(
    symbol: str,
    event_timestamp: float,
    history_offset_hours: float,
    rates: list[dict[str, Any]],
    ticks: list[dict[str, Any]],
    lot: float,
    balance: float,
    stopout_percent: float,
) -> dict[str, Any]:
    config = load_config()
    setup_rows = [row for row in rates if float(row["time"]) < event_timestamp]
    if not setup_rows:
        raise RuntimeError("No completed setup candle exists immediately before the release.")
    setup = max(setup_rows, key=lambda row: float(row["time"]))

    buy_levels = [
        normalize_price(
            symbol,
            float(setup["high"]) + config.buy_first_offset_usd + index * config.buy_price_diff_usd,
        )
        for index in range(config.buy_order_count)
    ]
    sell_levels = [
        normalize_price(
            symbol,
            float(setup["low"]) - config.sell_first_offset_usd - index * config.sell_price_diff_usd,
        )
        for index in range(config.sell_order_count)
    ]
    buy_sl = normalize_price(symbol, float(setup["low"]) - config.sl_room_usd)
    sell_sl = normalize_price(symbol, float(setup["high"]) + config.sl_room_usd)
    expiration = event_timestamp + config.expiration_minutes * 60.0
    monitor_end = event_timestamp + config.runner_monitor_minutes * 60.0

    pending = {
        "BUY": {index + 1: level for index, level in enumerate(buy_levels)},
        "SELL": {index + 1: level for index, level in enumerate(sell_levels)},
    }
    triggered_side: str | None = None
    positions: list[ReplayPosition] = []
    active: list[dict[str, Any]] = []
    rejected_for_margin: list[dict[str, Any]] = []
    realized_pnl = 0.0

    for tick in ticks:
        timestamp = float(tick["time_msc"]) / 1000.0
        if timestamp < event_timestamp:
            continue
        if timestamp > monitor_end:
            break
        bid = float(tick["bid"])
        ask = float(tick["ask"])

        for position in list(active):
            item: ReplayPosition = position["item"]
            current_sl = float(position["sl"])
            stop_hit = bid <= current_sl if item.side == "BUY" else ask >= current_sl
            if stop_hit:
                exit_price = min(current_sl, bid) if item.side == "BUY" else max(current_sl, ask)
                item.exit_time = utc_text(timestamp, history_offset_hours)
                item.exit = normalize_price(symbol, exit_price)
                item.exit_reason = "stop/trail"
                item.pnl_usd = tick_profit(symbol, item.side, lot, item.entry, item.exit)
                realized_pnl += item.pnl_usd
                item.final_sl = normalize_price(symbol, current_sl)
                active.remove(position)
                continue

            live_price = bid if item.side == "BUY" else ask
            risk = abs(item.entry - item.initial_sl)
            current_r = (
                (live_price - item.entry) / risk
                if item.side == "BUY"
                else (item.entry - live_price) / risk
            )
            item.max_r = max(item.max_r, current_r)
            floating_pnl = tick_profit(symbol, item.side, lot, item.entry, live_price)
            if floating_pnl > item.max_floating_pnl_usd:
                item.max_floating_pnl_usd = floating_pnl
                item.max_floating_time = utc_text(timestamp, history_offset_hours)
            if current_r >= config.runner_trail_start_r:
                candidate = (
                    live_price - config.runner_trail_distance_r * risk
                    if item.side == "BUY"
                    else live_price + config.runner_trail_distance_r * risk
                )
                if item.side == "BUY":
                    position["sl"] = max(current_sl, candidate)
                else:
                    position["sl"] = min(current_sl, candidate)

        if active:
            active_floating = sum(
                tick_profit(
                    symbol,
                    position["item"].side,
                    lot,
                    position["item"].entry,
                    bid if position["item"].side == "BUY" else ask,
                )
                for position in active
            )
            used_margin = sum(float(position["margin"]) for position in active)
            equity = balance + realized_pnl + active_floating
            margin_level = equity / used_margin * 100.0 if used_margin > 0 else float("inf")
            if margin_level <= stopout_percent:
                for position in list(active):
                    item = position["item"]
                    exit_price = bid if item.side == "BUY" else ask
                    item.exit_time = utc_text(timestamp, history_offset_hours)
                    item.exit = normalize_price(symbol, exit_price)
                    item.exit_reason = f"broker stop-out at {stopout_percent:g}% margin level"
                    item.pnl_usd = tick_profit(symbol, item.side, lot, item.entry, item.exit)
                    realized_pnl += item.pnl_usd
                    item.final_sl = normalize_price(symbol, float(position["sl"]))
                    active.remove(position)

        if timestamp > expiration:
            continue

        if triggered_side is None:
            buy_crossed = any(ask >= price for price in pending["BUY"].values())
            sell_crossed = any(bid <= price for price in pending["SELL"].values())
            if buy_crossed and not sell_crossed:
                triggered_side = "BUY"
                pending["SELL"].clear()
            elif sell_crossed and not buy_crossed:
                triggered_side = "SELL"
                pending["BUY"].clear()
            elif buy_crossed and sell_crossed:
                buy_gap = min(abs(ask - price) for price in pending["BUY"].values())
                sell_gap = min(abs(bid - price) for price in pending["SELL"].values())
                triggered_side = "BUY" if buy_gap <= sell_gap else "SELL"
                pending["SELL" if triggered_side == "BUY" else "BUY"].clear()

        if triggered_side is None:
            continue

        for level_number, level_price in list(pending[triggered_side].items()):
            crossed = ask >= level_price if triggered_side == "BUY" else bid <= level_price
            if not crossed:
                continue
            fill = max(level_price, ask) if triggered_side == "BUY" else min(level_price, bid)
            initial_sl = buy_sl if triggered_side == "BUY" else sell_sl
            order_margin = margin_required(symbol, triggered_side, lot, fill) or 0.0
            active_floating = sum(
                tick_profit(
                    symbol,
                    position["item"].side,
                    lot,
                    position["item"].entry,
                    bid if position["item"].side == "BUY" else ask,
                )
                for position in active
            )
            used_margin = sum(float(position["margin"]) for position in active)
            free_margin = balance + realized_pnl + active_floating - used_margin
            if order_margin > free_margin:
                rejected_for_margin.append(
                    {
                        "level": level_number,
                        "side": triggered_side,
                        "stop_price": level_price,
                        "attempted_fill": normalize_price(symbol, fill),
                        "required_margin_usd": round(order_margin, 2),
                        "free_margin_usd": round(free_margin, 2),
                        "time_utc": utc_text(timestamp, history_offset_hours),
                    }
                )
                del pending[triggered_side][level_number]
                continue
            item = ReplayPosition(
                level=level_number,
                side=triggered_side,
                stop_price=level_price,
                entry_time=utc_text(timestamp, history_offset_hours),
                entry=normalize_price(symbol, fill),
                initial_sl=initial_sl,
                final_sl=initial_sl,
            )
            positions.append(item)
            active.append({"item": item, "sl": initial_sl, "margin": order_margin})
            del pending[triggered_side][level_number]

        if active:
            active_floating = sum(
                tick_profit(
                    symbol,
                    position["item"].side,
                    lot,
                    position["item"].entry,
                    bid if position["item"].side == "BUY" else ask,
                )
                for position in active
            )
            used_margin = sum(float(position["margin"]) for position in active)
            equity = balance + realized_pnl + active_floating
            margin_level = equity / used_margin * 100.0 if used_margin > 0 else float("inf")
            if margin_level <= stopout_percent:
                for position in list(active):
                    item = position["item"]
                    exit_price = bid if item.side == "BUY" else ask
                    item.exit_time = utc_text(timestamp, history_offset_hours)
                    item.exit = normalize_price(symbol, exit_price)
                    item.exit_reason = f"broker stop-out at {stopout_percent:g}% margin level"
                    item.pnl_usd = tick_profit(symbol, item.side, lot, item.entry, item.exit)
                    realized_pnl += item.pnl_usd
                    item.final_sl = normalize_price(symbol, float(position["sl"]))
                    active.remove(position)

    if ticks:
        final_tick = ticks[-1]
        final_timestamp = min(
            float(final_tick["time_msc"]) / 1000.0,
            monitor_end,
        )
        final_bid = float(final_tick["bid"])
        final_ask = float(final_tick["ask"])
        for position in active:
            item = position["item"]
            exit_price = final_bid if item.side == "BUY" else final_ask
            item.exit_time = utc_text(final_timestamp, history_offset_hours)
            item.exit = normalize_price(symbol, exit_price)
            item.exit_reason = "marked at 120-minute monitor end"
            item.pnl_usd = tick_profit(symbol, item.side, lot, item.entry, item.exit)
            item.final_sl = normalize_price(symbol, float(position["sl"]))

    first = positions[0] if positions else None
    single_margin = margin_required(symbol, first.side, lot, first.entry) if first else None
    single_pnl = first.pnl_usd if first and first.pnl_usd is not None else 0.0
    batch_pnl = sum(item.pnl_usd or 0.0 for item in positions)
    batch_margin = sum(
        margin_required(symbol, item.side, lot, item.entry) or 0.0 for item in positions
    )
    return {
        "event_utc": utc_text(event_timestamp, history_offset_hours),
        "history_offset_hours": history_offset_hours,
        "symbol": symbol,
        "account_start_usd": balance,
        "lot_per_order": lot,
        "setup_candle": {
            "time_utc": utc_text(float(setup["time"]), history_offset_hours),
            "open": float(setup["open"]),
            "high": float(setup["high"]),
            "low": float(setup["low"]),
            "close": float(setup["close"]),
        },
        "buy_stop_levels": buy_levels,
        "sell_stop_levels": sell_levels,
        "buy_sl": buy_sl,
        "sell_sl": sell_sl,
        "expiration_minutes": config.expiration_minutes,
        "positions": [asdict(item) for item in positions],
        "orders_rejected_for_margin": rejected_for_margin,
        "broker_stopout_percent": stopout_percent,
        "single_first_order": {
            "entry": first.entry if first else None,
            "exit": first.exit if first else None,
            "pnl_usd": round(single_pnl, 2),
            "ending_balance_usd": round(balance + single_pnl, 2),
            "margin_required_usd_on_connected_account": (
                round(single_margin, 2) if single_margin is not None else None
            ),
            "fits_100_usd_before_floating_pnl": (
                single_margin <= balance if single_margin is not None else None
            ),
        },
        "full_triggered_batch": {
            "orders_filled": len(positions),
            "total_lot": round(len(positions) * lot, 4),
            "pnl_usd": round(batch_pnl, 2),
            "ending_balance_usd": round(balance + batch_pnl, 2),
            "margin_required_usd_on_connected_account": round(batch_margin, 2),
            "fits_100_usd_before_floating_pnl": batch_margin <= balance,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only XAU FOMC tick replay.")
    parser.add_argument("--balance", type=float, default=100.0)
    parser.add_argument("--lot", type=float, default=0.08)
    parser.add_argument("--event", default="2026-07-29T18:00:00+00:00")
    args = parser.parse_args()

    load_env_file()
    config = load_config()
    path = __import__("os").getenv("MT5_PATH", "").strip()
    initialized = mt5.initialize(path=path) if path else mt5.initialize()
    if not initialized:
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        if account is None:
            raise RuntimeError("No connected MT5 account.")
        symbol = discover_xau_symbol(config.wanted_symbol)
        event_utc = datetime.fromisoformat(args.event).astimezone(UTC)
        preferred_offset = float(
            __import__("os").getenv("NEWS_MT5_HISTORY_OFFSET_HOURS", "3")
        )
        offset, event_timestamp, rates, ticks = choose_history_clock(
            symbol,
            event_utc,
            preferred_offset,
        )
        result = replay(
            symbol,
            event_timestamp,
            offset,
            rates,
            ticks,
            args.lot,
            args.balance,
            float(account.margin_so_so),
        )
        result["connected_account"] = {
            "login": int(account.login),
            "server": account.server,
            "leverage": int(account.leverage),
        }
        print(json.dumps(result, indent=2))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
