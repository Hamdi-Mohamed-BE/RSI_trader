from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import time
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {
        "1", "true", "yes", "on"
    }


def _time(name: str, default: str) -> time:
    hour, minute = (
        int(part) for part in os.getenv(name, default).split(":", 1)
    )
    return time(hour, minute)


@dataclass(frozen=True, slots=True)
class InstrumentSettings:
    canonical_symbol: str
    stop_points: float
    trail_start_r: float
    trail_distance_r: float
    max_hold_hours: int
    max_spread_points: float


@dataclass(frozen=True, slots=True)
class Config:
    root: Path
    canonical_symbol: str
    enable_trading: bool
    dry_run: bool
    live_unlock: str
    risk_pct: float
    magic: int
    ny_timezone: str
    ny_open: time
    pending_expiry: time
    h4_hours: int
    d1_min_body_fraction: float
    h4_min_body_fraction: float
    strong_body_fraction: float
    pullback_points: float
    stop_points: float
    trail_start_r: float
    trail_distance_r: float
    max_hold_hours: int
    max_trades_per_week: int
    poll_seconds: int
    deviation_points: int
    max_spread_points: float
    comment_reason: str
    h1_confirmation_mode: str = "none"
    entry_mode: str = "fixed_pullback"
    target_mode: str = "trail"
    stop_mode: str = "fixed"
    structure_stop_buffer_points: float = 10.0
    minimum_stop_points: float = 25.0
    maximum_stop_points: float = 100.0
    body_level_daily_lookback: int = 10
    body_level_weekly_lookback: int = 4
    body_level_monthly_lookback: int = 3
    minimum_target_r: float = 0.50
    maximum_target_r: float = 1.7
    instruments: tuple[InstrumentSettings, ...] = ()
    max_total_risk_pct: float = 4.0
    risk_progression_enabled: bool = False
    risk_progression_multiplier: float = 1.6
    live_max_risk_pct: float = 4.0
    trailing_enabled: bool = True
    target_rr: float = 1.7

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.ny_timezone)

    @property
    def live_allowed(self) -> bool:
        return (
            self.enable_trading
            and not self.dry_run
            and self.live_unlock == "I_ACCEPT_DMC_LIVE_RISK"
        )

    def for_instrument(self, hint: str) -> "Config":
        for item in self.instruments:
            if item.canonical_symbol.casefold() == hint.casefold():
                return replace(
                    self,
                    canonical_symbol=item.canonical_symbol,
                    stop_points=item.stop_points,
                    trail_start_r=item.trail_start_r,
                    trail_distance_r=item.trail_distance_r,
                    max_hold_hours=item.max_hold_hours,
                    max_spread_points=item.max_spread_points,
                )
        return replace(self, canonical_symbol=hint)


def load_config(env_path: str | Path | None = None) -> Config:
    root = Path(__file__).resolve().parents[2]
    load_dotenv(Path(env_path) if env_path else root / ".env", override=True)
    config = Config(
        root=root,
        canonical_symbol=os.getenv("CANONICAL_SYMBOL", "US100").strip(),
        enable_trading=_bool("ENABLE_TRADING", False),
        dry_run=_bool("DRY_RUN", True),
        live_unlock=os.getenv("LIVE_UNLOCK", "").strip(),
        risk_pct=float(os.getenv("RISK_PCT", "2.0")),
        magic=int(os.getenv("MAGIC", "1082601")),
        ny_timezone=os.getenv("NY_TIMEZONE", "America/New_York").strip(),
        ny_open=_time("NY_OPEN", "09:30"),
        pending_expiry=_time("PENDING_EXPIRY", "16:00"),
        h4_hours=int(os.getenv("H4_HOURS", "4")),
        d1_min_body_fraction=float(
            os.getenv("D1_MIN_BODY_FRACTION", "0.20")
        ),
        h4_min_body_fraction=float(
            os.getenv("H4_MIN_BODY_FRACTION", "0.20")
        ),
        strong_body_fraction=float(
            os.getenv("STRONG_BODY_FRACTION", "0.50")
        ),
        pullback_points=float(os.getenv("PULLBACK_POINTS", "25")),
        stop_points=float(os.getenv("STOP_POINTS", "55")),
        trail_start_r=float(os.getenv("TRAIL_START_R", "1.0")),
        trail_distance_r=float(os.getenv("TRAIL_DISTANCE_R", "0.5")),
        max_hold_hours=int(os.getenv("MAX_HOLD_HOURS", "72")),
        max_trades_per_week=int(os.getenv("MAX_TRADES_PER_WEEK", "3")),
        poll_seconds=int(os.getenv("POLL_SECONDS", "15")),
        deviation_points=int(os.getenv("DEVIATION_POINTS", "30")),
        max_spread_points=float(os.getenv("MAX_SPREAD_POINTS", "12")),
        comment_reason=os.getenv(
            "ORDER_COMMENT_REASON", "D1+H4 aligned"
        ).strip(),
        h1_confirmation_mode=os.getenv(
            "H1_CONFIRMATION_MODE", "none"
        ).strip().lower(),
        entry_mode=os.getenv("ENTRY_MODE", "fixed_pullback").strip().lower(),
        target_mode=os.getenv("TARGET_MODE", "trail").strip().lower(),
        stop_mode=os.getenv("STOP_MODE", "fixed").strip().lower(),
        structure_stop_buffer_points=float(
            os.getenv("STRUCTURE_STOP_BUFFER_POINTS", "10")
        ),
        minimum_stop_points=float(os.getenv("MINIMUM_STOP_POINTS", "25")),
        maximum_stop_points=float(os.getenv("MAXIMUM_STOP_POINTS", "100")),
        body_level_daily_lookback=int(
            os.getenv("BODY_LEVEL_DAILY_LOOKBACK", "10")
        ),
        body_level_weekly_lookback=int(
            os.getenv("BODY_LEVEL_WEEKLY_LOOKBACK", "4")
        ),
        body_level_monthly_lookback=int(
            os.getenv("BODY_LEVEL_MONTHLY_LOOKBACK", "3")
        ),
        minimum_target_r=float(os.getenv("MINIMUM_TARGET_R", "0.50")),
        maximum_target_r=float(os.getenv("MAXIMUM_TARGET_R", "1.7")),
        max_total_risk_pct=float(os.getenv("MAX_TOTAL_RISK_PCT", "4.0")),
        risk_progression_enabled=_bool("RISK_PROGRESSION_ENABLED", False),
        risk_progression_multiplier=float(
            os.getenv("RISK_PROGRESSION_MULTIPLIER", "1.6")
        ),
        live_max_risk_pct=float(os.getenv("LIVE_MAX_RISK_PCT", "4.0")),
        trailing_enabled=_bool("TRAILING_ENABLED", True),
        target_rr=float(os.getenv("TARGET_RR", "1.7")),
    )
    hints = tuple(
        item.strip()
        for item in os.getenv("SYMBOLS", config.canonical_symbol).split(",")
        if item.strip()
    )
    instruments: list[InstrumentSettings] = []
    for hint in hints:
        prefix = "".join(character for character in hint.upper() if character.isalnum())
        instruments.append(
            InstrumentSettings(
                canonical_symbol=hint,
                stop_points=float(
                    os.getenv(f"{prefix}_STOP_POINTS", str(config.stop_points))
                ),
                trail_start_r=float(
                    os.getenv(f"{prefix}_TRAIL_START_R", str(config.trail_start_r))
                ),
                trail_distance_r=float(
                    os.getenv(
                        f"{prefix}_TRAIL_DISTANCE_R",
                        str(config.trail_distance_r),
                    )
                ),
                max_hold_hours=int(
                    os.getenv(f"{prefix}_MAX_HOLD_HOURS", str(config.max_hold_hours))
                ),
                max_spread_points=float(
                    os.getenv(
                        f"{prefix}_MAX_SPREAD_POINTS",
                        str(config.max_spread_points),
                    )
                ),
            )
        )
    config = replace(config, instruments=tuple(instruments))
    if not 0 < config.risk_pct <= 10:
        raise ValueError("RISK_PCT must be within (0, 10]")
    if config.risk_progression_multiplier < 1.0:
        raise ValueError("RISK_PROGRESSION_MULTIPLIER must be at least 1.0")
    if not 0 < config.live_max_risk_pct <= 100:
        raise ValueError("LIVE_MAX_RISK_PCT must be within (0, 100]")
    if config.live_max_risk_pct < config.risk_pct:
        raise ValueError("LIVE_MAX_RISK_PCT must be at least RISK_PCT")
    if config.max_total_risk_pct < config.risk_pct:
        raise ValueError("MAX_TOTAL_RISK_PCT must be at least RISK_PCT")
    if config.live_max_risk_pct > config.max_total_risk_pct:
        raise ValueError("LIVE_MAX_RISK_PCT must not exceed MAX_TOTAL_RISK_PCT")
    if config.pullback_points <= 0 or config.stop_points <= 0:
        raise ValueError("Pullback and stop distances must be positive")
    if config.max_trades_per_week < 1:
        raise ValueError("MAX_TRADES_PER_WEEK must be positive")
    if config.h1_confirmation_mode not in {
        "none", "aligned", "previous_body", "body_level"
    }:
        raise ValueError(
            "H1_CONFIRMATION_MODE must be none, aligned, previous_body or body_level"
        )
    if config.entry_mode not in {
        "fixed_pullback", "h1_retest", "reaction_retest"
    }:
        raise ValueError(
            "ENTRY_MODE must be fixed_pullback, h1_retest or reaction_retest"
        )
    if config.target_mode not in {"trail", "next_body"}:
        raise ValueError("TARGET_MODE must be trail or next_body")
    if config.stop_mode not in {"fixed", "h1_structure"}:
        raise ValueError("STOP_MODE must be fixed or h1_structure")
    if not 0 < config.minimum_stop_points <= config.maximum_stop_points:
        raise ValueError("Structural stop limits are invalid")
    if not 0 < config.minimum_target_r <= config.maximum_target_r:
        raise ValueError("Target R limits are invalid")
    if not 0 < config.target_rr <= 1.7:
        raise ValueError("TARGET_RR must be within (0, 1.7]")
    if config.maximum_target_r > 1.7:
        raise ValueError("MAXIMUM_TARGET_R must not exceed the 1.7R TP ceiling")
    _ = config.timezone
    return config
