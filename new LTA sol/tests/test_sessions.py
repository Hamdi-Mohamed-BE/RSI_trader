from __future__ import annotations

import pandas as pd

from lta_system.sessions import with_session_keys


def test_futures_day_rolls_at_1800_new_york() -> None:
    frame = pd.DataFrame(
        {
            "time": pd.to_datetime(
                ["2026-07-01T21:59:00Z", "2026-07-01T22:01:00Z"],
                utc=True,
            ),
            "open": [1, 1],
            "high": [1, 1],
            "low": [1, 1],
            "close": [1, 1],
        }
    )
    keyed = with_session_keys(frame)
    assert keyed.loc[0, "session_day"] != keyed.loc[1, "session_day"]

