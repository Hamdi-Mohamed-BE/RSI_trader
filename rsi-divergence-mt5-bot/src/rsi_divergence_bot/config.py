from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from .symbols import market_key

Timeframe = Literal["M1", "M5", "M15", "M30", "H1"]
StrategyMode = Literal["signal_no_tp_protection", "signal_with_tp_protection"]
TradeDecisionProfile = Literal["safe", "balanced", "backtest"]
Confirmation = Literal["off", "ema", "trend_guard", "rsi_extreme", "strict"]
MT5Mode = Literal["native_windows", "linux_bridge"]
MT5Transport = Literal["tcp", "stdio"]


class MT5Config(BaseModel):
    mode: MT5Mode = "native_windows"
    path: str = "C:/Program Files/MetaTrader 5/terminal64.exe"
    login: int | None = None
    password: str | None = None
    server: str | None = None
    host: str = "localhost"
    port: int = 18812
    transport: MT5Transport = "tcp"
    timeout: int = 300

    @model_validator(mode="after")
    def validate_linux_bridge(self) -> "MT5Config":
        if self.mode == "linux_bridge":
            missing = [
                name
                for name in ("login", "password", "server")
                if getattr(self, name) in (None, "")
            ]
            if missing:
                raise ValueError(f"linux_bridge mt5 config is missing: {', '.join(missing)}")
            if self.transport != "tcp":
                raise ValueError("linux_bridge currently supports transport: tcp")
        return self


class BotRuntimeConfig(BaseModel):
    dry_run: bool = True
    auto_start: bool = True
    poll_seconds: int = 15
    magic: int = 260521
    strategy: StrategyMode = "signal_with_tp_protection"
    trade_decision_profile: TradeDecisionProfile = "safe"
    max_concurrent_setups: int = 3
    state_file: str = "runtime/state.json"
    log_file: str = "runtime/bot.log"


class RiskConfig(BaseModel):
    max_setup_risk_usd: float | None = 180.0
    max_daily_loss_pct: float | None = Field(default=15.0, ge=0)
    max_extension_atr: float = 1.8
    max_spread_atr: float = 0.35
    min_tp1_spread_multiple: float = Field(default=1.5, ge=0)
    use_spread_filter: bool | None = None
    use_tp1_spread_filter: bool | None = None
    use_risk_filter: bool | None = None
    use_existing_position_filter: bool | None = None
    use_max_setups_filter: bool | None = None
    skip_if_symbol_has_position: bool = True


class WebConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8787


class AuthConfig(BaseModel):
    username: str = "admin"
    password: str = "admin"
    cookie_name: str = "rsi_bot_auth"


class TelegramChannelConfig(BaseModel):
    name: str
    url: str
    enabled: bool = True


class TelegramSignalsConfig(BaseModel):
    enabled: bool = False
    poll_seconds: int = Field(default=5, ge=2)
    telegram_url: str = "https://web.telegram.org/k/"
    channels: list[TelegramChannelConfig] = Field(default_factory=list)
    browser_user_data_dir: str = "runtime/telegram-browser"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"
    ignore_open_symbol_trades: bool = True
    max_tps: int = Field(default=5, ge=1, le=8)
    default_lot: float | None = None
    max_message_age_seconds: int = Field(default=300, ge=30, le=3600)


class SymbolConfig(BaseModel):
    symbol: str
    name: str
    market_key_override: str | None = None
    enabled: bool = True
    timeframe: Timeframe = "M5"
    lot_per_leg: float = Field(gt=0)
    max_setup_risk_usd: float | None = None
    pivot_len: int = Field(default=3, ge=2, le=20)
    sl_atr_mult: float = Field(default=1.5, gt=0)
    rr: list[float] = Field(default_factory=lambda: [1.0, 1.5, 2.0])
    confirmation: Confirmation = "ema"
    sessions: list[str] = Field(default_factory=list)
    max_wait_bars: int = Field(default=8, ge=1, le=50)

    @property
    def key(self) -> str:
        return market_key(self.market_key_override or self.symbol)


class AppConfig(BaseModel):
    mt5: MT5Config = Field(default_factory=MT5Config)
    bot: BotRuntimeConfig = Field(default_factory=BotRuntimeConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    telegram_signals: TelegramSignalsConfig = Field(default_factory=TelegramSignalsConfig)
    symbols: list[SymbolConfig]

    @property
    def enabled_symbols(self) -> list[SymbolConfig]:
        return [item for item in self.symbols if item.enabled]


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return AppConfig.model_validate(raw)


def save_config(path: str | Path, config: AppConfig) -> None:
    config_path = Path(path)
    payload = config.model_dump(mode="python")
    config_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def update_symbol_lots(config: AppConfig, lots: dict[str, float]) -> list[str]:
    updated: list[str] = []
    for symbol_cfg in config.symbols:
        if symbol_cfg.symbol not in lots:
            continue
        lot = lots[symbol_cfg.symbol]
        if lot <= 0:
            raise ValueError(f"Lot for {symbol_cfg.symbol} must be greater than 0")
        symbol_cfg.lot_per_leg = lot
        updated.append(symbol_cfg.symbol)
    return updated


def update_symbol_enabled(config: AppConfig, enabled: dict[str, bool]) -> list[str]:
    updated: list[str] = []
    for symbol_cfg in config.symbols:
        if symbol_cfg.symbol not in enabled:
            continue
        symbol_cfg.enabled = enabled[symbol_cfg.symbol]
        updated.append(symbol_cfg.symbol)
    return updated


def update_bot_strategy(config: AppConfig, strategy: StrategyMode) -> None:
    config.bot.strategy = strategy
