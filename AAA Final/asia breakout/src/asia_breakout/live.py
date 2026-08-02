from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN
import logging
import time as time_module

import MetaTrader5 as mt5
import pandas as pd

from .config import AppConfig, StrategyConfig
from .engine import EntrySignal, find_entry_signal
from .mt5_data import (
    MarketDataUnavailable,
    MT5Error,
    discover_symbols,
    fetch_m1,
    mt5_connection,
    symbol_metadata,
)
from .observability import log_event, render_table
from .portfolio_guard import selected_xau_entry_guard
from .risk import progressed_risk_pct


LOGGER = logging.getLogger("asia_breakout.live")


def closed_strategy_loss_streak(config: AppConfig, now: datetime | None = None) -> int:
    """Count consecutive closed losing positions for this bot's magic number."""
    now = now or datetime.now(timezone.utc)
    deals = mt5.history_deals_get(now - timedelta(days=3650), now) or ()
    closed: dict[int, dict[str, float]] = {}
    for deal in deals:
        if int(deal.magic) != config.magic:
            continue
        if int(deal.entry) not in {mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_INOUT}:
            continue
        position_id = int(getattr(deal, "position_id", deal.ticket))
        record = closed.setdefault(position_id, {"time": 0.0, "pnl": 0.0})
        record["time"] = max(record["time"], float(deal.time))
        record["pnl"] += sum(
            float(getattr(deal, field, 0.0) or 0.0)
            for field in ("profit", "commission", "swap", "fee")
        )
    streak = 0
    for record in sorted(closed.values(), key=lambda item: item["time"], reverse=True):
        if record["pnl"] < -1e-9:
            streak += 1
        elif record["pnl"] > 1e-9:
            break
    return streak


def effective_live_risk_pct(
    config: AppConfig,
    strategy: StrategyConfig,
    now: datetime | None = None,
) -> float:
    if not strategy.risk_progression_enabled:
        return min(strategy.risk_pct, strategy.max_live_risk_pct)
    return progressed_risk_pct(
        strategy.risk_pct,
        closed_strategy_loss_streak(config, now),
        strategy.risk_progression_multiplier,
        strategy.max_live_risk_pct,
    )


def _round_volume(value: float, minimum: float, maximum: float, step: float) -> float:
    value = min(maximum, max(minimum, value))
    steps = (Decimal(str(value)) / Decimal(str(step))).quantize(
        Decimal("1"), rounding=ROUND_DOWN
    )
    return max(minimum, float(steps * Decimal(str(step))))


def volume_for_risk(
    symbol: str,
    direction: str,
    entry: float,
    stop: float,
    risk_cash: float,
) -> float:
    info = symbol_metadata(symbol)
    order_type = mt5.ORDER_TYPE_BUY if direction == "buy" else mt5.ORDER_TYPE_SELL
    loss_one_lot = mt5.order_calc_profit(order_type, symbol, 1.0, entry, stop)
    if loss_one_lot is None or loss_one_lot == 0:
        raise MT5Error(f"Cannot calculate risk for {symbol}: {mt5.last_error()}")
    raw = risk_cash / abs(float(loss_one_lot))
    volume = _round_volume(
        raw,
        float(info["volume_min"]),
        float(info["volume_max"]),
        float(info["volume_step"]),
    )
    planned = abs(float(loss_one_lot)) * volume
    if planned > risk_cash * 1.001:
        LOGGER.warning(
            "Using broker minimum volume %.4f for %s: planned risk $%.2f "
            "exceeds the configured $%.2f budget",
            volume,
            symbol,
            planned,
            risk_cash,
        )
    return volume


def _today_range(
    symbol: str,
    now: datetime,
    strategy: StrategyConfig,
) -> tuple[float, float]:
    day = now.date()
    start = datetime.combine(day, strategy.asia_start, tzinfo=timezone.utc)
    end = datetime.combine(day, strategy.asia_end, tzinfo=timezone.utc)
    # copy_rates_range is inclusive, so exclude the first London minute.
    range_end = min(now, end) - timedelta(seconds=1)
    frame = fetch_m1(symbol, start, range_end)
    return float(frame["high"].max()), float(frame["low"].min())


def _pending_request(
    symbol: str,
    direction: str,
    entry: float,
    stop: float,
    target: float,
    volume: float,
    expiration: datetime,
    magic: int,
    risk_pct: float,
) -> dict[str, object]:
    return {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY_STOP if direction == "buy" else mt5.ORDER_TYPE_SELL_STOP,
        "price": entry,
        "sl": stop,
        "tp": target,
        "magic": magic,
        "comment": f"AsiaBreakout A {direction.upper()} range break"[:31],
        "type_time": mt5.ORDER_TIME_SPECIFIED,
        "expiration": int(expiration.timestamp()),
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }


def _market_request(
    symbol: str,
    direction: str,
    entry: float,
    stop: float,
    target: float,
    volume: float,
    magic: int,
    risk_pct: float,
    filling_mode: int,
) -> dict[str, object]:
    return {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY if direction == "buy" else mt5.ORDER_TYPE_SELL,
        "price": entry,
        "sl": stop,
        "tp": target,
        "deviation": 20,
        "magic": magic,
        "comment": f"AsiaBreakout A {direction.upper()} range break"[:31],
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }


def _market_filling_modes(symbol: str) -> tuple[int, ...]:
    """Translate MT5 symbol filling flags into valid market-order modes.

    ``symbol_info().filling_mode`` is a bit mask of ``SYMBOL_FILLING_*``
    flags, not an ``ORDER_FILLING_*`` enum. For example, a value of 3 means
    that both FOK and IOC are supported; passing the raw value 3 in a trade
    request incorrectly selects BOC and causes retcode 10030.
    """
    info = mt5.symbol_info(symbol)
    if info is None:
        raise MT5Error(f"No symbol information for {symbol}")

    flags = int(info.filling_mode)
    modes: list[int] = []
    # The Python MT5 package does not expose SYMBOL_FILLING_* constants.
    # Their documented flag values are FOK=1 and IOC=2.
    if flags & 1:
        modes.append(int(mt5.ORDER_FILLING_FOK))
    if flags & 2:
        modes.append(int(mt5.ORDER_FILLING_IOC))

    # Brokers occasionally expose incomplete/incorrect symbol flags. These
    # safe market-order fallbacks are verified with order_check before use.
    for fallback in (
        int(mt5.ORDER_FILLING_FOK),
        int(mt5.ORDER_FILLING_IOC),
        int(mt5.ORDER_FILLING_RETURN),
    ):
        if fallback not in modes:
            modes.append(fallback)
    return tuple(modes)


def place_confirmation_market(
    config: AppConfig,
    instrument: str,
    symbol: str,
    signal: EntrySignal,
) -> dict[str, object]:
    strategy = config.strategy_for(instrument)
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise MT5Error(f"No live tick for {symbol}: {mt5.last_error()}")
    metadata = symbol_metadata(symbol)
    digits = int(metadata["digits"])
    entry = float(tick.ask if signal.direction == "buy" else tick.bid)
    stop = round(float(signal.stop), digits)
    risk_distance = abs(entry - stop)
    if risk_distance <= 0:
        raise MT5Error(f"Invalid live stop distance for {symbol}")
    target = (
        entry + strategy.rr * risk_distance
        if signal.direction == "buy"
        else entry - strategy.rr * risk_distance
    )
    entry = round(entry, digits)
    target = round(target, digits)
    account = mt5.account_info()
    if account is None:
        raise MT5Error(f"No MT5 account: {mt5.last_error()}")
    live_risk_pct = effective_live_risk_pct(config, strategy)
    risk_cash = float(account.balance) * live_risk_pct / 100.0
    volume = volume_for_risk(
        symbol,
        signal.direction,
        entry,
        stop,
        risk_cash,
    )
    request: dict[str, object] | None = None
    check = None
    rejected_modes: list[tuple[int, object]] = []
    for filling_mode in _market_filling_modes(symbol):
        candidate = _market_request(
            symbol,
            signal.direction,
            entry,
            stop,
            target,
            volume,
            config.magic,
            live_risk_pct,
            filling_mode,
        )
        candidate_check = mt5.order_check(candidate)
        if candidate_check is not None and candidate_check.retcode == 0:
            request = candidate
            check = candidate_check
            break
        rejected_modes.append((filling_mode, candidate_check))
    if request is None or check is None:
        raise MT5Error(
            f"Market order check failed for {symbol} with all supported "
            f"filling modes: {rejected_modes}"
        )
    log_event(
        LOGGER,
        logging.INFO,
        "market_filling_selected",
        f"{instrument} selected broker-compatible market filling mode",
        instrument=instrument,
        broker_symbol=symbol,
        symbol_filling_flags=int(mt5.symbol_info(symbol).filling_mode),
        selected_filling_mode=request["type_filling"],
    )
    if config.dry_run or not config.enable_trading:
        receipt = {
            "instrument": instrument,
            "status": "DRY_RUN",
            "risk_cash": risk_cash,
            **request,
        }
        log_event(
            LOGGER,
            logging.INFO,
            "market_order_dry_run",
            f"{instrument} confirmed market order displayed but not sent",
            **receipt,
        )
        return receipt
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        raise MT5Error(f"Market order send failed for {symbol}: {result}")
    receipt = {
        "instrument": instrument,
        "status": "PLACED",
        "risk_cash": risk_cash,
        **request,
        **result._asdict(),
    }
    log_event(
        LOGGER,
        logging.WARNING,
        "market_order_placed",
        f"{instrument} confirmed {signal.direction.upper()} market order placed",
        instrument=instrument,
        broker_symbol=symbol,
        ticket=getattr(result, "order", None),
        deal=getattr(result, "deal", None),
        volume=volume,
        entry=entry,
        stop=stop,
        target=target,
        risk_cash=risk_cash,
        risk_pct=live_risk_pct,
    )
    return receipt


def place_mechanical_oco(
    config: AppConfig,
    instrument: str,
    symbol: str,
    now: datetime,
) -> list[dict[str, object]]:
    strategy = config.strategy_for(instrument)
    if strategy.entry_mode != "mechanical_oco":
        raise NotImplementedError(
            "The live set-and-forget runner currently places mechanical OCO orders. "
            "Use backtest/optimization before enabling another live entry mode."
        )
    high, low = _today_range(symbol, now, strategy)
    metadata = symbol_metadata(symbol)
    digits = int(metadata["digits"])
    height = high - low
    buffer = height * strategy.buffer_range_fraction
    midpoint = (high + low) / 2.0
    buy_entry = high + buffer
    sell_entry = low - buffer
    if strategy.stop_mode == "midpoint":
        buy_stop = sell_stop = midpoint
    else:
        buy_stop = low - buffer
        sell_stop = high + buffer
    buy_target = buy_entry + strategy.rr * (buy_entry - buy_stop)
    sell_target = sell_entry - strategy.rr * (sell_stop - sell_entry)
    buy_entry = round(buy_entry, digits)
    sell_entry = round(sell_entry, digits)
    buy_stop = round(buy_stop, digits)
    sell_stop = round(sell_stop, digits)
    buy_target = round(buy_target, digits)
    sell_target = round(sell_target, digits)
    account = mt5.account_info()
    if account is None:
        raise MT5Error(f"No MT5 account: {mt5.last_error()}")
    live_risk_pct = effective_live_risk_pct(config, strategy, now)
    risk_cash = float(account.balance) * live_risk_pct / 100.0
    expiration = datetime.combine(
        now.date(), strategy.entry_cutoff, tzinfo=timezone.utc
    )
    requests = [
        _pending_request(
            symbol,
            "buy",
            buy_entry,
            buy_stop,
            buy_target,
            volume_for_risk(symbol, "buy", buy_entry, buy_stop, risk_cash),
            expiration,
            config.magic,
            live_risk_pct,
        ),
        _pending_request(
            symbol,
            "sell",
            sell_entry,
            sell_stop,
            sell_target,
            volume_for_risk(symbol, "sell", sell_entry, sell_stop, risk_cash),
            expiration,
            config.magic,
            live_risk_pct,
        ),
    ]
    log_event(
        LOGGER,
        logging.INFO,
        "oco_signal_generated",
        f"{instrument} mechanical OCO signal generated",
        instrument=instrument,
        broker_symbol=symbol,
        asian_high=high,
        asian_low=low,
        range=height,
        buffer=buffer,
        stop_mode=strategy.stop_mode,
        rr=strategy.rr,
        risk_pct=live_risk_pct,
        risk_cash=risk_cash,
    )
    receipts: list[dict[str, object]] = []
    for request in requests:
        direction = "BUY" if request["type"] == mt5.ORDER_TYPE_BUY_STOP else "SELL"
        log_event(
            LOGGER,
            logging.INFO,
            "pending_signal",
            f"{instrument} {direction}_STOP prepared",
            instrument=instrument,
            broker_symbol=symbol,
            direction=direction,
            order_type=f"{direction}_STOP",
            volume=request["volume"],
            entry=request["price"],
            stop=request["sl"],
            target=request["tp"],
            expiration=expiration,
            risk_pct=live_risk_pct,
            risk_cash=risk_cash,
        )
        check = mt5.order_check(request)
        if check is None or check.retcode != 0:
            log_event(
                LOGGER,
                logging.ERROR,
                "order_check_failed",
                f"{instrument} {direction}_STOP failed MT5 validation",
                instrument=instrument,
                broker_symbol=symbol,
                request=request,
                check=check,
                error=mt5.last_error(),
            )
            raise MT5Error(f"Order check failed for {symbol}: {check}")
        log_event(
            LOGGER,
            logging.INFO,
            "order_check_passed",
            f"{instrument} {direction}_STOP passed MT5 validation",
            instrument=instrument,
            broker_symbol=symbol,
            margin=getattr(check, "margin", None),
            free_margin=getattr(check, "margin_free", None),
        )
        if config.dry_run or not config.enable_trading:
            receipt = {
                "instrument": instrument,
                "status": "DRY_RUN",
                "risk_cash": risk_cash,
                **request,
            }
            receipts.append(receipt)
            log_event(
                LOGGER,
                logging.INFO,
                "order_dry_run",
                f"{instrument} {direction}_STOP displayed but not sent",
                **receipt,
            )
            continue
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            log_event(
                LOGGER,
                logging.ERROR,
                "order_send_failed",
                f"{instrument} {direction}_STOP was rejected",
                instrument=instrument,
                broker_symbol=symbol,
                request=request,
                result=result,
                error=mt5.last_error(),
            )
            raise MT5Error(f"Order send failed for {symbol}: {result}")
        receipt = {
            "instrument": instrument,
            "status": "PLACED",
            "risk_cash": risk_cash,
            **request,
            **result._asdict(),
        }
        receipts.append(receipt)
        log_event(
            LOGGER,
            logging.INFO,
            "order_placed",
            f"{instrument} {direction}_STOP placed",
            instrument=instrument,
            broker_symbol=symbol,
            ticket=getattr(result, "order", None),
            volume=request["volume"],
            entry=request["price"],
            stop=request["sl"],
            target=request["tp"],
        )
    return receipts


def _strategy_board(
    config: AppConfig,
    symbol_map: dict[str, str],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for instrument, symbol in symbol_map.items():
        strategy = config.strategy_for(instrument)
        if strategy.entry_mode == "mechanical_oco":
            execution = "BUY_STOP + SELL_STOP"
            status = (
                "DRY_RUN"
                if config.dry_run or not config.enable_trading
                else "AUTO"
            )
        elif strategy.entry_mode == "confirmed_close":
            execution = "MARKET AFTER M15 CLOSE"
            status = (
                "DRY_RUN"
                if config.dry_run or not config.enable_trading
                else "AUTO"
            )
        else:
            execution = "MARKET AFTER RETEST"
            status = (
                "DRY_RUN"
                if config.dry_run or not config.enable_trading
                else "AUTO"
            )
        exit_rule = (
            f"{strategy.rr:g}R fixed"
            if strategy.exit_mode == "fixed"
            else (
                f"{strategy.rr:g}R cap; trail "
                f"{strategy.trail_start_r:g}/{strategy.trail_distance_r:g}R"
            )
        )
        rows.append(
            {
                "instrument": instrument,
                "broker": symbol,
                "setup": strategy.entry_mode,
                "execution": execution,
                "exit": exit_rule,
                "risk": f"{strategy.risk_pct:g}%",
                "status": status,
            }
        )
    return rows


def _account_board(account: object) -> str:
    trade_mode = int(getattr(account, "trade_mode", -1))
    mode_names = {
        int(mt5.ACCOUNT_TRADE_MODE_DEMO): "DEMO",
        int(mt5.ACCOUNT_TRADE_MODE_CONTEST): "CONTEST",
        int(mt5.ACCOUNT_TRADE_MODE_REAL): "LIVE",
    }
    row = {
        "account": getattr(account, "login", "unknown"),
        "type": mode_names.get(trade_mode, "UNKNOWN"),
        "server": getattr(account, "server", "unknown"),
        "currency": getattr(account, "currency", "unknown"),
        "leverage": f"1:{getattr(account, 'leverage', 0)}",
        "balance": f"{float(getattr(account, 'balance', 0.0)):,.2f}",
        "equity": f"{float(getattr(account, 'equity', 0.0)):,.2f}",
        "free_margin": f"{float(getattr(account, 'margin_free', 0.0)):,.2f}",
        "floating_pnl": f"{float(getattr(account, 'profit', 0.0)):,.2f}",
        "trade_allowed": (
            "YES" if bool(getattr(account, "trade_allowed", False)) else "NO"
        ),
    }
    return render_table(
        [row],
        (
            "account",
            "type",
            "server",
            "currency",
            "leverage",
            "balance",
            "equity",
            "free_margin",
            "floating_pnl",
            "trade_allowed",
        ),
    )


def _order_board(receipts: list[dict[str, object]]) -> str:
    rows: list[dict[str, object]] = []
    for receipt in receipts:
        buy = receipt["type"] == mt5.ORDER_TYPE_BUY_STOP
        rows.append(
            {
                "instrument": receipt["instrument"],
                "order": "BUY_STOP" if buy else "SELL_STOP",
                "volume": receipt["volume"],
                "entry": receipt["price"],
                "sl": receipt["sl"],
                "tp": receipt["tp"],
                "risk_cash": f"${float(receipt['risk_cash']):.2f}",
                "status": receipt["status"],
            }
        )
    return render_table(
        rows,
        (
            "instrument",
            "order",
            "volume",
            "entry",
            "sl",
            "tp",
            "risk_cash",
            "status",
        ),
    )


def _recent_adr(symbol: str, now: datetime, days: int) -> float | None:
    today = datetime.combine(now.date(), datetime.min.time(), tzinfo=timezone.utc)
    rates = mt5.copy_rates_range(
        symbol,
        mt5.TIMEFRAME_D1,
        today - timedelta(days=max(days * 3, 30)),
        today - timedelta(seconds=1),
    )
    if rates is None or len(rates) < days:
        return None
    frame = pd.DataFrame(rates).tail(days)
    return float((frame["high"] - frame["low"]).mean())


def _current_confirmation_signal(
    config: AppConfig,
    instrument: str,
    symbol: str,
    now: datetime,
) -> tuple[EntrySignal, dict[str, object]] | None:
    strategy = config.strategy_for(instrument)
    if strategy.entry_mode not in {"confirmed_close", "close_retest"}:
        return None
    day_start = datetime.combine(
        now.date(),
        datetime.min.time(),
        tzinfo=timezone.utc,
    )
    closed_slot = now.replace(
        minute=(now.minute // 15) * 15,
        second=0,
        microsecond=0,
    )
    if closed_slot <= day_start:
        return None
    frame = fetch_m1(symbol, day_start, closed_slot - timedelta(seconds=1))
    asia_start = datetime.combine(
        now.date(),
        strategy.asia_start,
        tzinfo=timezone.utc,
    )
    asia_end = datetime.combine(
        now.date(),
        strategy.asia_end,
        tzinfo=timezone.utc,
    )
    asia = frame[(frame["time"] >= asia_start) & (frame["time"] < asia_end)]
    if len(asia) < 60:
        return None
    high = float(asia["high"].max())
    low = float(asia["low"].min())
    asian_range = high - low
    adr = _recent_adr(symbol, now, strategy.adr_days)
    if adr is None or adr <= 0:
        return None
    range_fraction = asian_range / adr
    if not (
        strategy.min_range_adr_fraction
        <= range_fraction
        <= strategy.max_range_adr_fraction
    ):
        log_event(
            LOGGER,
            logging.INFO,
            "signal_filtered_range_quality",
            f"{instrument} Asian range failed its ADR filter",
            instrument=instrument,
            broker_symbol=symbol,
            asian_range=asian_range,
            adr=adr,
            range_adr_fraction=range_fraction,
            minimum=strategy.min_range_adr_fraction,
            maximum=strategy.max_range_adr_fraction,
        )
        return None
    point = float(symbol_metadata(symbol)["point"])
    signal = find_entry_signal(frame, strategy, high, low, point)
    if signal is None:
        return None
    account = mt5.account_info()
    live_risk_pct = effective_live_risk_pct(config, strategy, now)
    risk_cash = (
        float(account.balance) * live_risk_pct / 100.0
        if account is not None
        else 0.0
    )
    volume = volume_for_risk(
        symbol,
        signal.direction,
        signal.entry,
        signal.stop,
        risk_cash,
    )
    order_type = mt5.ORDER_TYPE_BUY if signal.direction == "buy" else mt5.ORDER_TYPE_SELL
    one_lot_risk = mt5.order_calc_profit(
        order_type, symbol, 1.0, signal.entry, signal.stop
    )
    planned_risk_cash = (
        abs(float(one_lot_risk)) * volume if one_lot_risk is not None else risk_cash
    )
    actual_risk_pct = (
        planned_risk_cash / float(account.balance) * 100.0
        if account is not None and float(account.balance) > 0
        else live_risk_pct
    )
    details: dict[str, object] = {
        "instrument": instrument,
        "broker_symbol": symbol,
        "direction": signal.direction.upper(),
        "execution": "MARKET_AUTO",
        "volume": volume,
        "entry": signal.entry,
        "stop": signal.stop,
        "target": signal.target,
        "rr": strategy.rr,
        "risk_pct": max(live_risk_pct, actual_risk_pct),
        "risk_cash": planned_risk_cash,
        "asian_high": high,
        "asian_low": low,
        "asian_range": asian_range,
        "adr": adr,
        "range_adr_fraction": range_fraction,
        "signal_time": signal.time,
        "status": (
            "DRY_RUN"
            if config.dry_run or not config.enable_trading
            else "AUTO_READY"
        ),
    }
    return signal, details


def _confirmation_board(details: dict[str, object]) -> str:
    row = {
        "instrument": details["instrument"],
        "side": details["direction"],
        "execution": details["execution"],
        "volume": details["volume"],
        "entry": round(float(details["entry"]), 6),
        "sl": round(float(details["stop"]), 6),
        "tp": round(float(details["target"]), 6),
        "rr": details["rr"],
        "risk_cash": f"${float(details['risk_cash']):.2f}",
        "status": details["status"],
    }
    return render_table(
        [row],
        (
            "instrument",
            "side",
            "execution",
            "volume",
            "entry",
            "sl",
            "tp",
            "rr",
            "risk_cash",
            "status",
        ),
    )


def has_strategy_exposure(config: AppConfig, symbol: str) -> bool:
    positions = mt5.positions_get(symbol=symbol) or ()
    orders = mt5.orders_get(symbol=symbol) or ()
    return any(int(item.magic) == config.magic for item in (*positions, *orders))


def has_traded_today(config: AppConfig, symbol: str, now: datetime) -> bool:
    start = datetime.combine(now.date(), datetime.min.time(), tzinfo=timezone.utc)
    deals = mt5.history_deals_get(start, now) or ()
    return any(
        int(deal.magic) == config.magic
        and deal.symbol == symbol
        and int(deal.entry) in {mt5.DEAL_ENTRY_IN, mt5.DEAL_ENTRY_INOUT}
        for deal in deals
    )


def strategy_exposure_risk_pct(config: AppConfig) -> float:
    positions = mt5.positions_get() or ()
    orders = mt5.orders_get() or ()
    symbols = {
        item.symbol
        for item in (*positions, *orders)
        if int(item.magic) == config.magic
    }
    # MT5 does not retain the strategy's original percentage. Reserve the
    # configured per-trade safety cap while progression is active.
    return sum(
        (
            config.strategy_for(symbol).max_live_risk_pct
            if config.strategy_for(symbol).risk_progression_enabled
            else config.strategy_for(symbol).risk_pct
        )
        for symbol in symbols
    )


def trailing_stop_candidate(
    direction: str,
    entry: float,
    original_stop: float,
    current_stop: float,
    closed_price: float,
    trail_start_r: float,
    trail_distance_r: float,
) -> float | None:
    risk = abs(entry - original_stop)
    if risk <= 0:
        return None
    if direction == "buy":
        if closed_price < entry + trail_start_r * risk:
            return None
        candidate = closed_price - trail_distance_r * risk
        return candidate if candidate > current_stop else None
    if closed_price > entry - trail_start_r * risk:
        return None
    candidate = closed_price + trail_distance_r * risk
    return candidate if current_stop <= 0 or candidate < current_stop else None


def manage_trailing_stops(
    config: AppConfig,
    symbol_map: dict[str, str],
) -> int:
    positions = mt5.positions_get() or ()
    instrument_by_symbol = {
        broker_symbol: instrument
        for instrument, broker_symbol in symbol_map.items()
    }
    modified = 0
    for position in positions:
        if int(position.magic) != config.magic:
            continue
        instrument = instrument_by_symbol.get(position.symbol)
        if instrument is None:
            continue
        strategy = config.strategy_for(instrument)
        if strategy.exit_mode != "trailing" or float(position.tp) <= 0:
            continue
        rates = mt5.copy_rates_from_pos(position.symbol, mt5.TIMEFRAME_M1, 1, 1)
        if rates is None or len(rates) != 1:
            continue
        closed_price = float(rates[0]["close"])
        direction = (
            "buy" if int(position.type) == mt5.POSITION_TYPE_BUY else "sell"
        )
        entry = float(position.price_open)
        original_risk = abs(float(position.tp) - entry) / strategy.rr
        original_stop = (
            entry - original_risk if direction == "buy" else entry + original_risk
        )
        candidate = trailing_stop_candidate(
            direction,
            entry,
            original_stop,
            float(position.sl),
            closed_price,
            strategy.trail_start_r,
            strategy.trail_distance_r,
        )
        if candidate is None:
            continue
        info = mt5.symbol_info(position.symbol)
        tick = mt5.symbol_info_tick(position.symbol)
        if info is None or tick is None:
            continue
        minimum_distance = float(info.trade_stops_level) * float(info.point)
        if direction == "buy":
            candidate = min(candidate, float(tick.bid) - minimum_distance)
            if candidate <= float(position.sl):
                continue
        else:
            candidate = max(candidate, float(tick.ask) + minimum_distance)
            if float(position.sl) > 0 and candidate >= float(position.sl):
                continue
        candidate = round(candidate, int(info.digits))
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": int(position.ticket),
            "symbol": position.symbol,
            "sl": candidate,
            "tp": float(position.tp),
            "magic": config.magic,
        }
        if config.dry_run or not config.enable_trading:
            log_event(
                LOGGER,
                logging.INFO,
                "trailing_stop_dry_run",
                f"{instrument} trailing stop prepared but not sent",
                instrument=instrument,
                broker_symbol=position.symbol,
                ticket=int(position.ticket),
                old_stop=float(position.sl),
                new_stop=candidate,
                closed_m1=closed_price,
            )
            continue
        result = mt5.order_send(request)
        if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
            modified += 1
            log_event(
                LOGGER,
                logging.INFO,
                "trailing_stop_modified",
                f"{instrument} trailing stop advanced",
                instrument=instrument,
                broker_symbol=position.symbol,
                ticket=int(position.ticket),
                old_stop=float(position.sl),
                new_stop=candidate,
                closed_m1=closed_price,
            )
        else:
            log_event(
                LOGGER,
                logging.ERROR,
                "trailing_stop_modify_failed",
                f"{instrument} trailing stop modification failed",
                instrument=instrument,
                broker_symbol=position.symbol,
                ticket=int(position.ticket),
                requested_stop=candidate,
                result=result,
                error=mt5.last_error(),
            )
    return modified


def cancel_oco_siblings(config: AppConfig) -> int:
    positions = mt5.positions_get()
    orders = mt5.orders_get()
    if positions is None or orders is None:
        return 0
    active_symbols = {
        position.symbol for position in positions if int(position.magic) == config.magic
    }
    cancelled = 0
    for order in orders:
        if int(order.magic) != config.magic or order.symbol not in active_symbols:
            continue
        result = mt5.order_send(
            {"action": mt5.TRADE_ACTION_REMOVE, "order": int(order.ticket)}
        )
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            cancelled += 1
            log_event(
                LOGGER,
                logging.INFO,
                "oco_sibling_cancelled",
                f"Cancelled sibling pending order {order.ticket}",
                symbol=order.symbol,
                ticket=int(order.ticket),
            )
    return cancelled


def run_live(config: AppConfig, once: bool = False, poll_seconds: int = 5) -> None:
    with mt5_connection(config):
        account = mt5.account_info()
        if account is None:
            raise MT5Error(f"No connected MT5 account: {mt5.last_error()}")
        symbol_map = discover_symbols(config.symbols)
        board = _strategy_board(config, symbol_map)
        print(
            "\nMT5 CONNECTED ACCOUNT\n"
            + _account_board(account)
            + "\n\nASIAN BREAKOUT - LIVE STRATEGY BOARD\n"
            + render_table(
                board,
                (
                    "instrument",
                    "broker",
                    "setup",
                    "execution",
                    "exit",
                    "risk",
                    "status",
                ),
            )
            + "\n"
        )
        log_event(
            LOGGER,
            logging.INFO,
            "live_started",
            "Live monitor started",
            symbols=symbol_map,
            trading_enabled=config.enable_trading,
            dry_run=config.dry_run,
            basket_risk_cap_pct=config.max_basket_risk_pct,
        )
        last_heartbeat: datetime | None = None
        last_confirmation_slot: dict[str, datetime] = {}
        displayed_signals: set[tuple[str, str]] = set()
        while True:
            now = datetime.now(timezone.utc)
            cancelled = cancel_oco_siblings(config)
            if cancelled:
                LOGGER.info("Cancelled %d OCO sibling order(s)", cancelled)
            trailed = manage_trailing_stops(config, symbol_map)
            if trailed:
                LOGGER.info("Advanced %d trailing stop(s)", trailed)
            if last_heartbeat is None or now - last_heartbeat >= timedelta(minutes=1):
                log_event(
                    LOGGER,
                    logging.INFO,
                    "monitor_heartbeat",
                    "Live monitor heartbeat",
                    utc_time=now,
                    strategy_exposure_risk_pct=strategy_exposure_risk_pct(config),
                    basket_risk_cap_pct=config.max_basket_risk_pct,
                )
                last_heartbeat = now
            setup_time = datetime.combine(
                now.date(), config.strategy.asia_end, tzinfo=timezone.utc
            )
            cutoff_time = datetime.combine(
                now.date(), config.strategy.entry_cutoff, tzinfo=timezone.utc
            )
            if setup_time <= now < cutoff_time:
                slot = now.replace(
                    minute=(now.minute // 15) * 15,
                    second=0,
                    microsecond=0,
                )
                for instrument, symbol in symbol_map.items():
                    strategy = config.strategy_for(instrument)
                    if strategy.entry_mode == "mechanical_oco":
                        continue
                    if last_confirmation_slot.get(instrument) == slot:
                        continue
                    last_confirmation_slot[instrument] = slot
                    try:
                        detected = _current_confirmation_signal(
                            config,
                            instrument,
                            symbol,
                            now,
                        )
                    except MarketDataUnavailable:
                        log_event(
                            LOGGER,
                            logging.INFO,
                            "market_data_unavailable",
                            (
                                f"{instrument} waiting: market closed or no fresh "
                                "M1 bars"
                            ),
                            instrument=instrument,
                            broker_symbol=symbol,
                            utc_time=now,
                        )
                        continue
                    except Exception:
                        LOGGER.exception(
                            "Failed to scan confirmation signal for %s (%s)",
                            instrument,
                            symbol,
                            extra={
                                "event_name": "confirmation_scan_failed",
                                "event_data": {
                                    "instrument": instrument,
                                    "broker_symbol": symbol,
                                },
                            },
                        )
                        continue
                    if detected is None:
                        continue
                    signal, details = detected
                    expected_signal_slot = slot - timedelta(minutes=15)
                    if signal.time < pd.Timestamp(expected_signal_slot):
                        log_event(
                            LOGGER,
                            logging.INFO,
                            "stale_confirmation_ignored",
                            f"Ignoring stale confirmation for {instrument}",
                            instrument=instrument,
                            broker_symbol=symbol,
                            signal_time=signal.time,
                            expected_signal_slot=expected_signal_slot,
                        )
                        continue
                    signal_key = (instrument, signal.time.isoformat())
                    if signal_key in displayed_signals:
                        continue
                    displayed_signals.add(signal_key)
                    log_event(
                        LOGGER,
                        logging.WARNING,
                        "confirmed_trade_signal",
                        (
                            f"{instrument} {signal.direction.upper()} "
                            f"{strategy.entry_mode} signal confirmed"
                        ),
                        **details,
                    )
                    print(
                        f"\nCONFIRMED TRADE SIGNAL - {now:%Y-%m-%d %H:%M UTC}\n"
                        + _confirmation_board(details)
                        + "\n"
                    )
                    if has_strategy_exposure(config, symbol):
                        log_event(
                            LOGGER,
                            logging.INFO,
                            "confirmed_signal_skipped_existing_exposure",
                            f"Skipping {instrument}: exposure already exists",
                            instrument=instrument,
                            broker_symbol=symbol,
                        )
                        continue
                    if has_traded_today(config, symbol, now):
                        log_event(
                            LOGGER,
                            logging.INFO,
                            "confirmed_signal_skipped_daily_limit",
                            f"Skipping {instrument}: already traded today",
                            instrument=instrument,
                            broker_symbol=symbol,
                        )
                        continue
                    current_risk = strategy_exposure_risk_pct(config)
                    proposed_risk = float(details["risk_pct"])
                    if current_risk + proposed_risk > config.max_basket_risk_pct:
                        log_event(
                            LOGGER,
                            logging.WARNING,
                            "confirmed_signal_blocked_risk_cap",
                            f"Skipping {instrument}: basket risk cap reached",
                            instrument=instrument,
                            broker_symbol=symbol,
                            basket_risk_cap_pct=config.max_basket_risk_pct,
                            current_risk_pct=current_risk,
                            proposed_risk_pct=proposed_risk,
                        )
                        continue
                    try:
                        with selected_xau_entry_guard(proposed_risk) as decision:
                            if not decision.allowed:
                                log_event(
                                    LOGGER,
                                    logging.WARNING,
                                    "confirmed_signal_blocked_shared_xau_cap",
                                    f"Skipping {instrument}: shared XAU risk cap reached",
                                    instrument=instrument,
                                    broker_symbol=symbol,
                                    current_risk_pct=decision.current_risk_pct,
                                    proposed_risk_pct=decision.proposed_risk_pct,
                                    shared_cap_pct=decision.cap_risk_pct,
                                )
                                continue
                            receipt = place_confirmation_market(
                                config,
                                instrument,
                                symbol,
                                signal,
                            )
                            details["status"] = receipt["status"]
                    except Exception:
                        LOGGER.exception(
                            "Failed to place confirmed signal for %s (%s)",
                            instrument,
                            symbol,
                            extra={
                                "event_name": "confirmed_order_failed",
                                "event_data": {
                                    "instrument": instrument,
                                    "broker_symbol": symbol,
                                },
                            },
                        )
            if setup_time <= now < setup_time + timedelta(minutes=1):
                for instrument, symbol in symbol_map.items():
                    if has_strategy_exposure(config, symbol):
                        log_event(
                            LOGGER,
                            logging.INFO,
                            "signal_skipped_existing_exposure",
                            f"Skipping {instrument}: strategy exposure already exists",
                            instrument=instrument,
                            broker_symbol=symbol,
                        )
                        continue
                    strategy = config.strategy_for(instrument)
                    if strategy.entry_mode != "mechanical_oco":
                        log_event(
                            LOGGER,
                            logging.INFO,
                            "signal_display_only",
                            f"{instrument} is waiting for {strategy.entry_mode}",
                            instrument=instrument,
                            broker_symbol=symbol,
                            entry_mode=strategy.entry_mode,
                            execution="market_after_confirmation",
                        )
                        continue
                    proposed_risk = effective_live_risk_pct(config, strategy, now)
                    if (
                        strategy_exposure_risk_pct(config) + proposed_risk
                        > config.max_basket_risk_pct
                    ):
                        log_event(
                            LOGGER,
                            logging.WARNING,
                            "signal_blocked_risk_cap",
                            f"Skipping {instrument}: basket risk cap reached",
                            instrument=instrument,
                            broker_symbol=symbol,
                            basket_risk_cap_pct=config.max_basket_risk_pct,
                            current_risk_pct=strategy_exposure_risk_pct(config),
                            proposed_risk_pct=proposed_risk,
                        )
                        continue
                    try:
                        receipts = place_mechanical_oco(
                            config,
                            instrument,
                            symbol,
                            now,
                        )
                        print(
                            f"\nTRADE SIGNALS — {now:%Y-%m-%d %H:%M UTC}\n"
                            + _order_board(receipts)
                            + "\n"
                        )
                    except Exception:
                        LOGGER.exception(
                            "Failed to prepare/place signal for %s (%s)",
                            instrument,
                            symbol,
                            extra={
                                "event_name": "signal_processing_failed",
                                "event_data": {
                                    "instrument": instrument,
                                    "broker_symbol": symbol,
                                },
                            },
                        )
            if once:
                log_event(
                    LOGGER,
                    logging.INFO,
                    "live_stopped",
                    "One-cycle live monitor completed",
                )
                return
            time_module.sleep(poll_seconds)
