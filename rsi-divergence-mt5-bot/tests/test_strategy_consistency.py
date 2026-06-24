from rsi_divergence_bot.config import AppConfig, update_bot_strategy
from rsi_divergence_bot.strategy_modes import (
    canonical_strategy,
    is_full_position_strategy,
    is_partial_strategy,
    tp_protection_enabled,
)


def minimal_config(strategy: str = "signal_with_tp_protection") -> AppConfig:
    return AppConfig.model_validate(
        {
            "bot": {"strategy": strategy},
            "symbols": [{"symbol": "EURUSD", "name": "Euro / US Dollar", "lot_per_leg": 0.01}],
        }
    )


def test_legacy_partial_strategies_load_as_split_aliases():
    protected = minimal_config("signal_partial_with_tp_protection")
    unprotected = minimal_config("signal_partial_no_tp_protection")

    assert protected.bot.strategy == "signal_with_tp_protection"
    assert unprotected.bot.strategy == "signal_no_tp_protection"


def test_strategy_aliases_never_enable_partial_execution():
    assert canonical_strategy("signal_partial_with_tp_protection") == "signal_with_tp_protection"
    assert canonical_strategy("signal_partial_no_tp_protection") == "signal_no_tp_protection"
    assert is_partial_strategy("signal_partial_with_tp_protection") is False
    assert is_partial_strategy("signal_partial_no_tp_protection") is False
    assert tp_protection_enabled("signal_partial_with_tp_protection") is True
    assert tp_protection_enabled("signal_partial_no_tp_protection") is False


def test_update_bot_strategy_persists_canonical_strategy():
    config = minimal_config()

    update_bot_strategy(config, "signal_partial_no_tp_protection")

    assert config.bot.strategy == "signal_no_tp_protection"


def test_full_position_strategies_are_canonical():
    no_protect = minimal_config("signal_full_no_tp_protection")
    with_protect = minimal_config("signal_full_with_tp_protection")

    assert no_protect.bot.strategy == "signal_full_no_tp_protection"
    assert with_protect.bot.strategy == "signal_full_with_tp_protection"
    assert is_full_position_strategy("signal_full_no_tp_protection") is True
    assert is_full_position_strategy("signal_full_with_tp_protection") is True
    assert tp_protection_enabled("signal_full_no_tp_protection") is False
    assert tp_protection_enabled("signal_full_with_tp_protection") is True
