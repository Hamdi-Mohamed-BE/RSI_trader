from __future__ import annotations

import pandas as pd

from .config import AppConfig, RiskConfig, SymbolConfig
from .strategy import Signal
from . import forex_trade
from . import silver_optimized
from . import strategy as rsi_strategy


def generate_signals(
    config: AppConfig,
    df: pd.DataFrame,
    symbol_cfg: SymbolConfig,
    risk_cfg: RiskConfig | None = None,
) -> list[Signal]:
    if config.bot.signal_algorithm == "forex_trade":
        return forex_trade.generate_signals(df, symbol_cfg, risk_cfg, config.bot.forex_trade)
    if config.bot.signal_algorithm == "silver_optimized":
        return silver_optimized.generate_signals(df, symbol_cfg, risk_cfg, config.bot.silver_optimized)
    return rsi_strategy.generate_signals(df, symbol_cfg, risk_cfg)


def latest_closed_signal(
    config: AppConfig,
    df: pd.DataFrame,
    symbol_cfg: SymbolConfig,
    risk_cfg: RiskConfig,
) -> Signal | None:
    if config.bot.signal_algorithm == "forex_trade":
        return forex_trade.latest_closed_signal(df, symbol_cfg, risk_cfg, config.bot.forex_trade)
    if config.bot.signal_algorithm == "silver_optimized":
        return silver_optimized.latest_closed_signal(df, symbol_cfg, risk_cfg, config.bot.silver_optimized)
    return rsi_strategy.latest_closed_signal(df, symbol_cfg, risk_cfg)


def signal_at_closed_index(
    config: AppConfig,
    df: pd.DataFrame,
    end_index: int,
    symbol_cfg: SymbolConfig,
    risk_cfg: RiskConfig,
) -> Signal | None:
    if config.bot.signal_algorithm == "forex_trade":
        return forex_trade.signal_at_closed_index(
            df,
            end_index,
            symbol_cfg,
            risk_cfg,
            config.bot.forex_trade,
        )
    if config.bot.signal_algorithm == "silver_optimized":
        return silver_optimized.signal_at_closed_index(
            df,
            end_index,
            symbol_cfg,
            risk_cfg,
            config.bot.silver_optimized,
        )
    return rsi_strategy.signal_at_closed_index(df, end_index, symbol_cfg, risk_cfg)
