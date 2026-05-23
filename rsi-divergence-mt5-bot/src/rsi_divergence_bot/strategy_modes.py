from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import StrategyMode


CANONICAL_STRATEGIES = {
    "signal_no_tp_protection",
    "signal_with_tp_protection",
    "box_theory",
}

LEGACY_STRATEGY_ALIASES = {
    "signal_partial_no_tp_protection": "signal_no_tp_protection",
    "signal_partial_with_tp_protection": "signal_with_tp_protection",
}

TP_PROTECTION_STRATEGIES = {
    "signal_with_tp_protection",
}


def canonical_strategy(strategy: "StrategyMode | str") -> str:
    value = str(strategy)
    return LEGACY_STRATEGY_ALIASES.get(value, value)


def is_partial_strategy(strategy: "StrategyMode | str") -> bool:
    return False


def tp_protection_enabled(strategy: "StrategyMode | str") -> bool:
    return canonical_strategy(strategy) in TP_PROTECTION_STRATEGIES


def is_box_theory_strategy(strategy: "StrategyMode | str") -> bool:
    return canonical_strategy(strategy) == "box_theory"


def is_single_leg_strategy(strategy: "StrategyMode | str") -> bool:
    return is_box_theory_strategy(strategy)


def closes_opposite_before_entry(strategy: "StrategyMode | str") -> bool:
    return is_box_theory_strategy(strategy)
