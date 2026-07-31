from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


@dataclass(frozen=True)
class AppConfig:
    project_dir: Path
    canonical_symbol: str = "XAUUSD"
    analysis_timeframe: str = "H1"
    execution_timeframe: str = "M15"
    history_days: int = 180
    risk_pct: float = 2.5
    max_portfolio_risk_pct: float = 2.5
    min_rr: float = 2.0
    profile_rows: int = 128
    value_area_pct: float = 70.0
    zone_lookback: int = 500
    zone_max_touches: int = 2
    entry_models: tuple[str, ...] = ("EM1", "EM2", "EM3", "EM4")
    min_grade: str = "A"
    max_hold_bars: int = 48
    enable_trading: bool = False
    dry_run: bool = True
    live_unlock: str = ""
    magic: int = 310726
    poll_seconds: int = 30

    @property
    def cache_dir(self) -> Path:
        return self.project_dir / "data" / "cache"

    @property
    def reports_dir(self) -> Path:
        return self.project_dir / "reports"

    @property
    def logs_dir(self) -> Path:
        return self.project_dir / "logs"

    @property
    def live_submission_allowed(self) -> bool:
        return (
            self.enable_trading
            and not self.dry_run
            and self.live_unlock == "I_ACCEPT_LIVE_LTA_RISK"
        )

    def validate(self) -> None:
        if not 0 < self.risk_pct <= 2.5:
            raise ValueError("RISK_PCT must be greater than 0 and no more than 2.5")
        if self.max_portfolio_risk_pct < self.risk_pct:
            raise ValueError("MAX_PORTFOLIO_RISK_PCT cannot be below RISK_PCT")
        if self.min_rr < 1:
            raise ValueError("MIN_RR must be at least 1")
        if self.profile_rows < 16:
            raise ValueError("PROFILE_ROWS must be at least 16")
        if not 50 <= self.value_area_pct <= 90:
            raise ValueError("VALUE_AREA_PCT must be between 50 and 90")
        unknown = set(self.entry_models) - {"EM1", "EM2", "EM3", "EM4"}
        if unknown:
            raise ValueError(f"Unknown entry models: {sorted(unknown)}")


def load_config(project_dir: Path | None = None) -> AppConfig:
    base = project_dir or Path.cwd()
    load_dotenv(base / ".env", override=False)
    models = tuple(
        value.strip().upper()
        for value in os.getenv("ENTRY_MODELS", "EM1,EM2,EM3,EM4").split(",")
        if value.strip()
    )
    config = AppConfig(
        project_dir=base,
        canonical_symbol=os.getenv("CANONICAL_SYMBOL", "XAUUSD").upper(),
        analysis_timeframe=os.getenv("ANALYSIS_TIMEFRAME", "H1").upper(),
        execution_timeframe=os.getenv("EXECUTION_TIMEFRAME", "M15").upper(),
        history_days=_int("HISTORY_DAYS", 180),
        risk_pct=_float("RISK_PCT", 2.5),
        max_portfolio_risk_pct=_float("MAX_PORTFOLIO_RISK_PCT", 2.5),
        min_rr=_float("MIN_RR", 2.0),
        profile_rows=_int("PROFILE_ROWS", 128),
        value_area_pct=_float("VALUE_AREA_PCT", 70.0),
        zone_lookback=_int("ZONE_LOOKBACK", 500),
        zone_max_touches=_int("ZONE_MAX_TOUCHES", 2),
        entry_models=models,
        min_grade=os.getenv("MIN_GRADE", "A").upper(),
        max_hold_bars=_int("MAX_HOLD_BARS", 48),
        enable_trading=_bool("ENABLE_TRADING", False),
        dry_run=_bool("DRY_RUN", True),
        live_unlock=os.getenv("LIVE_UNLOCK", ""),
        magic=_int("MAGIC", 310726),
        poll_seconds=_int("POLL_SECONDS", 30),
    )
    config.validate()
    config.cache_dir.mkdir(parents=True, exist_ok=True)
    config.reports_dir.mkdir(parents=True, exist_ok=True)
    config.logs_dir.mkdir(parents=True, exist_ok=True)
    return config
