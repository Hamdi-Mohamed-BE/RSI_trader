from __future__ import annotations

import csv
import io
from bisect import bisect_left
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import requests

from news_core import ROOT


FRED_SERIES = {
    "usd_broad": "DTWEXBGS",
    "us_2y": "DGS2",
    "us_10y": "DGS10",
    "vix": "VIXCLS",
    "breakeven_10y": "T10YIE",
    "fed_funds": "DFF",
}
CACHE_DIR = ROOT / "data" / "macro-regime"
MAX_STALENESS_DAYS = 7
LOOKBACKS = (1, 5, 20)


@dataclass(frozen=True)
class SeriesData:
    dates: tuple[date, ...]
    values: tuple[float, ...]


def feature_names() -> tuple[str, ...]:
    names: list[str] = []
    for label in FRED_SERIES:
        names.extend(
            (
                f"macro_{label}_level",
                *(f"macro_{label}_change_{window}" for window in LOOKBACKS),
                f"macro_{label}_staleness_days",
                f"macro_{label}_missing",
            )
        )
    names.append("macro_yield_curve_10y_2y")
    return tuple(names)


def _fred_csv(series_id: str) -> str:
    response = requests.get(
        "https://fred.stlouisfed.org/graph/fredgraph.csv",
        params={"id": series_id},
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def _cache_path(series_id: str) -> Path:
    return CACHE_DIR / f"{series_id}.csv"


def _load_series(series_id: str, refresh: bool = False) -> SeriesData:
    path = _cache_path(series_id)
    if refresh or not path.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(_fred_csv(series_id), encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    rows: list[tuple[date, float]] = []
    for row in csv.DictReader(io.StringIO(text)):
        raw_date = row.get("observation_date") or row.get("DATE")
        raw_value = row.get(series_id)
        if not raw_date or raw_value in (None, "", "."):
            continue
        try:
            rows.append((date.fromisoformat(raw_date), float(raw_value)))
        except ValueError:
            continue
    rows.sort(key=lambda item: item[0])
    return SeriesData(
        dates=tuple(item[0] for item in rows),
        values=tuple(item[1] for item in rows),
    )


class MacroRegimeStore:
    def __init__(self, refresh: bool = False) -> None:
        self.series = {
            label: _load_series(series_id, refresh=refresh)
            for label, series_id in FRED_SERIES.items()
        }

    @staticmethod
    def _point_before(series: SeriesData, release_date: date) -> int:
        return bisect_left(series.dates, release_date) - 1

    def features(self, release_utc: str | datetime) -> list[float]:
        release = (
            release_utc
            if isinstance(release_utc, datetime)
            else datetime.fromisoformat(release_utc.replace("Z", "+00:00"))
        )
        output: list[float] = []
        current: dict[str, float | None] = {}
        for label, series in self.series.items():
            index = self._point_before(series, release.date())
            stale = (
                index < 0
                or (release.date() - series.dates[index]).days > MAX_STALENESS_DAYS
            )
            if stale:
                output.extend((0.0, *(0.0 for _ in LOOKBACKS), 0.0, 1.0))
                current[label] = None
                continue
            value = series.values[index]
            changes = [
                value - series.values[index - window]
                if index >= window
                else 0.0
                for window in LOOKBACKS
            ]
            staleness = float((release.date() - series.dates[index]).days)
            output.extend((value, *changes, staleness, 0.0))
            current[label] = value
        curve = (
            float(current["us_10y"] - current["us_2y"])
            if current["us_10y"] is not None and current["us_2y"] is not None
            else 0.0
        )
        output.append(curve)
        return output

