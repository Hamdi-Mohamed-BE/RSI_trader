"""Causal full-pipeline screen for volatility-compression breakouts."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path
import itertools
import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from numba import njit

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "Data"
CHARTS = ROOT / "Charts"
SYMBOLS = ("XAUUSD", "XAGUSD", "BTCUSD", "US30", "USTEC", "GBPJPY")
TIMEFRAMES = {"M5": ("5min", 5), "M15": ("15min", 15), "M30": ("30min", 30), "H1": ("1h", 60), "H4": ("4h", 240)}
SESSIONS = ("all-day", "asia", "london", "new-york", "overlap", "london-new-york")
COMPRESSION_VARIANTS = tuple(
    [("atr-ratio", value) for value in (0.50, 0.65, 0.80)]
    + [("bb-percentile", value) for value in (0.10, 0.20, 0.30)]
    + [("narrow-range", value) for value in (5.0, 7.0, 10.0)]
    + [("bb-keltner", value) for value in (1.0, 1.5, 2.0)]
)
CONFIRMATIONS = ("close", "body", "volume", "body-volume")
TRENDS = ("none", "ema50", "ema200", "ema50-200")
DIRECTIONS = ("both", "long-only", "short-only")
STOP_VARIANTS = tuple([("range", 0.10), ("range", 0.20)] + [("atr", value) for value in (0.75, 1.0, 1.25, 1.5, 2.0)] + [("signal", 0.10), ("swing5", 0.10)])
RR_VALUES = (0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0)
MANAGEMENTS = ("none", "breakeven", "atr-trail", "dynamic-m15-50-20")
HOLD_BARS = (6, 12, 24, 48)
TRAIN = (pd.Timestamp("2023-09-01", tz="UTC"), pd.Timestamp("2024-09-01", tz="UTC"))
VALIDATION = (pd.Timestamp("2024-09-01", tz="UTC"), pd.Timestamp("2025-09-01", tz="UTC"))
LOCKED = (pd.Timestamp("2025-09-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC"))
FULL = (pd.Timestamp("2023-09-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC"))


@dataclass(frozen=True)
class Config:
    timeframe: str = "M30"
    session: str = "all-day"
    compression: str = "atr-ratio"
    compression_value: float = 0.65
    range_bars: int = 12
    arm_bars: int = 6
    breakout_buffer_atr: float = 0.10
    confirmation: str = "close"
    trend: str = "ema50"
    direction: str = "both"
    maximum_hold_bars: int = 12
    stop_mode: str = "atr"
    stop_value: float = 1.25
    rr: float = 2.0
    management: str = "none"


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def load(symbol: str) -> tuple[pd.DataFrame, dict]:
    rates = np.load(DATA / f"{symbol}-M5.npz")["rates"]
    index = pd.to_datetime(rates["time"], unit="s", utc=True)
    frame = pd.DataFrame(
        {name: rates[name].astype(float) for name in ("open", "high", "low", "close", "tick_volume", "spread")},
        index=index,
    )
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    meta = json.loads((DATA / "metadata.json").read_text(encoding="utf-8"))["symbols"][symbol]
    positive = frame.loc[frame.spread > 0, "spread"]
    spread_floor = float(positive.quantile(0.35)) if len(positive) else 1.0
    frame["spread_price"] = np.maximum(frame.spread, spread_floor) * float(meta["point"])
    return frame, meta | {"spread_floor_points": spread_floor}


def true_range(frame: pd.DataFrame) -> pd.Series:
    previous = frame.close.shift(1)
    return pd.concat(((frame.high - frame.low), (frame.high - previous).abs(), (frame.low - previous).abs()), axis=1).max(axis=1)


def session_code(index: pd.DatetimeIndex) -> np.ndarray:
    utc_minute = index.hour * 60 + index.minute
    london = index.tz_convert("Europe/London")
    ny = index.tz_convert("America/New_York")
    london_minute = london.hour * 60 + london.minute
    ny_minute = ny.hour * 60 + ny.minute
    asia = (utc_minute >= 0) & (utc_minute < 480)
    london_open = (london_minute >= 480) & (london_minute < 990)
    ny_open = (ny_minute >= 570) & (ny_minute < 960)
    overlap = london_open & ny_open
    code = np.zeros(len(index), dtype=np.int16)
    code[asia] |= 1
    code[london_open] |= 2
    code[ny_open] |= 4
    code[overlap] |= 8
    return code


def resample(base: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    rule, _minutes = TIMEFRAMES[timeframe]
    if timeframe == "M5":
        bars = base.copy()
    else:
        bars = base.resample(rule, label="left", closed="left").agg(
            open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"),
            tick_volume=("tick_volume", "sum"), spread_price=("spread_price", "last"),
        ).dropna()
    tr = true_range(bars)
    bars["tr"] = tr
    bars["atr5"] = tr.ewm(alpha=1 / 5, adjust=False, min_periods=5).mean()
    bars["atr14"] = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    bars["atr20"] = tr.ewm(alpha=1 / 20, adjust=False, min_periods=20).mean()
    bars["atr50"] = tr.ewm(alpha=1 / 50, adjust=False, min_periods=50).mean()
    bars["ema50"] = bars.close.ewm(span=50, adjust=False, min_periods=50).mean()
    bars["ema200"] = bars.close.ewm(span=200, adjust=False, min_periods=200).mean()
    bars["volume_mean20"] = bars.tick_volume.shift(1).rolling(20, min_periods=20).mean()
    mean20 = bars.close.rolling(20, min_periods=20).mean()
    std20 = bars.close.rolling(20, min_periods=20).std(ddof=0)
    bars["bb_width"] = 4.0 * std20 / mean20.replace(0, np.nan)
    bars["bb_rank"] = bars.bb_width.rolling(100, min_periods=80).rank(pct=True)
    bars["bb_std"] = std20
    bars["session_code"] = session_code(bars.index)
    bars["day_key"] = (bars.index.year * 10000 + bars.index.month * 100 + bars.index.day).astype(np.int32)
    return bars.dropna(subset=["atr5", "atr14", "atr20", "atr50", "ema50", "ema200", "volume_mean20", "bb_rank"])


def arrays(bars: pd.DataFrame, range_bars: int) -> dict[str, np.ndarray]:
    rolling_high = bars.high.rolling(range_bars, min_periods=range_bars).max()
    rolling_low = bars.low.rolling(range_bars, min_periods=range_bars).min()
    narrow5 = bars.tr.rolling(5, min_periods=5).min()
    narrow7 = bars.tr.rolling(7, min_periods=7).min()
    narrow10 = bars.tr.rolling(10, min_periods=10).min()
    return {
        "time": bars.index.as_unit("s").asi8.astype(np.int64),
        "open": bars.open.to_numpy(float), "high": bars.high.to_numpy(float), "low": bars.low.to_numpy(float), "close": bars.close.to_numpy(float),
        "tr": bars.tr.to_numpy(float),
        "volume": bars.tick_volume.to_numpy(float), "spread": bars.spread_price.to_numpy(float), "atr5": bars.atr5.to_numpy(float),
        "atr14": bars.atr14.to_numpy(float), "atr20": bars.atr20.to_numpy(float), "atr50": bars.atr50.to_numpy(float),
        "ema50": bars.ema50.to_numpy(float), "ema200": bars.ema200.to_numpy(float), "volume_mean20": bars.volume_mean20.to_numpy(float),
        "bb_rank": bars.bb_rank.to_numpy(float), "bb_std": bars.bb_std.to_numpy(float), "range_high": rolling_high.to_numpy(float),
        "range_low": rolling_low.to_numpy(float), "narrow5": narrow5.to_numpy(float), "narrow7": narrow7.to_numpy(float),
        "narrow10": narrow10.to_numpy(float), "session_code": bars.session_code.to_numpy(np.int16), "day_key": bars.day_key.to_numpy(np.int32),
    }


@njit(inline="always")
def session_allows(code, session):
    if session == 0:
        return True
    if session == 1:
        return (code & 1) != 0
    if session == 2:
        return (code & 2) != 0
    if session == 3:
        return (code & 4) != 0
    if session == 4:
        return (code & 8) != 0
    return (code & 2) != 0 or (code & 4) != 0


@njit(inline="always")
def compression_at(index, mode, value, tr, atr5, atr20, atr50, bb_rank, bb_std, narrow5, narrow7, narrow10):
    if mode == 0:
        return atr50[index] > 0 and atr5[index] / atr50[index] <= value
    if mode == 1:
        return bb_rank[index] <= value
    if mode == 2:
        length = int(round(value))
        floor = narrow5[index] if length == 5 else narrow7[index] if length == 7 else narrow10[index]
        return tr[index] <= floor + 1e-12
    return 2.0 * bb_std[index] <= value * atr20[index]


@njit
def simulate(time, op, hi, lo, cl, tr, volume, spread, atr5, atr14, atr20, atr50, ema50, ema200, volume_mean20,
             bb_rank, bb_std, range_high, range_low, narrow5, narrow7, narrow10, session_codes, day_keys,
             start_ts, end_ts, session, compression, compression_value, arm_bars, breakout_buffer, confirmation,
             trend, direction, maximum_hold_bars, stop_mode, stop_value, rr, management, friction_r):
    n = len(time)
    capacity = n // 3 + 20
    entries = np.empty(capacity, np.int64); exits = np.empty(capacity, np.int64)
    results = np.empty(capacity, np.float64); sides = np.empty(capacity, np.int8)
    count = 0; position = 0; entry = 0.0; stop = 0.0; target = 0.0; initial = 0.0; entry_i = 0
    realized = 1.0; peak = 1.0; maximum_dd = 0.0; last_day = -1; day_trades = 0
    for i in range(220, n):
        if time[i] < start_ts:
            continue
        if time[i] >= end_ts:
            break
        if day_keys[i] != last_day:
            last_day = day_keys[i]; day_trades = 0
        if position != 0:
            hit = False; exit_price = 0.0
            if position > 0:
                if op[i] <= stop: exit_price = op[i]; hit = True
                elif lo[i] <= stop: exit_price = stop; hit = True
                elif hi[i] >= target: exit_price = target; hit = True
            else:
                ask_open = op[i] + spread[i]; ask_high = hi[i] + spread[i]; ask_low = lo[i] + spread[i]
                if ask_open >= stop: exit_price = ask_open; hit = True
                elif ask_high >= stop: exit_price = stop; hit = True
                elif ask_low <= target: exit_price = target; hit = True
            if not hit and i - entry_i >= maximum_hold_bars:
                exit_price = cl[i] if position > 0 else cl[i] + spread[i]; hit = True
            if hit:
                result = position * (exit_price - entry) / initial - friction_r
                entries[count] = time[entry_i]; exits[count] = time[i]; results[count] = result; sides[count] = position; count += 1
                realized *= max(0.01, 1.0 + 0.01 * result); peak = max(peak, realized)
                maximum_dd = max(maximum_dd, 1.0 - realized / peak); position = 0
            else:
                favorable = ((hi[i] - entry) / initial if position > 0 else (entry - (lo[i] + spread[i])) / initial) - friction_r
                adverse = ((lo[i] - entry) / initial if position > 0 else (entry - (hi[i] + spread[i])) / initial) - friction_r
                peak = max(peak, realized * (1.0 + 0.01 * favorable))
                maximum_dd = max(maximum_dd, 1.0 - realized * (1.0 + 0.01 * adverse) / peak)
                progress = (cl[i] - entry) / initial if position > 0 else (entry - (cl[i] + spread[i])) / initial
                if management == 1 and progress >= 1.0:
                    stop = max(stop, entry) if position > 0 else min(stop, entry)
                elif management == 2 and progress >= 1.0:
                    candidate = cl[i] - 1.5 * atr14[i] if position > 0 else cl[i] + spread[i] + 1.5 * atr14[i]
                    stop = max(stop, candidate) if position > 0 else min(stop, candidate)
                elif management == 3 and time[i] % 900 == 0 and progress >= 0.5 * rr:
                    candidate = entry + position * 0.2 * rr * initial
                    stop = max(stop, candidate) if position > 0 else min(stop, candidate)
        if position != 0 or day_trades >= 2:
            continue
        p = i - 1
        if not session_allows(session_codes[p], session):
            continue
        compressed = -1
        for shift in range(2, arm_bars + 2):
            candidate = i - shift
            if candidate < 210:
                break
            if compression_at(candidate, compression, compression_value, tr, atr5, atr20, atr50, bb_rank, bb_std, narrow5, narrow7, narrow10):
                compressed = candidate
                break
        if compressed < 0 or not np.isfinite(range_high[compressed]) or not np.isfinite(range_low[compressed]):
            continue
        upper = range_high[compressed] + breakout_buffer * atr14[p]
        lower = range_low[compressed] - breakout_buffer * atr14[p]
        side = 0
        if cl[p] > upper and cl[p - 1] <= upper:
            side = 1
        elif cl[p] < lower and cl[p - 1] >= lower:
            side = -1
        if side == 0 or (direction == 1 and side < 0) or (direction == 2 and side > 0):
            continue
        body = side * (cl[p] - op[p])
        volume_ok = volume[p] >= 1.2 * volume_mean20[p]
        if confirmation == 1 and body < 0.30 * atr14[p]:
            continue
        if confirmation == 2 and not volume_ok:
            continue
        if confirmation == 3 and (body < 0.30 * atr14[p] or not volume_ok):
            continue
        if trend == 1 and side * (cl[p] - ema50[p]) <= 0:
            continue
        if trend == 2 and side * (cl[p] - ema200[p]) <= 0:
            continue
        if trend == 3 and (side * (cl[p] - ema50[p]) <= 0 or side * (ema50[p] - ema200[p]) <= 0):
            continue
        entry_price = op[i] + spread[i] if side > 0 else op[i]
        if stop_mode == 0:
            raw_stop = range_low[compressed] - stop_value * atr14[p] if side > 0 else range_high[compressed] + spread[i] + stop_value * atr14[p]
        elif stop_mode == 1:
            raw_stop = entry_price - side * stop_value * atr14[p]
        elif stop_mode == 2:
            raw_stop = lo[p] - stop_value * atr14[p] if side > 0 else hi[p] + spread[i] + stop_value * atr14[p]
        else:
            start = max(0, p - 4)
            raw_stop = np.min(lo[start:p + 1]) - stop_value * atr14[p] if side > 0 else np.max(hi[start:p + 1]) + spread[i] + stop_value * atr14[p]
        distance = entry_price - raw_stop if side > 0 else raw_stop - entry_price
        if not np.isfinite(distance) or distance <= max(2.0 * spread[i], 0.10 * atr14[p]) or distance > 6.0 * atr14[p]:
            continue
        position = side; entry = entry_price; initial = distance; stop = raw_stop
        target = entry_price + side * rr * distance; entry_i = i; day_trades += 1
    if position != 0:
        i = n - 1; exit_price = cl[i] if position > 0 else cl[i] + spread[i]
        result = position * (exit_price - entry) / initial - friction_r
        entries[count] = time[entry_i]; exits[count] = time[i]; results[count] = result; sides[count] = position; count += 1
    return entries[:count], exits[:count], results[:count], sides[:count], 100.0 * maximum_dd


SESSION_CODE = {name: index for index, name in enumerate(SESSIONS)}
COMPRESSION_CODE = {name: index for index, name in enumerate(("atr-ratio", "bb-percentile", "narrow-range", "bb-keltner"))}
CONFIRM_CODE = {name: index for index, name in enumerate(CONFIRMATIONS)}
TREND_CODE = {name: index for index, name in enumerate(TRENDS)}
DIRECTION_CODE = {name: index for index, name in enumerate(DIRECTIONS)}
STOP_CODE = {name: index for index, name in enumerate(("range", "atr", "signal", "swing5"))}
MANAGEMENT_CODE = {name: index for index, name in enumerate(MANAGEMENTS)}


def metrics(entries, exits, results, sides, equity_dd=0.0) -> dict:
    if not len(results):
        return dict(return_pct=0.0, profit_factor=0.0, win_rate=0.0, max_dd_pct=0.0, trades=0, sharpe=0.0, recovery=0.0, expectancy_r=0.0, average_rr=0.0, longs=0, shorts=0)
    fractions = 0.01 * results
    equity = np.r_[1.0, np.cumprod(1.0 + fractions)]
    pnl = np.diff(equity); gains = pnl[pnl > 0].sum(); losses = -pnl[pnl < 0].sum()
    pf = gains / losses if losses > 0 else 99.0
    dd = max(float(equity_dd), float(np.max(1.0 - equity / np.maximum.accumulate(equity)) * 100.0))
    # Keep the configuration screen fast: aggregate observed exit-day returns
    # directly with NumPy instead of constructing a pandas calendar per run.
    # Zero-trade calendar days do not change candidate ordering and native MT5
    # supplies the final reported Sharpe for every frozen configuration.
    day = exits // 86400
    _, starts = np.unique(day, return_index=True)
    daily = np.add.reduceat(fractions, starts)
    daily_std = float(np.std(daily, ddof=1)) if len(daily) > 1 else 0.0
    sharpe = float(np.mean(daily) / daily_std * math.sqrt(252)) if daily_std > 0 else 0.0
    ret = float((equity[-1] - 1.0) * 100.0)
    return dict(
        return_pct=ret, profit_factor=float(min(pf, 99.0)), win_rate=float(100.0 * np.mean(results > 0)), max_dd_pct=dd,
        trades=int(len(results)), sharpe=sharpe, recovery=float(ret / dd if dd else 0.0), expectancy_r=float(results.mean()),
        average_rr=float(results[results > 0].mean() if np.any(results > 0) else 0.0), longs=int(np.sum(sides > 0)), shorts=int(np.sum(sides < 0)),
    )


def run(cache, config: Config, period, collect=False) -> dict:
    a = cache[(config.timeframe, config.range_bars)]
    output = simulate(
        *(a[name] for name in ("time", "open", "high", "low", "close", "tr", "volume", "spread", "atr5", "atr14", "atr20", "atr50", "ema50", "ema200", "volume_mean20", "bb_rank", "bb_std", "range_high", "range_low", "narrow5", "narrow7", "narrow10", "session_code", "day_key")),
        int(period[0].timestamp()), int(period[1].timestamp()), SESSION_CODE[config.session], COMPRESSION_CODE[config.compression],
        config.compression_value, config.arm_bars, config.breakout_buffer_atr, CONFIRM_CODE[config.confirmation], TREND_CODE[config.trend],
        DIRECTION_CODE[config.direction], config.maximum_hold_bars, STOP_CODE[config.stop_mode], config.stop_value, config.rr,
        MANAGEMENT_CODE[config.management], 0.02,
    )
    entries, exits, results, sides, dd = output
    result = metrics(entries, exits, results, sides, dd)
    if collect:
        result["trades_data"] = [
            dict(entry=pd.Timestamp(int(a), unit="s", tz="UTC").isoformat(), exit=pd.Timestamp(int(b), unit="s", tz="UTC").isoformat(), r=float(value), side="long" if side > 0 else "short")
            for a, b, value, side in zip(entries, exits, results, sides)
        ]
    return result


def score(train: dict, validation: dict) -> float:
    if train["trades"] < 18 or validation["trades"] < 18:
        return -10000.0 + train["trades"] + validation["trades"]
    minimum_return = min(train["return_pct"], validation["return_pct"])
    minimum_pf = min(train["profit_factor"], validation["profit_factor"])
    value = 0.40 * minimum_return + 12.0 * math.log(max(0.05, min(3.0, minimum_pf)))
    value += min(2.5, min(train["sharpe"], validation["sharpe"])) + min(train["recovery"], validation["recovery"])
    value -= 0.20 * max(train["max_dd_pct"], validation["max_dd_pct"])
    if minimum_return <= 0:
        value -= 30.0 + abs(minimum_return)
    if minimum_pf < 1.0:
        value -= 25.0 * (1.0 - minimum_pf)
    return float(value)


def evaluate(cache, config: Config):
    train = run(cache, config, TRAIN); validation = run(cache, config, VALIDATION)
    return train, validation, score(train, validation)


def row(symbol, phase, config, train, validation, rank):
    return dict(symbol=symbol, phase=phase, config=json.dumps(asdict(config), sort_keys=True), score=rank,
                **{f"train_{key}": value for key, value in train.items()}, **{f"validation_{key}": value for key, value in validation.items()})


def research_symbol(symbol: str, base: pd.DataFrame):
    bars = {timeframe: resample(base, timeframe) for timeframe in TIMEFRAMES}
    cache = {(timeframe, range_bars): arrays(frame, range_bars) for timeframe, frame in bars.items() for range_bars in (6, 12, 20)}
    rows = []; current = Config()

    def choose(phase: str, variants: list[Config], incumbent: Config) -> Config:
        ranked = []
        for candidate in variants:
            train, validation, value = evaluate(cache, candidate); rows.append(row(symbol, phase, candidate, train, validation, value)); ranked.append((value, candidate))
        incumbent_value = evaluate(cache, incumbent)[2]
        return max(ranked + [(incumbent_value, incumbent)], key=lambda item: item[0])[1]

    current = choose("timeframe-session", [replace(current, timeframe=tf, session=session) for tf, session in itertools.product(TIMEFRAMES, SESSIONS)], current)
    current = choose("compression", [replace(current, compression=mode, compression_value=value) for mode, value in COMPRESSION_VARIANTS], current)
    current = choose("range-arm-buffer", [replace(current, range_bars=rng, arm_bars=arm, breakout_buffer_atr=buffer) for rng, arm, buffer in itertools.product((6, 12, 20), (3, 6, 12), (0.0, 0.10, 0.20))], current)
    current = choose("confirmation-trend-direction", [replace(current, confirmation=confirm, trend=trend, direction=direction) for confirm, trend, direction in itertools.product(CONFIRMATIONS, TRENDS, DIRECTIONS)], current)
    current = choose("maximum-hold", [replace(current, maximum_hold_bars=value) for value in HOLD_BARS], current)
    current = choose("stop", [replace(current, stop_mode=mode, stop_value=value) for mode, value in STOP_VARIANTS], current)
    current = choose("reward-risk", [replace(current, rr=value) for value in RR_VALUES], current)
    current = choose("management", [replace(current, management=value) for value in MANAGEMENTS], current)
    current = choose("interaction-recheck", [replace(current, timeframe=tf, session=session) for tf, session in itertools.product(TIMEFRAMES, SESSIONS)], current)
    train, validation, value = evaluate(cache, current)
    return dict(config=asdict(current), train=train, validation=validation, score=value), rows, cache


def monte_carlo(trades, paths=10000, seed=260906):
    values = np.asarray([trade["r"] for trade in trades], dtype=float)
    if not len(values):
        return dict(paths=paths, profitable_probability=0.0, return_p5=0.0, return_median=0.0, return_p95=0.0, dd_median=0.0, dd_p95=0.0)
    rng = np.random.default_rng(seed); returns = np.empty(paths); drawdowns = np.empty(paths); block = min(5, len(values))
    for index in range(paths):
        starts = rng.integers(0, max(1, len(values) - block + 1), size=math.ceil(len(values) / block))
        sample = np.concatenate([values[start:start + block] for start in starts])[:len(values)]
        curve = np.r_[1.0, np.cumprod(1.0 + 0.01 * sample)]
        returns[index] = (curve[-1] - 1.0) * 100
        drawdowns[index] = np.max(1.0 - curve / np.maximum.accumulate(curve)) * 100
    return dict(paths=paths, profitable_probability=float(np.mean(returns > 0) * 100), return_p5=float(np.percentile(returns, 5)), return_median=float(np.median(returns)), return_p95=float(np.percentile(returns, 95)), dd_median=float(np.median(drawdowns)), dd_p95=float(np.percentile(drawdowns, 95)))


def make_charts(final, rows) -> None:
    CHARTS.mkdir(exist_ok=True); symbols = list(final); locked = [final[symbol]["locked"] for symbol in symbols]
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    axes[0, 0].bar(symbols, [item["return_pct"] for item in locked], color=["#39e6a0" if item["return_pct"] > 0 else "#ff5d73" for item in locked]); axes[0, 0].set_title("Locked-year return (%)")
    axes[0, 1].bar(symbols, [item["profit_factor"] for item in locked], color="#60a5fa"); axes[0, 1].axhline(1.2, color="#fbbf24", ls="--"); axes[0, 1].set_title("Profit factor")
    axes[1, 0].bar(symbols, [item["win_rate"] for item in locked], color="#a78bfa"); axes[1, 0].set_title("Win rate (%)")
    axes[1, 1].bar(symbols, [item["max_dd_pct"] for item in locked], color="#fb7185"); axes[1, 1].set_title("Maximum drawdown (%)")
    for axis in axes.flat: axis.grid(alpha=.2, axis="y")
    fig.suptitle("Volatility Compression → Expansion — untouched proxy year"); fig.tight_layout(); fig.savefig(CHARTS / "locked-summary.png", dpi=170); plt.close(fig)
    fig, axis = plt.subplots(figsize=(13, 6))
    for symbol in symbols:
        trades = final[symbol]["locked"]["trades_data"]
        dates = [pd.Timestamp(item["exit"]) for item in trades]; values = np.asarray([item["r"] for item in trades]); equity = 10000 * np.cumprod(1 + .01 * values)
        if len(dates): axis.plot(dates, equity, label=symbol)
    axis.axhline(10000, color="#777", ls="--"); axis.set_title("Locked-year closed equity — fixed 1% risk"); axis.set_ylabel("USD"); axis.grid(alpha=.2); axis.legend(ncol=3); fig.tight_layout(); fig.savefig(CHARTS / "locked-equity-curves.png", dpi=170); plt.close(fig)
    frame = pd.DataFrame(rows); rr = frame.loc[frame.phase == "reward-risk"].copy(); rr["rr"] = rr.config.map(lambda value: json.loads(value)["rr"])
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    for axis, symbol in zip(axes.flat, symbols):
        group = rr.loc[rr.symbol == symbol].sort_values("rr"); axis.plot(group.rr, group.validation_return_pct, marker="o", color="#39e6a0"); axis.axhline(0, color="#777", ls="--"); axis.set_title(symbol); axis.set_xlabel("R target"); axis.set_ylabel("Validation return (%)"); axis.grid(alpha=.2)
    fig.suptitle("Reward/risk sensitivity before locked year"); fig.tight_layout(); fig.savefig(CHARTS / "rr-sensitivity.png", dpi=170); plt.close(fig)


def main() -> None:
    selections = {}; all_rows = []; caches = {}
    for symbol in SYMBOLS:
        base, _meta = load(symbol); selection, rows, cache = research_symbol(symbol, base)
        selections[symbol] = selection; all_rows.extend(rows); caches[symbol] = cache
        print("SELECT", symbol, selection, flush=True)
    dump(ROOT / "selection-lock.json", selections)
    final = {}; rolling = []; monte = []
    for symbol in SYMBOLS:
        config = Config(**selections[symbol]["config"]); cache = caches[symbol]
        locked = run(cache, config, LOCKED, collect=True); full = run(cache, config, FULL, collect=True)
        final[symbol] = dict(config=asdict(config), train=selections[symbol]["train"], validation=selections[symbol]["validation"], locked=locked, full=full)
        monte.append(dict(symbol=symbol, **monte_carlo(locked["trades_data"])))
        cursor = FULL[0]
        while cursor + pd.DateOffset(months=6) <= FULL[1]:
            finish = cursor + pd.DateOffset(months=6); result = run(cache, config, (cursor, finish))
            rolling.append(dict(symbol=symbol, start=cursor.date().isoformat(), end=finish.date().isoformat(), **result)); cursor += pd.DateOffset(months=3)
    dump(ROOT / "screen-final.json", final); pd.DataFrame(all_rows).to_csv(ROOT / "all-screen-results.csv", index=False)
    frame = pd.DataFrame(all_rows)
    for phase, filename in (("reward-risk", "rr-sensitivity.csv"), ("stop", "stop-sensitivity.csv"), ("management", "management-sensitivity.csv"), ("timeframe-session", "session-timeframe-sensitivity.csv"), ("compression", "compression-sensitivity.csv")):
        frame.loc[frame.phase == phase].to_csv(ROOT / filename, index=False)
    pd.DataFrame(rolling).to_csv(ROOT / "rolling-stability.csv", index=False)
    pd.DataFrame(monte).to_csv(ROOT / "proxy-monte-carlo-summary.csv", index=False)
    make_charts(final, all_rows)
    dump(ROOT / "progress.json", dict(step=6, title="Volatility Compression to Expansion", status="screen-complete", locked_first_read_after_freeze=True, configurations=len(all_rows), risk_percent=1.0, symbols=list(SYMBOLS), production_changed=False))


if __name__ == "__main__":
    main()
