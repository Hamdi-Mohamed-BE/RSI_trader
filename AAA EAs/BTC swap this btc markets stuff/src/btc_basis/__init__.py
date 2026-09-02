"""BTC spot–CME futures basis research package."""

from .strategy import StrategyConfig, backtest, detect_reopen_events, performance_metrics

__all__ = ["StrategyConfig", "backtest", "detect_reopen_events", "performance_metrics"]

