from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="NAW_LTA_",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = 8010
    database_url: str = "sqlite:///./data/naw_lta.sqlite"
    celery_broker: str = "sqla+sqlite:///./data/celery_broker.sqlite"
    celery_backend: str = "db+sqlite:///./data/celery_results.sqlite"
    databento_api_key: str = Field(default="", validation_alias="DATABENTO_API_KEY")


settings = Settings()


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "exports").mkdir(parents=True, exist_ok=True)
