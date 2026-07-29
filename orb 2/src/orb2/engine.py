from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta
import math

import numpy as np
import pandas as pd

from .config import RuntimeConfig, StrategyConfig
from .models import Metrics, Signal, Trade


MODEL_PRIORITY = {
    "retest": 0,
    "sweep_rejection": 1,
    "sweep": 2,
    "rejection": 3,
    "straight": 4,
}


def _atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        (
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ),
        axis=1,
    ).max(axis=1)
    return true_range.ewm(
        alpha=1.0 / period, adjust=False, min_periods=period
    ).mean()


def prepare_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["_atr"] = _atr(result)
    candle_range = (result["high"] - result["low"]).replace(0, np.nan)
    result["_body_ratio"] = (
        (result["close"] - result["open"]).abs() / candle_range
    ).fillna(0.0)
    median_volume = result["tick_volume"].rolling(20, min_periods=10).median().shift(1)
    result["_relative_volume"] = (
        result["tick_volume"] / median_volume.replace(0, np.nan)
    ).fillna(0.0)

    h1 = result[["open", "high", "low", "close"]].resample(
        "1h", label="left", closed="left"
    ).agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
        }
    )
    h1 = h1.dropna()
    fast = h1["close"].ewm(span=20, adjust=False).mean()
    slow = h1["close"].ewm(span=50, adjust=False).mean()
    trend = pd.Series(
        np.where(fast > slow, 1, np.where(fast < slow, -1, 0)),
        index=h1.index + pd.Timedelta(hours=1),
    )
    result["_h1_bias"] = (
        trend.reindex(result.index, method="ffill").fillna(0).astype(int)
    )
    return result


def _stamp(day: date, clock: time, timezone) -> pd.Timestamp:
    return pd.Timestamp(datetime.combine(day, clock), tz=timezone)


def _direction_allowed(row: pd.Series, direction: str, config: StrategyConfig) -> bool:
    if not config.use_h1_bias:
        return True
    bias = int(row.get("_h1_bias", 0))
    return (direction == "buy" and bias > 0) or (
        direction == "sell" and bias < 0
    )


def _fvg_near_level(
    rows: pd.DataFrame,
    direction: str,
    level: float,
    tolerance: float,
) -> bool:
    if len(rows) < 3:
        return False
    for index in range(2, len(rows)):
        first = rows.iloc[index - 2]
        third = rows.iloc[index]
        if direction == "buy" and float(third["low"]) > float(first["high"]):
            lower, upper = float(first["high"]), float(third["low"])
            if lower - tolerance <= level <= upper + tolerance:
                return True
        if direction == "sell" and float(third["high"]) < float(first["low"]):
            lower, upper = float(third["high"]), float(first["low"])
            if lower - tolerance <= level <= upper + tolerance:
                return True
    return False


def _make_signal(
    symbol: str,
    session_date: date,
    model: str,
    direction: str,
    stamp: pd.Timestamp,
    index: int,
    row: pd.Series,
    or_high: float,
    or_low: float,
    stop_reference: float,
    target_reference: float | None,
    fvg: bool = False,
    liquidity: bool = False,
) -> Signal:
    return Signal(
        symbol=symbol,
        session_date=session_date.isoformat(),
        model=model,
        direction=direction,
        signal_time=stamp.isoformat(),
        signal_index=index,
        or_high=or_high,
        or_low=or_low,
        stop_reference=stop_reference,
        target_reference=target_reference,
        atr=float(row["_atr"]),
        spread_points=int(row.get("spread", 0) or 0),
        body_ratio=float(row["_body_ratio"]),
        relative_volume=float(row["_relative_volume"]),
        fvg_confluence=fvg,
        liquidity_confluence=liquidity,
    )


def find_day_signals(
    symbol: str,
    local_frame: pd.DataFrame,
    session_date: date,
    previous_session: tuple[float, float] | None,
    runtime: RuntimeConfig,
    config: StrategyConfig,
) -> tuple[list[Signal], str]:
    day = local_frame[local_frame.index.date == session_date]
    if day.empty:
        return [], "no_data"
    if session_date.weekday() >= 5:
        return [], "weekend"

    range_start = _stamp(session_date, runtime.range_start, runtime.timezone)
    range_end = range_start + pd.Timedelta(minutes=runtime.range_minutes)
    scan_end = _stamp(session_date, runtime.last_entry, runtime.timezone)
    opening = day[(day.index >= range_start) & (day.index < range_end)]
    expected_bars = math.ceil(runtime.range_minutes / 5)
    if len(opening) < expected_bars:
        return [], "opening_range_incomplete"
    or_high = float(opening["high"].max())
    or_low = float(opening["low"].min())
    candidates = day[(day.index >= range_end) & (day.index <= scan_end)]
    if candidates.empty:
        return [], "no_scan_window"

    rows = list(candidates.iterrows())
    signals: list[Signal] = []
    breakouts: list[tuple[int, pd.Timestamp, pd.Series, str]] = []
    for offset, (stamp, row) in enumerate(rows):
        atr_value = float(row["_atr"])
        if not math.isfinite(atr_value) or atr_value <= 0:
            continue
        body = float(row["_body_ratio"])
        relative_volume = float(row["_relative_volume"])
        direction = None
        if (
            float(row["close"]) > or_high
            and float(row["close"]) > float(row["open"])
        ):
            direction = "buy"
        elif (
            float(row["close"]) < or_low
            and float(row["close"]) < float(row["open"])
        ):
            direction = "sell"
        if (
            direction
            and body >= config.breakout_body_min
            and relative_volume >= config.relative_volume_min
            and _direction_allowed(row, direction, config)
        ):
            breakouts.append((offset, stamp, row, direction))
            if "straight" in config.models:
                buffer = max(config.stop_buffer_atr * atr_value, 1e-12)
                stop = (
                    or_high - buffer if direction == "buy" else or_low + buffer
                )
                signals.append(
                    _make_signal(
                        symbol,
                        session_date,
                        "straight",
                        direction,
                        stamp,
                        day.index.get_loc(stamp),
                        row,
                        or_high,
                        or_low,
                        stop,
                        None,
                    )
                )

        excursion = config.sweep_excursion_atr * atr_value
        fake_high = (
            float(row["high"]) >= or_high + excursion
            and float(row["close"]) < or_high
            and float(row["close"]) > or_low
            and float(row["close"]) < float(row["open"])
        )
        fake_low = (
            float(row["low"]) <= or_low - excursion
            and float(row["close"]) > or_low
            and float(row["close"]) < or_high
            and float(row["close"]) > float(row["open"])
        )
        previous_high = previous_session[0] if previous_session else None
        previous_low = previous_session[1] if previous_session else None
        sweep_high = bool(
            previous_high is not None
            and float(row["high"]) >= previous_high + excursion
            and float(row["close"]) < previous_high
            and float(row["close"]) < float(row["open"])
        )
        sweep_low = bool(
            previous_low is not None
            and float(row["low"]) <= previous_low - excursion
            and float(row["close"]) > previous_low
            and float(row["close"]) > float(row["open"])
        )
        reversal_quality = (
            body >= config.rejection_body_min
            and relative_volume >= config.relative_volume_min
        )
        if reversal_quality and (fake_high or sweep_high):
            direction = "sell"
            if _direction_allowed(row, direction, config):
                is_confluence = fake_high and sweep_high
                if is_confluence and (
                    "sweep" in config.models or "rejection" in config.models
                ):
                    model = "sweep_rejection"
                elif sweep_high and "sweep" in config.models:
                    model = "sweep"
                elif fake_high and "rejection" in config.models:
                    model = "rejection"
                else:
                    model = ""
                if model:
                    signals.append(
                        _make_signal(
                            symbol,
                            session_date,
                            model,
                            direction,
                            stamp,
                            day.index.get_loc(stamp),
                            row,
                            or_high,
                            or_low,
                            float(row["high"])
                            + config.stop_buffer_atr * atr_value,
                            or_low,
                            liquidity=sweep_high,
                        )
                    )
        if reversal_quality and (fake_low or sweep_low):
            direction = "buy"
            if _direction_allowed(row, direction, config):
                is_confluence = fake_low and sweep_low
                if is_confluence and (
                    "sweep" in config.models or "rejection" in config.models
                ):
                    model = "sweep_rejection"
                elif sweep_low and "sweep" in config.models:
                    model = "sweep"
                elif fake_low and "rejection" in config.models:
                    model = "rejection"
                else:
                    model = ""
                if model:
                    signals.append(
                        _make_signal(
                            symbol,
                            session_date,
                            model,
                            direction,
                            stamp,
                            day.index.get_loc(stamp),
                            row,
                            or_high,
                            or_low,
                            float(row["low"])
                            - config.stop_buffer_atr * atr_value,
                            or_high,
                            liquidity=sweep_low,
                        )
                    )

    if "retest" in config.models:
        for breakout_offset, breakout_stamp, breakout, direction in breakouts:
            level = or_high if direction == "buy" else or_low
            tolerance = config.retest_tolerance_atr * float(breakout["_atr"])
            retest_slice = rows[
                breakout_offset + 1 : breakout_offset + 1 + config.retest_bars
            ]
            for retest_position, (stamp, row) in enumerate(retest_slice, start=1):
                if float(row["_body_ratio"]) < config.rejection_body_min:
                    continue
                if direction == "buy":
                    touches = (
                        float(row["low"]) <= level + tolerance
                        and float(row["low"]) >= level - tolerance
                    )
                    rejects = (
                        float(row["close"]) >= level
                        and float(row["close"]) > float(row["open"])
                    )
                else:
                    touches = (
                        float(row["high"]) >= level - tolerance
                        and float(row["high"]) <= level + tolerance
                    )
                    rejects = (
                        float(row["close"]) <= level
                        and float(row["close"]) < float(row["open"])
                    )
                if not (touches and rejects):
                    continue
                context_start = max(0, breakout_offset - 2)
                context_end = breakout_offset + retest_position + 1
                context = candidates.iloc[context_start:context_end]
                fvg = _fvg_near_level(
                    context, direction, level, tolerance
                )
                if config.require_fvg and not fvg:
                    continue
                stop = (
                    float(row["low"])
                    - config.stop_buffer_atr * float(row["_atr"])
                    if direction == "buy"
                    else float(row["high"])
                    + config.stop_buffer_atr * float(row["_atr"])
                )
                signals.append(
                    _make_signal(
                        symbol,
                        session_date,
                        "retest",
                        direction,
                        stamp,
                        day.index.get_loc(stamp),
                        row,
                        or_high,
                        or_low,
                        stop,
                        None,
                        fvg=fvg,
                    )
                )
                break

    if not signals:
        return [], "no_model_confirmed"
    unique: dict[tuple[str, str, str], Signal] = {}
    for signal in signals:
        key = (signal.signal_time, signal.model, signal.direction)
        unique.setdefault(key, signal)
    ordered = sorted(
        unique.values(),
        key=lambda item: (
            item.signal_time,
            MODEL_PRIORITY.get(item.model, 99),
        ),
    )
    return ordered, "signals"


def simulate_signal(
    local_day: pd.DataFrame,
    signal: Signal,
    runtime: RuntimeConfig,
    config: StrategyConfig,
    point: float,
    balance: float,
) -> Trade | None:
    next_index = signal.signal_index + 1
    if next_index >= len(local_day):
        return None
    entry_stamp = local_day.index[next_index]
    if entry_stamp.time() > runtime.last_entry:
        return None
    entry_row = local_day.iloc[next_index]
    spread_points = int(entry_row.get("spread", signal.spread_points) or 0)
    spread = spread_points * point
    slippage = runtime.slippage_points * point
    entry = (
        float(entry_row["open"]) + spread + slippage
        if signal.direction == "buy"
        else float(entry_row["open"]) - slippage
    )
    stop = signal.stop_reference
    risk = entry - stop if signal.direction == "buy" else stop - entry
    if risk <= point:
        return None
    fixed_target = (
        entry + config.target_rr * risk
        if signal.direction == "buy"
        else entry - config.target_rr * risk
    )
    target = signal.target_reference
    if target is None:
        target = fixed_target
    target_reward = (
        target - entry if signal.direction == "buy" else entry - target
    )
    if target_reward / risk + 1e-9 < 2.0:
        return None

    flat_stamp = _stamp(
        date.fromisoformat(signal.session_date),
        runtime.flat_time,
        runtime.timezone,
    )
    management = local_day[
        (local_day.index >= entry_stamp) & (local_day.index <= flat_stamp)
    ]
    if management.empty:
        return None

    active_stop = stop
    be_armed = False
    partial_done = False
    remaining = 1.0
    realized_r = 0.0
    target_r = target_reward / risk
    outcome = "session_close"
    exit_stamp = management.index[-1]
    for stamp, row in management.iterrows():
        row_spread = float(row.get("spread", spread_points) or 0) * point
        if signal.direction == "buy":
            high = float(row["high"])
            low = float(row["low"])
            stop_hit = low <= active_stop
            target_hit = high >= target
            be_trigger_hit = high >= entry + config.move_to_be_at_r * risk
            partial_hit = high >= entry + config.partial_at_r * risk
        else:
            high = float(row["high"]) + row_spread
            low = float(row["low"]) + row_spread
            stop_hit = high >= active_stop
            target_hit = low <= target
            be_trigger_hit = low <= entry - config.move_to_be_at_r * risk
            partial_hit = low <= entry - config.partial_at_r * risk

        if stop_hit:
            stop_r = (
                (active_stop - entry) / risk
                if signal.direction == "buy"
                else (entry - active_stop) / risk
            )
            realized_r += remaining * stop_r
            outcome = "stop" if not be_armed else "break_even"
            if partial_done:
                outcome = "partial_then_stop"
            exit_stamp = stamp
            remaining = 0.0
            break
        if (
            config.partial_fraction > 0
            and not partial_done
            and target_r > config.partial_at_r
            and partial_hit
        ):
            fraction = min(max(config.partial_fraction, 0.0), 0.9)
            realized_r += fraction * config.partial_at_r
            remaining -= fraction
            partial_done = True
        if target_hit:
            realized_r += remaining * target_r
            outcome = "target"
            exit_stamp = stamp
            remaining = 0.0
            break
        if not be_armed and be_trigger_hit:
            active_stop = entry
            be_armed = True

    if remaining > 0:
        last = management.iloc[-1]
        row_spread = float(last.get("spread", spread_points) or 0) * point
        exit_price = (
            float(last["close"])
            if signal.direction == "buy"
            else float(last["close"]) + row_spread
        )
        close_r = (
            (exit_price - entry) / risk
            if signal.direction == "buy"
            else (entry - exit_price) / risk
        )
        realized_r += remaining * close_r

    risk_amount = balance * runtime.risk_percent / 100.0
    pnl = risk_amount * realized_r
    return Trade(
        symbol=signal.symbol,
        session_date=signal.session_date,
        model=signal.model,
        direction=signal.direction,
        signal_time=signal.signal_time,
        entry_time=entry_stamp.isoformat(),
        exit_time=exit_stamp.isoformat(),
        entry=entry,
        stop=stop,
        target=target,
        outcome=outcome,
        r_multiple=realized_r,
        risk_amount=risk_amount,
        pnl=pnl,
        balance_after=balance + pnl,
        spread_points=spread_points,
        body_ratio=signal.body_ratio,
        relative_volume=signal.relative_volume,
        fvg_confluence=signal.fvg_confluence,
        liquidity_confluence=signal.liquidity_confluence,
    )


def calculate_metrics(trades: list[Trade], starting_balance: float) -> Metrics:
    wins = [trade for trade in trades if trade.pnl > 1e-9]
    losses = [trade for trade in trades if trade.pnl < -1e-9]
    gross_profit = sum(trade.pnl for trade in wins)
    gross_loss = abs(sum(trade.pnl for trade in losses))
    ending = trades[-1].balance_after if trades else starting_balance
    equity = [starting_balance] + [trade.balance_after for trade in trades]
    peak = starting_balance
    drawdown = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak > 0:
            drawdown = max(drawdown, (peak - value) / peak * 100.0)
    factor = gross_profit / gross_loss if gross_loss else (
        math.inf if gross_profit else 0.0
    )
    return Metrics(
        starting_balance=round(starting_balance, 2),
        ending_balance=round(ending, 2),
        net_profit=round(ending - starting_balance, 2),
        return_percent=round((ending / starting_balance - 1.0) * 100.0, 2),
        trades=len(trades),
        wins=len(wins),
        losses=len(losses),
        breakeven=len(trades) - len(wins) - len(losses),
        win_rate=round(len(wins) / len(trades) * 100.0, 2) if trades else 0.0,
        profit_factor=round(factor, 3) if math.isfinite(factor) else "inf",
        average_r=round(
            sum(trade.r_multiple for trade in trades) / len(trades), 3
        )
        if trades
        else 0.0,
        max_drawdown_percent=round(drawdown, 2),
        gross_profit=round(gross_profit, 2),
        gross_loss=round(gross_loss, 2),
    )


def run_backtest(
    symbol: str,
    frame: pd.DataFrame,
    point: float,
    runtime: RuntimeConfig,
    config: StrategyConfig,
    start_date: date,
    end_date: date,
    starting_balance: float | None = None,
) -> tuple[list[Trade], Metrics, dict[str, int]]:
    prepared = frame if "_atr" in frame.columns else prepare_frame(frame)
    local = prepared.tz_convert(runtime.timezone)
    day_frames = {
        session_date: day
        for session_date, day in local.groupby(local.index.date, sort=True)
    }
    cash_sessions: dict[date, tuple[float, float]] = {}
    for session_date, day in day_frames.items():
        cash_start = _stamp(session_date, runtime.range_start, runtime.timezone)
        cash_end = _stamp(session_date, runtime.flat_time, runtime.timezone)
        cash = day[(day.index >= cash_start) & (day.index <= cash_end)]
        if not cash.empty:
            cash_sessions[session_date] = (
                float(cash["high"].max()),
                float(cash["low"].min()),
            )
    available_dates = sorted(
        item
        for item in cash_sessions
        if start_date <= item <= end_date and item.weekday() < 5
    )
    balance = starting_balance or runtime.starting_balance
    initial_balance = balance
    trades: list[Trade] = []
    reasons: Counter[str] = Counter()
    session_keys = sorted(cash_sessions)
    previous_sessions = {
        current: cash_sessions[session_keys[index - 1]] if index else None
        for index, current in enumerate(session_keys)
    }
    for session_date in available_dates:
        previous = previous_sessions[session_date]
        day = day_frames[session_date]
        signals, reason = find_day_signals(
            symbol, day, session_date, previous, runtime, config
        )
        reasons[reason] += 1
        if not signals:
            continue
        for signal in signals:
            trade = simulate_signal(day, signal, runtime, config, point, balance)
            if trade is None:
                reasons["invalid_entry_or_rr"] += 1
                continue
            trades.append(trade)
            balance = trade.balance_after
            break
    return trades, calculate_metrics(trades, initial_balance), dict(reasons)
