from __future__ import annotations

from dataclasses import dataclass
from datetime import time
import os
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_SYMBOLS = (
    "XAUUSD",
)


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _time(name: str, default: str) -> time:
    value = os.getenv(name, default).strip()
    hour, minute = (int(part) for part in value.split(":", maxsplit=1))
    return time(hour, minute)


@dataclass(frozen=True, slots=True)
class Config:
    symbols: tuple[str, ...]
    starting_balance: float
    risk_pct: float
    asia_start: time
    asia_end: time
    london_start: time
    london_end: time
    ny_start: time
    ny_cutoff: time
    force_exit: time
    ny_rr: float
    ny_fallback_rr: float
    ny_fallback_minutes: int
    ny_entry_buffer_spreads: float
    ny_entry_mode: str
    lock_trigger_r: float
    lock_profit_r: float
    ny_stop_buffer_fraction: float
    enable_trading: bool
    dry_run: bool
    magic: int
    poll_seconds: int
    deviation_points: int
    log_level: str
    root: Path


def load_config(env_path: str | Path | None = None) -> Config:
    root = Path(__file__).resolve().parents[2]
    path = Path(env_path) if env_path else root / ".env"
    load_dotenv(path, override=True)
    symbols = tuple(
        item.strip().upper()
        for item in os.getenv("SYMBOLS", ",".join(DEFAULT_SYMBOLS)).split(",")
        if item.strip()
    )
    return Config(
        symbols=symbols,
        starting_balance=float(os.getenv("STARTING_BALANCE", "1000")),
        risk_pct=float(os.getenv("RISK_PCT", "3")),
        asia_start=_time("ASIA_START_UTC", "00:00"),
        asia_end=_time("ASIA_END_UTC", "08:00"),
        london_start=_time("LONDON_CONFIRM_START_UTC", "08:00"),
        london_end=_time("LONDON_CONFIRM_END_UTC", "09:00"),
        ny_start=_time("NY_START_UTC", "13:30"),
        ny_cutoff=_time("NY_SIGNAL_CUTOFF_UTC", "16:00"),
        force_exit=_time("FORCE_EXIT_UTC", "21:00"),
        ny_rr=float(os.getenv("NY_RR", "5")),
        ny_fallback_rr=float(os.getenv("NY_FALLBACK_RR", "4")),
        ny_fallback_minutes=int(os.getenv("NY_FALLBACK_MINUTES", "45")),
        ny_entry_buffer_spreads=float(
            os.getenv("NY_ENTRY_BUFFER_SPREADS", "1")
        ),
        ny_entry_mode=os.getenv("NY_ENTRY_MODE", "dual").strip().lower(),
        lock_trigger_r=float(os.getenv("LOCK_TRIGGER_R", "0.5")),
        lock_profit_r=float(os.getenv("LOCK_PROFIT_R", "0.15")),
        ny_stop_buffer_fraction=float(
            os.getenv("NY_STOP_BUFFER_RANGE_FRACTION", "0.05")
        ),
        enable_trading=_bool("ENABLE_TRADING", False),
        dry_run=_bool("DRY_RUN", True),
        magic=int(os.getenv("MAGIC", "300730")),
        poll_seconds=int(os.getenv("POLL_SECONDS", "15")),
        deviation_points=int(os.getenv("DEVIATION_POINTS", "30")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        root=root,
    )
