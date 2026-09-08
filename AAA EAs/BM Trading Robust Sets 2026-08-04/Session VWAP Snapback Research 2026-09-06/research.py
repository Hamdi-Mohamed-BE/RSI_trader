"""Causal multi-asset screen for the Session VWAP Liquidity Snapback hypothesis."""
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
SYMBOLS = ("XAUUSD", "XAGUSD", "USTEC", "US30", "GBPJPY")
TIMEFRAMES = {"M5": ("5min", 5), "M15": ("15min", 15), "M30": ("30min", 30), "H1": ("1h", 60)}
SESSIONS = ("all-day", "asia", "london", "new-york", "overlap")
CONFIRMATIONS = ("close-inside", "rejection-candle", "engulfing")
REGIMES = ("none", "adx15", "adx20", "adx25", "ema-flat", "adx25-ema-flat", "daily-sideways")
STOP_VARIANTS = (("candle", 0.10), ("swing", 0.10), ("session-extreme", 0.10), ("atr", 0.75), ("atr", 1.0), ("atr", 1.25), ("atr", 1.5))
TARGET_VARIANTS = (("vwap", 0.0),) + tuple(("fixed-r", rr) for rr in (0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0))
MANAGEMENTS = ("none", "breakeven", "atr-trail", "dynamic-m15-50-20")
DIRECTIONS = ("both", "long-only", "short-only")
TRAIN = (pd.Timestamp("2023-09-01", tz="UTC"), pd.Timestamp("2024-09-01", tz="UTC"))
VALIDATION = (pd.Timestamp("2024-09-01", tz="UTC"), pd.Timestamp("2025-09-01", tz="UTC"))
LOCKED = (pd.Timestamp("2025-09-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC"))
FULL = (pd.Timestamp("2023-09-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC"))


@dataclass(frozen=True)
class Config:
    timeframe: str = "M15"
    session: str = "new-york"
    sigma: float = 2.0
    confirmation: str = "close-inside"
    regime: str = "adx25-ema-flat"
    direction: str = "both"
    max_trades: int = 1
    stop_mode: str = "atr"
    stop_value: float = 1.0
    target_mode: str = "fixed-r"
    rr: float = 1.0
    management: str = "none"


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def load(symbol: str) -> tuple[pd.DataFrame, dict]:
    rates = np.load(DATA / f"{symbol}-M5.npz")["rates"]
    index = pd.to_datetime(rates["time"], unit="s", utc=True)
    frame = pd.DataFrame({name: rates[name].astype(float) for name in ("open", "high", "low", "close", "tick_volume", "spread")}, index=index)
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    meta = json.loads((DATA / "metadata.json").read_text(encoding="utf-8"))["symbols"][symbol]
    positive = frame.loc[frame.spread > 0, "spread"]
    floor = float(positive.quantile(0.35)) if len(positive) else 1.0
    frame["spread_price"] = np.maximum(frame.spread, floor) * float(meta["point"])
    return frame, meta | {"spread_floor_points": floor}


def true_range(frame: pd.DataFrame) -> pd.Series:
    previous = frame.close.shift(1)
    return pd.concat(((frame.high - frame.low), (frame.high - previous).abs(), (frame.low - previous).abs()), axis=1).max(axis=1)


def adx(frame: pd.DataFrame, length: int = 14) -> pd.Series:
    up = frame.high.diff()
    down = -frame.low.diff()
    plus = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=frame.index)
    minus = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=frame.index)
    atr = true_range(frame).ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    plus_di = 100 * plus.ewm(alpha=1 / length, adjust=False, min_periods=length).mean() / atr
    minus_di = 100 * minus.ewm(alpha=1 / length, adjust=False, min_periods=length).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()


def resample(base: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    rule, minutes = TIMEFRAMES[timeframe]
    if timeframe == "M5":
        bars = base.copy()
        bars["volume"] = bars.tick_volume
    else:
        bars = base.resample(rule, label="left", closed="left").agg(
            open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"),
            volume=("tick_volume", "sum"), spread_price=("spread_price", "last"),
        ).dropna()
    bars["atr"] = true_range(bars).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    bars["adx"] = adx(bars)
    ema = bars.close.ewm(span=50, adjust=False, min_periods=50).mean()
    slope_bars = max(1, int(round(60 / minutes)))
    bars["ema_slope"] = (ema - ema.shift(slope_bars)).abs() / bars.atr.replace(0, np.nan)
    bars["swing_low"] = bars.low.rolling(4, min_periods=2).min()
    bars["swing_high"] = bars.high.rolling(4, min_periods=2).max()
    daily = base.resample("1D", label="right", closed="left").agg(close=("close", "last")).dropna()
    daily["sideways"] = (daily.close / daily.close.shift(20) - 1.0).abs() <= 0.05
    bars["daily_sideways"] = daily.sideways.reindex(bars.index, method="ffill").fillna(False)
    bars["utc_minute"] = bars.index.hour * 60 + bars.index.minute
    return bars.dropna(subset=["atr", "adx"])


def session_clock(index: pd.DatetimeIndex, session: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if session in ("all-day", "asia"):
        local = index
    elif session == "london":
        local = index.tz_convert("Europe/London")
    else:
        local = index.tz_convert("America/New_York")
    minute = np.asarray(local.hour * 60 + local.minute, dtype=np.int32)
    key = np.asarray(local.year * 10000 + local.month * 100 + local.day, dtype=np.int32)
    if session == "all-day": start, finish = 0, 24 * 60
    elif session == "asia": start, finish = 0, 8 * 60
    elif session == "london": start, finish = 8 * 60, 16 * 60 + 30
    elif session == "new-york": start, finish = 9 * 60 + 30, 16 * 60
    else: start, finish = 9 * 60 + 30, 12 * 60
    active = (minute >= start) & (minute < finish)
    entry = active & (minute >= start + 30) & (minute < finish - 15)
    return key, active, entry


def anchored_features(bars: pd.DataFrame, session: str) -> dict[str, np.ndarray]:
    key, active, entry_window = session_clock(bars.index, session)
    typical = (bars.high.to_numpy() + bars.low.to_numpy() + bars.close.to_numpy()) / 3.0
    volume = np.maximum(1.0, bars.volume.to_numpy())
    work = pd.DataFrame({
        "key": key,
        "active": active,
        "v": np.where(active, volume, 0.0),
        "pv": np.where(active, typical * volume, 0.0),
        "p2v": np.where(active, typical * typical * volume, 0.0),
        "high": np.where(active, bars.high.to_numpy(), np.nan),
        "low": np.where(active, bars.low.to_numpy(), np.nan),
    }, index=bars.index)
    group = work.groupby("key", sort=False)
    cv = group.v.cumsum(); cpv = group.pv.cumsum(); cp2v = group.p2v.cumsum()
    mean = cpv / cv.replace(0, np.nan)
    variance = cp2v / cv.replace(0, np.nan) - mean * mean
    dev = np.sqrt(np.maximum(variance.to_numpy(), 0.0))
    mean_prev = mean.groupby(work.key, sort=False).shift(1)
    dev_prev = pd.Series(dev, index=bars.index).groupby(work.key, sort=False).shift(1)
    count_prev = pd.Series(active.astype(np.int32), index=bars.index).groupby(work.key, sort=False).cumsum().groupby(work.key, sort=False).shift(1).fillna(0)
    running_high = work.high.groupby(work.key, sort=False).cummax()
    running_low = work.low.groupby(work.key, sort=False).cummin()
    return {
        "time": bars.index.as_unit("s").asi8.astype(np.int64),
        "open": bars.open.to_numpy(float), "high": bars.high.to_numpy(float), "low": bars.low.to_numpy(float), "close": bars.close.to_numpy(float),
        "spread": bars.spread_price.to_numpy(float), "atr": bars.atr.to_numpy(float), "adx": bars.adx.to_numpy(float),
        "ema_slope": bars.ema_slope.to_numpy(float), "daily_sideways": bars.daily_sideways.to_numpy(np.int8),
        "swing_low": bars.swing_low.to_numpy(float), "swing_high": bars.swing_high.to_numpy(float),
        "vwap": mean_prev.to_numpy(float), "deviation": dev_prev.to_numpy(float), "session_high": running_high.to_numpy(float), "session_low": running_low.to_numpy(float),
        "key": key, "active": active.astype(np.int8), "entry_window": entry_window.astype(np.int8), "session_bars": count_prev.to_numpy(np.int32),
        "utc_minute": bars.utc_minute.to_numpy(np.int32),
    }


@njit(cache=True)
def simulate(time, op, hi, lo, cl, spr, atr, adx_values, ema_slope, daily_sideways, swing_low, swing_high,
             vwap, deviation, session_high, session_low, key, active, entry_window, session_bars, utc_minute,
             start_ts, end_ts, sigma, confirmation, regime, direction_mode, max_trades, stop_mode, stop_value,
             target_mode, rr, management, friction_r):
    n = len(time)
    out_entry = np.empty(n // 2 + 10, np.int64); out_exit = np.empty(n // 2 + 10, np.int64)
    out_r = np.empty(n // 2 + 10, np.float64); out_side = np.empty(n // 2 + 10, np.int8)
    count = 0; current_key = -1; trades_today = 0; position = 0
    entry = 0.0; initial = 0.0; stop = 0.0; target = 0.0; entry_i = 0
    realized = 1.0; peak = 1.0; max_dd = 0.0
    for i in range(2, n):
        if time[i] < start_ts: continue
        if time[i] >= end_ts: break
        if key[i] != current_key:
            current_key = key[i]; trades_today = 0
        if position != 0 and (active[i] == 0 or key[i] != key[entry_i]):
            p = i - 1
            exit_px = cl[p] if position > 0 else cl[p] + spr[p]
            result = position * (exit_px - entry) / initial - friction_r
            out_entry[count] = time[entry_i]; out_exit[count] = time[p]; out_r[count] = result; out_side[count] = position; count += 1
            realized *= max(0.01, 1.0 + 0.01 * result); peak = max(peak, realized); max_dd = max(max_dd, 1.0 - realized / peak); position = 0
        if position != 0:
            hit = False; exit_px = 0.0
            if position > 0:
                if op[i] <= stop: exit_px = op[i]; hit = True
                elif lo[i] <= stop: exit_px = stop; hit = True
                elif hi[i] >= target: exit_px = target; hit = True
            else:
                ask_open = op[i] + spr[i]; ask_hi = hi[i] + spr[i]; ask_lo = lo[i] + spr[i]
                if ask_open >= stop: exit_px = ask_open; hit = True
                elif ask_hi >= stop: exit_px = stop; hit = True
                elif ask_lo <= target: exit_px = target; hit = True
            if hit:
                result = position * (exit_px - entry) / initial - friction_r
                out_entry[count] = time[entry_i]; out_exit[count] = time[i]; out_r[count] = result; out_side[count] = position; count += 1
                realized *= max(0.01, 1.0 + 0.01 * result); peak = max(peak, realized); max_dd = max(max_dd, 1.0 - realized / peak); position = 0
            else:
                best = ((hi[i] - entry) / initial if position > 0 else (entry - (lo[i] + spr[i])) / initial) - friction_r
                worst = ((lo[i] - entry) / initial if position > 0 else (entry - (hi[i] + spr[i])) / initial) - friction_r
                peak = max(peak, realized * (1.0 + 0.01 * best)); max_dd = max(max_dd, 1.0 - realized * (1.0 + 0.01 * worst) / peak)
                progress = (cl[i] - entry) / initial if position > 0 else (entry - (cl[i] + spr[i])) / initial
                if management == 1 and progress >= 1.0:
                    stop = max(stop, entry) if position > 0 else min(stop, entry)
                elif management == 2 and progress >= 1.0:
                    candidate = cl[i] - 1.5 * atr[i] if position > 0 else cl[i] + spr[i] + 1.5 * atr[i]
                    stop = max(stop, candidate) if position > 0 else min(stop, candidate)
                elif management == 3 and progress >= 0.5 and utc_minute[i] % 15 == 0:
                    candidate = entry + position * 0.2 * initial
                    stop = max(stop, candidate) if position > 0 else min(stop, candidate)
        if position != 0 or trades_today >= max_trades: continue
        p = i - 1
        if active[p] == 0 or entry_window[i] == 0 or key[p] != key[i] or session_bars[p] < 6: continue
        if not np.isfinite(vwap[p]) or not np.isfinite(deviation[p]) or deviation[p] <= 0.0 or not np.isfinite(atr[p]) or atr[p] <= 0.0: continue
        if regime == 1 and adx_values[p] > 15.0: continue
        if regime == 2 and adx_values[p] > 20.0: continue
        if regime == 3 and adx_values[p] > 25.0: continue
        if regime == 4 and ema_slope[p] > 0.20: continue
        if regime == 5 and (adx_values[p] > 25.0 or ema_slope[p] > 0.20): continue
        if regime == 6 and daily_sideways[p] == 0: continue
        upper = vwap[p] + sigma * deviation[p]; lower = vwap[p] - sigma * deviation[p]
        long_signal = lo[p] + spr[p] <= lower and cl[p] + spr[p] > lower
        short_signal = hi[p] >= upper and cl[p] < upper
        if confirmation == 1:
            long_signal = long_signal and cl[p] > op[p]
            short_signal = short_signal and cl[p] < op[p]
        elif confirmation == 2:
            long_signal = long_signal and cl[p] > op[p] and cl[p] >= op[p-1] and op[p] <= cl[p-1]
            short_signal = short_signal and cl[p] < op[p] and cl[p] <= op[p-1] and op[p] >= cl[p-1]
        if direction_mode == 1: short_signal = False
        if direction_mode == 2: long_signal = False
        if long_signal == short_signal: continue
        side = 1 if long_signal else -1
        ent = op[i] + spr[i] if side > 0 else op[i]
        if stop_mode == 0:
            raw_stop = lo[p] - stop_value * atr[p] if side > 0 else hi[p] + spr[p] + stop_value * atr[p]
        elif stop_mode == 1:
            raw_stop = swing_low[p] - stop_value * atr[p] if side > 0 else swing_high[p] + spr[p] + stop_value * atr[p]
        elif stop_mode == 2:
            raw_stop = session_low[p] - stop_value * atr[p] if side > 0 else session_high[p] + spr[p] + stop_value * atr[p]
        else:
            raw_stop = ent - side * stop_value * atr[p]
        distance = ent - raw_stop if side > 0 else raw_stop - ent
        if not np.isfinite(distance) or distance <= max(2.0 * spr[i], 0.10 * atr[p]) or distance > 5.0 * atr[p]: continue
        if target_mode == 0:
            tgt = vwap[p]
            if side * (tgt - ent) <= 0.25 * distance: continue
        else:
            tgt = ent + side * rr * distance
        position = side; entry = ent; initial = distance; stop = raw_stop; target = tgt; entry_i = i; trades_today += 1
    if position != 0:
        i = n - 1; exit_px = cl[i] if position > 0 else cl[i] + spr[i]
        result = position * (exit_px - entry) / initial - friction_r
        out_entry[count] = time[entry_i]; out_exit[count] = time[i]; out_r[count] = result; out_side[count] = position; count += 1
        realized *= max(0.01, 1.0 + 0.01 * result); peak = max(peak, realized); max_dd = max(max_dd, 1.0 - realized / peak)
    return out_entry[:count], out_exit[:count], out_r[:count], out_side[:count], 100.0 * max_dd


CONFIRM_CODE = {name: i for i, name in enumerate(CONFIRMATIONS)}
REGIME_CODE = {name: i for i, name in enumerate(REGIMES)}
DIRECTION_CODE = {name: i for i, name in enumerate(DIRECTIONS)}
STOP_CODE = {name: i for i, name in enumerate(("candle", "swing", "session-extreme", "atr"))}
TARGET_CODE = {name: i for i, name in enumerate(("vwap", "fixed-r"))}
MANAGEMENT_CODE = {name: i for i, name in enumerate(MANAGEMENTS)}


def metrics(entries, exits, results, sides, equity_dd=0.0) -> dict:
    if not len(results):
        return dict(return_pct=0.0, profit_factor=0.0, win_rate=0.0, max_dd_pct=0.0, trades=0, sharpe=0.0, recovery=0.0, expectancy_r=0.0, average_rr=0.0, longs=0, shorts=0)
    fraction = 0.01 * results
    equity = np.r_[1.0, np.cumprod(1.0 + fraction)]
    pnl = np.diff(equity); gain = pnl[pnl > 0].sum(); loss = -pnl[pnl < 0].sum()
    pf = gain / loss if loss > 0 else 99.0
    dd = max(float(equity_dd), float(np.max(1.0 - equity / np.maximum.accumulate(equity)) * 100.0))
    daily = pd.Series(fraction, index=pd.to_datetime(exits, unit="s", utc=True)).groupby(level=0).sum().resample("1D").sum()
    sharpe = float(daily.mean() / daily.std(ddof=1) * math.sqrt(252)) if daily.std(ddof=1) > 0 else 0.0
    ret = float((equity[-1] - 1.0) * 100.0)
    return dict(return_pct=ret, profit_factor=float(min(pf, 99.0)), win_rate=float(100.0 * np.mean(results > 0)), max_dd_pct=dd,
                trades=int(len(results)), sharpe=sharpe, recovery=float(ret / dd if dd else 0.0), expectancy_r=float(results.mean()),
                average_rr=float(results[results > 0].mean() if np.any(results > 0) else 0.0), longs=int(np.sum(sides > 0)), shorts=int(np.sum(sides < 0)))


def run(arrays: dict[str, np.ndarray], config: Config, period, collect=False, friction_r=0.02) -> dict:
    result = simulate(*(arrays[name] for name in ("time","open","high","low","close","spread","atr","adx","ema_slope","daily_sideways","swing_low","swing_high","vwap","deviation","session_high","session_low","key","active","entry_window","session_bars","utc_minute")),
                      int(period[0].timestamp()), int(period[1].timestamp()), config.sigma, CONFIRM_CODE[config.confirmation], REGIME_CODE[config.regime],
                      DIRECTION_CODE[config.direction], config.max_trades, STOP_CODE[config.stop_mode], config.stop_value,
                      TARGET_CODE[config.target_mode], config.rr, MANAGEMENT_CODE[config.management], friction_r)
    entries, exits, rs, sides, dd = result
    out = metrics(entries, exits, rs, sides, dd)
    if collect:
        out["trades_data"] = [dict(entry=pd.Timestamp(int(a), unit="s", tz="UTC").isoformat(), exit=pd.Timestamp(int(b), unit="s", tz="UTC").isoformat(), r=float(r), side="long" if s > 0 else "short") for a,b,r,s in zip(entries, exits, rs, sides)]
    return out


def robust_score(train: dict, validation: dict) -> float:
    if train["trades"] < 15 or validation["trades"] < 15: return -10000.0 + train["trades"] + validation["trades"]
    minimum_return = min(train["return_pct"], validation["return_pct"])
    minimum_pf = min(train["profit_factor"], validation["profit_factor"])
    score = 0.35 * minimum_return + 12.0 * math.log(max(0.05, min(3.0, minimum_pf)))
    score += 1.5 * min(train["sharpe"], validation["sharpe"])
    score += 1.0 * min(train["recovery"], validation["recovery"])
    score -= 0.20 * max(train["max_dd_pct"], validation["max_dd_pct"])
    if minimum_return <= 0: score -= 25.0 + abs(minimum_return)
    if minimum_pf < 1.0: score -= 20.0 * (1.0 - minimum_pf)
    return float(score)


def evaluate_prelock(cache, config: Config) -> tuple[dict, dict, float]:
    arrays = cache[(config.timeframe, config.session)]
    train = run(arrays, config, TRAIN); validation = run(arrays, config, VALIDATION)
    return train, validation, robust_score(train, validation)


def config_row(symbol: str, phase: str, name: str, config: Config, train: dict, validation: dict, score: float) -> dict:
    return dict(symbol=symbol, phase=phase, name=name, config=json.dumps(asdict(config), sort_keys=True), score=score,
                **{f"train_{k}": v for k,v in train.items()}, **{f"validation_{k}": v for k,v in validation.items()})


def research_symbol(symbol: str, base: pd.DataFrame) -> tuple[dict, list[dict], dict]:
    bars = {tf: resample(base, tf) for tf in TIMEFRAMES}
    cache = {(tf, session): anchored_features(frame, session) for tf,frame in bars.items() for session in SESSIONS}
    rows: list[dict] = []
    signal_rows = []
    for tf, session, sigma, confirmation, regime in itertools.product(TIMEFRAMES, SESSIONS, (1.5,2.0,2.5,3.0), CONFIRMATIONS, REGIMES):
        c = Config(timeframe=tf, session=session, sigma=sigma, confirmation=confirmation, regime=regime)
        tr, va, score = evaluate_prelock(cache, c)
        row = config_row(symbol, "signal", f"{tf}-{session}-{sigma:g}-{confirmation}-{regime}", c, tr, va, score); rows.append(row); signal_rows.append((score,c))
    c = max(signal_rows, key=lambda x:x[0])[1]
    def choose_stage(phase: str, variants: list[Config], current: Config) -> Config:
        candidates = []
        for x in variants:
            tr, va, score = evaluate_prelock(cache, x)
            row = config_row(symbol, phase, phase, x, tr, va, score); rows.append(row); candidates.append((score,x))
        return max(candidates + [(evaluate_prelock(cache,current)[2],current)], key=lambda x:x[0])[1]
    c = choose_stage("direction", [replace(c, direction=x) for x in DIRECTIONS], c)
    c = choose_stage("frequency", [replace(c, max_trades=x) for x in (1,2)], c)
    c = choose_stage("stop", [replace(c, stop_mode=mode, stop_value=value) for mode,value in STOP_VARIANTS], c)
    c = choose_stage("target", [replace(c, target_mode=mode, rr=value) for mode,value in TARGET_VARIANTS], c)
    c = choose_stage("management", [replace(c, management=x) for x in MANAGEMENTS], c)
    # Revisit timeframe/session with the final exit logic to catch interactions.
    interaction = []
    for tf, session in itertools.product(TIMEFRAMES, SESSIONS):
        x = replace(c, timeframe=tf, session=session); tr, va, score = evaluate_prelock(cache, x)
        rows.append(config_row(symbol, "session-timeframe-recheck", f"{tf}-{session}", x, tr, va, score)); interaction.append((score,x))
    c = max(interaction + [(evaluate_prelock(cache,c)[2],c)], key=lambda x:x[0])[1]
    tr, va, score = evaluate_prelock(cache, c)
    selection = dict(config=asdict(c), train=tr, validation=va, score=score)
    baseline = Config()
    baseline_result = {"train": run(cache[(baseline.timeframe,baseline.session)],baseline,TRAIN), "validation": run(cache[(baseline.timeframe,baseline.session)],baseline,VALIDATION)}
    return selection, rows, dict(cache=cache, baseline=baseline_result)


def monte_carlo(trades: list[dict], paths=10000, seed=260906) -> dict:
    rs = np.array([x["r"] for x in trades], dtype=float)
    if len(rs) == 0: return dict(paths=paths, profitable_probability=0.0, return_p5=0.0, return_median=0.0, return_p95=0.0, dd_median=0.0, dd_p95=0.0)
    rng=np.random.default_rng(seed); returns=np.empty(paths); drawdowns=np.empty(paths); block=5
    for p in range(paths):
        starts=rng.integers(0,max(1,len(rs)-block+1),size=math.ceil(len(rs)/block)); sample=np.concatenate([rs[s:s+block] for s in starts])[:len(rs)]
        curve=np.r_[1.0,np.cumprod(1.0+0.01*sample)];returns[p]=(curve[-1]-1.0)*100;drawdowns[p]=np.max(1.0-curve/np.maximum.accumulate(curve))*100
    return dict(paths=paths,profitable_probability=float(np.mean(returns>0)*100),return_p5=float(np.percentile(returns,5)),return_median=float(np.median(returns)),return_p95=float(np.percentile(returns,95)),dd_median=float(np.median(drawdowns)),dd_p95=float(np.percentile(drawdowns,95)),returns=returns,drawdowns=drawdowns)


def plot_results(final: dict, all_rows: list[dict]) -> None:
    CHARTS.mkdir(exist_ok=True)
    symbols=list(final); locked=[final[s]["locked"] for s in symbols]
    fig,axes=plt.subplots(2,2,figsize=(14,9)); colors=["#39e6a0" if x["return_pct"]>0 else "#ff5d73" for x in locked]
    axes[0,0].bar(symbols,[x["return_pct"] for x in locked],color=colors);axes[0,0].set_title("Locked-year return (%)")
    axes[0,1].bar(symbols,[x["profit_factor"] for x in locked],color="#60a5fa");axes[0,1].axhline(1.1,color="#fbbf24",ls="--");axes[0,1].set_title("Locked-year profit factor")
    axes[1,0].bar(symbols,[x["win_rate"] for x in locked],color="#a78bfa");axes[1,0].set_title("Locked-year win rate (%)")
    axes[1,1].bar(symbols,[x["max_dd_pct"] for x in locked],color="#fb7185");axes[1,1].set_title("Locked-year max equity drawdown (%)")
    for ax in axes.flat: ax.grid(alpha=.2,axis="y")
    fig.suptitle("Session VWAP Liquidity Snapback — untouched validation");fig.tight_layout();fig.savefig(CHARTS/"locked-summary.png",dpi=170);plt.close(fig)
    fig,ax=plt.subplots(figsize=(13,7))
    for symbol in symbols:
        trades=final[symbol]["locked"].get("trades_data",[]); dates=[pd.Timestamp(x["exit"]) for x in trades]; rs=np.array([x["r"] for x in trades]);curve=10000*np.cumprod(1+.01*rs)
        if len(dates):ax.plot(dates,curve,label=symbol,lw=1.5)
    ax.axhline(10000,color="#777",ls="--",lw=.8);ax.set_title("Frozen locked-year closed-equity curves — 1% risk");ax.set_ylabel("USD");ax.grid(alpha=.2);ax.legend();fig.tight_layout();fig.savefig(CHARTS/"locked-equity-curves.png",dpi=170);plt.close(fig)
    frame=pd.DataFrame(all_rows);fig,ax=plt.subplots(figsize=(12,7));
    for symbol in symbols:
        x=frame[(frame.symbol==symbol)&(frame.phase=="signal")];ax.scatter(x.validation_max_dd_pct,x.validation_return_pct,s=8,alpha=.45,label=symbol)
    ax.axhline(0,color="#777",lw=.8);ax.set_xlabel("Pre-lock validation DD (%)");ax.set_ylabel("Pre-lock validation return (%)");ax.set_title("Signal/session/regime configuration screen");ax.grid(alpha=.2);ax.legend();fig.tight_layout();fig.savefig(CHARTS/"configuration-screen.png",dpi=170);plt.close(fig)


def main() -> int:
    selections={}; all_rows=[]; prepared={}; metadata={}
    for symbol in SYMBOLS:
        base,meta=load(symbol);metadata[symbol]=meta
        print("SCREEN",symbol,len(base),flush=True)
        selection,rows,extra=research_symbol(symbol,base);selections[symbol]=selection;all_rows.extend(rows);prepared[symbol]=extra
        dump(ROOT/"selection-lock.json",selections)
        print("FROZEN",symbol,selection["config"],selection["train"]["return_pct"],selection["validation"]["return_pct"],flush=True)
    # The locked interval is first inspected here, after all five parameter sets are frozen.
    final={}
    for symbol in SYMBOLS:
        c=Config(**selections[symbol]["config"]); arrays=prepared[symbol]["cache"][(c.timeframe,c.session)]
        locked=run(arrays,c,LOCKED,collect=True);full=run(arrays,c,FULL,collect=True);stress=run(arrays,c,LOCKED,friction_r=0.12)
        mc=monte_carlo(locked["trades_data"]);mc_public={k:v for k,v in mc.items() if k not in ("returns","drawdowns")}
        passes=locked["return_pct"]>0 and locked["profit_factor"]>=1.10 and locked["trades"]>=30 and locked["max_dd_pct"]<15 and locked["sharpe"]>0
        final[symbol]=dict(config=asdict(c),train=selections[symbol]["train"],validation=selections[symbol]["validation"],locked=locked,full=full,cost_stress_locked=stress,monte_carlo=mc_public,screen_pass=passes,metadata=metadata[symbol])
        print("LOCKED",symbol,{k:locked[k] for k in ("return_pct","profit_factor","win_rate","max_dd_pct","trades","sharpe","recovery")},"PASS",passes,flush=True)
    dump(ROOT/"screen-final.json",final)
    pd.DataFrame(all_rows).to_csv(ROOT/"all-screen-results.csv",index=False)
    plot_results(final,all_rows)
    progress=dict(step=4,title="Session VWAP Liquidity Snapback",status="screen-complete",configurations=len(all_rows),locked_first_read_after_freeze=True,monte_carlo_paths=10000,production_changed=False,screen_passes=[s for s in SYMBOLS if final[s]["screen_pass"]])
    dump(ROOT/"progress.json",progress)
    print("SCREEN COMPLETE",len(all_rows),progress["screen_passes"],flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
