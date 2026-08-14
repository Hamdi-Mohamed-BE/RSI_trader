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
from numba import njit


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "Results"
COMMON_PATH = ROOT.parent / "FVG Volume Research 2026-08-14" / "backtest_fvg_volume.py"
COMMON_SPEC = importlib.util.spec_from_file_location("aaa_common_market_data", COMMON_PATH)
if COMMON_SPEC is None or COMMON_SPEC.loader is None:
    raise RuntimeError(f"Cannot load common market data module: {COMMON_PATH}")
COMMON = importlib.util.module_from_spec(COMMON_SPEC)
sys.modules[COMMON_SPEC.name] = COMMON
COMMON_SPEC.loader.exec_module(COMMON)

SOURCE_MAP = COMMON.SOURCE_MAP
load_asset = COMMON.load_asset
resample_bars = COMMON.resample_bars

TIMEFRAMES = (5, 15, 30, 60, 240)
BODY_RANGE_MAX = (0.25, 0.40)
UPPER_WICK_BODY_MIN = (2.0, 3.0)
LOWER_WICK_RANGE_MAX = (0.10, 0.20)
TREND_LOOKBACK = (3, 8)
TREND_ATR_MIN = (0.50, 1.00)
LOCATION_LOOKBACK = (10, 20)
VOLUME_MULTIPLIER = (0.0, 1.25)
ENTRY_MODES = (0, 1, 2)  # next open, low break, confirmed close below low
STOP_MODES = (0, 1)  # above shooting-star high, fixed ATR above entry
STOP_BUFFER_ATR = (0.0, 0.10, 0.25)
REWARD_RISKS = (1.0, 1.5, 2.0, 2.5, 3.0)
MAX_HOLD_HOURS = (2, 6, 24, 48)
MANAGEMENTS = (0, 1)  # fixed stop, break-even at +1R
STARTING_BALANCE = 10_000.0
RISK_FRACTION = 0.01


@dataclass(frozen=True)
class PatternConfig:
    timeframe_minutes: int
    maximum_body_range: float
    minimum_upper_wick_body: float
    maximum_lower_wick_range: float
    trend_lookback_bars: int
    minimum_trend_atr: float
    location_lookback_bars: int
    volume_multiplier: float
    entry_mode: int


@dataclass(frozen=True)
class ExecutionConfig:
    stop_mode: int
    stop_buffer_atr: float
    reward_risk: float
    maximum_hold_hours: int
    management: int


@njit(cache=True)
def simulate_metrics(
    entries: np.ndarray,
    entry_styles: np.ndarray,
    triggers: np.ndarray,
    pattern_highs: np.ndarray,
    atrs: np.ndarray,
    years: np.ndarray,
    m1_open: np.ndarray,
    m1_high: np.ndarray,
    m1_low: np.ndarray,
    m1_close: np.ndarray,
    m1_spread: np.ndarray,
    median_spread: float,
    start_year: int,
    end_year: int,
    stop_mode: int,
    stop_buffer_atr: float,
    reward_risk: float,
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
        if years[signal] < start_year or years[signal] > end_year:
            continue
        entry_index = entries[signal]
        if entry_index <= last_exit or entry_index < 0 or entry_index >= len(m1_open):
            continue
        if entry_styles[signal] == 1:
            entry = min(triggers[signal], m1_open[entry_index]) - slippage
        else:
            entry = m1_open[entry_index] - slippage
        if stop_mode == 0:
            stop = pattern_highs[signal] + stop_buffer_atr * atrs[signal]
        else:
            stop = entry + (1.0 + stop_buffer_atr) * atrs[signal]
        distance = stop - entry
        if distance < minimum_stop or not np.isfinite(distance):
            continue
        target = entry - reward_risk * distance
        active_stop = stop
        moved_to_be = False
        exit_index = min(len(m1_open) - 1, entry_index + maximum_hold_minutes)
        result_r = 0.0

        for minute in range(entry_index, exit_index + 1):
            spread = m1_spread[minute]
            if spread <= 0.0:
                spread = median_spread
            ask_high = m1_high[minute] + spread
            ask_low = m1_low[minute] + spread
            stopped = ask_high >= active_stop
            targeted = ask_low <= target
            if stopped:
                result_r = -((active_stop + slippage) - entry) / distance
                exit_index = minute
                break
            if targeted:
                result_r = -((target + slippage) - entry) / distance
                exit_index = minute
                break

            mark_price = m1_close[minute] + spread
            mark_r = -(mark_price - entry) / distance
            marked_equity = balance * (1.0 + RISK_FRACTION * mark_r)
            if marked_equity > peak:
                peak = marked_equity
            if peak > 0.0:
                drawdown = (peak - marked_equity) / peak * 100.0
                if drawdown > maximum_drawdown:
                    maximum_drawdown = drawdown

            if management == 1 and not moved_to_be and ask_low <= entry - distance:
                active_stop = entry
                moved_to_be = True
            if minute == exit_index:
                result_r = -((m1_close[minute] + spread + slippage) - entry) / distance

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


def metric_dict(values: tuple) -> dict:
    names = ["trades", "wins", "losses", "win_rate_pct", "profit_factor", "net_r", "mean_r", "return_pct", "max_drawdown_pct", "final_balance"]
    result = dict(zip(names, values))
    for name in ("trades", "wins", "losses"):
        result[name] = int(result[name])
    return result


def prepare_geometry_features(bars: pd.DataFrame) -> dict:
    open_ = bars.open.to_numpy(float)
    high = bars.high.to_numpy(float)
    low = bars.low.to_numpy(float)
    close = bars.close.to_numpy(float)
    volume = bars.tick_volume.to_numpy(float)
    atr = bars.atr.to_numpy(float)
    candle_range = high - low
    body = np.abs(close - open_)
    upper_wick = high - np.maximum(open_, close)
    lower_wick = np.minimum(open_, close) - low
    safe_body = np.maximum(body, 0.02 * candle_range)
    close_series = pd.Series(close)
    prior_close = close_series.shift(1).to_numpy()
    return {
        "open": open_, "high": high, "low": low, "close": close, "volume": volume, "atr": atr,
        "range": candle_range, "body": body, "upper_wick": upper_wick, "lower_wick": lower_wick,
        "safe_body": safe_body, "prior_close": prior_close,
        "ema20": close_series.ewm(span=20, adjust=False).mean().shift(1).to_numpy(),
        "average_volume": pd.Series(volume).shift(1).rolling(20).mean().to_numpy(),
        "trend_move": {
            lookback: prior_close - close_series.shift(lookback + 1).to_numpy()
            for lookback in TREND_LOOKBACK
        },
        "rolling_high": {
            lookback: pd.Series(high).shift(1).rolling(lookback).max().to_numpy()
            for lookback in LOCATION_LOOKBACK
        },
    }


def build_geometry_mask(bars: pd.DataFrame, config: PatternConfig, features: dict | None = None) -> np.ndarray:
    feature = prepare_geometry_features(bars) if features is None else features
    open_ = feature["open"]
    high = feature["high"]
    low = feature["low"]
    close = feature["close"]
    volume = feature["volume"]
    atr = feature["atr"]
    candle_range = feature["range"]
    body = feature["body"]
    upper_wick = feature["upper_wick"]
    lower_wick = feature["lower_wick"]
    safe_body = feature["safe_body"]
    prior_close = feature["prior_close"]
    ema20 = feature["ema20"]
    trend_move = feature["trend_move"][config.trend_lookback_bars]
    rolling_high = feature["rolling_high"][config.location_lookback_bars]
    average_volume = feature["average_volume"]

    mask = (
        (candle_range > 0.0)
        & (body / np.maximum(candle_range, 1e-12) >= 0.02)
        & (body / np.maximum(candle_range, 1e-12) <= config.maximum_body_range)
        & (upper_wick >= config.minimum_upper_wick_body * safe_body)
        & (lower_wick / np.maximum(candle_range, 1e-12) <= config.maximum_lower_wick_range)
        & (np.maximum(open_, close) <= low + 0.55 * candle_range)
        & (trend_move >= config.minimum_trend_atr * atr)
        & (prior_close > ema20)
        & (high >= rolling_high)
    )
    if config.volume_multiplier > 0.0:
        mask &= volume >= config.volume_multiplier * average_volume
    mask &= np.isfinite(atr) & np.isfinite(rolling_high) & np.isfinite(trend_move)
    return mask


def build_signals(bars: pd.DataFrame, m1: pd.DataFrame, config: PatternConfig, features: dict | None = None) -> dict[str, np.ndarray]:
    mask = build_geometry_mask(bars, config, features)
    indices = np.flatnonzero(mask)
    bar_times = bars.time.astype("int64").to_numpy()
    m1_times = m1.time.astype("int64").to_numpy()
    bar_m1 = np.searchsorted(m1_times, bar_times)
    m1_low = m1.low.to_numpy(float)
    events = []
    for pattern in indices:
        if pattern + 4 >= len(bars):
            continue
        pattern_low = float(bars.low.iloc[pattern])
        pattern_high = float(bars.high.iloc[pattern])
        atr = float(bars.atr.iloc[pattern])
        entry_index = -1
        entry_style = 0
        trigger = 0.0
        if config.entry_mode == 0:
            entry_index = int(bar_m1[pattern + 1])
        elif config.entry_mode == 1:
            start = int(bar_m1[pattern + 1])
            finish_bar = min(pattern + 4, len(bars) - 1)
            finish = int(bar_m1[finish_bar])
            for minute in range(start, min(finish + 1, len(m1_low))):
                if m1_low[minute] <= pattern_low:
                    entry_index = minute
                    entry_style = 1
                    trigger = pattern_low
                    break
        else:
            for confirmation in range(pattern + 1, min(pattern + 4, len(bars) - 1)):
                if bars.close.iloc[confirmation] < pattern_low:
                    entry_index = int(bar_m1[confirmation + 1])
                    break
        if 0 <= entry_index < len(m1):
            events.append((entry_index, entry_style, trigger, pattern_high, atr, m1.time.iloc[entry_index].year))

    events.sort(key=lambda item: item[0])
    deduplicated = []
    seen = set()
    for event in events:
        if event[0] not in seen:
            seen.add(event[0])
            deduplicated.append(event)
    if not deduplicated:
        return {
            "entries": np.array([], dtype=np.int64), "styles": np.array([], dtype=np.int8),
            "triggers": np.array([], dtype=float), "highs": np.array([], dtype=float),
            "atrs": np.array([], dtype=float), "years": np.array([], dtype=np.int16),
        }
    array = np.asarray(deduplicated, dtype=float)
    return {
        "entries": array[:, 0].astype(np.int64), "styles": array[:, 1].astype(np.int8),
        "triggers": array[:, 2], "highs": array[:, 3], "atrs": array[:, 4], "years": array[:, 5].astype(np.int16),
    }


def run_metrics(signals: dict, arrays: dict, median_spread: float, years: tuple[int, int], execution: ExecutionConfig) -> dict:
    return metric_dict(
        simulate_metrics(
            signals["entries"], signals["styles"], signals["triggers"], signals["highs"], signals["atrs"], signals["years"],
            arrays["open"], arrays["high"], arrays["low"], arrays["close"], arrays["spread"], median_spread,
            years[0], years[1], execution.stop_mode, execution.stop_buffer_atr, execution.reward_risk,
            execution.maximum_hold_hours * 60, execution.management,
        )
    )


def score(train: dict, validation: dict) -> float:
    if train["trades"] < 30 or validation["trades"] < 8:
        return -1e9
    return (
        100.0 * min(train["mean_r"], validation["mean_r"])
        + 2.0 * min(train["profit_factor"], validation["profit_factor"], 3.0)
        - 0.06 * max(train["max_drawdown_pct"], validation["max_drawdown_pct"])
        + 0.10 * math.log1p(validation["trades"])
    )


def screen_record(pattern: PatternConfig, execution: ExecutionConfig, train: dict, validation: dict) -> dict:
    return {
        **asdict(pattern), **asdict(execution),
        **{f"train_{key}": value for key, value in train.items()},
        **{f"validation_{key}": value for key, value in validation.items()},
        "robust_score": score(train, validation),
    }


def detailed_trades(signals: dict, arrays: dict, m1: pd.DataFrame, median_spread: float, execution: ExecutionConfig) -> pd.DataFrame:
    rows = []
    balance = STARTING_BALANCE
    last_exit = -1
    slippage = 0.25 * median_spread
    minimum_stop = max(2.0 * median_spread, 1e-12)
    for signal, entry_index in enumerate(signals["entries"]):
        if entry_index <= last_exit or entry_index >= len(m1):
            continue
        entry = min(signals["triggers"][signal], arrays["open"][entry_index]) - slippage if signals["styles"][signal] == 1 else arrays["open"][entry_index] - slippage
        stop = (
            signals["highs"][signal] + execution.stop_buffer_atr * signals["atrs"][signal]
            if execution.stop_mode == 0 else entry + (1.0 + execution.stop_buffer_atr) * signals["atrs"][signal]
        )
        distance = stop - entry
        if distance < minimum_stop:
            continue
        target = entry - execution.reward_risk * distance
        active_stop = stop
        moved = False
        maximum = min(len(m1) - 1, entry_index + execution.maximum_hold_hours * 60)
        exit_index = maximum
        reason = "time"
        result_r = 0.0
        for minute in range(entry_index, maximum + 1):
            spread = arrays["spread"][minute] or median_spread
            ask_high = arrays["high"][minute] + spread
            ask_low = arrays["low"][minute] + spread
            if ask_high >= active_stop:
                result_r = -((active_stop + slippage) - entry) / distance
                exit_index, reason = minute, "stop"
                break
            if ask_low <= target:
                result_r = -((target + slippage) - entry) / distance
                exit_index, reason = minute, "target"
                break
            if execution.management == 1 and not moved and ask_low <= entry - distance:
                active_stop, moved = entry, True
            if minute == maximum:
                result_r = -((arrays["close"][minute] + spread + slippage) - entry) / distance
        balance *= max(0.0, 1.0 + RISK_FRACTION * result_r)
        rows.append({
            "entry_time_utc": m1.time.iloc[entry_index], "exit_time_utc": m1.time.iloc[exit_index],
            "direction": "short", "entry": entry, "initial_stop": stop, "target": target,
            "exit_reason": reason, "r_multiple": result_r, "balance": balance,
        })
        last_exit = exit_index
    return pd.DataFrame(rows)


def analyze_asset(label: str) -> dict:
    print(f"\n=== {label}: shooting-star research ===", flush=True)
    m1, specification = load_asset(label)
    median_spread = float(specification["median_spread_price"])
    arrays = {
        "open": m1.open.to_numpy(float), "high": m1.high.to_numpy(float), "low": m1.low.to_numpy(float),
        "close": m1.close.to_numpy(float), "spread": m1.spread.to_numpy(float) * float(specification["point"]),
    }
    bars_by_timeframe = {timeframe: resample_bars(m1, timeframe) for timeframe in TIMEFRAMES}
    features_by_timeframe = {
        timeframe: prepare_geometry_features(bars)
        for timeframe, bars in bars_by_timeframe.items()
    }
    default_execution = ExecutionConfig(0, 0.10, 1.5, 6, 0)
    stage = []

    for timeframe in TIMEFRAMES:
        bars = bars_by_timeframe[timeframe]
        for body in BODY_RANGE_MAX:
            for wick in UPPER_WICK_BODY_MIN:
                for lower in LOWER_WICK_RANGE_MAX:
                    for trend in TREND_LOOKBACK:
                        for trend_atr in TREND_ATR_MIN:
                            for location in LOCATION_LOOKBACK:
                                for volume in VOLUME_MULTIPLIER:
                                    for entry_mode in ENTRY_MODES:
                                        pattern = PatternConfig(timeframe, body, wick, lower, trend, trend_atr, location, volume, entry_mode)
                                        signals = build_signals(bars, m1, pattern, features_by_timeframe[timeframe])
                                        train = run_metrics(signals, arrays, median_spread, (2022, 2024), default_execution)
                                        if train["trades"] >= 20:
                                            stage_score = train["mean_r"] * math.sqrt(train["trades"]) + 0.02 * train["profit_factor"] - 0.002 * train["max_drawdown_pct"]
                                            stage.append((stage_score, pattern, train))
    stage.sort(key=lambda item: item[0], reverse=True)
    finalists = [item[1] for item in stage[:15]]
    if not finalists:
        raise RuntimeError(f"{label}: no shooting-star definition produced enough development trades")

    rows = []
    signal_cache = {
        pattern: build_signals(
            bars_by_timeframe[pattern.timeframe_minutes], m1, pattern,
            features_by_timeframe[pattern.timeframe_minutes],
        )
        for pattern in finalists
    }
    for pattern in finalists:
        signals = signal_cache[pattern]
        for stop_mode in STOP_MODES:
            for buffer in STOP_BUFFER_ATR:
                for reward_risk in REWARD_RISKS:
                    for hold in MAX_HOLD_HOURS:
                        for management in MANAGEMENTS:
                            execution = ExecutionConfig(stop_mode, buffer, reward_risk, hold, management)
                            train = run_metrics(signals, arrays, median_spread, (2022, 2024), execution)
                            if train["trades"] < 30:
                                continue
                            validation = run_metrics(signals, arrays, median_spread, (2025, 2025), execution)
                            rows.append(screen_record(pattern, execution, train, validation))
    if not rows:
        fallback_pattern = finalists[0]
        fallback_signals = signal_cache[fallback_pattern]
        rows.append(screen_record(
            fallback_pattern, default_execution,
            run_metrics(fallback_signals, arrays, median_spread, (2022, 2024), default_execution),
            run_metrics(fallback_signals, arrays, median_spread, (2025, 2025), default_execution),
        ))
    screen = pd.DataFrame(rows).sort_values("robust_score", ascending=False)
    screen.to_csv(RESULTS / f"{label}-development-screen.csv", index=False)
    gate = screen.loc[
        (screen.train_profit_factor >= 1.05) & (screen.train_return_pct > 0.0) & (screen.train_max_drawdown_pct < 20.0)
        & (screen.validation_profit_factor >= 1.0) & (screen.validation_return_pct > 0.0)
        & (screen.validation_trades >= 8) & (screen.validation_max_drawdown_pct < 20.0)
    ]
    selected = (gate.iloc[0] if len(gate) else screen.iloc[0]).to_dict()
    pattern = PatternConfig(
        int(selected["timeframe_minutes"]), float(selected["maximum_body_range"]), float(selected["minimum_upper_wick_body"]),
        float(selected["maximum_lower_wick_range"]), int(selected["trend_lookback_bars"]), float(selected["minimum_trend_atr"]),
        int(selected["location_lookback_bars"]), float(selected["volume_multiplier"]), int(selected["entry_mode"]),
    )
    execution = ExecutionConfig(
        int(selected["stop_mode"]), float(selected["stop_buffer_atr"]), float(selected["reward_risk"]),
        int(selected["maximum_hold_hours"]), int(selected["management"]),
    )
    signals = signal_cache[pattern]
    development = run_metrics(signals, arrays, median_spread, (2022, 2024), execution)
    validation = run_metrics(signals, arrays, median_spread, (2025, 2025), execution)
    confirmation = run_metrics(signals, arrays, median_spread, (2026, 2026), execution)
    full = run_metrics(signals, arrays, median_spread, (2022, 2026), execution)
    years_covered = max((m1.time.max() - m1.time.min()).total_seconds() / (365.25 * 86400.0), 1e-9)
    cagr = ((full["final_balance"] / STARTING_BALANCE) ** (1.0 / years_covered) - 1.0) * 100.0
    statistical_pass = (
        confirmation["trades"] >= 8 and confirmation["profit_factor"] >= 1.05 and confirmation["return_pct"] > 0.0
        and confirmation["max_drawdown_pct"] < 15.0 and full["profit_factor"] >= 1.05
    )
    portfolio_pass = statistical_pass and cagr >= 15.0
    trades = detailed_trades(signals, arrays, m1, median_spread, execution)
    trades.to_csv(RESULTS / f"{label}-selected-trades.csv", index=False)
    result = {
        "instrument": label, "broker_symbol": specification["symbol"],
        "data": {"server": "MEXAtlantic-Demo", "first_utc": m1.time.min().isoformat(), "last_utc": m1.time.max().isoformat(),
                 "m1_rows": len(m1), "median_spread_price": median_spread, "real_volume_sum": int(specification.get("real_volume_sum", 0))},
        "selection_gate_passed_2022_2025": bool(len(gate)), "selected_pattern": asdict(pattern), "selected_execution": asdict(execution),
        "development_2022_2024": development, "validation_2025": validation, "confirmation_2026": confirmation,
        "full_2022_2026": full, "full_cagr_pct": cagr,
        "research_status": "POSITIVE_CONFIRMATION" if statistical_pass else "FAILED_CONFIRMATION",
        "final_status": "PASS" if portfolio_pass else "REJECT",
    }
    (RESULTS / f"{label}-selected-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"instrument": label, "status": result["final_status"], "pattern": asdict(pattern), "execution": asdict(execution), "confirmation": confirmation, "full": full, "cagr": cagr}, indent=2), flush=True)
    return {"result": result, "trades": trades}


def write_outputs(outputs: dict[str, dict]) -> None:
    rows = []
    figure, axes = plt.subplots(2, 3, figsize=(18, 10), constrained_layout=True)
    for axis, (label, output) in zip(axes.flat, outputs.items()):
        result, trades = output["result"], output["trades"]
        pattern = result["selected_pattern"]
        execution = result["selected_execution"]
        full = result["full_2022_2026"]
        confirmation = result["confirmation_2026"]
        rows.append({
            "status": result["final_status"], "research_status": result["research_status"], "instrument": label,
            "symbol": result["broker_symbol"], "timeframe": f"M{pattern['timeframe_minutes']}",
            **pattern, **execution, "full_trades": full["trades"], "full_win_rate_pct": full["win_rate_pct"],
            "full_pf": full["profit_factor"], "full_return_pct": full["return_pct"], "full_cagr_pct": result["full_cagr_pct"],
            "full_max_dd_pct": full["max_drawdown_pct"], "confirm_trades": confirmation["trades"],
            "confirm_win_rate_pct": confirmation["win_rate_pct"], "confirm_pf": confirmation["profit_factor"],
            "confirm_return_pct": confirmation["return_pct"], "confirm_max_dd_pct": confirmation["max_drawdown_pct"],
        })
        if trades.empty:
            axis.text(0.5, 0.5, "No trades", ha="center", va="center")
            continue
        time = pd.to_datetime(trades.entry_time_utc, utc=True)
        equity = STARTING_BALANCE * np.cumprod(1.0 + RISK_FRACTION * trades.r_multiple.to_numpy(float))
        axis.step(time, equity, where="post", linewidth=1.2)
        axis.axhline(STARTING_BALANCE, color="gray", linestyle="--", linewidth=0.8)
        axis.axvline(pd.Timestamp("2026-01-01", tz="UTC"), color="red", linestyle="--", linewidth=1.0)
        axis.set_title(f"{label} — {result['final_status']} | Full {full['return_pct']:+.1f}% PF {full['profit_factor']:.2f} | 2026 {confirmation['return_pct']:+.1f}%")
        axis.set_ylabel("Closed equity ($)")
        axis.grid(alpha=0.25)
        individual, individual_axis = plt.subplots(figsize=(12, 6), constrained_layout=True)
        individual_axis.step(time, equity, where="post")
        individual_axis.axhline(STARTING_BALANCE, color="gray", linestyle="--")
        individual_axis.axvline(pd.Timestamp("2026-01-01", tz="UTC"), color="red", linestyle="--", label="Locked 2026 confirmation")
        individual_axis.set_title(axis.get_title())
        individual_axis.set_xlabel("Date (UTC)")
        individual_axis.set_ylabel("Closed equity ($)")
        individual_axis.grid(alpha=0.25)
        individual_axis.legend()
        individual.savefig(RESULTS / f"{label}-equity.png", dpi=170)
        plt.close(individual)
    figure.suptitle("Shooting-star reversal optimization — 1% risk per trade", fontsize=16)
    figure.savefig(RESULTS / "all-markets-equity.png", dpi=180)
    plt.close(figure)
    pd.DataFrame(rows).to_csv(RESULTS / "summary.csv", index=False)
    (RESULTS / "all-results.json").write_text(json.dumps({label: output["result"] for label, output in outputs.items()}, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", nargs="*", default=list(SOURCE_MAP))
    parser.add_argument("--combine-existing", action="store_true")
    args = parser.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)
    if args.combine_existing:
        outputs = {}
        for label in SOURCE_MAP:
            result = json.loads((RESULTS / f"{label}-selected-result.json").read_text(encoding="utf-8"))
            trades = pd.read_csv(RESULTS / f"{label}-selected-trades.csv", parse_dates=["entry_time_utc", "exit_time_utc"])
            outputs[label] = {"result": result, "trades": trades}
    else:
        outputs = {label: analyze_asset(label) for label in args.assets}
    write_outputs(outputs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
