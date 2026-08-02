from datetime import datetime, timezone

import pytest

from asia_breakout import mt5_data
from asia_breakout.mt5_data import MarketDataUnavailable


def test_fetch_m1_reports_closed_market_without_mt5_success_error(monkeypatch) -> None:
    monkeypatch.setattr(mt5_data.mt5, "symbol_select", lambda *_: True)
    monkeypatch.setattr(mt5_data.mt5, "copy_rates_range", lambda *_: None)
    monkeypatch.setattr(mt5_data.time, "sleep", lambda *_: None)

    with pytest.raises(MarketDataUnavailable, match="market may be closed"):
        mt5_data.fetch_m1(
            "XAUUSDm",
            datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 8, 2, 3, 45, tzinfo=timezone.utc),
        )
