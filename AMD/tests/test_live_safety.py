from dataclasses import replace

import pytest

from amd_bot.config import load_config
from amd_bot.live import required_live_history_days, validate_execution_flags


def test_failed_model_cannot_be_enabled_for_live_execution() -> None:
    config = replace(
        load_config(),
        enable_trading=True,
        dry_run=False,
        model_approved=False,
    )
    with pytest.raises(RuntimeError, match="out-of-sample"):
        validate_execution_flags(config)


def test_failed_model_can_still_run_in_dry_run() -> None:
    config = replace(
        load_config(),
        enable_trading=False,
        dry_run=True,
        model_approved=False,
    )
    validate_execution_flags(config)


def test_live_history_warms_atr_and_relative_atr_baseline() -> None:
    config = replace(
        load_config(),
        regime_filter_enabled=True,
        regime_atr_days=5,
        regime_atr_median_days=30,
        regime_asia_median_days=20,
    )
    assert required_live_history_days(config) >= 70


def test_disabled_regime_filter_uses_small_history_window() -> None:
    config = replace(load_config(), regime_filter_enabled=False)
    assert required_live_history_days(config) == 14
