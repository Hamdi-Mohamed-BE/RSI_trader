from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import time
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from .symbols import canonical_for_symbol


DEFAULT_SYMBOLS = (
    "XAUUSD",
    "XAGUSD",
    "BTCUSD",
    "ETHUSD",
    "EURJPY",
    "AUDCAD",
    "AUDCHF",
    "GBPJPY",
)


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _time(name: str, default: str) -> time:
    value = os.getenv(name, default)
    hour, minute = (int(part) for part in value.split(":", maxsplit=1))
    return time(hour, minute)


@dataclass(frozen=True, slots=True)
class StrategyConfig:
    entry_mode: str = "confirmed_close"
    stop_mode: str = "midpoint"
    rr: float = 1.5
    exit_mode: str = "fixed"
    trail_start_r: float = 1.0
    trail_distance_r: float = 1.0
    buffer_range_fraction: float = 0.03
    min_range_adr_fraction: float = 0.05
    max_range_adr_fraction: float = 0.50
    retest_bars: int = 4
    risk_pct: float = 3.0
    starting_balance: float = 1_000.0
    asia_start: time = time(0, 0)
    asia_end: time = time(8, 0)
    entry_cutoff: time = time(13, 0)
    force_exit: time = time(17, 0)
    adr_days: int = 14

    def evolved(self, **changes: object) -> "StrategyConfig":
        return replace(self, **changes)


@dataclass(frozen=True, slots=True)
class AppConfig:
    terminal_path: Path
    login: int | None
    password: str | None
    server: str | None
    enable_trading: bool
    dry_run: bool
    magic: int
    max_basket_risk_pct: float
    log_dir: Path
    log_level: str
    symbols: tuple[str, ...]
    strategy: StrategyConfig
    symbol_strategies: dict[str, StrategyConfig] = field(default_factory=dict)

    def strategy_for(self, symbol: str) -> StrategyConfig:
        direct = self.symbol_strategies.get(symbol)
        if direct is not None:
            return direct
        canonical = canonical_for_symbol(symbol, tuple(self.symbol_strategies))
        if canonical is None:
            return self.strategy
        return self.symbol_strategies[canonical]


def load_config(env_file: str | Path | None = None) -> AppConfig:
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()

    login_text = os.getenv("MT5_LOGIN", "").strip()
    strategy = StrategyConfig(
        entry_mode=os.getenv("ENTRY_MODE", "confirmed_close"),
        stop_mode=os.getenv("STOP_MODE", "midpoint"),
        rr=float(os.getenv("RR", "1.5")),
        exit_mode=os.getenv("EXIT_MODE", "fixed"),
        trail_start_r=float(os.getenv("TRAIL_START_R", "1.0")),
        trail_distance_r=float(os.getenv("TRAIL_DISTANCE_R", "1.0")),
        buffer_range_fraction=float(os.getenv("BUFFER_RANGE_FRACTION", "0.03")),
        min_range_adr_fraction=float(os.getenv("MIN_RANGE_ADR_FRACTION", "0.05")),
        max_range_adr_fraction=float(os.getenv("MAX_RANGE_ADR_FRACTION", "0.50")),
        retest_bars=int(os.getenv("RETEST_BARS", "4")),
        risk_pct=float(os.getenv("RISK_PCT", "3.0")),
        starting_balance=float(os.getenv("STARTING_BALANCE", "1000")),
        asia_start=_time("ASIA_START_UTC", "00:00"),
        asia_end=_time("ASIA_END_UTC", "08:00"),
        entry_cutoff=_time("ENTRY_CUTOFF_UTC", "13:00"),
        force_exit=_time("FORCE_EXIT_UTC", "17:00"),
        adr_days=int(os.getenv("ADR_DAYS", "14")),
    )
    symbol_strategies: dict[str, StrategyConfig] = {}
    symbol_config_text = os.getenv("SYMBOL_CONFIG_PATH", "").strip()
    if symbol_config_text:
        symbol_config_path = Path(symbol_config_text)
        if not symbol_config_path.is_absolute() and env_file:
            symbol_config_path = Path(env_file).resolve().parent / symbol_config_path
        if symbol_config_path.exists():
            payload = json.loads(symbol_config_path.read_text(encoding="utf-8"))
            symbol_strategies = {
                symbol: strategy.evolved(**record["strategy"])
                for symbol, record in payload.items()
            }
    symbols_text = os.getenv("SYMBOLS", "").strip()
    if symbols_text:
        symbols = tuple(
            item.strip() for item in symbols_text.split(",") if item.strip()
        )
    elif symbol_strategies:
        symbols = tuple(symbol_strategies)
    else:
        symbols = DEFAULT_SYMBOLS
    return AppConfig(
        terminal_path=Path(
            os.getenv("MT5_TERMINAL_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
        ),
        login=int(login_text) if login_text else None,
        password=os.getenv("MT5_PASSWORD") or None,
        server=os.getenv("MT5_SERVER") or None,
        enable_trading=_bool("ENABLE_TRADING"),
        dry_run=_bool("DRY_RUN", True),
        magic=int(os.getenv("MAGIC", "290729")),
        max_basket_risk_pct=float(os.getenv("MAX_BASKET_RISK_PCT", "6.0")),
        log_dir=Path(os.getenv("LOG_DIR", "logs")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        symbols=symbols,
        strategy=strategy,
        symbol_strategies=symbol_strategies,
    )
