from __future__ import annotations

from dataclasses import dataclass
from datetime import time
import os
from pathlib import Path

from dotenv import load_dotenv


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _time(name: str, default: str) -> time:
    h, m = (int(v) for v in os.getenv(name, default).split(":", 1))
    return time(h, m)


@dataclass(frozen=True, slots=True)
class Config:
    root: Path
    auto_discover: bool
    symbol_override: str
    aliases: tuple[str, ...]
    pip_size: float
    enable_trading: bool
    dry_run: bool
    demo_only: bool
    magic: int
    order_comment: str
    risk_mode: str
    risk_percent: float
    fixed_lot: float
    max_risk_cash: float
    max_daily_loss_pct: float
    max_combined_risk_pct: float
    max_spread_pips: float
    max_slippage_pips: float
    min_stop_pips: float
    max_stop_pips: float
    friday_filter: bool
    news_filter_enabled: bool
    news_blackout_minutes: int
    strategy_a_enabled: bool
    ny_open: time
    a_stop_pips: float
    a_target_pips: float
    a_runner_method: str
    a_trail_buffer_pips: float
    a_break_even_r: float
    a_force_exit: time
    strategy_b_enabled: bool
    b1_enabled: bool
    b2_enabled: bool
    second_start: time
    second_end: time
    doji_body_pips: float
    b1_stop_reference: str
    b1_stop_buffer_pips: float
    b1_rr: float
    b2_pullback_mode: str
    b2_entry_pips: float
    b2_stop_pips: float
    b2_rr: float
    b2_expiry: time
    london_start: time
    starting_balance: float
    commission_per_lot: float
    slippage_pips: float
    data_dir: Path
    report_dir: Path
    log_dir: Path
    state_dir: Path


def load_config(env_file: str | Path | None = None) -> Config:
    env_path = Path(env_file).resolve() if env_file else Path.cwd() / ".env"
    load_dotenv(env_path)
    root = env_path.parent
    aliases = tuple(
        x.strip().upper()
        for x in os.getenv(
            "US100_ALIASES", "US100,NAS100,USTEC,UT100,NDX100,NDX,NASDAQ"
        ).split(",")
        if x.strip()
    )
    rel = lambda name, default: (root / os.getenv(name, default)).resolve()
    return Config(
        root=root,
        auto_discover=_bool("AUTO_DISCOVER_SYMBOL", True),
        symbol_override=os.getenv("US100_SYMBOL", "").strip(),
        aliases=aliases,
        pip_size=float(os.getenv("US100_PIP_SIZE", "1.0")),
        enable_trading=_bool("ENABLE_TRADING"),
        dry_run=_bool("DRY_RUN", True),
        demo_only=_bool("DEMO_ONLY", True),
        magic=int(os.getenv("MAGIC_NUMBER", "1000930")),
        order_comment=os.getenv("ORDER_COMMENT", "US100_NY")[:20],
        risk_mode=os.getenv("RISK_MODE", "percent"),
        risk_percent=float(os.getenv("RISK_PERCENT", "0.50")),
        fixed_lot=float(os.getenv("FIXED_LOT", "0.01")),
        max_risk_cash=float(os.getenv("MAX_RISK_CASH", "100")),
        max_daily_loss_pct=float(os.getenv("MAX_DAILY_LOSS_PERCENT", "1")),
        max_combined_risk_pct=float(os.getenv("MAX_COMBINED_RISK_PERCENT", "1")),
        max_spread_pips=float(os.getenv("MAX_SPREAD_PIPS", "5")),
        max_slippage_pips=float(os.getenv("MAX_SLIPPAGE_PIPS", "2")),
        min_stop_pips=float(os.getenv("MIN_STOP_PIPS", "10")),
        max_stop_pips=float(os.getenv("MAX_STOP_PIPS", "250")),
        friday_filter=_bool("FRIDAY_FILTER"),
        news_filter_enabled=_bool("NEWS_FILTER_ENABLED"),
        news_blackout_minutes=int(os.getenv("NEWS_BLACKOUT_MINUTES", "15")),
        strategy_a_enabled=_bool("STRATEGY_A_ENABLED", True),
        ny_open=_time("NY_OPEN", "09:30"),
        a_stop_pips=float(os.getenv("A_STOP_PIPS", "50")),
        a_target_pips=float(os.getenv("A_FIXED_TARGET_PIPS", "100")),
        a_runner_method=os.getenv("A_RUNNER_METHOD", "previous_m15"),
        a_trail_buffer_pips=float(os.getenv("A_TRAIL_BUFFER_PIPS", "0")),
        a_break_even_r=float(os.getenv("A_BREAK_EVEN_R", "0")),
        a_force_exit=_time("A_FORCE_EXIT", "15:55"),
        strategy_b_enabled=_bool("STRATEGY_B_ENABLED", True),
        b1_enabled=_bool("B1_ENABLED", True),
        b2_enabled=_bool("B2_ENABLED", True),
        second_start=_time("SECOND_CANDLE_START", "09:45"),
        second_end=_time("SECOND_CANDLE_END", "10:00"),
        doji_body_pips=float(os.getenv("DOJI_BODY_PIPS", "2")),
        b1_stop_reference=os.getenv("B1_STOP_REFERENCE", "london_session_high"),
        b1_stop_buffer_pips=float(os.getenv("B1_STOP_BUFFER_PIPS", "2")),
        b1_rr=float(os.getenv("B1_RR", "2")),
        b2_pullback_mode=os.getenv("B2_PULLBACK_MODE", "close_plus_fixed"),
        b2_entry_pips=float(os.getenv("B2_ENTRY_PIPS", "50")),
        b2_stop_pips=float(os.getenv("B2_STOP_PIPS", "100")),
        b2_rr=float(os.getenv("B2_RR", "2")),
        b2_expiry=_time("B2_EXPIRY", "12:00"),
        london_start=_time("LONDON_START", "03:00"),
        starting_balance=float(os.getenv("STARTING_BALANCE", "10000")),
        commission_per_lot=float(os.getenv("COMMISSION_PER_LOT_ROUND_TURN", "0")),
        slippage_pips=float(os.getenv("SLIPPAGE_PIPS", "1")),
        data_dir=rel("DATA_DIR", "data"),
        report_dir=rel("REPORT_DIR", "reports"),
        log_dir=rel("LOG_DIR", "logs"),
        state_dir=rel("STATE_DIR", "state"),
    )
