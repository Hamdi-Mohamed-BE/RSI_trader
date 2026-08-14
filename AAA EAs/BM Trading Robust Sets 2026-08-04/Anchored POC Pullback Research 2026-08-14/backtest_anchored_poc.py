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


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "Results"
COMMON_PATH = ROOT.parent / "FVG Volume Research 2026-08-14" / "backtest_fvg_volume.py"
COMMON_SPEC = importlib.util.spec_from_file_location("anchored_poc_common", COMMON_PATH)
if COMMON_SPEC is None or COMMON_SPEC.loader is None:
    raise RuntimeError(f"Cannot load common research utilities: {COMMON_PATH}")
COMMON = importlib.util.module_from_spec(COMMON_SPEC)
sys.modules[COMMON_SPEC.name] = COMMON
COMMON_SPEC.loader.exec_module(COMMON)

SOURCE_MAP = COMMON.SOURCE_MAP
load_asset = COMMON.load_asset
resample_bars = COMMON.resample_bars
pivot_flags = COMMON.pivot_flags
profile_poc = COMMON.profile_poc
simulate_metrics = COMMON.simulate_metrics
metric_dict = COMMON.metric_dict
period_metrics_from_trades = COMMON.period_metrics_from_trades

TIMEFRAMES = (5, 15, 30, 60)
PIVOTS = (2, 3, 5)
MINIMUM_LEG_ATR = (1.5, 2.5, 3.5)
STRUCTURE_MODES = (0, 1)  # break of prior swing; break plus higher-low/lower-high
REACTION_MODES = (0, 1, 2, 3)  # reclaim, wick rejection, strong body, previous-bar break
POC_TOLERANCE_ATR = (0.05, 0.15)
EXPIRY_BARS = (12, 24, 48)
STOP_MODES = (0, 1)  # swing origin; reaction-candle extreme
STOP_BUFFERS_ATR = (0.0, 0.10, 0.25)
REWARD_RISKS = (1.0, 1.5, 2.0, 2.5, 3.0)
MAX_HOLD_HOURS = (6, 24, 72)
MANAGEMENTS = (0, 1)  # fixed; break-even after +1R
PROFILE_BINS = 64
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
    reaction_mode: int
    poc_tolerance_atr: float
    expiry_bars: int


ExecutionConfig = COMMON.ExecutionConfig


def base_profile_candidates(bars: pd.DataFrame, m1: pd.DataFrame, pivot: int) -> list[dict]:
    high = bars.high.to_numpy(float)
    low = bars.low.to_numpy(float)
    atr = bars.atr.to_numpy(float)
    bar_times = bars.time.astype("int64").to_numpy()
    m1_times = m1.time.astype("int64").to_numpy()
    bar_m1 = np.searchsorted(m1_times, bar_times)
    m1_low = m1.low.to_numpy(float)
    m1_high = m1.high.to_numpy(float)
    m1_volume = m1.tick_volume.to_numpy(float)
    high_pivot = pivot_flags(high, pivot, True)
    low_pivot = pivot_flags(low, pivot, False)
    high_points: list[int] = []
    low_points: list[int] = []
    candidates: list[dict] = []

    for endpoint in range(pivot, len(bars) - pivot - 1):
        if high_pivot[endpoint]:
            if high_points and low_points:
                origin = low_points[-1]
                previous_high = high_points[-1]
                previous_low = low_points[-2] if len(low_points) >= 2 else -1
                confirmation = endpoint + pivot
                if origin < endpoint and confirmation + 1 < len(bars) and np.isfinite(atr[endpoint]):
                    leg = high[endpoint] - low[origin]
                    leg_atr = leg / max(atr[endpoint], 1e-12)
                    broke_swing = high[endpoint] > high[previous_high]
                    strict_structure = broke_swing and previous_low >= 0 and low[origin] > low[previous_low]
                    start_m1 = int(bar_m1[origin])
                    finish_m1 = int(bar_m1[endpoint + 1])
                    poc = profile_poc(
                        m1_low, m1_high, m1_volume, start_m1, finish_m1,
                        low[origin], high[endpoint], PROFILE_BINS,
                    )
                    if np.isfinite(poc):
                        candidates.append({
                            "confirmation": confirmation, "direction": 1, "poc": float(poc),
                            "swing_low": float(low[origin]), "swing_high": float(high[endpoint]),
                            "atr": float(atr[confirmation]), "leg_atr": float(leg_atr),
                            "broke_swing": bool(broke_swing), "strict_structure": bool(strict_structure),
                        })
            high_points.append(endpoint)

        if low_pivot[endpoint]:
            if low_points and high_points:
                origin = high_points[-1]
                previous_low = low_points[-1]
                previous_high = high_points[-2] if len(high_points) >= 2 else -1
                confirmation = endpoint + pivot
                if origin < endpoint and confirmation + 1 < len(bars) and np.isfinite(atr[endpoint]):
                    leg = high[origin] - low[endpoint]
                    leg_atr = leg / max(atr[endpoint], 1e-12)
                    broke_swing = low[endpoint] < low[previous_low]
                    strict_structure = broke_swing and previous_high >= 0 and high[origin] < high[previous_high]
                    start_m1 = int(bar_m1[origin])
                    finish_m1 = int(bar_m1[endpoint + 1])
                    poc = profile_poc(
                        m1_low, m1_high, m1_volume, start_m1, finish_m1,
                        low[endpoint], high[origin], PROFILE_BINS,
                    )
                    if np.isfinite(poc):
                        candidates.append({
                            "confirmation": confirmation, "direction": -1, "poc": float(poc),
                            "swing_low": float(low[endpoint]), "swing_high": float(high[origin]),
                            "atr": float(atr[confirmation]), "leg_atr": float(leg_atr),
                            "broke_swing": bool(broke_swing), "strict_structure": bool(strict_structure),
                        })
            low_points.append(endpoint)

    candidates.sort(key=lambda item: (item["confirmation"], -item["direction"]))
    return candidates


def build_signals(
    candidates: list[dict], bars: pd.DataFrame, m1: pd.DataFrame,
    minimum_leg_atr: float, structure_mode: int, reaction_mode: int,
    poc_tolerance_atr: float, expiry_bars: int,
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
        structure_ok = candidate["strict_structure"] if structure_mode == 1 else candidate["broke_swing"]
        if not structure_ok:
            continue
        direction = int(candidate["direction"])
        poc = float(candidate["poc"])
        tolerance = poc_tolerance_atr * float(candidate["atr"])
        start = int(candidate["confirmation"]) + 1
        finish = min(len(bars) - 2, start + expiry_bars)
        for bar in range(start, finish + 1):
            if direction > 0 and close[bar] < candidate["swing_low"]:
                break
            if direction < 0 and close[bar] > candidate["swing_high"]:
                break
            touched = low[bar] <= poc + tolerance and high[bar] >= poc - tolerance
            if not touched:
                continue
            candle_range = max(high[bar] - low[bar], 1e-12)
            body = abs(close[bar] - open_[bar])
            directional = close[bar] > open_[bar] if direction > 0 else close[bar] < open_[bar]
            closed_through = close[bar] >= poc if direction > 0 else close[bar] <= poc
            if direction > 0:
                rejection_wick = min(open_[bar], close[bar]) - low[bar]
                broke_previous = close[bar] > high[bar - 1]
            else:
                rejection_wick = high[bar] - max(open_[bar], close[bar])
                broke_previous = close[bar] < low[bar - 1]
            accepted = directional and (
                (reaction_mode == 0 and closed_through)
                or (reaction_mode == 1 and closed_through and rejection_wick >= max(body, 0.05 * atr[bar]))
                or (reaction_mode == 2 and closed_through and body / candle_range >= 0.55)
                or (reaction_mode == 3 and broke_previous)
            )
            if not accepted:
                continue
            entry_index = int(bar_m1[bar + 1])
            if entry_index < len(m1):
                events.append((
                    entry_index, direction, candidate["swing_low"], candidate["swing_high"],
                    low[bar], high[bar], atr[bar], bars.time.iloc[bar + 1].year, poc,
                ))
            break

    events.sort(key=lambda item: (item[0], -item[1]))
    direction_by_entry: dict[int, set[int]] = {}
    for event in events:
        direction_by_entry.setdefault(int(event[0]), set()).add(int(event[1]))
    deduplicated = []
    seen = set()
    for event in events:
        entry = int(event[0])
        direction = int(event[1])
        if len(direction_by_entry[entry]) > 1:
            continue
        key = (entry, direction)
        if key not in seen:
            seen.add(key)
            deduplicated.append(event)

    names = {
        "entries": np.int64, "directions": np.int8, "gap_lows": np.float64,
        "gap_highs": np.float64, "rejection_lows": np.float64,
        "rejection_highs": np.float64, "atrs": np.float64, "years": np.int16,
        "pocs": np.float64,
    }
    if not deduplicated:
        return {name: np.array([], dtype=dtype) for name, dtype in names.items()}
    array = np.asarray(deduplicated, dtype=float)
    return {
        "entries": array[:, 0].astype(np.int64), "directions": array[:, 1].astype(np.int8),
        "gap_lows": array[:, 2], "gap_highs": array[:, 3], "rejection_lows": array[:, 4],
        "rejection_highs": array[:, 5], "atrs": array[:, 6], "years": array[:, 7].astype(np.int16),
        "pocs": array[:, 8],
    }


def run_metrics(signals: dict, arrays: dict, median_spread: float, years: tuple[int, int], execution: ExecutionConfig) -> dict:
    return metric_dict(simulate_metrics(
        signals["entries"], signals["directions"], signals["gap_lows"], signals["gap_highs"],
        signals["rejection_lows"], signals["rejection_highs"], signals["atrs"], signals["years"],
        arrays["open"], arrays["high"], arrays["low"], arrays["close"], arrays["spread_price"],
        median_spread, years[0], years[1], execution.stop_mode, execution.stop_buffer_atr,
        execution.reward_risk, execution.maximum_hold_hours * 60, execution.management,
    ))


def candidate_score(metrics: dict) -> float:
    if metrics["trades"] < 15:
        return -1e9
    return (
        metrics["mean_r"] * math.sqrt(metrics["trades"])
        + 0.02 * min(metrics["profit_factor"], 3.0)
        - 0.002 * metrics["max_drawdown_pct"]
    )


def robust_score(train: dict, validation: dict) -> float:
    trade_penalty = 2.0 * max(0, 25 - train["trades"]) + 5.0 * max(0, 6 - validation["trades"])
    return (
        100.0 * min(train["mean_r"], validation["mean_r"])
        + 2.0 * min(train["profit_factor"], validation["profit_factor"], 3.0)
        - 0.06 * max(train["max_drawdown_pct"], validation["max_drawdown_pct"])
        + 0.10 * math.log1p(validation["trades"])
        - trade_penalty
    )


def config_record(pattern: PatternConfig, execution: ExecutionConfig, train: dict, validation: dict) -> dict:
    return {
        **asdict(pattern), **asdict(execution),
        **{f"train_{key}": value for key, value in train.items()},
        **{f"validation_{key}": value for key, value in validation.items()},
        "robust_score": robust_score(train, validation),
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
        direction = int(signals["directions"][signal])
        spread = arrays["spread_price"][entry_index] or median_spread
        entry = arrays["open"][entry_index] + (spread + slippage if direction > 0 else -slippage)
        buffer = execution.stop_buffer_atr * signals["atrs"][signal]
        if direction > 0:
            base = signals["gap_lows"][signal] if execution.stop_mode == 0 else signals["rejection_lows"][signal]
            stop = base - buffer
            distance = entry - stop
        else:
            base = signals["gap_highs"][signal] if execution.stop_mode == 0 else signals["rejection_highs"][signal]
            stop = base + buffer
            distance = stop - entry
        if distance < minimum_stop or not np.isfinite(distance):
            continue
        target = entry + direction * execution.reward_risk * distance
        active_stop = stop
        moved = False
        maximum = min(len(m1) - 1, entry_index + execution.maximum_hold_hours * 60)
        exit_index = maximum
        reason = "time"
        result_r = 0.0
        for minute in range(entry_index, maximum + 1):
            minute_spread = arrays["spread_price"][minute] or median_spread
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
                    active_stop, moved = entry, True
            if minute == maximum:
                fill = arrays["close"][minute] - slippage if direction > 0 else arrays["close"][minute] + minute_spread + slippage
                result_r = direction * (fill - entry) / distance
        balance *= max(0.0, 1.0 + RISK_FRACTION * result_r)
        rows.append({
            "entry_time_utc": m1.time.iloc[entry_index], "exit_time_utc": m1.time.iloc[exit_index],
            "direction": "long" if direction > 0 else "short", "poc": signals["pocs"][signal],
            "entry": entry, "initial_stop": stop, "target": target, "exit_reason": reason,
            "r_multiple": result_r, "balance": balance,
        })
        last_exit = exit_index
    return pd.DataFrame(rows)


def pattern_from_row(row: dict) -> PatternConfig:
    return PatternConfig(
        int(row["timeframe_minutes"]), int(row["pivot_bars"]), float(row["minimum_leg_atr"]),
        int(row["structure_mode"]), int(row["reaction_mode"]), float(row["poc_tolerance_atr"]),
        int(row["expiry_bars"]),
    )


def analyze_asset(label: str) -> dict:
    print(f"\n=== {label}: anchored POC pullback research ===", flush=True)
    m1, spec = load_asset(label)
    median_spread = float(spec["median_spread_price"])
    arrays = {
        "open": m1.open.to_numpy(float), "high": m1.high.to_numpy(float), "low": m1.low.to_numpy(float),
        "close": m1.close.to_numpy(float), "spread_price": m1.spread.to_numpy(float) * float(spec["point"]),
    }
    bars_by_tf = {timeframe: resample_bars(m1, timeframe) for timeframe in TIMEFRAMES}
    base_cache = {
        (timeframe, pivot): base_profile_candidates(bars, m1, pivot)
        for timeframe, bars in bars_by_tf.items() for pivot in PIVOTS
    }
    default_execution = ExecutionConfig(1, 0.10, 2.0, 24, 0)

    structure_rows = []
    for timeframe in TIMEFRAMES:
        bars = bars_by_tf[timeframe]
        for pivot in PIVOTS:
            candidates = base_cache[(timeframe, pivot)]
            for impulse in MINIMUM_LEG_ATR:
                for structure_mode in STRUCTURE_MODES:
                    signals = build_signals(candidates, bars, m1, impulse, structure_mode, 0, 0.15, 24)
                    train = run_metrics(signals, arrays, median_spread, (2022, 2024), default_execution)
                    if train["trades"] >= 15:
                        structure_rows.append((candidate_score(train), StructureBase(timeframe, pivot, impulse, structure_mode)))
    structure_rows.sort(key=lambda item: item[0], reverse=True)
    structure_finalists = [item[1] for item in structure_rows[:12]]
    if not structure_finalists:
        raise RuntimeError(f"{label}: no swing/POC structure produced 15 development trades")

    pattern_rows = []
    for structure in structure_finalists:
        bars = bars_by_tf[structure.timeframe_minutes]
        candidates = base_cache[(structure.timeframe_minutes, structure.pivot_bars)]
        for reaction_mode in REACTION_MODES:
            for tolerance in POC_TOLERANCE_ATR:
                for expiry in EXPIRY_BARS:
                    pattern = PatternConfig(
                        structure.timeframe_minutes, structure.pivot_bars, structure.minimum_leg_atr,
                        structure.structure_mode, reaction_mode, tolerance, expiry,
                    )
                    signals = build_signals(
                        candidates, bars, m1, structure.minimum_leg_atr, structure.structure_mode,
                        reaction_mode, tolerance, expiry,
                    )
                    train = run_metrics(signals, arrays, median_spread, (2022, 2024), default_execution)
                    if train["trades"] >= 15:
                        pattern_rows.append((candidate_score(train), pattern))
    pattern_rows.sort(key=lambda item: item[0], reverse=True)
    finalists = [item[1] for item in pattern_rows[:16]]
    if not finalists:
        raise RuntimeError(f"{label}: no POC reaction produced 15 development trades")

    signal_cache = {}
    screen_rows = []
    for pattern in finalists:
        bars = bars_by_tf[pattern.timeframe_minutes]
        signals = build_signals(
            base_cache[(pattern.timeframe_minutes, pattern.pivot_bars)], bars, m1,
            pattern.minimum_leg_atr, pattern.structure_mode, pattern.reaction_mode,
            pattern.poc_tolerance_atr, pattern.expiry_bars,
        )
        signal_cache[pattern] = signals
        for stop_mode in STOP_MODES:
            for buffer in STOP_BUFFERS_ATR:
                for reward_risk in REWARD_RISKS:
                    for hold in MAX_HOLD_HOURS:
                        for management in MANAGEMENTS:
                            execution = ExecutionConfig(stop_mode, buffer, reward_risk, hold, management)
                            train = run_metrics(signals, arrays, median_spread, (2022, 2024), execution)
                            if train["trades"] < 20:
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
        (screen.train_trades >= 25) & (screen.train_profit_factor >= 1.05)
        & (screen.train_return_pct > 0.0) & (screen.train_max_drawdown_pct < 20.0)
        & (screen.validation_trades >= 6) & (screen.validation_profit_factor >= 1.0)
        & (screen.validation_return_pct > 0.0) & (screen.validation_max_drawdown_pct < 20.0)
    ]
    selected = (gate.iloc[0] if len(gate) else screen.iloc[0]).to_dict()
    pattern = pattern_from_row(selected)
    execution = ExecutionConfig(
        int(selected["stop_mode"]), float(selected["stop_buffer_atr"]), float(selected["reward_risk"]),
        int(selected["maximum_hold_hours"]), int(selected["management"]),
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
        "strategy_source": "https://www.youtube.com/shorts/hEshGpglJUg",
        "strategy_name": "Swing-anchored Volume Profile POC Pullback Continuation",
        "data": {
            "server": "MEXAtlantic-Demo", "first_utc": m1.time.min().isoformat(),
            "last_utc": m1.time.max().isoformat(), "m1_rows": len(m1),
            "median_spread_price": median_spread, "real_volume_sum": int(spec.get("real_volume_sum", 0)),
            "volume_warning": "The CFD histories contain no centralized real volume; POC uses broker tick-volume activity.",
        },
        "selection_gate_passed_2022_2025": bool(len(gate)), "selected_pattern": asdict(pattern),
        "selected_execution": asdict(execution), "development_2022_2024": development,
        "validation_2025": validation, "confirmation_2026": confirmation, "full_2022_2026": full,
        "full_cagr_pct": cagr, "yearly": {
            str(year): period_metrics_from_trades(trades, year, year) for year in range(2022, 2027)
        },
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
    figure.suptitle("Swing-anchored tick-volume POC pullback — 1% risk per trade", fontsize=16)
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
