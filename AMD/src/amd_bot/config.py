from __future__ import annotations

from dataclasses import dataclass
from datetime import time
import os
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_SYMBOLS = (
    "XAUUSD",
)


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _time(name: str, default: str) -> time:
    value = os.getenv(name, default).strip()
    hour, minute = (int(part) for part in value.split(":", maxsplit=1))
    return time(hour, minute)


@dataclass(frozen=True, slots=True)
class Config:
    strategy_model: str
    symbols: tuple[str, ...]
    starting_balance: float
    risk_pct: float
    asia_start: time
    asia_end: time
    london_start: time
    london_end: time
    ny_start: time
    ny_cutoff: time
    force_exit: time
    ny_rr: float
    ny_fallback_rr: float
    ny_fallback_minutes: int
    ny_entry_buffer_spreads: float
    ny_entry_mode: str
    lock_trigger_r: float
    lock_profit_r: float
    ny_stop_buffer_fraction: float
    regime_filter_enabled: bool
    regime_atr_days: int
    regime_atr_pct_min: float
    regime_atr_pct_max: float
    regime_use_relative_atr: bool
    regime_atr_median_days: int
    regime_atr_ratio_min: float
    regime_atr_ratio_max: float
    regime_asia_median_days: int
    regime_asia_ratio_min: float
    regime_asia_ratio_max: float
    enable_trading: bool
    dry_run: bool
    model_approved: bool
    magic: int
    poll_seconds: int
    deviation_points: int
    log_level: str
    article_enable_fade: bool
    article_enable_distribution: bool
    article_trade_london: bool
    article_trade_new_york: bool
    article_max_trades_per_day: int
    article_fade_rr: float
    article_distribution_rr: float
    article_sweep_min_fraction: float
    article_sweep_max_fraction: float
    article_breakout_fraction: float
    article_retest_tolerance_fraction: float
    article_stop_buffer_fraction: float
    article_volume_factor: float
    article_require_directional_confirmation: bool
    article_min_body_fraction: float
    article_min_close_location: float
    article_fade_reclaim_fraction: float
    article_fade_confirmation_mode: str
    article_fade_mss_lookahead_bars: int
    article_distribution_hold_fraction: float
    article_breakout_max_fraction: float
    article_max_risk_fraction: float
    article_trend_filter_mode: str
    article_trend_fast: int
    article_trend_slow: int
    article_trend_price_alignment: bool
    article_london_window_minutes: int
    article_ny_window_minutes: int
    article_signal_max_age_seconds: int
    root: Path


def load_config(env_path: str | Path | None = None) -> Config:
    root = Path(__file__).resolve().parents[2]
    path = Path(env_path) if env_path else root / ".env"
    load_dotenv(path, override=True)
    symbols = tuple(
        item.strip().upper()
        for item in os.getenv("SYMBOLS", ",".join(DEFAULT_SYMBOLS)).split(",")
        if item.strip()
    )
    return Config(
        strategy_model=os.getenv("STRATEGY_MODEL", "legacy").strip().lower(),
        symbols=symbols,
        starting_balance=float(os.getenv("STARTING_BALANCE", "1000")),
        risk_pct=float(os.getenv("RISK_PCT", "3")),
        asia_start=_time("ASIA_START_UTC", "00:00"),
        asia_end=_time("ASIA_END_UTC", "08:00"),
        london_start=_time("LONDON_CONFIRM_START_UTC", "08:00"),
        london_end=_time("LONDON_CONFIRM_END_UTC", "09:00"),
        ny_start=_time("NY_START_UTC", "13:30"),
        ny_cutoff=_time("NY_SIGNAL_CUTOFF_UTC", "16:00"),
        force_exit=_time("FORCE_EXIT_UTC", "21:00"),
        ny_rr=float(os.getenv("NY_RR", "5")),
        ny_fallback_rr=float(os.getenv("NY_FALLBACK_RR", "4")),
        ny_fallback_minutes=int(os.getenv("NY_FALLBACK_MINUTES", "45")),
        ny_entry_buffer_spreads=float(
            os.getenv("NY_ENTRY_BUFFER_SPREADS", "1")
        ),
        ny_entry_mode=os.getenv("NY_ENTRY_MODE", "dual").strip().lower(),
        lock_trigger_r=float(os.getenv("LOCK_TRIGGER_R", "0.5")),
        lock_profit_r=float(os.getenv("LOCK_PROFIT_R", "0.15")),
        ny_stop_buffer_fraction=float(
            os.getenv("NY_STOP_BUFFER_RANGE_FRACTION", "0.05")
        ),
        regime_filter_enabled=_bool("REGIME_FILTER_ENABLED", False),
        regime_atr_days=int(os.getenv("REGIME_ATR_DAYS", "5")),
        regime_atr_pct_min=float(
            os.getenv("REGIME_ATR_PCT_MIN", "1.5")
        ),
        regime_atr_pct_max=float(
            os.getenv("REGIME_ATR_PCT_MAX", "2.8")
        ),
        regime_use_relative_atr=_bool(
            "REGIME_USE_RELATIVE_ATR", False
        ),
        regime_atr_median_days=int(
            os.getenv("REGIME_ATR_MEDIAN_DAYS", "60")
        ),
        regime_atr_ratio_min=float(
            os.getenv("REGIME_ATR_RATIO_MIN", "0.65")
        ),
        regime_atr_ratio_max=float(
            os.getenv("REGIME_ATR_RATIO_MAX", "1.60")
        ),
        regime_asia_median_days=int(
            os.getenv("REGIME_ASIA_MEDIAN_DAYS", "20")
        ),
        regime_asia_ratio_min=float(
            os.getenv("REGIME_ASIA_RATIO_MIN", "0.40")
        ),
        regime_asia_ratio_max=float(
            os.getenv("REGIME_ASIA_RATIO_MAX", "1.20")
        ),
        enable_trading=_bool("ENABLE_TRADING", False),
        dry_run=_bool("DRY_RUN", True),
        model_approved=_bool("MODEL_APPROVED", False),
        magic=int(os.getenv("MAGIC", "300730")),
        poll_seconds=int(os.getenv("POLL_SECONDS", "15")),
        deviation_points=int(os.getenv("DEVIATION_POINTS", "30")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        article_enable_fade=_bool("ARTICLE_ENABLE_FADE", True),
        article_enable_distribution=_bool(
            "ARTICLE_ENABLE_DISTRIBUTION", True
        ),
        article_trade_london=_bool("ARTICLE_TRADE_LONDON", True),
        article_trade_new_york=_bool("ARTICLE_TRADE_NEW_YORK", False),
        article_max_trades_per_day=int(
            os.getenv("ARTICLE_MAX_TRADES_PER_DAY", "1")
        ),
        article_fade_rr=float(os.getenv("ARTICLE_FADE_RR", "2.0")),
        article_distribution_rr=float(
            os.getenv("ARTICLE_DISTRIBUTION_RR", "2.0")
        ),
        article_sweep_min_fraction=float(
            os.getenv("ARTICLE_SWEEP_MIN_FRACTION", "0.02")
        ),
        article_sweep_max_fraction=float(
            os.getenv("ARTICLE_SWEEP_MAX_FRACTION", "0.60")
        ),
        article_breakout_fraction=float(
            os.getenv("ARTICLE_BREAKOUT_FRACTION", "0.00")
        ),
        article_retest_tolerance_fraction=float(
            os.getenv("ARTICLE_RETEST_TOLERANCE_FRACTION", "0.04")
        ),
        article_stop_buffer_fraction=float(
            os.getenv("ARTICLE_STOP_BUFFER_FRACTION", "0.03")
        ),
        article_volume_factor=float(
            os.getenv("ARTICLE_VOLUME_FACTOR", "0.00")
        ),
        article_require_directional_confirmation=_bool(
            "ARTICLE_REQUIRE_DIRECTIONAL_CONFIRMATION", False
        ),
        article_min_body_fraction=float(
            os.getenv("ARTICLE_MIN_BODY_FRACTION", "0.00")
        ),
        article_min_close_location=float(
            os.getenv("ARTICLE_MIN_CLOSE_LOCATION", "0.00")
        ),
        article_fade_reclaim_fraction=float(
            os.getenv("ARTICLE_FADE_RECLAIM_FRACTION", "0.00")
        ),
        article_fade_confirmation_mode=os.getenv(
            "ARTICLE_FADE_CONFIRMATION_MODE", "immediate"
        ).strip().lower(),
        article_fade_mss_lookahead_bars=int(
            os.getenv("ARTICLE_FADE_MSS_LOOKAHEAD_BARS", "6")
        ),
        article_distribution_hold_fraction=float(
            os.getenv("ARTICLE_DISTRIBUTION_HOLD_FRACTION", "0.00")
        ),
        article_breakout_max_fraction=float(
            os.getenv("ARTICLE_BREAKOUT_MAX_FRACTION", "0.00")
        ),
        article_max_risk_fraction=float(
            os.getenv("ARTICLE_MAX_RISK_FRACTION", "0.00")
        ),
        article_trend_filter_mode=os.getenv(
            "ARTICLE_TREND_FILTER_MODE", "none"
        ).strip().lower(),
        article_trend_fast=int(
            os.getenv("ARTICLE_TREND_FAST", "8")
        ),
        article_trend_slow=int(
            os.getenv("ARTICLE_TREND_SLOW", "24")
        ),
        article_trend_price_alignment=_bool(
            "ARTICLE_TREND_PRICE_ALIGNMENT", True
        ),
        article_london_window_minutes=int(
            os.getenv("ARTICLE_LONDON_WINDOW_MINUTES", "180")
        ),
        article_ny_window_minutes=int(
            os.getenv("ARTICLE_NY_WINDOW_MINUTES", "180")
        ),
        article_signal_max_age_seconds=int(
            os.getenv("ARTICLE_SIGNAL_MAX_AGE_SECONDS", "120")
        ),
        root=root,
    )
