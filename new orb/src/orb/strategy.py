from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
import csv
import math

import numpy as np
import pandas as pd

from .config import Config


@dataclass
class Setup:
    session_date: str
    direction: str
    range_high: float
    range_low: float
    range_atr_ratio: float
    daily_open: float
    breakout_time: str
    retest_time: str
    entry: float
    stop: float
    tp1: float
    tp2: float
    atr: float
    spread_points: int
    h1_score: int
    relative_volume: float
    vwap: float
    double_sweep: bool
    rejection_index: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DayAnalysis:
    session_date: str
    status: str
    reason: str
    setup: Setup | None = None


@dataclass
class Trade:
    session_date: str
    direction: str
    entry_time: str
    exit_time: str
    entry: float
    stop: float
    tp1: float
    tp2: float
    outcome: str
    r_multiple: float
    risk_amount: float
    pnl: float
    balance_after: float
    spread_points: int

    def to_dict(self) -> dict:
        return asdict(self)


def atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def _body_ratio(row: pd.Series) -> float:
    candle_range = float(row["high"] - row["low"])
    if candle_range <= 0:
        return 0.0
    return abs(float(row["close"] - row["open"])) / candle_range


def _pivots(values: pd.Series, high: bool, order: int = 2) -> list[tuple[int, float]]:
    array = values.to_numpy(dtype=float)
    result: list[tuple[int, float]] = []
    for index in range(order, len(array) - order):
        window = array[index - order : index + order + 1]
        value = array[index]
        if high and value == np.nanmax(window) and np.sum(window == value) == 1:
            result.append((index, float(value)))
        elif not high and value == np.nanmin(window) and np.sum(window == value) == 1:
            result.append((index, float(value)))
    return result


def h1_bias(
    h1: pd.DataFrame, cutoff_utc: pd.Timestamp, min_score: int = 2
) -> tuple[str | None, str, int]:
    completed = h1[h1.index + pd.Timedelta(hours=1) <= cutoff_utc].tail(120).copy()
    if len(completed) < 30:
        return None, "insufficient_h1_history", 0

    highs = _pivots(completed["high"], high=True)
    lows = _pivots(completed["low"], high=False)
    if len(highs) < 2 or len(lows) < 2:
        return None, "insufficient_h1_swings", 0

    close = completed["close"].to_numpy(dtype=float)
    ema20 = completed["close"].ewm(span=20, adjust=False).mean()
    recent_broken_high = any(
        np.nanmax(close[index + 1 :]) > price for index, price in highs[-4:] if index + 1 < len(close)
    )
    recent_broken_low = any(
        np.nanmin(close[index + 1 :]) < price for index, price in lows[-4:] if index + 1 < len(close)
    )
    bullish_score = sum(
        (
            lows[-1][1] > lows[-2][1] and highs[-1][1] >= highs[-2][1],
            recent_broken_high,
            close[-1] > float(ema20.iloc[-1])
            and float(ema20.iloc[-1]) > float(ema20.iloc[-4]),
        )
    )
    bearish_score = sum(
        (
            highs[-1][1] < highs[-2][1] and lows[-1][1] <= lows[-2][1],
            recent_broken_low,
            close[-1] < float(ema20.iloc[-1])
            and float(ema20.iloc[-1]) < float(ema20.iloc[-4]),
        )
    )
    if bullish_score >= min_score and bullish_score > bearish_score:
        return "buy", f"bullish_h1_score_{bullish_score}", bullish_score
    if bearish_score >= min_score and bearish_score > bullish_score:
        return "sell", f"bearish_h1_score_{bearish_score}", bearish_score
    return None, "h1_bias_score_below_threshold_or_tied", max(
        bullish_score, bearish_score
    )


def _local_timestamp(day: date, clock: time, timezone) -> pd.Timestamp:
    return pd.Timestamp(datetime.combine(day, clock), tz=timezone)


def load_news_blackouts(path: Path, timezone) -> list[tuple[pd.Timestamp, pd.Timestamp, str]]:
    if not path.exists():
        return []
    windows: list[tuple[pd.Timestamp, pd.Timestamp, str]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(line for line in handle if not line.lstrip().startswith("#"))
        for row in rows:
            try:
                day = date.fromisoformat(row["date"].strip())
                start = datetime.strptime(row["start_time"].strip(), "%H:%M").time()
                end = datetime.strptime(row["end_time"].strip(), "%H:%M").time()
            except (KeyError, TypeError, ValueError):
                continue
            label = row.get("event", "High-impact news").strip()
            windows.append(
                (
                    _local_timestamp(day, start, timezone),
                    _local_timestamp(day, end, timezone),
                    label,
                )
            )
    return windows


def analyze_day(
    m5: pd.DataFrame,
    h1: pd.DataFrame,
    session_date: date,
    config: Config,
    point: float,
    news_windows: list[tuple[pd.Timestamp, pd.Timestamp, str]],
) -> DayAnalysis:
    label = session_date.isoformat()
    if config.weekdays_only and session_date.weekday() >= 5:
        return DayAnalysis(label, "skipped", "weekend")

    local = m5.tz_convert(config.timezone)
    day_frame = local[local.index.date == session_date].copy()
    if day_frame.empty:
        return DayAnalysis(label, "skipped", "no_session_data")
    if "_atr" not in day_frame.columns:
        day_frame["_atr"] = atr(local).reindex(day_frame.index)

    range_start = _local_timestamp(session_date, config.range_start, config.timezone)
    range_end = range_start + pd.Timedelta(minutes=config.range_minutes)
    last_breakout = _local_timestamp(
        session_date, config.last_breakout_time, config.timezone
    )
    expected_bars = math.ceil(config.range_minutes / 5)
    opening = day_frame[(day_frame.index >= range_start) & (day_frame.index < range_end)]
    if len(opening) < expected_bars:
        return DayAnalysis(label, "skipped", "opening_range_incomplete")

    atr_value = float(opening["_atr"].iloc[-1])
    if not math.isfinite(atr_value) or atr_value <= 0:
        return DayAnalysis(label, "skipped", "atr_unavailable")
    range_high = float(opening["high"].max())
    range_low = float(opening["low"].min())
    range_width = range_high - range_low
    ratio = range_width / atr_value
    if ratio < config.range_atr_min:
        return DayAnalysis(label, "rejected", "opening_range_too_narrow")
    if ratio > config.range_atr_max:
        return DayAnalysis(label, "rejected", "opening_range_too_wide")

    for start, end, event in news_windows:
        if start < last_breakout and end > range_start:
            return DayAnalysis(label, "rejected", f"news_blackout:{event}")
    if config.require_news_file and not news_windows:
        return DayAnalysis(label, "rejected", "news_calendar_required_but_empty")

    cutoff_utc = range_end.tz_convert("UTC")
    bias, bias_reason, bias_score = h1_bias(
        h1, cutoff_utc, config.h1_min_score
    )
    if bias is None:
        return DayAnalysis(label, "rejected", bias_reason)

    daily_open = float(day_frame.iloc[0]["open"])
    candidates = day_frame[
        (day_frame.index >= range_end) & (day_frame.index <= last_breakout)
    ]
    if candidates.empty:
        return DayAnalysis(label, "skipped", "no_breakout_window_data")

    seen_high = False
    seen_low = False
    rows = list(candidates.iterrows())
    for offset, (stamp, row) in enumerate(rows):
        spread_points = int(row.get("spread", 0) or 0)
        seen_high = seen_high or float(row["high"]) > range_high
        seen_low = seen_low or float(row["low"]) < range_low
        double_sweep = seen_high and seen_low
        if double_sweep and not config.allow_double_sweep:
            return DayAnalysis(label, "rejected", "both_range_sides_swept")
        if spread_points > config.max_spread_points:
            continue

        body_ratio = _body_ratio(row)
        if body_ratio < config.breakout_body_min:
            continue
        if double_sweep and body_ratio < config.double_sweep_body_min:
            continue
        prior = day_frame[day_frame.index < stamp].tail(20)
        median_volume = float(prior["tick_volume"].median()) if not prior.empty else 0.0
        relative_volume = (
            float(row["tick_volume"]) / median_volume if median_volume > 0 else 0.0
        )
        if relative_volume < config.min_relative_volume:
            continue
        through_breakout = day_frame[day_frame.index <= stamp]
        volume_sum = float(through_breakout["tick_volume"].sum())
        if volume_sum <= 0:
            continue
        typical_price = (
            through_breakout["high"]
            + through_breakout["low"]
            + through_breakout["close"]
        ) / 3.0
        vwap = float(
            (typical_price * through_breakout["tick_volume"]).sum() / volume_sum
        )
        extension = config.breakout_extension_atr_min * atr_value
        if bias == "buy":
            is_breakout = (
                float(row["close"]) >= range_high + extension
                and float(row["close"]) > float(row["open"])
                and float(row["close"]) > daily_open
                and (not config.require_vwap or float(row["close"]) > vwap)
            )
        else:
            is_breakout = (
                float(row["close"]) <= range_low - extension
                and float(row["close"]) < float(row["open"])
                and float(row["close"]) < daily_open
                and (not config.require_vwap or float(row["close"]) < vwap)
            )
        if not is_breakout:
            continue

        tolerance = config.retest_tolerance_atr * atr_value
        retest_rows = rows[offset + 1 : offset + 1 + config.retest_bars]
        for retest_offset, (retest_stamp, retest) in enumerate(retest_rows, start=1):
            if _body_ratio(retest) < config.rejection_body_min:
                continue
            if int(retest.get("spread", 0) or 0) > config.max_spread_points:
                continue
            if bias == "buy":
                touches = (
                    float(retest["low"]) <= range_high + tolerance
                    and float(retest["low"]) >= range_high - tolerance
                )
                holds = (
                    float(retest["close"]) >= range_high
                    and float(retest["close"]) > float(retest["open"])
                )
            else:
                touches = (
                    float(retest["high"]) >= range_low - tolerance
                    and float(retest["high"]) <= range_low + tolerance
                )
                holds = (
                    float(retest["close"]) <= range_low
                    and float(retest["close"]) < float(retest["open"])
                )
            if not (touches and holds):
                continue

            buffer_price = max(config.entry_buffer_points * point, point)
            stop_buffer = max(config.sl_buffer_atr * atr_value, point)
            if bias == "buy":
                entry = float(retest["high"]) + buffer_price
                stop = float(retest["low"]) - stop_buffer
                risk = entry - stop
                tp1 = entry + risk * config.partial_r
                tp2 = entry + risk * config.runner_r
            else:
                entry = float(retest["low"]) - buffer_price
                stop = float(retest["high"]) + stop_buffer
                risk = stop - entry
                tp1 = entry - risk * config.partial_r
                tp2 = entry - risk * config.runner_r
            if risk <= point or risk > config.max_stop_atr * atr_value:
                return DayAnalysis(label, "rejected", "structural_stop_outside_limits")

            rejection_index = day_frame.index.get_loc(retest_stamp)
            setup = Setup(
                session_date=label,
                direction=bias,
                range_high=range_high,
                range_low=range_low,
                range_atr_ratio=ratio,
                daily_open=daily_open,
                breakout_time=stamp.isoformat(),
                retest_time=retest_stamp.isoformat(),
                entry=entry,
                stop=stop,
                tp1=tp1,
                tp2=tp2,
                atr=atr_value,
                spread_points=int(retest.get("spread", 0) or 0),
                h1_score=bias_score,
                relative_volume=relative_volume,
                vwap=vwap,
                double_sweep=double_sweep,
                rejection_index=int(rejection_index),
            )
            return DayAnalysis(label, "setup", "a_plus_retest_confirmed", setup)
        return DayAnalysis(label, "rejected", "breakout_not_retested_and_rejected")

    return DayAnalysis(label, "rejected", "no_confirmed_breakout")


def simulate_trade(
    day_frame_utc: pd.DataFrame,
    setup: Setup,
    config: Config,
    point: float,
    balance: float,
) -> Trade | None:
    local = day_frame_utc.tz_convert(config.timezone)
    after_rejection = local.iloc[
        setup.rejection_index + 1 : setup.rejection_index + 1 + config.entry_valid_bars
    ]
    if after_rejection.empty:
        return None

    fill_stamp = None
    fill_row = None
    fill_price = 0.0
    slip = config.slippage_points * point
    for stamp, row in after_rejection.iterrows():
        spread = float(row.get("spread", setup.spread_points) or 0) * point
        if setup.direction == "buy" and float(row["high"]) + spread >= setup.entry:
            fill_stamp, fill_row = stamp, row
            fill_price = setup.entry + slip
            break
        if setup.direction == "sell" and float(row["low"]) <= setup.entry:
            fill_stamp, fill_row = stamp, row
            fill_price = setup.entry - slip
            break
    if fill_stamp is None or fill_row is None:
        return None

    initial_risk = (
        fill_price - setup.stop
        if setup.direction == "buy"
        else setup.stop - fill_price
    )
    if initial_risk <= point:
        return None
    tp1 = (
        fill_price + initial_risk * config.partial_r
        if setup.direction == "buy"
        else fill_price - initial_risk * config.partial_r
    )
    tp2 = (
        fill_price + initial_risk * config.runner_r
        if setup.direction == "buy"
        else fill_price - initial_risk * config.runner_r
    )

    flat_stamp = _local_timestamp(
        date.fromisoformat(setup.session_date), config.flat_time, config.timezone
    )
    management = local[(local.index >= fill_stamp) & (local.index <= flat_stamp)]
    partial_fraction = config.partial_fraction
    remaining = 1.0
    realized_r = 0.0
    partial_hit = False
    active_stop = setup.stop
    outcome = "session_close"
    exit_stamp = management.index[-1] if not management.empty else fill_stamp

    for stamp, row in management.iterrows():
        spread = float(row.get("spread", setup.spread_points) or 0) * point
        if setup.direction == "buy":
            bar_high = float(row["high"])
            bar_low = float(row["low"])
            stop_hit = bar_low <= active_stop
            tp1_hit = bar_high >= tp1
            tp2_hit = bar_high >= tp2
        else:
            bar_high = float(row["high"]) + spread
            bar_low = float(row["low"]) + spread
            stop_hit = bar_high >= active_stop
            tp1_hit = bar_low <= tp1
            tp2_hit = bar_low <= tp2

        # A bar containing both the active stop and a target is scored stop-first.
        if stop_hit:
            stop_r = (
                (active_stop - fill_price) / initial_risk
                if setup.direction == "buy"
                else (fill_price - active_stop) / initial_risk
            )
            realized_r += remaining * stop_r
            outcome = "stop" if not partial_hit else "tp1_then_be"
            exit_stamp = stamp
            remaining = 0.0
            break

        if not partial_hit and tp1_hit:
            realized_r += partial_fraction * config.partial_r
            remaining -= partial_fraction
            partial_hit = True
            if config.move_sl_to_be:
                active_stop = fill_price
            if tp2_hit:
                realized_r += remaining * config.runner_r
                outcome = "tp2"
                exit_stamp = stamp
                remaining = 0.0
                break
            continue

        if partial_hit and tp2_hit:
            realized_r += remaining * config.runner_r
            outcome = "tp2"
            exit_stamp = stamp
            remaining = 0.0
            break

    if remaining > 0 and not management.empty:
        last = management.iloc[-1]
        spread = float(last.get("spread", setup.spread_points) or 0) * point
        exit_price = (
            float(last["close"])
            if setup.direction == "buy"
            else float(last["close"]) + spread
        )
        close_r = (
            (exit_price - fill_price) / initial_risk
            if setup.direction == "buy"
            else (fill_price - exit_price) / initial_risk
        )
        realized_r += remaining * close_r
        outcome = "session_close_after_tp1" if partial_hit else "session_close"

    risk_amount = balance * config.risk_percent / 100.0
    pnl = risk_amount * realized_r
    return Trade(
        session_date=setup.session_date,
        direction=setup.direction,
        entry_time=fill_stamp.isoformat(),
        exit_time=exit_stamp.isoformat(),
        entry=fill_price,
        stop=setup.stop,
        tp1=tp1,
        tp2=tp2,
        outcome=outcome,
        r_multiple=realized_r,
        risk_amount=risk_amount,
        pnl=pnl,
        balance_after=balance + pnl,
        spread_points=setup.spread_points,
    )
