from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"
RUNTIME_DIR = ROOT / "runtime"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    copier_enabled: bool = True
    live_trading: bool = True
    telegram_mode: Literal["bot", "user"] = "bot"
    telegram_bot_token: str = ""
    telegram_api_id: int | None = None
    telegram_api_hash: str = ""
    telegram_phone: str = ""
    gemini_api_key: str = ""
    telegram_session_path: str = "runtime/telegram-user"
    telegram_source_chats: str = ""
    poll_seconds: int = Field(default=5, ge=2, le=300)
    max_message_age_seconds: int = Field(default=300, ge=30, le=86_400)
    risk_percent: float = Field(default=5.0, gt=0, le=100)
    mt5_magic_number: int = Field(default=26070277, ge=1)
    mt5_deviation_points: int = Field(default=30, ge=0, le=10_000)
    symbol_aliases: str = '{"GOLD":"XAUUSD","SILVER":"XAGUSD"}'
    web_host: str = "127.0.0.1"
    web_port: int = Field(default=8787, ge=1, le=65_535)

    @field_validator(
        "telegram_bot_token", "telegram_api_hash", "telegram_phone", "gemini_api_key"
    )
    @classmethod
    def trim_secrets(cls, value: str) -> str:
        return value.strip()

    @property
    def source_chats(self) -> list[str]:
        return [item.strip() for item in self.telegram_source_chats.split(",") if item.strip()]

    @property
    def aliases(self) -> dict[str, str]:
        try:
            payload = json.loads(self.symbol_aliases)
        except json.JSONDecodeError as exc:
            raise ValueError("SYMBOL_ALIASES must be a JSON object.") from exc
        if not isinstance(payload, dict):
            raise ValueError("SYMBOL_ALIASES must be a JSON object.")
        return {str(key).upper(): str(value).upper() for key, value in payload.items()}

    @property
    def session_file(self) -> Path:
        path = Path(self.telegram_session_path)
        return path if path.is_absolute() else ROOT / path


EDITABLE_KEYS = (
    "COPIER_ENABLED",
    "LIVE_TRADING",
    "TELEGRAM_MODE",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_API_ID",
    "TELEGRAM_API_HASH",
    "TELEGRAM_PHONE",
    "GEMINI_API_KEY",
    "TELEGRAM_SESSION_PATH",
    "TELEGRAM_SOURCE_CHATS",
    "POLL_SECONDS",
    "MAX_MESSAGE_AGE_SECONDS",
    "RISK_PERCENT",
    "MT5_MAGIC_NUMBER",
    "MT5_DEVIATION_POINTS",
    "SYMBOL_ALIASES",
    "WEB_HOST",
    "WEB_PORT",
)


def load_settings() -> Settings:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    return Settings()


def update_env(values: dict[str, object]) -> Settings:
    current = _read_env()
    for key in EDITABLE_KEYS:
        if key not in values:
            continue
        value = values[key]
        if key in {"TELEGRAM_BOT_TOKEN", "TELEGRAM_API_HASH", "GEMINI_API_KEY"}:
            secret = str(value or "").strip()
            if not secret or secret == "configured":
                continue
        if isinstance(value, bool):
            current[key] = "true" if value else "false"
        elif value is None:
            current[key] = ""
        else:
            current[key] = str(value).strip()
    lines = [f"{key}={current.get(key, '')}" for key in EDITABLE_KEYS]
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return Settings()


def public_settings(settings: Settings) -> dict[str, object]:
    return {
        "COPIER_ENABLED": settings.copier_enabled,
        "LIVE_TRADING": settings.live_trading,
        "TELEGRAM_MODE": settings.telegram_mode,
        "TELEGRAM_BOT_TOKEN": "" if not settings.telegram_bot_token else "configured",
        "TELEGRAM_API_ID": settings.telegram_api_id or "",
        "TELEGRAM_API_HASH": "" if not settings.telegram_api_hash else "configured",
        "TELEGRAM_PHONE": settings.telegram_phone,
        "GEMINI_API_KEY": "" if not settings.gemini_api_key else "configured",
        "TELEGRAM_SESSION_PATH": settings.telegram_session_path,
        "TELEGRAM_SOURCE_CHATS": settings.telegram_source_chats,
        "POLL_SECONDS": settings.poll_seconds,
        "MAX_MESSAGE_AGE_SECONDS": settings.max_message_age_seconds,
        "RISK_PERCENT": settings.risk_percent,
        "MT5_MAGIC_NUMBER": settings.mt5_magic_number,
        "MT5_DEVIATION_POINTS": settings.mt5_deviation_points,
        "SYMBOL_ALIASES": settings.symbol_aliases,
        "WEB_HOST": settings.web_host,
        "WEB_PORT": settings.web_port,
        "bot_token_configured": bool(settings.telegram_bot_token),
        "user_api_configured": bool(settings.telegram_api_id and settings.telegram_api_hash),
        "gemini_configured": bool(settings.gemini_api_key),
    }


def _read_env() -> dict[str, str]:
    result: dict[str, str] = {}
    if not ENV_PATH.exists():
        return result
    for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result
