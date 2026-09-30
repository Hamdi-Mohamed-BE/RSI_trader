"""Application settings loaded from environment variables (prefix ``CRYPTOLAB_``) or a local ``.env`` file."""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Runtime configuration. Secrets are never defined here; only where to find them."""

    model_config = SettingsConfigDict(env_prefix="CRYPTOLAB_", env_file=".env", extra="ignore")

    app_name: str = "Calyx Crypto Lab"
    environment: Literal["development", "test", "production"] = "development"

    data_dir: Path = PROJECT_ROOT / "data"
    database_url: str | None = None  # defaults to sqlite+aiosqlite:///<data_dir>/crypto_lab.sqlite

    host: str = "127.0.0.1"
    port: int = 8090

    # Master key for the credential vault. Resolution order: env value -> OS keyring -> dev key file.
    master_key: str | None = Field(default=None, repr=False)
    master_key_keyring_service: str = "crypto-lab"
    allow_dev_key_file: bool = True

    session_ttl_minutes: int = 12 * 60
    cookie_secure: bool = False  # set True behind HTTPS
    login_max_failures: int = 5
    login_lockout_minutes: int = 15
    login_rate_per_minute: int = 10

    # Hard safety switch: LIVE bot mode cannot be selected unless this is explicitly enabled.
    live_trading_enabled: bool = False
    autostart_workers: bool = False
    local_paper_access: bool = False
    default_paper_mode: bool = False
    paper_balance_usdc: Decimal = Field(default=Decimal(100), gt=0)
    paper_trade_limit_usdc: Decimal = Field(default=Decimal(10), gt=0, le=10)

    @model_validator(mode="after")
    def safe_local_access(self) -> Settings:
        if self.local_paper_access and (
            self.host not in {"127.0.0.1", "localhost", "::1"}
            or self.live_trading_enabled
            or self.environment == "production"
        ):
            raise ValueError("Login bypass requires loopback binding, development/test and live trading disabled.")
        if self.paper_trade_limit_usdc > self.paper_balance_usdc:
            raise ValueError("Trade limit cannot exceed the shared starting balance.")
        return self

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite+aiosqlite:///{(self.data_dir / 'crypto_lab.sqlite').as_posix()}"

    @property
    def dev_key_file(self) -> Path:
        return self.data_dir / "dev-master.key"


@lru_cache
def get_settings() -> Settings:
    return Settings()
