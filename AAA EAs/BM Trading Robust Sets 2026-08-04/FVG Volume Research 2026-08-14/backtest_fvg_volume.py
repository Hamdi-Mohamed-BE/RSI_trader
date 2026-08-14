from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from numba import njit


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "Results"
PROJECT = ROOT.parent

SOURCE_MAP = {
    "XAU": (
        PROJECT / "Apex Pulse and IVB Research 2026-08-10" / "Data",
        "XAU",
        "MEXAtlantic-XAU-*-M1-*.csv.gz",
    ),
    "XAG": (ROOT / "Data", "XAG", "MEXAtlantic-XAG-*-M1-*.csv.gz"),
    "US30": (
        PROJECT / "Apex Pulse and IVB Research 2026-08-10" / "Data",
        "US30",
        "MEXAtlantic-US30-*-M1-*.csv.gz",
    ),
    "US100": (
        PROJECT / "Apex Pulse and IVB Research 2026-08-10" / "Data",
        "US100",
        "MEXAtlantic-US100-*-M1-*.csv.gz",
    ),
    "BTC": (
        PROJECT / "Daily Bias AMD Validation 2026-08-10" / "Data",
        "BTC",
        "MEXAtlantic-BTC-*-M1-*.csv.gz",
    ),
    "ETH": (ROOT / "Data", "ETH", "MEXAtlantic-ETH-*-M1-*.csv.gz"),
}

TIMEFRAMES = (5, 15, 30)
PIVOTS = (3, 5)
IMPULSE_ATR = (2.0, 3.0, 4.0)
MIN_GAP_ATR = (0.05, 0.10, 0.20)
REJECTION_MODES = (0, 1, 2)  # close through POC, close out of FVG, wick rejection at POC
EXPIRY_BARS = (24, 48)
STOP_MODES = (0, 1)  # FVG edge, rejection-candle extreme
STOP_BUFFERS_ATR = (0.0, 0.10, 0.25)
REWARD_RISKS = (1.5, 2.0, 2.5, 3.0)
MAX_HOLD_HOURS = (6, 24, 72)
MANAGEMENTS = (0, 1)  # fixed stop, break-even at +1R
PROFILE_BINS = 64
STARTING_BALANCE = 10_000.0
RISK_FRACTION = 0.01


@dataclass(frozen=True)
class StructureConfig:
    timeframe_minutes: int
    pivot_bars: int
    minimum_impulse_atr: float
    minimum_gap_atr: float
    rejection_mode: int
    expiry_bars: int


@dataclass(frozen=True)
class ExecutionConfig:
    stop_mode: int
    stop_buffer_atr: float
    reward_risk: float
    maximum_hold_hours: int
    management: int


@njit(cache=True)
def profile_poc(
    lows: np.ndarray,
    highs: np.ndarray,
    volumes: np.ndarray,
    start: int,
    finish: int,
    profile_low: float,
    profile_high: float,
    bins: int,
) -> float:
    if finish <= start or profile_high <= profile_low:
        return np.nan
    histogram = np.zeros(bins, dtype=np.float64)
    width = (profile_high - profile_low) / bins
    for i in range(start, finish):
        low_bin = int(math.floor((lows[i] - profile_low) / width))
        high_bin = int(math.floor((highs[i] - profile_low) / width))
        if low_bin < 0:
            low_bin = 0
        if high_bin >= bins:
            high_bin = bins - 1
        if high_bin < low_bin:
            middle = 0.5 * (lows[i] + highs[i])
            low_bin = int(math.floor((middle - profile_low) / width))
            low_bin = max(0, min(bins - 1, low_bin))
            high_bin = low_bin
        allocation = max(volumes[i], 1.0) / (high_bin - low_bin + 1)
        for level in range(low_bin, high_bin + 1):
            histogram[level] += allocation
    best = 0
    for level in range(1, bins):
        if histogram[level] > histogram[best]:
            best = level
    return profile_low + (best + 0.5) * width


@njit(cache=True)
def simulate_metrics(
    entries: np.ndarray,
    directions: np.ndarray,
    gap_lows: np.ndarray,
    gap_highs: np.ndarray,
    rejection_lows: np.ndarray,
    rejection_highs: np.ndarray,
    atrs: np.ndarray,
    signal_years: np.ndarray,
    m1_open: np.ndarray,
    m1_high: np.ndarray,
    m1_low: np.ndarray,
    m1_close: np.ndarray,
    m1_spread_price: np.ndarray,
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
    max_drawdown = 0.0
    gross_profit = 0.0
    gross_loss = 0.0
    net_r = 0.0
    wins = 0
    losses = 0
    trades = 0
    last_exit = -1
    slippage = 0.25 * median_spread
    minimum_stop = max(2.0 * median_spread, 1e-12)

    for s in range(len(entries)):
        if signal_years[s] < start_year or signal_years[s] > end_year:
            continue
        entry_index = entries[s]
        if entry_index <= last_exit or entry_index < 0 or entry_index >= len(m1_open):
            continue
        direction = directions[s]
        spread = m1_spread_price[entry_index]
        if spread <= 0.0:
            spread = median_spread
        entry = m1_open[entry_index] + (spread + slippage if direction > 0 else -slippage)
        buffer = stop_buffer_atr * atrs[s]
        if direction > 0:
            base = gap_lows[s] if stop_mode == 0 else rejection_lows[s]
            stop = base - buffer
            distance = entry - stop
        else:
            base = gap_highs[s] if stop_mode == 0 else rejection_highs[s]
            stop = base + buffer
            distance = stop - entry
        if distance < minimum_stop or not np.isfinite(distance):
            continue
        target = entry + direction * reward_risk * distance
        active_stop = stop
        moved_to_be = False
        exit_index = min(len(m1_open) - 1, entry_index + maximum_hold_minutes)
        result_r = 0.0

        for j in range(entry_index, exit_index + 1):
            minute_spread = m1_spread_price[j]
            if minute_spread <= 0.0:
                minute_spread = median_spread
            if direction > 0:
                stopped = m1_low[j] <= active_stop
                targeted = m1_high[j] >= target
                mark_price = m1_close[j]
            else:
                ask_high = m1_high[j] + minute_spread
                ask_low = m1_low[j] + minute_spread
                stopped = ask_high >= active_stop
                targeted = ask_low <= target
                mark_price = m1_close[j] + minute_spread

            if stopped:
                fill = active_stop - slippage if direction > 0 else active_stop + slippage
                result_r = direction * (fill - entry) / distance
                exit_index = j
                break
            if targeted:
                fill = target - slippage if direction > 0 else target + slippage
                result_r = direction * (fill - entry) / distance
                exit_index = j
                break

            mark_r = direction * (mark_price - entry) / distance
            marked_equity = balance * (1.0 + RISK_FRACTION * mark_r)
            if marked_equity > peak:
                peak = marked_equity
            if peak > 0.0:
                drawdown = (peak - marked_equity) / peak * 100.0
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

            if management == 1 and not moved_to_be:
                reached = (m1_high[j] >= entry + distance) if direction > 0 else (m1_low[j] + minute_spread <= entry - distance)
                if reached:
                    active_stop = entry
                    moved_to_be = True

            if j == exit_index:
                fill = m1_close[j] - slippage if direction > 0 else m1_close[j] + minute_spread + slippage
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
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        last_exit = exit_index

    profit_factor = gross_profit / abs(gross_loss) if gross_loss < 0.0 else (999.0 if gross_profit > 0.0 else 0.0)
    win_rate = 100.0 * wins / trades if trades else 0.0
    return_pct = 100.0 * (balance / STARTING_BALANCE - 1.0)
    mean_r = net_r / trades if trades else 0.0
    return trades, wins, losses, win_rate, profit_factor, net_r, mean_r, return_pct, max_drawdown, balance


def load_manifest(data_directory: Path, key: str) -> dict:
    manifest = json.loads((data_directory / "manifest.json").read_text(encoding="utf-8"))
    return manifest["instruments"][key]


def load_asset(label: str) -> tuple[pd.DataFrame, dict]:
    data_directory, manifest_key, pattern = SOURCE_MAP[label]
    spec = load_manifest(data_directory, manifest_key)
    files = []
    for path in sorted(data_directory.glob(pattern)):
        match = re.search(r"M1-(\d{4})\.csv\.gz$", path.name)
        if match and 2022 <= int(match.group(1)) <= 2026:
            files.append(path)
    if not files:
        raise FileNotFoundError(f"No M1 data found for {label} in {data_directory}")
    frames = []
    columns = ["time", "open", "high", "low", "close", "tick_volume", "spread"]
    for path in files:
        frames.append(pd.read_csv(path, compression="gzip", usecols=columns, parse_dates=["time"]))
    frame = pd.concat(frames, ignore_index=True)
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    frame = frame.loc[(frame.time >= "2022-01-01") & (frame.time < "2027-01-01")]
    frame = frame.sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)
    return frame, spec


def resample_bars(m1: pd.DataFrame, minutes: int) -> pd.DataFrame:
    indexed = m1.set_index("time")
    bars = indexed.resample(f"{minutes}min", label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        tick_volume=("tick_volume", "sum"),
    )
    bars = bars.dropna().reset_index()
    previous = bars.close.shift(1)
    true_range = pd.concat(
        [(bars.high - bars.low), (bars.high - previous).abs(), (bars.low - previous).abs()], axis=1
    ).max(axis=1)
    bars["atr"] = true_range.rolling(14, min_periods=14).mean()
    bars["atr"] = bars.atr.bfill()
    return bars


def pivot_flags(values: np.ndarray, pivot: int, use_maximum: bool) -> np.ndarray:
    series = pd.Series(values)
    rolled = series.rolling(2 * pivot + 1, center=True).max() if use_maximum else series.rolling(2 * pivot + 1, center=True).min()
    flags = np.isclose(values, rolled.to_numpy(), rtol=0.0, atol=1e-12)
    flags[:pivot] = False
    flags[-pivot:] = False
    return flags


def base_profile_candidates(
    bars: pd.DataFrame,
    m1: pd.DataFrame,
    timeframe: int,
    pivot: int,
    minimum_impulse_atr: float,
) -> list[dict]:
    high = bars.high.to_numpy(float)
    low = bars.low.to_numpy(float)
    close = bars.close.to_numpy(float)
    atr = bars.atr.to_numpy(float)
    times_ns = bars.time.astype("int64").to_numpy()
    m1_times_ns = m1.time.astype("int64").to_numpy()
    m1_low = m1.low.to_numpy(float)
    m1_high = m1.high.to_numpy(float)
    m1_volume = m1.tick_volume.to_numpy(float)
    bar_m1 = np.searchsorted(m1_times_ns, times_ns)
    high_pivot = pivot_flags(high, pivot, True)
    low_pivot = pivot_flags(low, pivot, False)
    bull_fvg = low[2:] > high[:-2]
    bear_fvg = high[2:] < low[:-2]
    output: list[dict] = []
    last_low = -1
    last_high = -1

    for endpoint in range(pivot, len(bars) - pivot - 1):
        if low_pivot[endpoint]:
            if last_high >= 0 and last_high < endpoint and np.isfinite(atr[endpoint]):
                leg_move = high[last_high] - low[endpoint]
                if leg_move >= minimum_impulse_atr * atr[endpoint]:
                    start_m1 = bar_m1[last_high]
                    finish_m1 = bar_m1[endpoint + 1]
                    poc = profile_poc(m1_low, m1_high, m1_volume, start_m1, finish_m1, low[endpoint], high[last_high], PROFILE_BINS)
                    confirmation = endpoint + pivot
                    possible = []
                    for formation in range(last_high + 2, endpoint + 1):
                        if not bear_fvg[formation - 2]:
                            continue
                        gap_low, gap_high = high[formation], low[formation - 2]
                        gap_ratio = (gap_high - gap_low) / max(atr[formation], 1e-12)
                        if gap_low <= poc <= gap_high and np.max(high[formation + 1 : confirmation + 1], initial=-np.inf) < gap_low:
                            possible.append((formation, gap_low, gap_high, gap_ratio))
                    if possible:
                        formation, gap_low, gap_high, gap_ratio = max(possible, key=lambda item: item[0])
                        output.append(
                            {"confirmation": confirmation, "direction": -1, "gap_low": gap_low, "gap_high": gap_high,
                             "poc": poc, "atr": atr[confirmation], "gap_ratio": gap_ratio, "formation": formation}
                        )
            last_low = endpoint

        if high_pivot[endpoint]:
            if last_low >= 0 and last_low < endpoint and np.isfinite(atr[endpoint]):
                leg_move = high[endpoint] - low[last_low]
                if leg_move >= minimum_impulse_atr * atr[endpoint]:
                    start_m1 = bar_m1[last_low]
                    finish_m1 = bar_m1[endpoint + 1]
                    poc = profile_poc(m1_low, m1_high, m1_volume, start_m1, finish_m1, low[last_low], high[endpoint], PROFILE_BINS)
                    confirmation = endpoint + pivot
                    possible = []
                    for formation in range(last_low + 2, endpoint + 1):
                        if not bull_fvg[formation - 2]:
                            continue
                        gap_low, gap_high = high[formation - 2], low[formation]
                        gap_ratio = (gap_high - gap_low) / max(atr[formation], 1e-12)
                        if gap_low <= poc <= gap_high and np.min(low[formation + 1 : confirmation + 1], initial=np.inf) > gap_high:
                            possible.append((formation, gap_low, gap_high, gap_ratio))
                    if possible:
                        formation, gap_low, gap_high, gap_ratio = max(possible, key=lambda item: item[0])
                        output.append(
                            {"confirmation": confirmation, "direction": 1, "gap_low": gap_low, "gap_high": gap_high,
                             "poc": poc, "atr": atr[confirmation], "gap_ratio": gap_ratio, "formation": formation}
                        )
            last_high = endpoint

    output.sort(key=lambda item: item["confirmation"])
    return output


def rejection_signals(
    candidates: list[dict],
    bars: pd.DataFrame,
    m1: pd.DataFrame,
    minimum_gap_atr: float,
    rejection_mode: int,
    expiry_bars: int,
) -> dict[str, np.ndarray]:
    open_ = bars.open.to_numpy(float)
    high = bars.high.to_numpy(float)
    low = bars.low.to_numpy(float)
    close = bars.close.to_numpy(float)
    atr = bars.atr.to_numpy(float)
    bar_times_ns = bars.time.astype("int64").to_numpy()
    m1_times_ns = m1.time.astype("int64").to_numpy()
    bar_m1 = np.searchsorted(m1_times_ns, bar_times_ns)
    events = []

    for candidate in candidates:
        if candidate["gap_ratio"] < minimum_gap_atr:
            continue
        direction = candidate["direction"]
        gap_low = candidate["gap_low"]
        gap_high = candidate["gap_high"]
        poc = candidate["poc"]
        start = candidate["confirmation"] + 1
        finish = min(len(bars) - 2, start + expiry_bars)
        for bar in range(start, finish + 1):
            if (direction > 0 and close[bar] < gap_low) or (direction < 0 and close[bar] > gap_high):
                break
            touched = low[bar] <= gap_high and high[bar] >= gap_low
            if not touched:
                continue
            body = abs(close[bar] - open_[bar])
            if direction > 0:
                directional = close[bar] > open_[bar]
                poc_close = close[bar] >= poc
                edge_close = close[bar] >= gap_high
                wick_rejection = (min(open_[bar], close[bar]) - low[bar]) >= max(body, 0.05 * atr[bar])
            else:
                directional = close[bar] < open_[bar]
                poc_close = close[bar] <= poc
                edge_close = close[bar] <= gap_low
                wick_rejection = (high[bar] - max(open_[bar], close[bar])) >= max(body, 0.05 * atr[bar])
            accepted = directional and (
                (rejection_mode == 0 and poc_close)
                or (rejection_mode == 1 and edge_close)
                or (rejection_mode == 2 and poc_close and wick_rejection)
            )
            if accepted:
                entry_index = int(bar_m1[bar + 1])
                if entry_index < len(m1):
                    events.append(
                        (entry_index, direction, gap_low, gap_high, low[bar], high[bar], atr[bar], bars.time.iloc[bar + 1].year)
                    )
                break

    events.sort(key=lambda item: (item[0], -abs(item[1])))
    deduplicated = []
    seen = set()
    for event in events:
        key = (event[0], event[1])
        if key not in seen:
            seen.add(key)
            deduplicated.append(event)
    if not deduplicated:
        return {name: np.array([], dtype=dtype) for name, dtype in {
            "entries": np.int64, "directions": np.int8, "gap_lows": np.float64, "gap_highs": np.float64,
            "rejection_lows": np.float64, "rejection_highs": np.float64, "atrs": np.float64, "years": np.int16,
        }.items()}
    array = np.asarray(deduplicated, dtype=float)
    return {
        "entries": array[:, 0].astype(np.int64),
        "directions": array[:, 1].astype(np.int8),
        "gap_lows": array[:, 2],
        "gap_highs": array[:, 3],
        "rejection_lows": array[:, 4],
        "rejection_highs": array[:, 5],
        "atrs": array[:, 6],
        "years": array[:, 7].astype(np.int16),
    }


def metric_dict(values: tuple) -> dict:
    keys = ["trades", "wins", "losses", "win_rate_pct", "profit_factor", "net_r", "mean_r", "return_pct", "max_drawdown_pct", "final_balance"]
    result = dict(zip(keys, values))
    for key in ("trades", "wins", "losses"):
        result[key] = int(result[key])
    return result


def run_metrics(signals: dict, arrays: dict, median_spread: float, years: tuple[int, int], execution: ExecutionConfig) -> dict:
    values = simulate_metrics(
        signals["entries"], signals["directions"], signals["gap_lows"], signals["gap_highs"],
        signals["rejection_lows"], signals["rejection_highs"], signals["atrs"], signals["years"],
        arrays["open"], arrays["high"], arrays["low"], arrays["close"], arrays["spread_price"], median_spread,
        years[0], years[1], execution.stop_mode, execution.stop_buffer_atr, execution.reward_risk,
        execution.maximum_hold_hours * 60, execution.management,
    )
    return metric_dict(values)


def robust_score(train: dict, validation: dict) -> float:
    if train["trades"] < 25 or validation["trades"] < 6:
        return -1e9
    conservative_mean = min(train["mean_r"], validation["mean_r"])
    conservative_pf = min(train["profit_factor"], validation["profit_factor"])
    worst_drawdown = max(train["max_drawdown_pct"], validation["max_drawdown_pct"])
    return 100.0 * conservative_mean + 2.0 * min(conservative_pf, 3.0) - 0.06 * worst_drawdown + 0.1 * math.log1p(validation["trades"])


def config_record(structure: StructureConfig, execution: ExecutionConfig, train: dict, validation: dict) -> dict:
    return {
        **asdict(structure),
        **asdict(execution),
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
    for s, entry_index in enumerate(signals["entries"]):
        if entry_index <= last_exit or entry_index >= len(m1):
            continue
        direction = int(signals["directions"][s])
        spread = arrays["spread_price"][entry_index] or median_spread
        entry = arrays["open"][entry_index] + (spread + slippage if direction > 0 else -slippage)
        buffer = execution.stop_buffer_atr * signals["atrs"][s]
        if direction > 0:
            base = signals["gap_lows"][s] if execution.stop_mode == 0 else signals["rejection_lows"][s]
            stop = base - buffer
            distance = entry - stop
        else:
            base = signals["gap_highs"][s] if execution.stop_mode == 0 else signals["rejection_highs"][s]
            stop = base + buffer
            distance = stop - entry
        if distance < minimum_stop:
            continue
        target = entry + direction * execution.reward_risk * distance
        active_stop = stop
        moved = False
        maximum = min(len(m1) - 1, entry_index + execution.maximum_hold_hours * 60)
        reason = "time"
        exit_index = maximum
        result_r = 0.0
        for j in range(entry_index, maximum + 1):
            minute_spread = arrays["spread_price"][j] or median_spread
            stopped = arrays["low"][j] <= active_stop if direction > 0 else arrays["high"][j] + minute_spread >= active_stop
            targeted = arrays["high"][j] >= target if direction > 0 else arrays["low"][j] + minute_spread <= target
            if stopped:
                fill = active_stop - slippage if direction > 0 else active_stop + slippage
                result_r = direction * (fill - entry) / distance
                exit_index, reason = j, "stop"
                break
            if targeted:
                fill = target - slippage if direction > 0 else target + slippage
                result_r = direction * (fill - entry) / distance
                exit_index, reason = j, "target"
                break
            if execution.management == 1 and not moved:
                reached = arrays["high"][j] >= entry + distance if direction > 0 else arrays["low"][j] + minute_spread <= entry - distance
                if reached:
                    active_stop, moved = entry, True
            if j == maximum:
                fill = arrays["close"][j] - slippage if direction > 0 else arrays["close"][j] + minute_spread + slippage
                result_r = direction * (fill - entry) / distance
        balance *= max(0.0, 1.0 + RISK_FRACTION * result_r)
        rows.append({
            "entry_time_utc": m1.time.iloc[entry_index], "exit_time_utc": m1.time.iloc[exit_index],
            "direction": "long" if direction > 0 else "short", "entry": entry, "initial_stop": stop,
            "target": target, "exit_reason": reason, "r_multiple": result_r, "balance": balance,
        })
        last_exit = exit_index
    return pd.DataFrame(rows)


def period_metrics_from_trades(trades: pd.DataFrame, start_year: int, end_year: int) -> dict:
    if trades.empty:
        return metric_dict((0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, STARTING_BALANCE))
    years = pd.to_datetime(trades.entry_time_utc, utc=True).dt.year
    subset = trades.loc[(years >= start_year) & (years <= end_year)].copy()
    if subset.empty:
        return metric_dict((0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, STARTING_BALANCE))
    r = subset.r_multiple.to_numpy(float)
    balances = STARTING_BALANCE * np.cumprod(1.0 + RISK_FRACTION * r)
    curve = np.r_[STARTING_BALANCE, balances]
    peak = np.maximum.accumulate(curve)
    drawdown = np.max((peak - curve) / peak * 100.0)
    profit = r[r > 0].sum()
    loss = r[r <= 0].sum()
    pf = profit / abs(loss) if loss < 0 else (999.0 if profit > 0 else 0.0)
    return {
        "trades": int(len(r)), "wins": int((r > 0).sum()), "losses": int((r <= 0).sum()),
        "win_rate_pct": float(100.0 * (r > 0).mean()), "profit_factor": float(pf), "net_r": float(r.sum()),
        "mean_r": float(r.mean()), "return_pct": float((balances[-1] / STARTING_BALANCE - 1.0) * 100.0),
        "max_drawdown_pct": float(drawdown), "final_balance": float(balances[-1]),
    }


def analyze_asset(label: str) -> dict:
    print(f"\n=== {label}: loading M1 history ===", flush=True)
    m1, spec = load_asset(label)
    median_spread = float(spec["median_spread_price"])
    arrays = {
        "open": m1.open.to_numpy(float), "high": m1.high.to_numpy(float), "low": m1.low.to_numpy(float),
        "close": m1.close.to_numpy(float), "spread_price": m1.spread.to_numpy(float) * float(spec["point"]),
    }
    bars_by_tf = {tf: resample_bars(m1, tf) for tf in TIMEFRAMES}
    signal_cache: dict[StructureConfig, dict] = {}
    stage_one = []
    default_execution = ExecutionConfig(0, 0.10, 2.0, 24, 0)

    for timeframe in TIMEFRAMES:
        bars = bars_by_tf[timeframe]
        for pivot in PIVOTS:
            for impulse in IMPULSE_ATR:
                base = base_profile_candidates(bars, m1, timeframe, pivot, impulse)
                for gap in MIN_GAP_ATR:
                    for rejection in REJECTION_MODES:
                        for expiry in EXPIRY_BARS:
                            structure = StructureConfig(timeframe, pivot, impulse, gap, rejection, expiry)
                            signals = rejection_signals(base, bars, m1, gap, rejection, expiry)
                            signal_cache[structure] = signals
                            train = run_metrics(signals, arrays, median_spread, (2022, 2024), default_execution)
                            if train["trades"] >= 15:
                                stage_score = train["mean_r"] * math.sqrt(train["trades"]) + 0.02 * train["profit_factor"] - 0.002 * train["max_drawdown_pct"]
                                stage_one.append((stage_score, structure, train))
    stage_one.sort(key=lambda item: item[0], reverse=True)
    finalists = [item[1] for item in stage_one[:16]]
    if not finalists:
        raise RuntimeError(f"{label}: no structure produced at least 15 development trades")

    screen_rows = []
    for structure in finalists:
        signals = signal_cache[structure]
        for stop_mode in STOP_MODES:
            for buffer in STOP_BUFFERS_ATR:
                for rr in REWARD_RISKS:
                    for hold in MAX_HOLD_HOURS:
                        for management in MANAGEMENTS:
                            execution = ExecutionConfig(stop_mode, buffer, rr, hold, management)
                            train = run_metrics(signals, arrays, median_spread, (2022, 2024), execution)
                            if train["trades"] < 25:
                                continue
                            validation = run_metrics(signals, arrays, median_spread, (2025, 2025), execution)
                            screen_rows.append(config_record(structure, execution, train, validation))
    if not screen_rows:
        fallback_structure = finalists[0]
        fallback_signals = signal_cache[fallback_structure]
        fallback_train = run_metrics(fallback_signals, arrays, median_spread, (2022, 2024), default_execution)
        fallback_validation = run_metrics(fallback_signals, arrays, median_spread, (2025, 2025), default_execution)
        screen_rows.append(config_record(fallback_structure, default_execution, fallback_train, fallback_validation))
    screen = pd.DataFrame(screen_rows).sort_values("robust_score", ascending=False)
    screen.to_csv(RESULTS / f"{label}-development-screen.csv", index=False)
    if screen.empty:
        raise RuntimeError(f"{label}: no execution configuration had enough development trades")

    gate = screen.loc[
        (screen.train_profit_factor >= 1.05) & (screen.train_return_pct > 0.0) & (screen.train_max_drawdown_pct < 20.0)
        & (screen.validation_profit_factor >= 1.0) & (screen.validation_return_pct > 0.0)
        & (screen.validation_max_drawdown_pct < 20.0) & (screen.validation_trades >= 6)
    ]
    selected_row = (gate.iloc[0] if len(gate) else screen.iloc[0]).to_dict()
    selected_structure = StructureConfig(
        int(selected_row["timeframe_minutes"]), int(selected_row["pivot_bars"]),
        float(selected_row["minimum_impulse_atr"]), float(selected_row["minimum_gap_atr"]),
        int(selected_row["rejection_mode"]), int(selected_row["expiry_bars"]),
    )
    selected_execution = ExecutionConfig(
        int(selected_row["stop_mode"]), float(selected_row["stop_buffer_atr"]),
        float(selected_row["reward_risk"]), int(selected_row["maximum_hold_hours"]), int(selected_row["management"]),
    )
    selected_signals = signal_cache[selected_structure]
    confirmation = run_metrics(selected_signals, arrays, median_spread, (2026, 2026), selected_execution)
    full_metrics = run_metrics(selected_signals, arrays, median_spread, (2022, 2026), selected_execution)
    trades = detailed_trades(selected_signals, arrays, m1, median_spread, selected_execution)
    trades.to_csv(RESULTS / f"{label}-selected-trades.csv", index=False)

    yearly = {str(year): period_metrics_from_trades(trades, year, year) for year in range(2022, 2027)}
    statistical_pass = (
        confirmation["trades"] >= 6 and confirmation["profit_factor"] >= 1.05
        and confirmation["return_pct"] > 0.0 and confirmation["max_drawdown_pct"] < 15.0
        and full_metrics["profit_factor"] >= 1.05
    )
    years_covered = max((m1.time.max() - m1.time.min()).total_seconds() / (365.25 * 86400.0), 1e-9)
    full_cagr_pct = ((full_metrics["final_balance"] / STARTING_BALANCE) ** (1.0 / years_covered) - 1.0) * 100.0
    portfolio_pass = statistical_pass and full_cagr_pct >= 15.0
    result = {
        "instrument": label,
        "broker_symbol": spec["symbol"],
        "data": {
            "server": "MEXAtlantic-Demo", "first_utc": m1.time.min().isoformat(), "last_utc": m1.time.max().isoformat(),
            "m1_rows": len(m1), "median_spread_price": median_spread, "real_volume_sum": int(spec.get("real_volume_sum", 0)),
            "volume_warning": "Fixed-range volume profile uses broker tick-volume because centralized real volume is unavailable.",
        },
        "selection_gate_passed_2022_2025": bool(len(gate)),
        "selected_structure": asdict(selected_structure),
        "selected_execution": asdict(selected_execution),
        "development_2022_2024": run_metrics(selected_signals, arrays, median_spread, (2022, 2024), selected_execution),
        "validation_2025": run_metrics(selected_signals, arrays, median_spread, (2025, 2025), selected_execution),
        "confirmation_2026": confirmation,
        "full_2022_2026": full_metrics,
        "full_cagr_pct": full_cagr_pct,
        "yearly": yearly,
        "research_status": "POSITIVE_CONFIRMATION" if statistical_pass else "FAILED_CONFIRMATION",
        "final_status": "PASS" if portfolio_pass else "REJECT",
    }
    (RESULTS / f"{label}-selected-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"instrument": label, "status": result["final_status"], "parameters": {**asdict(selected_structure), **asdict(selected_execution)}, "confirmation": confirmation, "full": full_metrics}, indent=2), flush=True)
    return {"result": result, "trades": trades}


def graph_results(outputs: dict[str, dict]) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(18, 10), constrained_layout=True)
    for axis, (label, output) in zip(axes.flat, outputs.items()):
        trades = output["trades"]
        result = output["result"]
        if trades.empty:
            axis.text(0.5, 0.5, "No trades", ha="center", va="center")
            axis.set_title(label)
            continue
        time = pd.to_datetime(trades.entry_time_utc, utc=True)
        balance = STARTING_BALANCE * np.cumprod(1.0 + RISK_FRACTION * trades.r_multiple.to_numpy(float))
        axis.step(time, balance, where="post", linewidth=1.25)
        axis.axhline(STARTING_BALANCE, color="gray", linestyle="--", linewidth=0.8)
        axis.axvline(pd.Timestamp("2026-01-01", tz="UTC"), color="red", linestyle="--", linewidth=1.0)
        confirm = result["confirmation_2026"]
        full = result["full_2022_2026"]
        axis.set_title(f"{label} — {result['final_status']} | Full {full['return_pct']:+.1f}% PF {full['profit_factor']:.2f} | 2026 {confirm['return_pct']:+.1f}%")
        axis.grid(alpha=0.25)
        axis.set_ylabel("Closed equity ($)")

        individual, individual_axis = plt.subplots(figsize=(12, 6), constrained_layout=True)
        individual_axis.step(time, balance, where="post")
        individual_axis.axhline(STARTING_BALANCE, color="gray", linestyle="--")
        individual_axis.axvline(pd.Timestamp("2026-01-01", tz="UTC"), color="red", linestyle="--", label="Locked 2026 confirmation")
        individual_axis.set_title(axis.get_title())
        individual_axis.set_xlabel("Date (UTC)")
        individual_axis.set_ylabel("Closed equity ($)")
        individual_axis.grid(alpha=0.25)
        individual_axis.legend()
        individual.savefig(RESULTS / f"{label}-equity.png", dpi=170)
        plt.close(individual)
    fig.suptitle("FVG + fixed-range tick-volume POC strategy — 1% risk per trade", fontsize=16)
    fig.savefig(RESULTS / "all-markets-equity.png", dpi=180)
    plt.close(fig)


def write_summary(outputs: dict[str, dict]) -> None:
    rows = []
    payload = {}
    for label, output in outputs.items():
        result = output["result"]
        payload[label] = result
        config = {**result["selected_structure"], **result["selected_execution"]}
        full = result["full_2022_2026"]
        confirmation = result["confirmation_2026"]
        rows.append({
            "status": result["final_status"], "research_status": result.get("research_status", ""),
            "instrument": label, "symbol": result["broker_symbol"],
            "timeframe": f"M{config['timeframe_minutes']}", "pivot": config["pivot_bars"],
            "impulse_atr": config["minimum_impulse_atr"], "min_gap_atr": config["minimum_gap_atr"],
            "rejection_mode": config["rejection_mode"], "expiry_bars": config["expiry_bars"],
            "stop_mode": config["stop_mode"], "stop_buffer_atr": config["stop_buffer_atr"],
            "rr": config["reward_risk"], "hold_hours": config["maximum_hold_hours"], "management": config["management"],
            "full_trades": full["trades"], "full_win_rate_pct": full["win_rate_pct"], "full_pf": full["profit_factor"],
            "full_return_pct": full["return_pct"], "full_max_dd_pct": full["max_drawdown_pct"],
            "full_cagr_pct": result.get("full_cagr_pct"),
            "confirm_trades": confirmation["trades"], "confirm_win_rate_pct": confirmation["win_rate_pct"],
            "confirm_pf": confirmation["profit_factor"], "confirm_return_pct": confirmation["return_pct"],
            "confirm_max_dd_pct": confirmation["max_drawdown_pct"],
        })
    pd.DataFrame(rows).to_csv(RESULTS / "summary.csv", index=False)
    (RESULTS / "all-results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", nargs="*", default=list(SOURCE_MAP))
    parser.add_argument("--combine-existing", action="store_true")
    args = parser.parse_args()
    unknown = [asset for asset in args.assets if asset not in SOURCE_MAP]
    if unknown:
        raise SystemExit(f"Unknown assets: {unknown}")
    RESULTS.mkdir(parents=True, exist_ok=True)
    if args.combine_existing:
        outputs = {}
        for asset in SOURCE_MAP:
            result_path = RESULTS / f"{asset}-selected-result.json"
            trades_path = RESULTS / f"{asset}-selected-trades.csv"
            if not result_path.exists() or not trades_path.exists():
                raise FileNotFoundError(f"Missing completed artifacts for {asset}")
            result = json.loads(result_path.read_text(encoding="utf-8"))
            first = pd.Timestamp(result["data"]["first_utc"])
            last = pd.Timestamp(result["data"]["last_utc"])
            years = max((last - first).total_seconds() / (365.25 * 86400.0), 1e-9)
            full = result["full_2022_2026"]
            cagr = ((full["final_balance"] / STARTING_BALANCE) ** (1.0 / years) - 1.0) * 100.0
            old_pass = result.get("final_status") == "PASS"
            result["full_cagr_pct"] = cagr
            result["research_status"] = "POSITIVE_CONFIRMATION" if old_pass else "FAILED_CONFIRMATION"
            result["final_status"] = "PASS" if old_pass and cagr >= 15.0 else "REJECT"
            result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            trades = pd.read_csv(trades_path, parse_dates=["entry_time_utc", "exit_time_utc"])
            outputs[asset] = {"result": result, "trades": trades}
        graph_results(outputs)
        write_summary(outputs)
        return 0
    outputs = {asset: analyze_asset(asset) for asset in args.assets}
    graph_results(outputs)
    write_summary(outputs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
