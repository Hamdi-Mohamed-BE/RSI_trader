from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import sqrt
from typing import Iterable, Mapping, Sequence

import numpy as np


CORE_FEATURES = (
    "xau_ret_15m",
    "xau_ret_60m",
    "xau_ret_240m",
    "xau_ret_1440m",
    "xau_ret_7200m",
    "xau_rv_60m",
    "xau_rv_240m",
    "xau_rv_1440m",
    "xau_range_60m",
    "xau_range_240m",
    "xau_range_1440m",
    "xau_close_location_60m",
    "xau_close_location_240m",
    "xau_close_location_1440m",
    "xau_body_ratio_60m",
    "xau_body_ratio_240m",
    "xau_upper_wick_ratio_60m",
    "xau_lower_wick_ratio_60m",
    "xau_volume_ratio_60_240",
    "xau_volume_ratio_240_1440",
    "xau_spread_usd",
    "xau_spread_ratio_60m",
    "xau_close_vs_mean_240m",
    "xau_mean_240_vs_1440m",
    "month_sin",
    "month_cos",
    "week_sin",
    "week_cos",
)

HISTORY_FEATURES = (
    "previous_gap_direction",
    "previous_gap_pct",
    "up_rate_last_4",
    "up_rate_last_12",
    "mean_gap_pct_last_4",
    "mean_abs_gap_pct_last_12",
)

CROSS_MARKETS = ("XAGUSD", "US30", "BTCUSD")
CROSS_SUFFIXES = ("ret_1h", "ret_4h", "ret_24h", "ret_120h", "rv_24h", "close_location_24h")
CROSS_FEATURES = tuple(f"{symbol.lower()}_{suffix}" for symbol in CROSS_MARKETS for suffix in CROSS_SUFFIXES)
FEATURE_NAMES = CORE_FEATURES + HISTORY_FEATURES + CROSS_FEATURES


@dataclass(frozen=True)
class MarketSeries:
    symbol: str
    point: float
    timeframe_seconds: int
    time: np.ndarray
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    tick_volume: np.ndarray
    spread: np.ndarray

    def __post_init__(self) -> None:
        length = len(self.time)
        if length == 0:
            raise ValueError(f"{self.symbol} has no bars")
        for values in (self.open, self.high, self.low, self.close, self.tick_volume, self.spread):
            if len(values) != length:
                raise ValueError(f"{self.symbol} arrays are not aligned")
        if np.any(np.diff(self.time) <= 0):
            raise ValueError(f"{self.symbol} times must be strictly increasing")


@dataclass(frozen=True)
class WeekendRecord:
    feature_time_utc: str
    friday_close_utc: str
    reopen_utc: str
    friday_mid_close: float
    reopen_mid_open: float
    gap_usd: float
    gap_pct: float
    label_up: int
    feature_values: tuple[float, ...]


def iso_utc(timestamp: int) -> str:
    return datetime.fromtimestamp(int(timestamp), timezone.utc).isoformat()


def find_weekend_windows(times: np.ndarray) -> list[tuple[int, int]]:
    candidates = np.flatnonzero(np.diff(times) >= 24 * 60 * 60)
    windows: list[tuple[int, int]] = []
    for close_index in candidates:
        reopen_index = int(close_index) + 1
        before = datetime.fromtimestamp(int(times[close_index]), timezone.utc)
        after = datetime.fromtimestamp(int(times[reopen_index]), timezone.utc)
        if before.weekday() in (4, 5) and after.weekday() in (6, 0):
            windows.append((int(close_index), reopen_index))
    return windows


def _return(close: np.ndarray, end: int, bars: int) -> float:
    start = end - bars
    if start < 0 or close[start] <= 0:
        return float("nan")
    return float(close[end] / close[start] - 1.0)


def _realized_vol(close: np.ndarray, end: int, bars: int) -> float:
    start = end - bars + 1
    if start < 0:
        return float("nan")
    values = close[start : end + 1]
    if len(values) < 3 or np.any(values <= 0):
        return float("nan")
    return float(np.std(np.diff(np.log(values)), ddof=1) * sqrt(len(values) - 1))


def _range_pct(high: np.ndarray, low: np.ndarray, close: np.ndarray, end: int, bars: int) -> float:
    start = end - bars + 1
    if start < 0 or close[end] <= 0:
        return float("nan")
    return float((np.max(high[start : end + 1]) - np.min(low[start : end + 1])) / close[end])


def _location(high: np.ndarray, low: np.ndarray, close: np.ndarray, end: int, bars: int) -> float:
    start = end - bars + 1
    if start < 0:
        return float("nan")
    top = float(np.max(high[start : end + 1]))
    bottom = float(np.min(low[start : end + 1]))
    return 0.5 if top <= bottom else float((close[end] - bottom) / (top - bottom))


def _aggregate_shape(series: MarketSeries, end: int, bars: int) -> tuple[float, float, float]:
    start = end - bars + 1
    if start < 0:
        return float("nan"), float("nan"), float("nan")
    open_price = float(series.open[start])
    close_price = float(series.close[end])
    top = float(np.max(series.high[start : end + 1]))
    bottom = float(np.min(series.low[start : end + 1]))
    span = top - bottom
    if span <= 0:
        return 0.0, 0.0, 0.0
    body = (close_price - open_price) / span
    upper = (top - max(open_price, close_price)) / span
    lower = (min(open_price, close_price) - bottom) / span
    return float(body), float(upper), float(lower)


def _safe_ratio(numerator: float, denominator: float) -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or abs(denominator) < 1e-12:
        return float("nan")
    return float(numerator / denominator)


def _cross_features(series: MarketSeries | None, cutoff_timestamp: int) -> list[float]:
    if series is None:
        return [float("nan")] * len(CROSS_SUFFIXES)

    # H1 bars are stamped at their opening time. Requiring a full timeframe to
    # elapse prevents an unfinished Friday H1 close from leaking future prices.
    latest_closed_start = cutoff_timestamp - series.timeframe_seconds
    end = int(np.searchsorted(series.time, latest_closed_start, side="right") - 1)
    if end < 121:
        return [float("nan")] * len(CROSS_SUFFIXES)
    return [
        _return(series.close, end, 1),
        _return(series.close, end, 4),
        _return(series.close, end, 24),
        _return(series.close, end, 120),
        _realized_vol(series.close, end, 24),
        _location(series.high, series.low, series.close, end, 24),
    ]


def feature_vector_at(
    gold: MarketSeries,
    cutoff_index: int,
    cross_markets: Mapping[str, MarketSeries],
    previous_gaps: Sequence[float],
) -> tuple[float, ...]:
    if gold.timeframe_seconds != 60:
        raise ValueError("Gold features require M1 bars")
    if cutoff_index < 7200:
        raise ValueError("At least 7,200 completed M1 bars are required")

    body_60, upper_60, lower_60 = _aggregate_shape(gold, cutoff_index, 60)
    body_240, _, _ = _aggregate_shape(gold, cutoff_index, 240)
    volume_60 = float(np.mean(gold.tick_volume[cutoff_index - 59 : cutoff_index + 1]))
    volume_240 = float(np.mean(gold.tick_volume[cutoff_index - 239 : cutoff_index + 1]))
    volume_1440 = float(np.mean(gold.tick_volume[cutoff_index - 1439 : cutoff_index + 1]))
    spread_last = float(gold.spread[cutoff_index]) * gold.point
    spread_60 = float(np.mean(gold.spread[cutoff_index - 59 : cutoff_index + 1])) * gold.point
    mean_240 = float(np.mean(gold.close[cutoff_index - 239 : cutoff_index + 1]))
    mean_1440 = float(np.mean(gold.close[cutoff_index - 1439 : cutoff_index + 1]))
    current = float(gold.close[cutoff_index])
    moment = datetime.fromtimestamp(int(gold.time[cutoff_index]), timezone.utc)
    week_angle = 2.0 * np.pi * moment.isocalendar().week / 52.1775
    month_angle = 2.0 * np.pi * moment.month / 12.0

    core = [
        _return(gold.close, cutoff_index, 15),
        _return(gold.close, cutoff_index, 60),
        _return(gold.close, cutoff_index, 240),
        _return(gold.close, cutoff_index, 1440),
        _return(gold.close, cutoff_index, 7200),
        _realized_vol(gold.close, cutoff_index, 60),
        _realized_vol(gold.close, cutoff_index, 240),
        _realized_vol(gold.close, cutoff_index, 1440),
        _range_pct(gold.high, gold.low, gold.close, cutoff_index, 60),
        _range_pct(gold.high, gold.low, gold.close, cutoff_index, 240),
        _range_pct(gold.high, gold.low, gold.close, cutoff_index, 1440),
        _location(gold.high, gold.low, gold.close, cutoff_index, 60),
        _location(gold.high, gold.low, gold.close, cutoff_index, 240),
        _location(gold.high, gold.low, gold.close, cutoff_index, 1440),
        body_60,
        body_240,
        upper_60,
        lower_60,
        _safe_ratio(volume_60, volume_240),
        _safe_ratio(volume_240, volume_1440),
        spread_last,
        _safe_ratio(spread_last, spread_60),
        _safe_ratio(current, mean_240) - 1.0,
        _safe_ratio(mean_240, mean_1440) - 1.0,
        float(np.sin(month_angle)),
        float(np.cos(month_angle)),
        float(np.sin(week_angle)),
        float(np.cos(week_angle)),
    ]

    previous = list(previous_gaps)
    last = previous[-1] if previous else float("nan")
    last_4 = previous[-4:]
    last_12 = previous[-12:]
    history = [
        float(last > 0) if np.isfinite(last) else float("nan"),
        float(last),
        float(np.mean(np.asarray(last_4) > 0)) if last_4 else float("nan"),
        float(np.mean(np.asarray(last_12) > 0)) if last_12 else float("nan"),
        float(np.mean(last_4)) if last_4 else float("nan"),
        float(np.mean(np.abs(last_12))) if last_12 else float("nan"),
    ]

    cross: list[float] = []
    cutoff_timestamp = int(gold.time[cutoff_index])
    for symbol in CROSS_MARKETS:
        cross.extend(_cross_features(cross_markets.get(symbol), cutoff_timestamp))

    values = tuple(float(value) for value in core + history + cross)
    if len(values) != len(FEATURE_NAMES):
        raise AssertionError("Feature name/value mismatch")
    return values


def build_weekend_dataset(
    gold: MarketSeries,
    cross_markets: Mapping[str, MarketSeries],
    *,
    placement_lead_minutes: int = 5,
) -> list[WeekendRecord]:
    records: list[WeekendRecord] = []
    previous_gaps: list[float] = []
    for close_index, reopen_index in find_weekend_windows(gold.time):
        cutoff_index = close_index - placement_lead_minutes
        if cutoff_index < 7200:
            continue
        friday_mid = float(gold.close[close_index]) + float(gold.spread[close_index]) * gold.point / 2.0
        reopen_mid = float(gold.open[reopen_index]) + float(gold.spread[reopen_index]) * gold.point / 2.0
        gap_usd = reopen_mid - friday_mid
        gap_pct = gap_usd / friday_mid if friday_mid else 0.0
        values = feature_vector_at(gold, cutoff_index, cross_markets, previous_gaps)
        records.append(
            WeekendRecord(
                feature_time_utc=iso_utc(gold.time[cutoff_index]),
                friday_close_utc=iso_utc(gold.time[close_index]),
                reopen_utc=iso_utc(gold.time[reopen_index]),
                friday_mid_close=round(friday_mid, 6),
                reopen_mid_open=round(reopen_mid, 6),
                gap_usd=round(gap_usd, 6),
                gap_pct=float(gap_pct),
                label_up=int(gap_usd > 0),
                feature_values=values,
            )
        )
        previous_gaps.append(gap_pct)
    return records


def records_to_arrays(records: Iterable[WeekendRecord]) -> tuple[np.ndarray, np.ndarray]:
    items = list(records)
    return (
        np.asarray([record.feature_values for record in items], dtype=float),
        np.asarray([record.label_up for record in items], dtype=int),
    )


def expanding_folds(sample_count: int, *, initial_train: int, splits: int = 4, embargo: int = 1) -> list[tuple[np.ndarray, np.ndarray]]:
    if sample_count <= initial_train + splits:
        raise ValueError("Not enough samples for expanding validation")
    boundaries = np.linspace(initial_train, sample_count, splits + 1, dtype=int)
    folds: list[tuple[np.ndarray, np.ndarray]] = []
    for index in range(splits):
        test_start = int(boundaries[index])
        test_end = int(boundaries[index + 1])
        train_end = max(0, test_start - embargo)
        folds.append((np.arange(train_end), np.arange(test_start, test_end)))
    return folds


def wilson_interval(correct: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 0.0
    proportion = correct / total
    denominator = 1.0 + z * z / total
    centre = (proportion + z * z / (2.0 * total)) / denominator
    margin = z * sqrt((proportion * (1.0 - proportion) + z * z / (4.0 * total)) / total) / denominator
    return max(0.0, centre - margin), min(1.0, centre + margin)


def choose_confidence_threshold(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    *,
    minimum_coverage: float = 0.25,
    minimum_actions: int = 25,
) -> dict:
    predictions = (probabilities >= 0.5).astype(int)
    confidence = np.maximum(probabilities, 1.0 - probabilities)
    candidates: list[dict] = []
    for threshold in np.arange(0.50, 0.751, 0.025):
        mask = confidence >= threshold - 1e-12
        count = int(np.sum(mask))
        if count < minimum_actions or count / len(y_true) < minimum_coverage:
            continue
        correct = int(np.sum(predictions[mask] == y_true[mask]))
        low, high = wilson_interval(correct, count)
        candidates.append(
            {
                "threshold": round(float(threshold), 3),
                "actions": count,
                "coverage_pct": round(100.0 * count / len(y_true), 2),
                "accuracy_pct": round(100.0 * correct / count, 2),
                "wilson_low_pct": round(100.0 * low, 2),
                "wilson_high_pct": round(100.0 * high, 2),
            }
        )
    if not candidates:
        raise ValueError("No confidence threshold satisfies the coverage constraints")
    return max(candidates, key=lambda item: (item["wilson_low_pct"], item["coverage_pct"], -item["threshold"]))
