from datetime import date, datetime, time, timezone

import pandas as pd

from amd_bot.config import Config
from amd_bot.config import load_config
from amd_bot.engine import combine, regime_states, resample_ohlc


def test_combine_uses_utc() -> None:
    value = combine(date(2026, 7, 30), time(13, 30))
    assert value == datetime(2026, 7, 30, 13, 30, tzinfo=timezone.utc)


def test_resample_ohlc() -> None:
    frame = pd.DataFrame(
        {
            "time": pd.date_range(
                "2026-07-30T13:30:00Z", periods=5, freq="min"
            ),
            "open": [1, 2, 3, 4, 5],
            "high": [2, 3, 4, 5, 6],
            "low": [0, 1, 2, 3, 4],
            "close": [1.5, 2.5, 3.5, 4.5, 5.5],
            "spread": [1, 1, 1, 1, 1],
            "tick_volume": [2, 2, 2, 2, 2],
        }
    )
    result = resample_ohlc(frame, "5min")
    assert len(result) == 1
    assert result.iloc[0]["high"] == 6
    assert result.iloc[0]["low"] == 0


def test_regime_state_uses_only_prior_days() -> None:
    config = load_config()
    rows: list[dict[str, object]] = []
    days = pd.date_range("2026-01-01", periods=40, freq="D", tz="UTC")
    for day in days:
        for minute in range(24 * 60):
            timestamp = day + pd.Timedelta(minutes=minute)
            price = 100.0 + minute / 10_000
            rows.append(
                {
                    "time": timestamp,
                    "open": price,
                    "high": price + 0.5,
                    "low": price - 0.5,
                    "close": price,
                    "spread": 1,
                    "tick_volume": 1,
                }
            )
    states = regime_states(pd.DataFrame(rows), config)
    assert states[days[-1].date()].ready
