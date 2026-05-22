from __future__ import annotations

from .config import StrategyMode

PARTIAL_STRATEGIES = {
    "signal_partial_no_tp_protection",
    "signal_partial_with_tp_protection",
}

TP_PROTECTION_STRATEGIES = {
    "signal_with_tp_protection",
    "signal_partial_with_tp_protection",
}


def is_partial_strategy(strategy: StrategyMode | str) -> bool:
    return str(strategy) in PARTIAL_STRATEGIES


def tp_protection_enabled(strategy: StrategyMode | str) -> bool:
    return str(strategy) in TP_PROTECTION_STRATEGIES
