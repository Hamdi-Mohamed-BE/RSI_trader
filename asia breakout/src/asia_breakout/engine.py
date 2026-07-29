from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from math import inf
from typing import Iterable

import numpy as np
import pandas as pd

from .config import StrategyConfig
from .models import Metrics, Trade


@dataclass(slots=True)
class EntrySignal:
    direction: str
    time: pd.Timestamp
    entry: float
    stop: float
    target: float
    start_index: int
    ambiguous: bool = False


@dataclass(slots=True)
class PreparedSession:
    session_day: date
    day_frame: pd.DataFrame
    m15_frame: pd.DataFrame
    asian_high: float
    asian_low: float
    asian_range: float
    adr: float
    range_adr_fraction: float


def _at(day: date, value: time) -> pd.Timestamp:
    return pd.Timestamp(
        datetime.combine(day, value, tzinfo=timezone.utc)
    )


def _spread_price(row: pd.Series, point: float) -> float:
    spread = float(row.get("spread", 0.0))
    return max(spread, 0.0) * point


def _m15(frame: pd.DataFrame) -> pd.DataFrame:
    indexed = frame.set_index("time")
    result = indexed.resample("15min", label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        spread=("spread", "median"),
    )
    return result.dropna(subset=["open", "high", "low", "close"]).reset_index()


def _daily_adr(frame: pd.DataFrame, days: int) -> dict[date, float]:
    daily = (
        frame.set_index("time")
        .resample("1D", label="left", closed="left")
        .agg(high=("high", "max"), low=("low", "min"))
        .dropna()
    )
    daily["range"] = daily["high"] - daily["low"]
    daily["adr"] = daily["range"].shift(1).rolling(days, min_periods=days).mean()
    return {index.date(): float(value) for index, value in daily["adr"].items()}


def _stop_for(
    direction: str,
    stop_mode: str,
    asian_high: float,
    asian_low: float,
    buffer: float,
) -> float:
    midpoint = (asian_high + asian_low) / 2.0
    if stop_mode == "midpoint":
        return midpoint
    if stop_mode == "opposite":
        return asian_low - buffer if direction == "buy" else asian_high + buffer
    raise ValueError(f"Unknown stop mode: {stop_mode}")


def _mechanical_signal(
    day_frame: pd.DataFrame,
    config: StrategyConfig,
    asian_high: float,
    asian_low: float,
    buffer: float,
    point: float,
) -> EntrySignal | None:
    day = day_frame["time"].iloc[0].date()
    start = _at(day, config.asia_end)
    cutoff = _at(day, config.entry_cutoff)
    window = day_frame[(day_frame["time"] >= start) & (day_frame["time"] < cutoff)]
    if window.empty:
        return None
    buy_stop_base = asian_high + buffer
    sell_stop = asian_low - buffer
    spreads = window["spread"].to_numpy(dtype=float).clip(min=0.0) * point
    buy_hits = window["high"].to_numpy(dtype=float) + spreads >= buy_stop_base
    sell_hits = window["low"].to_numpy(dtype=float) <= sell_stop
    hits = np.flatnonzero(buy_hits | sell_hits)
    if not len(hits):
        return None
    position = int(hits[0])
    row = window.iloc[position]
    spread = float(spreads[position])
    buy_stop = buy_stop_base
    buy_hit = bool(buy_hits[position])
    sell_hit = bool(sell_hits[position])
    ambiguous = buy_hit and sell_hit
    if ambiguous:
        # M1 OHLC cannot reveal which side traded first. Use distance from
        # the opening quote, with ties resolved conservatively to sell.
        open_bid = float(row["open"])
        open_ask = open_bid + spread
        buy_distance = abs(buy_stop - open_ask)
        sell_distance = abs(open_bid - sell_stop)
        direction = "buy" if buy_distance < sell_distance else "sell"
    else:
        direction = "buy" if buy_hit else "sell"
    entry = buy_stop if direction == "buy" else sell_stop
    stop = _stop_for(direction, config.stop_mode, asian_high, asian_low, buffer)
    risk = entry - stop if direction == "buy" else stop - entry
    if risk <= 0:
        return None
    target = entry + config.rr * risk if direction == "buy" else entry - config.rr * risk
    return EntrySignal(
        direction,
        row["time"],
        entry,
        stop,
        target,
        int(window.index[position]),
        ambiguous,
    )


def _confirmed_signal(
    day_frame: pd.DataFrame,
    m15_frame: pd.DataFrame,
    config: StrategyConfig,
    asian_high: float,
    asian_low: float,
    buffer: float,
    point: float,
    require_retest: bool,
) -> EntrySignal | None:
    day = day_frame["time"].iloc[0].date()
    start = _at(day, config.asia_end)
    cutoff = _at(day, config.entry_cutoff)
    bars = m15_frame[
        (m15_frame["time"] >= start) & (m15_frame["time"] < cutoff)
    ].reset_index(drop=True)
    if bars.empty:
        return None
    upper = asian_high + buffer
    lower = asian_low - buffer
    breakout_i: int | None = None
    direction: str | None = None
    for i, row in bars.iterrows():
        if float(row["close"]) > upper:
            breakout_i, direction = i, "buy"
            break
        if float(row["close"]) < lower:
            breakout_i, direction = i, "sell"
            break
    if breakout_i is None or direction is None:
        return None

    signal_bar = bars.iloc[breakout_i]
    if require_retest:
        signal_bar = None
        last_i = min(breakout_i + config.retest_bars, len(bars) - 1)
        for i in range(breakout_i + 1, last_i + 1):
            candidate = bars.iloc[i]
            if direction == "buy":
                valid = float(candidate["low"]) <= upper and float(candidate["close"]) > upper
            else:
                valid = float(candidate["high"]) >= lower and float(candidate["close"]) < lower
            if valid:
                signal_bar = candidate
                break
        if signal_bar is None:
            return None

    entry_time = pd.Timestamp(signal_bar["time"]) + pd.Timedelta(minutes=15)
    if entry_time >= cutoff:
        return None
    next_rows = day_frame[day_frame["time"] >= entry_time]
    if next_rows.empty:
        return None
    row = next_rows.iloc[0]
    spread = _spread_price(row, point)
    entry = float(row["open"]) + spread if direction == "buy" else float(row["open"])
    stop = _stop_for(direction, config.stop_mode, asian_high, asian_low, buffer)
    risk = entry - stop if direction == "buy" else stop - entry
    if risk <= 0:
        return None
    target = entry + config.rr * risk if direction == "buy" else entry - config.rr * risk
    return EntrySignal(
        direction=direction,
        time=row["time"],
        entry=entry,
        stop=stop,
        target=target,
        start_index=int(row.name),
    )


def find_entry_signal(
    day_frame: pd.DataFrame,
    config: StrategyConfig,
    asian_high: float,
    asian_low: float,
    point: float,
    m15_frame: pd.DataFrame | None = None,
) -> EntrySignal | None:
    """Return the first valid entry signal for one completed Asian range."""
    buffer = (asian_high - asian_low) * config.buffer_range_fraction
    if config.entry_mode == "mechanical_oco":
        return _mechanical_signal(
            day_frame,
            config,
            asian_high,
            asian_low,
            buffer,
            point,
        )
    if config.entry_mode == "confirmed_close":
        return _confirmed_signal(
            day_frame,
            m15_frame if m15_frame is not None else _m15(day_frame),
            config,
            asian_high,
            asian_low,
            buffer,
            point,
            False,
        )
    if config.entry_mode == "close_retest":
        return _confirmed_signal(
            day_frame,
            m15_frame if m15_frame is not None else _m15(day_frame),
            config,
            asian_high,
            asian_low,
            buffer,
            point,
            True,
        )
    raise ValueError(f"Unknown entry mode: {config.entry_mode}")


def _exit_trade(
    day_frame: pd.DataFrame,
    signal: EntrySignal,
    config: StrategyConfig,
    point: float,
) -> tuple[pd.Timestamp, float, float, str, float]:
    day = signal.time.date()
    force_exit = _at(day, config.force_exit)
    after = day_frame[
        (day_frame["time"] >= signal.time) & (day_frame["time"] <= force_exit)
    ]
    if config.exit_mode == "trailing":
        return _exit_with_trailing(after, signal, config, point)
    if config.exit_mode != "fixed":
        raise ValueError(f"Unknown exit mode: {config.exit_mode}")
    if not after.empty:
        spreads = after["spread"].to_numpy(dtype=float).clip(min=0.0) * point
        if signal.direction == "buy":
            stop_hits = after["low"].to_numpy(dtype=float) <= signal.stop
            target_hits = after["high"].to_numpy(dtype=float) >= signal.target
        else:
            stop_hits = (
                after["high"].to_numpy(dtype=float) + spreads >= signal.stop
            )
            target_hits = (
                after["low"].to_numpy(dtype=float) + spreads <= signal.target
            )
        stop_indexes = np.flatnonzero(stop_hits)
        target_indexes = np.flatnonzero(target_hits)
        stop_i = int(stop_indexes[0]) if len(stop_indexes) else None
        target_i = int(target_indexes[0]) if len(target_indexes) else None
        # Stop-first is deliberately conservative if both occur in one M1 bar.
        if stop_i is not None and (target_i is None or stop_i <= target_i):
            mae_r = _mae_r(after.iloc[: stop_i + 1], signal, point)
            return after.iloc[stop_i]["time"], signal.stop, -1.0, "loss", mae_r
        if target_i is not None:
            mae_r = _mae_r(after.iloc[: target_i + 1], signal, point)
            return (
                after.iloc[target_i]["time"],
                signal.target,
                config.rr,
                "win",
                mae_r,
            )

    final_rows = day_frame[day_frame["time"] <= force_exit]
    if final_rows.empty:
        final_rows = day_frame
    row = final_rows.iloc[-1]
    spread = _spread_price(row, point)
    exit_price = float(row["close"]) if signal.direction == "buy" else float(row["close"]) + spread
    risk = signal.entry - signal.stop if signal.direction == "buy" else signal.stop - signal.entry
    pnl_r = (
        (exit_price - signal.entry) / risk
        if signal.direction == "buy"
        else (signal.entry - exit_price) / risk
    )
    outcome = "win" if pnl_r > 1e-9 else "loss" if pnl_r < -1e-9 else "breakeven"
    return row["time"], exit_price, float(pnl_r), outcome, _mae_r(
        final_rows[final_rows["time"] >= signal.time], signal, point
    )


def _exit_with_trailing(
    after: pd.DataFrame,
    signal: EntrySignal,
    config: StrategyConfig,
    point: float,
) -> tuple[pd.Timestamp, float, float, str, float]:
    """Trail only after a completed M1 bar; the updated stop applies next bar."""
    if after.empty:
        return signal.time, signal.entry, 0.0, "breakeven", 0.0
    risk = (
        signal.entry - signal.stop
        if signal.direction == "buy"
        else signal.stop - signal.entry
    )
    active_stop = signal.stop
    best_price = signal.entry
    mae_r = 0.0
    times = after["time"].tolist()
    highs = after["high"].to_numpy(dtype=float)
    lows = after["low"].to_numpy(dtype=float)
    closes = after["close"].to_numpy(dtype=float)
    spreads = after["spread"].to_numpy(dtype=float).clip(min=0.0) * point
    for index in range(len(after)):
        spread = float(spreads[index])
        if signal.direction == "buy":
            low = float(lows[index])
            high = float(highs[index])
            mae_r = min(mae_r, max(-1.0, (low - signal.entry) / risk))
            if low <= active_stop:
                pnl_r = (active_stop - signal.entry) / risk
                outcome = (
                    "win" if pnl_r > 1e-9 else "loss" if pnl_r < -1e-9 else "breakeven"
                )
                return times[index], active_stop, float(pnl_r), outcome, mae_r
            if high >= signal.target:
                return times[index], signal.target, config.rr, "win", mae_r
            best_price = max(best_price, high)
            if best_price >= signal.entry + config.trail_start_r * risk:
                candidate = max(
                    signal.entry,
                    best_price - config.trail_distance_r * risk,
                )
                active_stop = max(active_stop, candidate)
        else:
            ask_high = float(highs[index]) + spread
            ask_low = float(lows[index]) + spread
            mae_r = min(mae_r, max(-1.0, (signal.entry - ask_high) / risk))
            if ask_high >= active_stop:
                pnl_r = (signal.entry - active_stop) / risk
                outcome = (
                    "win" if pnl_r > 1e-9 else "loss" if pnl_r < -1e-9 else "breakeven"
                )
                return times[index], active_stop, float(pnl_r), outcome, mae_r
            if ask_low <= signal.target:
                return times[index], signal.target, config.rr, "win", mae_r
            best_price = min(best_price, ask_low)
            if best_price <= signal.entry - config.trail_start_r * risk:
                candidate = min(
                    signal.entry,
                    best_price + config.trail_distance_r * risk,
                )
                active_stop = min(active_stop, candidate)

    spread = float(spreads[-1])
    exit_price = (
        float(closes[-1])
        if signal.direction == "buy"
        else float(closes[-1]) + spread
    )
    pnl_r = (
        (exit_price - signal.entry) / risk
        if signal.direction == "buy"
        else (signal.entry - exit_price) / risk
    )
    outcome = "win" if pnl_r > 1e-9 else "loss" if pnl_r < -1e-9 else "breakeven"
    return times[-1], exit_price, float(pnl_r), outcome, mae_r


def _mae_r(frame: pd.DataFrame, signal: EntrySignal, point: float) -> float:
    if frame.empty:
        return 0.0
    risk = (
        signal.entry - signal.stop
        if signal.direction == "buy"
        else signal.stop - signal.entry
    )
    if signal.direction == "buy":
        raw = (float(frame["low"].min()) - signal.entry) / risk
    else:
        ask_high = (
            frame["high"].to_numpy(dtype=float)
            + frame["spread"].to_numpy(dtype=float).clip(min=0.0) * point
        )
        raw = (signal.entry - float(ask_high.max())) / risk
    # The execution model assumes a resting stop fills at its requested level.
    return float(min(0.0, max(-1.0, raw)))


def prepare_sessions(
    frame: pd.DataFrame,
    config: StrategyConfig,
    test_start: datetime | None = None,
    test_end: datetime | None = None,
) -> list[PreparedSession]:
    required = {"time", "open", "high", "low", "close", "spread"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    bars = frame.copy()
    bars["time"] = pd.to_datetime(bars["time"], utc=True)
    bars = bars.sort_values("time").reset_index(drop=True)
    adr_by_day = _daily_adr(bars, config.adr_days)
    sessions: list[PreparedSession] = []
    for session_day, day_frame in bars.groupby(bars["time"].dt.date, sort=True):
        if test_start and session_day < test_start.date():
            continue
        if test_end and session_day > test_end.date():
            continue
        day_frame = day_frame.copy().reset_index(drop=True)
        asia_start = _at(session_day, config.asia_start)
        asia_end = _at(session_day, config.asia_end)
        asia = day_frame[
            (day_frame["time"] >= asia_start) & (day_frame["time"] < asia_end)
        ]
        if len(asia) < 60:
            continue
        asian_high = float(asia["high"].max())
        asian_low = float(asia["low"].min())
        asian_range = asian_high - asian_low
        adr = adr_by_day.get(session_day, np.nan)
        if not np.isfinite(adr) or adr <= 0 or asian_range <= 0:
            continue
        range_fraction = asian_range / adr
        sessions.append(
            PreparedSession(
                session_day=session_day,
                day_frame=day_frame,
                m15_frame=_m15(day_frame),
                asian_high=asian_high,
                asian_low=asian_low,
                asian_range=asian_range,
                adr=adr,
                range_adr_fraction=range_fraction,
            )
        )
    return sessions


def backtest_prepared(
    sessions: Iterable[PreparedSession],
    symbol: str,
    point: float,
    config: StrategyConfig,
) -> list[Trade]:
    trades: list[Trade] = []
    for session in sessions:
        session_day = session.session_day
        day_frame = session.day_frame
        asian_high = session.asian_high
        asian_low = session.asian_low
        asian_range = session.asian_range
        adr = session.adr
        range_fraction = session.range_adr_fraction
        if not (
            config.min_range_adr_fraction
            <= range_fraction
            <= config.max_range_adr_fraction
        ):
            continue
        signal = find_entry_signal(
            day_frame,
            config,
            asian_high,
            asian_low,
            point,
            session.m15_frame,
        )
        if signal is None:
            continue
        exit_time, exit_price, pnl_r, outcome, mae_r = _exit_trade(
            day_frame, signal, config, point
        )
        trades.append(
            Trade(
                symbol=symbol,
                session_date=session_day,
                direction=signal.direction,
                entry_mode=config.entry_mode,
                stop_mode=config.stop_mode,
                rr_target=config.rr,
                entry_time=signal.time.isoformat(),
                exit_time=exit_time.isoformat(),
                entry=signal.entry,
                stop=signal.stop,
                target=signal.target,
                exit_price=exit_price,
                pnl_r=pnl_r,
                outcome=outcome,
                asian_high=asian_high,
                asian_low=asian_low,
                asian_range=asian_range,
                adr=adr,
                range_adr_fraction=range_fraction,
                exit_mode=config.exit_mode,
                trail_start_r=config.trail_start_r,
                trail_distance_r=config.trail_distance_r,
                mae_r=mae_r,
                ambiguous_bar=signal.ambiguous,
            )
        )
    return trades


def backtest(
    frame: pd.DataFrame,
    symbol: str,
    point: float,
    config: StrategyConfig,
    test_start: datetime | None = None,
    test_end: datetime | None = None,
) -> list[Trade]:
    sessions = prepare_sessions(frame, config, test_start, test_end)
    return backtest_prepared(sessions, symbol, point, config)


def calculate_metrics(
    trades: Iterable[Trade],
    symbol: str,
    starting_balance: float,
    risk_pct: float,
) -> Metrics:
    items = list(trades)
    wins = sum(item.pnl_r > 1e-9 for item in items)
    losses = sum(item.pnl_r < -1e-9 for item in items)
    breakeven = len(items) - wins - losses
    gross_profit = sum(max(item.pnl_r, 0.0) for item in items)
    gross_loss = abs(sum(min(item.pnl_r, 0.0) for item in items))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else inf if gross_profit > 0 else 0.0
    balance = starting_balance
    peak = balance
    max_dd = 0.0
    for trade in items:
        risk_cash = balance * (risk_pct / 100.0)
        open_equity_trough = balance + risk_cash * trade.mae_r
        if peak > 0:
            max_dd = max(max_dd, (peak - open_equity_trough) / peak * 100.0)
        balance += risk_cash * trade.pnl_r
        peak = max(peak, balance)
        if peak > 0:
            max_dd = max(max_dd, (peak - balance) / peak * 100.0)
    net_r = sum(item.pnl_r for item in items)
    return Metrics(
        symbol=symbol,
        trades=len(items),
        wins=wins,
        losses=losses,
        breakeven=breakeven,
        win_rate_pct=(wins / len(items) * 100.0) if items else 0.0,
        profit_factor=float(profit_factor),
        net_r=float(net_r),
        average_r=(net_r / len(items)) if items else 0.0,
        gross_profit_r=float(gross_profit),
        gross_loss_r=float(gross_loss),
        max_drawdown_pct=float(max_dd),
        ending_balance=float(balance),
        net_profit=float(balance - starting_balance),
        return_pct=float((balance / starting_balance - 1.0) * 100.0),
    )
