from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import math
import time

import MetaTrader5 as mt5
import pandas as pd

from .config import Config
from .mt5_data import (
    MT5Error,
    account_summary,
    discover_symbol,
    fetch_m1,
    normalize_price,
    strategy_orders,
    strategy_positions,
    volume_for_risk,
)
from .portfolio_guard import selected_xau_entry_guard
from .strategy import (
    build_plans,
    idea_comment,
    loss_streak_from_results,
    risk_pct_for_streak,
)


LOGGER = logging.getLogger("dmc.live")


def _closed_trade_results(magic: int) -> list[float]:
    """Reconstruct completed strategy-position P/L in chronological order."""
    start = datetime(2000, 1, 1, tzinfo=timezone.utc)
    deals = tuple(mt5.history_deals_get(start, datetime.now(timezone.utc)) or ())
    grouped: dict[int, dict[str, float]] = {}
    for deal in deals:
        if int(getattr(deal, "magic", 0)) != magic:
            continue
        position_id = int(getattr(deal, "position_id", 0))
        if position_id <= 0:
            continue
        item = grouped.setdefault(
            position_id, {"pnl": 0.0, "closed": 0.0, "time_msc": 0.0}
        )
        item["pnl"] += sum(
            float(getattr(deal, name, 0.0) or 0.0)
            for name in ("profit", "commission", "swap", "fee")
        )
        entry = int(getattr(deal, "entry", -1))
        if entry in {mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY}:
            item["closed"] = 1.0
            item["time_msc"] = max(
                item["time_msc"], float(getattr(deal, "time_msc", 0) or 0)
            )
    closed = sorted(
        (item for item in grouped.values() if item["closed"]),
        key=lambda item: item["time_msc"],
    )
    return [item["pnl"] for item in closed]


def _next_live_risk_pct(config: Config) -> tuple[float, int]:
    if not config.risk_progression_enabled:
        return config.risk_pct, 0
    streak = loss_streak_from_results(_closed_trade_results(config.magic))
    risk_pct = risk_pct_for_streak(
        config.risk_pct,
        streak,
        config.risk_progression_multiplier,
        config.live_max_risk_pct,
    )
    return risk_pct, streak


def _accepted(retcode: int) -> bool:
    return retcode in {0, mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED}


def _send_pending(config: Config, symbol: str, plan, volume: float):
    order_type = mt5.ORDER_TYPE_BUY_LIMIT if plan.side > 0 else mt5.ORDER_TYPE_SELL_LIMIT
    base = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": normalize_price(symbol, plan.entry),
        "sl": normalize_price(symbol, plan.initial_stop),
        "tp": normalize_price(symbol, plan.target) if plan.target else 0.0,
        "deviation": config.deviation_points,
        "magic": config.magic,
        "comment": idea_comment(plan.rank, plan.reason),
        "type_time": mt5.ORDER_TIME_SPECIFIED,
        "expiration": int(plan.expiry.timestamp()),
    }
    last = None
    for filling in (mt5.ORDER_FILLING_RETURN, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK):
        request = {**base, "type_filling": filling}
        check = mt5.order_check(request)
        if check is None or not _accepted(int(check.retcode)):
            last = check
            continue
        result = mt5.order_send(request)
        if result is not None and _accepted(int(result.retcode)):
            return result
        last = result
    raise MT5Error(f"Pending order rejected for {symbol}: {last}")


def _modify_stop(symbol: str, position, stop: float) -> None:
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": symbol,
        "position": int(position.ticket),
        "sl": normalize_price(symbol, stop),
        "tp": float(position.tp or 0.0),
    }
    result = mt5.order_send(request)
    if result is None or int(result.retcode) != mt5.TRADE_RETCODE_DONE:
        raise MT5Error(f"Could not trail position {position.ticket}: {result}")


def _close_position(config: Config, symbol: str, position) -> None:
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise MT5Error(f"No current tick for {symbol}")
    is_buy = int(position.type) == mt5.POSITION_TYPE_BUY
    base = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": int(position.ticket),
        "symbol": symbol,
        "volume": float(position.volume),
        "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
        "price": float(tick.bid if is_buy else tick.ask),
        "deviation": config.deviation_points,
        "magic": config.magic,
        "comment": "DmC manage max hold",
        "type_time": mt5.ORDER_TIME_GTC,
    }
    last = None
    for filling in (mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN):
        result = mt5.order_send({**base, "type_filling": filling})
        if result is not None and int(result.retcode) == mt5.TRADE_RETCODE_DONE:
            return
        last = result
    raise MT5Error(f"Could not close position {position.ticket}: {last}")


def _manage(config: Config, symbol: str, frame: pd.DataFrame, now: datetime) -> None:
    if frame.empty:
        return
    closed = frame[frame.time < pd.Timestamp(now)]
    if closed.empty:
        return
    close = float(closed.iloc[-1].close)
    risk = config.stop_points
    for position in strategy_positions(symbol, config.magic):
        opened = datetime.fromtimestamp(int(position.time), timezone.utc)
        if now - opened >= timedelta(hours=config.max_hold_hours):
            _close_position(config, symbol, position)
            LOGGER.info("Closed %s after max hold", position.ticket)
            continue
        is_buy = int(position.type) == mt5.POSITION_TYPE_BUY
        favorable = close - float(position.price_open) if is_buy else float(position.price_open) - close
        if not config.trailing_enabled:
            continue
        if favorable < config.trail_start_r * risk:
            continue
        proposed = close - config.trail_distance_r * risk if is_buy else close + config.trail_distance_r * risk
        current = float(position.sl or 0.0)
        improves = proposed > current if is_buy else current == 0.0 or proposed < current
        if improves:
            _modify_stop(symbol, position, proposed)
            LOGGER.info("Trailed %s stop to %.3f", position.ticket, proposed)


def _active_symbol_count(symbols: list[str], magic: int) -> int:
    return sum(
        bool(strategy_orders(symbol, magic) or strategy_positions(symbol, magic))
        for symbol in symbols
    )


def _run_symbol_cycle(
    config: Config,
    account: dict[str, object],
    symbol: str,
    *,
    can_open: bool,
    risk_pct: float,
) -> bool:
    now = datetime.now(timezone.utc)
    history_days = (
        120
        if config.h1_confirmation_mode == "body_level"
        or config.target_mode == "next_body"
        else 10
    )
    frame = fetch_m1(symbol, now - timedelta(days=history_days), now)
    _manage(config, symbol, frame, now)
    if strategy_orders(symbol, config.magic) or strategy_positions(symbol, config.magic):
        return False
    if not can_open:
        LOGGER.info(
            "Skipping %s: DmC portfolio risk cap %.2f%% is already allocated",
            symbol,
            config.max_total_risk_pct,
        )
        return False
    plans = [plan for plan in build_plans(frame, config) if plan.signal_time <= now <= plan.expiry]
    if not plans:
        LOGGER.info("No current aligned D1/H4 setup for %s", symbol)
        return False
    plan = plans[-1]
    tick = mt5.symbol_info_tick(symbol)
    info = mt5.symbol_info(symbol)
    if tick is None or info is None:
        raise MT5Error(f"No live quote for {symbol}")
    spread = (float(tick.ask) - float(tick.bid)) / float(info.point)
    if spread > config.max_spread_points:
        LOGGER.info("Skipping %s: spread %.1f > %.1f", symbol, spread, config.max_spread_points)
        return False
    valid_limit = plan.entry < float(tick.ask) if plan.side > 0 else plan.entry > float(tick.bid)
    if not valid_limit:
        LOGGER.info("Ignoring stale %s setup: pullback entry was already crossed", symbol)
        return False
    risk_cash = float(account["equity"]) * risk_pct / 100.0
    volume = volume_for_risk(symbol, plan.side, plan.entry, plan.initial_stop, risk_cash)
    order_type = mt5.ORDER_TYPE_BUY if plan.side > 0 else mt5.ORDER_TYPE_SELL
    projected_loss = mt5.order_calc_profit(
        order_type,
        symbol,
        volume,
        plan.entry,
        plan.initial_stop,
    )
    actual_risk_pct = (
        abs(float(projected_loss)) / float(account["equity"]) * 100.0
        if projected_loss is not None and float(account["equity"]) > 0
        else risk_pct
    )
    guard_risk_pct = max(risk_pct, actual_risk_pct)
    if actual_risk_pct > risk_pct + 1e-9:
        LOGGER.warning(
            "%s broker minimum %.2f lots raises planned risk from %.2f%% to %.2f%%",
            symbol,
            volume,
            risk_pct,
            actual_risk_pct,
        )
    with selected_xau_entry_guard(guard_risk_pct) as decision:
        if not decision.allowed:
            LOGGER.warning(
                "Skipping %s: shared XAU risk %.2f%% + %.2f%% exceeds %.2f%%",
                symbol,
                decision.current_risk_pct,
                decision.proposed_risk_pct,
                decision.cap_risk_pct,
            )
            return False
        result = _send_pending(config, symbol, plan, volume)
    LOGGER.info(
        "Placed %s %s %s %.2f at %.3f SL %.3f ticket=%s",
        symbol,
        plan.rank,
        "BUY_LIMIT" if plan.side > 0 else "SELL_LIMIT",
        volume,
        plan.entry,
        plan.initial_stop,
        getattr(result, "order", 0),
    )
    return True


def run_cycle(config: Config) -> None:
    if not config.live_allowed:
        raise RuntimeError(
            "Live execution requires ENABLE_TRADING=true, DRY_RUN=false and "
            "LIVE_UNLOCK=I_ACCEPT_DMC_LIVE_RISK"
        )
    account = account_summary()
    if not account["trade_allowed"]:
        raise MT5Error("The connected MT5 account does not permit trading")
    configured = (
        [config.for_instrument(item.canonical_symbol) for item in config.instruments]
        if config.instruments
        else [config]
    )
    resolved: list[tuple[Config, str]] = []
    seen: set[str] = set()
    for instrument_config in configured:
        try:
            symbol = discover_symbol(instrument_config.canonical_symbol)
        except MT5Error as error:
            LOGGER.error("Skipping %s: %s", instrument_config.canonical_symbol, error)
            continue
        if symbol.casefold() in seen:
            continue
        seen.add(symbol.casefold())
        resolved.append((instrument_config, symbol))
    if not resolved:
        raise MT5Error("None of the configured DmC instruments is tradeable")

    symbols = [symbol for _, symbol in resolved]
    next_risk_pct, loss_streak = _next_live_risk_pct(config)
    maximum_slots = max(
        1,
        math.floor(config.max_total_risk_pct / next_risk_pct + 1e-9),
    )
    LOGGER.info(
        "Risk state: base %.3f%% | loss streak %d | next %.3f%% | live cap %.3f%%",
        config.risk_pct,
        loss_streak,
        next_risk_pct,
        config.live_max_risk_pct,
    )
    for instrument_config, symbol in resolved:
        active = _active_symbol_count(symbols, config.magic)
        placed = _run_symbol_cycle(
            instrument_config,
            account,
            symbol,
            can_open=active < maximum_slots,
            risk_pct=next_risk_pct,
        )
        if placed:
            LOGGER.info(
                "DmC exposure after %s: %.2f%% / %.2f%% cap",
                symbol,
                (active + 1) * next_risk_pct,
                config.max_total_risk_pct,
            )


def run_live(config: Config, *, once: bool = False) -> None:
    account = account_summary()
    LOGGER.info(
        "Account %s | %s | balance %.2f %s | equity %.2f | leverage 1:%s",
        account["login"], account["server"], account["balance"], account["currency"],
        account["equity"], account["leverage"],
    )
    while True:
        run_cycle(config)
        if once:
            return
        time.sleep(config.poll_seconds)
