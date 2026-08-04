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
    risk_pct: float = 1.0
    impulse_bars: int = 12
    impulse_atr: float = 2.0
    test_tolerance_atr: float = 0.2
    min_test_gap: int = 4
    max_test_gap: int = 16
    rejection_atr: float = 0.1
    min_dip_atr: float = 0.6
    min_recovery_atr: float = 0.6
    entry_buffer_atr: float = 0.05
    stop_buffer_atr: float = 0.05
    min_range_atr: float = 0.5
    max_range_atr: float = 3.0
    target_rr: float = 2.0
    activation_delay_bars: int = 2
    pending_expiry_bars: int = 8
    max_hold_bars: int = 48
    cooldown_bars: int = 4
    session_start_utc: int = 0
    session_end_utc: int = 24
    max_spread_price: float = 0.8
    max_daily_loss_pct: float = 2.0

    def validate(self) -> "StrategyConfig":
        if not 0 < self.risk_pct <= 2:
            raise ValueError("RISK_PCT must be above 0 and no more than 2%")
        if self.impulse_bars < 2 or self.impulse_atr <= 0:
            raise ValueError("Impulse settings are invalid")
        if self.min_test_gap < 1 or self.max_test_gap < self.min_test_gap:
            raise ValueError("Double-test gap settings are invalid")
        if self.min_dip_atr <= 0 or self.min_recovery_atr <= 0:
            raise ValueError("Swing-depth settings are invalid")
        if self.target_rr not in {1.0, 2.0}:
            raise ValueError("TARGET_RR must be 1 or 2")
        if self.activation_delay_bars < 0 or self.activation_delay_bars >= self.pending_expiry_bars:
            raise ValueError("ACTIVATION_DELAY_BARS must be below PENDING_EXPIRY_BARS")
        if self.min_range_atr <= 0 or self.max_range_atr <= self.min_range_atr:
            raise ValueError("Range ATR bounds are invalid")
        if not 0 <= self.session_start_utc <= 23 or not 1 <= self.session_end_utc <= 24 or self.session_start_utc >= self.session_end_utc:
            raise ValueError("UTC session window is invalid")
        return self

    def with_values(self, **values) -> "StrategyConfig":
        return replace(self, **values).validate()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class LiveConfig:
    strategy: StrategyConfig
    canonical_symbol: str = "XAUUSD"
    magic: int = 4_080_402
    poll_seconds: int = 15
    max_equity_dd_pct: float = 6.0
    min_margin_level_pct: float = 500.0
    shared_xau_risk_cap_pct: float = 4.0
    selected_xau_magic_risks: str = ""
    enable_trading: bool = False
    dry_run: bool = True
    live_unlock: str = ""

    @property
    def unlocked(self) -> bool:
        return self.enable_trading and not self.dry_run and self.live_unlock == "I_ACCEPT_XAU_WEAKNESS_LIVE_RISK"


def load_config(env_path: Path | None = None) -> LiveConfig:
    load_dotenv(env_path or ROOT / ".env", override=True)
    defaults = StrategyConfig()
    values: dict[str, object] = {}
    for item in fields(StrategyConfig):
        raw = os.getenv(item.name.upper())
        if raw is None:
            continue
        current = getattr(defaults, item.name)
        values[item.name] = int(raw) if isinstance(current, int) else float(raw)
    strategy = defaults.with_values(**values)
    return LiveConfig(
        strategy=strategy,
        canonical_symbol=os.getenv("CANONICAL_SYMBOL", "XAUUSD"),
        magic=int(os.getenv("MAGIC", "4080402")),
        poll_seconds=int(os.getenv("POLL_SECONDS", "15")),
        max_equity_dd_pct=float(os.getenv("MAX_EQUITY_DD_PCT", "6")),
        min_margin_level_pct=float(os.getenv("MIN_MARGIN_LEVEL_PCT", "500")),
        shared_xau_risk_cap_pct=float(os.getenv("SHARED_XAU_RISK_CAP_PCT", "4")),
        selected_xau_magic_risks=os.getenv("SELECTED_XAU_MAGIC_RISKS", ""),
        enable_trading=_bool("ENABLE_TRADING", False),
        dry_run=_bool("DRY_RUN", True),
        live_unlock=os.getenv("LIVE_UNLOCK", ""),
    )
