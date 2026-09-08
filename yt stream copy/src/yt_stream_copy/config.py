from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8765"))
    risk_percent: float = float(os.getenv("RISK_PERCENT", "1.0"))
    no_sl_paper_volume: float = float(os.getenv("NO_SL_PAPER_VOLUME", "0.04"))
    auto_paper: bool = os.getenv("AUTO_PAPER", "true").strip().lower() in {"1", "true", "yes", "on"}
    whisper_model: str = os.getenv("WHISPER_MODEL", "small.en")
    whisper_device: str = os.getenv("WHISPER_DEVICE", "auto")
    chunk_seconds: int = int(os.getenv("CHUNK_SECONDS", "12"))
    frame_seconds: int = int(os.getenv("FRAME_SECONDS", "5"))
    screen_ocr: bool = os.getenv("SCREEN_OCR", "true").strip().lower() in {"1", "true", "yes", "on"}
    ai_mode: str = os.getenv("AI_MODE", "rules")
    ai_base_url: str = os.getenv("AI_BASE_URL", "http://127.0.0.1:11434/v1")
    ai_model: str = os.getenv("AI_MODEL", "qwen2.5vl:3b")
    ai_api_key: str = os.getenv("AI_API_KEY", "ollama")
    auto_start_url: str = os.getenv("AUTO_START_URL", "")
    data_dir: Path = ROOT / "data"


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
