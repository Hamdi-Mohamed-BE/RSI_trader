from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AAA Trade Copier"
    app_env: Literal["development", "test", "production"] = "development"
    app_secret_key: str = "development-only-change-me"
    database_url: str = "sqlite:///./storage/trade_copier.db"
    web_host: str = "127.0.0.1"
    web_port: int = Field(default=8100, ge=1, le=65535)
    log_level: str = "INFO"

    safe_mode: bool = True
    live_execution_enabled: bool = False
    demo_mode: bool = False
    auto_detect_mt5: bool = True

    admin_email: str = "admin@aaa.local"
    admin_password: str = ""

    heartbeat_timeout_seconds: int = Field(default=15, ge=5, le=300)
    mt5_discovery_interval_seconds: int = Field(default=5, ge=2, le=60)
    mt5_template_path: str = ""
    max_follower_accounts: int = Field(default=10, ge=1, le=100)
    master_pipe_name: str = "aaa_trade_copier_master"
    follower_pipe_prefix: str = "aaa_trade_copier_follower"
    continuous_copy_enabled: bool = True
    continuous_copy_poll_ms: int = Field(default=1000, ge=250, le=5000)
    auto_install_mt5_agents: bool = True

    storage_dir: Path = Path("storage")

    @field_validator("app_secret_key")
    @classmethod
    def validate_production_secret(cls, value: str, info: object) -> str:
        del info
        return value

    @property
    def execution_is_permitted(self) -> bool:
        return not self.safe_mode and self.live_execution_enabled

    @property
    def mt5_instances_dir(self) -> Path:
        return self.storage_dir / "mt5_instances"

    def validate_runtime_safety(self) -> None:
        if self.app_env == "production" and len(self.app_secret_key) < 32:
            raise ValueError("APP_SECRET_KEY must contain at least 32 characters in production.")
        if self.app_env == "production" and self.app_secret_key == "development-only-change-me":
            raise ValueError("The development APP_SECRET_KEY cannot be used in production.")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime_safety()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    return settings


def clear_settings_cache() -> None:
    get_settings.cache_clear()
