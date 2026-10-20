"""Causal, bounded DEVELOPMENT search for a long Bitcoin weekend hypothesis.

This is an M5-OHLC search surrogate, not a native tick-fill simulator. Importing
the module performs no I/O. No account, terminal, subprocess or network APIs.
The root driver must approve source coverage, then call run_development().
OOS evaluation requires a persisted, hash-verified final-configuration freeze.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace
from datetime import datetime, time, timedelta, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np


UTC = timezone.utc
NY = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parent
ATR_BANDS = {0: (10.0, 90.0), 1: (20.0, 80.0), 2: (20.0, 95.0), 3: (30.0, 90.0)}
RR_VALUES = (0, 0.5, 0.75, 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6)
ATR_VALUES = (0.5, 0.75, 1, 1.5, 2, 3, 4)
PERCENT_VALUES = (0.5, 1, 1.5, 2, 3, 5)
TIMEFRAMES = (1, 3, 5, 15, 30, 60, 240, 1440)


@dataclass(frozen=True)
class Configuration:
    timeframe_minutes: int = 5
    entry_mode: int = 0
    stop_mode: int = 0
    stop_value: float = 0
    target_rr: float = 0
    management_mode: int = 0
    management_value: float = 0
    filter_mode: int = 0
    filter_value: float = 0
    entry_minute_ny: int = 1020
    exit_minute_ny: int = 1020


def canonical(config: Configuration | dict) -> Configuration:
    value = config if isinstance(config, Configuration) else Configuration(**config)
    integral = ("timeframe_minutes", "entry_mode", "stop_mode", "management_mode", "filter_mode", "entry_minute_ny", "exit_minute_ny")
    for name in integral:
        number = getattr(value, name)
        if isinstance(number, bool) or not math.isfinite(float(number)) or int(number) != number:
            raise ValueError("Integral configuration field required: " + name)
    value = replace(value, **{name: int(getattr(value, name)) for name in integral}, **{name: float(getattr(value, name)) for name in ("stop_value", "target_rr", "management_value", "filter_value")})
    if value.timeframe_minutes not in TIMEFRAMES:
        raise ValueError("Unregistered timeframe")
    if value.entry_mode not in (0, 1, 2) or value.stop_mode not in (0, 1, 2, 3):
        raise ValueError("Unknown entry or stop mode")
    if value.management_mode not in range(6) or value.filter_mode not in range(8):
        raise ValueError("Unknown management or filter")
    if not 0 <= value.entry_minute_ny < 1440 or not 0 <= value.exit_minute_ny < 1440:
        raise ValueError("Invalid New York wall-clock minute")
    if any(not math.isfinite(float(getattr(value, name))) for name in ("stop_value", "target_rr", "management_value", "filter_value")):
        raise ValueError("Nonfinite configuration")
    changes = {}
    if value.stop_mode == 0:
        changes.update(stop_value=0.0, target_rr=0.0, management_mode=0, management_value=0.0)
    elif value.stop_mode == 3:
        changes["stop_value"] = 0.0
    elif value.stop_value <= 0:
        raise ValueError("Positive stop multiplier required")
    if value.target_rr < 0:
        raise ValueError("Target R must be nonnegative")
    if value.management_mode in (0, 5):
        changes["management_value"] = 0.0
    elif value.stop_mode and value.management_value <= 0:
        raise ValueError("Positive management setting required")
    if value.filter_mode in range(6):
        changes["filter_value"] = 0.0
    elif value.filter_mode == 6 and value.filter_value not in ATR_BANDS:
        raise ValueError("Unknown ATR percentile band")
    elif value.filter_mode == 7 and value.filter_value <= 0:
        raise ValueError("Positive percent spread cap required")
    value = replace(value, **changes)
    # Clock-only and fixed-percent-stop-only systems do not use the signal TF.
    if value.entry_mode == 0 and value.stop_mode in (0, 2) and value.management_mode == 0 and value.filter_mode in (0, 7):
        value = replace(value, timeframe_minutes=5)
    return value


BASELINE = asdict(Configuration())


def default_config() -> dict:
    return dict(BASELINE)


def config_id(config: Configuration | dict) -> str:
    body = json.dumps(asdict(canonical(config)), sort_keys=True, separators=(",", ":"))
    return sha256(body.encode()).hexdigest()[:16]


def timestamp(value: int | str | datetime) -> int:
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return int(value.timestamp())


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def sma(values: np.ndarray, length: int) -> np.ndarray:
    result = np.full(len(values), np.nan)
    if len(values) >= length:
        sums = np.cumsum(np.r_[0.0, np.asarray(values, dtype=float)])
        result[length - 1:] = (sums[length:] - sums[:-length]) / length
    return result


def ema(values: np.ndarray, length: int) -> np.ndarray:
    result = np.full(len(values), np.nan)
    if not len(values):
        return result
    state = float(values[0])
    alpha = 2 / (length + 1)
    for index, close in enumerate(values):
        state = state if index == 0 else alpha * float(close) + (1 - alpha) * state
        if index >= length - 1:
            result[index] = state
    return result


def true_range(bars: np.ndarray) -> np.ndarray:
    if not len(bars):
        return np.array([], dtype=float)
    previous = np.r_[bars["close"][0], bars["close"][:-1]]
    return np.maximum(bars["high"] - bars["low"], np.maximum(abs(bars["high"] - previous), abs(bars["low"] - previous)))


def wilder_adx(bars: np.ndarray, length: int = 14) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    count = len(bars)
    adx, plus, minus = (np.full(count, np.nan) for _ in range(3))
    if count < length:
        return adx, plus, minus
    tr = true_range(bars)
    up = np.r_[0.0, np.diff(bars["high"])]
    down = np.r_[0.0, -np.diff(bars["low"])]
    dm_plus = np.where((up > down) & (up > 0), up, 0.0)
    dm_minus = np.where((down > up) & (down > 0), down, 0.0)
    total, positive, negative = float(tr[:length].sum()), float(dm_plus[:length].sum()), float(dm_minus[:length].sum())
    for index in range(length - 1, count):
        if index >= length:
            total = total - total / length + float(tr[index])
            positive = positive - positive / length + float(dm_plus[index])
            negative = negative - negative / length + float(dm_minus[index])
        plus[index] = 100 * positive / total if total > 0 else 0
        minus[index] = 100 * negative / total if total > 0 else 0
    denominator = plus + minus
    dx = np.divide(abs(plus - minus) * 100, denominator, out=np.zeros(count), where=denominator > 0)
    dx[:length - 1] = np.nan
    first = 2 * length - 2
    if count > first:
        adx[first] = float(np.mean(dx[length - 1:first + 1]))
        for index in range(first + 1, count):
            adx[index] = (adx[index - 1] * (length - 1) + dx[index]) / length
    return adx, plus, minus


def resample_bars(source: np.ndarray, minutes: int) -> np.ndarray:
    """Aggregate only observed source bars; never invent a missing interval."""
    if not len(source):
        return source.copy()
    group = source["time"] // (minutes * 60)
    starts = np.r_[0, np.flatnonzero(np.diff(group)) + 1]
    last = np.r_[starts[1:] - 1, len(source) - 1]
    result = np.zeros(len(starts), dtype=source.dtype)
    result["time"] = group[starts] * minutes * 60
    result["open"] = source["open"][starts]
    result["high"] = np.maximum.reduceat(source["high"], starts)
    result["low"] = np.minimum.reduceat(source["low"], starts)
    result["close"] = source["close"][last]
    for name in ("tick_volume", "real_volume"):
        if name in source.dtype.names:
            result[name] = np.add.reduceat(source[name], starts)
    if "spread" in source.dtype.names:
        result["spread"] = source["spread"][last]
    return result


class Features:
    def __init__(self, bars: np.ndarray, minutes: int, complete: np.ndarray | None = None):
        self.bars, self.minutes = bars, minutes
        # Structured-array fields are strided.  Scalar searchsorted otherwise
        # copies the whole timestamp field on every weekend/configuration.
        self.open_times = np.ascontiguousarray(bars["time"])
        self.ends = self.open_times + minutes * 60
        self.cache = {}
        self.percentiles = {}
        self.complete = np.ones(len(bars), dtype=bool) if complete is None else complete
        self.coverage_cache = {}

    def valid_lookback(self, length: int) -> np.ndarray:
        if length not in self.coverage_cache:
            bad = ~self.complete.copy()
            if len(bad) > 1:
                bad[1:] |= np.diff(self.open_times) != self.minutes * 60
            counts = np.cumsum(np.r_[0, bad.astype(int)])
            valid = np.zeros(len(bad), dtype=bool)
            if len(bad) >= length:
                valid[length - 1:] = (counts[length:] - counts[:-length]) == 0
            self.coverage_cache[length] = valid
        return self.coverage_cache[length]

    def at(self, epoch: int) -> int:
        return int(np.searchsorted(self.ends, epoch, side="right")) - 1

    def get(self, key: str) -> np.ndarray:
        if key not in self.cache:
            if key == "atr":
                self.cache[key] = sma(true_range(self.bars), 14)
            elif key.startswith("ema"):
                self.cache[key] = ema(self.bars["close"], int(key[3:]))
            elif key in ("adx", "plus", "minus"):
                adx, plus, minus = wilder_adx(self.bars)
                self.cache.update(adx=adx, plus=plus, minus=minus)
            else:
                raise ValueError(key)
        return self.cache[key]

    def percentile(self, index: int) -> float:
        if index not in self.percentiles:
            value = self.get("atr") / self.bars["close"]
            prior = value[:index]
            valid = self.valid_lookback(14)
            prior = prior[np.isfinite(prior) & valid[:index]]
            current = value[index]
            self.percentiles[index] = float(np.mean(prior <= current) * 100) if len(prior) >= 60 and valid[index] and math.isfinite(current) else math.nan
        return self.percentiles[index]


def schedule(start: int, end: int, config: Configuration, weekday: int = 4):
    day = datetime.fromtimestamp(start, NY).date() - timedelta(days=2)
    last = datetime.fromtimestamp(end, NY).date()
    while day <= last:
        if day.weekday() == weekday:
            entry = datetime.combine(day, time(config.entry_minute_ny // 60, config.entry_minute_ny % 60), NY)
            exit_day = day + timedelta(days=2)
            leave = datetime.combine(exit_day, time(config.exit_minute_ny // 60, config.exit_minute_ny % 60), NY)
            entry_epoch, exit_epoch = int(entry.timestamp()), int(leave.timestamp())
            if start <= entry_epoch < end:
                yield day.isoformat(), entry_epoch, exit_epoch
        day += timedelta(days=1)


def summarize(records: list[dict], start: int, end: int, weekly_returns: list[float] | None = None) -> dict:
    returns = np.array([row["return_per_notional"] for row in records], dtype=float)
    if np.any(returns <= -1) or not np.all(np.isfinite(returns)):
        raise ValueError("Invalid one-times-notional return")
    balances = 10000 * np.cumprod(np.r_[1.0, 1 + returns])
    pnl = np.diff(balances)
    peak = np.maximum.accumulate(balances)
    dd = peak - balances
    dd_percent = dd / peak * 100
    positive, negative = pnl[pnl > 0], pnl[pnl < 0]
    loss = float(-negative.sum())
    pf = float(positive.sum() / loss) if loss > 0 else None
    max_wins = max_losses = win_streak = loss_streak = 0
    for value in returns:
        win_streak = win_streak + 1 if value > 0 else 0
        loss_streak = loss_streak + 1 if value < 0 else 0
        max_wins, max_losses = max(max_wins, win_streak), max(max_losses, loss_streak)
    years = (end - start) / (365.25 * 86400)
    annual_log_return = float(np.log(balances[-1] / 10000) / years) if years > 0 else 0
    score = annual_log_return / max(float(dd_percent.max()) / 100, 0.01)
    weekly = np.asarray(weekly_returns if weekly_returns is not None else returns, dtype=float)
    finite_weekly = weekly[np.isfinite(weekly)]
    std = float(np.std(finite_weekly, ddof=1)) if len(finite_weekly) > 1 else 0
    return {
        "trades": len(records), "wins": int(np.sum(returns > 0)), "losses": int(np.sum(returns < 0)),
        "win_rate_pct": float(np.mean(returns > 0) * 100) if len(returns) else None,
        "profit_factor": pf, "return_pct": float((balances[-1] / 10000 - 1) * 100),
        "pnl_usd": float(balances[-1] - 10000), "ending_balance_usd": float(balances[-1]),
        "closed_dd_pct": float(dd_percent.max()), "closed_dd_usd": float(dd.max()),
        "max_win_streak": max_wins, "max_loss_streak": max_losses,
        "weekly_sharpe": float(np.mean(finite_weekly) / std * math.sqrt(52)) if std > 0 else None,
        "annualized_log_return": annual_log_return, "score": score,
        "ambiguous_stop_target_bars": sum(bool(row.get("bar_ambiguous")) for row in records),
        "missing_intrahold_m5_bars": sum(row.get("missing_bar_count", 0) for row in records),
        "cost_basis": "gross M5 bar surrogate, not measured executable net returns",
    }


def score_or_worst(value) -> float:
    return float(value) if value is not None and math.isfinite(float(value)) else -math.inf


def plateau_statistics(rows: list[dict]) -> dict:
    """Unknown neighbor evidence is never an optimistic vote or score."""
    valid = [bool(row["metrics"].get("coverage_evidence_pass", False)) for row in rows]
    positive = sum(ok and row["metrics"]["return_pct"] > 0 for ok, row in zip(valid, rows))
    lower_scores = [row["metrics"]["score"] if ok else -math.inf for ok, row in zip(valid, rows)]
    median = float(np.median(lower_scores)) if lower_scores else -math.inf
    return {
        "median_score": median if math.isfinite(median) else None,
        "positive_neighbours": positive, "total_neighbours": len(rows),
        "coverage_valid_neighbours": sum(valid),
        "missing_neighbour_ids": [row["config_id"] for ok, row in zip(valid, rows) if not ok],
        "majority_positive": positive > len(rows) / 2,
        "median_score_basis": "Missing-coverage neighbors retain denominator and receive negative-infinity lower-bound score; nonfinite median is unavailable, never a boosted descriptive score",
        "neighbourhood_scope": "Joint -15/0/+15 minute timing grid INCLUDING centre, plus adjacent registered stop/RR values; deduplicated configurations",
    }


class WeekendEngine:
    def __init__(self, data_dir: Path | dict[int, np.ndarray], plan: dict, split: dict, root: Path | None = None):
        self.root = Path(root) if root is not None else ROOT
        self.plan, self.split = plan, split
        self.oos_start = timestamp(split["oos"]["start"])
        self.data = {}
        if isinstance(data_dir, dict):
            self.data = {int(key): value.copy() for key, value in data_dir.items()}
        else:
            for minutes, name in ((1, "M1"), (5, "M5"), (60, "H1"), (1440, "D1")):
                path = Path(data_dir) / f"BTCUSD-{name}.npz"
                if path.is_file():
                    with np.load(path, allow_pickle=False) as archive:
                        self.data[minutes] = archive["rates"].copy()
        if 5 not in self.data:
            raise ValueError("Native M5 archive is required")
        for minutes, bars in self.data.items():
            if not {"time", "open", "high", "low", "close"}.issubset(bars.dtype.names or ()) or not len(bars):
                raise ValueError("Unsupported price schema")
            if not np.all(np.diff(bars["time"]) > 0) or not np.all(bars["open"] > 0):
                raise ValueError("Duplicate/unordered/invalid prices")
        self.time_arrays = {minutes: np.ascontiguousarray(bars["time"]) for minutes, bars in self.data.items()}
        self.m5_times = self.time_arrays[5]
        m1_complete = 1 in self.data and self.data[1]["time"][0] <= self.data[5]["time"][0] + 60 and self.data[1]["time"][-1] >= self.data[5]["time"][-1]
        self.available_timeframes = TIMEFRAMES if m1_complete else tuple(value for value in TIMEFRAMES if value not in (1, 3))
        self.features_cache, self.panel_cache = {}, {}
        self.trials: list[dict] = []
        self.trial_by_id: dict[str, dict] = {}
        self.cap = int(plan.get("search", {}).get("max_unique_configurations", 1500))
        self.dev_start = timestamp(split["development"]["start"])
        self.dev_end = timestamp(split["development"]["end_exclusive"])
        self.source_coverage = {str(tf): {"first": int(bars["time"][0]), "last": int(bars["time"][-1]), "rows": len(bars)} for tf, bars in self.data.items()}
        self.finest_complete_minutes = 1 if m1_complete else 5

    def _authorize_window(self, config: Configuration, end: int, allow_oos: bool):
        if end <= self.oos_start:
            return
        if not allow_oos:
            raise PermissionError("OOS locked: persist final selection freeze before evaluation")
        path = self.root / "FROZEN.json"
        if not path.is_file():
            raise PermissionError("Missing final FROZEN.json")
        frozen = json.loads(path.read_text(encoding="utf-8-sig"))
        selected = frozen.get("selected_config", frozen.get("locked", {}).get("selected_config"))
        baseline = frozen.get("baseline_config", BASELINE)
        if selected is None or config_id(config) not in (config_id(selected), config_id(baseline)):
            raise PermissionError("OOS is restricted to frozen final configuration and baseline")
        locked = frozen.get("locked", {})
        if "selected_config" in locked and config_id(locked["selected_config"]) != config_id(selected):
            raise PermissionError("Top-level selected configuration differs from frozen locked selection")
        required = {"PLAN.json", "data-split.json", "search.py", "SEARCH RESULTS.json", "SELECTION.json", "DATA.json"}
        if not required.issubset(locked.get("files", {})):
            raise PermissionError("Incomplete frozen file receipts")
        for name, expected in locked.get("files", {}).items():
            candidate = self.root / name
            if not candidate.is_file() or digest(candidate) != expected:
                raise PermissionError("Frozen input differs: " + name)
        selection = json.loads((self.root / "SELECTION.json").read_text(encoding="utf-8-sig"))
        if config_id(selection["selected_config"]) != config_id(selected):
            raise PermissionError("Frozen configuration differs from hash-locked SELECTION.json")
        if not locked.get("source_hashes"):
            raise PermissionError("Missing frozen source hashes")
        for name, expected in locked["source_hashes"].items():
            candidate = self.root / name
            if not candidate.is_file():
                candidate = self.root / "data" / name
            if not candidate.is_file() or digest(candidate) != expected:
                raise PermissionError("Frozen source differs: " + name)

    def features(self, minutes: int, allow_oos: bool = False) -> Features:
        key = (minutes, allow_oos)
        if key not in self.features_cache:
            if minutes not in self.available_timeframes:
                raise ValueError("Short timeframe lacks full comparable M1 coverage")
            if minutes in self.data:
                bars = self.data[minutes]
            else:
                base = self.data[1 if minutes < 5 else 5]
                bars = resample_bars(base, minutes)
            # Do not even compute indicator arrays through OOS before unlock.
            if not allow_oos:
                bars = bars[bars["time"] + minutes * 60 <= self.oos_start]
            finest = self.time_arrays[self.finest_complete_minutes]
            counts = np.searchsorted(finest, bars["time"] + minutes * 60) - np.searchsorted(finest, bars["time"])
            complete = counts == minutes / self.finest_complete_minutes
            self.features_cache[key] = Features(bars, minutes, complete=complete)
        return self.features_cache[key]

    def _filter(self, cfg: Configuration, f: Features, index: int, entry: np.void) -> tuple[bool, str]:
        if cfg.entry_mode or cfg.stop_mode in (1, 3) or cfg.management_mode or cfg.filter_mode in range(1, 7):
            if index < 0:
                return False, "warmup: no completed signal bar"
        if cfg.entry_mode == 1 and not f.bars["close"][index] > f.bars["open"][index]:
            return False, "entry confirmation failed"
        if cfg.entry_mode == 2:
            if index < 1:
                return False, "warmup: no previous signal close"
            if not f.bars["close"][index] > f.bars["close"][index - 1]:
                return False, "entry confirmation failed"
        mode = cfg.filter_mode
        if mode in (1, 2):
            value = f.get("ema50" if mode == 1 else "ema200")[index]
            if not math.isfinite(value):
                return False, "warmup: EMA"
            return bool(f.bars["close"][index] > value), "filter failed"
        if mode in (3, 4, 5):
            value = f.get("adx")[index]
            if not math.isfinite(value):
                return False, "warmup: ADX"
            passed = value >= (25 if mode == 4 else 20)
            if mode == 5:
                passed = passed and f.get("plus")[index] > f.get("minus")[index]
            return bool(passed), "filter failed"
        if mode == 6:
            value = f.percentile(index)
            if not math.isfinite(value):
                return False, "warmup: expanding ATR percentile"
            lo, hi = ATR_BANDS[int(cfg.filter_value)]
            return lo <= value <= hi, "filter failed"
        if mode == 7:
            source = self.data[5]
            previous = int(np.searchsorted(self.m5_times, int(entry["time"]))) - 1
            if previous < 0 or int(source["time"][previous]) + 300 != int(entry["time"]):
                return False, "missing immediately previous completed M5 spread bar"
            if self.finest_complete_minutes == 1:
                minute_times = self.time_arrays[1]
                count = np.searchsorted(minute_times, int(entry["time"])) - np.searchsorted(minute_times, int(source["time"][previous]))
                if count != 5:
                    return False, "missing constituents of completed M5 spread bar"
            spread = float(source["spread"][previous]) if "spread" in source.dtype.names else 0
            if spread <= 0:
                return False, "missing historical completed M5 spread"
            return spread * 0.01 / float(source["close"][previous]) * 100 <= cfg.filter_value, "filter failed"
        return True, ""

    def _trade(self, cfg: Configuration, week: str, entry_epoch: int, planned_exit: int, i: int, j: int, f: Features, include_paths: bool) -> tuple[dict | None, str]:
        bars = self.data[5][i:j + 1]
        entry = float(bars["open"][0])
        feature_index = f.at(entry_epoch)
        needed = 0
        if cfg.entry_mode:
            needed = 2 if cfg.entry_mode == 2 else 1
        if cfg.stop_mode in (1, 3) or cfg.management_mode or cfg.filter_mode == 6:
            needed = max(needed, 14)
        if cfg.filter_mode in (1, 2):
            needed = max(needed, 50 if cfg.filter_mode == 1 else 200)
        if cfg.filter_mode in (3, 4, 5):
            needed = max(needed, 28)
        expected_feature_end = entry_epoch // (cfg.timeframe_minutes * 60) * (cfg.timeframe_minutes * 60)
        if needed and feature_index >= 0 and int(f.ends[feature_index]) != expected_feature_end:
            return None, "missing latest completed signal timeframe; stale feature rejected"
        if needed and feature_index + 1 < needed:
            return None, "warmup: insufficient completed signal bars"
        if needed and not f.valid_lookback(needed)[feature_index]:
            return None, "missing complete causal feature lookback"
        passed, reason = self._filter(cfg, f, feature_index, bars[0])
        if not passed:
            return None, reason
        distance = 0.0
        if cfg.stop_mode in (1, 3):
            atr = f.get("atr")[feature_index]
            if not math.isfinite(atr) or atr <= 0:
                return None, "warmup: ATR unavailable or zero"
            distance = atr * cfg.stop_value if cfg.stop_mode == 1 else entry - (float(f.bars["low"][feature_index]) - 0.1 * atr)
        elif cfg.stop_mode == 2:
            distance = entry * cfg.stop_value / 100
        if cfg.stop_mode and (distance <= 0 or distance >= entry):
            return None, "invalid stop geometry"
        feature_incomplete = bool(needed and not f.valid_lookback(needed)[feature_index])
        management_bad = np.zeros(len(bars), dtype=bool)
        stops = np.full(len(bars), entry - distance if cfg.stop_mode else -np.inf)
        target = entry + distance * cfg.target_rr if cfg.stop_mode and cfg.target_rr > 0 else math.inf
        if cfg.management_mode:
            indices = np.searchsorted(f.ends, bars["time"], side="right") - 1
            safe = np.maximum(indices, 0)
            after_entry = (indices >= 0) & (f.ends[safe] > entry_epoch)
            closes = f.bars["close"][safe]
            trigger = cfg.management_value if cfg.management_mode == 1 else 1.0
            active = after_entry & (closes >= entry + distance * trigger)
            management_bad = after_entry & ~f.valid_lookback(14)[safe]
            candidates = np.full(len(bars), entry - distance)
            if cfg.management_mode == 1:
                candidates[active] = entry
            elif cfg.management_mode == 2:
                candidates[active] = closes[active] - f.get("atr")[safe[active]] * cfg.management_value
            elif cfg.management_mode == 3:
                candidates[active] = closes[active] * (1 - cfg.management_value / 100)
            else:
                first = int(np.searchsorted(f.open_times, entry_epoch))
                last = max(first, int(safe[-1]) + 1)
                favorable = np.full(len(bars), entry)
                if first < len(f.bars) and last > first:
                    local_highs = np.maximum.accumulate(f.bars["high"][first:last])
                    eligible_indices = (safe >= first) & (safe < last)
                    favorable[eligible_indices] = local_highs[safe[eligible_indices] - first]
                if cfg.management_mode == 4:
                    candidates[active] = favorable[active] - f.get("atr")[safe[active]] * cfg.management_value
                else:
                    candidates[active] = entry + 0.5 * (favorable[active] - entry)
            candidates[~np.isfinite(candidates)] = entry - distance
            stops = np.maximum.accumulate(np.maximum(stops, candidates))
        opens, lows, highs = bars["open"], bars["low"].copy(), bars["high"].copy()
        # Sunday deadline is at OPEN; no high/low from the following interval.
        lows[-1] = highs[-1] = opens[-1]
        gap_sl, gap_tp = opens <= stops, opens >= target
        hit_sl, hit_tp = lows <= stops, highs >= target
        events = np.flatnonzero(hit_sl | hit_tp)
        k = int(events[0]) if len(events) else len(bars) - 1
        ambiguity = bool(hit_sl[k] and hit_tp[k] and not gap_sl[k] and not gap_tp[k])
        if gap_sl[k]:
            price, exit_reason, exact = float(opens[k]), "SL opening gap", True
        elif gap_tp[k]:
            price, exit_reason, exact = float(target), "TP opening gap (target-price conservative)", True
        elif hit_sl[k]:
            price, exit_reason, exact = float(stops[k]), "SL intrabar (stop first if ambiguous)", False
        elif hit_tp[k]:
            price, exit_reason, exact = float(target), "TP intrabar", False
        else:
            price, exit_reason, exact = float(opens[-1]), "Sunday scheduled OPEN", True
        exit_epoch = int(bars["time"][k]) + (0 if exact else 299)
        gross_return = price / entry - 1
        recorded_spread = float(bars["spread"][0]) if "spread" in bars.dtype.names else 0
        observed_proxy = price / (entry + recorded_spread * 0.01) - 1 if recorded_spread > 0 else None
        expected = (int(bars["time"][k]) - entry_epoch) // 300 + 1
        record = {
            "config_id": config_id(cfg), "week_id": week, "entry_epoch": entry_epoch,
            "exit_epoch": exit_epoch, "planned_exit_epoch": planned_exit,
            "entry_price": entry, "exit_price": price, "exit_reason": exit_reason,
            "exit_time_basis": "scheduled/opening-gap bar OPEN" if exact else "unknown intrabar hit, timestamp conservatively assigned end of M5 interval",
            "exit_interval_start": int(bars["time"][k]), "exit_interval_end": int(bars["time"][k]) + (0 if exact else 299),
            "initial_stop_distance": distance, "initial_stop_fraction": distance / entry if distance else None,
            "return_per_notional": gross_return, "gross_return_per_notional": gross_return,
            "observed_spread_proxy_return": observed_proxy,
            "observed_entry_spread_points": recorded_spread if recorded_spread > 0 else None,
            "return_r": (price - entry) / distance if distance else None,
            "bar_ambiguous": ambiguity, "missing_bar_count": max(0, int(expected - k - 1)),
            "incomplete_signal_feature": feature_incomplete,
            "incomplete_management_updates": int(np.sum(management_bad[:k + 1])),
            "cost_basis": "gross M5 surrogate; spread proxy uses the same gross exit geometry, not a quote-level re-execution",
        }
        if include_paths:
            path = [{"epoch": int(bar["time"]), "equity_factor": float(bar["open"] / entry)} for bar in bars[:k + 1]]
            if not path or path[-1]["epoch"] != exit_epoch or path[-1]["equity_factor"] != 1 + gross_return:
                path.append({"epoch": exit_epoch, "equity_factor": 1 + gross_return})
            record["intratrade_path"] = path
        return record, ""

    def panel(self, config: dict | Configuration, start, end, *, include_paths: bool = False, allow_oos: bool = False, control_weekday: int = 4) -> dict:
        cfg = canonical(config)
        start, end = timestamp(start), timestamp(end)
        if end <= start or control_weekday not in range(5):
            raise ValueError("Invalid evaluation window or weekday")
        self._authorize_window(cfg, end, allow_oos)
        key = (config_id(cfg), start, end, include_paths, allow_oos, control_weekday)
        if key in self.panel_cache:
            return self.panel_cache[key]
        f = self.features(cfg.timeframe_minutes, allow_oos=allow_oos)
        times = self.m5_times
        records, missing, filtered, censored, weekly = [], [], [], [], {}
        for week, entry, leave in schedule(start, end, cfg, control_weekday):
            if leave >= end:
                censored.append(week)
                continue
            weekly[week] = None
            i, j = int(np.searchsorted(times, entry)), int(np.searchsorted(times, leave))
            if i >= len(times) or j >= len(times) or times[i] != entry or times[j] != leave:
                missing.append({"week_id": week, "reason": "missing exact scheduled M5 entry/exit bar"})
                continue
            record, reason = self._trade(cfg, week, entry, leave, i, j, f, include_paths)
            if record is None:
                if reason.startswith("missing"):
                    missing.append({"week_id": week, "reason": reason})
                else:
                    filtered.append({"week_id": week, "reason": reason})
                    weekly[week] = 0.0
                continue
            records.append(record)
            if record["missing_bar_count"] or record["incomplete_signal_feature"] or record["incomplete_management_updates"]:
                missing.append({"week_id": week, "reason": "unpriced holding M5 interval or incomplete causal signal/management constituents; descriptive surrogate return retained but not certified"})
            else:
                weekly[week] = record["return_per_notional"]
        values = [math.nan if value is None else value for value in weekly.values()]
        metrics = summarize(records, start, end, values)
        middle = start + (end - start) // 2
        first = summarize([row for row in records if row["entry_epoch"] < middle], start, middle)
        second = summarize([row for row in records if row["entry_epoch"] >= middle], middle, end)
        metrics["halves"] = [first, second]
        metrics["calendar_halves_basis"] = "Split by entry epoch at calendar midpoint, half accounts independently normalized"
        metrics["missing_week_count"] = len(missing)
        metrics["filtered_week_count"] = len(filtered)
        metrics["coverage_evidence_pass"] = not missing
        metrics["eligible_development"] = self.eligible(metrics, development=True)
        result = {
            "config": asdict(cfg), "config_id": config_id(cfg), "start_epoch": start, "end_exclusive_epoch": end,
            "metrics": metrics, "trades": records, "scheduled_week_ids": list(weekly),
            "missing_week_ids": [row["week_id"] for row in missing], "missing_details": missing,
            "filtered_week_ids": [row["week_id"] for row in filtered], "filtered_details": filtered,
            "censored_incomplete_week_ids": censored, "weekly_returns": weekly,
        }
        self.panel_cache[key] = result
        return result

    @staticmethod
    def eligible(metrics: dict, development: bool = True) -> bool:
        pf = metrics["profit_factor"]
        base = metrics.get("coverage_evidence_pass", True) and metrics["trades"] >= 30 and metrics["return_pct"] > 0 and (pf is None and metrics["losses"] == 0 or pf is not None and pf >= 1.15)
        if not base:
            return False
        if development:
            return all(half["trades"] > 0 and half["return_pct"] > 0 and (half["profit_factor"] is None and half["losses"] == 0 or half["profit_factor"] is not None and half["profit_factor"] > 1) for half in metrics.get("halves", []))
        return True

    @staticmethod
    def ranking(row: dict):
        metrics = row["metrics"]
        return (bool(metrics.get("eligible_development", False)), metrics["trades"] >= 100, metrics["score"], metrics["profit_factor"] if metrics["profit_factor"] is not None and metrics["trades"] else -1, metrics["return_pct"], metrics["trades"], row["config_id"])

    def register(self, config: Configuration | dict, stage: str) -> dict:
        cfg, identity = canonical(config), config_id(config)
        if identity in self.trial_by_id:
            if stage not in self.trial_by_id[identity]["stages"]:
                self.trial_by_id[identity]["stages"].append(stage)
            return self.trial_by_id[identity]
        if len(self.trials) >= self.cap:
            raise RuntimeError("Preregistered unique-configuration cap reached; fail, never truncate")
        panel = self.panel(cfg, self.dev_start, self.dev_end)
        row = {"config": asdict(cfg), "config_id": identity, "metrics": panel["metrics"], "stages": [stage]}
        self.trials.append(row)
        self.trial_by_id[identity] = row
        return row

    def _options(self, cfg: Configuration, stage: str) -> list[Configuration]:
        if stage == "entry":
            return [replace(cfg, entry_mode=value) for value in (0, 1, 2)]
        if stage == "stop":
            return [replace(cfg, stop_mode=0), replace(cfg, stop_mode=3)] + [replace(cfg, stop_mode=1, stop_value=value) for value in ATR_VALUES] + [replace(cfg, stop_mode=2, stop_value=value) for value in PERCENT_VALUES]
        if stage == "management":
            if not cfg.stop_mode:
                return [cfg]
            return [replace(cfg, management_mode=0), replace(cfg, management_mode=5)] + [replace(cfg, management_mode=1, management_value=value) for value in (0.5, 1, 1.5)] + [replace(cfg, management_mode=mode, management_value=value) for mode in (2, 4) for value in (1, 2, 3, 4)] + [replace(cfg, management_mode=3, management_value=value) for value in (0.5, 1, 2, 3)]
        if stage == "target":
            return [replace(cfg, target_rr=value) for value in RR_VALUES] if cfg.stop_mode else [cfg]
        if stage == "timing":
            return [replace(cfg, entry_minute_ny=entry, exit_minute_ny=leave) for entry in (960, 1020, 1080) for leave in (960, 1020, 1080)]
        if stage == "filter":
            return [replace(cfg, filter_mode=mode) for mode in range(6)] + [replace(cfg, filter_mode=6, filter_value=value) for value in ATR_BANDS] + [replace(cfg, filter_mode=7, filter_value=value) for value in (0.01, 0.02, 0.05)]
        raise ValueError(stage)

    def neighbours(self, cfg: Configuration | dict) -> list[Configuration]:
        cfg = canonical(cfg)
        candidates = [replace(cfg, entry_minute_ny=cfg.entry_minute_ny + a, exit_minute_ny=cfg.exit_minute_ny + b) for a in (-15, 0, 15) for b in (-15, 0, 15)]
        if cfg.stop_mode in (1, 2):
            values = ATR_VALUES if cfg.stop_mode == 1 else PERCENT_VALUES
            closest = min(range(len(values)), key=lambda i: abs(values[i] - cfg.stop_value))
            candidates += [replace(cfg, stop_value=values[index]) for index in (closest - 1, closest + 1) if 0 <= index < len(values)]
        if cfg.stop_mode:
            closest = min(range(len(RR_VALUES)), key=lambda i: abs(RR_VALUES[i] - cfg.target_rr))
            candidates += [replace(cfg, target_rr=RR_VALUES[index]) for index in (closest - 1, closest + 1) if 0 <= index < len(RR_VALUES)]
        return list({config_id(value): canonical(value) for value in candidates}.values())

    def search_development(self) -> dict:
        stages = []
        seeds = [Configuration()]
        for tf in self.available_timeframes:
            seeds += [Configuration(timeframe_minutes=tf, entry_mode=mode) for mode in (1, 2)]
            seeds.append(Configuration(timeframe_minutes=tf, stop_mode=1, stop_value=2))
        rows = [self.register(cfg, "timeframe") for cfg in seeds]
        beam = sorted({row["config_id"]: row for row in rows}.values(), key=self.ranking, reverse=True)[:3]
        stages.append({"stage": "timeframe", "tested_ids": list(dict.fromkeys(row["config_id"] for row in rows)), "carried_forward_ids": [row["config_id"] for row in beam]})
        for stage in ("entry", "stop", "management", "target", "timing", "filter"):
            candidates = [self.register(cfg, stage) for parent in beam for cfg in self._options(Configuration(**parent["config"]), stage)]
            candidates.append(self.register(BASELINE, stage))
            unique = {row["config_id"]: row for row in candidates}
            beam = sorted(unique.values(), key=self.ranking, reverse=True)[:3]
            stages.append({"stage": stage, "tested_ids": list(unique), "carried_forward_ids": [row["config_id"] for row in beam]})
        # A bounded, preregistered independent neighborhood audit of the top
        # development centres. Never optimize against older validation or OOS.
        centres = sorted(self.trials, key=self.ranking, reverse=True)[:12]
        plateaus = []
        for centre in centres:
            neighbours = [self.register(value, "joint-neighbourhood") for value in self.neighbours(centre["config"])]
            plateaus.append({
                "config": centre["config"], "config_id": centre["config_id"], "metrics": centre["metrics"],
                "neighbour_ids": [row["config_id"] for row in neighbours],
                **plateau_statistics(neighbours),
            })
        plateaus.sort(key=lambda row: (row["metrics"]["eligible_development"] and row["majority_positive"] and row["median_score"] is not None, row["metrics"]["trades"] >= 100, score_or_worst(row["median_score"]), self.ranking(row)), reverse=True)
        finalists = plateaus[:3]
        return {"trials": self.trials, "unique_configurations": len(self.trials), "stages": stages, "plateaus": plateaus, "finalists": finalists, "baseline_config": BASELINE, "rules": rules_contract(), "source_coverage": self.source_coverage, "available_timeframes": list(self.available_timeframes)}

    def validate_finalists(self, development: dict) -> dict:
        start = self.split["validation"]["start"]
        end = self.split["validation"]["end_exclusive"]
        ranked = []
        for finalist in development["finalists"]:
            panel = self.panel(finalist["config"], start, end)
            eligible = self.eligible(panel["metrics"], development=False) and finalist["majority_positive"] and finalist["median_score"] is not None and finalist["metrics"]["eligible_development"]
            ranked.append({"config": finalist["config"], "config_id": finalist["config_id"], "metrics": panel["metrics"], "eligible": eligible, "development_plateau_median": finalist["median_score"]})
        ranked.sort(key=lambda row: (row["eligible"], row["metrics"]["score"], row["metrics"]["profit_factor"] or -1, score_or_worst(row["development_plateau_median"]), row["config_id"]), reverse=True)
        eligible = [row for row in ranked if row["eligible"]]
        chosen = eligible[0] if eligible else development["finalists"][0]
        return {
            "selected_config": chosen["config"], "baseline_config": BASELINE,
            "selected_config_id": chosen["config_id"],
            "selection_status": "research_selection_passed_older_validation" if eligible else "FAILED_VALIDATION_EXPLORATORY_ONLY",
            "reason": "Best older-validation score among the three preselected development plateaus" if eligible else "No finalist passed the registered older-validation/development stability gates; frozen best DEVELOPMENT plateau only, never picked using OOS",
            "dev_finalists": development["finalists"], "validation_ranked": ranked,
            "unique_configurations": len(self.trials), "trial_rows_path": "SEARCH RESULTS.json",
            "oos_read_for_selection": False, "research_only": True,
        }

    def week_return_matrix(self, configs: list[dict], start, end, *, allow_oos: bool = False):
        panels = [self.panel(cfg, start, end, allow_oos=allow_oos) for cfg in configs]
        weeks = sorted(set().union(*(panel["weekly_returns"] for panel in panels)))
        matrix = np.array([[panel["weekly_returns"].get(week, math.nan) if panel["weekly_returns"].get(week) is not None else math.nan for panel in panels] for week in weeks], dtype=float)
        missing = [week for index, week in enumerate(weeks) if not np.all(np.isfinite(matrix[index]))]
        return matrix, [panel["config_id"] for panel in panels], weeks, missing


def rules_contract() -> dict:
    return {
        "baseline": BASELINE, "selection_cost_basis": "gross one-times-current-cash notional, no leverage/risk sizing optimization",
        "rank_score": "annualized log cash return / max(closed-cash drawdown fraction,0.01); eligible first, >=100-trade preference, score/PF/return/count/id ties",
        "development_gate": ">=30 trades, PF>=1.15, positive return; both chronological calendar entry-time halves positive with PF>1; missing histories remain disclosed, no coverage gate waived",
        "coverage_gate": "Any unpriced held M5 interval, incomplete signal-indicator lookback or incomplete management constituent blocks eligible evidence. Descriptive returns remain labelled; affected weekly matrix cells stay missing/NaN, neverzero. Finest full-window feed is used to count completedTF constituents.",
        "stale_features": "Used latest closedTF bar must end at floor(entry_epoch/TFseconds)*TFseconds; no stale completed-feature substitution",
        "warmup": "Initial insufficient indicator bars or percentile observations are a known no-entry rule and valid zero weeks; actual incomplete/gapped constituents after warmup remain missing, notzero",
        "validation_gate": ">=30 trades, PF>=1.15, positive return, development gate and majority positive joint neighbors",
        "seed": "Baseline plus every available TF with entry confirmation1/2 and each TF clock-entry ATR2 protective stop; inactive dimensions canonicalized/deduplicated",
        "beam": "Top3 per stage; top12 development centres get joint-time and adjacent-stop/RR neighborhoods; best3 median-score plateaus enter older validation",
        "plateau_missing": "Coverage-invalid neighbors cannot vote profitable and remain in denominator; score lower bound negativeinfinity, medianNone if unbounded. Timing neighborhood includes its predeclared0/0centre.",
        "atr14": "SMA of14 true ranges, firstTR=H-L, laterTR=max(H-L,abs(H-prevC),abs(L-prevC));14completed bars required",
        "ema": "Recursive alpha2/(N+1), seed first exported close, requireNcompleted bars",
        "adx14": "Wilder sums seed index13 fromfirst14 TR/DM; recursively prev-prev/14+raw;DI=100DM/TR,DX=100abs(DI+-DI-)/(DI++DI-),zero denominator0;firstADXindex26=meanDX13..26;then(prev*13+DX)/14",
        "atr_percentile": "100*count(priorATR14/close<=currentATR14/close)/nprior; allpriorvalidcompletedTFbars since exported2018 start;exclude current;minimum60prior;bothcurrentandpriorrequirecompleteconsecutive14barlookbacks",
        "atr_percentile_bands": ATR_BANDS,
        "filter7": "Immediately previous COMPLETED M5 bar must end at entry clock. Its positive recorded spreadpoints*.01/itsCLOSE*100 <=filter_value percent;0spread=unknown, never invented; native uses same closed feature and separately audits actual request spread",
        "management": "UpdatesbeforeeachM5bar using lastcompletedTF close endingSTRICTLYafterentry. BEtrigger=management_valueR then SLentry. Othersactivateclose>=entry+1R. ATRtrail=close-ATR*value;percenttrail=close*(1-value/100). Chandelier=maxcompletedTFHIGHsinceentry-ATR*value;steplock=entry+.5*(maxHIGH-entry). EligibleHIGHbars requirebarOPEN>=entry;ratchetneverlowers.",
        "execution": "Long only; exact scheduled M5 OPEN; no interpolation. SL gap fills worseOPEN,TP gap fills fixedtarget conservatively;ambiguoussamebarSLfirst;SundayatOPENbeforeitsfutureH/L. Intrabarhittimeunknown,reportedendofM5interval,notactualfilltimestamp.",
        "cost_proxy": "exitgrossgeometry/(entrybid+positiveobservedbarspread*.01)-1 diagnostic only, not reexecuted quote fills; unknown spreads remainNone",
        "oos": "Only frozen final/baseline after FROZEN.json with verified input+source hashes; no automatic OOS in development driver",
    }


def save(path: Path, value: Any):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run_development(root: Path = ROOT) -> dict:
    """Explicit root-driver entry point; never runs automatically on import."""
    root = Path(root)
    freeze = json.loads((root / "PLAN-FREEZE.json").read_text(encoding="utf-8-sig"))
    if digest(root / "PLAN.json") != freeze["plan_sha256"] or digest(root / "data-split.json") != freeze["split_sha256"]:
        raise PermissionError("Preregistered plan or date split changed")
    plan = json.loads((root / "PLAN.json").read_text(encoding="utf-8-sig"))
    split = json.loads((root / "data-split.json").read_text(encoding="utf-8-sig"))
    engine = WeekendEngine(root / "data", plan, split, root)
    development = engine.search_development()
    selection = engine.validate_finalists(development)
    save(root / "SEARCH RESULTS.json", {"trials": engine.trials, "unique_configurations": len(engine.trials), "rules": development["rules"], "source_coverage": engine.source_coverage, "available_timeframes": development["available_timeframes"], "no_oos_evaluated": True})
    save(root / "DEVELOPMENT-STAGES.json", {"stages": development["stages"], "all_trials_counted_and_deduplicated": True})
    save(root / "PLATEAU.json", {"centres": development["plateaus"], "development_only": True})
    save(root / "SELECTION.json", selection)
    return {"engine": engine, "development": development, "selection": selection}


if __name__ == "__main__":
    raise SystemExit("Import and call run_development(root) only after root has verified frozen native export coverage; no automatic search or OOS evaluation.")
