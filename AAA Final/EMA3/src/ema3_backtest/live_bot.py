from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import logging
import math
from pathlib import Path
import re
import time
from typing import Iterable

import MetaTrader5 as mt5
import pandas as pd
from dotenv import load_dotenv

from .portfolio_guard import selected_xau_entry_guard


UTC = timezone.utc


def canonical(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def env_bool(name: str, default: bool) -> bool:
    import os

    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class LiveConfig:
    symbol_hint: str
    pivot_distance: int
    max_same_direction_legs: int
    risk_pct_per_trade: float
    risk_progression_enabled: bool
    risk_progression_multiplier: float
    risk_progression_max_pct: float
    maximum_lot: float
    live_trading: bool
    close_on_opposite: bool
    exit_mode: str
    trailing_enabled: bool
    target_r: float
    max_target_r: float
    trail_start_r: float
    trail_distance_r: float
    signal_filter: str
    ema_slope_bars: int
    entry_window_minutes: int
    poll_seconds: int
    history_bars: int
    deviation_points: int
    max_tick_age_seconds: int
    magic: int
    comment: str
    state_file: Path
    log_file: Path

    @classmethod
    def from_env(cls) -> "LiveConfig":
        import os

        load_dotenv()
        return cls(
            symbol_hint=os.getenv("GOLD_SYMBOL_HINT", "AUTO").strip(),
            pivot_distance=int(os.getenv("PIVOT_DISTANCE", "5")),
            max_same_direction_legs=int(
                os.getenv("MAX_SAME_DIRECTION_LEGS", "1")
            ),
            risk_pct_per_trade=float(
                os.getenv("RISK_PCT_PER_TRADE", "0.5")
            ),
            risk_progression_enabled=env_bool("RISK_PROGRESSION_ENABLED", False),
            risk_progression_multiplier=float(
                os.getenv("RISK_PROGRESSION_MULTIPLIER", "1.6")
            ),
            risk_progression_max_pct=float(
                os.getenv("RISK_PROGRESSION_MAX_PCT", "3.2")
            ),
            maximum_lot=float(os.getenv("MAXIMUM_LOT", "100.0")),
            live_trading=env_bool("LIVE_TRADING", False),
            close_on_opposite=env_bool("CLOSE_ON_OPPOSITE", True),
            exit_mode=os.getenv("EXIT_MODE", "trail").strip().lower(),
            trailing_enabled=env_bool("TRAILING_ENABLED", True),
            target_r=float(os.getenv("TARGET_R", "1.7")),
            max_target_r=float(os.getenv("MAX_TARGET_R", "1.7")),
            trail_start_r=float(os.getenv("TRAIL_START_R", "1.0")),
            trail_distance_r=float(os.getenv("TRAIL_DISTANCE_R", "1.0")),
            signal_filter=os.getenv("SIGNAL_FILTER", "ema200_slope").strip().lower(),
            ema_slope_bars=int(os.getenv("EMA_SLOPE_BARS", "6")),
            entry_window_minutes=int(os.getenv("ENTRY_WINDOW_MINUTES", "10")),
            poll_seconds=int(os.getenv("POLL_SECONDS", "15")),
            history_bars=int(os.getenv("HISTORY_BARS", "300")),
            deviation_points=int(os.getenv("DEVIATION_POINTS", "50")),
            max_tick_age_seconds=int(os.getenv("MAX_TICK_AGE_SECONDS", "120")),
            magic=int(os.getenv("MAGIC_NUMBER", "3082026")),
            comment=os.getenv("ORDER_COMMENT", "EMA3 A H4 EMA200 trail")[:31],
            state_file=Path(os.getenv("STATE_FILE", "runtime/state.json")),
            log_file=Path(os.getenv("LOG_FILE", "logs/ema3-live.log")),
        )

    def validate(self) -> None:
        if self.pivot_distance < 1:
            raise ValueError("PIVOT_DISTANCE must be at least 1")
        if self.max_same_direction_legs < 1:
            raise ValueError("MAX_SAME_DIRECTION_LEGS must be at least 1")
        if not 0 < self.risk_pct_per_trade <= 100:
            raise ValueError("RISK_PCT_PER_TRADE must be between 0 and 100")
        if self.risk_progression_multiplier < 1:
            raise ValueError("RISK_PROGRESSION_MULTIPLIER must be at least 1")
        if not 0 < self.risk_progression_max_pct <= 100:
            raise ValueError("RISK_PROGRESSION_MAX_PCT must be between 0 and 100")
        if self.maximum_lot <= 0:
            raise ValueError("MAXIMUM_LOT must be positive")
        if self.history_bars < self.pivot_distance * 2 + 3:
            raise ValueError("HISTORY_BARS is too small for the pivot distance")
        if self.entry_window_minutes < 1:
            raise ValueError("ENTRY_WINDOW_MINUTES must be positive")
        if self.exit_mode not in {"fixed", "trail", "opposite"}:
            raise ValueError("EXIT_MODE must be fixed, trail, or opposite")
        if not 0 < self.max_target_r <= 1.7:
            raise ValueError("MAX_TARGET_R must be positive and no greater than 1.7")
        if self.exit_mode == "fixed" and self.target_r <= 0:
            raise ValueError("TARGET_R must be positive for fixed exits")
        if self.exit_mode == "trail" and (
            self.trail_start_r <= 0 or self.trail_distance_r <= 0
        ):
            raise ValueError("Trailing R values must be positive")
        if self.signal_filter not in {"none", "ema200_slope"}:
            raise ValueError("SIGNAL_FILTER must be none or ema200_slope")
        if self.ema_slope_bars < 1:
            raise ValueError("EMA_SLOPE_BARS must be positive")
        if self.signal_filter == "ema200_slope" and self.history_bars < 250:
            raise ValueError("HISTORY_BARS must be at least 250 for EMA200 filtering")

    @property
    def effective_exit_mode(self) -> str:
        if self.exit_mode == "trail" and not self.trailing_enabled:
            return "fixed"
        return self.exit_mode


def progressive_risk_pct(config: LiveConfig, loss_streak: int) -> float:
    """Return capped live risk for the next entry."""
    if not config.risk_progression_enabled:
        return config.risk_pct_per_trade
    uncapped = (
        config.risk_pct_per_trade
        * config.risk_progression_multiplier ** max(loss_streak, 0)
    )
    return min(uncapped, config.risk_progression_max_pct)


def gold_symbol_score(item: object, hint: str) -> tuple[int, int, int, int, str]:
    name = str(getattr(item, "name", ""))
    description = str(getattr(item, "description", ""))
    path = str(getattr(item, "path", ""))
    normalized = canonical(name)
    requested = canonical(hint)
    text = canonical(f"{name} {description} {path}")
    exact_hint = requested not in {"", "AUTO"} and normalized == requested
    starts_hint = (
        requested not in {"", "AUTO"} and normalized.startswith(requested)
    )
    is_xauusd = normalized == "XAUUSD" or normalized.startswith("XAUUSD")
    is_gold_name = normalized == "GOLD" or normalized.startswith("GOLD")
    describes_gold = "GOLD" in text or "XAU" in text
    if not any((exact_hint, starts_hint, is_xauusd, is_gold_name, describes_gold)):
        return (-10_000, 0, 0, 0, name)
    trade_mode = int(getattr(item, "trade_mode", 0))
    disabled = trade_mode == int(mt5.SYMBOL_TRADE_MODE_DISABLED)
    visible = bool(getattr(item, "visible", False))
    base = (
        1_000 if exact_hint else
        900 if is_xauusd else
        800 if is_gold_name else
        700 if starts_hint else
        500
    )
    return (
        base,
        0 if disabled else 1,
        1 if visible else 0,
        -len(name),
        name,
    )


def choose_gold_symbol(symbols: Iterable[object], hint: str = "AUTO") -> str:
    ranked = sorted(
        ((gold_symbol_score(item, hint), item) for item in symbols),
        key=lambda row: row[0],
        reverse=True,
    )
    if not ranked or ranked[0][0][0] < 0:
        raise RuntimeError(
            "No broker gold symbol found. Set GOLD_SYMBOL_HINT to its name."
        )
    return str(getattr(ranked[0][1], "name"))


def discover_gold_symbol(hint: str) -> str:
    symbols = mt5.symbols_get()
    if not symbols:
        raise RuntimeError(f"MT5 symbol catalogue unavailable: {mt5.last_error()}")
    symbol = choose_gold_symbol(symbols, hint)
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"Could not select {symbol}: {mt5.last_error()}")
    info = mt5.symbol_info(symbol)
    if info is None or int(info.trade_mode) == int(mt5.SYMBOL_TRADE_MODE_DISABLED):
        raise RuntimeError(f"Discovered gold symbol {symbol} is not tradable")
    return symbol


def latest_h4_frame(symbol: str, bars: int) -> pd.DataFrame:
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, bars)
    if rates is None or len(rates) < 3:
        raise RuntimeError(f"No H4 data for {symbol}: {mt5.last_error()}")
    frame = pd.DataFrame(rates).sort_values("time").reset_index(drop=True)
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    return frame


def confirmed_signal(
    completed: pd.DataFrame, distance: int
) -> dict[str, object] | None:
    confirmation_idx = len(completed) - 1
    pivot_idx = confirmation_idx - distance
    if pivot_idx < distance:
        return None
    left = pivot_idx - distance
    right = pivot_idx + distance
    lows = completed.loc[left:right, "low"]
    highs = completed.loc[left:right, "high"]
    pivot_low = float(completed.at[pivot_idx, "low"])
    pivot_high = float(completed.at[pivot_idx, "high"])
    is_buy = (
        pivot_low == float(lows.min())
        and int((lows == pivot_low).sum()) == 1
    )
    is_sell = (
        pivot_high == float(highs.max())
        and int((highs == pivot_high).sum()) == 1
    )
    if is_buy == is_sell:
        return None
    side = "buy" if is_buy else "sell"
    pivot_time = completed.at[pivot_idx, "time"]
    confirmation_time = completed.at[confirmation_idx, "time"]
    return {
        "side": side,
        "pivot_price": pivot_low if side == "buy" else pivot_high,
        "pivot_time": pivot_time,
        "confirmation_time": confirmation_time,
        "signal_id": f"{side}:{pivot_time.isoformat()}:{confirmation_time.isoformat()}",
    }


def signal_passes_filter(
    completed: pd.DataFrame,
    signal: dict[str, object],
    signal_filter: str,
    ema_slope_bars: int,
) -> bool:
    if signal_filter == "none":
        return True
    ema200 = completed["close"].ewm(
        span=200, adjust=False, min_periods=200
    ).mean()
    current_idx = len(completed) - 1
    earlier_idx = current_idx - ema_slope_bars
    if earlier_idx < 0 or pd.isna(ema200.iat[current_idx]) or pd.isna(
        ema200.iat[earlier_idx]
    ):
        return False
    current = float(ema200.iat[current_idx])
    earlier = float(ema200.iat[earlier_idx])
    return (str(signal["side"]) == "buy" and current > earlier) or (
        str(signal["side"]) == "sell" and current < earlier
    )


def load_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"processed_signals": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"processed_signals": []}


def save_state(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temporary.replace(path)


def normalized_volume(
    symbol: str, requested: float, round_down: bool = False
) -> float:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"No symbol information for {symbol}")
    step = float(info.volume_step)
    minimum = float(info.volume_min)
    maximum = float(info.volume_max)
    volume = min(max(requested, minimum), maximum)
    if step > 0:
        units = (
            math.floor((volume + 1e-12) / step)
            if round_down
            else round(volume / step)
        )
        volume = round(units * step, 8)
    return volume


def risk_sized_volume(
    symbol: str,
    side: str,
    entry: float,
    stop: float,
    risk_budget: float,
    maximum_lot: float,
) -> tuple[float, float]:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"No symbol information for {symbol}")
    order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
    loss_one_lot = mt5.order_calc_profit(order_type, symbol, 1.0, entry, stop)
    if loss_one_lot is None:
        raise RuntimeError(
            f"Could not calculate position risk for {symbol}: {mt5.last_error()}"
        )
    loss_one_lot = abs(float(loss_one_lot))
    if loss_one_lot <= 0:
        raise RuntimeError("Calculated one-lot stop risk is zero")
    raw_volume = min(
        risk_budget / loss_one_lot,
        maximum_lot,
        float(info.volume_max),
    )
    if raw_volume + 1e-12 < float(info.volume_min):
        raw_volume = float(info.volume_min)
    volume = normalized_volume(symbol, raw_volume, round_down=True)
    if volume <= 0:
        raise RuntimeError("Risk-sized volume rounded to zero")
    return volume, loss_one_lot * volume


def managed_positions(symbol: str, magic: int) -> list[object]:
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        raise RuntimeError(f"Could not read positions: {mt5.last_error()}")
    return [position for position in positions if int(position.magic) == magic]


def advance_loss_streak(loss_streak: int, closed_trade_pnls: Iterable[float]) -> int:
    """Apply the exact rule: loss increments, win resets, flat leaves unchanged."""
    streak = max(int(loss_streak), 0)
    for pnl in closed_trade_pnls:
        if pnl < 0:
            streak += 1
        elif pnl > 0:
            streak = 0
    return streak


def sync_loss_streak(
    symbol: str, config: LiveConfig, state: dict[str, object]
) -> bool:
    """Persist the loss streak from newly closed positions owned by this bot."""
    if not config.risk_progression_enabled:
        return False
    deals = mt5.history_deals_get(datetime.now(UTC) - timedelta(days=730), datetime.now(UTC))
    if deals is None:
        raise RuntimeError(f"Could not read deal history: {mt5.last_error()}")
    open_positions = mt5.positions_get(symbol=symbol)
    if open_positions is None:
        raise RuntimeError(f"Could not read open positions: {mt5.last_error()}")
    active_position_ids = {
        int(getattr(position, "identifier", getattr(position, "ticket", 0)))
        for position in open_positions
        if int(getattr(position, "magic", 0)) == config.magic
    }
    processed = {int(value) for value in state.get("processed_closed_positions", [])}
    grouped: dict[int, tuple[int, float]] = {}
    for deal in deals:
        if str(getattr(deal, "symbol", "")) != symbol:
            continue
        if int(getattr(deal, "magic", 0)) != config.magic:
            continue
        if int(getattr(deal, "entry", -1)) not in {
            int(mt5.DEAL_ENTRY_OUT),
            int(getattr(mt5, "DEAL_ENTRY_OUT_BY", 3)),
        }:
            continue
        position_id = int(getattr(deal, "position_id", 0))
        if not position_id or position_id in processed:
            continue
        pnl = sum(
            float(getattr(deal, name, 0.0))
            for name in ("profit", "commission", "swap", "fee")
        )
        time_msc = int(getattr(deal, "time_msc", 0))
        previous_time, previous_pnl = grouped.get(position_id, (0, 0.0))
        grouped[position_id] = (max(previous_time, time_msc), previous_pnl + pnl)
    closed = [
        (time_msc, position_id, pnl)
        for position_id, (time_msc, pnl) in grouped.items()
        if position_id not in active_position_ids
    ]
    if not closed:
        return False
    closed.sort()
    streak = advance_loss_streak(
        int(state.get("loss_streak", 0)), [pnl for _, _, pnl in closed]
    )
    processed.update(position_id for _, position_id, _ in closed)
    state["loss_streak"] = streak
    state["processed_closed_positions"] = sorted(processed)[-500:]
    logging.info(
        "Risk progression updated: loss_streak=%d next_risk=%.4f%%",
        streak,
        progressive_risk_pct(config, streak),
    )
    return True


def side_of_position(position: object) -> str:
    return "buy" if int(position.type) == int(mt5.POSITION_TYPE_BUY) else "sell"


def filling_modes(symbol: str | None = None) -> list[int]:
    """Return broker-advertised market modes, followed by safe fallbacks."""
    modes: list[int] = []
    info = mt5.symbol_info(symbol) if symbol else None
    flags = int(getattr(info, "filling_mode", 0))
    # symbol_info().filling_mode is a flag mask: FOK=1 and IOC=2.
    if flags & 1:
        modes.append(int(mt5.ORDER_FILLING_FOK))
    if flags & 2:
        modes.append(int(mt5.ORDER_FILLING_IOC))
    for fallback in (
        int(mt5.ORDER_FILLING_FOK),
        int(mt5.ORDER_FILLING_IOC),
        int(mt5.ORDER_FILLING_RETURN),
    ):
        if fallback not in modes:
            modes.append(fallback)
    return modes


def send_request(request: dict[str, object]) -> object:
    last_result = None
    rejected: list[str] = []
    symbol = str(request.get("symbol", ""))
    for mode in filling_modes(symbol):
        attempt = dict(request)
        attempt["type_filling"] = mode
        check = mt5.order_check(attempt)
        if check is None or int(check.retcode) not in {
            0,
            int(mt5.TRADE_RETCODE_DONE),
            int(mt5.TRADE_RETCODE_PLACED),
        }:
            rejected.append(
                f"fill={mode} check={getattr(check, 'retcode', None)} "
                f"{getattr(check, 'comment', mt5.last_error())}"
            )
            continue
        result = mt5.order_send(attempt)
        last_result = result
        if result is not None and int(result.retcode) in {
            int(mt5.TRADE_RETCODE_DONE),
            int(mt5.TRADE_RETCODE_DONE_PARTIAL),
            int(mt5.TRADE_RETCODE_PLACED),
        }:
            return result
        if result is None or int(result.retcode) not in {
            int(mt5.TRADE_RETCODE_INVALID_FILL),
            int(mt5.TRADE_RETCODE_INVALID),
        }:
            break
        rejected.append(
            f"fill={mode} send={getattr(result, 'retcode', None)} "
            f"{getattr(result, 'comment', mt5.last_error())}"
        )
    detail = mt5.last_error() if last_result is None else (
        last_result.retcode,
        last_result.comment,
    )
    suffix = f"; checks: {' | '.join(rejected)}" if rejected else ""
    raise RuntimeError(f"MT5 order failed: {detail}{suffix}")


def close_position(
    symbol: str, position: object, config: LiveConfig, dry_run: bool
) -> None:
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"No live tick for {symbol}")
    side = side_of_position(position)
    order_type = mt5.ORDER_TYPE_SELL if side == "buy" else mt5.ORDER_TYPE_BUY
    price = float(tick.bid) if side == "buy" else float(tick.ask)
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "position": int(position.ticket),
        "volume": float(position.volume),
        "type": order_type,
        "price": price,
        "deviation": config.deviation_points,
        "magic": config.magic,
        "comment": f"{config.comment}_EXIT"[:31],
        "type_time": mt5.ORDER_TIME_GTC,
    }
    if dry_run:
        logging.info("DRY RUN close ticket=%s side=%s", position.ticket, side)
        return
    result = send_request(request)
    logging.info(
        "Closed ticket=%s retcode=%s deal=%s",
        position.ticket,
        result.retcode,
        result.deal,
    )


def open_position(
    symbol: str,
    side: str,
    stop: float,
    config: LiveConfig,
    state: dict[str, object],
    dry_run: bool,
) -> dict[str, object] | None:
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"No live tick for {symbol}")
    order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
    price = float(tick.ask) if side == "buy" else float(tick.bid)
    info = mt5.symbol_info(symbol)
    account = mt5.account_info()
    if info is None or account is None:
        raise RuntimeError("Symbol or account information unavailable")
    # MT5 bars are Bid-based. A Sell closes at Ask, so its structural pivot
    # stop needs the current spread above the recorded Bid pivot high.
    if side == "sell":
        stop += max(float(tick.ask) - float(tick.bid), 0.0)
    stop = round(float(stop), int(info.digits))
    if (side == "buy" and stop >= price) or (side == "sell" and stop <= price):
        raise RuntimeError(
            f"Invalid structural stop {stop} for {side} entry near {price}"
        )
    minimum_stop_distance = float(info.trade_stops_level) * float(info.point)
    if abs(price - stop) + 1e-12 < minimum_stop_distance:
        raise RuntimeError(
            "Structural stop is inside the broker minimum stop distance "
            f"({minimum_stop_distance})"
        )
    applied_risk_pct = progressive_risk_pct(
        config, int(state.get("loss_streak", 0))
    )
    risk_budget = float(account.equity) * applied_risk_pct / 100.0
    volume, actual_risk = risk_sized_volume(
        symbol,
        side,
        price,
        stop,
        risk_budget,
        config.maximum_lot,
    )
    risk_distance = abs(price - stop)
    target = 0.0
    effective_exit_mode = config.effective_exit_mode
    if effective_exit_mode in {"fixed", "trail"}:
        target_r = min(config.target_r, config.max_target_r)
        if effective_exit_mode == "trail":
            target_r = config.max_target_r
        target = (
            price + target_r * risk_distance
            if side == "buy"
            else price - target_r * risk_distance
        )
        target = round(target, int(info.digits))
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "sl": stop,
        "deviation": config.deviation_points,
        "magic": config.magic,
        "comment": config.comment,
        "type_time": mt5.ORDER_TIME_GTC,
    }
    if target:
        request["tp"] = target
    exit_label: float | str = target or (
        f"trail {config.trail_start_r:g}R/{config.trail_distance_r:g}R"
        if effective_exit_mode == "trail"
        else "opposite signal"
    )
    if dry_run:
        logging.info(
            "DRY RUN open side=%s symbol=%s volume=%.2f price=%s stop=%s "
            "target=%s risk=$%.2f (%.2f%% equity)",
            side,
            symbol,
            volume,
            price,
            stop,
            exit_label,
            actual_risk,
            actual_risk / float(account.equity) * 100.0,
        )
        return None
    actual_risk_pct = actual_risk / float(account.equity) * 100.0
    with selected_xau_entry_guard(max(applied_risk_pct, actual_risk_pct)) as decision:
        if not decision.allowed:
            logging.warning(
                "Entry blocked: shared XAU risk %.2f%% + %.2f%% exceeds %.2f%%",
                decision.current_risk_pct,
                decision.proposed_risk_pct,
                decision.cap_risk_pct,
            )
            return None
        result = send_request(request)
    logging.info(
        "Opened %s %.2f %s entry=%s stop=%s target=%s risk=$%.2f retcode=%s "
        "order=%s deal=%s",
        side,
        volume,
        symbol,
        price,
        stop,
        exit_label,
        actual_risk,
        result.retcode,
        result.order,
        result.deal,
    )
    return {
        "ticket": int(result.order),
        "side": side,
        "entry": price,
        "initial_stop": stop,
        "risk_distance": risk_distance,
    }


def manage_trailing_positions(
    symbol: str,
    completed: pd.DataFrame,
    positions: list[object],
    config: LiveConfig,
    state: dict[str, object],
    dry_run: bool,
) -> bool:
    if config.effective_exit_mode != "trail" or completed.empty:
        return False
    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if info is None or tick is None:
        raise RuntimeError("Symbol or tick unavailable for trailing stop")
    risk_state = state.setdefault("position_risk", {})
    if not isinstance(risk_state, dict):
        risk_state = {}
        state["position_risk"] = risk_state
    active_tickets = {str(int(position.ticket)) for position in positions}
    changed = False
    for key in list(risk_state):
        if key not in active_tickets:
            del risk_state[key]
            changed = True

    spread_now = max(float(tick.ask) - float(tick.bid), 0.0)
    completed_bid_close = float(completed.iloc[-1]["close"])
    minimum_distance = float(info.trade_stops_level) * float(info.point)
    for position in positions:
        key = str(int(position.ticket))
        side = side_of_position(position)
        entry = float(position.price_open)
        record = risk_state.get(key)
        if not isinstance(record, dict):
            initial_stop = float(position.sl)
            losing_side_stop = initial_stop > 0 and (
                (side == "buy" and initial_stop < entry)
                or (side == "sell" and initial_stop > entry)
            )
            if not losing_side_stop:
                logging.warning(
                    "Cannot reconstruct initial risk for ticket=%s; trailing skipped",
                    position.ticket,
                )
                continue
            record = {
                "side": side,
                "entry": entry,
                "initial_stop": initial_stop,
                "risk_distance": abs(entry - initial_stop),
            }
            risk_state[key] = record
            changed = True
        risk_distance = float(record.get("risk_distance", 0.0))
        if risk_distance <= float(info.point):
            continue
        mark_close = completed_bid_close if side == "buy" else completed_bid_close + spread_now
        progress = mark_close - entry if side == "buy" else entry - mark_close
        if progress + 1e-12 < config.trail_start_r * risk_distance:
            continue
        candidate = (
            mark_close - config.trail_distance_r * risk_distance
            if side == "buy"
            else mark_close + config.trail_distance_r * risk_distance
        )
        current_stop = float(position.sl)
        improves = (side == "buy" and candidate > current_stop) or (
            side == "sell" and (current_stop <= 0 or candidate < current_stop)
        )
        valid_now = (
            side == "buy" and candidate < float(tick.bid) - minimum_distance
        ) or (side == "sell" and candidate > float(tick.ask) + minimum_distance)
        if not improves or not valid_now:
            continue
        candidate = round(candidate, int(info.digits))
        if dry_run:
            logging.info(
                "DRY RUN trail ticket=%s side=%s old_sl=%s new_sl=%s progress=%.2fR",
                position.ticket,
                side,
                current_stop,
                candidate,
                progress / risk_distance,
            )
            continue
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": symbol,
            "position": int(position.ticket),
            "sl": candidate,
            "tp": float(position.tp),
            "magic": config.magic,
        }
        result = mt5.order_send(request)
        success = {
            int(mt5.TRADE_RETCODE_DONE),
            int(getattr(mt5, "TRADE_RETCODE_NO_CHANGES", -1)),
        }
        if result is None or int(result.retcode) not in success:
            detail = mt5.last_error() if result is None else (result.retcode, result.comment)
            raise RuntimeError(f"Trailing stop update failed: {detail}")
        logging.info(
            "Trailed ticket=%s side=%s old_sl=%s new_sl=%s progress=%.2fR",
            position.ticket,
            side,
            current_stop,
            candidate,
            progress / risk_distance,
        )
    return changed


def account_line() -> str:
    account = mt5.account_info()
    if account is None:
        raise RuntimeError(f"No connected MT5 account: {mt5.last_error()}")
    return (
        f"Account {account.login} | {account.server} | {account.currency} | "
        f"balance {account.balance:,.2f} | equity {account.equity:,.2f} | "
        f"free margin {account.margin_free:,.2f} | leverage 1:{account.leverage}"
    )


def process_once(symbol: str, config: LiveConfig, state: dict[str, object]) -> None:
    if sync_loss_streak(symbol, config, state):
        save_state(config.state_file, state)
    frame = latest_h4_frame(symbol, config.history_bars)
    completed = frame.iloc[:-1].reset_index(drop=True)
    positions = managed_positions(symbol, config.magic)
    dry_run = not config.live_trading
    if manage_trailing_positions(
        symbol, completed, positions, config, state, dry_run
    ):
        save_state(config.state_file, state)
    current = frame.iloc[-1]
    now = datetime.now(UTC)
    current_open = current["time"].to_pydatetime()
    bar_age_minutes = (now - current_open).total_seconds() / 60.0
    if not 0 <= bar_age_minutes < config.entry_window_minutes:
        logging.debug(
            "No entry: current H4 bar age %.1f min (window %d)",
            bar_age_minutes,
            config.entry_window_minutes,
        )
        return
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"No live tick for {symbol}")
    tick_age = now.timestamp() - float(tick.time)
    if tick_age > config.max_tick_age_seconds:
        logging.warning("No entry: stale tick is %.0f seconds old", tick_age)
        return

    signal = confirmed_signal(completed, config.pivot_distance)
    if signal is None:
        logging.info("No newly confirmed pivot at %s", current_open.isoformat())
        return
    signal_id = str(signal["signal_id"])
    processed = list(state.get("processed_signals", []))
    if signal_id in processed:
        return
    if not signal_passes_filter(
        completed, signal, config.signal_filter, config.ema_slope_bars
    ):
        logging.info(
            "Signal %s rejected by %s filter",
            str(signal["side"]).upper(),
            config.signal_filter,
        )
        processed.append(signal_id)
        state["processed_signals"] = processed[-100:]
        save_state(config.state_file, state)
        return

    side = str(signal["side"])
    opposite = [position for position in positions if side_of_position(position) != side]
    same_side = [position for position in positions if side_of_position(position) == side]
    logging.info(
        "Signal %s pivot=%s confirmation=%s managed=%d",
        side.upper(),
        signal["pivot_time"],
        signal["confirmation_time"],
        len(positions),
    )
    if opposite and config.close_on_opposite:
        for position in opposite:
            close_position(symbol, position, config, dry_run)
            risk_state = state.get("position_risk", {})
            if isinstance(risk_state, dict):
                risk_state.pop(str(int(position.ticket)), None)
        same_side = []
    if len(same_side) < config.max_same_direction_legs:
        opened = open_position(
            symbol,
            side,
            float(signal["pivot_price"]),
            config,
            state,
            dry_run,
        )
        if opened is not None:
            risk_state = state.setdefault("position_risk", {})
            if isinstance(risk_state, dict):
                risk_state[str(int(opened["ticket"]))] = {
                    "side": opened["side"],
                    "entry": opened["entry"],
                    "initial_stop": opened["initial_stop"],
                    "risk_distance": opened["risk_distance"],
                }
    else:
        logging.info(
            "Signal ignored: already at max %d %s leg(s)",
            config.max_same_direction_legs,
            side,
        )
    processed.append(signal_id)
    state["processed_signals"] = processed[-100:]
    state["last_signal"] = {
        "side": side,
        "pivot_price": float(signal["pivot_price"]),
        "pivot_time": signal["pivot_time"].isoformat(),
        "confirmation_time": signal["confirmation_time"].isoformat(),
        "signal_id": signal_id,
    }
    save_state(config.state_file, state)


def configure_logging(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(path, encoding="utf-8"),
        ],
        force=True,
    )


def run(once: bool = False) -> None:
    config = LiveConfig.from_env()
    config.validate()
    configure_logging(config.log_file)
    if not mt5.initialize():
        raise RuntimeError(
            "Could not connect to the already-open MT5 terminal. "
            f"MT5 error: {mt5.last_error()}"
        )
    try:
        logging.info(account_line())
        symbol = discover_gold_symbol(config.symbol_hint)
        logging.info(
            "Gold discovered as %s | H4 | pivot=%d | risk=%.2f%% | "
            "exit=%s | filter=%s | max lot=%.2f | max legs=%d | mode=%s",
            symbol,
            config.pivot_distance,
            config.risk_pct_per_trade,
            (
                f"fixed {min(config.target_r, config.max_target_r):g}R"
                if config.effective_exit_mode == "fixed"
                else f"trail {config.trail_start_r:g}R/{config.trail_distance_r:g}R cap {config.max_target_r:g}R"
                if config.effective_exit_mode == "trail"
                else "opposite signal"
            ),
            config.signal_filter,
            config.maximum_lot,
            config.max_same_direction_legs,
            "LIVE" if config.live_trading else "DRY RUN",
        )
        state = load_state(config.state_file)
        while True:
            try:
                process_once(symbol, config, state)
            except Exception:
                logging.exception("Scan failed")
            if once:
                break
            time.sleep(config.poll_seconds)
    finally:
        mt5.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="Live EMA3 H4 pivot reversal bot")
    parser.add_argument(
        "--once",
        action="store_true",
        help="perform one scan and exit",
    )
    arguments = parser.parse_args()
    run(once=arguments.once)


if __name__ == "__main__":
    main()
