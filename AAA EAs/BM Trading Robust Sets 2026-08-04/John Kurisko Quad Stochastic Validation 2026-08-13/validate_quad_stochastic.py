from __future__ import annotations

import itertools
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "Results"
RESULTS.mkdir(exist_ok=True)

BASE = ROOT.parent
APEX_DATA = BASE / "Apex Pulse and IVB Research 2026-08-10" / "Data"
BIAS_DATA = BASE / "Daily Bias AMD Validation 2026-08-10" / "Data"

TRAIN_START = pd.Timestamp("2022-01-01", tz="UTC")
TRAIN_END = pd.Timestamp("2024-12-31 23:59:59", tz="UTC")
HOLDOUT_START = pd.Timestamp("2025-01-01", tz="UTC")
HOLDOUT_END = pd.Timestamp("2026-08-10 23:59:59", tz="UTC")
INITIAL_BALANCE = 10_000.0
RISK_PCT = 0.01
MAX_NOTIONAL_LEVERAGE = 3.0
SLIPPAGE_SPREAD_FRACTION = 0.05


@dataclass(frozen=True)
class Instrument:
    name: str
    folder: Path
    pattern: str
    point: float
    tick_size: float
    tick_value: float
    contract_size: float
    min_volume: float
    volume_step: float


INSTRUMENTS = [
    Instrument("BTCUSD", BIAS_DATA, "MEXAtlantic-BTC-BTCUSD-M1-*.csv.gz", 0.01, 0.01, 0.01, 1.0, 0.01, 0.01),
    Instrument("XAUUSD", APEX_DATA, "MEXAtlantic-XAU-XAUUSD..-M1-*.csv.gz", 0.01, 0.01, 1.0, 100.0, 0.01, 0.01),
    Instrument("US100", APEX_DATA, "MEXAtlantic-US100-UT100-M1-*.csv.gz", 0.01, 0.01, 0.01, 1.0, 0.01, 0.01),
    Instrument("US30", APEX_DATA, "MEXAtlantic-US30-US30-M1-*.csv.gz", 0.01, 0.01, 0.01, 1.0, 0.1, 0.1),
    Instrument("EURUSD", APEX_DATA, "MEXAtlantic-EURUSD-EURUSD..-M1-*.csv.gz", 0.00001, 0.00001, 1.0, 100_000.0, 0.01, 0.01),
]


def load_data(inst: Instrument) -> pd.DataFrame:
    files = sorted(
        p for p in inst.folder.glob(inst.pattern)
        if any(p.name.endswith(f"-{year}.csv.gz") for year in [2022, 2023, 2024, 2025, 2026])
    )
    if not files:
        raise FileNotFoundError(f"No data for {inst.name}: {inst.folder / inst.pattern}")
    frames = []
    for path in files:
        frame = pd.read_csv(
            path,
            usecols=["time", "open", "high", "low", "close", "spread"],
            parse_dates=["time"],
        )
        frames.append(frame)
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    df = df[(df["time"] >= TRAIN_START) & (df["time"] <= HOLDOUT_END)].copy()
    for col in ["open", "high", "low", "close", "spread"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna().reset_index(drop=True)
    positive = df.loc[df["spread"] > 0, "spread"]
    median_spread_points = float(positive.median())
    spread_points = df["spread"].where(df["spread"] > 0, median_spread_points)
    spread_points = spread_points.clip(upper=median_spread_points * 5.0)
    df["spread_price"] = (spread_points * inst.point).astype("float32")
    return df


def fast_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int, d_period: int) -> pd.Series:
    highest = high.rolling(k_period, min_periods=k_period).max()
    lowest = low.rolling(k_period, min_periods=k_period).min()
    span = highest - lowest
    raw = 100.0 * (close - lowest) / span.where(span > 0)
    raw = raw.fillna(50.0)
    return raw.rolling(d_period, min_periods=d_period).mean().astype("float32")


def confirmed_pivots(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    valid = np.isfinite(values[:-2]) & np.isfinite(values[1:-1]) & np.isfinite(values[2:])
    trough = np.flatnonzero(valid & (values[1:-1] <= values[:-2]) & (values[1:-1] < values[2:])) + 1
    peak = np.flatnonzero(valid & (values[1:-1] >= values[:-2]) & (values[1:-1] > values[2:])) + 1
    return trough.astype(np.int32), peak.astype(np.int32)


def last_true_position(mask: np.ndarray) -> np.ndarray:
    positions = np.where(mask, np.arange(len(mask), dtype=np.int32), -1)
    return np.maximum.accumulate(positions)


def build_pair_table(
    pivots: np.ndarray,
    direction: int,
    s9: np.ndarray,
    body_low: np.ndarray,
    body_high: np.ndarray,
    low: np.ndarray,
    high: np.ndarray,
    atr: np.ndarray,
    last_quad: np.ndarray,
    max_lookback: int = 24,
) -> pd.DataFrame:
    rows: list[tuple] = []
    recent: list[int] = []
    for p_raw in pivots:
        p = int(p_raw)
        recent = [q for q in recent if p - q <= max_lookback]
        if p + 1 >= len(s9) or not np.isfinite(atr[p]) or atr[p] <= 0:
            recent.append(p)
            continue
        for q in reversed(recent):
            if direction == 1:
                first_ok = s9[q] < 25.0
                osc_delta = float(s9[p] - s9[q])
                break_atr = float((body_low[q] - body_low[p]) / atr[p])
                stop_base = float(np.min(low[q : p + 2]))
            else:
                first_ok = s9[q] > 75.0
                osc_delta = float(s9[q] - s9[p])
                break_atr = float((body_high[p] - body_high[q]) / atr[p])
                stop_base = float(np.max(high[q : p + 2]))
            if not first_ok or osc_delta < 0.5:
                continue
            if break_atr < -0.35 or break_atr > 1.5:
                continue
            if last_quad[p] < q - 5:
                continue
            rows.append((p + 1, q, p - q, direction, float(s9[q]), float(s9[p]), osc_delta, break_atr, stop_base))
        recent.append(p)
    return pd.DataFrame(
        rows,
        columns=["signal", "prior_pivot", "distance", "direction", "first_osc", "second_osc", "osc_delta", "break_atr", "stop_base"],
    )


def prepare_features(df: pd.DataFrame) -> dict:
    high_s, low_s, close_s = df["high"], df["low"], df["close"]
    s9 = fast_stochastic(high_s, low_s, close_s, 9, 3).to_numpy(dtype=np.float32)
    s14 = fast_stochastic(high_s, low_s, close_s, 14, 3).to_numpy(dtype=np.float32)
    s44 = fast_stochastic(high_s, low_s, close_s, 44, 1).to_numpy(dtype=np.float32)
    s60 = fast_stochastic(high_s, low_s, close_s, 60, 10).to_numpy(dtype=np.float32)
    prev_close = close_s.shift(1)
    true_range = pd.concat(
        [(high_s - low_s), (high_s - prev_close).abs(), (low_s - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    atr = true_range.rolling(14, min_periods=14).mean().to_numpy(dtype=np.float32)
    ema20 = close_s.ewm(span=20, adjust=False).mean().to_numpy(dtype=np.float32)
    ema50 = close_s.ewm(span=50, adjust=False).mean().to_numpy(dtype=np.float32)
    open_a = df["open"].to_numpy(dtype=np.float64)
    high_a = df["high"].to_numpy(dtype=np.float64)
    low_a = df["low"].to_numpy(dtype=np.float64)
    close_a = df["close"].to_numpy(dtype=np.float64)
    body_low = np.minimum(open_a, close_a)
    body_high = np.maximum(open_a, close_a)
    troughs, peaks = confirmed_pivots(s9)
    quad_long = (s9 < 20) & (s14 < 20) & (s44 < 20) & (s60 < 20)
    quad_short = (s9 > 80) & (s14 > 80) & (s44 > 80) & (s60 > 80)
    pair_long = build_pair_table(
        troughs, 1, s9, body_low, body_high, low_a, high_a, atr, last_true_position(quad_long)
    )
    pair_short = build_pair_table(
        peaks, -1, s9, body_low, body_high, low_a, high_a, atr, last_true_position(quad_short)
    )
    return {
        "time": df["time"].dt.as_unit("ns").astype("int64").to_numpy(dtype=np.int64),
        "open": open_a,
        "high": high_a,
        "low": low_a,
        "close": close_a,
        "spread": df["spread_price"].to_numpy(dtype=np.float64),
        "s9": s9,
        "s14": s14,
        "s44": s44,
        "s60": s60,
        "atr": atr,
        "ema20": ema20,
        "ema50": ema50,
        "troughs": troughs,
        "peaks": peaks,
        "pair_long": pair_long,
        "pair_short": pair_short,
        "pull_low": low_s.rolling(5, min_periods=1).min().to_numpy(dtype=np.float64),
        "pull_high": high_s.rolling(5, min_periods=1).max().to_numpy(dtype=np.float64),
    }


def reversal_events(f: dict, cfg: dict) -> pd.DataFrame:
    selected = []
    for direction, pairs in [(1, f["pair_long"]), (-1, f["pair_short"])]:
        if pairs.empty:
            continue
        if direction == 1:
            hold_ok = pairs["second_osc"] >= cfg["second_hold"]
        else:
            hold_ok = pairs["second_osc"] <= 100.0 - cfg["second_hold"]
        subset = pairs[
            (pairs["distance"] <= cfg["div_lookback"])
            & hold_ok
            & (pairs["osc_delta"] >= cfg["div_delta"])
            & (pairs["break_atr"] >= -cfg["price_tolerance_atr"])
            & (pairs["break_atr"] <= cfg["max_break_atr"])
        ].copy()
        if subset.empty:
            continue
        subset = subset.sort_values(["signal", "prior_pivot"], ascending=[True, False])
        subset = subset.drop_duplicates("signal", keep="first")
        selected.append(subset[["signal", "direction", "stop_base"]])
    if not selected:
        return pd.DataFrame(columns=["signal", "direction", "stop_base"])
    events = pd.concat(selected, ignore_index=True).sort_values("signal")
    return events.drop_duplicates("signal", keep="first").reset_index(drop=True)


def flag_events(f: dict, cfg: dict) -> pd.DataFrame:
    s9, s60 = f["s9"], f["s60"]
    ema = f["ema20"] if cfg["ema_period"] == 20 else f["ema50"]
    rows = []
    for direction, pivots in [(1, f["troughs"]), (-1, f["peaks"])]:
        if direction == 1:
            embedded = s60 >= cfg["trend_level"]
        else:
            embedded = s60 <= 100.0 - cfg["trend_level"]
        segment = np.cumsum(embedded != np.r_[False, embedded[:-1]])
        for p_raw in pivots:
            p = int(p_raw)
            signal = p + 1
            if signal >= len(s9) - 1 or not embedded[p] or not np.isfinite(f["atr"][signal]):
                continue
            if direction == 1:
                ok = s9[p] <= cfg["touch_level"] and s9[signal] > s9[p] and f["close"][signal] > ema[signal]
                stop = f["pull_low"][signal]
            else:
                ok = s9[p] >= 100.0 - cfg["touch_level"] and s9[signal] < s9[p] and f["close"][signal] < ema[signal]
                stop = f["pull_high"][signal]
            if ok:
                rows.append((signal, direction, float(stop), int(segment[p])))
    if not rows:
        return pd.DataFrame(columns=["signal", "direction", "stop_base"])
    events = pd.DataFrame(rows, columns=["signal", "direction", "stop_base", "segment"])
    events = events.sort_values("signal")
    events["rank"] = events.groupby(["direction", "segment"]).cumcount() + 1
    events = events[events["rank"] <= 2]
    return events[["signal", "direction", "stop_base"]].reset_index(drop=True)


def round_volume(raw: float, inst: Instrument) -> float:
    if raw < inst.min_volume:
        return 0.0
    steps = math.floor((raw + 1e-12) / inst.volume_step)
    volume = steps * inst.volume_step
    return round(volume, 8) if volume >= inst.min_volume else 0.0


def backtest(
    f: dict,
    events: pd.DataFrame,
    cfg: dict,
    inst: Instrument,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    times = f["time"]
    start_ns = int(start.value)
    end_ns = int(end.value)
    five_minutes_ns = 5 * 60 * 1_000_000_000
    fifteen_minutes_ns = 15 * 60 * 1_000_000_000
    equity = INITIAL_BALANCE
    peak = equity
    max_dd = 0.0
    last_exit = -1
    trades = []
    curve = [(pd.Timestamp(start), equity)]
    unit_value = inst.tick_value / inst.tick_size
    n = len(times)
    max_hold = int(cfg["max_hold"])
    buffer_atr = float(cfg["stop_buffer_atr"])

    for row in events.itertuples(index=False):
        signal = int(row.signal)
        entry_idx = signal + 1
        if entry_idx >= n - 1 or entry_idx <= last_exit:
            continue
        entry_time_ns = int(times[entry_idx])
        if entry_time_ns < start_ns or entry_time_ns > end_ns:
            continue
        if (entry_time_ns - int(times[signal])) > five_minutes_ns:
            continue
        direction = int(row.direction)
        atr_now = float(f["atr"][signal])
        if not np.isfinite(atr_now) or atr_now <= 0:
            continue
        spread_entry = float(f["spread"][entry_idx])
        slip_entry = spread_entry * SLIPPAGE_SPREAD_FRACTION
        if direction == 1:
            entry = float(f["open"][entry_idx] + spread_entry + slip_entry)
            stop = float(row.stop_base - buffer_atr * atr_now)
            if stop >= entry - 0.10 * atr_now:
                continue
            stop_fill = stop - spread_entry * SLIPPAGE_SPREAD_FRACTION
            risk_price = entry - stop_fill
        else:
            entry = float(f["open"][entry_idx] - slip_entry)
            stop = float(row.stop_base + buffer_atr * atr_now + spread_entry)
            if stop <= entry + 0.10 * atr_now:
                continue
            stop_fill = stop + spread_entry * SLIPPAGE_SPREAD_FRACTION
            risk_price = stop_fill - entry
        if risk_price <= 0:
            continue
        risk_budget = equity * RISK_PCT
        raw_volume = risk_budget / (risk_price * unit_value)
        notional_per_lot = max(1e-12, inst.contract_size * entry)
        raw_volume = min(raw_volume, equity * MAX_NOTIONAL_LEVERAGE / notional_per_lot)
        volume = round_volume(raw_volume, inst)
        if volume <= 0:
            continue

        exit_idx = None
        exit_price = None
        reason = None
        ideal_exit = None
        horizon = min(n - 2, entry_idx + max_hold - 1)
        for j in range(entry_idx, horizon + 1):
            if j > entry_idx and (int(times[j]) - int(times[j - 1])) > fifteen_minutes_ns:
                spr = float(f["spread"][j])
                slip = spr * SLIPPAGE_SPREAD_FRACTION
                exit_idx = j
                exit_price = float(f["open"][j] - slip) if direction == 1 else float(f["open"][j] + spr + slip)
                ideal_exit = float(f["open"][j])
                reason = "gap"
                break

            spr = float(f["spread"][j])
            slip = spr * SLIPPAGE_SPREAD_FRACTION
            if direction == 1:
                stopped = f["low"][j] <= stop
                close_fill = f["close"][j] - slip
                adverse_fill = f["low"][j] - slip
            else:
                stopped = f["high"][j] + spr >= stop
                close_fill = f["close"][j] + spr + slip
                adverse_fill = f["high"][j] + spr + slip
            mtm_close = equity + direction * (close_fill - entry) * unit_value * volume
            peak = max(peak, mtm_close)
            adverse_equity = equity + direction * (adverse_fill - entry) * unit_value * volume
            max_dd = max(max_dd, (peak - adverse_equity) / peak * 100.0 if peak > 0 else 0.0)

            if stopped:
                exit_idx = j
                if direction == 1:
                    exit_price = float(min(stop, f["open"][j]) - slip)
                else:
                    exit_price = float(max(stop, f["open"][j] + spr) + slip)
                ideal_exit = float(stop)
                reason = "stop"
                break

            oscillator_exit = (direction == 1 and f["s9"][j] >= 80.0) or (direction == -1 and f["s9"][j] <= 20.0)
            time_exit = j >= horizon
            if oscillator_exit or time_exit:
                k = j + 1
                spr2 = float(f["spread"][k])
                slip2 = spr2 * SLIPPAGE_SPREAD_FRACTION
                exit_idx = k
                exit_price = float(f["open"][k] - slip2) if direction == 1 else float(f["open"][k] + spr2 + slip2)
                ideal_exit = float(f["open"][k])
                reason = "rotation" if oscillator_exit else "time"
                break

        if exit_idx is None or exit_price is None:
            continue
        pnl = direction * (exit_price - entry) * unit_value * volume
        ideal_pnl = direction * (ideal_exit - f["open"][entry_idx]) * unit_value * volume
        execution_cost = max(0.0, ideal_pnl - pnl)
        equity_before = equity
        equity += pnl
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak * 100.0 if peak > 0 else 0.0)
        last_exit = int(exit_idx)
        trade = {
            "entry_time": pd.Timestamp(int(times[entry_idx]), unit="ns", tz="UTC"),
            "exit_time": pd.Timestamp(int(times[exit_idx]), unit="ns", tz="UTC"),
            "direction": "long" if direction == 1 else "short",
            "entry": entry,
            "stop": stop,
            "exit": exit_price,
            "volume": volume,
            "pnl": pnl,
            "return_on_equity_pct": pnl / equity_before * 100.0,
            "reason": reason,
            "bars": int(exit_idx - entry_idx + 1),
            "execution_cost": execution_cost,
        }
        trades.append(trade)
        curve.append((pd.Timestamp(int(times[exit_idx]), unit="ns", tz="UTC"), equity))

    trade_df = pd.DataFrame(trades)
    curve_df = pd.DataFrame(curve, columns=["time", "equity"]).drop_duplicates("time", keep="last")
    if trade_df.empty:
        stats = {
            "initial": INITIAL_BALANCE, "final": INITIAL_BALANCE, "net": 0.0, "return_pct": 0.0,
            "annualized_return_pct": 0.0, "profit_factor": 0.0, "win_rate_pct": 0.0,
            "trades": 0, "wins": 0, "losses": 0, "max_equity_drawdown_pct": 0.0,
            "average_trade": 0.0, "largest_win": 0.0, "largest_loss": 0.0,
            "execution_cost": 0.0,
        }
    else:
        wins = trade_df[trade_df.pnl > 0]
        losses = trade_df[trade_df.pnl <= 0]
        gross_profit = float(wins.pnl.sum())
        gross_loss = float(-losses.pnl.sum())
        years = max(1 / 365.25, (pd.Timestamp(end) - pd.Timestamp(start)).total_seconds() / (365.25 * 86400))
        annualized = ((equity / INITIAL_BALANCE) ** (1 / years) - 1) * 100 if equity > 0 else -100.0
        stats = {
            "initial": INITIAL_BALANCE,
            "final": equity,
            "net": equity - INITIAL_BALANCE,
            "return_pct": (equity / INITIAL_BALANCE - 1) * 100.0,
            "annualized_return_pct": annualized,
            "profit_factor": gross_profit / gross_loss if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0),
            "win_rate_pct": len(wins) / len(trade_df) * 100.0,
            "trades": int(len(trade_df)),
            "wins": int(len(wins)),
            "losses": int(len(losses)),
            "max_equity_drawdown_pct": max_dd,
            "average_trade": float(trade_df.pnl.mean()),
            "largest_win": float(trade_df.pnl.max()),
            "largest_loss": float(trade_df.pnl.min()),
            "execution_cost": float(trade_df.execution_cost.sum()),
        }
    return stats, trade_df, curve_df


def config_key(cfg: dict) -> str:
    return json.dumps(cfg, sort_keys=True, separators=(",", ":"))


def make_configs() -> tuple[list[dict], list[dict]]:
    reversal_literal = {
        "model": "reversal", "div_lookback": 20, "second_hold": 20.0, "div_delta": 3.0,
        "price_tolerance_atr": 0.15, "max_break_atr": 1.0, "stop_buffer_atr": 0.10, "max_hold": 20,
    }
    reversal = [reversal_literal]
    for values in itertools.product([12, 20], [10.0, 20.0], [2.0, 5.0], [0.5, 1.0]):
        div_lookback, second_hold, div_delta, max_break = values
        reversal.append({
            "model": "reversal", "div_lookback": div_lookback, "second_hold": second_hold,
            "div_delta": div_delta, "price_tolerance_atr": 0.15, "max_break_atr": max_break,
            "stop_buffer_atr": 0.10, "max_hold": 20,
        })
    flag_literal = {
        "model": "flag", "trend_level": 85.0, "touch_level": 20.0, "ema_period": 20,
        "stop_buffer_atr": 0.10, "max_hold": 20,
    }
    flag = [flag_literal]
    for values in itertools.product([80.0, 85.0, 90.0], [20.0, 25.0], [20, 50]):
        trend, touch, ema_period = values
        flag.append({
            "model": "flag", "trend_level": trend, "touch_level": touch, "ema_period": ema_period,
            "stop_buffer_atr": 0.10, "max_hold": 20,
        })
    def unique(items: list[dict]) -> list[dict]:
        seen, out = set(), []
        for item in items:
            key = config_key(item)
            if key not in seen:
                seen.add(key)
                out.append(item)
        return out
    return unique(reversal), unique(flag)


def event_factory(f: dict, cfg: dict) -> pd.DataFrame:
    return reversal_events(f, cfg) if cfg["model"] == "reversal" else flag_events(f, cfg)


def select_training_configs(training_df: pd.DataFrame, configs: dict[str, dict]) -> dict:
    rows = []
    for (model, cfg_id), group in training_df.groupby(["model", "config_id"]):
        positive = int((group.return_pct > 0).sum())
        total_trades = int(group.trades.sum())
        median_pf = float(group.profit_factor.replace(999.0, np.nan).median())
        if not np.isfinite(median_pf):
            median_pf = 10.0
        median_return = float(group.return_pct.median())
        worst_dd = float(group.max_equity_drawdown_pct.max())
        score = median_return - 0.35 * worst_dd + 3.0 * (positive - 2.5) + math.log1p(total_trades)
        passed = positive >= 3 and median_pf >= 1.05 and total_trades >= 250 and worst_dd <= 35.0
        rows.append({
            "model": model, "config_id": cfg_id, "median_return_pct": median_return,
            "median_profit_factor": median_pf, "positive_instruments": positive,
            "total_trades": total_trades, "worst_drawdown_pct": worst_dd,
            "score": score, "passed_training_gate": passed,
        })
    ranking = pd.DataFrame(rows).sort_values(["model", "passed_training_gate", "score"], ascending=[True, False, False])
    selected = {}
    for model in ["reversal", "flag"]:
        model_rank = ranking[ranking.model == model]
        passed = model_rank[model_rank.passed_training_gate]
        choice = passed.iloc[0] if not passed.empty else model_rank.iloc[0]
        selected[model] = {
            "config_id": choice.config_id,
            "parameters": configs[choice.config_id],
            "training_gate_passed": bool(choice.passed_training_gate),
            "training_summary": choice.to_dict(),
        }
    ranking.to_csv(RESULTS / "training-ranking.csv", index=False)
    return selected


def combine_curves(curves: dict[str, pd.DataFrame], start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    index = pd.date_range(start.normalize(), end.normalize(), freq="1D", tz="UTC")
    total = pd.Series(0.0, index=index)
    for curve in curves.values():
        c = curve.copy().set_index("time")["equity"].sort_index()
        c = c[~c.index.duplicated(keep="last")]
        c = c.reindex(index.union(c.index)).sort_index().ffill().reindex(index).ffill().fillna(INITIAL_BALANCE)
        total = total.add(c, fill_value=0.0)
    return pd.DataFrame({"time": index, "equity": total.values})


def portfolio_stats(curve: pd.DataFrame, trades: pd.DataFrame, instruments: int) -> dict:
    initial = INITIAL_BALANCE * instruments
    final = float(curve.equity.iloc[-1])
    running_max = curve.equity.cummax()
    dd = ((running_max - curve.equity) / running_max * 100.0).max()
    if trades.empty:
        return {"initial": initial, "final": final, "return_pct": 0.0, "profit_factor": 0.0, "win_rate_pct": 0.0, "trades": 0, "max_equity_drawdown_pct": float(dd)}
    wins = trades[trades.pnl > 0]
    losses = trades[trades.pnl <= 0]
    gp, gl = float(wins.pnl.sum()), float(-losses.pnl.sum())
    return {
        "initial": initial, "final": final, "return_pct": (final / initial - 1) * 100.0,
        "profit_factor": gp / gl if gl > 0 else 999.0,
        "win_rate_pct": len(wins) / len(trades) * 100.0, "trades": int(len(trades)),
        "max_equity_drawdown_pct": float(dd), "execution_cost": float(trades.execution_cost.sum()),
    }


def plot_holdout(portfolio_curves: dict[str, pd.DataFrame], best_label: str, best_instrument_curves: dict[str, pd.DataFrame]) -> None:
    plt.style.use("seaborn-v0_8-darkgrid")
    fig, axes = plt.subplots(2, 1, figsize=(13, 9), constrained_layout=True)
    for label, curve in portfolio_curves.items():
        axes[0].plot(curve.time, curve.equity, label=label, linewidth=1.8)
    axes[0].axhline(INITIAL_BALANCE * len(INSTRUMENTS), color="black", linewidth=1, linestyle="--", alpha=0.6)
    axes[0].set_title("Untouched 2025–2026 equal-weight portfolio equity")
    axes[0].set_ylabel("Portfolio equity (USD)")
    axes[0].legend(loc="best")
    for inst, curve in best_instrument_curves.items():
        axes[1].plot(curve.time, curve.equity, label=inst, linewidth=1.35)
    axes[1].axhline(INITIAL_BALANCE, color="black", linewidth=1, linestyle="--", alpha=0.6)
    axes[1].set_title(f"{best_label}: instrument equity")
    axes[1].set_ylabel("Equity from $10,000")
    axes[1].set_xlabel("Date (UTC)")
    axes[1].legend(loc="best", ncol=3)
    fig.savefig(RESULTS / "holdout-equity.png", dpi=170)
    plt.close(fig)


def main() -> None:
    reversal_configs, flag_configs = make_configs()
    all_configs = reversal_configs + flag_configs
    config_map = {config_key(c): c for c in all_configs}
    literal_ids = {
        "Literal super signal": config_key(reversal_configs[0]),
        "Literal continuation flag": config_key(flag_configs[0]),
    }

    training_rows = []
    data_manifest = {}
    print(f"Training {len(reversal_configs)} reversal and {len(flag_configs)} flag configurations")
    for inst in INSTRUMENTS:
        print(f"Loading training features: {inst.name}", flush=True)
        df = load_data(inst)
        data_manifest[inst.name] = {
            "rows": int(len(df)), "first": str(df.time.iloc[0]), "last": str(df.time.iloc[-1]),
            "median_spread_price": float(df.spread_price.median()),
        }
        features = prepare_features(df)
        for cfg in all_configs:
            cfg_id = config_key(cfg)
            events = event_factory(features, cfg)
            stats, _, _ = backtest(features, events, cfg, inst, TRAIN_START, TRAIN_END)
            training_rows.append({"instrument": inst.name, "model": cfg["model"], "config_id": cfg_id, **stats})
        del features, df
    training_df = pd.DataFrame(training_rows)
    training_df.to_csv(RESULTS / "training-by-instrument.csv", index=False)
    selected = select_training_configs(training_df, config_map)
    (RESULTS / "frozen-configs.json").write_text(json.dumps(selected, indent=2, default=str), encoding="utf-8")

    variants = dict(literal_ids)
    variants["Frozen reversal"] = selected["reversal"]["config_id"]
    variants["Frozen continuation"] = selected["flag"]["config_id"]
    variants = dict(dict.fromkeys((f"{label}||{cfg_id}" for label, cfg_id in variants.items())))
    variant_pairs = [(item.split("||", 1)[0], item.split("||", 1)[1]) for item in variants]

    holdout_rows = []
    portfolio_curves = {}
    portfolio_trades = {}
    instrument_curves_by_variant = {}
    for inst in INSTRUMENTS:
        print(f"Running untouched holdout: {inst.name}", flush=True)
        df = load_data(inst)
        features = prepare_features(df)
        for label, cfg_id in variant_pairs:
            cfg = config_map[cfg_id]
            events = event_factory(features, cfg)
            stats, trades, curve = backtest(features, events, cfg, inst, HOLDOUT_START, HOLDOUT_END)
            holdout_rows.append({"variant": label, "instrument": inst.name, "model": cfg["model"], **stats})
            safe = label.lower().replace(" ", "-")
            trades.to_csv(RESULTS / f"{safe}-{inst.name.lower()}-trades.csv", index=False)
            curve.to_csv(RESULTS / f"{safe}-{inst.name.lower()}-equity.csv", index=False)
            portfolio_curves.setdefault(label, {})[inst.name] = curve
            if not trades.empty:
                t = trades.copy()
                t["instrument"] = inst.name
                portfolio_trades.setdefault(label, []).append(t)
            instrument_curves_by_variant.setdefault(label, {})[inst.name] = curve
        del features, df

    holdout_df = pd.DataFrame(holdout_rows)
    holdout_df.to_csv(RESULTS / "holdout-by-instrument.csv", index=False)
    portfolio_rows = []
    combined = {}
    for label, curves in portfolio_curves.items():
        combined_curve = combine_curves(curves, HOLDOUT_START, HOLDOUT_END)
        combined[label] = combined_curve
        combined_curve.to_csv(RESULTS / f"{label.lower().replace(' ', '-')}-portfolio-equity.csv", index=False)
        trades = pd.concat(portfolio_trades.get(label, []), ignore_index=True) if portfolio_trades.get(label) else pd.DataFrame()
        pstats = portfolio_stats(combined_curve, trades, len(INSTRUMENTS))
        portfolio_rows.append({"variant": label, "instrument": "PORTFOLIO", **pstats})
    portfolio_df = pd.DataFrame(portfolio_rows)
    portfolio_df.to_csv(RESULTS / "holdout-portfolio-summary.csv", index=False)

    frozen_labels = [label for label, _ in variant_pairs if label.startswith("Frozen")]
    training_choice = max(
        frozen_labels,
        key=lambda label: float(selected["reversal" if "reversal" in label.lower() else "flag"]["training_summary"]["score"]),
    )
    plot_holdout(combined, training_choice, instrument_curves_by_variant[training_choice])

    output = {
        "source_video": "https://www.youtube.com/watch?v=PpysVy2NNQ4",
        "test_design": {
            "training": [str(TRAIN_START), str(TRAIN_END)],
            "untouched_holdout": [str(HOLDOUT_START), str(HOLDOUT_END)],
            "initial_balance_per_instrument": INITIAL_BALANCE,
            "risk_per_trade_pct": RISK_PCT * 100.0,
            "max_notional_leverage": MAX_NOTIONAL_LEVERAGE,
            "execution": "recorded spread plus 5% of spread slippage on each fill; next-bar entries/exits",
            "news_filter": "not applied; no reliable machine-readable historical calendar in the supplied broker data",
        },
        "data_manifest": data_manifest,
        "selected": selected,
        "holdout_portfolios": portfolio_rows,
        "holdout_instruments": holdout_rows,
        "best_training_frozen_label": training_choice,
    }
    (RESULTS / "final-results.json").write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print("Done")
    print(portfolio_df.to_string(index=False))


if __name__ == "__main__":
    main()
