from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]


def _flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (ROOT / path).resolve()


@dataclass(frozen=True)
class Config:
    ai_news_root: Path
    calendar_path: Path
    live_calendar_enabled: bool
    live_calendar_days: int
    events: frozenset[str]
    allowed_events: frozenset[str]
    mode: str
    confidence_threshold: float
    reward_risk: float
    allow_reentry: bool
    breakout_sl_pips: float
    reentry_sl_pips: float
    pip_size: float
    buy_reentry_fib: float
    sell_reentry_fib: float
    min_buffer_pips: float
    spread_multiplier: float
    atr_multiplier: float
    pending_expiry_minutes: int
    max_hold_minutes: int
    sizing_mode: str
    fixed_lot: float
    risk_pct: float
    max_spread_usd: float
    max_slippage_usd: float
    max_daily_loss_pct: float
    max_daily_trades: int
    max_open_risk_pct: float
    min_margin_level_pct: float
    magic: int
    poll_seconds: float
    live_trading: bool
    place_orders: bool
    dry_run: bool

    @property
    def execution_enabled(self) -> bool:
        return self.live_trading and self.place_orders and not self.dry_run

    @classmethod
    def load(cls) -> "Config":
        load_dotenv(ROOT / ".env", override=False)
        mode = os.getenv("MODE", "oco").strip().lower()
        if mode not in {"oco", "forecast"}:
            raise ValueError("MODE must be oco or forecast")
        events = frozenset(x.strip().upper() for x in os.getenv("EVENTS", "NFP,CPI,PPI,GDP,FOMC").split(",") if x.strip())
        allowed = frozenset(x.strip().upper() for x in os.getenv("ALLOWED_EVENTS", "PPI").split(",") if x.strip())
        return cls(
            ai_news_root=_path(os.getenv("AI_NEWS_ROOT", r"..\..\AI news")),
            calendar_path=_path(os.getenv("CALENDAR_PATH", r"..\..\AI news\news_15y_calendar.csv")),
            live_calendar_enabled=_flag("LIVE_CALENDAR_ENABLED", True),
            live_calendar_days=int(os.getenv("LIVE_CALENDAR_DAYS", "14")),
            events=events,
            allowed_events=allowed,
            mode=mode,
            confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", "0.60")),
            reward_risk=float(os.getenv("REWARD_RISK", "5")),
            allow_reentry=_flag("ALLOW_REENTRY", True),
            breakout_sl_pips=float(os.getenv("BREAKOUT_SL_PIPS", "90")),
            reentry_sl_pips=float(os.getenv("REENTRY_SL_PIPS", "50")),
            pip_size=float(os.getenv("GOLD_PIP_SIZE", "0.10")),
            buy_reentry_fib=float(os.getenv("BUY_REENTRY_FIB", "0.60")),
            sell_reentry_fib=float(os.getenv("SELL_REENTRY_FIB", "0.50")),
            min_buffer_pips=float(os.getenv("MIN_BUFFER_PIPS", "2")),
            spread_multiplier=float(os.getenv("SPREAD_BUFFER_MULTIPLIER", "1")),
            atr_multiplier=float(os.getenv("ATR_BUFFER_MULTIPLIER", "0.10")),
            pending_expiry_minutes=int(os.getenv("PENDING_EXPIRY_MINUTES", "15")),
            max_hold_minutes=int(os.getenv("MAX_HOLD_MINUTES", "180")),
            sizing_mode=os.getenv("SIZING_MODE", "risk_pct").strip().lower(),
            fixed_lot=float(os.getenv("FIXED_LOT", "0.01")),
            risk_pct=float(os.getenv("RISK_PCT", "1")),
            max_spread_usd=float(os.getenv("MAX_SPREAD_USD", "5")),
            max_slippage_usd=float(os.getenv("MAX_SLIPPAGE_USD", "2")),
            max_daily_loss_pct=float(os.getenv("MAX_DAILY_LOSS_PCT", "2")),
            max_daily_trades=int(os.getenv("MAX_DAILY_TRADES", "2")),
            max_open_risk_pct=float(os.getenv("MAX_OPEN_RISK_PCT", "2")),
            min_margin_level_pct=float(os.getenv("MIN_MARGIN_LEVEL_PCT", "200")),
            magic=int(os.getenv("MAGIC", "860301")),
            poll_seconds=float(os.getenv("POLL_SECONDS", "1")),
            live_trading=_flag("LIVE_TRADING"),
            place_orders=_flag("PLACE_ORDERS"),
            dry_run=_flag("DRY_RUN", True),
        )
