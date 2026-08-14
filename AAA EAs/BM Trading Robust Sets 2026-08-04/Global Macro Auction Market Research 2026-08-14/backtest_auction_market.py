from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from numba import njit, prange


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "Results"
COMMON_PATH = ROOT.parent / "FVG Volume Research 2026-08-14" / "backtest_fvg_volume.py"
SPEC = importlib.util.spec_from_file_location("auction_market_common", COMMON_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load common research utilities: {COMMON_PATH}")
COMMON = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = COMMON
SPEC.loader.exec_module(COMMON)

SOURCE_MAP = COMMON.SOURCE_MAP
load_asset = COMMON.load_asset
resample_bars = COMMON.resample_bars

TIMEFRAMES = (240, 1440)  # The video explicitly requires H4 or daily closes.
LOOKBACK_DAYS = (10, 20, 40, 80)
SHIFT_LAGS = (5, 10)
ENTRY_TOLERANCE_ATR = (0.0, 0.10)
BREAKOUT_EXPIRY_BARS = (3, 6)
STOP_BUFFERS_ATR = (0.0, 0.10, 0.25)
MINIMUM_RR = (1.0, 1.5)
BREAKOUT_RR = (1.5, 2.0, 3.0)
MAX_HOLD_HOURS = (72, 168, 336)
MANAGEMENTS = (0, 1)  # fixed; move stop to entry after +1R
PROFILE_BINS = 64
VALUE_AREA_FRACTION = 0.70
STARTING_BALANCE = 10_000.0
RISK_FRACTION = 0.01
INDEX_LONG_ONLY = {"US30", "US100"}


@dataclass(frozen=True)
class PatternConfig:
    model: str  # failed_auction or breakout_retest
    timeframe_minutes: int
    lookback_days: int
    regime_mode: str  # migrating_value or balanced_value
    shift_lag_days: int
    shift_threshold_atr: float
    entry_tolerance_atr: float
    retest_expiry_bars: int


@dataclass(frozen=True)
class ExecutionConfig:
    stop_buffer_atr: float
    reward_risk: float
    minimum_reward_risk: float
    maximum_hold_hours: int
    management: int


@njit(cache=True, parallel=True)
def rolling_profile_levels(
    lows: np.ndarray,
    highs: np.ndarray,
    volumes: np.ndarray,
    day_starts: np.ndarray,
    lookback_days: int,
    bins: int,
    value_area_fraction: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calculate each day's as-of-open composite POC/VAH/VAL from prior days only."""
    number_days = len(day_starts) - 1
    pocs = np.full(number_days, np.nan)
    vahs = np.full(number_days, np.nan)
    vals = np.full(number_days, np.nan)
    for day in prange(lookback_days, number_days):
        start = day_starts[day - lookback_days]
        finish = day_starts[day]
        if finish <= start:
            continue
        profile_low = lows[start]
        profile_high = highs[start]
        for minute in range(start + 1, finish):
            if lows[minute] < profile_low:
                profile_low = lows[minute]
            if highs[minute] > profile_high:
                profile_high = highs[minute]
        if profile_high <= profile_low:
            continue
        width = (profile_high - profile_low) / bins
        histogram = np.zeros(bins, dtype=np.float64)
        for minute in range(start, finish):
            low_bin = int(math.floor((lows[minute] - profile_low) / width))
            high_bin = int(math.floor((highs[minute] - profile_low) / width))
            low_bin = max(0, min(bins - 1, low_bin))
            high_bin = max(0, min(bins - 1, high_bin))
            if high_bin < low_bin:
                low_bin, high_bin = high_bin, low_bin
            allocation = max(volumes[minute], 1.0) / (high_bin - low_bin + 1)
            for level in range(low_bin, high_bin + 1):
                histogram[level] += allocation
        poc_index = 0
        total = histogram[0]
        for level in range(1, bins):
            total += histogram[level]
            if histogram[level] > histogram[poc_index]:
                poc_index = level
        target_volume = total * value_area_fraction
        low_index = poc_index
        high_index = poc_index
        included = histogram[poc_index]
        while included < target_volume and (low_index > 0 or high_index < bins - 1):
            below = histogram[low_index - 1] if low_index > 0 else -1.0
            above = histogram[high_index + 1] if high_index < bins - 1 else -1.0
            if above >= below and high_index < bins - 1:
                high_index += 1
                included += histogram[high_index]
            elif low_index > 0:
                low_index -= 1
                included += histogram[low_index]
            else:
                break
        pocs[day] = profile_low + (poc_index + 0.5) * width
        vals[day] = profile_low + low_index * width
        vahs[day] = profile_low + (high_index + 1.0) * width
    return pocs, vahs, vals


def profile_cache(m1: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]]]:
    minute_days = m1.time.dt.floor("D").astype("int64").to_numpy()
    day_numbers, day_starts = np.unique(minute_days, return_index=True)
    day_starts = np.r_[day_starts.astype(np.int64), len(m1)]
    lows = m1.low.to_numpy(float)
    highs = m1.high.to_numpy(float)
    volumes = m1.tick_volume.to_numpy(float)
    cache = {}
    for lookback in LOOKBACK_DAYS:
        print(f"  calculating {lookback}-day composite profiles", flush=True)
        cache[lookback] = rolling_profile_levels(
            lows, highs, volumes, day_starts, lookback, PROFILE_BINS, VALUE_AREA_FRACTION
        )
    return day_numbers, day_starts, cache


def empty_signals() -> dict[str, np.ndarray]:
    return {
        "entries": np.empty(0, dtype=np.int64),
        "directions": np.empty(0, dtype=np.int8),
        "stop_references": np.empty(0, dtype=float),
        "exact_targets": np.empty(0, dtype=float),
        "atrs": np.empty(0, dtype=float),
        "years": np.empty(0, dtype=np.int16),
        "pocs": np.empty(0, dtype=float),
        "vahs": np.empty(0, dtype=float),
        "vals": np.empty(0, dtype=float),
    }


def regime_allows(
    direction: int,
    current_poc: float,
    previous_poc: float,
    atr: float,
    regime_mode: str,
    threshold: float,
) -> bool:
    shift = current_poc - previous_poc
    if regime_mode == "migrating_value":
        return direction * shift >= threshold * atr and direction * shift > 0.0
    return abs(shift) <= threshold * atr


def build_signals(
    bars: pd.DataFrame,
    m1: pd.DataFrame,
    day_numbers: np.ndarray,
    levels: tuple[np.ndarray, np.ndarray, np.ndarray],
    pattern: PatternConfig,
    long_only: bool,
) -> dict[str, np.ndarray]:
    open_ = bars.open.to_numpy(float)
    high = bars.high.to_numpy(float)
    low = bars.low.to_numpy(float)
    close = bars.close.to_numpy(float)
    atr = bars.atr.to_numpy(float)
    bar_days = bars.time.dt.floor("D").astype("int64").to_numpy()
    day_indices = np.searchsorted(day_numbers, bar_days)
    bar_times = bars.time.astype("int64").to_numpy()
    m1_times = m1.time.astype("int64").to_numpy()
    bar_m1 = np.searchsorted(m1_times, bar_times)
    m1_years = m1.time.dt.year.to_numpy(np.int16)
    pocs, vahs, vals = levels
    directions = (1,) if long_only else (1, -1)
    events: list[tuple] = []

    if pattern.model == "failed_auction":
        for bar in range(1, len(bars) - 1):
            day = int(day_indices[bar])
            previous_day = day - pattern.shift_lag_days
            if day >= len(pocs) or previous_day < 0 or not np.isfinite(atr[bar]):
                continue
            poc, vah, val = pocs[day], vahs[day], vals[day]
            previous_poc = pocs[previous_day]
            if not (np.isfinite(poc) and np.isfinite(vah) and np.isfinite(val) and np.isfinite(previous_poc)):
                continue
            tolerance = pattern.entry_tolerance_atr * atr[bar]
            for direction in directions:
                if not regime_allows(
                    direction, poc, previous_poc, atr[bar], pattern.regime_mode, pattern.shift_threshold_atr
                ):
                    continue
                if direction > 0:
                    triggered = low[bar] < val and close[bar] >= val + tolerance
                    stop_reference = low[bar]
                    target = vah
                else:
                    triggered = high[bar] > vah and close[bar] <= vah - tolerance
                    stop_reference = high[bar]
                    target = val
                if not triggered:
                    continue
                entry_index = int(bar_m1[bar + 1])
                if entry_index < len(m1):
                    events.append((
                        entry_index, direction, stop_reference, target, atr[bar], int(m1_years[entry_index]),
                        poc, vah, val,
                    ))
    else:
        for breakout in range(1, len(bars) - 2):
            day = int(day_indices[breakout])
            previous_day = day - pattern.shift_lag_days
            if day >= len(pocs) or previous_day < 0 or not np.isfinite(atr[breakout]):
                continue
            poc, vah, val = pocs[day], vahs[day], vals[day]
            previous_poc = pocs[previous_day]
            if not (np.isfinite(poc) and np.isfinite(vah) and np.isfinite(val) and np.isfinite(previous_poc)):
                continue
            tolerance = pattern.entry_tolerance_atr * atr[breakout]
            for direction in directions:
                if not regime_allows(
                    direction, poc, previous_poc, atr[breakout], pattern.regime_mode,
                    pattern.shift_threshold_atr,
                ):
                    continue
                level = vah if direction > 0 else val
                crossed = (
                    close[breakout] > level + tolerance and close[breakout - 1] <= level + tolerance
                    if direction > 0
                    else close[breakout] < level - tolerance and close[breakout - 1] >= level - tolerance
                )
                if not crossed:
                    continue
                finish = min(len(bars) - 2, breakout + pattern.retest_expiry_bars)
                for retest in range(breakout + 1, finish + 1):
                    retest_tolerance = pattern.entry_tolerance_atr * atr[retest]
                    if direction > 0:
                        accepted = low[retest] <= level + retest_tolerance and close[retest] > level
                        invalid = close[retest] < val
                        stop_reference = low[retest]
                    else:
                        accepted = high[retest] >= level - retest_tolerance and close[retest] < level
                        invalid = close[retest] > vah
                        stop_reference = high[retest]
                    if invalid:
                        break
                    if not accepted:
                        continue
                    entry_index = int(bar_m1[retest + 1])
                    if entry_index < len(m1):
                        events.append((
                            entry_index, direction, stop_reference, np.nan, atr[retest],
                            int(m1_years[entry_index]), poc, vah, val,
                        ))
                    break

    if not events:
        return empty_signals()
    events.sort(key=lambda item: (item[0], -item[1]))
    deduplicated = []
    seen = set()
    for event in events:
        key = (int(event[0]), int(event[1]))
        if key not in seen:
            seen.add(key)
            deduplicated.append(event)
    array = np.asarray(deduplicated, dtype=float)
    return {
        "entries": array[:, 0].astype(np.int64),
        "directions": array[:, 1].astype(np.int8),
        "stop_references": array[:, 2],
        "exact_targets": array[:, 3],
        "atrs": array[:, 4],
        "years": array[:, 5].astype(np.int16),
        "pocs": array[:, 6],
        "vahs": array[:, 7],
        "vals": array[:, 8],
    }


@njit(cache=True)
def simulate_metrics(
    entries: np.ndarray,
    directions: np.ndarray,
    stop_references: np.ndarray,
    exact_targets: np.ndarray,
    atrs: np.ndarray,
    signal_years: np.ndarray,
    m1_open: np.ndarray,
    m1_high: np.ndarray,
    m1_low: np.ndarray,
    m1_close: np.ndarray,
    m1_spread: np.ndarray,
    median_spread: float,
    start_year: int,
    end_year: int,
    stop_buffer_atr: float,
    reward_risk: float,
    minimum_reward_risk: float,
    maximum_hold_minutes: int,
    management: int,
) -> tuple:
    balance = STARTING_BALANCE
    peak = STARTING_BALANCE
    maximum_drawdown = 0.0
    gross_profit = 0.0
    gross_loss = 0.0
    net_r = 0.0
    wins = 0
    losses = 0
    trades = 0
    last_exit = -1
    slippage = 0.25 * median_spread
    minimum_stop = max(2.0 * median_spread, 1e-12)

    for signal in range(len(entries)):
        if signal_years[signal] < start_year or signal_years[signal] > end_year:
            continue
        entry_index = entries[signal]
        if entry_index <= last_exit or entry_index < 0 or entry_index >= len(m1_open):
            continue
        direction = directions[signal]
        spread = m1_spread[entry_index]
        if spread <= 0.0:
            spread = median_spread
        entry = m1_open[entry_index] + (spread + slippage if direction > 0 else -slippage)
        stop = stop_references[signal] - stop_buffer_atr * atrs[signal] if direction > 0 else stop_references[signal] + stop_buffer_atr * atrs[signal]
        distance = entry - stop if direction > 0 else stop - entry
        if distance < minimum_stop or not np.isfinite(distance):
            continue
        if np.isfinite(exact_targets[signal]):
            target = exact_targets[signal]
            target_r = direction * (target - entry) / distance
            if target_r < minimum_reward_risk:
                continue
        else:
            target = entry + direction * reward_risk * distance
        active_stop = stop
        moved = False
        maximum = min(len(m1_open) - 1, entry_index + maximum_hold_minutes)
        exit_index = maximum
        result_r = 0.0

        for minute in range(entry_index, maximum + 1):
            minute_spread = m1_spread[minute]
            if minute_spread <= 0.0:
                minute_spread = median_spread
            if direction > 0:
                stopped = m1_low[minute] <= active_stop
                targeted = m1_high[minute] >= target
                mark = m1_close[minute]
            else:
                ask_high = m1_high[minute] + minute_spread
                ask_low = m1_low[minute] + minute_spread
                stopped = ask_high >= active_stop
                targeted = ask_low <= target
                mark = m1_close[minute] + minute_spread
            if stopped:
                fill = active_stop - slippage if direction > 0 else active_stop + slippage
                result_r = direction * (fill - entry) / distance
                exit_index = minute
                break
            if targeted:
                fill = target - slippage if direction > 0 else target + slippage
                result_r = direction * (fill - entry) / distance
                exit_index = minute
                break
            mark_r = direction * (mark - entry) / distance
            marked_equity = balance * (1.0 + RISK_FRACTION * mark_r)
            if marked_equity > peak:
                peak = marked_equity
            if peak > 0.0:
                drawdown = (peak - marked_equity) / peak * 100.0
                if drawdown > maximum_drawdown:
                    maximum_drawdown = drawdown
            if management == 1 and not moved:
                reached_one_r = (
                    m1_high[minute] >= entry + distance
                    if direction > 0
                    else m1_low[minute] + minute_spread <= entry - distance
                )
                if reached_one_r:
                    active_stop = entry
                    moved = True
            if minute == maximum:
                fill = m1_close[minute] - slippage if direction > 0 else m1_close[minute] + minute_spread + slippage
                result_r = direction * (fill - entry) / distance

        trades += 1
        if result_r > 0.0:
            wins += 1
            gross_profit += result_r
        else:
            losses += 1
            gross_loss += result_r
        net_r += result_r
        balance *= max(0.0, 1.0 + RISK_FRACTION * result_r)
        if balance > peak:
            peak = balance
        if peak > 0.0:
            drawdown = (peak - balance) / peak * 100.0
            if drawdown > maximum_drawdown:
                maximum_drawdown = drawdown
        last_exit = exit_index

    profit_factor = gross_profit / abs(gross_loss) if gross_loss < 0.0 else (999.0 if gross_profit > 0.0 else 0.0)
    win_rate = 100.0 * wins / trades if trades else 0.0
    return_pct = 100.0 * (balance / STARTING_BALANCE - 1.0)
    mean_r = net_r / trades if trades else 0.0
    return trades, wins, losses, win_rate, profit_factor, net_r, mean_r, return_pct, maximum_drawdown, balance


METRIC_KEYS = (
    "trades", "wins", "losses", "win_rate_pct", "profit_factor", "net_r", "mean_r",
    "return_pct", "max_drawdown_pct", "final_balance",
)


def run_metrics(signals: dict, arrays: dict, median_spread: float, years: tuple[int, int], execution: ExecutionConfig) -> dict:
    values = simulate_metrics(
        signals["entries"], signals["directions"], signals["stop_references"],
        signals["exact_targets"], signals["atrs"], signals["years"], arrays["open"], arrays["high"],
        arrays["low"], arrays["close"], arrays["spread"], median_spread, years[0], years[1],
        execution.stop_buffer_atr, execution.reward_risk, execution.minimum_reward_risk,
        execution.maximum_hold_hours * 60, execution.management,
    )
    result = dict(zip(METRIC_KEYS, values))
    for key in ("trades", "wins", "losses"):
        result[key] = int(result[key])
    return result


def single_score(metrics: dict) -> float:
    if metrics["trades"] < 8:
        return -1e9
    pf = min(metrics["profit_factor"], 4.0)
    return metrics["mean_r"] * math.sqrt(metrics["trades"]) + 0.04 * pf - 0.003 * metrics["max_drawdown_pct"]


def robust_score(train: dict, validation: dict) -> float:
    if train["trades"] < 12 or validation["trades"] < 2:
        return -1e9
    return (
        100.0 * min(train["mean_r"], validation["mean_r"])
        + 2.0 * min(train["profit_factor"], validation["profit_factor"], 3.0)
        - 0.06 * max(train["max_drawdown_pct"], validation["max_drawdown_pct"])
        + 0.1 * math.log1p(validation["trades"])
    )


def execution_grid(model: str):
    if model == "failed_auction":
        for buffer in STOP_BUFFERS_ATR:
            for minimum_rr in MINIMUM_RR:
                for hold in MAX_HOLD_HOURS:
                    for management in MANAGEMENTS:
                        yield ExecutionConfig(buffer, 0.0, minimum_rr, hold, management)
    else:
        for buffer in STOP_BUFFERS_ATR:
            for reward_rr in BREAKOUT_RR:
                for hold in MAX_HOLD_HOURS:
                    for management in MANAGEMENTS:
                        yield ExecutionConfig(buffer, reward_rr, 0.0, hold, management)


def default_execution(model: str) -> ExecutionConfig:
    return ExecutionConfig(0.10, 0.0, 1.0, 168, 0) if model == "failed_auction" else ExecutionConfig(0.10, 2.0, 0.0, 168, 0)


def detailed_trades(
    signals: dict,
    arrays: dict,
    m1: pd.DataFrame,
    median_spread: float,
    execution: ExecutionConfig,
) -> pd.DataFrame:
    rows = []
    balance = STARTING_BALANCE
    last_exit = -1
    slippage = 0.25 * median_spread
    minimum_stop = max(2.0 * median_spread, 1e-12)
    for signal, entry_index in enumerate(signals["entries"]):
        if entry_index <= last_exit or entry_index >= len(m1):
            continue
        direction = int(signals["directions"][signal])
        spread = arrays["spread"][entry_index]
        if spread <= 0.0:
            spread = median_spread
        entry = arrays["open"][entry_index] + (spread + slippage if direction > 0 else -slippage)
        stop = (
            signals["stop_references"][signal] - execution.stop_buffer_atr * signals["atrs"][signal]
            if direction > 0
            else signals["stop_references"][signal] + execution.stop_buffer_atr * signals["atrs"][signal]
        )
        distance = entry - stop if direction > 0 else stop - entry
        if distance < minimum_stop:
            continue
        exact = signals["exact_targets"][signal]
        if np.isfinite(exact):
            target = exact
            if direction * (target - entry) / distance < execution.minimum_reward_risk:
                continue
        else:
            target = entry + direction * execution.reward_risk * distance
        active_stop = stop
        moved = False
        maximum = min(len(m1) - 1, entry_index + execution.maximum_hold_hours * 60)
        result_r = 0.0
        reason = "time"
        exit_index = maximum
        for minute in range(entry_index, maximum + 1):
            minute_spread = arrays["spread"][minute] if arrays["spread"][minute] > 0 else median_spread
            stopped = arrays["low"][minute] <= active_stop if direction > 0 else arrays["high"][minute] + minute_spread >= active_stop
            targeted = arrays["high"][minute] >= target if direction > 0 else arrays["low"][minute] + minute_spread <= target
            if stopped:
                fill = active_stop - slippage if direction > 0 else active_stop + slippage
                result_r = direction * (fill - entry) / distance
                exit_index, reason = minute, "stop"
                break
            if targeted:
                fill = target - slippage if direction > 0 else target + slippage
                result_r = direction * (fill - entry) / distance
                exit_index, reason = minute, "target"
                break
            if execution.management == 1 and not moved:
                reached = arrays["high"][minute] >= entry + distance if direction > 0 else arrays["low"][minute] + minute_spread <= entry - distance
                if reached:
                    active_stop = entry
                    moved = True
            if minute == maximum:
                fill = arrays["close"][minute] - slippage if direction > 0 else arrays["close"][minute] + minute_spread + slippage
                result_r = direction * (fill - entry) / distance
        balance *= max(0.0, 1.0 + RISK_FRACTION * result_r)
        rows.append({
            "entry_time_utc": m1.time.iloc[entry_index], "exit_time_utc": m1.time.iloc[exit_index],
            "direction": "long" if direction > 0 else "short", "poc": signals["pocs"][signal],
            "vah": signals["vahs"][signal], "val": signals["vals"][signal], "entry": entry,
            "initial_stop": stop, "target": target, "exit_reason": reason, "r_multiple": result_r,
            "balance": balance,
        })
        last_exit = exit_index
    return pd.DataFrame(rows)


def trade_period_metrics(trades: pd.DataFrame, start_year: int, end_year: int) -> dict:
    if trades.empty:
        subset = trades
    else:
        years = pd.to_datetime(trades.entry_time_utc, utc=True).dt.year
        subset = trades.loc[(years >= start_year) & (years <= end_year)]
    if subset.empty:
        return dict(zip(METRIC_KEYS, (0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, STARTING_BALANCE)))
    r = subset.r_multiple.to_numpy(float)
    balances = STARTING_BALANCE * np.cumprod(1.0 + RISK_FRACTION * r)
    curve = np.r_[STARTING_BALANCE, balances]
    peak = np.maximum.accumulate(curve)
    drawdown = float(np.max((peak - curve) / peak * 100.0))
    profit = float(r[r > 0].sum())
    loss = float(r[r <= 0].sum())
    pf = profit / abs(loss) if loss < 0 else (999.0 if profit > 0 else 0.0)
    return {
        "trades": int(len(r)), "wins": int((r > 0).sum()), "losses": int((r <= 0).sum()),
        "win_rate_pct": float(100.0 * (r > 0).mean()), "profit_factor": float(pf),
        "net_r": float(r.sum()), "mean_r": float(r.mean()),
        "return_pct": float((balances[-1] / STARTING_BALANCE - 1.0) * 100.0),
        "max_drawdown_pct": drawdown, "final_balance": float(balances[-1]),
    }


def analyze_asset(label: str) -> dict:
    print(f"\n=== {label}: global-macro auction-market technical layer ===", flush=True)
    m1, spec = load_asset(label)
    median_spread = float(spec["median_spread_price"])
    arrays = {
        "open": m1.open.to_numpy(float), "high": m1.high.to_numpy(float),
        "low": m1.low.to_numpy(float), "close": m1.close.to_numpy(float),
        "spread": m1.spread.to_numpy(float) * float(spec["point"]),
    }
    bars_by_tf = {timeframe: resample_bars(m1, timeframe) for timeframe in TIMEFRAMES}
    day_numbers, _, profiles = profile_cache(m1)
    long_only = label in INDEX_LONG_ONLY
    signal_cache: dict[PatternConfig, dict] = {}
    stage = []

    for model in ("failed_auction", "breakout_retest"):
        for timeframe in TIMEFRAMES:
            bars = bars_by_tf[timeframe]
            for lookback in LOOKBACK_DAYS:
                for lag in SHIFT_LAGS:
                    regime_settings = (
                        ("migrating_value", 0.0), ("migrating_value", 0.25),
                        ("balanced_value", 0.25), ("balanced_value", 0.50),
                    )
                    for regime_mode, threshold in regime_settings:
                        for tolerance in ENTRY_TOLERANCE_ATR:
                            expiries = (0,) if model == "failed_auction" else BREAKOUT_EXPIRY_BARS
                            for expiry in expiries:
                                pattern = PatternConfig(
                                    model, timeframe, lookback, regime_mode, lag, threshold, tolerance, expiry
                                )
                                signals = build_signals(
                                    bars, m1, day_numbers, profiles[lookback], pattern, long_only
                                )
                                signal_cache[pattern] = signals
                                train = run_metrics(
                                    signals, arrays, median_spread, (2022, 2024), default_execution(model)
                                )
                                if train["trades"] >= 8:
                                    stage.append((single_score(train), pattern, train))
    stage.sort(key=lambda item: item[0], reverse=True)
    finalists = []
    for model in ("failed_auction", "breakout_retest"):
        finalists.extend([item[1] for item in stage if item[1].model == model][:8])
    if not finalists:
        raise RuntimeError(f"{label}: no definition produced eight development trades")

    screen_rows = []
    for pattern in finalists:
        signals = signal_cache[pattern]
        for execution in execution_grid(pattern.model):
            train = run_metrics(signals, arrays, median_spread, (2022, 2024), execution)
            if train["trades"] < 10:
                continue
            validation = run_metrics(signals, arrays, median_spread, (2025, 2025), execution)
            screen_rows.append({
                **asdict(pattern), **asdict(execution),
                **{f"train_{key}": value for key, value in train.items()},
                **{f"validation_{key}": value for key, value in validation.items()},
                "robust_score": robust_score(train, validation),
            })
    if not screen_rows:
        pattern = finalists[0]
        execution = default_execution(pattern.model)
        train = run_metrics(signal_cache[pattern], arrays, median_spread, (2022, 2024), execution)
        validation = run_metrics(signal_cache[pattern], arrays, median_spread, (2025, 2025), execution)
        screen_rows.append({
            **asdict(pattern), **asdict(execution),
            **{f"train_{key}": value for key, value in train.items()},
            **{f"validation_{key}": value for key, value in validation.items()},
            "robust_score": robust_score(train, validation),
        })
    screen = pd.DataFrame(screen_rows).sort_values("robust_score", ascending=False)
    screen.to_csv(RESULTS / f"{label}-development-screen.csv", index=False)
    gate = screen.loc[
        (screen.train_trades >= 15) & (screen.train_profit_factor >= 1.05)
        & (screen.train_return_pct > 0.0) & (screen.train_max_drawdown_pct < 25.0)
        & (screen.validation_trades >= 3) & (screen.validation_profit_factor >= 1.0)
        & (screen.validation_return_pct > 0.0) & (screen.validation_max_drawdown_pct < 20.0)
    ]
    selected = (gate.iloc[0] if len(gate) else screen.iloc[0]).to_dict()
    pattern = PatternConfig(
        str(selected["model"]), int(selected["timeframe_minutes"]), int(selected["lookback_days"]),
        str(selected["regime_mode"]), int(selected["shift_lag_days"]),
        float(selected["shift_threshold_atr"]), float(selected["entry_tolerance_atr"]),
        int(selected["retest_expiry_bars"]),
    )
    execution = ExecutionConfig(
        float(selected["stop_buffer_atr"]), float(selected["reward_risk"]),
        float(selected["minimum_reward_risk"]), int(selected["maximum_hold_hours"]),
        int(selected["management"]),
    )
    signals = signal_cache[pattern]
    development = run_metrics(signals, arrays, median_spread, (2022, 2024), execution)
    validation = run_metrics(signals, arrays, median_spread, (2025, 2025), execution)
    confirmation = run_metrics(signals, arrays, median_spread, (2026, 2026), execution)
    full = run_metrics(signals, arrays, median_spread, (2022, 2026), execution)
    trades = detailed_trades(signals, arrays, m1, median_spread, execution)
    trades.to_csv(RESULTS / f"{label}-selected-trades.csv", index=False)
    years_covered = max((m1.time.max() - m1.time.min()).total_seconds() / (365.25 * 86400.0), 1e-9)
    cagr = ((full["final_balance"] / STARTING_BALANCE) ** (1.0 / years_covered) - 1.0) * 100.0
    confirmation_pass = (
        confirmation["trades"] >= 3 and confirmation["profit_factor"] >= 1.05
        and confirmation["return_pct"] > 0.0 and confirmation["max_drawdown_pct"] < 15.0
        and full["profit_factor"] >= 1.05
    )
    final_pass = confirmation_pass and cagr >= 15.0
    result = {
        "instrument": label, "broker_symbol": spec["symbol"],
        "strategy_name": "Global Macro Auction Market technical execution layer",
        "source_transcript": str(
            Path.home() / ".codex" / "attachments" / "cb26eed0-1dc7-4e80-885f-ab1123dbcada" / "pasted-text.txt"
        ),
        "scope_warning": (
            "This test covers the objective volume-profile entry layer only. The video's discretionary "
            "macro scenario, intermarket selection, COT interpretation, and VIX context were not encoded."
        ),
        "data": {
            "server": "MEXAtlantic-Demo", "first_utc": m1.time.min().isoformat(),
            "last_utc": m1.time.max().isoformat(), "m1_rows": len(m1),
            "median_spread_price": median_spread, "real_volume_sum": int(spec.get("real_volume_sum", 0)),
            "volume_warning": "CFD real volume is unavailable; profiles use broker quote-tick activity.",
        },
        "selection_gate_passed_2022_2025": bool(len(gate)),
        "selected_pattern": asdict(pattern), "selected_execution": asdict(execution),
        "development_2022_2024": development, "validation_2025": validation,
        "confirmation_2026": confirmation, "full_2022_2026": full, "full_cagr_pct": cagr,
        "yearly": {str(year): trade_period_metrics(trades, year, year) for year in range(2022, 2027)},
        "research_status": "POSITIVE_CONFIRMATION" if confirmation_pass else "FAILED_CONFIRMATION",
        "final_status": "PASS" if final_pass else "REJECT",
    }
    (RESULTS / f"{label}-selected-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({
        "instrument": label, "status": result["final_status"], "pattern": asdict(pattern),
        "execution": asdict(execution), "confirmation": confirmation, "full": full, "cagr": cagr,
    }, indent=2), flush=True)
    return {"result": result, "trades": trades}


def write_outputs(outputs: dict[str, dict]) -> None:
    rows = []
    figure, axes = plt.subplots(2, 3, figsize=(18, 10), constrained_layout=True)
    for axis in axes.flat:
        axis.set_visible(False)
    for axis, (label, output) in zip(axes.flat, outputs.items()):
        axis.set_visible(True)
        result = output["result"]
        trades = output["trades"]
        pattern = result["selected_pattern"]
        execution = result["selected_execution"]
        full = result["full_2022_2026"]
        confirm = result["confirmation_2026"]
        rows.append({
            "status": result["final_status"], "research_status": result["research_status"],
            "instrument": label, "symbol": result["broker_symbol"],
            "timeframe": "H4" if pattern["timeframe_minutes"] == 240 else "D1",
            **pattern, **execution, "full_trades": full["trades"],
            "full_win_rate_pct": full["win_rate_pct"], "full_pf": full["profit_factor"],
            "full_return_pct": full["return_pct"], "full_cagr_pct": result["full_cagr_pct"],
            "full_max_dd_pct": full["max_drawdown_pct"], "confirm_trades": confirm["trades"],
            "confirm_win_rate_pct": confirm["win_rate_pct"], "confirm_pf": confirm["profit_factor"],
            "confirm_return_pct": confirm["return_pct"], "confirm_max_dd_pct": confirm["max_drawdown_pct"],
        })
        if trades.empty:
            axis.text(0.5, 0.5, "No trades", ha="center", va="center")
            axis.set_title(label)
            continue
        time = pd.to_datetime(trades.entry_time_utc, utc=True)
        equity = STARTING_BALANCE * np.cumprod(1.0 + RISK_FRACTION * trades.r_multiple.to_numpy(float))
        title = f"{label} — {result['final_status']} | Full {full['return_pct']:+.1f}% PF {full['profit_factor']:.2f} | 2026 {confirm['return_pct']:+.1f}%"
        axis.step(time, equity, where="post", linewidth=1.2)
        axis.axhline(STARTING_BALANCE, color="gray", linestyle="--", linewidth=0.8)
        axis.axvline(pd.Timestamp("2026-01-01", tz="UTC"), color="red", linestyle="--", linewidth=1.0)
        axis.set_title(title)
        axis.set_ylabel("Closed equity ($)")
        axis.grid(alpha=0.25)
        individual, individual_axis = plt.subplots(figsize=(12, 6), constrained_layout=True)
        individual_axis.step(time, equity, where="post")
        individual_axis.axhline(STARTING_BALANCE, color="gray", linestyle="--")
        individual_axis.axvline(pd.Timestamp("2026-01-01", tz="UTC"), color="red", linestyle="--", label="Locked 2026 confirmation")
        individual_axis.set_title(title)
        individual_axis.set_xlabel("Date (UTC)")
        individual_axis.set_ylabel("Closed equity ($)")
        individual_axis.grid(alpha=0.25)
        individual_axis.legend()
        individual.savefig(RESULTS / f"{label}-equity.png", dpi=170)
        plt.close(individual)
    figure.suptitle("Auction-market value-area models — 1% risk, realistic CFD execution", fontsize=16)
    figure.savefig(RESULTS / "all-markets-equity.png", dpi=180)
    plt.close(figure)
    pd.DataFrame(rows).to_csv(RESULTS / "summary.csv", index=False)
    (RESULTS / "all-results.json").write_text(
        json.dumps({label: output["result"] for label, output in outputs.items()}, indent=2), encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", nargs="*", default=list(SOURCE_MAP))
    parser.add_argument("--combine-existing", action="store_true")
    args = parser.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)
    if args.combine_existing:
        outputs = {}
        for label in SOURCE_MAP:
            result_path = RESULTS / f"{label}-selected-result.json"
            result = json.loads(result_path.read_text(encoding="utf-8"))
            result["source_transcript"] = str(
                Path.home() / ".codex" / "attachments" / "cb26eed0-1dc7-4e80-885f-ab1123dbcada" / "pasted-text.txt"
            )
            result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            trades = pd.read_csv(
                RESULTS / f"{label}-selected-trades.csv", parse_dates=["entry_time_utc", "exit_time_utc"]
            )
            outputs[label] = {"result": result, "trades": trades}
    else:
        outputs = {label: analyze_asset(label) for label in args.assets}
    write_outputs(outputs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
