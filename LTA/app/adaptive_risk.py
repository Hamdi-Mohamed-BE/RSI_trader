from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import os
from typing import Any, TYPE_CHECKING

import numpy as np
import pandas as pd

from .mt5_client import TIMEFRAME_MINUTES

if TYPE_CHECKING:
    from .mt5_client import MT5Client


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(float(os.getenv(name, str(default)) or default))
    except ValueError:
        return default


@dataclass(frozen=True)
class DynamicStopSettings:
    enabled: bool = True
    atr_period: int = 14
    base_atr: float = 1.5
    volatility_lookback: int = 50
    volume_lookback: int = 30
    high_volatility_ratio: float = 1.2
    high_volume_ratio: float = 1.35
    max_atr: float = 3.5
    max_widen_factor: float = 2.5


@dataclass(frozen=True)
class SmartExitSettings:
    enabled: bool = True
    timeframe: str = "M15"
    lookback_bars: int = 100
    atr_period: int = 14
    ema_fast: int = 9
    ema_slow: int = 21
    min_bars_open: int = 2
    profitable_confirmations: int = 1
    losing_confirmations: int = 2
    adverse_entry_atr: float = 0.25
    momentum_body_atr: float = 0.65
    momentum_volume_ratio: float = 1.3
    structure_lookback: int = 8


def dynamic_stop_settings(prefix: str) -> DynamicStopSettings:
    key = prefix.rstrip("_").upper()
    return DynamicStopSettings(
        enabled=_env_bool(f"{key}_DYNAMIC_STOP_ENABLED", True),
        atr_period=max(2, _env_int(f"{key}_DYNAMIC_STOP_ATR_PERIOD", 14)),
        base_atr=max(0.1, _env_float(f"{key}_DYNAMIC_STOP_BASE_ATR", 1.5)),
        volatility_lookback=max(20, _env_int(f"{key}_DYNAMIC_STOP_VOLATILITY_LOOKBACK", 50)),
        volume_lookback=max(10, _env_int(f"{key}_DYNAMIC_STOP_VOLUME_LOOKBACK", 30)),
        high_volatility_ratio=max(1.0, _env_float(f"{key}_DYNAMIC_STOP_HIGH_VOL_RATIO", 1.2)),
        high_volume_ratio=max(1.0, _env_float(f"{key}_DYNAMIC_STOP_HIGH_VOLUME_RATIO", 1.35)),
        max_atr=max(0.5, _env_float(f"{key}_DYNAMIC_STOP_MAX_ATR", 3.5)),
        max_widen_factor=max(1.0, _env_float(f"{key}_DYNAMIC_STOP_MAX_WIDEN_FACTOR", 2.5)),
    )


def smart_exit_settings(prefix: str) -> SmartExitSettings:
    key = prefix.rstrip("_").upper()
    return SmartExitSettings(
        enabled=_env_bool(f"{key}_SMART_EXIT_ENABLED", True),
        timeframe=(os.getenv(f"{key}_SMART_EXIT_TIMEFRAME", "M15").strip().upper() or "M15"),
        lookback_bars=max(40, _env_int(f"{key}_SMART_EXIT_LOOKBACK_BARS", 100)),
        atr_period=max(2, _env_int(f"{key}_SMART_EXIT_ATR_PERIOD", 14)),
        ema_fast=max(2, _env_int(f"{key}_SMART_EXIT_EMA_FAST", 9)),
        ema_slow=max(3, _env_int(f"{key}_SMART_EXIT_EMA_SLOW", 21)),
        min_bars_open=max(1, _env_int(f"{key}_SMART_EXIT_MIN_BARS_OPEN", 2)),
        profitable_confirmations=max(1, _env_int(f"{key}_SMART_EXIT_PROFIT_CONFIRMATIONS", 1)),
        losing_confirmations=max(1, _env_int(f"{key}_SMART_EXIT_LOSS_CONFIRMATIONS", 2)),
        adverse_entry_atr=max(0.0, _env_float(f"{key}_SMART_EXIT_ADVERSE_ENTRY_ATR", 0.25)),
        momentum_body_atr=max(0.1, _env_float(f"{key}_SMART_EXIT_MOMENTUM_BODY_ATR", 0.65)),
        momentum_volume_ratio=max(1.0, _env_float(f"{key}_SMART_EXIT_MOMENTUM_VOLUME_RATIO", 1.3)),
        structure_lookback=max(3, _env_int(f"{key}_SMART_EXIT_STRUCTURE_LOOKBACK", 8)),
    )


def _frame(candles: pd.DataFrame) -> pd.DataFrame:
    df = candles.copy()
    for column in ("open", "high", "low", "close"):
        df[column] = pd.to_numeric(df[column], errors="coerce")
    volume_column = "volume" if "volume" in df.columns else "tick_volume" if "tick_volume" in df.columns else None
    if volume_column is None:
        df["volume"] = 1.0
    elif volume_column != "volume":
        df["volume"] = pd.to_numeric(df[volume_column], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(1.0).clip(lower=1.0)
    return df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)


def _closed_frame(candles: pd.DataFrame) -> pd.DataFrame:
    df = _frame(candles)
    return df.iloc[:-1].copy() if len(df) > 2 else df


def _true_range(df: pd.DataFrame) -> pd.Series:
    previous_close = df["close"].shift(1)
    return pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def _level_at_r(entry: float, risk: float, direction: str, multiple: float) -> float:
    return entry + risk * multiple if direction == "BUY" else entry - risk * multiple


def apply_dynamic_stop(
    signal: dict[str, Any],
    candles: pd.DataFrame | None,
    settings: DynamicStopSettings,
    last_bar_is_closed: bool = False,
) -> dict[str, Any]:
    if not settings.enabled or candles is None:
        return signal
    df = _frame(candles) if last_bar_is_closed else _closed_frame(candles)
    required = max(settings.atr_period + 3, settings.volume_lookback + 3)
    if len(df) < required:
        return signal

    try:
        entry = float(signal.get("trigger_price") or signal.get("entry") or 0.0)
        old_stop = float(signal.get("stop_loss") or 0.0)
        direction = str(signal.get("direction") or "").upper()
    except (TypeError, ValueError):
        return signal
    old_risk = abs(entry - old_stop)
    if direction not in {"BUY", "SELL"} or entry <= 0 or old_stop <= 0 or old_risk <= 0:
        return signal

    atr_series = _true_range(df).rolling(settings.atr_period).mean().dropna()
    if atr_series.empty:
        return signal
    current_atr = float(atr_series.iloc[-1])
    baseline_values = atr_series.tail(settings.volatility_lookback)
    baseline_atr = float(baseline_values.median()) if len(baseline_values) else current_atr
    if not np.isfinite(current_atr) or current_atr <= 0 or baseline_atr <= 0:
        return signal

    recent_volume = float(df["volume"].tail(3).mean())
    volume_history = df["volume"].iloc[:-3].tail(settings.volume_lookback)
    baseline_volume = float(volume_history.median()) if len(volume_history) else recent_volume
    volatility_ratio = current_atr / max(baseline_atr, 1e-12)
    volume_ratio = recent_volume / max(baseline_volume, 1.0)

    volatility_boost = max(0.0, volatility_ratio - 1.0) * 0.55
    volume_boost = max(0.0, volume_ratio - 1.0) * 0.20
    joint_boost = 0.15 if (
        volatility_ratio >= settings.high_volatility_ratio
        and volume_ratio >= settings.high_volume_ratio
    ) else 0.0
    activity_factor = min(settings.max_widen_factor, 1.0 + volatility_boost + volume_boost + joint_boost)
    desired_risk = current_atr * settings.base_atr * activity_factor
    maximum_dynamic_risk = current_atr * settings.max_atr
    new_risk = max(old_risk, min(desired_risk, maximum_dynamic_risk))

    adjusted = dict(signal)
    if new_risk <= old_risk * 1.001:
        adjusted["dynamic_stop"] = {
            "applied": False,
            "reason": "structural_stop_already_wide_enough",
            "atr": current_atr,
            "volatility_ratio": volatility_ratio,
            "volume_ratio": volume_ratio,
            "activity_factor": activity_factor,
            "risk_distance": old_risk,
        }
        return adjusted

    new_stop = entry - new_risk if direction == "BUY" else entry + new_risk
    rr = float(signal.get("configured_risk_reward") or signal.get("risk_reward") or 3.0)
    rr = max(0.5, rr)
    adjusted["original_stop_loss"] = old_stop
    adjusted["stop_loss"] = round(new_stop, 8)
    adjusted["take_profit"] = round(_level_at_r(entry, new_risk, direction, rr), 8)
    adjusted["risk_reward"] = rr
    for stage in range(1, 6):
        adjusted[f"tp{stage}"] = (
            round(_level_at_r(entry, new_risk, direction, float(stage)), 8)
            if rr >= stage
            else None
        )
    adjusted["dynamic_stop"] = {
        "applied": True,
        "atr": current_atr,
        "baseline_atr": baseline_atr,
        "volatility_ratio": volatility_ratio,
        "volume_ratio": volume_ratio,
        "activity_factor": activity_factor,
        "old_risk_distance": old_risk,
        "new_risk_distance": new_risk,
    }
    reasons = list(adjusted.get("reasons") or [])
    reasons.append(
        f"Dynamic stop widened to {new_risk / current_atr:.2f} ATR; lot sizing must preserve the configured dollar-risk cap."
    )
    adjusted["reasons"] = list(dict.fromkeys(reasons))
    return adjusted


def evaluate_setup_validity(
    candles: pd.DataFrame,
    direction: str,
    entry: float,
    profit: float,
    settings: SmartExitSettings,
    last_bar_is_closed: bool = False,
) -> dict[str, Any]:
    df = _frame(candles) if last_bar_is_closed else _closed_frame(candles)
    required = max(settings.ema_slow + 3, settings.atr_period + 3, settings.structure_lookback + 3)
    if len(df) < required:
        return {"invalid": False, "score": 0, "reasons": ["not_enough_closed_bars"]}

    direction = direction.upper()
    atr_series = _true_range(df).rolling(settings.atr_period).mean().dropna()
    if direction not in {"BUY", "SELL"} or atr_series.empty:
        return {"invalid": False, "score": 0, "reasons": ["invalid_direction_or_atr"]}
    atr = float(atr_series.iloc[-1])
    if atr <= 0:
        return {"invalid": False, "score": 0, "reasons": ["invalid_atr"]}

    fast = df["close"].ewm(span=settings.ema_fast, adjust=False).mean()
    slow = df["close"].ewm(span=settings.ema_slow, adjust=False).mean()
    latest = df.iloc[-1]
    last_two = df.tail(2)
    previous_structure = df.iloc[-settings.structure_lookback - 1 : -1]
    volume_baseline = float(df["volume"].iloc[:-1].tail(30).median())
    volume_ratio = float(latest["volume"]) / max(volume_baseline, 1.0)
    body = abs(float(latest["close"]) - float(latest["open"]))

    if direction == "BUY":
        trend_reversal = bool(fast.iloc[-1] < slow.iloc[-1] and (last_two["close"] < fast.tail(2)).all())
        failed_entry = bool((last_two["close"] < entry - atr * settings.adverse_entry_atr).all())
        adverse_momentum = bool(float(latest["close"]) < float(latest["open"]) and body >= atr * settings.momentum_body_atr)
        structure_break = bool(float(latest["close"]) < float(previous_structure["low"].min()))
    else:
        trend_reversal = bool(fast.iloc[-1] > slow.iloc[-1] and (last_two["close"] > fast.tail(2)).all())
        failed_entry = bool((last_two["close"] > entry + atr * settings.adverse_entry_atr).all())
        adverse_momentum = bool(float(latest["close"]) > float(latest["open"]) and body >= atr * settings.momentum_body_atr)
        structure_break = bool(float(latest["close"]) > float(previous_structure["high"].max()))
    adverse_volume_momentum = adverse_momentum and volume_ratio >= settings.momentum_volume_ratio

    score = 0
    reasons: list[str] = []
    if trend_reversal:
        score += 1
        reasons.append("ema_trend_reversed")
    if failed_entry:
        score += 1
        reasons.append("two_closes_failed_entry")
    if adverse_volume_momentum:
        score += 1
        reasons.append("high_volume_adverse_momentum")
    if structure_break:
        score += 2
        reasons.append("adverse_structure_break")

    required_confirmations = (
        settings.profitable_confirmations if profit > 0 else settings.losing_confirmations
    )
    return {
        "invalid": score >= required_confirmations,
        "score": score,
        "required_confirmations": required_confirmations,
        "reasons": reasons,
        "atr": atr,
        "volume_ratio": volume_ratio,
        "profit": profit,
    }


def maybe_close_invalid_position(
    client: MT5Client,
    position: dict[str, Any],
    settings: SmartExitSettings,
    live_trading: bool,
    now: datetime | None = None,
    comment: str = "Smart invalidation exit",
) -> dict[str, Any] | None:
    if not settings.enabled:
        return None
    now = now or datetime.now()
    timeframe = settings.timeframe if settings.timeframe in TIMEFRAME_MINUTES else "M15"
    minutes = TIMEFRAME_MINUTES[timeframe]
    opened_timestamp = int(position.get("time") or 0)
    elapsed_seconds = datetime.now().timestamp() - opened_timestamp if opened_timestamp else None
    if elapsed_seconds is not None and elapsed_seconds < minutes * settings.min_bars_open * 60:
        return None

    symbol = str(position.get("symbol") or "")
    start = now - timedelta(minutes=minutes * (settings.lookback_bars + 10))
    candles = client.fetch_candles(symbol, timeframe, start, now, max_bars=settings.lookback_bars + 10)
    if candles is None:
        return None
    direction = "SELL" if int(position.get("type") or 0) == 1 else "BUY"
    evaluation = evaluate_setup_validity(
        candles,
        direction=direction,
        entry=float(position.get("price_open") or 0.0),
        profit=float(position.get("profit") or 0.0),
        settings=settings,
    )
    if not evaluation.get("invalid"):
        return None

    result = client.close_position(
        ticket=int(position.get("ticket") or 0),
        symbol=symbol,
        direction=direction,
        volume=float(position.get("volume") or 0.0),
        comment=comment,
        live_trading=live_trading,
    )
    return {
        "status": "closed" if result.get("closed") else "dry_run" if result.get("dry_run") else "close_failed",
        "ticket": int(position.get("ticket") or 0),
        "symbol": symbol,
        "direction": direction,
        "evaluation": evaluation,
        "result": result,
    }
