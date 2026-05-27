from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator

from .strategy_modes import CANONICAL_STRATEGIES, canonical_strategy
from .symbols import CRYPTO_DEFAULT_LOTS, asset_group, market_key
from .timeframes import validate_timeframe

Timeframe = Literal[
    "M1",
    "M2",
    "M3",
    "M4",
    "M5",
    "M6",
    "M10",
    "M12",
    "M15",
    "M20",
    "M30",
    "H1",
    "H2",
    "H3",
    "H4",
    "H6",
    "H8",
    "H12",
    "D1",
    "W1",
    "MN1",
]
StrategyMode = Literal[
    "signal_no_tp_protection",
    "signal_with_tp_protection",
    "signal_full_no_tp_protection",
    "signal_full_with_tp_protection",
    "signal_partial_no_tp_protection",
    "signal_partial_with_tp_protection",
]
TradeDecisionProfile = Literal["safe", "balanced", "backtest"]
Confirmation = Literal["off", "ema", "trend_guard", "rsi_extreme", "strict"]
MT5Mode = Literal["native_windows", "linux_bridge"]
MT5Transport = Literal["tcp", "stdio"]
SignalAlgorithm = Literal["rsi_divergence", "silver_optimized"]
SilverPreset = Literal["auto", "xauusd", "xagusd", "btcusd", "custom"]
SilverDirection = Literal["long_only", "short_only", "long_and_short"]


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
    broker_symbol_suffix: str = Field(
        default="-VIP",
        validation_alias=AliasChoices("broker_symbol_suffix", "RSI_BOT_BROKER_SYMBOL_SUFFIX"),
    )

    @field_validator("broker_symbol_suffix", mode="before")
    @classmethod
    def normalize_broker_symbol_suffix(cls, value: object) -> str:
        from .symbols import DEFAULT_BROKER_SYMBOL_SUFFIX, normalize_broker_symbol_suffix

        if value is None:
            return DEFAULT_BROKER_SYMBOL_SUFFIX
        return normalize_broker_symbol_suffix(str(value))

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


class SilverOptimizedConfig(BaseModel):
    preset: SilverPreset = "auto"
    trade_direction: SilverDirection = "long_and_short"
    htf_timeframe: str = "D1"
    use_vol_filter: bool = True
    use_time_filter: bool = False
    custom_fast_len: int = Field(default=21, ge=2)
    custom_slow_len: int = Field(default=55, ge=3)
    custom_htf_len: int = Field(default=200, ge=20)
    custom_rsi_len: int = Field(default=14, ge=2)
    custom_adx_min: float = Field(default=18.0, ge=1.0)
    custom_atr_len: int = Field(default=14, ge=2)
    custom_stop_atr: float = Field(default=2.2, gt=0)
    custom_tp_atr: float = Field(default=3.5, gt=0)
    custom_trail_atr: float = Field(default=1.6, gt=0)


class BotRuntimeConfig(BaseModel):
    dry_run: bool = True
    auto_start: bool = True
    poll_seconds: int = 15
    magic: int = 260521
    strategy: StrategyMode = "signal_with_tp_protection"
    signal_algorithm: SignalAlgorithm = "rsi_divergence"
    silver_optimized: SilverOptimizedConfig = Field(default_factory=SilverOptimizedConfig)
    trade_decision_profile: TradeDecisionProfile = "safe"
    max_concurrent_setups: int = 3
    state_file: str = "runtime/state.json"
    log_file: str = "runtime/bot.log"

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_strategy(cls, data):
        if isinstance(data, dict) and "strategy" in data:
            data = dict(data)
            data["strategy"] = canonical_strategy(data["strategy"])
        return data

    @model_validator(mode="after")
    def validate_canonical_strategy(self) -> "BotRuntimeConfig":
        self.strategy = canonical_strategy(self.strategy)  # type: ignore[assignment]
        if self.strategy not in CANONICAL_STRATEGIES:
            raise ValueError(f"Unknown bot strategy: {self.strategy}")
        return self


class RiskConfig(BaseModel):
    max_setup_risk_usd: float | None = 180.0
    default_forex_lot: float = Field(default=0.25, gt=0)
    use_daily_loss_guard: bool = True
    max_daily_loss_pct: float | None = Field(default=15.0, ge=0)
    max_extension_atr: float = 1.8
    max_spread_atr: float = 0.35
    max_live_entry_drift_risk: float | None = Field(default=0.35, ge=0)
    min_tp1_spread_multiple: float = Field(default=1.5, ge=0)
    use_spread_filter: bool | None = None
    use_tp1_spread_filter: bool | None = None
    use_risk_filter: bool | None = None
    use_existing_position_filter: bool | None = None
    use_max_setups_filter: bool | None = None
    skip_if_symbol_has_position: bool = True

    def daily_loss_guard_active(self) -> bool:
        return (
            self.use_daily_loss_guard
            and self.max_daily_loss_pct is not None
            and self.max_daily_loss_pct > 0
        )

    def effective_daily_loss_pct(self) -> float | None:
        if not self.daily_loss_guard_active():
            return None
        return self.max_daily_loss_pct


class WebConfig(BaseModel):
    host: str = "0.0.0.0"
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
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
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
    optimized_timeframe: Timeframe | None = None
    lot_per_leg: float = Field(gt=0)
    max_setup_risk_usd: float | None = None
    pivot_len: int = Field(default=3, ge=2, le=20)
    sl_atr_mult: float = Field(default=1.5, gt=0)
    rr: list[float] = Field(default_factory=lambda: [1.0, 1.5, 2.0])
    confirmation: Confirmation = "ema"
    sessions: list[str] = Field(default_factory=list)
    max_wait_bars: int = Field(default=8, ge=1, le=50)

    @model_validator(mode="after")
    def validate_rr_levels(self) -> "SymbolConfig":
        if not self.rr:
            raise ValueError(f"{self.symbol} must define at least one risk-reward TP level")
        if any(level <= 0 for level in self.rr):
            raise ValueError(f"{self.symbol} RR levels must be positive numbers")
        self.rr = sorted(float(level) for level in self.rr)
        return self

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


def default_symbol_lot(symbol_cfg: SymbolConfig, config: AppConfig | None = None) -> float:
    key = symbol_cfg.key.upper()
    symbol = symbol_cfg.symbol.upper()
    name = symbol_cfg.name.upper()
    if key in CRYPTO_DEFAULT_LOTS:
        return CRYPTO_DEFAULT_LOTS[key]
    if key == "XAUUSD" or "GOLD" in name:
        return 0.08
    if key == "XAGUSD" or "SILVER" in name:
        return 0.01
    if "OIL" in symbol or "OIL" in name or symbol.startswith("CL"):
        return 0.01
    if config is not None:
        return config.risk.default_forex_lot
    return 0.25


def symbol_asset_group(symbol_cfg: SymbolConfig) -> str:
    return asset_group(symbol_cfg.key, symbol_cfg.name)


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return AppConfig.model_validate(raw)


def save_config(path: str | Path, config: AppConfig) -> None:
    config_path = Path(path)
    payload = config.model_dump(mode="python")
    tmp_path = config_path.with_suffix(f"{config_path.suffix}.tmp")
    tmp_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    tmp_path.replace(config_path)


def update_default_forex_lot(config: AppConfig, lot: float) -> None:
    if lot <= 0:
        raise ValueError("Default forex lot must be greater than 0")
    config.risk.default_forex_lot = lot


def broker_symbol_suffix(config: AppConfig) -> str:
    return config.mt5.broker_symbol_suffix


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


def update_symbol_timeframes(config: AppConfig, timeframes: dict[str, str]) -> list[str]:
    updated: list[str] = []
    for symbol_cfg in config.symbols:
        if symbol_cfg.symbol not in timeframes:
            continue
        try:
            timeframe = validate_timeframe(timeframes[symbol_cfg.symbol])
        except ValueError as exc:
            raise ValueError(f"Timeframe for {symbol_cfg.symbol}: {exc}") from exc
        symbol_cfg.timeframe = timeframe  # type: ignore[assignment]
        updated.append(symbol_cfg.symbol)
    return updated


def update_bot_strategy(config: AppConfig, strategy: StrategyMode) -> None:
    normalized = canonical_strategy(strategy)
    if normalized not in CANONICAL_STRATEGIES:
        raise ValueError(f"Unknown bot strategy: {strategy}")
    config.bot.strategy = normalized  # type: ignore[assignment]


def update_signal_algorithm(config: AppConfig, algorithm: SignalAlgorithm) -> None:
    if algorithm not in {"rsi_divergence", "silver_optimized"}:
        raise ValueError(f"Unknown signal algorithm: {algorithm}")
    config.bot.signal_algorithm = algorithm  # type: ignore[assignment]


def normalize_telegram_channel_url(url: str) -> str:
    raw = str(url or "").strip()
    if not raw:
        raise ValueError("Channel URL is required")
    base = "https://web.telegram.org/k/#"
    if raw.startswith("http"):
        if "#" not in raw:
            raise ValueError("Telegram Web URL must include #channel hash or @username")
        token = raw.split("#", 1)[1].lstrip("#").strip()
        if not token:
            raise ValueError("Telegram Web URL is missing channel hash")
        return f"{base}{token}"
    token = raw.lstrip("#").strip()
    if not token:
        raise ValueError("Invalid Telegram channel link")
    if not token.startswith("@") and not token.startswith("-") and not token.isdigit():
        token = f"@{token}"
    return f"{base}{token}"


def telegram_channel_key(url: str) -> str:
    return normalize_telegram_channel_url(url).casefold()


def derive_telegram_channel_name(url: str) -> str:
    normalized = normalize_telegram_channel_url(url)
    token = normalized.rsplit("#", 1)[-1]
    if token.startswith("@"):
        return token[1:]
    return f"Telegram {token}"


def find_telegram_channel(config: AppConfig, url: str) -> TelegramChannelConfig | None:
    target = telegram_channel_key(url)
    for channel in config.telegram_signals.channels:
        if telegram_channel_key(channel.url) == target:
            return channel
    return None


def add_telegram_channel(
    config: AppConfig,
    url: str,
    *,
    name: str | None = None,
    enabled: bool = True,
) -> TelegramChannelConfig:
    normalized = normalize_telegram_channel_url(url)
    if find_telegram_channel(config, normalized) is not None:
        raise ValueError("Channel already exists")
    channel = TelegramChannelConfig(
        name=(name or derive_telegram_channel_name(normalized)).strip() or derive_telegram_channel_name(normalized),
        url=normalized,
        enabled=enabled,
    )
    config.telegram_signals.channels.append(channel)
    return channel


def update_telegram_ignore_open_trades(config: AppConfig, *, ignore_open: bool) -> None:
    config.telegram_signals.ignore_open_symbol_trades = ignore_open


def update_telegram_channel(
    config: AppConfig,
    url: str,
    *,
    name: str | None = None,
    enabled: bool | None = None,
) -> TelegramChannelConfig:
    channel = find_telegram_channel(config, url)
    if channel is None:
        raise ValueError("Channel not found")
    if name is not None:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Channel name cannot be empty")
        channel.name = cleaned
    if enabled is not None:
        channel.enabled = enabled
    return channel


def remove_telegram_channel(config: AppConfig, url: str) -> TelegramChannelConfig:
    target = telegram_channel_key(url)
    removed: TelegramChannelConfig | None = None
    kept: list[TelegramChannelConfig] = []
    for channel in config.telegram_signals.channels:
        if telegram_channel_key(channel.url) == target:
            removed = channel
            continue
        kept.append(channel)
    if removed is None:
        raise ValueError("Channel not found")
    config.telegram_signals.channels = kept
    return removed
