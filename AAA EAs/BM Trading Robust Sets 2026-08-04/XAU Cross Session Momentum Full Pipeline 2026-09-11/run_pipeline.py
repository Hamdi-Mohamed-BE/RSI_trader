"""Locked full pipeline for the XAUUSD cross-session momentum paper idea.

The parameter search sees only development training and validation data.  The
most recent year remains locked until a single candidate is selected.  The
script uses cached connected-broker M30 bars, recorded spreads, a conservative
$3.50/lot/side commission, the recorded XAU long swap, 1% equity risk, and a
5x effective-leverage cap.  It creates research evidence only.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, time, timezone
from pathlib import Path
import itertools
import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from numba import njit
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
RESEARCH_ROOT = ROOT.parent / "Auction and Cross Session Papers Research 2026-09-11"
DATA_FILE = RESEARCH_ROOT / "Data" / "XAUUSD-M30.npz"
AUDIT_FILE = RESEARCH_ROOT / "Data" / "broker-data-audit.json"
CHARTS = ROOT / "Charts"

START = pd.Timestamp("2021-09-13", tz="UTC")
TRAIN_END = pd.Timestamp("2024-09-11", tz="UTC")
VALIDATION_END = pd.Timestamp("2025-09-11", tz="UTC")
LOCKED_END = pd.Timestamp("2026-09-11", tz="UTC")
TRAIN = (START, TRAIN_END)
VALIDATION = (TRAIN_END, VALIDATION_END)
LOCKED = (VALIDATION_END, LOCKED_END)
FULL = (START, LOCKED_END)

RISK_PER_TRADE = 0.01
LEVERAGE_CAP = 5.0
COMMISSION_PER_LOT_SIDE = 3.50
MC_PATHS = 10_000
SEED = 20260911

SESSION_BITS = {"Asia": 1, "Europe": 2, "US": 4}
SESSION_LABELS = {
    1: "Asia", 2: "Europe", 4: "US", 3: "Asia+Europe",
    5: "Asia+US", 6: "Europe+US", 7: "All",
}
SESSIONS = (
    ("Asia", time(0, 0), time(8, 0)),
    ("Europe", time(8, 0), time(14, 30)),
    ("US", time(14, 30), time(0, 0)),
)
THRESHOLDS = (0.0, 2.5, 5.0, 10.0, 20.0, 30.0)
STOP_MULTS = (1.0, 1.5, 2.0, 3.0, 4.0)
TARGETS = (0.0, 0.75, 1.0, 1.5, 2.0, 3.0)
WEEKDAYS = ("all", "no-monday", "no-friday", "tue-thu")
TRENDS = (0, 20, 50, 100, 200)
MANAGEMENTS = ("none", "breakeven", "atr-trail")


@dataclass(frozen=True)
class Config:
    threshold_bps: float = 0.0
    session_mask: int = 7
    weekdays: str = "all"
    trend_days: int = 0
    stop_atr: float = 3.0
    target_r: float = 0.0
    management: str = "none"


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def load_data() -> tuple[pd.DataFrame, dict]:
    audit = json.loads(AUDIT_FILE.read_text(encoding="utf-8"))
    meta = audit["symbols"]["XAUUSD"]
    rates = np.load(DATA_FILE)["rates"]
    index = pd.to_datetime(rates["time"], unit="s", utc=True)
    frame = pd.DataFrame(
        {key: rates[key].astype(float) for key in ("open", "high", "low", "close", "spread", "tick_volume")},
        index=index,
    ).sort_index()
    frame = frame[~frame.index.duplicated(keep="last")]
    positive = frame.loc[frame.spread > 0, "spread"]
    spread_floor = float(positive.median())
    frame["spread_price"] = frame.spread.where(frame.spread > 0, spread_floor) * float(meta["point"])
    previous = frame.close.shift(1)
    tr = pd.concat(
        ((frame.high - frame.low), (frame.high - previous).abs(), (frame.low - previous).abs()), axis=1
    ).max(axis=1)
    frame["atr"] = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    bars_per_day = 48
    for days in (20, 50, 100, 200):
        frame[f"sma_{days}"] = frame.close.rolling(days * bars_per_day, min_periods=days * bars_per_day).mean()
    return frame, audit


def nearest_index(index: pd.DatetimeIndex, stamp: pd.Timestamp) -> int | None:
    pos = int(index.searchsorted(stamp, side="left"))
    if pos >= len(index) or index[pos] - stamp > pd.Timedelta("45min"):
        return None
    return pos


def build_sessions(frame: pd.DataFrame, meta: dict) -> pd.DataFrame:
    rows: list[dict] = []
    for day in pd.date_range(START.normalize(), LOCKED_END.normalize(), freq="D", tz="UTC"):
        if day.weekday() >= 5:
            continue
        for name, begin_time, finish_time in SESSIONS:
            begin = day + pd.Timedelta(hours=begin_time.hour, minutes=begin_time.minute)
            finish = day + pd.Timedelta(days=1) if finish_time == time(0, 0) else day + pd.Timedelta(hours=finish_time.hour, minutes=finish_time.minute)
            i, j = nearest_index(frame.index, begin), nearest_index(frame.index, finish)
            if i is None or j is None or j <= i or i < 2:
                continue
            open_bid = float(frame.open.iloc[i])
            close_bid = float(frame.open.iloc[j])
            mt5_weekday = (int(day.weekday()) + 1) % 7
            triple = 3 if mt5_weekday == int(meta["swap_rollover3days"]) else 1
            crosses_rollover = name == "US"
            swap_cash_per_lot = (
                float(meta["swap_long"]) * float(meta["point"]) * float(meta["contract_size"]) * triple
                if crosses_rollover and int(meta["swap_mode"]) == 1 else 0.0
            )
            row = {
                "start": begin, "end": finish, "start_i": i, "end_i": j,
                "session": name, "session_bit": SESSION_BITS[name], "weekday": int(day.weekday()),
                "open_bid": open_bid, "close_bid": close_bid,
                "return": close_bid / open_bid - 1.0,
                "entry_spread": float(frame.spread_price.iloc[i]),
                "commission_side_fraction": COMMISSION_PER_LOT_SIDE / (float(meta["contract_size"]) * open_bid),
                "swap_cash_per_lot": swap_cash_per_lot,
                "rollover_ns": int((day + pd.Timedelta(hours=21)).value) if crosses_rollover else -1,
            }
            for days in (20, 50, 100, 200):
                value = float(frame[f"sma_{days}"].iloc[i - 1])
                row[f"trend_{days}"] = bool(math.isfinite(value) and float(frame.close.iloc[i - 1]) > value)
            rows.append(row)
    sessions = pd.DataFrame(rows).sort_values("start").reset_index(drop=True)
    valid_gap = (sessions.start - sessions.end.shift(1)) <= pd.Timedelta("3h")
    sessions["previous_return"] = sessions["return"].shift(1).where(valid_gap)
    return sessions


@njit(cache=True)
def engine(
    session_start_ns, session_end_ns, start_i, end_i, session_bit, weekday, previous_return,
    trend20, trend50, trend100, trend200, bar_time_ns, open_bid, high_bid, low_bid,
    close_bid, spread_price, atr, rollover_ns, swap_cash_per_lot,
    period_start_ns, period_end_ns, threshold_bps, allowed_mask, weekday_code,
    trend_code, stop_atr, target_r, management_code, contract_size,
    commission_round_turn, extra_spread_multiplier, commission_multiplier,
):
    n = len(session_start_ns)
    entries = np.empty(n, np.int64)
    exits = np.empty(n, np.int64)
    equity_returns = np.empty(n, np.float64)
    r_values = np.empty(n, np.float64)
    session_codes = np.empty(n, np.int8)
    exit_reasons = np.empty(n, np.int8)  # 1 stop, 2 target, 3 time
    risk_fractions = np.empty(n, np.float64)
    count = 0
    threshold = threshold_bps / 10000.0
    for k in range(n):
        if session_start_ns[k] < period_start_ns or session_end_ns[k] > period_end_ns:
            continue
        prior = previous_return[k]
        if not np.isfinite(prior) or prior <= threshold:
            continue
        if (session_bit[k] & allowed_mask) == 0:
            continue
        wd = weekday[k]
        if weekday_code == 1 and wd == 0:
            continue
        if weekday_code == 2 and wd == 4:
            continue
        if weekday_code == 3 and (wd < 1 or wd > 3):
            continue
        trend_ok = True
        if trend_code == 20:
            trend_ok = trend20[k] == 1
        elif trend_code == 50:
            trend_ok = trend50[k] == 1
        elif trend_code == 100:
            trend_ok = trend100[k] == 1
        elif trend_code == 200:
            trend_ok = trend200[k] == 1
        if not trend_ok:
            continue

        first = start_i[k]
        finish = end_i[k]
        base_atr = atr[first - 1]
        if not np.isfinite(base_atr) or base_atr <= 0.0:
            continue
        entry = open_bid[first] + spread_price[first]
        distance = stop_atr * base_atr
        if distance <= 2.0 * spread_price[first] or entry <= 0.0:
            continue
        stop = entry - distance
        target = entry + target_r * distance
        exit_price = open_bid[finish]
        exit_bar = finish
        reason = 3
        for b in range(first, finish):
            # Conservative ordering whenever stop and target occur in one M30 bar.
            if low_bid[b] <= stop:
                exit_price = stop
                exit_bar = b
                reason = 1
                break
            if target_r > 0.0 and high_bid[b] >= target:
                exit_price = target
                exit_bar = b
                reason = 2
                break
            progress = (close_bid[b] - entry) / distance
            if management_code == 1 and progress >= 1.0:
                if entry > stop:
                    stop = entry
            elif management_code == 2 and progress >= 1.0 and np.isfinite(atr[b]):
                candidate = close_bid[b] - 1.5 * atr[b]
                if candidate > stop:
                    stop = candidate

        gross_r = (exit_price - entry) / distance
        commission_r = commission_round_turn * commission_multiplier / (contract_size * distance)
        extra_spread_r = 0.0
        if extra_spread_multiplier > 0.0:
            extra_spread_r = extra_spread_multiplier * 0.5 * (
                spread_price[first] + spread_price[min(exit_bar, len(spread_price) - 1)]
            ) / distance
        swap_r = 0.0
        if rollover_ns[k] >= 0 and bar_time_ns[min(exit_bar, len(bar_time_ns) - 1)] >= rollover_ns[k]:
            swap_r = swap_cash_per_lot[k] / (contract_size * distance)
        net_r = gross_r - commission_r - extra_spread_r + swap_r
        risk_fraction = min(RISK_PER_TRADE, LEVERAGE_CAP * distance / entry)

        entries[count] = session_start_ns[k]
        exits[count] = bar_time_ns[min(exit_bar, len(bar_time_ns) - 1)]
        equity_returns[count] = risk_fraction * net_r
        r_values[count] = net_r
        session_codes[count] = session_bit[k]
        exit_reasons[count] = reason
        risk_fractions[count] = risk_fraction
        count += 1
    return (
        entries[:count], exits[:count], equity_returns[:count], r_values[:count],
        session_codes[:count], exit_reasons[:count], risk_fractions[:count],
    )


WEEKDAY_CODE = {"all": 0, "no-monday": 1, "no-friday": 2, "tue-thu": 3}
MANAGEMENT_CODE = {"none": 0, "breakeven": 1, "atr-trail": 2}


def make_arrays(frame: pd.DataFrame, sessions: pd.DataFrame) -> dict[str, np.ndarray]:
    return {
        "session_start_ns": pd.DatetimeIndex(sessions.start).as_unit("ns").asi8.astype(np.int64),
        "session_end_ns": pd.DatetimeIndex(sessions.end).as_unit("ns").asi8.astype(np.int64),
        "start_i": sessions.start_i.to_numpy(np.int64), "end_i": sessions.end_i.to_numpy(np.int64),
        "session_bit": sessions.session_bit.to_numpy(np.int8), "weekday": sessions.weekday.to_numpy(np.int8),
        "previous_return": sessions.previous_return.to_numpy(float),
        "trend20": sessions.trend_20.to_numpy(np.int8), "trend50": sessions.trend_50.to_numpy(np.int8),
        "trend100": sessions.trend_100.to_numpy(np.int8), "trend200": sessions.trend_200.to_numpy(np.int8),
        "bar_time_ns": frame.index.as_unit("ns").asi8.astype(np.int64),
        "open_bid": frame.open.to_numpy(float), "high_bid": frame.high.to_numpy(float),
        "low_bid": frame.low.to_numpy(float), "close_bid": frame.close.to_numpy(float),
        "spread_price": frame.spread_price.to_numpy(float), "atr": frame.atr.to_numpy(float),
        "rollover_ns": sessions.rollover_ns.to_numpy(np.int64),
        "swap_cash_per_lot": sessions.swap_cash_per_lot.to_numpy(float),
    }


def streaks(values: np.ndarray) -> tuple[int, int]:
    max_win = max_loss = win = loss = 0
    for value in values:
        if value > 0:
            win += 1; loss = 0
        elif value < 0:
            loss += 1; win = 0
        else:
            win = loss = 0
        max_win = max(max_win, win); max_loss = max(max_loss, loss)
    return max_win, max_loss


def metrics(outputs: tuple[np.ndarray, ...], collect: bool = False) -> dict:
    entries, exits, returns, r_values, sessions, reasons, risks = outputs
    if not len(returns):
        return {
            "return_pct": 0.0, "cagr_pct": 0.0, "profit_factor": 0.0, "win_rate_pct": 0.0,
            "max_drawdown_pct": 0.0, "sharpe": 0.0, "recovery": 0.0, "trades": 0,
            "expectancy_r": 0.0, "max_win_streak": 0, "max_loss_streak": 0,
        }
    equity_before = np.r_[1.0, np.cumprod(np.maximum(0.01, 1.0 + returns[:-1]))]
    pnl = equity_before * returns
    equity = np.r_[1.0, np.cumprod(np.maximum(0.01, 1.0 + returns))]
    peak = np.maximum.accumulate(equity)
    drawdown = float(np.max(1.0 - equity / peak) * 100.0)
    gross_profit = float(pnl[pnl > 0].sum())
    gross_loss = float(-pnl[pnl < 0].sum())
    exit_index = pd.to_datetime(exits, unit="ns", utc=True)
    series = pd.Series(returns, index=exit_index)
    daily = series.groupby(series.index.normalize()).apply(lambda x: float(np.prod(1.0 + x) - 1.0))
    daily = daily.reindex(pd.date_range(daily.index.min(), daily.index.max(), freq="D", tz="UTC"), fill_value=0.0)
    sd = float(daily.std(ddof=1))
    sharpe = float(daily.mean() / sd * math.sqrt(252.0)) if sd > 0 else 0.0
    elapsed_years = max((exit_index.max() - pd.to_datetime(entries.min(), unit="ns", utc=True)).days / 365.25, 1 / 365.25)
    ending = float(equity[-1])
    max_win, max_loss = streaks(r_values)
    result = {
        "return_pct": (ending - 1.0) * 100.0,
        "cagr_pct": (ending ** (1.0 / elapsed_years) - 1.0) * 100.0,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else 99.0,
        "win_rate_pct": float(np.mean(r_values > 0) * 100.0),
        "max_drawdown_pct": drawdown, "sharpe": sharpe,
        "recovery": ((ending - 1.0) * 100.0 / drawdown) if drawdown > 0 else 0.0,
        "trades": int(len(returns)), "expectancy_r": float(np.mean(r_values)),
        "average_risk_pct": float(np.mean(risks) * 100.0),
        "max_win_streak": max_win, "max_loss_streak": max_loss,
        "stop_pct": float(np.mean(reasons == 1) * 100.0),
        "target_pct": float(np.mean(reasons == 2) * 100.0),
        "time_exit_pct": float(np.mean(reasons == 3) * 100.0),
    }
    if collect:
        labels = {1: "Asia", 2: "Europe", 4: "US"}
        reason_labels = {1: "stop", 2: "target", 3: "session-close"}
        result["trades_data"] = [
            {
                "entry_utc": pd.Timestamp(int(entry), unit="ns", tz="UTC").isoformat(),
                "exit_utc": pd.Timestamp(int(exit_), unit="ns", tz="UTC").isoformat(),
                "session": labels[int(session)], "exit_reason": reason_labels[int(reason)],
                "net_r": float(r_value), "equity_return": float(ret), "risk_pct": float(risk * 100.0),
            }
            for entry, exit_, ret, r_value, session, reason, risk in zip(entries, exits, returns, r_values, sessions, reasons, risks)
        ]
    return result


def run(arrays: dict[str, np.ndarray], meta: dict, config: Config, period: tuple[pd.Timestamp, pd.Timestamp], collect: bool = False, stress: bool = False) -> dict:
    ordered = [arrays[key] for key in (
        "session_start_ns", "session_end_ns", "start_i", "end_i", "session_bit", "weekday", "previous_return",
        "trend20", "trend50", "trend100", "trend200", "bar_time_ns", "open_bid", "high_bid", "low_bid",
        "close_bid", "spread_price", "atr", "rollover_ns", "swap_cash_per_lot",
    )]
    outputs = engine(
        *ordered, int(period[0].value), int(period[1].value), config.threshold_bps, config.session_mask,
        WEEKDAY_CODE[config.weekdays], config.trend_days, config.stop_atr, config.target_r,
        MANAGEMENT_CODE[config.management], float(meta["contract_size"]), COMMISSION_PER_LOT_SIDE * 2.0,
        1.0 if stress else 0.0, 1.5 if stress else 1.0,
    )
    return metrics(outputs, collect)


def score(train: dict, validation: dict) -> float:
    if train["trades"] < 250 or validation["trades"] < 70:
        return -10000.0 + train["trades"] + validation["trades"]
    min_cagr = min(train["cagr_pct"], validation["cagr_pct"])
    min_pf = min(train["profit_factor"], validation["profit_factor"])
    min_sharpe = min(train["sharpe"], validation["sharpe"])
    max_dd = max(train["max_drawdown_pct"], validation["max_drawdown_pct"])
    value = 0.55 * min_cagr + 14.0 * math.log(max(0.10, min(3.0, min_pf))) + 2.0 * min_sharpe
    value += min(train["recovery"], validation["recovery"]) - 0.30 * max_dd
    if min_cagr <= 0:
        value -= 40.0 + abs(min_cagr)
    if min_pf < 1.0:
        value -= 35.0 * (1.0 - min_pf)
    return float(value)


def stage(arrays: dict, meta: dict, configs: list[Config], stage_name: str, width: int = 30) -> tuple[list[Config], list[dict]]:
    seen: set[Config] = set()
    ranked: list[tuple[float, Config]] = []
    audit: list[dict] = []
    for config in configs:
        if config in seen:
            continue
        seen.add(config)
        train = run(arrays, meta, config, TRAIN)
        validation = run(arrays, meta, config, VALIDATION)
        rank = score(train, validation)
        ranked.append((rank, config))
        audit.append({"stage": stage_name, "score": rank, **asdict(config), **{f"train_{k}": v for k, v in train.items()}, **{f"validation_{k}": v for k, v in validation.items()}})
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [config for _, config in ranked[:width]], audit


def neighbours(config: Config) -> list[Config]:
    def local(grid: tuple[float, ...], value: float) -> list[float]:
        index = min(range(len(grid)), key=lambda i: abs(grid[i] - value))
        return list(grid[max(0, index - 1):min(len(grid), index + 2)])
    thresholds = local(THRESHOLDS, config.threshold_bps)
    stops = local(STOP_MULTS, config.stop_atr)
    targets = local(TARGETS, config.target_r)
    trends = sorted(set((0, config.trend_days)))
    return list({
        replace(config, threshold_bps=threshold, stop_atr=stop, target_r=target, trend_days=trend)
        for threshold, stop, target, trend in itertools.product(thresholds, stops, targets, trends)
    })


def monte_carlo(trades: list[dict], paths: int = MC_PATHS, block: int = 5) -> dict:
    returns = np.asarray([trade["equity_return"] for trade in trades], dtype=float)
    if not len(returns):
        return {"paths": paths, "return_p5": -100.0, "return_median": -100.0, "return_p95": -100.0, "dd_p95": 100.0, "profit_probability_pct": 0.0}
    rng = np.random.default_rng(SEED)
    final_returns = np.empty(paths, dtype=float)
    drawdowns = np.empty(paths, dtype=float)
    for path in range(paths):
        sample: list[float] = []
        while len(sample) < len(returns):
            start = int(rng.integers(0, max(1, len(returns) - block + 1)))
            sample.extend(returns[start:start + block])
        sequence = np.asarray(sample[:len(returns)], dtype=float)
        equity = np.cumprod(np.maximum(0.01, 1.0 + sequence))
        peak = np.maximum.accumulate(np.r_[1.0, equity])[1:]
        final_returns[path] = (equity[-1] - 1.0) * 100.0
        drawdowns[path] = np.max(1.0 - equity / peak) * 100.0
    return {
        "paths": paths, "block_trades": block,
        "return_p5": float(np.percentile(final_returns, 5)),
        "return_median": float(np.median(final_returns)),
        "return_p95": float(np.percentile(final_returns, 95)),
        "dd_median": float(np.median(drawdowns)), "dd_p95": float(np.percentile(drawdowns, 95)),
        "profit_probability_pct": float(np.mean(final_returns > 0) * 100.0),
    }


def raw_continuous(sessions: pd.DataFrame, meta: dict, period: tuple[pd.Timestamp, pd.Timestamp]) -> dict:
    rows = sessions[(sessions.start >= period[0]) & (sessions.end <= period[1])].copy()
    rows["position"] = (rows.previous_return > 0).astype(float)
    rows["turnover"] = (rows.position - rows.position.shift(1).fillna(0.0)).abs()
    rows["cost"] = rows.turnover * (rows.entry_spread / (2.0 * rows.open_bid) + rows.commission_side_fraction)
    rows["swap"] = np.where(rows.position > 0, rows.swap_cash_per_lot / (float(meta["contract_size"]) * rows.open_bid), 0.0)
    rows["strategy_return"] = rows.position * rows["return"] - rows.cost + rows.swap
    daily = rows.set_index("start").strategy_return.resample("1D").sum()
    equity = (1.0 + daily).cumprod()
    peak = equity.cummax()
    active_groups = (rows.position != rows.position.shift(1)).cumsum()
    trades = rows[rows.position > 0].groupby(active_groups).strategy_return.sum()
    wins = trades[trades > 0].sum(); losses = -trades[trades < 0].sum()
    sd = float(daily.std(ddof=1))
    return {
        "return_pct": float((equity.iloc[-1] - 1.0) * 100.0),
        "profit_factor": float(wins / losses) if losses > 0 else 99.0,
        "win_rate_pct": float((trades > 0).mean() * 100.0), "trades": int(len(trades)),
        "max_drawdown_pct": float((1.0 - equity / peak).max() * 100.0),
        "sharpe": float(daily.mean() / sd * math.sqrt(252.0)) if sd > 0 else 0.0,
    }


def annual_stability(arrays: dict, meta: dict, config: Config) -> list[dict]:
    boundaries = pd.date_range(START, LOCKED_END, freq=pd.DateOffset(years=1))
    if boundaries[-1] < LOCKED_END:
        boundaries = boundaries.append(pd.DatetimeIndex([LOCKED_END]))
    rows = []
    for begin, end in zip(boundaries[:-1], boundaries[1:]):
        stats = run(arrays, meta, config, (begin, end))
        rows.append({"from": begin.date().isoformat(), "to": end.date().isoformat(), **stats})
    return rows


def concentration_stress(trades: list[dict]) -> dict:
    returns = np.asarray([trade["equity_return"] for trade in trades], dtype=float)
    risks = np.asarray([trade["risk_pct"] / 100.0 for trade in trades], dtype=float)
    if not len(returns):
        return {"remove_best_return_pct": -100.0, "cap_5r_return_pct": -100.0, "cap_3r_return_pct": -100.0, "best_trade_log_gain_share_pct": 100.0}
    best = int(np.argmax(returns))
    compounded = lambda values: float((np.prod(1.0 + values) - 1.0) * 100.0)
    total_log_gain = float(np.log1p(returns).sum())
    best_share = float(np.log1p(returns[best]) / total_log_gain * 100.0) if total_log_gain > 0 else 100.0
    return {
        "best_trade_entry_utc": trades[best]["entry_utc"],
        "best_trade_r": float(trades[best]["net_r"]),
        "best_trade_equity_return_pct": float(returns[best] * 100.0),
        "best_trade_log_gain_share_pct": best_share,
        "remove_best_return_pct": compounded(np.delete(returns, best)),
        "cap_5r_return_pct": compounded(np.minimum(returns, 5.0 * risks)),
        "cap_3r_return_pct": compounded(np.minimum(returns, 3.0 * risks)),
    }


def create_chart(selected: dict, raw: dict, validation_start: pd.Timestamp, locked_start: pd.Timestamp) -> Path:
    trades = selected["full"]["trades_data"]
    equity = 10_000.0
    x = [START]; y = [equity]
    for trade in trades:
        equity *= 1.0 + trade["equity_return"]
        x.append(pd.Timestamp(trade["exit_utc"])); y.append(equity)
    CHARTS.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={"height_ratios": [2, 1]})
    fig.patch.set_facecolor("#07110f")
    for axis in axes:
        axis.set_facecolor("#07110f"); axis.tick_params(colors="#b9d2cb"); axis.grid(alpha=0.15)
    axes[0].plot(x, y, color="#55b6ff", linewidth=2)
    axes[0].axvline(validation_start, color="#74f5ca", linestyle="--", label="validation")
    axes[0].axvline(locked_start, color="#f2c14e", linestyle="--", label="locked")
    axes[0].set_title("XAU cross-session momentum — selected candidate", color="white", loc="left", fontweight="bold")
    axes[0].set_ylabel("$10,000 account", color="#b9d2cb"); axes[0].legend()
    labels = ["Raw continuous\n5Y", "Selected\n5Y", "Selected\nlocked", "Stress\nlocked"]
    values = [raw["return_pct"], selected["full"]["return_pct"], selected["locked"]["return_pct"], selected["locked_stress"]["return_pct"]]
    colors = ["#8aa5a0", "#55b6ff", "#74f5ca", "#f2c14e"]
    axes[1].bar(labels, values, color=colors)
    axes[1].axhline(0, color="white", linewidth=0.8); axes[1].set_ylabel("Return %", color="#b9d2cb")
    fig.tight_layout()
    path = CHARTS / "xau-cross-session-full-pipeline.png"
    fig.savefig(path, dpi=170, bbox_inches="tight"); plt.close(fig)
    return path


def fmt(value: float) -> str:
    return f"{value:.2f}"


def build_report(payload: dict) -> str:
    selected = payload["selected"]
    config = selected["config"]
    lines = [
        "# XAUUSD Cross-Session Momentum — Full Locked Pipeline",
        "", "Research only. No EA, BAT, website or live-account change was made.", "",
        "## Decision", "",
        f"**{'PASS — production candidate pending native MT5 confirmation.' if selected['passed'] else 'FAIL — do not add to the system.'}**",
        "", f"Gate notes: {', '.join(selected['gate_failures']) if selected['gate_failures'] else 'all research gates passed'}", "",
        "## Selected configuration", "",
        f"- Prior-session return threshold: **{config['threshold_bps']:.1f} bps**",
        f"- Sessions traded: **{SESSION_LABELS[int(config['session_mask'])]}**",
        f"- Weekdays: **{config['weekdays']}**",
        f"- Trend filter: **{'none' if int(config['trend_days']) == 0 else 'price above ' + str(config['trend_days']) + '-day M30 SMA proxy'}**",
        f"- Stop: **{config['stop_atr']:.2f} × M30 ATR(14)**",
        f"- Target: **{'session close' if config['target_r'] == 0 else str(config['target_r']) + 'R'}**",
        f"- Management: **{config['management']}**",
        "- Sizing: **1% current-equity risk, capped at 5× effective leverage**", "",
        "## Locked results", "",
        "| Segment | Return | CAGR | PF | Win rate | Max DD | Sharpe | Recovery | Trades |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, key in (("Train", "train"), ("Validation", "validation"), ("Locked", "locked"), ("Locked extra-cost stress", "locked_stress"), ("Full five years", "full")):
        row = selected[key]
        lines.append(f"| {label} | {fmt(row['return_pct'])}% | {fmt(row['cagr_pct'])}% | {fmt(row['profit_factor'])} | {fmt(row['win_rate_pct'])}% | {fmt(row['max_drawdown_pct'])}% | {fmt(row['sharpe'])} | {fmt(row['recovery'])} | {row['trades']} |")
    raw = payload["raw_baseline"]
    lines += [
        "", "## Corrected raw baseline", "",
        "The raw continuous-position baseline below now includes recorded spread, commission **and XAU rollover swap**. The earlier raw report omitted that swap charge.", "",
        "| Window | Return | PF | Win rate | Max DD | Sharpe | Trades |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for label, row in raw.items():
        lines.append(f"| {label} | {fmt(row['return_pct'])}% | {fmt(row['profit_factor'])} | {fmt(row['win_rate_pct'])}% | {fmt(row['max_drawdown_pct'])}% | {fmt(row['sharpe'])} | {row['trades']} |")
    mc = selected["monte_carlo"]
    neighbour = selected["neighbour_stability"]
    concentration = selected["concentration_stress"]
    lines += [
        "", "## Robustness", "",
        f"- 10,000-path five-trade block bootstrap on the locked trades: P5 return **{fmt(mc['return_p5'])}%**, median **{fmt(mc['return_median'])}%**, P95 **{fmt(mc['return_p95'])}%**, P95 drawdown **{fmt(mc['dd_p95'])}%**, probability of profit **{fmt(mc['profit_probability_pct'])}%**.",
        f"- Parameter neighbours: **{neighbour['profitable_pct']:.1f}% profitable**, median PF **{neighbour['median_pf']:.2f}**, median return **{neighbour['median_return_pct']:+.2f}%** in the locked year.",
        f"- Winner concentration: the best locked trade was **{concentration['best_trade_r']:.2f}R** and supplied **{concentration['best_trade_log_gain_share_pct']:.1f}%** of compounded log gain. Removing it leaves **{concentration['remove_best_return_pct']:+.2f}%**; capping all winners at 5R leaves **{concentration['cap_5r_return_pct']:+.2f}%**, while a 3R cap gives **{concentration['cap_3r_return_pct']:+.2f}%**.",
        f"- Search control: **{payload['audit']['configurations_tested']} unique staged candidates** were ranked using train and validation only; the locked year was opened once after selection.",
        "- Cost stress adds one further recorded round-trip spread and raises commission by 50%.", "",
        "## Annual stability", "",
        "| From | To | Return | PF | Win rate | DD | Trades |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in selected["annual_stability"]:
        lines.append(f"| {row['from']} | {row['to']} | {fmt(row['return_pct'])}% | {fmt(row['profit_factor'])} | {fmt(row['win_rate_pct'])}% | {fmt(row['max_drawdown_pct'])}% | {row['trades']} |")
    lines += [
        "", "## Evidence", "",
        "- `results.json`: complete selection, locked, stress, neighbour and Monte Carlo evidence.",
        "- `configuration-audit.csv`: every staged development result.",
        "- `selected-trades.csv`: full-history trade list.",
        "- `neighbour-stability.csv` and `annual-stability.csv`: robustness evidence.",
        "- `Charts/xau-cross-session-full-pipeline.png`: equity and comparison chart.", "",
        "Historical results are diagnostics, not a guarantee of future profitability.",
    ]
    return "\n".join(lines)


def main() -> int:
    frame, broker_audit = load_data()
    meta = broker_audit["symbols"]["XAUUSD"]
    sessions = build_sessions(frame, meta)
    arrays = make_arrays(frame, sessions)

    print("Stage 1/3: signal threshold, session, weekday and trend", flush=True)
    initial = [
        Config(threshold_bps=threshold, session_mask=mask, weekdays=weekday, trend_days=trend)
        for threshold, mask, weekday, trend in itertools.product(THRESHOLDS, range(1, 8), WEEKDAYS, TRENDS)
    ]
    beam, audit1 = stage(arrays, meta, initial, "signal")
    print("Stage 2/3: ATR stop and target", flush=True)
    risk_configs = [replace(config, stop_atr=stop, target_r=target) for config, stop, target in itertools.product(beam, STOP_MULTS, TARGETS)]
    beam, audit2 = stage(arrays, meta, risk_configs, "risk")
    print("Stage 3/3: trade management", flush=True)
    management_configs = [replace(config, management=management) for config, management in itertools.product(beam, MANAGEMENTS)]
    beam, audit3 = stage(arrays, meta, management_configs, "management")
    selected_config = beam[0]

    train = run(arrays, meta, selected_config, TRAIN)
    validation = run(arrays, meta, selected_config, VALIDATION)
    locked = run(arrays, meta, selected_config, LOCKED, collect=True)
    locked_stress = run(arrays, meta, selected_config, LOCKED, stress=True)
    full = run(arrays, meta, selected_config, FULL, collect=True)

    neighbour_rows = []
    for config in neighbours(selected_config):
        stats = run(arrays, meta, config, LOCKED)
        neighbour_rows.append({**asdict(config), **stats})
    neighbour_df = pd.DataFrame(neighbour_rows)
    neighbour_summary = {
        "tested": len(neighbour_df),
        "profitable_pct": float((neighbour_df.return_pct > 0).mean() * 100.0),
        "median_return_pct": float(neighbour_df.return_pct.median()),
        "median_pf": float(neighbour_df.profit_factor.median()),
    }
    mc = monte_carlo(locked["trades_data"])
    concentration = concentration_stress(locked["trades_data"])
    yearly = annual_stability(arrays, meta, selected_config)
    positive_years = sum(row["return_pct"] > 0 for row in yearly)

    failures: list[str] = []
    for name, result in (("train", train), ("validation", validation), ("locked", locked), ("locked stress", locked_stress)):
        if result["return_pct"] <= 0:
            failures.append(f"{name} return <= 0")
    if locked["profit_factor"] < 1.20: failures.append("locked PF < 1.20")
    if locked["trades"] < 80: failures.append("locked trades < 80")
    if locked["max_drawdown_pct"] > 15: failures.append("locked DD > 15%")
    if locked_stress["profit_factor"] < 1.10: failures.append("stressed locked PF < 1.10")
    if mc["return_p5"] <= 0: failures.append("Monte Carlo P5 <= 0")
    if neighbour_summary["profitable_pct"] < 60: failures.append("fewer than 60% profitable neighbours")
    if positive_years < 4: failures.append("fewer than 4/5 positive annual windows")

    raw = {
        "Train": raw_continuous(sessions, meta, TRAIN),
        "Validation": raw_continuous(sessions, meta, VALIDATION),
        "Locked": raw_continuous(sessions, meta, LOCKED),
        "Full five years": raw_continuous(sessions, meta, FULL),
    }
    selected = {
        "config": asdict(selected_config), "selection_score": score(train, validation),
        "train": train, "validation": validation, "locked": locked,
        "locked_stress": locked_stress, "full": full,
        "neighbour_stability": neighbour_summary, "monte_carlo": mc,
        "concentration_stress": concentration,
        "annual_stability": yearly, "passed": not failures, "gate_failures": failures,
    }
    audit_rows = audit1 + audit2 + audit3
    payload = {
        "strategy": "XAUUSD long-only cross-session momentum",
        "source": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7257240",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "broker": broker_audit, "data_window": [START.isoformat(), LOCKED_END.isoformat()],
        "splits": {"train": [x.isoformat() for x in TRAIN], "validation": [x.isoformat() for x in VALIDATION], "locked": [x.isoformat() for x in LOCKED]},
        "cost_model": {
            "recorded_spread": True, "commission_per_lot_side_usd": COMMISSION_PER_LOT_SIDE,
            "recorded_long_swap_points": float(meta["swap_long"]), "swap_mode": int(meta["swap_mode"]),
            "risk_per_trade_pct": RISK_PER_TRADE * 100.0, "effective_leverage_cap": LEVERAGE_CAP,
            "stress": "one extra recorded round-trip spread plus 50% higher commission",
        },
        "raw_baseline": raw, "selected": selected,
        "audit": {"configurations_tested": len(audit_rows), "locked_used_in_selection": False},
    }

    ROOT.mkdir(parents=True, exist_ok=True)
    dump(ROOT / "results.json", payload)
    pd.DataFrame(audit_rows).to_csv(ROOT / "configuration-audit.csv", index=False)
    pd.DataFrame(full["trades_data"]).to_csv(ROOT / "selected-trades.csv", index=False)
    neighbour_df.to_csv(ROOT / "neighbour-stability.csv", index=False)
    pd.DataFrame(yearly).to_csv(ROOT / "annual-stability.csv", index=False)
    chart = create_chart(selected, raw["Full five years"], TRAIN_END, VALIDATION_END)
    (ROOT / "FULL REPORT.md").write_text(build_report(payload), encoding="utf-8")
    verification = {
        "script_compiles": True, "locked_used_in_selection": False,
        "xau_only": True, "xag_tested": False, "website_changed": False,
        "bat_changed": False, "live_mt5_changed": False,
        "outputs_present": all(path.exists() for path in (
            ROOT / "results.json", ROOT / "configuration-audit.csv", ROOT / "selected-trades.csv",
            ROOT / "neighbour-stability.csv", ROOT / "annual-stability.csv", ROOT / "FULL REPORT.md", chart,
        )),
    }
    dump(ROOT / "verification.json", verification)
    print(build_report(payload), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
