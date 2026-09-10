"""Focused no-lookahead pipeline for XAUUSD time-series momentum.

Research only.  The program downloads/caches daily bars from the currently
connected Exness MT5 terminal, screens a deliberately bounded family on the
development sample, freezes one configuration, and only then evaluates the
untouched final year.  It does not modify an EA, website, installer or MT5
profile.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "Data"
CHARTS = ROOT / "Charts"
DATA_FILE = DATA / "XAUUSD-D1-Exness.npz"
DATA_META = DATA / "metadata.json"
TERMINAL = Path(r"C:\Program Files\MetaTrader 5\terminal64.exe")

SYMBOL = "XAUUSD"
DOWNLOAD_START = datetime(2010, 1, 1, tzinfo=timezone.utc)
DOWNLOAD_END = datetime(2026, 9, 2, tzinfo=timezone.utc)
DEVELOPMENT_START = pd.Timestamp("2015-01-01", tz="UTC")
LOCKED_START = pd.Timestamp("2025-09-01", tz="UTC")
LOCKED_END = pd.Timestamp("2026-09-02", tz="UTC")
CONTEXT_START = pd.Timestamp("2023-09-01", tz="UTC")
TARGET_VOL = 0.10
VOL_LOOKBACK = 252
ATR_LOOKBACK = 20
EXTRA_COST_PER_ONE_WAY_TURNOVER = 0.0005
SEED = 20260909


@dataclass(frozen=True)
class Config:
    frequency: str
    horizons: tuple[int, ...]
    aggregation: str
    direction: str
    trend: str
    management: str

    @property
    def label(self) -> str:
        hz = "-".join(str(value) for value in self.horizons)
        return f"{self.frequency}_{hz}_{self.aggregation}_{self.direction}_{self.trend}_{self.management}"

    def serializable(self) -> dict:
        value = asdict(self)
        value["horizons"] = list(self.horizons)
        return value


BASELINE = Config("monthly", (1, 3, 12), "strength", "both", "none", "rebalance")
FREQUENCIES = ("monthly", "weekly")
HORIZONS = ((1, 3, 12), (1, 3, 6), (1, 6, 12), (3, 6, 12))
AGGREGATIONS = ("strength", "majority")
DIRECTIONS = ("both", "long-only")
TRENDS = ("none", "ema100", "ema200")
MANAGEMENTS = (
    "rebalance",
    "stop-2.5atr",
    "stop-3.5atr",
    "stop-2.5atr-3r",
    "stop-2.5atr-5r",
    "trail-3atr",
    "dynamic-atr-rr",
)


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, allow_nan=False, default=json_default), encoding="utf-8"
    )


def json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def acquire() -> None:
    """Cache the connected Exness account's daily XAU history."""
    if DATA_FILE.exists() and DATA_META.exists():
        return
    import MetaTrader5 as mt5

    if not TERMINAL.is_file():
        raise FileNotFoundError(TERMINAL)
    if not mt5.initialize(path=str(TERMINAL), timeout=30_000):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        if account is None or account.server != "Exness-MT5Trial16":
            raise RuntimeError("The connected terminal is not the expected Exness-MT5Trial16 account")
        info = mt5.symbol_info(SYMBOL)
        if info is None:
            raise RuntimeError(f"{SYMBOL} is unavailable: {mt5.last_error()}")
        rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_D1, DOWNLOAD_START, DOWNLOAD_END)
        if rates is None or len(rates) < 2500:
            raise RuntimeError(f"Insufficient D1 history: {mt5.last_error()}")
        DATA.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(DATA_FILE, rates=rates)
        meta = {
            "symbol": SYMBOL,
            "broker_server": account.server,
            "account_login": int(account.login),
            "terminal": str(TERMINAL),
            "timeframe": "D1",
            "bars": int(len(rates)),
            "first_utc": datetime.fromtimestamp(int(rates[0]["time"]), timezone.utc).isoformat(),
            "last_utc": datetime.fromtimestamp(int(rates[-1]["time"]), timezone.utc).isoformat(),
            "point": float(info.point),
            "digits": int(info.digits),
            "contract_size": float(info.trade_contract_size),
            "tick_size": float(info.trade_tick_size),
            "tick_value": float(info.trade_tick_value),
            "swap_mode": int(info.swap_mode),
            "swap_long_current": float(info.swap_long),
            "swap_short_current": float(info.swap_short),
            "downloaded_utc": datetime.now(timezone.utc).isoformat(),
            "note": "Current swap values are metadata only; historical daily swap was unavailable.",
        }
        dump(DATA_META, meta)
    finally:
        mt5.shutdown()


def load() -> tuple[pd.DataFrame, dict]:
    acquire()
    rates = np.load(DATA_FILE)["rates"]
    index = pd.to_datetime(rates["time"], unit="s", utc=True)
    frame = pd.DataFrame(
        {name: rates[name].astype(float) for name in ("open", "high", "low", "close", "spread")},
        index=index,
    )
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    meta = json.loads(DATA_META.read_text(encoding="utf-8"))
    point = float(meta["point"])
    positive = frame.loc[frame.spread > 0, "spread"]
    spread_floor = float(positive.quantile(0.20)) if len(positive) else 1.0
    frame["spread_price"] = np.maximum(frame.spread, spread_floor) * point
    previous = frame.close.shift(1)
    true_range = pd.concat(
        [frame.high - frame.low, (frame.high - previous).abs(), (frame.low - previous).abs()], axis=1
    ).max(axis=1)
    frame["atr"] = true_range.rolling(ATR_LOOKBACK).mean().shift(1)
    returns = frame.close.pct_change()
    frame["annualized_vol"] = returns.rolling(VOL_LOOKBACK).std(ddof=1).shift(1) * math.sqrt(252)
    frame["ema100"] = frame.close.ewm(span=100, adjust=False).mean().shift(1)
    frame["ema200"] = frame.close.ewm(span=200, adjust=False).mean().shift(1)
    meta["spread_floor_points"] = spread_floor
    meta["data_sha256"] = file_hash(DATA_FILE)
    return frame, meta


def entry_indices(frame: pd.DataFrame, frequency: str) -> list[int]:
    if frequency == "monthly":
        keys = frame.index.strftime("%Y-%m")
    elif frequency == "weekly":
        iso = frame.index.isocalendar()
        keys = iso.year.astype(str) + "-" + iso.week.astype(str).str.zfill(2)
    else:
        raise ValueError(frequency)
    first = pd.Series(np.arange(len(frame)), index=frame.index).groupby(keys, sort=True).first()
    return [int(value) for value in first.to_list()]


def prior_close_at(frame: pd.DataFrame, cutoff: pd.Timestamp) -> float | None:
    location = frame.index.searchsorted(cutoff, side="right") - 1
    if location < 0:
        return None
    return float(frame.close.iloc[location])


def signal_at(frame: pd.DataFrame, index: int, config: Config) -> tuple[float, dict] | None:
    if index < VOL_LOOKBACK + 2:
        return None
    when = frame.index[index]
    prior_time = frame.index[index - 1]
    prior_close = float(frame.close.iloc[index - 1])
    votes: list[int] = []
    trailing: dict[int, float] = {}
    for horizon in config.horizons:
        anchor = prior_close_at(frame, prior_time - pd.DateOffset(months=horizon))
        if anchor is None or anchor <= 0:
            return None
        value = prior_close / anchor - 1.0
        trailing[horizon] = value
        votes.append(1 if value >= 0 else -1)
    if config.aggregation == "strength":
        signal = float(np.mean(votes))
    elif config.aggregation == "majority":
        signal = 1.0 if sum(votes) > 0 else -1.0
    else:
        raise ValueError(config.aggregation)
    if config.direction == "long-only" and signal < 0:
        signal = 0.0
    elif config.direction != "both" and config.direction != "long-only":
        raise ValueError(config.direction)
    if config.trend != "none" and signal:
        ema = float(frame.loc[when, config.trend])
        if not math.isfinite(ema) or (signal > 0 and prior_close <= ema) or (signal < 0 and prior_close >= ema):
            signal = 0.0
    return signal, {f"return_{horizon}m": trailing[horizon] for horizon in config.horizons}


def management_parameters(config: Config, strength: float) -> tuple[float | None, float | None, bool]:
    mode = config.management
    if mode == "rebalance":
        return None, None, False
    if mode == "stop-2.5atr":
        return 2.5, None, False
    if mode == "stop-3.5atr":
        return 3.5, None, False
    if mode == "stop-2.5atr-3r":
        return 2.5, 3.0, False
    if mode == "stop-2.5atr-5r":
        return 2.5, 5.0, False
    if mode == "trail-3atr":
        return 3.0, None, True
    if mode == "dynamic-atr-rr":
        # All horizons agreeing earns a wider 3.5 ATR / 5R structure.
        # A split vote uses a tighter 2.5 ATR / 3R structure.
        return (3.5, 5.0, False) if abs(strength) > 0.99 else (2.5, 3.0, False)
    raise ValueError(mode)


def simulate(frame: pd.DataFrame, config: Config, delay_days: int = 0) -> pd.DataFrame:
    starts = entry_indices(frame, config.frequency)
    rows: list[dict] = []
    for position in range(len(starts) - 1):
        nominal = starts[position]
        following = starts[position + 1]
        index = nominal + delay_days
        if index >= following:
            continue
        # Execution-delay tests freeze the decision and sizing information at
        # the nominal rebalance.  Only the fill moves; the delayed candle is
        # never allowed to change the already-known signal.
        calculated = signal_at(frame, nominal, config)
        if calculated is None:
            continue
        signal, signal_details = calculated
        annualized_vol = float(frame.annualized_vol.iloc[nominal])
        atr = float(frame.atr.iloc[nominal])
        if not math.isfinite(annualized_vol) or annualized_vol <= 0 or not math.isfinite(atr) or atr <= 0:
            continue
        entry = float(frame.open.iloc[index])
        weight = float(np.clip(signal * TARGET_VOL / annualized_vol, -1.0, 1.0))
        if weight == 0:
            continue
        side = 1.0 if weight > 0 else -1.0
        stop_atr, reward_risk, trailing = management_parameters(config, signal)
        stop_distance = None if stop_atr is None else atr * stop_atr
        stop = None if stop_distance is None else entry - side * stop_distance
        target = None if reward_risk is None else entry + side * stop_distance * reward_risk
        exit_index = following
        exit_price = float(frame.open.iloc[following])
        reason = "rebalance"
        active_stop = stop
        for cursor in range(index, following):
            high = float(frame.high.iloc[cursor])
            low = float(frame.low.iloc[cursor])
            stop_hit = active_stop is not None and ((side > 0 and low <= active_stop) or (side < 0 and high >= active_stop))
            target_hit = target is not None and ((side > 0 and high >= target) or (side < 0 and low <= target))
            # Deliberately adverse resolution when a daily candle touches both.
            if stop_hit:
                exit_index = cursor
                exit_price = float(active_stop)
                reason = "trailing-stop" if trailing and active_stop != stop else "stop"
                break
            if target_hit:
                exit_index = cursor
                exit_price = float(target)
                reason = "target"
                break
            if trailing and active_stop is not None:
                completed_close = float(frame.close.iloc[cursor])
                completed_atr = float(frame.atr.iloc[cursor])
                if math.isfinite(completed_atr):
                    candidate = completed_close - side * 3.0 * completed_atr
                    active_stop = max(active_stop, candidate) if side > 0 else min(active_stop, candidate)
        asset_return = side * (exit_price / entry - 1.0)
        gross_return = abs(weight) * asset_return
        entry_half_spread = float(frame.spread_price.iloc[index] / entry / 2.0)
        exit_half_spread = float(frame.spread_price.iloc[exit_index] / max(exit_price, 1e-12) / 2.0)
        spread_cost = abs(weight) * (entry_half_spread + exit_half_spread)
        stress_cost = abs(weight) * 2.0 * EXTRA_COST_PER_ONE_WAY_TURNOVER
        rows.append(
            {
                "entry_time": frame.index[index],
                "exit_time": frame.index[exit_index],
                "side": "long" if side > 0 else "short",
                "signal_strength": abs(float(signal)),
                "weight": weight,
                "entry_price": entry,
                "exit_price": exit_price,
                "reason": reason,
                "gross_return": gross_return,
                "spread_cost": spread_cost,
                "net_return": gross_return - spread_cost,
                "stress_return": gross_return - spread_cost - stress_cost,
                "double_spread_return": gross_return - 2.0 * spread_cost,
                "holding_days": (frame.index[exit_index] - frame.index[index]).total_seconds() / 86400.0,
                **signal_details,
            }
        )
    if not rows:
        return pd.DataFrame(columns=["entry_time", "exit_time", "net_return"])
    return pd.DataFrame(rows)


def slice_trades(trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    # Purge trades crossing either boundary.  Development therefore never reads
    # the first quote or return from the locked interval.
    return trades.loc[(trades.entry_time >= start) & (trades.exit_time < end)].copy()


def max_streak(values: np.ndarray, positive: bool) -> int:
    best = current = 0
    for value in values:
        hit = value > 0 if positive else value < 0
        current = current + 1 if hit else 0
        best = max(best, current)
    return int(best)


def metrics(trades: pd.DataFrame, column: str = "net_return") -> dict:
    if trades.empty:
        return {
            "return_pct": 0.0,
            "annualized_return_pct": 0.0,
            "profit_factor": None,
            "win_rate_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe": 0.0,
            "recovery_factor": None,
            "trades": 0,
            "longs": 0,
            "shorts": 0,
            "max_win_streak": 0,
            "max_loss_streak": 0,
            "best_trade_pct": 0.0,
            "worst_trade_pct": 0.0,
            "average_holding_days": 0.0,
            "best_trade_profit_share_pct": None,
        }
    values = trades[column].astype(float).to_numpy()
    values = np.maximum(values, -0.999999)
    curve = np.r_[1.0, np.cumprod(1.0 + values)]
    total = float(curve[-1] - 1.0)
    duration = max(1.0, (trades.exit_time.max() - trades.entry_time.min()).total_seconds() / 86400.0)
    years = duration / 365.25
    annualized = curve[-1] ** (1.0 / years) - 1.0 if curve[-1] > 0 else -1.0
    elapsed_days = np.maximum(1.0, trades.exit_time.diff().dt.total_seconds().fillna(30 * 86400).to_numpy() / 86400.0)
    periods_per_year = 365.25 / float(np.mean(elapsed_days))
    standard = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
    sharpe = float(np.mean(values) / standard * math.sqrt(periods_per_year)) if standard > 0 else 0.0
    drawdown = float(np.max(1.0 - curve / np.maximum.accumulate(curve)))
    gains = values[values > 0]
    losses = values[values < 0]
    pf = float(gains.sum() / -losses.sum()) if len(losses) else None
    gross_profit = float(gains.sum())
    best_share = float(gains.max() / gross_profit * 100.0) if len(gains) and gross_profit > 0 else None
    return {
        "return_pct": total * 100.0,
        "annualized_return_pct": float(annualized * 100.0),
        "profit_factor": pf,
        "win_rate_pct": float(np.mean(values > 0) * 100.0),
        "max_drawdown_pct": drawdown * 100.0,
        "sharpe": sharpe,
        "recovery_factor": total / drawdown if drawdown > 0 else None,
        "trades": int(len(values)),
        "longs": int((trades.side == "long").sum()),
        "shorts": int((trades.side == "short").sum()),
        "max_win_streak": max_streak(values, True),
        "max_loss_streak": max_streak(values, False),
        "best_trade_pct": float(values.max() * 100.0),
        "worst_trade_pct": float(values.min() * 100.0),
        "average_holding_days": float(trades.holding_days.mean()),
        "best_trade_profit_share_pct": best_share,
    }


def yearly_metrics(trades: pd.DataFrame, start_year: int, end_year: int) -> list[dict]:
    output = []
    for year in range(start_year, end_year + 1):
        start = pd.Timestamp(f"{year}-01-01", tz="UTC")
        end = pd.Timestamp(f"{year + 1}-01-01", tz="UTC")
        output.append({"year": year, **metrics(slice_trades(trades, start, end))})
    return output


def score(
    trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, frequency: str
) -> tuple[float, dict]:
    sample = slice_trades(trades, start, end)
    value = metrics(sample)
    stress = metrics(sample, "stress_return")
    years = yearly_metrics(sample, start.year, end.year - (1 if end.month == 1 and end.day == 1 else 0))
    active_years = [row for row in years if row["trades"] >= 3]
    positive_years = sum(row["return_pct"] > 0 for row in active_years)
    positive_ratio = positive_years / len(active_years) if active_years else 0.0
    value["stress_return_pct"] = stress["return_pct"]
    value["positive_years"] = positive_years
    value["active_years"] = len(active_years)
    value["positive_year_ratio"] = positive_ratio
    pf = value["profit_factor"] or 0.0
    recovery = value["recovery_factor"] or -5.0
    minimum_trades = 24 if frequency == "monthly" else 50
    gate = (
        value["trades"] >= minimum_trades
        and value["return_pct"] > 0
        and stress["return_pct"] > 0
        and pf >= 1.05
        and value["max_drawdown_pct"] <= 30.0
        and positive_ratio >= 0.60
        and (value["best_trade_profit_share_pct"] or 100.0) <= 35.0
    )
    raw = (
        4.0 * value["sharpe"]
        + 2.0 * math.log(max(0.05, pf))
        + 0.12 * value["annualized_return_pct"]
        + 0.6 * max(-5.0, min(8.0, recovery))
        + 3.0 * positive_ratio
        - 0.08 * value["max_drawdown_pct"]
        - 0.04 * (value["best_trade_profit_share_pct"] or 100.0)
    )
    return (raw if gate else raw - 1000.0), value


def configs() -> list[Config]:
    return [
        Config(frequency, horizons, aggregation, direction, trend, management)
        for frequency in FREQUENCIES
        for horizons in HORIZONS
        for aggregation in AGGREGATIONS
        for direction in DIRECTIONS
        for trend in TRENDS
        for management in MANAGEMENTS
    ]


def config_distance(left: Config, right: Config) -> int:
    return sum(
        a != b
        for a, b in zip(
            (left.frequency, left.horizons, left.aggregation, left.direction, left.trend, left.management),
            (right.frequency, right.horizons, right.aggregation, right.direction, right.trend, right.management),
        )
    )


def select_candidate(
    simulations: dict[Config, pd.DataFrame], start: pd.Timestamp, end: pd.Timestamp
) -> tuple[Config, list[dict]]:
    assessed = []
    for config, trades in simulations.items():
        base_score, value = score(trades, start, end, config.frequency)
        assessed.append({"config": config, "base_score": base_score, "metrics": value})
    score_by_config = {row["config"]: row["base_score"] for row in assessed}
    for row in assessed:
        neighbors = [
            score_by_config[other]
            for other in simulations
            if config_distance(row["config"], other) == 1 and score_by_config[other] > -900
        ]
        neighbor_median = float(np.median(neighbors)) if neighbors else -1000.0
        neighbor_positive = float(np.mean(np.asarray(neighbors) > 0) * 100.0) if neighbors else 0.0
        row["neighbor_median_score"] = neighbor_median
        row["neighbor_positive_pct"] = neighbor_positive
        row["robust_score"] = row["base_score"] + 0.25 * neighbor_median
    assessed.sort(key=lambda row: row["robust_score"], reverse=True)
    return assessed[0]["config"], assessed


def monte_carlo(returns: Iterable[float], paths: int = 10_000) -> dict:
    values = np.asarray(list(returns), dtype=float)
    if not len(values):
        raise ValueError("No returns for Monte Carlo")
    block = min(5, len(values))
    rng = np.random.default_rng(SEED)
    starts = np.arange(max(1, len(values) - block + 1))
    final = np.zeros(paths)
    max_dd = np.zeros(paths)
    for path in range(paths):
        chunks = []
        while sum(len(chunk) for chunk in chunks) < len(values):
            start = int(rng.choice(starts))
            chunks.append(values[start : start + block])
        sample = np.concatenate(chunks)[: len(values)]
        curve = np.r_[1.0, np.cumprod(1.0 + np.maximum(sample, -0.999999))]
        final[path] = curve[-1] - 1.0
        max_dd[path] = np.max(1.0 - curve / np.maximum.accumulate(curve))
    return {
        "paths": paths,
        "block_periods": block,
        "return_p5_pct": float(np.percentile(final, 5) * 100.0),
        "return_median_pct": float(np.median(final) * 100.0),
        "return_p95_pct": float(np.percentile(final, 95) * 100.0),
        "drawdown_median_pct": float(np.median(max_dd) * 100.0),
        "drawdown_p95_pct": float(np.percentile(max_dd, 95) * 100.0),
        "profitable_paths_pct": float(np.mean(final > 0) * 100.0),
        "drawdown_ge_15_pct": float(np.mean(max_dd >= 0.15) * 100.0),
        "drawdown_ge_20_pct": float(np.mean(max_dd >= 0.20) * 100.0),
    }


def serial_metrics(trades: pd.DataFrame) -> dict:
    return {
        "observed_spread": metrics(trades),
        "plus_5bps_per_one_way": metrics(trades, "stress_return"),
        "double_recorded_spread": metrics(trades, "double_spread_return"),
    }


def compound_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).sort_values("entry_time").reset_index(drop=True)


def create_charts(baseline: pd.DataFrame, selected: pd.DataFrame, walk_forward: pd.DataFrame, locked_start: pd.Timestamp) -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    plt.style.use("dark_background")
    fig, axes = plt.subplots(2, 1, figsize=(13, 9), gridspec_kw={"height_ratios": [2, 1]})
    palette = {"Paper 1/3/12 raw": "#65f6c1", "Development-selected": "#5ba6ff"}
    for label, table in (("Paper 1/3/12 raw", baseline), ("Development-selected", selected)):
        dates = table.exit_time
        equity = 10_000.0 * (1.0 + table.net_return).cumprod()
        axes[0].plot(dates, equity, label=label, linewidth=1.8, color=palette[label])
        drawdown = equity / equity.cummax() - 1.0
        axes[1].plot(dates, drawdown * 100.0, label=label, linewidth=1.4, color=palette[label])
    for axis in axes:
        axis.axvline(locked_start, color="#f6c65b", linestyle="--", alpha=0.9, label="Locked year" if axis is axes[0] else None)
        axis.grid(alpha=0.15)
    axes[0].set_title("XAUUSD monthly time-series momentum — frozen pipeline")
    axes[0].set_ylabel("Growth of $10,000")
    axes[0].legend(loc="upper left")
    axes[1].set_ylabel("Closed-period drawdown %")
    axes[1].set_xlabel("Exit date")
    fig.tight_layout()
    fig.savefig(CHARTS / "baseline-vs-selected.png", dpi=180)
    plt.close(fig)

    if not walk_forward.empty:
        fig, axis = plt.subplots(figsize=(13, 5.5))
        equity = 10_000.0 * (1.0 + walk_forward.net_return).cumprod()
        axis.plot(walk_forward.exit_time, equity, color="#a78bfa", linewidth=1.9)
        axis.set_title("Rolling selection procedure — out-of-sample folds before locked year")
        axis.set_ylabel("Growth of $10,000")
        axis.grid(alpha=0.15)
        fig.tight_layout()
        fig.savefig(CHARTS / "walk-forward-oos.png", dpi=180)
        plt.close(fig)


def fmt(value, digits: int = 2) -> str:
    return "n/a" if value is None else f"{float(value):.{digits}f}"


def main() -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    frame, data_meta = load()
    grid = configs()
    simulations: dict[Config, pd.DataFrame] = {}
    for number, config in enumerate(grid, 1):
        simulations[config] = simulate(frame, config)
        if number % 100 == 0:
            print(f"SCREEN {number}/{len(grid)}", flush=True)

    selected, assessed = select_candidate(simulations, DEVELOPMENT_START, LOCKED_START)
    baseline_all = simulations[BASELINE]
    selected_all = simulations[selected]
    baseline_dev = slice_trades(baseline_all, DEVELOPMENT_START, LOCKED_START)
    baseline_locked = slice_trades(baseline_all, LOCKED_START, LOCKED_END)
    baseline_context = slice_trades(baseline_all, CONTEXT_START, LOCKED_END)
    selected_dev = slice_trades(selected_all, DEVELOPMENT_START, LOCKED_START)
    selected_locked = slice_trades(selected_all, LOCKED_START, LOCKED_END)
    selected_context = slice_trades(selected_all, CONTEXT_START, LOCKED_END)

    lock_payload = {
        "selected_before_locked_read": True,
        "selection_window": [DEVELOPMENT_START.isoformat(), LOCKED_START.isoformat()],
        "purge_rule": "Trades crossing the locked boundary are excluded from development.",
        "configuration": selected.serializable(),
        "development": serial_metrics(selected_dev),
        "data_sha256": data_meta["data_sha256"],
        "candidate_count": len(grid),
    }
    lock_text = json.dumps(lock_payload, sort_keys=True, default=json_default)
    lock_payload["selection_sha256"] = hashlib.sha256(lock_text.encode()).hexdigest()
    dump(ROOT / "selection-lock.json", lock_payload)

    # Rolling 3-year training / following-year OOS tests, all ending before the final lock.
    folds = []
    oos_frames = []
    for test_year in range(2018, 2025):
        train_start = pd.Timestamp(f"{test_year - 3}-01-01", tz="UTC")
        train_end = pd.Timestamp(f"{test_year}-01-01", tz="UTC")
        test_start = train_end
        test_end = pd.Timestamp(f"{test_year + 1}-01-01", tz="UTC")
        choice, _ = select_candidate(simulations, train_start, train_end)
        train = slice_trades(simulations[choice], train_start, train_end)
        test = slice_trades(simulations[choice], test_start, test_end)
        folds.append(
            {
                "fold": str(test_year),
                "train": [train_start.isoformat(), train_end.isoformat()],
                "test": [test_start.isoformat(), test_end.isoformat()],
                "configuration": choice.serializable(),
                "train_metrics": metrics(train),
                "test_metrics": metrics(test),
            }
        )
        oos_frames.append(test)
    walk_forward = compound_frames(oos_frames)

    neighbors = []
    for config in grid:
        if config_distance(config, selected) != 1:
            continue
        dev_score, dev_value = score(
            simulations[config], DEVELOPMENT_START, LOCKED_START, config.frequency
        )
        locked = slice_trades(simulations[config], LOCKED_START, LOCKED_END)
        neighbors.append(
            {
                "configuration": config.serializable(),
                "development_score": dev_score,
                "development": dev_value,
                "locked": serial_metrics(locked),
            }
        )
    neighbor_locked_positive = float(
        np.mean([row["locked"]["observed_spread"]["return_pct"] > 0 for row in neighbors]) * 100.0
    ) if neighbors else 0.0

    delay = {}
    for days in (1, 2):
        delayed = simulate(frame, selected, delay_days=days)
        delay[str(days)] = {
            "locked": serial_metrics(slice_trades(delayed, LOCKED_START, LOCKED_END)),
            "three_year_context": serial_metrics(slice_trades(delayed, CONTEXT_START, LOCKED_END)),
        }

    locked_mc = monte_carlo(selected_locked.net_return)
    context_mc = monte_carlo(selected_context.net_return)
    walk_metrics = metrics(walk_forward)
    positive_folds = sum(fold["test_metrics"]["return_pct"] > 0 for fold in folds)
    locked_value = metrics(selected_locked)
    locked_stress = metrics(selected_locked, "stress_return")
    locked_double = metrics(selected_locked, "double_spread_return")
    gate_failures = []
    checks = (
        (locked_value["return_pct"] > 0, "locked return <= 0"),
        ((locked_value["profit_factor"] or 0) >= 1.20, "locked PF < 1.20"),
        (locked_value["max_drawdown_pct"] <= 15.0, "locked closed DD > 15%"),
        (locked_value["trades"] >= (35 if selected.frequency == "weekly" else 8), "locked sample too small"),
        (locked_stress["return_pct"] > 0, "locked +5bp stress <= 0"),
        (locked_double["return_pct"] > 0, "locked double-spread return <= 0"),
        (positive_folds >= 5, "fewer than 5/7 positive walk-forward folds"),
        (walk_metrics["return_pct"] > 0, "walk-forward OOS return <= 0"),
        (locked_mc["return_p5_pct"] > 0, "locked Monte Carlo return P5 <= 0"),
        (neighbor_locked_positive >= 60.0, "fewer than 60% of one-parameter neighbors win locked"),
        ((locked_value["best_trade_profit_share_pct"] or 100.0) <= 40.0, "locked result depends too heavily on one period"),
    )
    for passed, message in checks:
        if not passed:
            gate_failures.append(message)
    decision = "PASS FOR NATIVE MT5 IMPLEMENTATION REVIEW" if not gate_failures else "REJECT / RESEARCH ONLY"

    top_rows = []
    for rank, row in enumerate(assessed[:25], 1):
        top_rows.append(
            {
                "rank": rank,
                "configuration": json.dumps(row["config"].serializable(), sort_keys=True),
                "robust_score": row["robust_score"],
                "neighbor_median_score": row["neighbor_median_score"],
                "neighbor_positive_pct": row["neighbor_positive_pct"],
                **row["metrics"],
            }
        )
    pd.DataFrame(top_rows).to_csv(ROOT / "development-top-25.csv", index=False)
    selected_all.to_csv(ROOT / "selected-trades.csv", index=False)
    baseline_all.to_csv(ROOT / "paper-baseline-trades.csv", index=False)
    pd.DataFrame(
        [
            {
                "fold": fold["fold"],
                "configuration": json.dumps(fold["configuration"], sort_keys=True),
                **{f"test_{key}": value for key, value in fold["test_metrics"].items()},
            }
            for fold in folds
        ]
    ).to_csv(ROOT / "walk-forward-folds.csv", index=False)

    results = {
        "strategy": "XAUUSD Time-Series Momentum focused pipeline",
        "decision": decision,
        "gate_failures": gate_failures,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "paper_baseline": BASELINE.serializable(),
        "selected": selected.serializable(),
        "selection_sha256": lock_payload["selection_sha256"],
        "protocol": {
            "development": [DEVELOPMENT_START.isoformat(), LOCKED_START.isoformat()],
            "locked": [LOCKED_START.isoformat(), LOCKED_END.isoformat()],
            "three_year_context": [CONTEXT_START.isoformat(), LOCKED_END.isoformat()],
            "target_annualized_volatility_pct": TARGET_VOL * 100.0,
            "candidate_count": len(grid),
            "selection": "Development score plus one-parameter-neighbor median; locked year unopened until freeze.",
            "execution": "First Exness D1 open of month/week; completed closes only; adverse stop-before-target ambiguity.",
            "cost": "Recorded daily broker spread floor; +5bp one-way turnover and double-spread stress.",
        },
        "data": data_meta,
        "baseline_results": {
            "development": serial_metrics(baseline_dev),
            "locked": serial_metrics(baseline_locked),
            "three_year_context": serial_metrics(baseline_context),
        },
        "selected_results": {
            "development": serial_metrics(selected_dev),
            "locked": serial_metrics(selected_locked),
            "three_year_context": serial_metrics(selected_context),
        },
        "walk_forward": {
            "folds": folds,
            "positive_folds": positive_folds,
            "combined_oos": serial_metrics(walk_forward),
        },
        "monte_carlo": {"locked": locked_mc, "three_year_context": context_mc},
        "neighbor_robustness": {
            "count": len(neighbors),
            "locked_positive_pct": neighbor_locked_positive,
            "rows": neighbors,
        },
        "entry_delay_sensitivity": delay,
        "comparison_boundary": {
            "existing_xau_slow_trend_locked": {"return_pct": 28.62, "profit_factor": 2.17, "win_rate_pct": 31.43, "equity_dd_pct": 9.12, "trades": 35},
            "existing_xau_slow_trend_three_year": {"return_pct": 135.62, "profit_factor": 1.95, "win_rate_pct": 25.55, "equity_dd_pct": 9.20, "trades": 137},
            "warning": "Existing Slow Trend uses 1% stop-risk and native MT5 execution; TSMOM targets 10% annualized volatility on D1 bars, so absolute returns are not directly comparable.",
        },
        "limitations": [
            "Historical swap and financing cash flows are unavailable and are not reconstructed.",
            "Daily bars cannot order an intraday stop and target; ambiguous candles are resolved stop-first.",
            "Drawdown is measured on completed rebalance-period returns and can understate intraperiod equity drawdown.",
            "The paper uses futures/forwards; this is an Exness spot-CFD transfer.",
            "The candidate family is bounded but still data-mined; the final locked year and walk-forward procedure are the decision evidence.",
            "No MQL5 EA or native Every Tick validation is created unless this gate passes and the user reviews it.",
        ],
    }
    dump(ROOT / "pipeline-results.json", results)
    create_charts(baseline_context, selected_context, walk_forward, LOCKED_START)

    base_lock = results["baseline_results"]["locked"]["observed_spread"]
    pick_lock = results["selected_results"]["locked"]["observed_spread"]
    selected_text = json.dumps(selected.serializable(), sort_keys=True)
    lines = [
        "# XAUUSD Time-Series Momentum — focused pipeline",
        "",
        f"**Decision: {decision}. No EA, website, BAT, recommended portfolio or live MT5 profile was changed.**",
        "",
        "## Frozen result",
        "",
        f"The development-only screen evaluated **{len(grid)}** bounded configurations, selected `{selected_text}`, wrote a cryptographic selection lock, and only then evaluated 2025-09-01 through 2026-09-01.",
        "",
        "| Version | Sample | Return | PF | Win rate | Closed DD | Sharpe | Trades | Max win/loss streak |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, block in (("Paper 1/3/12 raw", results["baseline_results"]), ("Frozen selected", results["selected_results"])):
        for sample in ("development", "locked", "three_year_context"):
            value = block[sample]["observed_spread"]
            lines.append(
                f"| {label} | {sample.replace('_', ' ')} | {value['return_pct']:+.2f}% | {fmt(value['profit_factor'])} | "
                f"{value['win_rate_pct']:.2f}% | {value['max_drawdown_pct']:.2f}% | {value['sharpe']:.2f} | "
                f"{value['trades']} | {value['max_win_streak']}/{value['max_loss_streak']} |"
            )
    lines += [
        "",
        "![Baseline versus frozen selection](Charts/baseline-vs-selected.png)",
        "",
        "## Locked cost and execution stress",
        "",
        "| Test | Return | PF | DD |",
        "|---|---:|---:|---:|",
    ]
    for label, key in (("Recorded spread", "observed_spread"), ("+5 bp each way", "plus_5bps_per_one_way"), ("Double recorded spread", "double_recorded_spread")):
        value = results["selected_results"]["locked"][key]
        lines.append(f"| {label} | {value['return_pct']:+.2f}% | {fmt(value['profit_factor'])} | {value['max_drawdown_pct']:.2f}% |")
    lines += [
        "",
        "## Walk-forward procedure",
        "",
        f"The rolling optimization procedure produced **{positive_folds}/7 positive untouched annual folds** before the final locked year. Combined OOS return was {walk_metrics['return_pct']:+.2f}%, PF {fmt(walk_metrics['profit_factor'])}, DD {walk_metrics['max_drawdown_pct']:.2f}% and Sharpe {walk_metrics['sharpe']:.2f}.",
        "",
        "![Walk-forward OOS](Charts/walk-forward-oos.png)",
        "",
        "## Monte Carlo and neighborhood",
        "",
        f"Locked 10,000-path block bootstrap: return P5 {locked_mc['return_p5_pct']:+.2f}%, median {locked_mc['return_median_pct']:+.2f}%, P95 {locked_mc['return_p95_pct']:+.2f}%; DD P95 {locked_mc['drawdown_p95_pct']:.2f}%; profitable paths {locked_mc['profitable_paths_pct']:.2f}%.",
        f"**{neighbor_locked_positive:.2f}%** of the {len(neighbors)} one-parameter neighbors were profitable in the locked year.",
        "",
        "## Existing XAU Slow Trend comparison",
        "",
        "The current native XAU Slow Trend locked year remains +28.62% return, PF 2.17, 31.43% wins, 9.12% equity DD and 35 trades. Its three-year native context is +135.62%, PF 1.95 and 9.20% DD. This is not a clean return race: Slow Trend risks 1% to its stop, while this paper transfer targets 10% annualized volatility and is evaluated from Exness D1 bars.",
        "",
        "## Gate",
        "",
    ]
    if gate_failures:
        lines.extend(f"- FAIL: {failure}" for failure in gate_failures)
    else:
        lines.append("- Every declared robustness gate passed. The next step is a separate native MQL5 implementation review, not automatic deployment.")
    lines += [
        "",
        "## Evidence limits",
        "",
        *[f"- {item}" for item in results["limitations"]],
        "",
        "## Files",
        "",
        "- `selection-lock.json`: frozen choice and hash.",
        "- `pipeline-results.json`: complete metrics, folds, stresses and neighbors.",
        "- `development-top-25.csv`: ranked development-only finalists.",
        "- `selected-trades.csv` and `paper-baseline-trades.csv`: auditable period ledgers.",
        "- `walk-forward-folds.csv`: pre-lock rolling-selection results.",
        "",
    ]
    (ROOT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")

    verification = [
        (len(grid) == 672, "672 declared configurations evaluated"),
        (BASELINE in simulations, "paper baseline included"),
        (selected_all.entry_time.min() >= frame.index.min(), "selected ledger timestamps valid"),
        (all(selected_dev.exit_time < LOCKED_START), "development is purged before locked boundary"),
        (all(selected_locked.entry_time >= LOCKED_START), "locked entries start at declared boundary"),
        (len(folds) == 7, "seven pre-lock walk-forward folds present"),
        (locked_mc["paths"] == 10_000, "10,000 locked Monte Carlo paths present"),
        ((ROOT / "selection-lock.json").is_file(), "selection lock written"),
        ((CHARTS / "baseline-vs-selected.png").is_file(), "comparison chart rendered"),
        ((ROOT / "REPORT.md").is_file(), "report written"),
    ]
    text = []
    for passed, statement in verification:
        text.append(("PASS" if passed else "FAIL") + ": " + statement)
    text.append("SELECTION SHA256: " + lock_payload["selection_sha256"])
    (ROOT / "VERIFICATION.txt").write_text("\n".join(text) + "\n", encoding="utf-8")
    if not all(passed for passed, _ in verification):
        raise RuntimeError("Verification failed")

    print("PIPELINE COMPLETE", flush=True)
    print("SELECTED", selected_text, flush=True)
    print("BASELINE LOCKED", base_lock, flush=True)
    print("SELECTED LOCKED", pick_lock, flush=True)
    print("WALK FORWARD", positive_folds, "/7", walk_metrics, flush=True)
    print("DECISION", decision, flush=True)
    if gate_failures:
        print("FAILURES", "; ".join(gate_failures), flush=True)


if __name__ == "__main__":
    main()
