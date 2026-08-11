from __future__ import annotations

import json
import math
from dataclasses import asdict, is_dataclass
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "Data"
INITIAL_BALANCE = 10_000.0
RISK_FRACTION = 0.01


def json_safe(value):
    if is_dataclass(value):
        return json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not math.isfinite(float(value)) else float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def load_manifest() -> dict:
    return json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))


def load_history(label: str, start_year: int = 2022) -> tuple[pd.DataFrame, dict]:
    manifest = load_manifest()["instruments"][label]
    files = [DATA / item["file"] for item in manifest["files"] if int(item["file"].rsplit("-", 1)[-1].split(".")[0]) >= start_year]
    frames = [pd.read_csv(path, compression="gzip", parse_dates=["time"]) for path in files]
    frame = pd.concat(frames, ignore_index=True)
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    frame = frame.drop_duplicates("time", keep="last").sort_values("time").reset_index(drop=True)
    positive = frame.loc[frame["spread"] > 0, "spread"]
    fallback = float(positive.median()) if len(positive) else float(manifest["median_positive_spread_points"])
    frame.loc[frame["spread"] <= 0, "spread"] = fallback
    return frame, manifest


def interval(frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    # DatetimeIndex slicing is logarithmic; a full-frame boolean scan for every
    # session would turn a multi-year test into billions of comparisons.
    return frame.loc[start : end - pd.Timedelta(nanoseconds=1)]


def metrics(r_values) -> dict:
    r = np.asarray(list(r_values), dtype=float)
    r = r[np.isfinite(r)]
    if len(r) == 0:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "mean_r": 0.0,
            "net_r": 0.0,
            "return_pct": 0.0,
            "max_closed_balance_dd_pct": 0.0,
            "final_balance": INITIAL_BALANCE,
        }
    gains = float(r[r > 0].sum())
    losses = float(-r[r < 0].sum())
    equity = INITIAL_BALANCE * np.cumprod(1.0 + RISK_FRACTION * r)
    peak = np.maximum.accumulate(np.concatenate(([INITIAL_BALANCE], equity)))
    curve = np.concatenate(([INITIAL_BALANCE], equity))
    dd = (peak - curve) / peak
    return {
        "trades": int(len(r)),
        "wins": int((r > 0).sum()),
        "losses": int((r <= 0).sum()),
        "win_rate_pct": float((r > 0).mean() * 100.0),
        "profit_factor": float(gains / losses) if losses > 0 else (999.0 if gains > 0 else 0.0),
        "mean_r": float(r.mean()),
        "net_r": float(r.sum()),
        "return_pct": float((equity[-1] / INITIAL_BALANCE - 1.0) * 100.0),
        "max_closed_balance_dd_pct": float(dd.max() * 100.0),
        "final_balance": float(equity[-1]),
    }


def period_metrics(trades: pd.DataFrame, date_column: str = "date") -> dict:
    dates = pd.to_datetime(trades[date_column])
    masks = {
        "train_2022_2023": dates.dt.year <= 2023,
        "validation_2024": dates.dt.year == 2024,
        "holdout_2025_2026": dates.dt.year >= 2025,
        "full_2022_2026": np.ones(len(trades), dtype=bool),
    }
    return {name: metrics(trades.loc[mask, "result_r"]) for name, mask in masks.items()}


def selection_score(train: dict, validation: dict) -> float:
    if train["trades"] < 40 or validation["trades"] < 15:
        return -999.0
    if train["profit_factor"] <= 1.0 or validation["profit_factor"] <= 1.0:
        return -500.0 + min(train["mean_r"], validation["mean_r"])
    robustness = min(train["mean_r"], validation["mean_r"])
    dd_penalty = max(train["max_closed_balance_dd_pct"], validation["max_closed_balance_dd_pct"]) / 100.0
    return robustness - 0.15 * dd_penalty


def simulate_trade(
    path: pd.DataFrame,
    entry_index: int,
    direction: int,
    entry: float,
    stop_distance: float,
    reward_risk: float,
    management: str,
    no_progress_minutes: int = 0,
) -> tuple[float, str, float, pd.Timestamp]:
    if stop_distance <= 0 or entry_index >= len(path):
        return math.nan, "invalid", entry, path.index[min(entry_index, len(path) - 1)]
    initial_stop = entry - stop_distance if direction > 0 else entry + stop_distance
    stop = initial_stop
    target = entry + direction * reward_risk * stop_distance
    best_r = 0.0
    pending_stop = stop
    last_exit = entry
    last_time = path.index[entry_index]
    for offset in range(entry_index, len(path)):
        row = path.iloc[offset]
        spread = float(row["spread_price"])
        if direction > 0:
            bar_open = float(row.open)
            bar_high = float(row.high)
            bar_low = float(row.low)
            bar_close = float(row.close)
            if bar_low <= stop and bar_high >= target:
                return (stop - entry) / stop_distance, "stop_same_bar", stop, path.index[offset]
            if bar_low <= stop:
                return (stop - entry) / stop_distance, "stop", stop, path.index[offset]
            if bar_high >= target:
                return reward_risk, "target", target, path.index[offset]
            best_r = max(best_r, (bar_high - entry) / stop_distance)
            if management == "be_1r" and best_r >= 1.0:
                pending_stop = max(pending_stop, entry)
            elif management == "trail_1_5r" and best_r >= 1.5:
                pending_stop = max(pending_stop, bar_close - 0.75 * stop_distance, entry)
            last_exit = bar_close
        else:
            bar_open = float(row.open + spread)
            bar_high = float(row.high + spread)
            bar_low = float(row.low + spread)
            bar_close = float(row.close + spread)
            if bar_high >= stop and bar_low <= target:
                return (entry - stop) / stop_distance, "stop_same_bar", stop, path.index[offset]
            if bar_high >= stop:
                return (entry - stop) / stop_distance, "stop", stop, path.index[offset]
            if bar_low <= target:
                return reward_risk, "target", target, path.index[offset]
            best_r = max(best_r, (entry - bar_low) / stop_distance)
            if management == "be_1r" and best_r >= 1.0:
                pending_stop = min(pending_stop, entry)
            elif management == "trail_1_5r" and best_r >= 1.5:
                pending_stop = min(pending_stop, bar_close + 0.75 * stop_distance, entry)
            last_exit = bar_close
        stop = pending_stop
        last_time = path.index[offset]
        if no_progress_minutes > 0 and offset - entry_index + 1 >= no_progress_minutes and best_r < 0.5:
            result = direction * (last_exit - entry) / stop_distance
            return result, "no_progress", last_exit, last_time
    return direction * (last_exit - entry) / stop_distance, "time", last_exit, last_time


def add_spread_price(frame: pd.DataFrame, point: float) -> pd.DataFrame:
    result = frame.copy()
    result["spread_price"] = result["spread"].astype(float) * point
    return result
