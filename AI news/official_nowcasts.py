from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from pathlib import Path

import openpyxl
import requests

from news_core import ROOT


CACHE_DIR = ROOT / "data" / "official-nowcasts"
CACHE_PATH = CACHE_DIR / "official_nowcasts.json"
CLEVELAND_URL = (
    "https://www.clevelandfed.org/-/media/files/webcharts/"
    "inflationnowcasting/nowcast_month.json"
)
ATLANTA_URL = (
    "https://www.atlantafed.org/-/media/Project/Atlanta/FRBA/Documents/"
    "cqer/researchcq/gdpnow/GDPTrackingModelDataAndForecasts.xlsx"
)


def _number(value: object) -> float | None:
    try:
        if value in ("", None, "#N/A"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _previous_month(value: datetime) -> str:
    year = value.year if value.month > 1 else value.year - 1
    month = value.month - 1 if value.month > 1 else 12
    return f"{year:04d}-{month:02d}"


def _parse_cleveland(payload: list[dict]) -> list[dict]:
    output = []
    for item in payload:
        target = str(item.get("chart", {}).get("subcaption") or "")
        try:
            year, month = (int(value) for value in target.split("-", 1))
        except (TypeError, ValueError):
            continue
        series = {
            row["seriesname"]: [
                _number(value.get("value"))
                for value in row.get("data", [])
            ]
            for row in item.get("dataset", [])
        }
        actual_values = series.get("Actual CPI Inflation", [])
        actual_index = next(
            (
                index
                for index, value in enumerate(actual_values)
                if value is not None
            ),
            None,
        )
        cutoff = actual_index if actual_index is not None else len(actual_values)

        def last_before(name: str) -> float | None:
            values = [
                value
                for value in series.get(name, [])[:cutoff]
                if value is not None
            ]
            return values[-1] if values else None

        headline = last_before("CPI Inflation")
        core = last_before("Core CPI Inflation")
        if headline is None and core is None:
            continue
        output.append(
            {
                "target_month": f"{year:04d}-{month:02d}",
                "headline_cpi_nowcast": headline,
                "core_cpi_nowcast": core,
                "actual_headline_cpi": (
                    actual_values[actual_index]
                    if actual_index is not None
                    else None
                ),
                "actual_core_cpi": (
                    series.get("Actual Core CPI Inflation", [])[actual_index]
                    if actual_index is not None
                    and actual_index
                    < len(series.get("Actual Core CPI Inflation", []))
                    else None
                ),
            }
        )
    return output


def _parse_atlanta(content: bytes) -> list[dict]:
    workbook = openpyxl.load_workbook(
        io.BytesIO(content),
        read_only=True,
        data_only=True,
    )
    sheet = workbook["TrackRecord"]
    output = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        quarter, forecast, actual, release = row[:4]
        if (
            not isinstance(release, datetime)
            or _number(forecast) is None
        ):
            continue
        output.append(
            {
                "release_date": release.date().isoformat(),
                "quarter": (
                    quarter.date().isoformat()
                    if isinstance(quarter, datetime)
                    else str(quarter)
                ),
                "final_gdp_nowcast": _number(forecast),
                "advance_gdp_actual": _number(actual),
            }
        )
    return sorted(output, key=lambda row: row["release_date"])


def refresh_official_nowcasts() -> dict:
    cleveland = requests.get(CLEVELAND_URL, timeout=60)
    cleveland.raise_for_status()
    atlanta = requests.get(ATLANTA_URL, timeout=90)
    atlanta.raise_for_status()
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "cleveland_fed": CLEVELAND_URL,
            "atlanta_fed": ATLANTA_URL,
        },
        "cpi": _parse_cleveland(cleveland.json()),
        "gdp": _parse_atlanta(atlanta.content),
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


class OfficialNowcastStore:
    def __init__(self, refresh: bool = False) -> None:
        if refresh or not CACHE_PATH.exists():
            try:
                self.payload = refresh_official_nowcasts()
            except (OSError, requests.RequestException, ValueError):
                self.payload = {}
        else:
            self.payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    def context(self, event: str, release_utc: datetime) -> dict | None:
        event = event.upper()
        if event == "CPI":
            target = _previous_month(release_utc)
            records = self.payload.get("cpi", [])
            current = next(
                (
                    row
                    for row in records
                    if row["target_month"] == target
                ),
                None,
            )
            if current is None:
                return None
            earlier = [
                row
                for row in records
                if row["target_month"] < target
                and row.get("actual_headline_cpi") is not None
            ]
            prior = earlier[-1] if earlier else None
            prior_errors = [
                row["actual_headline_cpi"] - row["headline_cpi_nowcast"]
                for row in earlier[-3:]
                if row.get("headline_cpi_nowcast") is not None
            ]
            return {
                "provider": "Federal Reserve Bank of Cleveland",
                "target_month": target,
                "headline_cpi_nowcast": current.get(
                    "headline_cpi_nowcast"
                ),
                "core_cpi_nowcast": current.get("core_cpi_nowcast"),
                "previous_actual_headline_cpi": (
                    prior.get("actual_headline_cpi") if prior else None
                ),
                "prior_three_mean_nowcast_error": (
                    sum(prior_errors) / len(prior_errors)
                    if prior_errors
                    else None
                ),
                "decision_weight": 0.0,
                "note": (
                    "Context only until a point-in-time consensus archive "
                    "validates the nowcast-versus-consensus signal."
                ),
            }
        if event == "GDP":
            release_date = release_utc.date().isoformat()
            records = self.payload.get("gdp", [])
            current = next(
                (
                    row
                    for row in records
                    if row["release_date"] == release_date
                ),
                None,
            )
            if current is None:
                return None
            previous = [
                row
                for row in records
                if row["release_date"] < release_date
                and row.get("advance_gdp_actual") is not None
            ]
            prior = previous[-1] if previous else None
            return {
                "provider": "Federal Reserve Bank of Atlanta GDPNow",
                "final_gdp_nowcast": current.get("final_gdp_nowcast"),
                "previous_advance_gdp_actual": (
                    prior.get("advance_gdp_actual") if prior else None
                ),
                "decision_weight": 0.0,
                "note": (
                    "Context only until a point-in-time consensus archive "
                    "validates the nowcast-versus-consensus signal."
                ),
            }
        return None


if __name__ == "__main__":
    result = refresh_official_nowcasts()
    print(
        json.dumps(
            {
                "status": "ok",
                "cpi_records": len(result["cpi"]),
                "gdp_records": len(result["gdp"]),
                "cache": str(CACHE_PATH),
            },
            indent=2,
        )
    )
