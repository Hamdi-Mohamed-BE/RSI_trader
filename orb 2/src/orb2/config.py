from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
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
    return datetime.strptime(os.getenv(name, default).strip(), "%H:%M").time()


@dataclass(frozen=True)
class RuntimeConfig:
    root: Path
    mt5_path: str
    symbols: tuple[str, ...]
    timezone_name: str
    range_start: time
    range_minutes: int
    last_entry: time
    flat_time: time
    backtest_days: int
    starting_balance: float
    risk_percent: float
    max_trades_per_symbol_day: int
    max_daily_losses: int
    slippage_points: int
    cache_data: bool
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


@dataclass(frozen=True)
class StrategyConfig:
    models: tuple[str, ...] = ("retest",)
    breakout_body_min: float = 0.60
    relative_volume_min: float = 1.10
    retest_bars: int = 4
    retest_tolerance_atr: float = 0.25
    rejection_body_min: float = 0.35
    stop_buffer_atr: float = 0.10
    sweep_excursion_atr: float = 0.05
    target_rr: float = 2.0
    use_h1_bias: bool = False
    require_fvg: bool = False
    move_to_be_at_r: float = 1.0
    partial_at_r: float = 2.0
    partial_fraction: float = 0.0

    def key(self) -> str:
        model_key = "+".join(self.models)
        return (
            f"{model_key}|body={self.breakout_body_min:g}|"
            f"vol={self.relative_volume_min:g}|retest={self.retest_bars}|"
            f"tol={self.retest_tolerance_atr:g}|rr={self.target_rr:g}|"
            f"bias={int(self.use_h1_bias)}|fvg={int(self.require_fvg)}|"
            f"partial={self.partial_fraction:g}"
        )


def load_runtime() -> RuntimeConfig:
    symbols = tuple(
        item.strip().upper()
        for item in os.getenv(
            "ORB2_SYMBOLS", "XAUUSD,XAGUSD,US100,US30,ETHUSD,BTCUSD"
        ).split(",")
        if item.strip()
    )
    return RuntimeConfig(
        root=ROOT,
        mt5_path=os.getenv(
            "MT5_PATH",
            r"C:\Program Files\JustMarkets MetaTrader 5\terminal64.exe",
        ).strip(),
        symbols=symbols,
        timezone_name=os.getenv("ORB2_TIMEZONE", "America/New_York").strip(),
        range_start=_time("ORB2_RANGE_START", "09:30"),
        range_minutes=max(_int("ORB2_RANGE_MINUTES", 15), 5),
        last_entry=_time("ORB2_LAST_ENTRY", "12:00"),
        flat_time=_time("ORB2_FLAT_TIME", "16:00"),
        backtest_days=max(_int("ORB2_BACKTEST_DAYS", 183), 30),
        starting_balance=max(_float("ORB2_START_BALANCE", 300.0), 1.0),
        risk_percent=min(max(_float("ORB2_RISK_PERCENT", 1.0), 0.01), 1.0),
        max_trades_per_symbol_day=max(
            _int("ORB2_MAX_TRADES_PER_SYMBOL_DAY", 1), 1
        ),
        max_daily_losses=max(_int("ORB2_MAX_DAILY_LOSSES", 2), 1),
        slippage_points=max(_int("ORB2_SLIPPAGE_POINTS", 5), 0),
        cache_data=_bool("ORB2_CACHE_DATA", True),
        live_trading=_bool("ORB2_LIVE_TRADING", False),
        place_trades=_bool("ORB2_PLACE_TRADES", False),
        poll_seconds=max(_int("ORB2_POLL_SECONDS", 10), 2),
        magic=_int("ORB2_MAGIC", 930945),
        comment=os.getenv("ORB2_COMMENT", "ORB2 PLAYBOOK").strip()[:31],
        fixed_lot=max(_float("ORB2_FIXED_LOT", 0.0), 0.0),
        deviation_points=max(_int("ORB2_DEVIATION_POINTS", 30), 1),
    )

