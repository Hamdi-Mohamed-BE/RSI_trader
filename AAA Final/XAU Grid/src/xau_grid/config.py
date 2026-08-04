from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
import os

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class StrategyConfig:
    mode: str = "trend"
    risk_pct: float = 0.50
    grid_levels: int = 3
    first_offset_atr: float = 0.25
    grid_step_atr: float = 0.75
    stop_extra_atr: float = 1.20
    target_atr: float = 1.50
    be_trigger_r: float = 1.00
    be_lock_r: float = 0.10
    trail_start_r: float = 0.0
    trail_distance_atr: float = 0.80
    pending_expiry_bars: int = 12
    max_hold_bars: int = 72
    cooldown_bars: int = 12
    session_start_utc: int = 6
    session_end_utc: int = 19
    adx_min: float = 18.0
    adx_max: float = 38.0
    range_adx_max: float = 20.0
    rsi_long_max: float = 48.0
    rsi_short_min: float = 52.0
    max_spread_price: float = 0.80
    max_daily_loss_pct: float = 1.00

    def validate(self) -> "StrategyConfig":
        if self.mode not in {"trend", "range", "momentum", "breakout"}:
            raise ValueError("MODE must be trend, range, momentum or breakout")
        if not 0 < self.risk_pct <= 2.0:
            raise ValueError("RISK_PCT must be above 0 and no more than 2%")
        if not 1 <= self.grid_levels <= 5:
            raise ValueError("GRID_LEVELS must be between 1 and 5")
        if self.grid_step_atr <= 0 or self.stop_extra_atr <= 0 or self.target_atr <= 0:
            raise ValueError("Grid, stop and target ATR multipliers must be positive")
        if not 0 <= self.session_start_utc <= 23 or not 1 <= self.session_end_utc <= 24:
            raise ValueError("Session hours are invalid")
        return self

    def with_values(self, **values) -> "StrategyConfig":
        return replace(self, **values).validate()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class LiveConfig:
    strategy: StrategyConfig
    canonical_symbol: str = "XAUUSD"
    magic: int = 4_080_401
    poll_seconds: int = 15
    max_equity_dd_pct: float = 8.0
    min_margin_level_pct: float = 500.0
    enable_trading: bool = True
    dry_run: bool = False
    live_unlock: str = ""

    @property
    def unlocked(self) -> bool:
        return (
            self.enable_trading
            and not self.dry_run
            and self.live_unlock == "I_ACCEPT_XAU_GRID_LIVE_RISK"
        )


def load_config(env_path: Path | None = None) -> LiveConfig:
    load_dotenv(env_path or ROOT / ".env", override=True)
    defaults = StrategyConfig()
    mapping: dict[str, object] = {}
    for item in fields(StrategyConfig):
        key = item.name.upper()
        raw = os.getenv(key)
        if raw is None:
            continue
        current = getattr(defaults, item.name)
        if isinstance(current, int):
            mapping[item.name] = int(raw)
        elif isinstance(current, float):
            mapping[item.name] = float(raw)
        else:
            mapping[item.name] = raw.strip().lower()
    strategy = defaults.with_values(**mapping)
    return LiveConfig(
        strategy=strategy,
        canonical_symbol=os.getenv("CANONICAL_SYMBOL", "XAUUSD"),
        magic=int(os.getenv("MAGIC", "4080401")),
        poll_seconds=int(os.getenv("POLL_SECONDS", "15")),
        max_equity_dd_pct=float(os.getenv("MAX_EQUITY_DD_PCT", "8")),
        min_margin_level_pct=float(os.getenv("MIN_MARGIN_LEVEL_PCT", "500")),
        enable_trading=_bool("ENABLE_TRADING", True),
        dry_run=_bool("DRY_RUN", False),
        live_unlock=os.getenv("LIVE_UNLOCK", ""),
    )
