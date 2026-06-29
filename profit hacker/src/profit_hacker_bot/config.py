from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _string(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _optional_int(name: str) -> int | None:
    value = _string(name)
    return int(value) if value else None


def _int(name: str, default: int) -> int:
    value = _string(name)
    return int(value) if value else default


def _float(name: str, default: float) -> float:
    value = _string(name)
    return float(value) if value else default


def _bool(name: str, default: bool) -> bool:
    value = _string(name)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "y", "on"}


def _channel(value: str) -> int | str:
    if value.lstrip("-").isdigit():
        return int(value)
    return value


def _symbol_map(value: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not value:
        return mapping
    chunks = value.replace(";", ",").split(",")
    for chunk in chunks:
        if not chunk.strip() or "=" not in chunk:
            continue
        left, right = chunk.split("=", 1)
        left = left.strip().upper()
        right = right.strip()
        if left and right:
            mapping[left] = right
    return mapping


@dataclass(frozen=True)
class Settings:
    telegram_api_id: int | None
    telegram_api_hash: str
    telegram_phone: str
    telegram_session: str
    telegram_channel: int | str
    recent_message_log_count: int
    rescan_message_count: int
    rescan_max_age_seconds: int
    mt5_path: str
    mt5_login: int | None
    mt5_password: str
    mt5_server: str
    dry_run: bool
    risk_percent: float
    max_signal_age_seconds: int
    pending_order_ttl_seconds: int
    order_mode: str
    symbol_map: dict[str, str]
    auto_discover_symbols: bool
    max_entry_drift_points: float
    break_even_enabled: bool
    break_even_offset_points: float
    mt5_magic: int
    trade_comment_prefix: str
    watch_interval_seconds: float
    state_db: Path
    log_level: str

    def resolve_symbol(self, telegram_symbol: str) -> str:
        symbol = telegram_symbol.upper()
        return self.symbol_map.get(symbol, symbol)

    def validate(self) -> list[str]:
        missing: list[str] = []
        if not self.telegram_api_id:
            missing.append("TELEGRAM_API_ID")
        if not self.telegram_api_hash:
            missing.append("TELEGRAM_API_HASH")
        if not self.telegram_channel:
            missing.append("TELEGRAM_CHANNEL")
        if not self.dry_run and not self.mt5_path:
            missing.append("MT5_PATH")
        return missing


def load_settings(env_path: str | Path | None = None) -> Settings:
    if env_path:
        load_dotenv(env_path)
    else:
        load_dotenv()

    return Settings(
        telegram_api_id=_optional_int("TELEGRAM_API_ID"),
        telegram_api_hash=_string("TELEGRAM_API_HASH"),
        telegram_phone=_string("TELEGRAM_PHONE"),
        telegram_session=_string("TELEGRAM_SESSION", "profit_hacker.session"),
        telegram_channel=_channel(_string("TELEGRAM_CHANNEL", "-1001303328644")),
        recent_message_log_count=_int("RECENT_MESSAGE_LOG_COUNT", 5),
        rescan_message_count=_int("RESCAN_MESSAGE_COUNT", 10),
        rescan_max_age_seconds=_int("RESCAN_MAX_AGE_SECONDS", 43200),
        mt5_path=_string("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe"),
        mt5_login=_optional_int("MT5_LOGIN"),
        mt5_password=_string("MT5_PASSWORD"),
        mt5_server=_string("MT5_SERVER"),
        dry_run=_bool("DRY_RUN", True),
        risk_percent=_float("RISK_PERCENT", 5.0),
        max_signal_age_seconds=_int("MAX_SIGNAL_AGE_SECONDS", 180),
        pending_order_ttl_seconds=_int("PENDING_ORDER_TTL_SECONDS", 180),
        order_mode=_string("ORDER_MODE", "single").lower(),
        symbol_map=_symbol_map(_string("SYMBOL_MAP")),
        auto_discover_symbols=_bool("AUTO_DISCOVER_SYMBOLS", True),
        max_entry_drift_points=_float("MAX_ENTRY_DRIFT_POINTS", 0.0),
        break_even_enabled=_bool("BREAK_EVEN_ENABLED", True),
        break_even_offset_points=_float("BREAK_EVEN_OFFSET_POINTS", 0.0),
        mt5_magic=_int("MT5_MAGIC", 1303328644),
        trade_comment_prefix=_string("TRADE_COMMENT_PREFIX", "PH"),
        watch_interval_seconds=_float("WATCH_INTERVAL_SECONDS", 2.0),
        state_db=Path(_string("STATE_DB", "state/profit_hacker.sqlite3")),
        log_level=_string("LOG_LEVEL", "INFO").upper(),
    )
