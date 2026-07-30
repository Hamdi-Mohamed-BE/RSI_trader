from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import math
import time as clock

import MetaTrader5 as mt5
import pandas as pd

from .article_engine import (
    Candidate,
    article_candidates_for_day,
    params_from_config,
)
from .config import Config
from .engine import ask, combine, regime_states
from .mt5_data import connection, discover_symbols, load_m1, MT5Error


UTC = timezone.utc
COMMENT_PREFIX = "AMD"


@dataclass(frozen=True, slots=True)
class PendingSignal:
    session_date: date
    side: str
    signal_time: datetime
    entry: float
    stop: float
    target: float
    risk: float
    asia_high: float
    asia_low: float


@dataclass(frozen=True, slots=True)
class ArticleSignal:
    session_date: date
    phase: str
    side: str
    signal_time: datetime
    stop: float
    rr: float
    asia_high: float
    asia_low: float


def _round_price(value: float, digits: int) -> float:
    return round(float(value), int(digits))


def _volume_digits(step: float) -> int:
    text = f"{step:.10f}".rstrip("0")
    return len(text.split(".")[1]) if "." in text else 0


def calculate_risk_volume(
    symbol: str,
    side: str,
    entry: float,
    stop: float,
    equity: float,
    risk_pct: float,
) -> tuple[float, float, float]:
    """Return volume, planned cash risk and allowed cash risk.

    Volume is always rounded down to the broker step. If the broker minimum
    lot would exceed the configured risk, volume is returned as zero.
    """
    info = mt5.symbol_info(symbol)
    if info is None:
        raise MT5Error(f"Cannot read symbol details for {symbol}")
    allowed = max(float(equity), 0.0) * float(risk_pct) / 100.0
    order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
    one_lot = mt5.order_calc_profit(order_type, symbol, 1.0, entry, stop)
    if one_lot is None or abs(float(one_lot)) <= 0 or allowed <= 0:
        return 0.0, 0.0, allowed
    loss_per_lot = abs(float(one_lot))
    raw = allowed / loss_per_lot
    step = float(info.volume_step)
    minimum = float(info.volume_min)
    maximum = float(info.volume_max)
    if step <= 0 or raw + 1e-12 < minimum:
        return 0.0, 0.0, allowed
    steps = math.floor((raw + 1e-12) / step)
    volume = min(steps * step, maximum)
    volume = round(volume, _volume_digits(step))
    planned = loss_per_lot * volume
    if volume < minimum or planned > allowed * 1.001:
        return 0.0, planned, allowed
    return volume, planned, allowed


def _filling_candidates() -> tuple[int, ...]:
    # Brokers encode supported filling modes differently. Validate each mode
    # with order_check and use the first accepted one.
    return (
        mt5.ORDER_FILLING_RETURN,
        mt5.ORDER_FILLING_IOC,
        mt5.ORDER_FILLING_FOK,
    )


def _checked_send(
    base_request: dict[str, object],
    *,
    try_fillings: bool = True,
) -> object:
    if not try_fillings:
        result = mt5.order_send(base_request)
        if result is not None and int(result.retcode) in {
            mt5.TRADE_RETCODE_DONE,
            mt5.TRADE_RETCODE_PLACED,
            mt5.TRADE_RETCODE_DONE_PARTIAL,
        }:
            return result
        raise MT5Error(
            "Order operation rejected: "
            f"{getattr(result, 'retcode', None)} "
            f"{getattr(result, 'comment', mt5.last_error())}"
        )
    failures: list[str] = []
    fillings = _filling_candidates()
    for filling in fillings:
        request = dict(base_request)
        if filling is not None:
            request["type_filling"] = filling
        check = mt5.order_check(request)
        if check is None:
            failures.append(f"check=None last_error={mt5.last_error()}")
            continue
        if int(check.retcode) not in {
            0,
            mt5.TRADE_RETCODE_DONE,
            mt5.TRADE_RETCODE_PLACED,
        }:
            failures.append(
                f"fill={filling} check={check.retcode} {check.comment}"
            )
            continue
        result = mt5.order_send(request)
        if result is not None and int(result.retcode) in {
            mt5.TRADE_RETCODE_DONE,
            mt5.TRADE_RETCODE_PLACED,
            mt5.TRADE_RETCODE_DONE_PARTIAL,
        }:
            return result
        failures.append(
            f"fill={filling} send="
            f"{getattr(result, 'retcode', None)} "
            f"{getattr(result, 'comment', mt5.last_error())}"
        )
    raise MT5Error("Order rejected: " + " | ".join(failures))


def build_pending_signal(
    frame: pd.DataFrame,
    point: float,
    config: Config,
    now: datetime,
) -> tuple[PendingSignal | None, str]:
    if config.ny_entry_mode != "stop_only":
        return None, "live execution supports the validated stop_only mode"
    day = now.date()
    if config.regime_filter_enabled:
        regime = regime_states(frame, config).get(day)
        if regime is None:
            return None, "regime history incomplete"
        if not regime.allowed:
            return None, regime.reason
    asia_start = combine(day, config.asia_start)
    asia_end = combine(day, config.asia_end)
    london_start = combine(day, config.london_start)
    london_end = combine(day, config.london_end)
    ny_start = combine(day, config.ny_start)
    signal_time = ny_start + timedelta(minutes=config.ny_fallback_minutes)
    cutoff = combine(day, config.ny_cutoff)
    if now < signal_time:
        return None, f"waiting for {signal_time:%H:%M} UTC"
    if now >= cutoff:
        return None, "New York entry cutoff passed"
    asia = frame.loc[
        (frame["time"] >= asia_start) & (frame["time"] < asia_end)
    ]
    london = frame.loc[
        (frame["time"] >= london_start) & (frame["time"] < london_end)
    ]
    observed = frame.loc[
        (frame["time"] >= ny_start) & (frame["time"] < signal_time)
    ]
    if len(asia) < 120 or len(london) < 30:
        return None, "Asia/London session data incomplete"
    if len(observed) < max(config.ny_fallback_minutes // 2, 10):
        return None, "New York observation window incomplete"
    asia_high = float(asia["high"].max())
    asia_low = float(asia["low"].min())
    asia_range = asia_high - asia_low
    london_close = float(london.iloc[-1]["close"])
    if london_close > asia_high:
        side = "sell"
    elif london_close < asia_low:
        side = "buy"
    else:
        return None, "London close stayed inside the Asia range"
    median_spread = max(
        float(observed["spread"].median()) * point,
        point,
    )
    stop_buffer = max(
        asia_range * config.ny_stop_buffer_fraction,
        median_spread * 2.0,
    )
    entry_buffer = max(
        median_spread * config.ny_entry_buffer_spreads,
        point,
    )
    range_high = float(observed["high"].max())
    range_low = float(observed["low"].min())
    if side == "buy":
        entry = range_high + entry_buffer
        stop = range_low - stop_buffer
        risk = entry - stop
        target = entry + config.ny_fallback_rr * risk
    else:
        entry = range_low - entry_buffer
        stop = range_high + stop_buffer
        risk = stop - entry
        target = entry - config.ny_fallback_rr * risk
    if risk <= median_spread:
        return None, "calculated stop distance is too small"
    # Never chase a stop entry that was already crossed while the bot was off.
    after_signal = frame.loc[
        (frame["time"] >= signal_time) & (frame["time"] < now)
    ]
    if side == "buy" and not after_signal.empty:
        crossed = any(
            ask(row, "high", point) >= entry
            for _, row in after_signal.iterrows()
        )
        if crossed:
            return None, "buy-stop trigger already crossed; stale signal"
    if side == "sell" and not after_signal.empty:
        if float(after_signal["low"].min()) <= entry:
            return None, "sell-stop trigger already crossed; stale signal"
    return (
        PendingSignal(
            session_date=day,
            side=side,
            signal_time=signal_time,
            entry=entry,
            stop=stop,
            target=target,
            risk=risk,
            asia_high=asia_high,
            asia_low=asia_low,
        ),
        "ready",
    )


def build_article_signal(
    frame: pd.DataFrame,
    point: float,
    config: Config,
    now: datetime,
) -> tuple[ArticleSignal | None, str]:
    """Return a fresh, confirmed article-model signal for live execution."""
    day = now.date()
    source = frame.loc[frame["time"] <= now].copy()
    if source.empty:
        return None, "M1 history unavailable"
    if config.regime_filter_enabled:
        regime = regime_states(source, config).get(day)
        if regime is None:
            return None, "regime history incomplete"
        if not regime.allowed:
            return None, regime.reason
    # Keep the current M1 row: its open is the executable next-bar reference
    # immediately after a completed M5 signal. An unfinished M5 bar cannot
    # qualify because its computed end_time is still in the future.
    day_frame = source.loc[source["time"].dt.date == day].reset_index(
        drop=True
    )
    candidates, asia_high, asia_low = article_candidates_for_day(
        day_frame,
        point,
        config,
        params_from_config(config),
        day,
    )
    if not candidates:
        return None, "waiting for confirmed AMD sweep/retest"
    candidate: Candidate = candidates[0]
    age = (now - candidate.signal_time).total_seconds()
    if age < 0:
        return None, f"waiting for M5 close at {candidate.signal_time:%H:%M} UTC"
    if age > config.article_signal_max_age_seconds:
        return None, (
            f"confirmed {candidate.phase} signal is stale "
            f"({int(age)}s old)"
        )
    rr = (
        config.article_fade_rr
        if candidate.phase.endswith("_fade")
        else config.article_distribution_rr
    )
    return (
        ArticleSignal(
            session_date=day,
            phase=candidate.phase,
            side=candidate.side,
            signal_time=candidate.signal_time,
            stop=candidate.stop,
            rr=rr,
            asia_high=asia_high,
            asia_low=asia_low,
        ),
        "ready",
    )


def _bot_orders(symbol: str) -> list[object]:
    return [
        order
        for order in (mt5.orders_get(symbol=symbol) or ())
        if int(order.magic) == int(_active_config.magic)
    ]


def _bot_positions(symbol: str) -> list[object]:
    return [
        position
        for position in (mt5.positions_get(symbol=symbol) or ())
        if int(position.magic) == int(_active_config.magic)
    ]


def _has_traded_today(symbol: str, day_start: datetime, now: datetime) -> bool:
    if _bot_orders(symbol) or _bot_positions(symbol):
        return True
    historical_orders = mt5.history_orders_get(day_start, now) or ()
    if any(
        order.symbol == symbol
        and int(order.magic) == int(_active_config.magic)
        for order in historical_orders
    ):
        return True
    deals = mt5.history_deals_get(day_start, now) or ()
    return any(
        deal.symbol == symbol
        and int(deal.magic) == int(_active_config.magic)
        for deal in deals
    )


def place_pending(
    symbol: str,
    signal: PendingSignal,
    account: object,
    config: Config,
) -> object:
    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if info is None or tick is None:
        raise MT5Error(f"No live quote for {symbol}")
    digits = int(info.digits)
    point = float(info.point)
    min_distance = max(float(info.trade_stops_level) * point, point)
    entry = _round_price(signal.entry, digits)
    stop = _round_price(signal.stop, digits)
    target = _round_price(signal.target, digits)
    if signal.side == "buy" and entry <= float(tick.ask) + min_distance:
        raise MT5Error("Buy-stop entry is no longer above the live ask")
    if signal.side == "sell" and entry >= float(tick.bid) - min_distance:
        raise MT5Error("Sell-stop entry is no longer below the live bid")
    volume, planned, allowed = calculate_risk_volume(
        symbol,
        signal.side,
        entry,
        stop,
        float(account.equity),
        config.risk_pct,
    )
    if volume <= 0:
        raise MT5Error(
            f"Broker minimum lot exceeds risk cap: allowed ${allowed:.2f}, "
            f"minimum-lot risk ${planned:.2f}"
        )
    order_type = (
        mt5.ORDER_TYPE_BUY_STOP
        if signal.side == "buy"
        else mt5.ORDER_TYPE_SELL_STOP
    )
    comment = (
        f"{COMMENT_PREFIX} "
        f"{'B' if signal.side == 'buy' else 'S'} "
        f"{signal.session_date:%Y%m%d}"
    )
    request: dict[str, object] = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": entry,
        "sl": stop,
        "tp": target,
        "deviation": config.deviation_points,
        "magic": config.magic,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
    }
    result = _checked_send(request)
    print(
        f"  LIVE ORDER PLACED {symbol} {signal.side.upper()} STOP "
        f"ticket={result.order} volume={volume} entry={entry} "
        f"SL={stop} TP={target} risk=${planned:.2f}/{allowed:.2f}"
    )
    return result


def place_article_market(
    symbol: str,
    signal: ArticleSignal,
    account: object,
    config: Config,
) -> object:
    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if info is None or tick is None:
        raise MT5Error(f"No live quote for {symbol}")
    digits = int(info.digits)
    point = float(info.point)
    min_distance = max(float(info.trade_stops_level) * point, point)
    is_buy = signal.side == "buy"
    entry = _round_price(float(tick.ask if is_buy else tick.bid), digits)
    stop = _round_price(signal.stop, digits)
    if is_buy and stop >= entry - min_distance:
        raise MT5Error("Confirmed buy no longer has a valid structural stop")
    if not is_buy and stop <= entry + min_distance:
        raise MT5Error("Confirmed sell no longer has a valid structural stop")
    risk = abs(entry - stop)
    target = _round_price(
        entry + signal.rr * risk if is_buy else entry - signal.rr * risk,
        digits,
    )
    volume, planned, allowed = calculate_risk_volume(
        symbol,
        signal.side,
        entry,
        stop,
        float(account.equity),
        config.risk_pct,
    )
    if volume <= 0:
        raise MT5Error(
            f"Broker minimum lot exceeds risk cap: allowed ${allowed:.2f}, "
            f"minimum-lot risk ${planned:.2f}"
        )
    phase_code = "AF" if signal.phase.endswith("_fade") else "AD"
    request: dict[str, object] = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL,
        "price": entry,
        "sl": stop,
        "tp": target,
        "deviation": config.deviation_points,
        "magic": config.magic,
        "comment": (
            f"{COMMENT_PREFIX} {phase_code} "
            f"{'B' if is_buy else 'S'} {signal.session_date:%Y%m%d}"
        ),
        "type_time": mt5.ORDER_TIME_GTC,
    }
    result = _checked_send(request)
    print(
        f"  LIVE MARKET PLACED {symbol} {signal.side.upper()} "
        f"{signal.phase} ticket={result.order or result.deal} "
        f"volume={volume} entry={entry} SL={stop} TP={target} "
        f"risk=${planned:.2f}/${allowed:.2f}"
    )
    return result


def _cancel_order(order: object) -> None:
    result = _checked_send(
        {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": int(order.ticket),
            "symbol": order.symbol,
            "magic": int(order.magic),
            "comment": f"{COMMENT_PREFIX} cutoff",
        },
        try_fillings=False,
    )
    print(f"  cancelled pending order {order.ticket}: {result.comment}")


def _modify_position_stop(position: object, new_stop: float) -> None:
    info = mt5.symbol_info(position.symbol)
    if info is None:
        return
    result = _checked_send(
        {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": int(position.ticket),
            "symbol": position.symbol,
            "sl": _round_price(new_stop, int(info.digits)),
            "tp": float(position.tp),
            "magic": int(position.magic),
            "comment": f"{COMMENT_PREFIX} protect",
        },
        try_fillings=False,
    )
    print(
        f"  protected position {position.ticket} "
        f"SL={new_stop:.{int(info.digits)}f}: {result.comment}"
    )


def _close_position(position: object, config: Config) -> None:
    tick = mt5.symbol_info_tick(position.symbol)
    if tick is None:
        raise MT5Error(f"No quote to close {position.symbol}")
    if int(position.type) == mt5.POSITION_TYPE_BUY:
        order_type = mt5.ORDER_TYPE_SELL
        price = float(tick.bid)
    else:
        order_type = mt5.ORDER_TYPE_BUY
        price = float(tick.ask)
    result = _checked_send(
        {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": int(position.ticket),
            "symbol": position.symbol,
            "volume": float(position.volume),
            "type": order_type,
            "price": price,
            "deviation": config.deviation_points,
            "magic": int(position.magic),
            "comment": f"{COMMENT_PREFIX} force exit",
            "type_time": mt5.ORDER_TIME_GTC,
        }
    )
    print(f"  force-closed position {position.ticket}: {result.comment}")


def manage_symbol(symbol: str, now: datetime, config: Config) -> None:
    cutoff = combine(now.date(), config.ny_cutoff)
    force_exit = combine(now.date(), config.force_exit)
    orders = _bot_orders(symbol)
    if now >= cutoff:
        for order in orders:
            _cancel_order(order)
    positions = _bot_positions(symbol)
    for position in positions:
        if now >= force_exit:
            _close_position(position, config)
            continue
        entry = float(position.price_open)
        target = float(position.tp)
        if target <= 0:
            print(f"  position {position.ticket} has no TP; protection skipped")
            continue
        comment = str(getattr(position, "comment", ""))
        if comment.startswith(f"{COMMENT_PREFIX} AF"):
            target_rr = config.article_fade_rr
        elif comment.startswith(f"{COMMENT_PREFIX} AD"):
            target_rr = config.article_distribution_rr
        else:
            target_rr = config.ny_fallback_rr
        risk = abs(target - entry) / target_rr
        if risk <= 0:
            continue
        tick = mt5.symbol_info_tick(symbol)
        info = mt5.symbol_info(symbol)
        if tick is None or info is None:
            continue
        min_distance = max(
            float(info.trade_stops_level) * float(info.point),
            float(info.point),
        )
        if int(position.type) == mt5.POSITION_TYPE_BUY:
            trigger = entry + config.lock_trigger_r * risk
            protected = entry + config.lock_profit_r * risk
            improves = float(position.sl) < protected
            valid = protected < float(tick.bid) - min_distance
            if float(tick.bid) >= trigger and improves and valid:
                _modify_position_stop(position, protected)
        else:
            trigger = entry - config.lock_trigger_r * risk
            protected = entry - config.lock_profit_r * risk
            improves = float(position.sl) == 0 or float(position.sl) > protected
            valid = protected > float(tick.ask) + min_distance
            if float(tick.ask) <= trigger and improves and valid:
                _modify_position_stop(position, protected)


_active_config: Config


def run_live(config: Config, once: bool = False) -> None:
    global _active_config
    _active_config = config
    if not config.enable_trading and not config.dry_run:
        raise RuntimeError(
            "Invalid execution flags: DRY_RUN=false requires "
            "ENABLE_TRADING=true"
        )
    while True:
        now = datetime.now(UTC)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        history_days = max(
            config.regime_atr_days,
            config.regime_asia_median_days,
        ) * 2
        history_start = day_start - timedelta(days=history_days)
        with connection() as account:
            mode = (
                "LIVE"
                if config.enable_trading and not config.dry_run
                else "DRY-RUN"
            )
            print(
                f"[{now.isoformat()}] account={account.login} "
                f"server={account.server} balance=${account.balance:,.2f} "
                f"equity=${account.equity:,.2f} free_margin="
                f"${account.margin_free:,.2f} mode={mode}"
            )
            if mode == "LIVE":
                terminal = mt5.terminal_info()
                if terminal is None or not bool(terminal.trade_allowed):
                    raise MT5Error("MT5 terminal does not allow Algo Trading")
                if not bool(account.trade_allowed):
                    raise MT5Error("Connected account does not allow trading")
            symbols = discover_symbols(config.symbols)
            for canonical, symbol in symbols.items():
                try:
                    manage_symbol(symbol, now, config)
                    frame = load_m1(
                        symbol,
                        history_start,
                        now,
                        config.root / "data" / "live",
                        refresh=True,
                    )
                    point = float(mt5.symbol_info(symbol).point)
                    if config.strategy_model == "article":
                        signal, reason = build_article_signal(
                            frame,
                            point,
                            config,
                            now,
                        )
                    elif config.strategy_model == "legacy":
                        signal, reason = build_pending_signal(
                            frame,
                            point,
                            config,
                            now,
                        )
                    else:
                        raise ValueError(
                            f"Unsupported STRATEGY_MODEL: "
                            f"{config.strategy_model}"
                        )
                    if signal is None:
                        print(f"  {canonical:<7} {reason}")
                        continue
                    if _has_traded_today(symbol, day_start, now):
                        print(
                            f"  {canonical:<7} bot order/position already "
                            "exists for today"
                        )
                        continue
                    if isinstance(signal, ArticleSignal):
                        print(
                            f"  {canonical:<7} {signal.side.upper()} "
                            f"{signal.phase} confirmed; structural "
                            f"SL={signal.stop:.5f}, target={signal.rr:.2f}R"
                        )
                        if mode == "LIVE":
                            place_article_market(
                                symbol,
                                signal,
                                account,
                                config,
                            )
                    else:
                        print(
                            f"  {canonical:<7} {signal.side.upper()} STOP ready "
                            f"entry={signal.entry:.5f} SL={signal.stop:.5f} "
                            f"TP={signal.target:.5f}"
                        )
                        if mode == "LIVE":
                            place_pending(symbol, signal, account, config)
                    if mode != "LIVE":
                        print("  DRY-RUN: order not submitted")
                except Exception as exc:
                    print(f"  {canonical:<7} ERROR: {exc}")
        if once:
            return
        clock.sleep(config.poll_seconds)
