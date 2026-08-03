from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import numpy as np

from weekend_direction_model import FEATURE_NAMES, WeekendRecord
from weekend_direction_v2 import (
    COT_FEATURES,
    MACRO_FEATURES,
    V2_FEATURE_NAMES,
    CotRecord,
    DatedSeries,
    build_v2_samples,
    cot_features,
    macro_features,
)


def record(index: int, gap_pct: float) -> WeekendRecord:
    friday = datetime(2020, 1, 3, 20, tzinfo=timezone.utc) + timedelta(days=7 * index)
    reopen = friday + timedelta(days=3)
    return WeekendRecord(
        friday_close_utc=friday.isoformat(),
        feature_time_utc=(friday - timedelta(minutes=5)).isoformat(),
        reopen_utc=reopen.isoformat(),
        friday_mid_close=2000.0,
        reopen_mid_open=2000.0 * (1.0 + gap_pct),
        gap_usd=2000.0 * gap_pct,
        gap_pct=gap_pct,
        label_up=int(gap_pct > 0),
        feature_values=tuple(float(index + offset) for offset in range(len(FEATURE_NAMES))),
    )


def context() -> dict[str, DatedSeries]:
    dates = tuple(date(2018, 1, 1) + timedelta(days=index) for index in range(2000))
    values = tuple(100.0 + index * 0.01 for index in range(2000))
    return {
        "usd_broad": DatedSeries(dates, values),
        "real_yield_10y": DatedSeries(dates, values),
        "nominal_2y": DatedSeries(dates, values),
        "nominal_10y": DatedSeries(dates, tuple(value + 1.0 for value in values)),
        "vix": DatedSeries(dates, values),
        "breakeven_10y": DatedSeries(dates, values),
    }


def cot_rows() -> list[CotRecord]:
    return [
        CotRecord(
            report_date=date(2018, 1, 2) + timedelta(days=7 * index),
            open_interest=1000.0,
            managed_long=300.0 + index,
            managed_short=200.0,
            managed_long_change=10.0,
            managed_short_change=5.0,
            producer_long=100.0,
            producer_short=300.0,
            swap_long=250.0,
            swap_short=200.0,
        )
        for index in range(150)
    ]


class WeekendDirectionV2Tests(unittest.TestCase):
    def test_feature_contract_has_expected_size(self) -> None:
        records = [record(index, 0.001 * ((index % 7) - 3)) for index in range(30)]
        samples = build_v2_samples(records, context(), cot_rows(), threshold_history=5)
        self.assertTrue(samples)
        self.assertEqual(len(samples[0].features), len(V2_FEATURE_NAMES))

    def test_threshold_uses_only_requested_trailing_history(self) -> None:
        records = [record(index, value) for index, value in enumerate((0.01, 0.02, 0.03, 0.04, 0.05, 0.06))]
        samples = build_v2_samples(records, context(), cot_rows(), meaningful_quantile=0.5, threshold_history=3)
        self.assertAlmostEqual(samples[0].meaningful_threshold_pct, 0.02)
        self.assertAlmostEqual(samples[1].meaningful_threshold_pct, 0.03)
        changed = list(records)
        changed[-1] = replace(changed[-1], gap_pct=99.0, gap_usd=198000.0)
        changed_samples = build_v2_samples(changed, context(), cot_rows(), meaningful_quantile=0.5, threshold_history=3)
        self.assertEqual(samples[0].features, changed_samples[0].features)
        self.assertEqual(samples[0].meaningful_threshold_pct, changed_samples[0].meaningful_threshold_pct)

    def test_macro_ignores_cutoff_day_and_future_values(self) -> None:
        base = context()
        cutoff = datetime(2021, 1, 8, 20, tzinfo=timezone.utc)
        expected = macro_features(base, cutoff)
        changed = {}
        for name, series in base.items():
            values = list(series.values)
            for index, day in enumerate(series.dates):
                if day >= cutoff.date():
                    values[index] += 10000.0
            changed[name] = DatedSeries(series.dates, tuple(values))
        np.testing.assert_allclose(expected, macro_features(changed, cutoff), equal_nan=True)
        self.assertEqual(len(expected), len(MACRO_FEATURES))

    def test_cot_uses_full_week_safety_lag(self) -> None:
        rows = cot_rows()
        cutoff = datetime(2020, 1, 10, 20, tzinfo=timezone.utc)
        expected = cot_features(rows, cutoff)
        safe_date = cutoff.date() - timedelta(days=7)
        changed = [
            replace(item, managed_long=item.managed_long + 50000.0)
            if item.report_date > safe_date
            else item
            for item in rows
        ]
        np.testing.assert_allclose(expected, cot_features(changed, cutoff), equal_nan=True)
        self.assertEqual(len(expected), len(COT_FEATURES))


if __name__ == "__main__":
    unittest.main()
