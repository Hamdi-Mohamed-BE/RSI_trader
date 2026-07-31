from __future__ import annotations

from pathlib import Path

import pytest

from lta_system.config import AppConfig
from lta_system.risk import cash_result, risk_cash


def test_requested_risk_is_2_5_percent() -> None:
    assert risk_cash(10_000, 2.5) == 250
    pnl, balance = cash_result(10_000, 2.5, -1)
    assert pnl == -250
    assert balance == 9_750


def test_config_refuses_more_than_2_5_percent() -> None:
    config = AppConfig(project_dir=Path("."), risk_pct=3.0)
    with pytest.raises(ValueError):
        config.validate()

