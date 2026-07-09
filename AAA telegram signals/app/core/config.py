import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

# Project directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # App Settings
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8787
    DATABASE_URL: str = "sqlite:///storage/copier.db"
    
    # Copier Settings
    COPIER_ENABLED: bool = False
    POLL_INTERVAL_SECONDS: int = 10
    
    # Telegram Settings
    TELEGRAM_MODE: str = "bot"  # "bot" or "user"
    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_SESSION_STRING: str = ""
    TELEGRAM_CHAT_LINK: str = ""
    TELEGRAM_READ_MODE: str = "api"  # "api" or "browser"
    TELEGRAM_BROWSER_HEADLESS: bool = False
    ALLOW_REPLY_SIGNALS: bool = False
    
    # Gemini Settings
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"
    MIN_LLM_CONFIDENCE: float = 0.80
    
    # Risk Settings
    RISK_MODE: str = "fixed_lot"  # "fixed_lot", "risk_percent", "risk_usd_cap"
    FIXED_LOT: float = 0.01
    SYMBOL_LOTS: str = ""
    RISK_PERCENT: float = 1.0
    RISK_USD_CAP: float = 10.0
    USE_EQUITY_INSTEAD_OF_BALANCE: bool = True
    ALLOW_MIN_LOT_IF_RISK_TOO_SMALL: bool = True
    MAX_LOT: float | None = None
    
    # Trade Management Settings
    MOVE_TO_BREAK_EVEN_ENABLED: bool = True
    BREAK_EVEN_OFFSET_POINTS: int = 0
    
    # Validation / Safety Settings
    ALLOW_NO_SL: bool = False
    MAX_SPREAD_POINTS: int | None = None
    MAX_TRADES_PER_DAY: int = 0
    STALE_SIGNAL_MAX_AGE_MINUTES: int = 5
    STALE_SIGNAL_MAX_ENTRY_DISTANCE_POINTS: int = 50

    @field_validator("MAX_LOT", "MAX_SPREAD_POINTS", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        if v == "":
            return None
        return v

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate config
settings = Settings()
