"""Causal full-pipeline screen for month-end institutional-flow effects."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path
import calendar
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
SOURCE_DATA = ROOT.parent / "Session VWAP Snapback Research 2026-09-06" / "Data"
CHARTS = ROOT / "Charts"
SYMBOLS = ("USTEC", "US30")
TIMEFRAMES = {"M5": ("5min", 5), "M15": ("15min", 15), "M30": ("30min", 30), "H1": ("1h", 60)}
WINDOWS = ("classic", "last1", "last2", "last3", "first1", "first3", "last2-first2", "last3-first3")
ENTRY_TIMES = ("london-open", "ny-open", "ny-first-hour", "ny-power-hour")
CONFIRMATIONS = ("none", "candle", "breakout")
TRENDS = ("none", "ema20", "ema50", "momentum20", "ema20-momentum20", "prior-day-reversal", "prior-day-strength")
DIRECTIONS = ("long-only", "short-only", "daily-trend")
STOP_VARIANTS = tuple(("atr", value) for value in (0.75, 1.0, 1.25, 1.5, 2.0)) + (("prior-day", 0.10), ("signal-candle", 0.10))
RR_VALUES = (0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0)
MANAGEMENTS = ("none", "breakeven", "atr-trail", "dynamic-m15-50-20")
HOLD_HOURS = (6, 12, 24, 72, 120)
TRAIN = (pd.Timestamp("2023-09-01", tz="UTC"), pd.Timestamp("2024-09-01", tz="UTC"))
VALIDATION = (pd.Timestamp("2024-09-01", tz="UTC"), pd.Timestamp("2025-09-01", tz="UTC"))
LOCKED = (pd.Timestamp("2025-09-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC"))
FULL = (pd.Timestamp("2023-09-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC"))


@dataclass(frozen=True)
class Config:
    timeframe: str = "M30"
    window: str = "classic"
    entry_time: str = "ny-open"
    confirmation: str = "none"
    trend: str = "none"
    direction: str = "long-only"
    max_hold_hours: int = 24
    stop_mode: str = "atr"
    stop_value: float = 1.25
    rr: float = 1.5
    management: str = "none"


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def load(symbol: str) -> tuple[pd.DataFrame, dict]:
    rates = np.load(SOURCE_DATA / f"{symbol}-M5.npz")["rates"]
    index = pd.to_datetime(rates["time"], unit="s", utc=True)
    frame = pd.DataFrame({name: rates[name].astype(float) for name in ("open", "high", "low", "close", "tick_volume", "spread")}, index=index)
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    meta = json.loads((SOURCE_DATA / "metadata.json").read_text(encoding="utf-8"))["symbols"][symbol]
    positive = frame.loc[frame.spread > 0, "spread"]
    spread_floor = float(positive.quantile(0.35)) if len(positive) else 1.0
    frame["spread_price"] = np.maximum(frame.spread, spread_floor) * float(meta["point"])
    return frame, meta | {"spread_floor_points": spread_floor}


def true_range(frame: pd.DataFrame) -> pd.Series:
    previous = frame.close.shift(1)
    return pd.concat(((frame.high - frame.low), (frame.high - previous).abs(), (frame.low - previous).abs()), axis=1).max(axis=1)


def calendar_positions(day: pd.Timestamp) -> tuple[int, int]:
    first = pd.Timestamp(day.year, day.month, 1)
    last = pd.Timestamp(day.year, day.month, calendar.monthrange(day.year, day.month)[1])
    start = sum(1 for value in pd.date_range(first, day, freq="D") if value.weekday() < 5)
    finish = sum(1 for value in pd.date_range(day, last, freq="D") if value.weekday() < 5)
    return start, finish


def daily_features(base: pd.DataFrame) -> pd.DataFrame:
    ny_dates = pd.Index(base.index.tz_convert("America/New_York").date, name="ny_date")
    work = base.copy(); work["ny_date"] = ny_dates
    daily = work.groupby("ny_date", sort=True).agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"))
    daily.index = pd.Index([pd.Timestamp(value) for value in daily.index], name="ny_date")
    tr = true_range(daily)
    daily["atr14"] = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    daily["ema20"] = daily.close.ewm(span=20, adjust=False, min_periods=20).mean()
    daily["ema50"] = daily.close.ewm(span=50, adjust=False, min_periods=50).mean()
    daily["momentum20"] = daily.close / daily.close.shift(20) - 1.0
    daily["day_return"] = daily.close.pct_change()
    shifted = daily[["close", "high", "low", "atr14", "ema20", "ema50", "momentum20", "day_return"]].shift(1)
    shifted.columns = [f"prior_{name}" for name in shifted.columns]
    positions = [calendar_positions(day) for day in daily.index]
    shifted["business_from_start"] = [value[0] for value in positions]
    shifted["business_to_end"] = [value[1] for value in positions]
    return shifted


def resample(base: pd.DataFrame, timeframe: str, daily: pd.DataFrame) -> pd.DataFrame:
    rule, _minutes = TIMEFRAMES[timeframe]
    if timeframe == "M5":
        bars = base.copy()
    else:
        bars = base.resample(rule, label="left", closed="left").agg(
            open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"),
            tick_volume=("tick_volume", "sum"), spread_price=("spread_price", "last"),
        ).dropna()
    bars["atr"] = true_range(bars).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    ny_local = bars.index.tz_convert("America/New_York")
    london_local = bars.index.tz_convert("Europe/London")
    bars["ny_date"] = pd.Index(ny_local.date)
    bars["ny_minute"] = ny_local.hour * 60 + ny_local.minute
    bars["london_minute"] = london_local.hour * 60 + london_local.minute
    for column in daily.columns:
        mapping = {key.date(): value for key, value in daily[column].items()}
        bars[column] = bars.ny_date.map(mapping)
    return bars.dropna(subset=["atr", "prior_close", "prior_ema50", "prior_atr14", "business_from_start", "business_to_end"])


def entry_flags(bars: pd.DataFrame, entry_time: str) -> np.ndarray:
    local_column = "london_minute" if entry_time == "london-open" else "ny_minute"
    target = {"london-open": 480, "ny-open": 570, "ny-first-hour": 630, "ny-power-hour": 900}[entry_time]
    minute = bars[local_column]
    candidate = bars.loc[(minute >= target) & (minute <= target + 75)]
    first_index = candidate.groupby("ny_date", sort=False).apply(lambda frame: frame.index[0], include_groups=False)
    return bars.index.isin(first_index.to_list()).astype(np.int8)


def arrays(bars: pd.DataFrame, entry_time: str) -> dict[str, np.ndarray]:
    return {
        "time": bars.index.as_unit("s").asi8.astype(np.int64),
        "open": bars.open.to_numpy(float), "high": bars.high.to_numpy(float), "low": bars.low.to_numpy(float), "close": bars.close.to_numpy(float),
        "spread": bars.spread_price.to_numpy(float), "atr": bars.atr.to_numpy(float),
        "prior_close": bars.prior_close.to_numpy(float), "prior_high": bars.prior_high.to_numpy(float), "prior_low": bars.prior_low.to_numpy(float),
        "prior_ema20": bars.prior_ema20.to_numpy(float), "prior_ema50": bars.prior_ema50.to_numpy(float),
        "prior_momentum20": bars.prior_momentum20.to_numpy(float), "prior_day_return": bars.prior_day_return.to_numpy(float),
        "business_from_start": bars.business_from_start.to_numpy(np.int16), "business_to_end": bars.business_to_end.to_numpy(np.int16),
        "entry_flag": entry_flags(bars, entry_time),
    }


@njit(cache=True)
def in_window(code, start_position, end_position):
    if code == 0: return end_position == 1 or start_position <= 3
    if code == 1: return end_position == 1
    if code == 2: return end_position <= 2
    if code == 3: return end_position <= 3
    if code == 4: return start_position == 1
    if code == 5: return start_position <= 3
    if code == 6: return end_position <= 2 or start_position <= 2
    return end_position <= 3 or start_position <= 3


@njit(cache=True)
def simulate(time, op, hi, lo, cl, spread, atr, prior_close, prior_high, prior_low, prior_ema20, prior_ema50,
             prior_momentum20, prior_day_return, business_from_start, business_to_end, entry_flag,
             start_ts, end_ts, window, confirmation, trend, direction, max_hold_hours, stop_mode, stop_value, rr, management, friction_r):
    n = len(time); capacity = n // 4 + 20
    entries = np.empty(capacity, np.int64); exits = np.empty(capacity, np.int64); results = np.empty(capacity, np.float64); sides = np.empty(capacity, np.int8)
    count = 0; position = 0; entry = 0.0; stop = 0.0; target = 0.0; initial = 0.0; entry_i = 0
    realized = 1.0; peak = 1.0; maximum_dd = 0.0
    for i in range(2, n):
        if time[i] < start_ts: continue
        if time[i] >= end_ts: break
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
            if not hit and time[i] - time[entry_i] >= max_hold_hours * 3600:
                exit_price = cl[i] if position > 0 else cl[i] + spread[i]; hit = True
            if hit:
                result = position * (exit_price - entry) / initial - friction_r
                entries[count] = time[entry_i]; exits[count] = time[i]; results[count] = result; sides[count] = position; count += 1
                realized *= max(0.01, 1.0 + 0.01 * result); peak = max(peak, realized); maximum_dd = max(maximum_dd, 1.0 - realized / peak); position = 0
            else:
                favorable = ((hi[i] - entry) / initial if position > 0 else (entry - (lo[i] + spread[i])) / initial) - friction_r
                adverse = ((lo[i] - entry) / initial if position > 0 else (entry - (hi[i] + spread[i])) / initial) - friction_r
                peak = max(peak, realized * (1.0 + 0.01 * favorable)); maximum_dd = max(maximum_dd, 1.0 - realized * (1.0 + 0.01 * adverse) / peak)
                progress = (cl[i] - entry) / initial if position > 0 else (entry - (cl[i] + spread[i])) / initial
                if management == 1 and progress >= 1.0:
                    stop = max(stop, entry) if position > 0 else min(stop, entry)
                elif management == 2 and progress >= 1.0:
                    candidate = cl[i] - 1.5 * atr[i] if position > 0 else cl[i] + spread[i] + 1.5 * atr[i]
                    stop = max(stop, candidate) if position > 0 else min(stop, candidate)
                elif management == 3 and time[i] % 900 == 0 and progress >= 0.5 * rr:
                    candidate = entry + position * 0.2 * rr * initial
                    stop = max(stop, candidate) if position > 0 else min(stop, candidate)
        if position != 0 or entry_flag[i] == 0: continue
        p = i - 1
        if not in_window(window, business_from_start[i], business_to_end[i]): continue
        side = 1 if direction == 0 else -1
        if direction == 2: side = 1 if prior_momentum20[p] >= 0 else -1
        if confirmation == 1 and side * (cl[p] - op[p]) <= 0: continue
        if confirmation == 2 and ((side > 0 and cl[p] <= hi[p-1]) or (side < 0 and cl[p] >= lo[p-1])): continue
        if trend == 1 and side * (prior_close[p] - prior_ema20[p]) <= 0: continue
        if trend == 2 and side * (prior_close[p] - prior_ema50[p]) <= 0: continue
        if trend == 3 and side * prior_momentum20[p] <= 0: continue
        if trend == 4 and (side * (prior_close[p] - prior_ema20[p]) <= 0 or side * prior_momentum20[p] <= 0): continue
        if trend == 5 and side * prior_day_return[p] >= 0: continue
        if trend == 6 and side * prior_day_return[p] <= 0: continue
        entry_price = op[i] + spread[i] if side > 0 else op[i]
        if stop_mode == 0: raw_stop = entry_price - side * stop_value * atr[p]
        elif stop_mode == 1: raw_stop = prior_low[p] - stop_value * atr[p] if side > 0 else prior_high[p] + spread[i] + stop_value * atr[p]
        else: raw_stop = lo[p] - stop_value * atr[p] if side > 0 else hi[p] + spread[i] + stop_value * atr[p]
        distance = entry_price - raw_stop if side > 0 else raw_stop - entry_price
        if not np.isfinite(distance) or distance <= max(2.0 * spread[i], 0.10 * atr[p]) or distance > 6.0 * atr[p]: continue
        position = side; entry = entry_price; initial = distance; stop = raw_stop; target = entry_price + side * rr * distance; entry_i = i
    if position != 0:
        i = n - 1; exit_price = cl[i] if position > 0 else cl[i] + spread[i]
        result = position * (exit_price - entry) / initial - friction_r
        entries[count] = time[entry_i]; exits[count] = time[i]; results[count] = result; sides[count] = position; count += 1
    return entries[:count], exits[:count], results[:count], sides[:count], 100.0 * maximum_dd


WINDOW_CODE = {name: index for index, name in enumerate(WINDOWS)}
CONFIRM_CODE = {name: index for index, name in enumerate(CONFIRMATIONS)}
TREND_CODE = {name: index for index, name in enumerate(TRENDS)}
DIRECTION_CODE = {name: index for index, name in enumerate(DIRECTIONS)}
STOP_CODE = {name: index for index, name in enumerate(("atr", "prior-day", "signal-candle"))}
MANAGEMENT_CODE = {name: index for index, name in enumerate(MANAGEMENTS)}


def metrics(entries, exits, results, sides, equity_dd=0.0) -> dict:
    if not len(results):
        return dict(return_pct=0.0, profit_factor=0.0, win_rate=0.0, max_dd_pct=0.0, trades=0, sharpe=0.0, recovery=0.0, expectancy_r=0.0, average_rr=0.0, longs=0, shorts=0)
    fractions = 0.01 * results; equity = np.r_[1.0, np.cumprod(1.0 + fractions)]; pnl = np.diff(equity)
    gains = pnl[pnl > 0].sum(); losses = -pnl[pnl < 0].sum(); pf = gains / losses if losses > 0 else 99.0
    dd = max(float(equity_dd), float(np.max(1.0 - equity / np.maximum.accumulate(equity)) * 100.0))
    daily = pd.Series(fractions, index=pd.to_datetime(exits, unit="s", utc=True)).groupby(level=0).sum().resample("1D").sum()
    sharpe = float(daily.mean() / daily.std(ddof=1) * math.sqrt(252)) if daily.std(ddof=1) > 0 else 0.0
    ret = float((equity[-1] - 1.0) * 100.0)
    return dict(return_pct=ret, profit_factor=float(min(pf, 99.0)), win_rate=float(100.0 * np.mean(results > 0)), max_dd_pct=dd,
                trades=int(len(results)), sharpe=sharpe, recovery=float(ret / dd if dd else 0.0), expectancy_r=float(results.mean()),
                average_rr=float(results[results > 0].mean() if np.any(results > 0) else 0.0), longs=int(np.sum(sides > 0)), shorts=int(np.sum(sides < 0)))


def run(cache, config: Config, period, collect=False) -> dict:
    a = cache[(config.timeframe, config.entry_time)]
    output = simulate(*(a[name] for name in ("time", "open", "high", "low", "close", "spread", "atr", "prior_close", "prior_high", "prior_low", "prior_ema20", "prior_ema50", "prior_momentum20", "prior_day_return", "business_from_start", "business_to_end", "entry_flag")),
                      int(period[0].timestamp()), int(period[1].timestamp()), WINDOW_CODE[config.window], CONFIRM_CODE[config.confirmation], TREND_CODE[config.trend], DIRECTION_CODE[config.direction],
                      config.max_hold_hours, STOP_CODE[config.stop_mode], config.stop_value, config.rr, MANAGEMENT_CODE[config.management], 0.02)
    entries, exits, results, sides, dd = output; result = metrics(entries, exits, results, sides, dd)
    if collect:
        result["trades_data"] = [dict(entry=pd.Timestamp(int(a), unit="s", tz="UTC").isoformat(), exit=pd.Timestamp(int(b), unit="s", tz="UTC").isoformat(), r=float(value), side="long" if side > 0 else "short") for a, b, value, side in zip(entries, exits, results, sides)]
    return result


def score(train: dict, validation: dict) -> float:
    if train["trades"] < 12 or validation["trades"] < 12: return -10000.0 + train["trades"] + validation["trades"]
    minimum_return = min(train["return_pct"], validation["return_pct"]); minimum_pf = min(train["profit_factor"], validation["profit_factor"])
    value = 0.35 * minimum_return + 12.0 * math.log(max(0.05, min(3.0, minimum_pf)))
    value += 1.5 * min(train["sharpe"], validation["sharpe"]) + min(train["recovery"], validation["recovery"])
    value -= 0.20 * max(train["max_dd_pct"], validation["max_dd_pct"])
    if minimum_return <= 0: value -= 25.0 + abs(minimum_return)
    if minimum_pf < 1.0: value -= 20.0 * (1.0 - minimum_pf)
    return float(value)


def evaluate(cache, config: Config):
    train = run(cache, config, TRAIN); validation = run(cache, config, VALIDATION)
    return train, validation, score(train, validation)


def row(symbol, phase, name, config, train, validation, rank):
    return dict(symbol=symbol, phase=phase, name=name, config=json.dumps(asdict(config), sort_keys=True), score=rank,
                **{f"train_{key}": value for key, value in train.items()}, **{f"validation_{key}": value for key, value in validation.items()})


def research_symbol(symbol: str, base: pd.DataFrame):
    daily = daily_features(base); bars = {timeframe: resample(base, timeframe, daily) for timeframe in TIMEFRAMES}
    cache = {(timeframe, entry): arrays(frame, entry) for timeframe, frame in bars.items() for entry in ENTRY_TIMES}
    rows = []; current = Config()

    def choose(phase: str, variants: list[Config], incumbent: Config) -> Config:
        ranked = []
        for candidate in variants:
            train, validation, value = evaluate(cache, candidate); rows.append(row(symbol, phase, phase, candidate, train, validation, value)); ranked.append((value, candidate))
        incumbent_value = evaluate(cache, incumbent)[2]
        return max(ranked + [(incumbent_value, incumbent)], key=lambda item: item[0])[1]

    current = choose("calendar-timeframe-session", [replace(current, timeframe=tf, window=window, entry_time=entry) for tf, window, entry in itertools.product(TIMEFRAMES, WINDOWS, ENTRY_TIMES)], current)
    current = choose("signal-direction", [replace(current, confirmation=confirm, trend=trend, direction=direction) for confirm, trend, direction in itertools.product(CONFIRMATIONS, TRENDS, DIRECTIONS)], current)
    current = choose("maximum-hold", [replace(current, max_hold_hours=value) for value in HOLD_HOURS], current)
    current = choose("stop", [replace(current, stop_mode=mode, stop_value=value) for mode, value in STOP_VARIANTS], current)
    current = choose("reward-risk", [replace(current, rr=value) for value in RR_VALUES], current)
    current = choose("management", [replace(current, management=value) for value in MANAGEMENTS], current)
    current = choose("interaction-recheck", [replace(current, timeframe=tf, window=window, entry_time=entry) for tf, window, entry in itertools.product(TIMEFRAMES, WINDOWS, ENTRY_TIMES)], current)
    train, validation, value = evaluate(cache, current)
    return dict(config=asdict(current), train=train, validation=validation, score=value), rows, cache


def monte_carlo(trades, paths=10000, seed=260906):
    values = np.asarray([trade["r"] for trade in trades], dtype=float)
    if not len(values): return dict(paths=paths, profitable_probability=0.0, return_p5=0.0, return_median=0.0, return_p95=0.0, dd_median=0.0, dd_p95=0.0)
    rng = np.random.default_rng(seed); returns = np.empty(paths); drawdowns = np.empty(paths); block = min(3, len(values))
    for index in range(paths):
        starts = rng.integers(0, max(1, len(values) - block + 1), size=math.ceil(len(values) / block)); sample = np.concatenate([values[start:start + block] for start in starts])[:len(values)]
        curve = np.r_[1.0, np.cumprod(1.0 + 0.01 * sample)]; returns[index] = (curve[-1] - 1.0) * 100; drawdowns[index] = np.max(1.0 - curve / np.maximum.accumulate(curve)) * 100
    return dict(paths=paths, profitable_probability=float(np.mean(returns > 0) * 100), return_p5=float(np.percentile(returns, 5)), return_median=float(np.median(returns)), return_p95=float(np.percentile(returns, 95)), dd_median=float(np.median(drawdowns)), dd_p95=float(np.percentile(drawdowns, 95)))


def make_charts(final, rows):
    CHARTS.mkdir(exist_ok=True); symbols = list(final)
    fig, axes = plt.subplots(2, 2, figsize=(13, 8)); locked = [final[symbol]["locked"] for symbol in symbols]
    axes[0, 0].bar(symbols, [item["return_pct"] for item in locked], color=["#39e6a0" if item["return_pct"] > 0 else "#ff5d73" for item in locked]); axes[0, 0].set_title("Locked-year return (%)")
    axes[0, 1].bar(symbols, [item["profit_factor"] for item in locked], color="#60a5fa"); axes[0, 1].axhline(1.1, color="#fbbf24", ls="--"); axes[0, 1].set_title("Profit factor")
    axes[1, 0].bar(symbols, [item["win_rate"] for item in locked], color="#a78bfa"); axes[1, 0].set_title("Win rate (%)")
    axes[1, 1].bar(symbols, [item["max_dd_pct"] for item in locked], color="#fb7185"); axes[1, 1].set_title("Max drawdown (%)")
    for axis in axes.flat: axis.grid(alpha=.2, axis="y")
    fig.suptitle("Month-End Institutional Flow — untouched proxy validation"); fig.tight_layout(); fig.savefig(CHARTS / "locked-summary.png", dpi=170); plt.close(fig)
    fig, axis = plt.subplots(figsize=(12, 6))
    for symbol in symbols:
        trades = final[symbol]["locked"]["trades_data"]; dates = [pd.Timestamp(item["exit"]) for item in trades]; values = np.asarray([item["r"] for item in trades]); equity = 10000 * np.cumprod(1 + .01 * values)
        if len(dates): axis.plot(dates, equity, label=symbol)
    axis.axhline(10000, color="#777", ls="--"); axis.set_title("Locked-year closed equity — fixed 1% risk"); axis.set_ylabel("USD"); axis.grid(alpha=.2); axis.legend(); fig.tight_layout(); fig.savefig(CHARTS / "locked-equity-curves.png", dpi=170); plt.close(fig)
    frame = pd.DataFrame(rows); rr = frame.loc[frame.phase == "reward-risk"].copy(); rr["rr"] = rr.config.map(lambda value: json.loads(value)["rr"])
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for axis, metric in zip(axes, ("validation_return_pct", "validation_profit_factor")):
        for symbol, group in rr.groupby("symbol"): axis.plot(group.rr, group[metric], marker="o", label=symbol)
        axis.set_xlabel("Reward / risk"); axis.set_title(metric.replace("validation_", "").replace("_", " ").title()); axis.grid(alpha=.2); axis.legend()
    fig.tight_layout(); fig.savefig(CHARTS / "rr-sensitivity.png", dpi=170); plt.close(fig)


def main():
    selections = {}; rows = []; caches = {}
    for symbol in SYMBOLS:
        base, _meta = load(symbol); selection, symbol_rows, cache = research_symbol(symbol, base)
        selections[symbol] = selection; rows.extend(symbol_rows); caches[symbol] = cache; print("SELECT", symbol, selection, flush=True)
    dump(ROOT / "selection-lock.json", selections)
    final = {}; rolling = []; monte = []
    for symbol in SYMBOLS:
        config = Config(**selections[symbol]["config"]); cache = caches[symbol]
        locked = run(cache, config, LOCKED, collect=True); full = run(cache, config, FULL, collect=True)
        final[symbol] = dict(config=asdict(config), train=selections[symbol]["train"], validation=selections[symbol]["validation"], locked=locked, full=full)
        monte.append(dict(symbol=symbol, **monte_carlo(locked["trades_data"])))
        cursor = FULL[0]
        while cursor + pd.DateOffset(months=6) <= FULL[1]:
            finish = cursor + pd.DateOffset(months=6); result = run(cache, config, (cursor, finish)); rolling.append(dict(symbol=symbol, start=cursor.date().isoformat(), end=finish.date().isoformat(), **result)); cursor += pd.DateOffset(months=3)
    dump(ROOT / "screen-final.json", final); pd.DataFrame(rows).to_csv(ROOT / "all-screen-results.csv", index=False)
    pd.DataFrame([item for item in rows if item["phase"] == "reward-risk"]).to_csv(ROOT / "rr-sensitivity.csv", index=False)
    pd.DataFrame([item for item in rows if item["phase"] == "stop"]).to_csv(ROOT / "stop-sensitivity.csv", index=False)
    pd.DataFrame([item for item in rows if item["phase"] == "management"]).to_csv(ROOT / "management-sensitivity.csv", index=False)
    pd.DataFrame([item for item in rows if item["phase"] in ("calendar-timeframe-session", "interaction-recheck")]).to_csv(ROOT / "calendar-session-timeframe-sensitivity.csv", index=False)
    pd.DataFrame(rolling).to_csv(ROOT / "rolling-stability.csv", index=False); pd.DataFrame(monte).to_csv(ROOT / "proxy-monte-carlo-summary.csv", index=False)
    make_charts(final, rows)
    dump(ROOT / "progress.json", dict(step=5, title="Month-End Institutional Flow", status="screen-complete", locked_first_read_after_freeze=True, configurations=len(rows), risk_percent=1.0, symbols=list(SYMBOLS)))


if __name__ == "__main__": main()
