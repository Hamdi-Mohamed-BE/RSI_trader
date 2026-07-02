from typing import Literal

from pydantic import BaseModel, Field, field_validator


SYMBOLS = ("BTCUSD", "ETHUSD", "XAUUSD", "XAGUSD", "US30", "US100")


class SymbolConfig(BaseModel):
    enabled: bool = True
    provider_symbol: str
    mt5_symbol: str = ""
    reward_risk: float = Field(ge=0.5, le=10.0)
    spread_bps: float = Field(ge=0.0, le=100.0)
    slippage_bps: float = Field(ge=0.0, le=100.0)
    atr_stop_multiplier: float = Field(ge=0.5, le=8.0)
    min_stop_atr: float = Field(ge=0.25, le=5.0)
    tick_size: float = Field(gt=0.0)
    minimum_score: float | None = Field(default=None, ge=0.0, le=100.0)
    sessions: list[Literal["ASIA", "LONDON", "NEW_YORK"]] | None = None


def default_symbols() -> dict[str, SymbolConfig]:
    return {
        "BTCUSD": SymbolConfig(
            enabled=False, provider_symbol="BTC.v.0", mt5_symbol="BTCUSD", reward_risk=3.0, spread_bps=3.0,
            slippage_bps=1.5, atr_stop_multiplier=1.8, min_stop_atr=1.1, tick_size=5.0,
        ),
        "ETHUSD": SymbolConfig(
            enabled=False, provider_symbol="ETH.v.0", mt5_symbol="ETHUSD", reward_risk=3.0, spread_bps=4.0,
            slippage_bps=2.0, atr_stop_multiplier=1.9, min_stop_atr=1.1, tick_size=0.5,
        ),
        "XAUUSD": SymbolConfig(
            provider_symbol="GC.v.0", mt5_symbol="XAUUSDm", reward_risk=3.0, spread_bps=1.2,
            slippage_bps=0.8, atr_stop_multiplier=1.6, min_stop_atr=1.0, tick_size=0.1,
        ),
        "XAGUSD": SymbolConfig(
            enabled=False, provider_symbol="SI.v.0", mt5_symbol="XAGUSD", reward_risk=2.5, spread_bps=2.5,
            slippage_bps=1.2, atr_stop_multiplier=1.7, min_stop_atr=1.0, tick_size=0.005,
        ),
        "US30": SymbolConfig(
            enabled=False, provider_symbol="YM.v.0", mt5_symbol="US30", reward_risk=2.5, spread_bps=1.0,
            slippage_bps=0.8, atr_stop_multiplier=1.7, min_stop_atr=1.0, tick_size=1.0,
        ),
        "US100": SymbolConfig(
            enabled=False, provider_symbol="NQ.v.0", mt5_symbol="US100", reward_risk=3.0, spread_bps=1.0,
            slippage_bps=0.8, atr_stop_multiplier=1.7, min_stop_atr=1.0, tick_size=0.25,
        ),
    }


class RuntimeConfig(BaseModel):
    symbols: dict[str, SymbolConfig] = Field(default_factory=default_symbols)
    dataset: str = "GLBX.MDP3"
    signal_timeframe_minutes: int = Field(default=15, ge=1, le=240)
    profile_lookback_days: int = Field(default=20, ge=2, le=90)
    profile_bins: int = Field(default=48, ge=12, le=200)
    value_area_percent: float = Field(default=0.70, ge=0.5, le=0.95)
    minimum_score: float = Field(default=78.0, ge=0.0, le=100.0)
    risk_percent: float = Field(default=5.0, ge=0.1, le=25.0)
    max_trades_per_day: int = Field(default=3, ge=1, le=20)
    pending_expiry_bars: int = Field(default=8, ge=1, le=100)
    orderbook_imbalance_threshold: float = Field(default=0.12, ge=0.0, le=1.0)
    volume_expansion_ratio: float = Field(default=1.20, ge=0.5, le=5.0)
    trail_enabled: bool = True
    trail_step_r: float = Field(default=1.0, ge=0.25, le=3.0)
    partial_take_profit_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    sessions: list[Literal["ASIA", "LONDON", "NEW_YORK"]] = Field(
        default_factory=lambda: ["ASIA", "LONDON", "NEW_YORK"]
    )
    weekdays: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
    scan_interval_seconds: int = Field(default=60, ge=15, le=3600)
    execution_mode: Literal["paper", "signals_only", "mt5"] = "paper"
    account_balance: float = Field(default=300.0, ge=1.0)
    use_trade_tape_profile: bool = True
    use_order_book: bool = True
    optimize_objective: Literal["growth", "balanced", "drawdown"] = "balanced"
    max_data_cost_usd: float = Field(default=1.0, ge=0.0, le=25.0)
    mt5_live_orders_enabled: bool = False
    mt5_magic_number: int = Field(default=26070201, ge=1)
    max_basis_bps: float = Field(default=150.0, ge=1.0, le=1000.0)

    @field_validator("symbols")
    @classmethod
    def supported_symbols_only(cls, value: dict[str, SymbolConfig]) -> dict[str, SymbolConfig]:
        unknown = set(value) - set(SYMBOLS)
        if unknown:
            raise ValueError(f"Unsupported symbols: {', '.join(sorted(unknown))}")
        return value


class ConfigEnvelope(BaseModel):
    config: RuntimeConfig
    databento_key_configured: bool


class BacktestRequest(BaseModel):
    period: Literal["1m", "6m", "custom"] = "1m"
    start_date: str | None = None
    end_date: str | None = None
    starting_balance: float = Field(default=300.0, ge=1.0)
    optimize: bool = False
    symbols: list[str] = Field(default_factory=lambda: list(SYMBOLS))

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, value: list[str]) -> list[str]:
        invalid = set(value) - set(SYMBOLS)
        if invalid:
            raise ValueError(f"Unsupported symbols: {', '.join(sorted(invalid))}")
        return value
