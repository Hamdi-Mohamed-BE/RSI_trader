from __future__ import annotations

import csv
import io
import json
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import requests

from weekend_direction_model import FEATURE_NAMES, WeekendRecord


ROOT = Path(__file__).resolve().parent
CONTEXT_DIR = ROOT / "data" / "weekend-direction-v2"
COT_CACHE = CONTEXT_DIR / "cftc_gold_cot.json"
FRED_DIR = ROOT / "data" / "macro-regime"

FRED_SERIES = {
    "usd_broad": "DTWEXBGS",
    "real_yield_10y": "DFII10",
    "nominal_2y": "DGS2",
    "nominal_10y": "DGS10",
    "vix": "VIXCLS",
    "breakeven_10y": "T10YIE",
}

MARKET_FEATURES = (
    "xau_ret_240m",
    "xau_ret_1440m",
    "xau_ret_7200m",
    "xau_rv_1440m",
    "xau_range_1440m",
    "xau_close_location_1440m",
    "xau_body_ratio_240m",
    "xau_spread_ratio_60m",
    "previous_gap_direction",
    "previous_gap_pct",
    "up_rate_last_4",
    "up_rate_last_12",
    "mean_gap_pct_last_4",
    "mean_abs_gap_pct_last_12",
    "xagusd_ret_24h",
    "xagusd_ret_120h",
    "us30_ret_24h",
    "us30_ret_120h",
    "btcusd_ret_24h",
    "btcusd_ret_120h",
)

MACRO_FEATURES = (
    "macro_usd_change_5d",
    "macro_usd_change_20d",
    "macro_real_yield_level",
    "macro_real_yield_change_5d",
    "macro_real_yield_change_20d",
    "macro_vix_level",
    "macro_vix_change_5d",
    "macro_yield_curve_10y_2y",
    "macro_breakeven_change_5d",
)

COT_FEATURES = (
    "cot_managed_net_share",
    "cot_managed_net_change_share",
    "cot_producer_net_share",
    "cot_swap_net_share",
)

V2_FEATURE_NAMES = MARKET_FEATURES + MACRO_FEATURES + COT_FEATURES


@dataclass(frozen=True)
class DatedSeries:
    dates: tuple[date, ...]
    values: tuple[float, ...]


@dataclass(frozen=True)
class CotRecord:
    report_date: date
    open_interest: float
    managed_long: float
    managed_short: float
    managed_long_change: float
    managed_short_change: float
    producer_long: float
    producer_short: float
    swap_long: float
    swap_short: float


@dataclass(frozen=True)
class V2Sample:
    record: WeekendRecord
    meaningful_threshold_pct: float
    meaningful_gap: int
    direction_up: int
    features: tuple[float, ...]


def _fred_text(series_id: str) -> str:
    response = requests.get(
        "https://fred.stlouisfed.org/graph/fredgraph.csv",
        params={"id": series_id},
        timeout=60,
    )
    response.raise_for_status()
    return response.text


def load_fred_series(series_id: str, *, refresh: bool = False) -> DatedSeries:
    path = FRED_DIR / f"{series_id}.csv"
    if refresh or not path.exists():
        FRED_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(_fred_text(series_id), encoding="utf-8")
    rows: list[tuple[date, float]] = []
    for row in csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))):
        raw_date = row.get("observation_date") or row.get("DATE")
        raw_value = row.get(series_id)
        if not raw_date or raw_value in (None, "", "."):
            continue
        try:
            rows.append((date.fromisoformat(raw_date), float(raw_value)))
        except ValueError:
            continue
    rows.sort(key=lambda item: item[0])
    return DatedSeries(tuple(item[0] for item in rows), tuple(item[1] for item in rows))


def load_macro_context(*, refresh: bool = False) -> dict[str, DatedSeries]:
    return {label: load_fred_series(series_id, refresh=refresh) for label, series_id in FRED_SERIES.items()}


def _float(row: Mapping[str, str], key: str) -> float:
    try:
        return float(row.get(key, 0.0))
    except (TypeError, ValueError):
        return 0.0


def fetch_gold_cot(*, refresh: bool = False) -> list[CotRecord]:
    if refresh or not COT_CACHE.exists():
        params = {
            "$select": ",".join(
                (
                    "report_date_as_yyyy_mm_dd",
                    "open_interest_all",
                    "m_money_positions_long_all",
                    "m_money_positions_short_all",
                    "change_in_m_money_long_all",
                    "change_in_m_money_short_all",
                    "prod_merc_positions_long",
                    "prod_merc_positions_short",
                    "swap_positions_long_all",
                    "swap__positions_short_all",
                )
            ),
            "$where": "cftc_contract_market_code='088691'",
            "$order": "report_date_as_yyyy_mm_dd ASC",
            "$limit": "5000",
        }
        response = requests.get(
            "https://publicreporting.cftc.gov/resource/72hh-3qpy.json",
            params=params,
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
        COT_CACHE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    else:
        payload = json.loads(COT_CACHE.read_text(encoding="utf-8"))

    records: list[CotRecord] = []
    for row in payload:
        raw_date = str(row.get("report_date_as_yyyy_mm_dd", ""))[:10]
        if not raw_date:
            continue
        records.append(
            CotRecord(
                report_date=date.fromisoformat(raw_date),
                open_interest=_float(row, "open_interest_all"),
                managed_long=_float(row, "m_money_positions_long_all"),
                managed_short=_float(row, "m_money_positions_short_all"),
                managed_long_change=_float(row, "change_in_m_money_long_all"),
                managed_short_change=_float(row, "change_in_m_money_short_all"),
                producer_long=_float(row, "prod_merc_positions_long"),
                producer_short=_float(row, "prod_merc_positions_short"),
                swap_long=_float(row, "swap_positions_long_all"),
                swap_short=_float(row, "swap__positions_short_all"),
            )
        )
    records.sort(key=lambda item: item.report_date)
    return records


def _latest_before(series: DatedSeries, cutoff: date) -> int:
    return bisect_left(series.dates, cutoff) - 1


def _change(series: DatedSeries, index: int, periods: int, *, relative: bool = False) -> float:
    if index < periods:
        return float("nan")
    current = series.values[index]
    previous = series.values[index - periods]
    if relative:
        return current / previous - 1.0 if previous else float("nan")
    return current - previous


def macro_features(context: Mapping[str, DatedSeries], cutoff: datetime) -> list[float]:
    # Friday-dated official observations may be published after some market
    # cutoffs. Restricting to dates before Friday is conservative and leak-free.
    indices = {label: _latest_before(series, cutoff.date()) for label, series in context.items()}
    if any(index < 20 for index in indices.values()):
        return [float("nan")] * len(MACRO_FEATURES)
    usd = context["usd_broad"]
    real = context["real_yield_10y"]
    vix = context["vix"]
    two = context["nominal_2y"]
    ten = context["nominal_10y"]
    breakeven = context["breakeven_10y"]
    return [
        _change(usd, indices["usd_broad"], 5, relative=True),
        _change(usd, indices["usd_broad"], 20, relative=True),
        real.values[indices["real_yield_10y"]],
        _change(real, indices["real_yield_10y"], 5),
        _change(real, indices["real_yield_10y"], 20),
        vix.values[indices["vix"]] / 100.0,
        _change(vix, indices["vix"], 5, relative=True),
        ten.values[indices["nominal_10y"]] - two.values[indices["nominal_2y"]],
        _change(breakeven, indices["breakeven_10y"], 5),
    ]


def cot_features(records: Sequence[CotRecord], cutoff: datetime) -> list[float]:
    # COT is normally published Friday for Tuesday's positions, but holiday
    # delays are not available as a complete historical timestamp series.
    # A full one-week lag guarantees every selected report was public.
    safe_report_date = cutoff.date() - timedelta(days=7)
    dates = [item.report_date for item in records]
    index = bisect_right(dates, safe_report_date) - 1
    if index < 0:
        return [float("nan")] * len(COT_FEATURES)
    item = records[index]
    oi = item.open_interest
    if oi <= 0:
        return [float("nan")] * len(COT_FEATURES)
    return [
        (item.managed_long - item.managed_short) / oi,
        (item.managed_long_change - item.managed_short_change) / oi,
        (item.producer_long - item.producer_short) / oi,
        (item.swap_long - item.swap_short) / oi,
    ]


def _market_features(record: WeekendRecord) -> list[float]:
    values = dict(zip(FEATURE_NAMES, record.feature_values))
    return [
        values["xau_ret_240m"],
        values["xau_ret_1440m"],
        values["xau_ret_7200m"],
        values["xau_rv_1440m"],
        values["xau_range_1440m"],
        values["xau_close_location_1440m"],
        values["xau_body_ratio_240m"],
        values["xau_spread_ratio_60m"],
        values["previous_gap_direction"],
        values["previous_gap_pct"],
        values["up_rate_last_4"],
        values["up_rate_last_12"],
        values["mean_gap_pct_last_4"],
        values["mean_abs_gap_pct_last_12"],
        values["xagusd_ret_24h"],
        values["xagusd_ret_120h"],
        values["us30_ret_24h"],
        values["us30_ret_120h"],
        values["btcusd_ret_24h"],
        values["btcusd_ret_120h"],
    ]


def v2_feature_vector(
    record: WeekendRecord,
    macro_context: Mapping[str, DatedSeries],
    cot_records: Sequence[CotRecord],
) -> tuple[float, ...]:
    cutoff = datetime.fromisoformat(record.feature_time_utc)
    return tuple(
        float(value)
        for value in _market_features(record)
        + macro_features(macro_context, cutoff)
        + cot_features(cot_records, cutoff)
    )


def build_v2_samples(
    records: Sequence[WeekendRecord],
    macro_context: Mapping[str, DatedSeries],
    cot_records: Sequence[CotRecord],
    *,
    meaningful_quantile: float = 0.70,
    threshold_history: int = 26,
) -> list[V2Sample]:
    samples: list[V2Sample] = []
    absolute_history: list[float] = []
    for record in records:
        if len(absolute_history) >= threshold_history:
            threshold = float(np.quantile(absolute_history[-threshold_history:], meaningful_quantile))
            features = v2_feature_vector(record, macro_context, cot_records)
            samples.append(
                V2Sample(
                    record=record,
                    meaningful_threshold_pct=threshold,
                    meaningful_gap=int(abs(record.gap_pct) >= threshold),
                    direction_up=record.label_up,
                    features=features,
                )
            )
        absolute_history.append(abs(record.gap_pct))
    return samples


def samples_to_arrays(samples: Sequence[V2Sample]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return (
        np.asarray([sample.features for sample in samples], dtype=float),
        np.asarray([sample.meaningful_gap for sample in samples], dtype=int),
        np.asarray([sample.direction_up for sample in samples], dtype=int),
    )
