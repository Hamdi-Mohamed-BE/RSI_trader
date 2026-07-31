from dataclasses import replace

import pytest

from amd_bot.config import load_config
from amd_bot.live import validate_execution_flags


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
