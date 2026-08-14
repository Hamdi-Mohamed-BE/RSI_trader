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
COMMON_SPEC = importlib.util.spec_from_file_location("vah_engulfing_common", COMMON_PATH)
if COMMON_SPEC is None or COMMON_SPEC.loader is None:
    raise RuntimeError(f"Cannot load common research utilities: {COMMON_PATH}")
COMMON = importlib.util.module_from_spec(COMMON_SPEC)
sys.modules[COMMON_SPEC.name] = COMMON
sys.modules["anchored_poc_common"] = COMMON
COMMON_SPEC.loader.exec_module(COMMON)

SOURCE_MAP = COMMON.SOURCE_MAP
load_asset = COMMON.load_asset
resample_bars = COMMON.resample_bars
pivot_flags = COMMON.pivot_flags
simulate_metrics = COMMON.simulate_metrics
metric_dict = COMMON.metric_dict
period_metrics_from_trades = COMMON.period_metrics_from_trades

TIMEFRAMES = (5, 15, 30, 60)
PIVOTS = (2, 3, 5)
MINIMUM_LEG_ATR = (1.5, 2.5, 3.5)
STRUCTURE_MODES = (0, 1)  # higher-high break; higher-high plus higher-low
VALUE_AREA_PCT = (0.60, 0.70, 0.80)
VAH_TOLERANCE_ATR = (0.05, 0.15)
REACTION_MODES = (0, 1)  # engulfing touches VAH; VAH rejection then engulfing
EXPIRY_BARS = (12, 24, 48)
STOP_MODES = (0, 1)  # swing low; setup low
STOP_BUFFERS_ATR = (0.0, 0.10, 0.25)
MAX_HOLD_HOURS = (6, 24, 72)
PROFILE_BINS = 64
REWARD_RISK = 3.0
STARTING_BALANCE = 10_000.0
RISK_FRACTION = 0.01


@dataclass(frozen=True)
class StructureBase:
    timeframe_minutes: int
    pivot_bars: int
    minimum_leg_atr: float
    structure_mode: int


@dataclass(frozen=True)
class PatternConfig:
    timeframe_minutes: int
    pivot_bars: int
    minimum_leg_atr: float
    structure_mode: int
    value_area_pct: float
    vah_tolerance_atr: float
    reaction_mode: int
    expiry_bars: int


ExecutionConfig = COMMON.ExecutionConfig


@njit(cache=True)
def profile_levels(
    lows: np.ndarray, highs: np.ndarray, volumes: np.ndarray,
    start: int, finish: int, profile_low: float, profile_high: float,
    bins: int, value_area_fraction: float,
) -> tuple[float, float, float]:
    if finish <= start or profile_high <= profile_low:
        return np.nan, np.nan, np.nan
    histogram = np.zeros(bins, dtype=np.float64)
    width = (profile_high - profile_low) / bins
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
    target = total * value_area_fraction
    low_index = poc_index
    high_index = poc_index
    included = histogram[poc_index]
    while included < target and (low_index > 0 or high_index < bins - 1):
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
    poc = profile_low + (poc_index + 0.5) * width
    val = profile_low + low_index * width
    vah = profile_low + (high_index + 1.0) * width
    return poc, vah, val


def base_candidates(
    bars: pd.DataFrame, m1: pd.DataFrame, pivot: int, value_area_fraction: float,
) -> list[dict]:
    high = bars.high.to_numpy(float)
    low = bars.low.to_numpy(float)
    close = bars.close.to_numpy(float)
    atr = bars.atr.to_numpy(float)
    bar_times = bars.time.astype("int64").to_numpy()
    m1_times = m1.time.astype("int64").to_numpy()
    bar_m1 = np.searchsorted(m1_times, bar_times)
    m1_low = m1.low.to_numpy(float)
    m1_high = m1.high.to_numpy(float)
    m1_volume = m1.tick_volume.to_numpy(float)
    highs = pivot_flags(high, pivot, True)
    lows = pivot_flags(low, pivot, False)
    high_points: list[int] = []
    low_points: list[int] = []
    output: list[dict] = []

    for endpoint in range(pivot, len(bars) - pivot - 1):
        if highs[endpoint]:
            if high_points and low_points:
                origin = low_points[-1]
                previous_high = high_points[-1]
                previous_low = low_points[-2] if len(low_points) >= 2 else -1
                confirmation = endpoint + pivot
                if origin < endpoint and confirmation + 1 < len(bars) and np.isfinite(atr[endpoint]):
                    leg = high[endpoint] - low[origin]
                    leg_atr = leg / max(atr[endpoint], 1e-12)
                    broke_high = high[endpoint] > high[previous_high]
                    strict = broke_high and previous_low >= 0 and low[origin] > low[previous_low]
                    start_m1 = int(bar_m1[origin])
                    finish_m1 = int(bar_m1[endpoint + 1])
                    poc, vah, val = profile_levels(
                        m1_low, m1_high, m1_volume, start_m1, finish_m1,
                        low[origin], high[endpoint], PROFILE_BINS, value_area_fraction,
                    )
                    if np.isfinite(poc) and close[confirmation] > vah:
                        output.append({
                            "confirmation": confirmation, "swing_low": float(low[origin]),
                            "swing_high": float(high[endpoint]), "atr": float(atr[confirmation]),
                            "leg_atr": float(leg_atr), "broke_high": bool(broke_high),
                            "strict_structure": bool(strict), "poc": float(poc),
                            "vah": float(vah), "val": float(val),
                        })
            high_points.append(endpoint)
        if lows[endpoint]:
            low_points.append(endpoint)
    output.sort(key=lambda item: item["confirmation"])
    return output


def bullish_engulfing(open_: np.ndarray, close: np.ndarray, bar: int, tolerance: float) -> bool:
    if bar <= 0 or close[bar - 1] >= open_[bar - 1] or close[bar] <= open_[bar]:
        return False
    return open_[bar] <= close[bar - 1] + tolerance and close[bar] >= open_[bar - 1]


def build_signals(
    candidates: list[dict], bars: pd.DataFrame, m1: pd.DataFrame,
    minimum_leg_atr: float, structure_mode: int, vah_tolerance_atr: float,
    reaction_mode: int, expiry_bars: int,
) -> dict[str, np.ndarray]:
    open_ = bars.open.to_numpy(float)
    high = bars.high.to_numpy(float)
    low = bars.low.to_numpy(float)
    close = bars.close.to_numpy(float)
    atr = bars.atr.to_numpy(float)
    bar_times = bars.time.astype("int64").to_numpy()
    m1_times = m1.time.astype("int64").to_numpy()
    bar_m1 = np.searchsorted(m1_times, bar_times)
    events = []

    for candidate in candidates:
        if candidate["leg_atr"] < minimum_leg_atr:
            continue
        structure_ok = candidate["strict_structure"] if structure_mode == 1 else candidate["broke_high"]
        if not structure_ok:
            continue
        vah = candidate["vah"]
        tolerance = vah_tolerance_atr * candidate["atr"]
        start = candidate["confirmation"] + 1
        finish = min(len(bars) - 2, start + expiry_bars)
        rejection_bar = -1
        for bar in range(start, finish + 1):
            if close[bar] < candidate["poc"]:
                break
            touched = low[bar] <= vah + tolerance and high[bar] >= vah - tolerance
            held_vah = close[bar] >= vah
            if reaction_mode == 0:
                accepted = touched and held_vah and bullish_engulfing(open_, close, bar, tolerance)
                setup_low = low[bar]
            else:
                if rejection_bar < 0 and touched and held_vah and close[bar] > open_[bar]:
                    rejection_bar = bar
                    continue
                accepted = (
                    rejection_bar >= 0 and bar <= rejection_bar + 2
                    and bullish_engulfing(open_, close, bar, tolerance)
                )
                setup_low = min(low[rejection_bar], low[bar]) if rejection_bar >= 0 else low[bar]
                if rejection_bar >= 0 and bar > rejection_bar + 2:
                    rejection_bar = -1
            if not accepted:
                continue
            entry_index = int(bar_m1[bar + 1])
            if entry_index < len(m1):
                events.append((
                    entry_index, 1, candidate["swing_low"], candidate["swing_high"],
                    setup_low, high[bar], atr[bar], bars.time.iloc[bar + 1].year,
                    candidate["poc"], candidate["vah"], candidate["val"],
                ))
            break

    events.sort(key=lambda item: item[0])
    deduplicated = []
    seen = set()
    for event in events:
        if event[0] not in seen:
            seen.add(event[0])
            deduplicated.append(event)
    names = {
        "entries": np.int64, "directions": np.int8, "gap_lows": np.float64,
        "gap_highs": np.float64, "rejection_lows": np.float64,
        "rejection_highs": np.float64, "atrs": np.float64, "years": np.int16,
        "pocs": np.float64, "vahs": np.float64, "vals": np.float64,
    }
    if not deduplicated:
        return {name: np.array([], dtype=dtype) for name, dtype in names.items()}
    array = np.asarray(deduplicated, dtype=float)
    return {
        "entries": array[:, 0].astype(np.int64), "directions": array[:, 1].astype(np.int8),
        "gap_lows": array[:, 2], "gap_highs": array[:, 3], "rejection_lows": array[:, 4],
        "rejection_highs": array[:, 5], "atrs": array[:, 6], "years": array[:, 7].astype(np.int16),
        "pocs": array[:, 8], "vahs": array[:, 9], "vals": array[:, 10],
    }


def run_metrics(signals: dict, arrays: dict, median_spread: float, years: tuple[int, int], execution: ExecutionConfig) -> dict:
    return metric_dict(simulate_metrics(
        signals["entries"], signals["directions"], signals["gap_lows"], signals["gap_highs"],
        signals["rejection_lows"], signals["rejection_highs"], signals["atrs"], signals["years"],
        arrays["open"], arrays["high"], arrays["low"], arrays["close"], arrays["spread_price"],
        median_spread, years[0], years[1], execution.stop_mode, execution.stop_buffer_atr,
        REWARD_RISK, execution.maximum_hold_hours * 60, 0,
    ))


def score_single(metrics: dict) -> float:
    if metrics["trades"] < 12:
        return -1e9
    return metrics["mean_r"] * math.sqrt(metrics["trades"]) + 0.02 * min(metrics["profit_factor"], 3.0) - 0.002 * metrics["max_drawdown_pct"]


def robust_score(train: dict, validation: dict) -> float:
    trade_penalty = 2.0 * max(0, 20 - train["trades"]) + 5.0 * max(0, 5 - validation["trades"])
    return (
        100.0 * min(train["mean_r"], validation["mean_r"])
        + 2.0 * min(train["profit_factor"], validation["profit_factor"], 3.0)
        - 0.06 * max(train["max_drawdown_pct"], validation["max_drawdown_pct"])
        + 0.1 * math.log1p(validation["trades"]) - trade_penalty
    )


def config_record(pattern: PatternConfig, execution: ExecutionConfig, train: dict, validation: dict) -> dict:
    return {
        **asdict(pattern), **asdict(execution),
        **{f"train_{key}": value for key, value in train.items()},
        **{f"validation_{key}": value for key, value in validation.items()},
        "robust_score": robust_score(train, validation),
    }


def pattern_from_row(row: dict) -> PatternConfig:
    return PatternConfig(
        int(row["timeframe_minutes"]), int(row["pivot_bars"]), float(row["minimum_leg_atr"]),
        int(row["structure_mode"]), float(row["value_area_pct"]), float(row["vah_tolerance_atr"]),
        int(row["reaction_mode"]), int(row["expiry_bars"]),
    )


def detailed_trades(signals: dict, arrays: dict, m1: pd.DataFrame, median_spread: float, execution: ExecutionConfig) -> pd.DataFrame:
    rows = []
    balance = STARTING_BALANCE
    last_exit = -1
    slippage = 0.25 * median_spread
    minimum_stop = max(2.0 * median_spread, 1e-12)
    for signal, entry_index in enumerate(signals["entries"]):
        if entry_index <= last_exit or entry_index >= len(m1):
            continue
        spread = arrays["spread_price"][entry_index] or median_spread
        entry = arrays["open"][entry_index] + spread + slippage
        base = signals["gap_lows"][signal] if execution.stop_mode == 0 else signals["rejection_lows"][signal]
        stop = base - execution.stop_buffer_atr * signals["atrs"][signal]
        distance = entry - stop
        if distance < minimum_stop or not np.isfinite(distance):
            continue
        target = entry + REWARD_RISK * distance
        maximum = min(len(m1) - 1, entry_index + execution.maximum_hold_hours * 60)
        exit_index = maximum
        reason = "time"
        result_r = 0.0
        for minute in range(entry_index, maximum + 1):
            if arrays["low"][minute] <= stop:
                result_r = (stop - slippage - entry) / distance
                exit_index, reason = minute, "stop"
                break
            if arrays["high"][minute] >= target:
                result_r = (target - slippage - entry) / distance
                exit_index, reason = minute, "target"
                break
            if minute == maximum:
                result_r = (arrays["close"][minute] - slippage - entry) / distance
        balance *= max(0.0, 1.0 + RISK_FRACTION * result_r)
        rows.append({
            "entry_time_utc": m1.time.iloc[entry_index], "exit_time_utc": m1.time.iloc[exit_index],
            "direction": "long", "poc": signals["pocs"][signal], "vah": signals["vahs"][signal],
            "val": signals["vals"][signal], "entry": entry, "initial_stop": stop, "target": target,
            "exit_reason": reason, "r_multiple": result_r, "balance": balance,
        })
        last_exit = exit_index
    return pd.DataFrame(rows)


def analyze_asset(label: str) -> dict:
    print(f"\n=== {label}: VAH engulfing research ===", flush=True)
    m1, spec = load_asset(label)
    median_spread = float(spec["median_spread_price"])
    arrays = {
        "open": m1.open.to_numpy(float), "high": m1.high.to_numpy(float), "low": m1.low.to_numpy(float),
        "close": m1.close.to_numpy(float), "spread_price": m1.spread.to_numpy(float) * float(spec["point"]),
    }
    bars_by_tf = {timeframe: resample_bars(m1, timeframe) for timeframe in TIMEFRAMES}
    base_cache = {
        (timeframe, pivot, value_area): base_candidates(bars, m1, pivot, value_area)
        for timeframe, bars in bars_by_tf.items() for pivot in PIVOTS for value_area in VALUE_AREA_PCT
    }
    default_execution = ExecutionConfig(1, 0.10, REWARD_RISK, 24, 0)

    structures = []
    for timeframe in TIMEFRAMES:
        bars = bars_by_tf[timeframe]
        for pivot in PIVOTS:
            candidates = base_cache[(timeframe, pivot, 0.70)]
            for impulse in MINIMUM_LEG_ATR:
                for structure_mode in STRUCTURE_MODES:
                    signals = build_signals(candidates, bars, m1, impulse, structure_mode, 0.05, 0, 24)
                    train = run_metrics(signals, arrays, median_spread, (2022, 2024), default_execution)
                    if train["trades"] >= 12:
                        structures.append((score_single(train), StructureBase(timeframe, pivot, impulse, structure_mode)))
    structures.sort(key=lambda item: item[0], reverse=True)
    structure_finalists = [item[1] for item in structures[:12]]
    if not structure_finalists:
        raise RuntimeError(f"{label}: no literal VAH-engulfing definition produced 12 development trades")

    patterns = []
    for structure in structure_finalists:
        bars = bars_by_tf[structure.timeframe_minutes]
        for value_area in VALUE_AREA_PCT:
            candidates = base_cache[(structure.timeframe_minutes, structure.pivot_bars, value_area)]
            for tolerance in VAH_TOLERANCE_ATR:
                for reaction_mode in REACTION_MODES:
                    for expiry in EXPIRY_BARS:
                        pattern = PatternConfig(
                            structure.timeframe_minutes, structure.pivot_bars, structure.minimum_leg_atr,
                            structure.structure_mode, value_area, tolerance, reaction_mode, expiry,
                        )
                        signals = build_signals(
                            candidates, bars, m1, structure.minimum_leg_atr, structure.structure_mode,
                            tolerance, reaction_mode, expiry,
                        )
                        train = run_metrics(signals, arrays, median_spread, (2022, 2024), default_execution)
                        if train["trades"] >= 12:
                            patterns.append((score_single(train), pattern))
    patterns.sort(key=lambda item: item[0], reverse=True)
    finalists = [item[1] for item in patterns[:16]]
    if not finalists:
        raise RuntimeError(f"{label}: no VAH reaction finalist had enough development trades")

    signal_cache = {}
    screen_rows = []
    for pattern in finalists:
        signals = build_signals(
            base_cache[(pattern.timeframe_minutes, pattern.pivot_bars, pattern.value_area_pct)],
            bars_by_tf[pattern.timeframe_minutes], m1, pattern.minimum_leg_atr,
            pattern.structure_mode, pattern.vah_tolerance_atr, pattern.reaction_mode, pattern.expiry_bars,
        )
        signal_cache[pattern] = signals
        for stop_mode in STOP_MODES:
            for buffer in STOP_BUFFERS_ATR:
                for hold in MAX_HOLD_HOURS:
                    execution = ExecutionConfig(stop_mode, buffer, REWARD_RISK, hold, 0)
                    train = run_metrics(signals, arrays, median_spread, (2022, 2024), execution)
                    if train["trades"] < 15:
                        continue
                    validation = run_metrics(signals, arrays, median_spread, (2025, 2025), execution)
                    screen_rows.append(config_record(pattern, execution, train, validation))
    if not screen_rows:
        fallback = finalists[0]
        signals = signal_cache[fallback]
        screen_rows.append(config_record(
            fallback, default_execution,
            run_metrics(signals, arrays, median_spread, (2022, 2024), default_execution),
            run_metrics(signals, arrays, median_spread, (2025, 2025), default_execution),
        ))
    screen = pd.DataFrame(screen_rows).sort_values("robust_score", ascending=False)
    screen.to_csv(RESULTS / f"{label}-development-screen.csv", index=False)
    gate = screen.loc[
        (screen.train_trades >= 20) & (screen.train_profit_factor >= 1.05)
        & (screen.train_return_pct > 0.0) & (screen.train_max_drawdown_pct < 20.0)
        & (screen.validation_trades >= 5) & (screen.validation_profit_factor >= 1.0)
        & (screen.validation_return_pct > 0.0) & (screen.validation_max_drawdown_pct < 20.0)
    ]
    selected = (gate.iloc[0] if len(gate) else screen.iloc[0]).to_dict()
    pattern = pattern_from_row(selected)
    execution = ExecutionConfig(
        int(selected["stop_mode"]), float(selected["stop_buffer_atr"]), REWARD_RISK,
        int(selected["maximum_hold_hours"]), 0,
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
    statistical_pass = (
        confirmation["trades"] >= 8 and confirmation["profit_factor"] >= 1.05
        and confirmation["return_pct"] > 0.0 and confirmation["max_drawdown_pct"] < 15.0
        and full["profit_factor"] >= 1.05
    )
    final_pass = statistical_pass and cagr >= 15.0
    result = {
        "instrument": label, "broker_symbol": spec["symbol"],
        "strategy_source": "https://www.youtube.com/shorts/xGHhSs3ENyk",
        "strategy_name": "Long-only VAH Rejection Bullish Engulfing 3R",
        "data": {
            "server": "MEXAtlantic-Demo", "first_utc": m1.time.min().isoformat(),
            "last_utc": m1.time.max().isoformat(), "m1_rows": len(m1),
            "median_spread_price": median_spread, "real_volume_sum": int(spec.get("real_volume_sum", 0)),
            "volume_warning": "The CFD histories contain no centralized real volume; the profile uses broker tick activity.",
        },
        "selection_gate_passed_2022_2025": bool(len(gate)), "selected_pattern": asdict(pattern),
        "selected_execution": asdict(execution), "development_2022_2024": development,
        "validation_2025": validation, "confirmation_2026": confirmation,
        "full_2022_2026": full, "full_cagr_pct": cagr,
        "yearly": {str(year): period_metrics_from_trades(trades, year, year) for year in range(2022, 2027)},
        "research_status": "POSITIVE_CONFIRMATION" if statistical_pass else "FAILED_CONFIRMATION",
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
    for axis, (label, output) in zip(axes.flat, outputs.items()):
        result = output["result"]
        trades = output["trades"]
        pattern = result["selected_pattern"]
        execution = result["selected_execution"]
        full = result["full_2022_2026"]
        confirm = result["confirmation_2026"]
        rows.append({
            "status": result["final_status"], "research_status": result["research_status"],
            "instrument": label, "symbol": result["broker_symbol"],
            "timeframe": f"M{pattern['timeframe_minutes']}", **pattern, **execution,
            "full_trades": full["trades"], "full_win_rate_pct": full["win_rate_pct"],
            "full_pf": full["profit_factor"], "full_return_pct": full["return_pct"],
            "full_cagr_pct": result["full_cagr_pct"], "full_max_dd_pct": full["max_drawdown_pct"],
            "confirm_trades": confirm["trades"], "confirm_win_rate_pct": confirm["win_rate_pct"],
            "confirm_pf": confirm["profit_factor"], "confirm_return_pct": confirm["return_pct"],
            "confirm_max_dd_pct": confirm["max_drawdown_pct"],
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
    figure.suptitle("Long-only VAH rejection + bullish engulfing — fixed 3R, 1% risk", fontsize=16)
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
            result = json.loads((RESULTS / f"{label}-selected-result.json").read_text(encoding="utf-8"))
            trades = pd.read_csv(RESULTS / f"{label}-selected-trades.csv", parse_dates=["entry_time_utc", "exit_time_utc"])
            outputs[label] = {"result": result, "trades": trades}
    else:
        outputs = {label: analyze_asset(label) for label in args.assets}
    write_outputs(outputs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
