from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _time(name: str, default: str) -> time:
    raw = os.getenv(name, default).strip()
    return datetime.strptime(raw, "%H:%M").time()


def _date(name: str) -> date | None:
    raw = os.getenv(name, "").strip()
    return date.fromisoformat(raw) if raw else None


@dataclass(frozen=True)
class Config:
    root: Path
    mt5_path: str
    symbol: str
    timezone_name: str
    range_start: time
    range_minutes: int
    last_breakout_time: time
    flat_time: time
    weekdays_only: bool
    h1_min_score: int
    require_vwap: bool
    min_relative_volume: float
    allow_double_sweep: bool
    double_sweep_body_min: float
    breakout_body_min: float
    breakout_extension_atr_min: float
    range_atr_min: float
    range_atr_max: float
    retest_bars: int
    retest_tolerance_atr: float
    rejection_body_min: float
    sl_buffer_atr: float
    entry_buffer_points: int
    entry_valid_bars: int
    max_stop_atr: float
    max_spread_points: int
    slippage_points: int
    require_news_file: bool
    news_blackout_csv: Path
    starting_balance: float
    risk_percent: float
    partial_r: float
    partial_percent: float
    runner_r: float
    move_sl_to_be: bool
    max_trades_per_day: int
    backtest_days: int
    backtest_start: date | None
    backtest_end: date | None
    live_trading: bool
    place_trades: bool
    poll_seconds: int
    magic: int
    comment: str
    fixed_lot: float
    deviation_points: int

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)

    @property
    def range_end(self) -> time:
        anchor = datetime.combine(date(2000, 1, 1), self.range_start)
        return (anchor + timedelta(minutes=self.range_minutes)).time()

    @property
    def partial_fraction(self) -> float:
        return min(max(self.partial_percent / 100.0, 0.0), 1.0)


def load_config() -> Config:
    news_path = Path(os.getenv("ORB_NEWS_BLACKOUT_CSV", "data/news_blackouts.csv"))
    if not news_path.is_absolute():
        news_path = ROOT / news_path
    return Config(
        root=ROOT,
        mt5_path=os.getenv("MT5_PATH", "").strip(),
        symbol=os.getenv("ORB_SYMBOL", "XAUUSD").strip().upper(),
        timezone_name=os.getenv("ORB_TIMEZONE", "America/New_York").strip(),
        range_start=_time("ORB_RANGE_START", "08:20"),
        range_minutes=max(_int("ORB_RANGE_MINUTES", 15), 5),
        last_breakout_time=_time("ORB_LAST_BREAKOUT_TIME", "11:30"),
        flat_time=_time("ORB_FLAT_TIME", "16:00"),
        weekdays_only=_bool("ORB_WEEKDAYS_ONLY", True),
        h1_min_score=min(max(_int("ORB_H1_MIN_SCORE", 2), 1), 3),
        require_vwap=_bool("ORB_REQUIRE_VWAP", True),
        min_relative_volume=max(_float("ORB_MIN_RELATIVE_VOLUME", 1.05), 0.0),
        allow_double_sweep=_bool("ORB_ALLOW_DOUBLE_SWEEP", True),
        double_sweep_body_min=_float("ORB_DOUBLE_SWEEP_BODY_MIN", 0.65),
        breakout_body_min=_float("ORB_BREAKOUT_BODY_MIN", 0.60),
        breakout_extension_atr_min=_float("ORB_BREAKOUT_EXTENSION_ATR_MIN", 0.10),
        range_atr_min=_float("ORB_RANGE_ATR_MIN", 0.75),
        range_atr_max=_float("ORB_RANGE_ATR_MAX", 4.00),
        retest_bars=max(_int("ORB_RETEST_BARS", 3), 1),
        retest_tolerance_atr=_float("ORB_RETEST_TOLERANCE_ATR", 0.25),
        rejection_body_min=_float("ORB_REJECTION_BODY_MIN", 0.35),
        sl_buffer_atr=_float("ORB_SL_BUFFER_ATR", 0.10),
        entry_buffer_points=max(_int("ORB_ENTRY_BUFFER_POINTS", 2), 0),
        entry_valid_bars=max(_int("ORB_ENTRY_VALID_BARS", 2), 1),
        max_stop_atr=_float("ORB_MAX_STOP_ATR", 4.00),
        max_spread_points=max(_int("ORB_MAX_SPREAD_POINTS", 80), 0),
        slippage_points=max(_int("ORB_SLIPPAGE_POINTS", 5), 0),
        require_news_file=_bool("ORB_REQUIRE_NEWS_FILE", False),
        news_blackout_csv=news_path,
        starting_balance=max(_float("ORB_START_BALANCE", 300.0), 1.0),
        risk_percent=max(_float("ORB_RISK_PERCENT", 0.50), 0.01),
        partial_r=max(_float("ORB_PARTIAL_R", 1.0), 0.1),
        partial_percent=_float("ORB_PARTIAL_PERCENT", 55.0),
        runner_r=max(_float("ORB_RUNNER_R", 2.0), 0.1),
        move_sl_to_be=_bool("ORB_MOVE_SL_TO_BE", True),
        max_trades_per_day=max(_int("ORB_MAX_TRADES_PER_DAY", 1), 1),
        backtest_days=max(_int("ORB_BACKTEST_DAYS", 60), 1),
        backtest_start=_date("ORB_BACKTEST_START"),
        backtest_end=_date("ORB_BACKTEST_END"),
        live_trading=_bool("ORB_LIVE_TRADING", False),
        place_trades=_bool("ORB_PLACE_TRADES", False),
        poll_seconds=max(_int("ORB_POLL_SECONDS", 10), 2),
        magic=_int("ORB_MAGIC", 820835),
        comment=os.getenv("ORB_COMMENT", "ORB RETEST").strip()[:31],
        fixed_lot=max(_float("ORB_FIXED_LOT", 0.0), 0.0),
        deviation_points=max(_int("ORB_DEVIATION_POINTS", 20), 1),
    )
