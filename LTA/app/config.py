from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os

from .models import DEFAULT_SYMBOL_LOTS, TRADE_SYMBOLS


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"
DATA_DIR = PROJECT_ROOT / "data"
PROMPT_PATH = PROJECT_ROOT / "LTA_BASE_TRADING_PROMPT.md"


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class AppConfig:
    live_trading: bool = False
    starting_balance: float = 1000.0
    symbol_lots: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_SYMBOL_LOTS)
    )
    max_risk_per_trade_percent: float = 1.0
    max_daily_loss_percent: float = 3.0
    max_total_drawdown_percent: float = 8.0
    max_trades_per_day: int = 3
    max_lot_risk_pct: float = 3.0
    max_spread_risk_percent: float = 15.0
    max_spread_points: float = 0.0
    min_setup_score: int = 90
    min_risk_reward: float = 5.0
    backtest_signal_stride: int = 3


def load_config() -> AppConfig:
    _load_dotenv(PROJECT_ROOT / ".env")
    return AppConfig(
        live_trading=_bool_env("LIVE_TRADING", False),
        starting_balance=_float_env("START_BALANCE", 1000.0),
        symbol_lots={
            symbol: _float_env(f"{symbol}_LOT", DEFAULT_SYMBOL_LOTS[symbol])
            for symbol in TRADE_SYMBOLS
        },
        max_risk_per_trade_percent=_float_env("MAX_RISK_PER_TRADE_PERCENT", 1.0),
        max_daily_loss_percent=_float_env("MAX_DAILY_LOSS_PERCENT", 3.0),
        max_total_drawdown_percent=_float_env("MAX_TOTAL_DRAWDOWN_PERCENT", 8.0),
        max_trades_per_day=_int_env("MAX_TRADES_PER_DAY", 3),
        max_lot_risk_pct=_float_env("MAX_LOT_RISK_PCT", _float_env("max_lot_risk_pct", 3.0)),
        max_spread_risk_percent=_float_env("MAX_SPREAD_RISK_PERCENT", 15.0),
        max_spread_points=_float_env("MAX_SPREAD_POINTS", 0.0),
        min_setup_score=_int_env("MIN_SETUP_SCORE", 90),
        min_risk_reward=_float_env("MIN_RISK_REWARD", 5.0),
        backtest_signal_stride=_int_env("BACKTEST_SIGNAL_STRIDE", 3),
    )
