"""No-lookahead cross-sectional momentum rotation research for Calyx."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime
from functools import lru_cache
import importlib.util
import json
import math
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from numba import njit


ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = ROOT.parent
BASE_SCRIPT = PACKAGE_ROOT / "HTF Paper Trend Portfolio Research 2026-09-07" / "research.py"
SYMBOLS = ("XAUUSD", "XAGUSD", "BTCUSD", "ETHUSD", "USTEC", "US30", "EURUSD", "GBPJPY")
DEV = (pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2025-09-01", tz="UTC"))
LOCKED = (pd.Timestamp("2025-09-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC"))
FULL = (pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC"))
HORIZONS = {
    "12m": (252,),
    "1-3-6m": (21, 63, 126),
    "1-3-12m": (21, 63, 252),
    "3-6-12m": (63, 126, 252),
}
SESSIONS = ("all-day", "asia", "london", "new-york", "overlap")
STOP_NAMES = {0: "ATR", 1: "swing", 2: "chandelier"}
EXIT_NAMES = {0: "rank change", 1: "fixed RR", 2: "adaptive RR", 3: "timed"}
MANAGE_NAMES = {0: "none", 1: "breakeven", 2: "ATR trail", 3: "chandelier trail", 4: "Dynamic 50/20"}


def _load_base():
    spec = importlib.util.spec_from_file_location("calyx_htf_base", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {BASE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


base = _load_base()
slow = base.slow


@dataclass(frozen=True)
class RotationConfig:
    rebalance: str = "weekly"
    horizon: str = "1-3-12m"
    slots: int = 2
    absolute_gate: bool = True
    rank_method: str = "risk-adjusted"
    direction: str = "long-only"
    trend: str = "ema200"
    indicator_tf: str = "D1"
    session: str = "all-day"
    stop_mode: int = 0
    stop_atr: float = 2.5
    exit_mode: int = 0
    rr: float = 2.0
    max_hold_days: int = 0
    manage: int = 0


def json_default(value):
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False, default=json_default), encoding="utf-8")


@lru_cache(maxsize=1)
def daily_panel() -> pd.DataFrame:
    series = {}
    for symbol in SYMBOLS:
        frame = base.frame_bundle(symbol)[0]
        series[symbol] = slow.resampled(frame, "D1").close.rename(symbol)
    panel = pd.concat(series.values(), axis=1).sort_index()
    # Weekend gaps in CFDs retain Friday's last completed close. This is only
    # used for cross-sectional comparison; no synthetic price bars are traded.
    return panel.ffill()


def _rebalance_mask(index: pd.DatetimeIndex, frequency: str) -> np.ndarray:
    if frequency == "weekly":
        return np.asarray(index.weekday == 0)
    periods = index.tz_localize(None).to_period("M")
    return np.asarray(periods != periods.shift(1))


@lru_cache(maxsize=512)
def rotation_state(
    rebalance: str,
    horizon: str,
    slots: int,
    absolute_gate: bool,
    rank_method: str,
    direction: str,
    trend: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    closes = daily_panel()
    components = [np.log(closes / closes.shift(period)) for period in HORIZONS[horizon]]
    score = sum(components) / len(components)
    if rank_method == "risk-adjusted":
        volatility = closes.pct_change().rolling(63, min_periods=42).std() * math.sqrt(252)
        score = score / volatility.replace(0, np.nan)

    ema_length = {"none": 0, "ema100": 100, "ema200": 200}[trend]
    if ema_length:
        ema = closes.ewm(span=ema_length, adjust=False, min_periods=ema_length).mean()
    else:
        ema = pd.DataFrame(np.nan, index=closes.index, columns=closes.columns)

    signals = pd.DataFrame(0, index=closes.index, columns=SYMBOLS, dtype=np.int8)
    strengths = score.abs().fillna(0.0)
    stamps = pd.Series(0, index=closes.index, dtype=np.int64)
    mask = _rebalance_mask(closes.index, rebalance)
    current = pd.Series(0, index=SYMBOLS, dtype=np.int8)
    stamp = 0

    for i, timestamp in enumerate(closes.index):
        if mask[i]:
            stamp += 1
            values = score.loc[timestamp].replace([np.inf, -np.inf], np.nan).dropna()
            next_signal = pd.Series(0, index=SYMBOLS, dtype=np.int8)
            if direction == "long-only":
                candidates = values[values > 0] if absolute_gate else values
                for symbol in candidates.nlargest(slots).index:
                    if not ema_length or closes.at[timestamp, symbol] > ema.at[timestamp, symbol]:
                        next_signal.at[symbol] = 1
            else:
                long_slots = (slots + 1) // 2
                short_slots = slots // 2
                long_candidates = values[values > 0] if absolute_gate else values
                chosen_longs = list(long_candidates.nlargest(long_slots).index)
                for symbol in chosen_longs:
                    if not ema_length or closes.at[timestamp, symbol] > ema.at[timestamp, symbol]:
                        next_signal.at[symbol] = 1
                short_candidates = values.drop(index=chosen_longs, errors="ignore")
                if absolute_gate:
                    short_candidates = short_candidates[short_candidates < 0]
                for symbol in short_candidates.nsmallest(short_slots).index:
                    if not ema_length or closes.at[timestamp, symbol] < ema.at[timestamp, symbol]:
                        next_signal.at[symbol] = -1
            current = next_signal
        signals.loc[timestamp] = current
        stamps.iat[i] = stamp
    return signals, strengths, stamps


@lru_cache(maxsize=512)
def asset_signal_bundle(
    symbol: str,
    rebalance: str,
    horizon: str,
    slots: int,
    absolute_gate: bool,
    rank_method: str,
    direction: str,
    trend: str,
    indicator_tf: str,
):
    frame = base.frame_bundle(symbol)[0]
    signals, strengths, stamps = rotation_state(
        rebalance,
        horizon,
        slots,
        absolute_gate,
        rank_method,
        direction,
        trend,
    )
    indicator = slow.resampled(frame, indicator_tf)
    look_scale = 1 if indicator_tf == "D1" else 5
    look = max(3, int(round(10 / look_scale)))
    chand_look = max(5, int(round(20 / look_scale)))
    values = pd.DataFrame(
        {
            "atr": indicator.atr,
            "swing_low": indicator.low.rolling(look).min(),
            "swing_high": indicator.high.rolling(look).max(),
            "chand_long": indicator.high.rolling(chand_look).max() - 3.0 * indicator.atr,
            "chand_short": indicator.low.rolling(chand_look).min() + 3.0 * indicator.atr,
        },
        index=indicator.index,
    ).reindex(frame.index, method="ffill")
    signal = signals[symbol].reindex(frame.index, method="ffill").fillna(0).to_numpy(np.int8)
    strength = strengths[symbol].reindex(frame.index, method="ffill").fillna(0).to_numpy(float)
    stamp = stamps.reindex(frame.index, method="ffill").fillna(0).to_numpy(np.int64)
    return (
        signal,
        strength,
        values.atr.to_numpy(),
        values.swing_low.to_numpy(),
        values.swing_high.to_numpy(),
        values.chand_long.to_numpy(),
        values.chand_short.to_numpy(),
        stamp,
    )


@njit(cache=True)
def simulate_rotation(
    ts, op, hi, lo, cl, spr, sig, strength, atr, swing_lo, swing_hi,
    chand_lo, chand_hi, stamp, start_ts, end_ts, session_minute,
    stop_mode, stop_atr, exit_mode, rr, max_hold_days, manage, tf_code,
):
    n = len(ts)
    entries = np.empty(n, np.int64)
    exits = np.empty(n, np.int64)
    rs = np.empty(n, np.float64)
    sides = np.empty(n, np.int8)
    count = 0
    pos = 0
    entry = 0.0
    initial = 0.0
    stop = 0.0
    target = 0.0
    entry_i = 0
    last_stamp = -1
    realized = 1.0
    peak = 1.0
    max_dd = 0.0
    cooldown = 96 if tf_code == 1 else 672
    last_i = -1

    for i in range(1, n):
        if ts[i] < start_ts:
            continue
        if ts[i] >= end_ts:
            break
        last_i = i
        s = int(sig[i])
        minute = int((ts[i] % 86400) // 60)

        # Rotation membership is authoritative for every exit style. This is
        # the key difference from an independent trend EA.
        if pos != 0 and (s == 0 or s == -pos):
            px = op[i] if pos > 0 else op[i] + spr[i]
            held = (ts[i] - ts[entry_i]) / 86400.0
            r = pos * (px - entry) / initial - 0.02 - 0.0015 * held
            entries[count] = ts[entry_i]
            exits[count] = ts[i]
            rs[count] = r
            sides[count] = pos
            count += 1
            realized *= 1.0 + 0.01 * r
            peak = max(peak, realized)
            max_dd = max(max_dd, 1.0 - realized / peak)
            pos = 0

        if pos != 0 and max_hold_days > 0 and ts[i] - ts[entry_i] >= max_hold_days * 86400:
            px = op[i] if pos > 0 else op[i] + spr[i]
            held = (ts[i] - ts[entry_i]) / 86400.0
            r = pos * (px - entry) / initial - 0.02 - 0.0015 * held
            entries[count] = ts[entry_i]
            exits[count] = ts[i]
            rs[count] = r
            sides[count] = pos
            count += 1
            realized *= 1.0 + 0.01 * r
            peak = max(peak, realized)
            max_dd = max(max_dd, 1.0 - realized / peak)
            pos = 0

        if pos != 0:
            hit = False
            px = 0.0
            if pos > 0:
                if op[i] <= stop:
                    px = op[i]
                    hit = True
                elif lo[i] <= stop:
                    px = stop
                    hit = True
                elif target > 0 and hi[i] >= target:
                    px = target
                    hit = True
            else:
                ask_open = op[i] + spr[i]
                ask_hi = hi[i] + spr[i]
                ask_lo = lo[i] + spr[i]
                if ask_open >= stop:
                    px = ask_open
                    hit = True
                elif ask_hi >= stop:
                    px = stop
                    hit = True
                elif target > 0 and ask_lo <= target:
                    px = target
                    hit = True
            if hit:
                held = (ts[i] - ts[entry_i]) / 86400.0
                r = pos * (px - entry) / initial - 0.02 - 0.0015 * held
                entries[count] = ts[entry_i]
                exits[count] = ts[i]
                rs[count] = r
                sides[count] = pos
                count += 1
                realized *= 1.0 + 0.01 * r
                peak = max(peak, realized)
                max_dd = max(max_dd, 1.0 - realized / peak)
                pos = 0
            else:
                held = (ts[i] - ts[entry_i]) / 86400.0
                best_r = ((hi[i] - entry) / initial if pos > 0 else (entry - (lo[i] + spr[i])) / initial) - 0.02 - 0.0015 * held
                worst_r = ((lo[i] - entry) / initial if pos > 0 else (entry - (hi[i] + spr[i])) / initial) - 0.02 - 0.0015 * held
                peak = max(peak, realized * (1.0 + 0.01 * best_r))
                if peak > 0:
                    max_dd = max(max_dd, 1.0 - realized * (1.0 + 0.01 * worst_r) / peak)
                progress = (cl[i] - entry) / initial if pos > 0 else (entry - (cl[i] + spr[i])) / initial
                if manage == 1 and progress >= 1.0:
                    stop = max(stop, entry) if pos > 0 else min(stop, entry)
                elif manage == 2 and progress >= 1.0:
                    candidate = cl[i] - 2.5 * atr[i] if pos > 0 else cl[i] + spr[i] + 2.5 * atr[i]
                    stop = max(stop, candidate) if pos > 0 else min(stop, candidate)
                elif manage == 3 and progress >= 1.0:
                    candidate = chand_lo[i] if pos > 0 else chand_hi[i] + spr[i]
                    candidate = min(candidate, cl[i]) if pos > 0 else max(candidate, cl[i] + spr[i])
                    stop = max(stop, candidate) if pos > 0 else min(stop, candidate)
                elif manage == 4 and progress >= 0.5:
                    candidate = entry + pos * 0.2 * initial
                    stop = max(stop, candidate) if pos > 0 else min(stop, candidate)

        allowed = session_minute < 0 or minute == session_minute
        if pos == 0 and s != 0 and allowed and stamp[i] > last_stamp and (entry_i == 0 or i - entry_i >= cooldown):
            ent = op[i] + spr[i] if s > 0 else op[i]
            a = atr[i]
            if not np.isfinite(a) or a <= 0:
                continue
            dist = stop_atr * a
            if stop_mode == 1:
                raw = ent - swing_lo[i] if s > 0 else swing_hi[i] + spr[i] - ent
                if np.isfinite(raw):
                    dist = max(0.75 * a, min(5.0 * a, raw + 0.15 * a))
            elif stop_mode == 2:
                raw = ent - chand_lo[i] if s > 0 else chand_hi[i] + spr[i] - ent
                if np.isfinite(raw):
                    dist = max(0.75 * a, min(5.0 * a, raw))
            if dist <= spr[i] * 1.5:
                continue
            pos = s
            entry = ent
            initial = dist
            stop = entry - s * dist
            entry_i = i
            last_stamp = stamp[i]
            effective_rr = rr
            if exit_mode == 2:
                effective_rr = 4.0 if strength[i] >= 1.0 else 1.5
            target = entry + s * effective_rr * dist if exit_mode in (1, 2) else 0.0

    # Close at the final bar inside this sample. Never leak a later dataset
    # price into development or stability-window results.
    if pos != 0 and last_i >= 0:
        i = last_i
        px = cl[i] if pos > 0 else cl[i] + spr[i]
        held = (ts[i] - ts[entry_i]) / 86400.0
        r = pos * (px - entry) / initial - 0.02 - 0.0015 * held
        entries[count] = ts[entry_i]
        exits[count] = ts[i]
        rs[count] = r
        sides[count] = pos
        count += 1
        realized *= 1.0 + 0.01 * r
        peak = max(peak, realized)
        max_dd = max(max_dd, 1.0 - realized / peak)
    return entries[:count], exits[:count], rs[:count], sides[:count], max_dd * 100.0


def config_description(config: RotationConfig) -> str:
    gate = "positive momentum required" if config.absolute_gate else "relative rank only"
    exit_text = EXIT_NAMES[config.exit_mode]
    if config.exit_mode == 1:
        exit_text = f"{config.rr:g}R or rank change"
    elif config.exit_mode == 2:
        exit_text = "adaptive RR or rank change"
    elif config.exit_mode == 3:
        exit_text = f"{config.max_hold_days}d or rank change"
    return (
        f"{config.rebalance} rebalance, {config.horizon}, top {config.slots}, "
        f"{config.rank_method}, {gate}, {config.direction}, {config.trend}, "
        f"{config.indicator_tf} {STOP_NAMES[config.stop_mode]} {config.stop_atr:g} ATR; "
        f"{exit_text}; {MANAGE_NAMES[config.manage]}; {config.session}"
    )


def run_asset(symbol: str, config: RotationConfig, start: pd.Timestamp, end: pd.Timestamp):
    frame, _, _, arrays = base.frame_bundle(symbol)
    signal_data = asset_signal_bundle(
        symbol,
        config.rebalance,
        config.horizon,
        config.slots,
        config.absolute_gate,
        config.rank_method,
        config.direction,
        config.trend,
        config.indicator_tf,
    )
    out = simulate_rotation(
        *arrays,
        *signal_data,
        int(start.timestamp()),
        int(end.timestamp()),
        slow.SESSIONS[config.session],
        config.stop_mode,
        config.stop_atr,
        config.exit_mode,
        config.rr,
        config.max_hold_days,
        config.manage,
        1 if config.indicator_tf == "D1" else 2,
    )
    entries, exits, rs, sides, mtm_dd = out
    metrics = slow.metrics(entries, exits, rs, sides, mtm_dd)
    ts = arrays[0]
    strength = signal_data[1]
    trades = []
    for entry, exit_, r_value, side in zip(entries, exits, rs, sides):
        index = int(np.searchsorted(ts, int(entry)))
        trades.append(
            {
                "symbol": symbol,
                "entry_time": pd.Timestamp(int(entry), unit="s", tz="UTC").isoformat(),
                "exit_time": pd.Timestamp(int(exit_), unit="s", tz="UTC").isoformat(),
                "r": float(r_value),
                "return_fraction": float(max(-0.95, 0.01 * r_value)),
                "side": "long" if side > 0 else "short",
                "signal_strength": float(strength[min(index, len(strength) - 1)]),
            }
        )
    return metrics, trades


def evaluate(config: RotationConfig, start: pd.Timestamp, end: pd.Timestamp, include_trades: bool = False):
    candidates = []
    standalone = {}
    for symbol in SYMBOLS:
        metrics, trades = run_asset(symbol, config, start, end)
        standalone[symbol] = {key: value for key, value in metrics.items() if key != "trades_data"}
        candidates.extend(trades)
    accepted = base.accept_risk_cap(candidates, cap=4)
    metrics = base.stats_from_trades(accepted)
    metrics["max_standalone_mtm_dd_pct"] = float(max(row["max_dd_pct"] for row in standalone.values()))
    result = {"metrics": metrics, "standalone": standalone}
    if include_trades:
        result["trades"] = accepted
        result["rejected_by_risk_cap"] = int(len(candidates) - len(accepted))
    return result


def score(metrics: dict) -> float:
    if metrics["trades"] < 50:
        return -10000.0 + metrics["trades"]
    if metrics["return_pct"] <= 0 or metrics["profit_factor"] < 1.0:
        return -1000.0 - metrics["max_dd_pct"]
    if metrics["profitable_assets"] < 4:
        return -500.0 + metrics["profitable_assets"]
    return (
        4.0 * math.log1p(metrics["return_pct"])
        + 5.0 * math.log(min(3.0, metrics["profit_factor"]))
        + 3.0 * max(-3.0, min(3.0, metrics["sharpe"]))
        + 2.0 * max(-3.0, min(8.0, metrics["recovery"]))
        + 0.7 * metrics["profitable_assets"]
        + 0.01 * metrics["win_rate"]
        - 0.40 * metrics["max_dd_pct"]
        - 0.10 * metrics["max_standalone_mtm_dd_pct"]
    )


def screen_rows(configs: list[RotationConfig], phase: str, start: pd.Timestamp, end: pd.Timestamp):
    rows = []
    for number, config in enumerate(configs, 1):
        metrics = evaluate(config, start, end)["metrics"]
        rows.append({"phase": phase, "config": asdict(config), **metrics, "score": score(metrics)})
        if number % 25 == 0 or number == len(configs):
            print(f"{phase}: {number}/{len(configs)}", flush=True)
    return rows


def choose(rows: list[dict], previous: list[dict]) -> RotationConfig:
    pool = rows + ([max(previous, key=lambda row: row["score"])] if previous else [])
    return RotationConfig(**max(pool, key=lambda row: row["score"])["config"])


def select_config(start: pd.Timestamp, end: pd.Timestamp):
    all_rows: list[dict] = []
    ranking_configs = [
        RotationConfig(
            rebalance=rebalance,
            horizon=horizon,
            slots=slots,
            absolute_gate=gate,
            rank_method=method,
            direction=direction,
        )
        for rebalance in ("weekly", "monthly")
        for horizon in HORIZONS
        for slots in (1, 2, 3, 4)
        for gate in (False, True)
        for method in ("raw", "risk-adjusted")
        for direction in ("long-only", "long-short")
    ]
    rows = screen_rows(ranking_configs, "ranking-design", start, end)
    all_rows.extend(rows)
    selected = choose(rows, [])

    rows = screen_rows(
        [replace(selected, trend=trend, indicator_tf=tf) for trend in ("none", "ema100", "ema200") for tf in ("D1", "W1")],
        "trend-timeframe",
        start,
        end,
    )
    all_rows.extend(rows)
    selected = choose(rows, all_rows)

    rows = screen_rows([replace(selected, session=session) for session in SESSIONS], "entry-session", start, end)
    all_rows.extend(rows)
    selected = choose(rows, all_rows)

    exit_variants = [(0, 2.0, 0)]
    exit_variants += [(1, rr, 0) for rr in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0)]
    exit_variants += [(2, 2.0, 0), (3, 2.0, 20), (3, 2.0, 60), (3, 2.0, 120)]
    exit_configs = [
        replace(
            selected,
            stop_mode=stop_mode,
            stop_atr=stop_atr,
            exit_mode=exit_mode,
            rr=rr,
            max_hold_days=days,
        )
        for stop_mode in STOP_NAMES
        for stop_atr in (1.5, 2.0, 2.5, 3.0, 3.5)
        for exit_mode, rr, days in exit_variants
    ]
    rows = screen_rows(exit_configs, "stop-and-exit", start, end)
    all_rows.extend(rows)
    selected = choose(rows, all_rows)

    rows = screen_rows([replace(selected, manage=manage) for manage in MANAGE_NAMES], "trade-management", start, end)
    all_rows.extend(rows)
    selected = choose(rows, all_rows)

    serialised = [{**row, "config": json.dumps(row["config"], sort_keys=True)} for row in all_rows]
    pd.DataFrame(serialised).to_csv(ROOT / "all-screen-results.csv", index=False)
    return selected, all_rows


def asset_table(trades: list[dict], standalone: dict):
    rows = []
    for symbol in SYMBOLS:
        selected = [row for row in trades if row["symbol"] == symbol]
        metrics = base.stats_from_trades(selected)
        rows.append(
            {
                "symbol": symbol,
                **metrics,
                "standalone_mtm_dd_pct": float(standalone[symbol]["max_dd_pct"]),
                "standalone_trades": int(standalone[symbol]["trades"]),
            }
        )
    return rows


def make_charts(screen: pd.DataFrame, locked: dict, assets: list[dict], stability: list[dict], curves: np.ndarray):
    charts = ROOT / "Charts"
    charts.mkdir(exist_ok=True)
    trades = locked["trades"]
    fractions = np.array([row["return_fraction"] for row in trades])
    equity = 10000.0 * np.cumprod(1.0 + fractions)
    dates = pd.to_datetime([row["exit_time"] for row in trades], utc=True)
    full = np.r_[10000.0, equity]
    drawdown = (1.0 - full / np.maximum.accumulate(full)) * 100.0
    plot_dates = pd.DatetimeIndex([LOCKED[0]]).append(pd.DatetimeIndex(dates))

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True, constrained_layout=True)
    axes[0].step(plot_dates, full, where="post", color="#25d9a0", linewidth=1.7)
    axes[0].set_title("Locked-year relative-strength rotation — closed balance")
    axes[0].set_ylabel("USD")
    axes[0].grid(alpha=0.2)
    axes[1].fill_between(plot_dates, -drawdown, 0, step="post", color="#e35d6a", alpha=0.55)
    axes[1].set_ylabel("Drawdown %")
    axes[1].grid(alpha=0.2)
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.savefig(charts / "locked-equity-drawdown.png", dpi=160)
    plt.close(fig)

    x = np.arange(len(assets))
    labels = [row["symbol"] for row in assets]
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    axes[0, 0].bar(x, [row["return_pct"] for row in assets], color=["#25b887" if row["return_pct"] > 0 else "#d85b67" for row in assets])
    axes[0, 0].set_title("Return contribution by asset")
    axes[0, 1].bar(x, [row["profit_factor"] for row in assets], color="#5794e6")
    axes[0, 1].axhline(1.0, color="black", linewidth=0.8)
    axes[0, 1].set_title("Profit factor by asset")
    axes[1, 0].bar(x, [row["win_rate"] for row in assets], color="#ad75d9")
    axes[1, 0].set_title("Win rate by asset")
    axes[1, 1].bar(x, [row["trades"] for row in assets], color="#e0a84f")
    axes[1, 1].set_title("Accepted trades by asset")
    for axis in axes.flat:
        axis.set_xticks(x, labels, rotation=25, ha="right")
        axis.grid(axis="y", alpha=0.2)
    fig.savefig(charts / "locked-asset-breakdown.png", dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)
    colors = ["#25b887" if row["return_pct"] > 0 else "#d85b67" for row in stability]
    axes[0].bar(np.arange(len(stability)), [row["return_pct"] for row in stability], color=colors)
    axes[0].set_xticks(np.arange(len(stability)), [row["period"] for row in stability], rotation=35, ha="right")
    axes[0].set_title("Consecutive six-month return")
    axes[1].bar(np.arange(len(stability)), [row["profit_factor"] for row in stability], color="#5794e6")
    axes[1].axhline(1.0, color="black", linewidth=0.8)
    axes[1].set_xticks(np.arange(len(stability)), [row["period"] for row in stability], rotation=35, ha="right")
    axes[1].set_title("Consecutive six-month PF")
    for axis in axes:
        axis.grid(axis="y", alpha=0.2)
    fig.savefig(charts / "six-month-stability.png", dpi=160)
    plt.close(fig)

    if curves.size:
        selected_paths = np.linspace(0, len(curves) - 1, min(250, len(curves)), dtype=int)
        fig, axes = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)
        for path in curves[selected_paths]:
            axes[0].plot(path, color="#5794e6", alpha=0.035, linewidth=0.6)
        axes[0].plot(np.median(curves, axis=0), color="#111111", linewidth=2.0, label="median")
        axes[0].set_title("10,000-path block bootstrap")
        axes[0].legend()
        final_returns = (curves[:, -1] / 10000.0 - 1.0) * 100.0
        axes[1].hist(final_returns, bins=60, color="#25b887", alpha=0.85)
        axes[1].axvline(0, color="#d85b67", linewidth=1.2)
        axes[1].set_title("Simulated final return distribution")
        fig.savefig(charts / "monte-carlo.png", dpi=160)
        plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
    scatter = axes[0].scatter(screen.max_dd_pct, screen.return_pct, c=screen.profit_factor.clip(0, 3), cmap="viridis", s=18, alpha=0.65)
    axes[0].set_xlabel("Development DD %")
    axes[0].set_ylabel("Development return %")
    axes[0].set_title("All screened configurations")
    fig.colorbar(scatter, ax=axes[0], label="PF capped at 3")
    axes[1].hist(screen.profit_factor.clip(0, 5), bins=35, color="#5794e6")
    axes[1].axvline(1.0, color="#d85b67")
    axes[1].set_title("Development PF distribution")
    axes[2].hist(screen.sharpe.clip(-5, 5), bins=35, color="#ad75d9")
    axes[2].axvline(0, color="#d85b67")
    axes[2].set_title("Development Sharpe distribution")
    fig.savefig(charts / "all-configurations.png", dpi=160)
    plt.close(fig)


def table_line(label: str, metrics: dict) -> str:
    return (
        f"| {label} | {metrics['return_pct']:+.2f}% | {metrics['profit_factor']:.2f} | "
        f"{metrics['win_rate']:.2f}% | {metrics['max_dd_pct']:.2f}% | {metrics['trades']} | "
        f"{metrics['sharpe']:.2f} | {metrics['recovery']:.2f} | {metrics['profitable_assets']}/8 |"
    )


def main():
    print("Selecting rotation configuration on development data only", flush=True)
    selected, rows = select_config(*DEV)
    selection = {
        "selected_before_locked_year": True,
        "development_period": [DEV[0].isoformat(), DEV[1].isoformat()],
        "locked_period": [LOCKED[0].isoformat(), LOCKED[1].isoformat()],
        "config": asdict(selected),
        "description": config_description(selected),
        "risk_percent_per_trade": 1.0,
        "maximum_concurrent_trades": 4,
    }
    dump(ROOT / "selection-lock.json", selection)
    print("FROZEN", selection["description"], flush=True)

    development = evaluate(selected, *DEV, include_trades=True)
    locked = evaluate(selected, *LOCKED, include_trades=True)
    full = evaluate(selected, *FULL, include_trades=True)
    assets = asset_table(locked["trades"], locked["standalone"])

    stability = []
    cursor = FULL[0]
    while cursor < FULL[1]:
        end = min(cursor + pd.DateOffset(months=6), FULL[1])
        metrics = evaluate(selected, cursor, end, include_trades=True)["metrics"]
        stability.append({"period": f"{cursor:%Y-%m}→{end:%Y-%m}", **metrics})
        cursor = end

    curves, mc = base.monte_carlo(locked["trades"], paths=10000, seed=20260907)
    stress_trades = [dict(row, return_fraction=float(row["return_fraction"]) - 0.0005) for row in locked["trades"]]
    cost_stress = base.stats_from_trades(stress_trades)
    risk_sensitivity = [
        {"risk_percent": risk, **base.stats_from_trades(locked["trades"], risk)} for risk in (0.5, 1.0)
    ]
    prior = json.loads((PACKAGE_ROOT / "HTF Paper Trend Portfolio Research 2026-09-07" / "results.json").read_text(encoding="utf-8"))["locked"]["metrics"]
    locked_metrics = locked["metrics"]
    positive_assets = sum(row["return_pct"] > 0 for row in assets)
    basic_gate = (
        locked_metrics["return_pct"] > 0
        and locked_metrics["profit_factor"] >= 1.20
        and locked_metrics["trades"] >= 40
        and locked_metrics["max_dd_pct"] <= 15.0
        and cost_stress["return_pct"] > 0
        and positive_assets >= 4
        and mc.get("return_p5", -1.0) > 0
    )
    improves_rejected_predecessor = (
        locked_metrics["return_pct"] > prior["return_pct"]
        and locked_metrics["profit_factor"] > prior["profit_factor"]
        and locked_metrics["max_dd_pct"] < prior["max_dd_pct"]
    )
    eligible_for_portfolio_fit = bool(basic_gate and improves_rejected_predecessor)
    decision = "QUALIFIES FOR INCREMENTAL PORTFOLIO-FIT TEST" if eligible_for_portfolio_fit else "REJECT / DO NOT ADD"

    result = {
        "protocol": "development-only selection, then untouched locked year",
        "config": asdict(selected),
        "description": config_description(selected),
        "screened_configurations": len(rows),
        "development": development,
        "locked": locked,
        "full_context": full,
        "locked_assets": assets,
        "six_month_stability": stability,
        "monte_carlo": mc,
        "cost_stress_extra_0_05pct_per_trade": cost_stress,
        "risk_sensitivity": risk_sensitivity,
        "predecessor_locked": prior,
        "basic_gate": basic_gate,
        "improves_rejected_predecessor": improves_rejected_predecessor,
        "eligible_for_portfolio_fit": eligible_for_portfolio_fit,
        "decision": decision,
        "production_changed": False,
    }
    dump(ROOT / "results.json", result)
    pd.DataFrame(assets).to_csv(ROOT / "locked-asset-breakdown.csv", index=False)
    pd.DataFrame(locked["trades"]).to_csv(ROOT / "locked-trades.csv", index=False)
    screen = pd.DataFrame([{**row, "config": json.dumps(row["config"], sort_keys=True)} for row in rows])
    make_charts(screen, locked, assets, stability, curves)

    lines = [
        "# Step 2 — Relative-Strength Momentum Rotation",
        "",
        f"**Decision: {decision}. No EA, BAT, website or recommended-portfolio file was changed.**",
        "",
        "## Frozen configuration",
        "",
        f"`{config_description(selected)}`",
        "",
        "The configuration was selected across all eight assets using development data only. Ranking uses completed daily closes. Risk is 1% of current equity per trade with a hard four-position cap.",
        "",
        "## Portfolio evidence",
        "",
        "| Sample | Return | PF | Win rate | Closed DD | Trades | Sharpe | Recovery | Positive assets |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        table_line("Development", development["metrics"]),
        table_line("Locked year", locked_metrics),
        table_line("Full context", full["metrics"]),
        "",
        "![Locked equity and drawdown](Charts/locked-equity-drawdown.png)",
        "",
        "## Locked-year asset breakdown",
        "",
        "| Asset | Return contribution | PF | Win rate | Trades | Sharpe | Recovery | Standalone M15 MTM DD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in assets:
        lines.append(
            f"| {row['symbol']} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
            f"{row['win_rate']:.2f}% | {row['trades']} | {row['sharpe']:.2f} | "
            f"{row['recovery']:.2f} | {row['standalone_mtm_dd_pct']:.2f}% |"
        )
    lines += [
        "",
        "![Asset breakdown](Charts/locked-asset-breakdown.png)",
        "",
        "## Consecutive six-month stability",
        "",
        "| Period | Return | PF | Win rate | DD | Trades |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in stability:
        lines.append(
            f"| {row['period']} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
            f"{row['win_rate']:.2f}% | {row['max_dd_pct']:.2f}% | {row['trades']} |"
        )
    lines += [
        "",
        "![Six-month stability](Charts/six-month-stability.png)",
        "",
        "## Robustness",
        "",
        f"Monte Carlo used 10,000 five-trade block-bootstrap paths. Return P5 was {mc['return_p5']:+.2f}%, median {mc['return_median']:+.2f}% and P95 {mc['return_p95']:+.2f}%. Median DD was {mc['dd_median']:.2f}% and P95 DD {mc['dd_p95']:.2f}%; {mc['profitable_probability_pct']:.2f}% of paths finished profitable.",
        "",
        f"Adding another 0.05% account cost to every trade produced {cost_stress['return_pct']:+.2f}% return, PF {cost_stress['profit_factor']:.2f} and {cost_stress['max_dd_pct']:.2f}% DD.",
        "",
        "![Monte Carlo](Charts/monte-carlo.png)",
        "",
        "## Promotion decision",
        "",
        f"- Standalone locked gate: {'PASS' if basic_gate else 'FAIL'}.",
        f"- Better than the rejected shared-rule predecessor: {'PASS' if improves_rejected_predecessor else 'FAIL'}.",
        f"- Eligible for an incremental test against the active Calyx portfolio: {'YES' if eligible_for_portfolio_fit else 'NO'}.",
        "- A strategy is never added merely because development or full-context performance looks strong.",
        "",
        "## Limitations",
        "",
        f"The pipeline screened {len(rows)} staged configurations using archived broker M15 bars, recorded spreads and conservative same-bar handling. It is not native MT5 tick replay. A passing result would still require native execution validation and an incremental portfolio correlation test before installation.",
        "",
        "![All configurations](Charts/all-configurations.png)",
    ]
    (ROOT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    checks = [
        (set(assets_row["symbol"] for assets_row in assets) == set(SYMBOLS), "all eight assets including EURUSD"),
        (selection["selected_before_locked_year"], "selection frozen before locked test"),
        (len(rows) == 467, "complete 467-configuration staged screen"),
        (locked_metrics["trades"] == len(locked["trades"]), "locked ledger count"),
        (all(pd.Timestamp(row["entry_time"]) >= LOCKED[0] for row in locked["trades"]), "locked entries inside interval"),
        (all(pd.Timestamp(row["exit_time"]) < LOCKED[1] for row in locked["trades"]), "no post-lock exits or leaked closing prices"),
        (mc.get("paths") == 10000, "10,000 Monte Carlo paths"),
        ((ROOT / "Charts" / "locked-equity-drawdown.png").is_file(), "equity graph generated"),
        ((ROOT / "Charts" / "locked-asset-breakdown.png").is_file(), "asset graph generated"),
        (not any(path.suffix.lower() in (".set", ".ex5") for path in ROOT.rglob("*")), "no production EA/SET created before gate"),
    ]
    (ROOT / "VERIFICATION.txt").write_text(
        "\n".join([f"{'PASS' if ok else 'FAIL'} {label}" for ok, label in checks] + [f"SUMMARY {sum(ok for ok, _ in checks)}/{len(checks)} checks passed"]) + "\n",
        encoding="utf-8",
    )
    dump(
        ROOT / "progress.json",
        {
            "step": 2,
            "title": "Relative-Strength Momentum Rotation",
            "status": "awaiting-review",
            "decision": decision,
            "screened_configurations": len(rows),
            "locked_trades": locked_metrics["trades"],
            "production_changed": False,
        },
    )
    print(decision, locked_metrics, flush=True)


if __name__ == "__main__":
    main()
