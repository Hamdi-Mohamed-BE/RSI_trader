from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from news_core import ROOT


STORE_DIR = ROOT / "data" / "point-in-time"
MACRO_DIR = STORE_DIR / "macro"
MARKET_DIR = STORE_DIR / "market"


def _utc(value: str | datetime) -> datetime:
    parsed = (
        value
        if isinstance(value, datetime)
        else datetime.fromisoformat(value.replace("Z", "+00:00"))
    )
    if parsed.tzinfo is None:
        raise ValueError("Point-in-time records must include a timezone.")
    return parsed.astimezone(timezone.utc)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _write_record(directory: Path, record: dict[str, Any]) -> Path:
    observed = _utc(record["observed_at_utc"])
    release = _utc(record["release_utc"])
    if observed >= release:
        raise ValueError("Pre-release context must be observed before the release.")
    directory.mkdir(parents=True, exist_ok=True)
    filename = (
        f"{release.strftime('%Y%m%dT%H%M%SZ')}-"
        f"{observed.strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    path = directory / filename
    path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    return path


def save_macro_snapshot(
    *,
    event: str,
    release_utc: str | datetime,
    observed_at_utc: str | datetime,
    forecast: float | str | None,
    previous: float | str | None,
    revised_previous: float | str | None = None,
    forecast_high: float | str | None = None,
    forecast_low: float | str | None = None,
    source: str,
    source_url: str | None = None,
) -> Path:
    release = _utc(release_utc)
    observed = _utc(observed_at_utc)
    record = {
        "schema_version": 1,
        "kind": "macro_consensus",
        "event": event.upper(),
        "release_utc": release.isoformat(),
        "observed_at_utc": observed.isoformat(),
        "forecast": forecast,
        "previous": previous,
        "revised_previous": revised_previous,
        "forecast_high": forecast_high,
        "forecast_low": forecast_low,
        "source": source,
        "source_url": source_url,
    }
    return _write_record(MACRO_DIR / _slug(event), record)


def save_market_snapshot(
    *,
    release_utc: str | datetime,
    observed_at_utc: str | datetime,
    instruments: dict[str, dict[str, float | int | None]],
    source: str,
) -> Path:
    release = _utc(release_utc)
    observed = _utc(observed_at_utc)
    record = {
        "schema_version": 1,
        "kind": "cross_market",
        "release_utc": release.isoformat(),
        "observed_at_utc": observed.isoformat(),
        "instruments": instruments,
        "source": source,
    }
    return _write_record(MARKET_DIR, record)


def latest_before(
    directory: Path,
    release_utc: str | datetime,
    cutoff_utc: str | datetime,
) -> dict[str, Any] | None:
    release = _utc(release_utc)
    cutoff = _utc(cutoff_utc)
    candidates: list[tuple[datetime, dict[str, Any]]] = []
    if not directory.exists():
        return None
    for path in directory.glob(f"{release.strftime('%Y%m%dT%H%M%SZ')}-*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        observed = _utc(payload["observed_at_utc"])
        if observed <= cutoff < release:
            candidates.append((observed, payload))
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def context_for_prediction(
    event: str,
    release_utc: str | datetime,
    cutoff_utc: str | datetime,
) -> dict[str, Any]:
    return {
        "macro": latest_before(
            MACRO_DIR / _slug(event),
            release_utc,
            cutoff_utc,
        ),
        "cross_market": latest_before(
            MARKET_DIR,
            release_utc,
            cutoff_utc,
        ),
    }
