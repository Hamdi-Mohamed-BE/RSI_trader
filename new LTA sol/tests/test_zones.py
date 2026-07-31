from __future__ import annotations

import numpy as np
import pandas as pd

from lta_system.structure import enrich_structure
from lta_system.zones import build_zone_timeline


def _bars(periods: int = 80) -> pd.DataFrame:
    time = pd.date_range("2026-01-01", periods=periods, freq="1h", tz="UTC")
    close = 100 + np.sin(np.arange(periods) / 4) * 2
    frame = pd.DataFrame(
        {
            "time": time,
            "open": close - 0.1,
            "high": close + 0.4,
            "low": close - 0.4,
            "close": close,
            "volume": 100,
            "spread": 2,
            "session_day": time.date,
            "session_week": "2026-W01",
            "ny_hour": time.hour,
        }
    )
    frame.loc[40:42, ["open", "high", "low", "close"]] = [
        [100.0, 100.3, 99.8, 100.1],
        [100.1, 100.4, 99.9, 100.0],
        [100.0, 100.2, 99.8, 100.1],
    ]
    frame.loc[43, ["open", "high", "low", "close"]] = [100.1, 104.5, 100.0, 104.2]
    return enrich_structure(frame)


def test_zone_timeline_has_no_future_dependency() -> None:
    frame = _bars()
    prefix = frame.iloc[:60].copy()
    prefix_timeline = build_zone_timeline(prefix)
    full_timeline = build_zone_timeline(frame)
    assert prefix_timeline[55] == full_timeline[55]


def test_displacement_creates_demand_zone() -> None:
    timeline = build_zone_timeline(_bars())
    assert any(zone.kind == "demand" for zone in timeline[43])

