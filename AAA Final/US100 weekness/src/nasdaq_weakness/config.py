from __future__ import annotations

from dataclasses import dataclass, replace
import os
from pathlib import Path

from dotenv import load_dotenv


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _clock(name: str, default: str) -> tuple[int, int]:
    raw = os.getenv(name, default)
    hour, minute = raw.split(":", maxsplit=1)
    return int(hour), int(minute)


@dataclass(frozen=True)
class Config:
    project_dir: Path
    canonical_symbol: str = "AUTO"
    history_days: int = 365
    risk_pct: float = 0.5
    max_daily_risk_pct: float = 5.0
    risk_progression_enabled: bool = False
    risk_progression_multiplier: float = 1.6
    risk_progression_max_pct: float = 5.0
    note_point_to_price: float = 0.1
    strategy_mode: str = "ALL"
    pending_mode: str = "OCO"
    s2a_entry_model: str = "REFERENCE_PAIR"
    s2b_entry_model: str = "CLOSE_PLUS_50"
    target_rr: float = 2.0
    max_target_rr: float = 1.7
    trailing_enabled: bool = True
    runner_trail_bars: int = 1
    runner_buffer_points: float = 5.0
    order_expiry_ny: tuple[int, int] = (12, 0)
    session_exit_ny: tuple[int, int] = (16, 0)
    max_spread_price: float = 8.0
    slippage_price: float = 1.0
    enable_trading: bool = False
    dry_run: bool = True
    live_unlock: str = ""
    magic: int = 310731
    poll_seconds: int = 15

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
    def live_allowed(self) -> bool:
        return (
            self.enable_trading
            and not self.dry_run
            and self.live_unlock == "I_ACCEPT_NASDAQ_WEAKNESS_LIVE_RISK"
        )

    def with_parameters(self, **kwargs: object) -> "Config":
        return replace(self, **kwargs)

    @property
    def effective_target_rr(self) -> float:
        return min(self.target_rr, self.max_target_rr)

    def validate(self) -> None:
        if not 0 < self.risk_pct <= 100:
            raise ValueError("RISK_PCT must be greater than 0 and below 100")
        if self.max_daily_risk_pct < self.risk_pct:
            raise ValueError("MAX_DAILY_RISK_PCT cannot be below RISK_PCT")
        if self.strategy_mode not in {"S1", "S2A", "S2B", "ALL"}:
            raise ValueError("STRATEGY_MODE must be S1, S2A, S2B, or ALL")
        if self.pending_mode not in {"OCO", "BOTH"}:
            raise ValueError("PENDING_MODE must be OCO or BOTH")
        if self.s2a_entry_model not in {"DIRECT", "REFERENCE_PAIR"}:
            raise ValueError(
                "S2A_ENTRY_MODEL must be DIRECT or REFERENCE_PAIR"
            )
        if self.s2b_entry_model not in {"CLOSE_PLUS_50", "MID_LOW_PAIR"}:
            raise ValueError(
                "S2B_ENTRY_MODEL must be CLOSE_PLUS_50 or MID_LOW_PAIR"
            )
        if self.note_point_to_price <= 0:
            raise ValueError("NOTE_POINT_TO_PRICE must be positive")
        if self.target_rr < 1:
            raise ValueError("TARGET_RR must be at least 1")
        if not 0 < self.max_target_rr <= 1.7:
            raise ValueError("MAX_TARGET_RR must be positive and no more than 1.7")
        if self.risk_progression_multiplier < 1:
            raise ValueError("RISK_PROGRESSION_MULTIPLIER must be at least 1")
        if not 0 < self.risk_progression_max_pct <= 100:
            raise ValueError("RISK_PROGRESSION_MAX_PCT must be between 0 and 100")
        if self.runner_trail_bars not in {1, 2}:
            raise ValueError("RUNNER_TRAIL_BARS must be 1 or 2")


def load_config(project_dir: Path | None = None) -> Config:
    base = (project_dir or Path.cwd()).resolve()
    load_dotenv(base / ".env", override=False)
    cfg = Config(
        project_dir=base,
        # Preserve broker-specific casing. MT5 symbol lookup is case-sensitive
        # for names such as USTEC_x100m; scoring normalizes case separately.
        canonical_symbol=os.getenv("CANONICAL_SYMBOL", "AUTO").strip(),
        history_days=int(os.getenv("HISTORY_DAYS", "365")),
        risk_pct=float(os.getenv("RISK_PCT", "0.5")),
        max_daily_risk_pct=float(os.getenv("MAX_DAILY_RISK_PCT", "5.0")),
        risk_progression_enabled=_bool("RISK_PROGRESSION_ENABLED", False),
        risk_progression_multiplier=float(
            os.getenv("RISK_PROGRESSION_MULTIPLIER", "1.6")
        ),
        risk_progression_max_pct=float(
            os.getenv("RISK_PROGRESSION_MAX_PCT", "5.0")
        ),
        note_point_to_price=float(os.getenv("NOTE_POINT_TO_PRICE", "0.1")),
        strategy_mode=os.getenv("STRATEGY_MODE", "ALL").upper(),
        pending_mode=os.getenv("PENDING_MODE", "OCO").upper(),
        s2a_entry_model=os.getenv(
            "S2A_ENTRY_MODEL", "REFERENCE_PAIR"
        ).upper(),
        s2b_entry_model=os.getenv(
            "S2B_ENTRY_MODEL", "CLOSE_PLUS_50"
        ).upper(),
        target_rr=float(os.getenv("TARGET_RR", "2.0")),
        max_target_rr=float(os.getenv("MAX_TARGET_RR", "1.7")),
        trailing_enabled=_bool("TRAILING_ENABLED", True),
        runner_trail_bars=int(os.getenv("RUNNER_TRAIL_BARS", "1")),
        runner_buffer_points=float(
            os.getenv("RUNNER_BUFFER_POINTS", "5")
        ),
        order_expiry_ny=_clock("ORDER_EXPIRY_NY", "12:00"),
        session_exit_ny=_clock("SESSION_EXIT_NY", "16:00"),
        max_spread_price=float(os.getenv("MAX_SPREAD_PRICE", "8")),
        slippage_price=float(os.getenv("SLIPPAGE_PRICE", "1.0")),
        enable_trading=_bool("ENABLE_TRADING", False),
        dry_run=_bool("DRY_RUN", True),
        live_unlock=os.getenv("LIVE_UNLOCK", ""),
        magic=int(os.getenv("MAGIC", "310731")),
        poll_seconds=int(os.getenv("POLL_SECONDS", "15")),
    )
    cfg.validate()
    cfg.cache_dir.mkdir(parents=True, exist_ok=True)
    cfg.reports_dir.mkdir(parents=True, exist_ok=True)
    cfg.logs_dir.mkdir(parents=True, exist_ok=True)
    return cfg
