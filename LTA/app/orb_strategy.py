from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from .session_time import (
    DEFAULT_DATA_TIMEZONE,
    DEFAULT_SESSION_TIMEZONE,
    date_in_timezone,
    now_naive,
    parse_hhmm,
    session_bounds as timezone_session_bounds,
)


@dataclass(frozen=True)
class ORBSettings:
    session_start: str = "09:30"
    session_end: str = "16:00"
    range_minutes: int = 30
    reward_risk: float = 2.0
    buffer_atr: float = 0.0
    min_range_atr: float = 0.0
    max_range_atr: float = 999.0
    max_signal_age_minutes: int = 30
    session_timezone: str = DEFAULT_SESSION_TIMEZONE
    data_timezone: str = DEFAULT_DATA_TIMEZONE


def session_bounds(session_day: date, settings: ORBSettings) -> tuple[datetime, datetime, datetime]:
    start, end = timezone_session_bounds(
        session_day,
        settings.session_start,
        settings.session_end,
        settings.session_timezone,
        settings.data_timezone,
    )
    range_end = start + timedelta(minutes=max(1, int(settings.range_minutes)))
    return start, range_end, end


def to_frame(candles: pd.DataFrame) -> pd.DataFrame:
    df = candles.copy()
    df["time"] = pd.to_datetime(df["time"])
    for column in ("open", "high", "low", "close"):
        df[column] = pd.to_numeric(df[column], errors="coerce")
    if "volume" not in df.columns:
        df["volume"] = 1.0
    return df.dropna(subset=["time", "open", "high", "low", "close"]).reset_index(drop=True)


def atr(candles: pd.DataFrame, period: int = 14) -> float:
    df = to_frame(candles)
    if len(df) < 2:
        return 0.0
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    previous_close = close.shift(1)
    tr = pd.concat([(high - low), (high - previous_close).abs(), (low - previous_close).abs()], axis=1).max(axis=1)
    value = float(tr.tail(period).mean())
    return value if np.isfinite(value) and value > 0 else 0.0


def _trigger_levels(range_high: float, range_low: float, atr_value: float, settings: ORBSettings) -> tuple[float, float]:
    buffer = max(0.0, float(settings.buffer_atr)) * max(0.0, float(atr_value))
    return range_high + buffer, range_low - buffer


def target_for(direction: str, entry: float, stop_loss: float, reward_risk: float) -> float:
    risk = abs(float(entry) - float(stop_loss))
    if direction.upper() == "BUY":
        return float(entry) + risk * float(reward_risk)
    return float(entry) - risk * float(reward_risk)


def build_orb_context(
    candles: pd.DataFrame,
    settings: ORBSettings,
    session_day: date | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    df = to_frame(candles)
    now = now or now_naive(settings.data_timezone)
    session_day = session_day or date_in_timezone(now, settings.data_timezone, settings.session_timezone)
    session_start, range_end, session_end = session_bounds(session_day, settings)
    range_bars = df[(df["time"] >= session_start) & (df["time"] < range_end)]
    prior = df[df["time"] < session_start].tail(64)
    atr_value = atr(prior, 14) if len(prior) >= 14 else atr(df[df["time"] < range_end].tail(64), 14)
    if range_bars.empty:
        return {
            "ready": False,
            "reason": "Opening range is not formed yet.",
            "session_start": session_start,
            "range_end": range_end,
            "session_end": session_end,
            "session_timezone": settings.session_timezone,
            "data_timezone": settings.data_timezone,
            "range_bars": 0,
            "atr": atr_value,
        }
    range_high = float(range_bars["high"].max())
    range_low = float(range_bars["low"].min())
    width = range_high - range_low
    range_atr = width / atr_value if atr_value > 0 else None
    buy_trigger, sell_trigger = _trigger_levels(range_high, range_low, atr_value, settings)
    ready = now >= range_end
    reason = "Opening range is complete." if ready else "Opening range is still building."
    if ready and range_atr is not None:
        if range_atr < settings.min_range_atr:
            reason = f"Opening range is too narrow: {range_atr:.2f} ATR."
            ready = False
        elif range_atr > settings.max_range_atr:
            reason = f"Opening range is too wide: {range_atr:.2f} ATR."
            ready = False
    return {
        "ready": ready,
        "reason": reason,
        "session_start": session_start,
        "range_end": range_end,
        "session_end": session_end,
        "session_timezone": settings.session_timezone,
        "data_timezone": settings.data_timezone,
        "range_bars": int(len(range_bars)),
        "range_high": range_high,
        "range_low": range_low,
        "range_width": width,
        "range_atr": range_atr,
        "atr": atr_value,
        "buy_trigger": buy_trigger,
        "sell_trigger": sell_trigger,
    }


def find_first_breakout(candles: pd.DataFrame, context: dict[str, Any], now: datetime | None = None) -> dict[str, Any] | None:
    df = to_frame(candles)
    data_timezone = str(context.get("data_timezone") or DEFAULT_DATA_TIMEZONE)
    now = now or now_naive(data_timezone)
    if not context.get("ready"):
        return None
    range_end = context["range_end"]
    session_end = context["session_end"]
    post = df[(df["time"] >= range_end) & (df["time"] <= min(now, session_end))]
    buy_trigger = float(context["buy_trigger"])
    sell_trigger = float(context["sell_trigger"])
    for index, row in post.iterrows():
        high = float(row["high"])
        low = float(row["low"])
        hit_buy = high >= buy_trigger
        hit_sell = low <= sell_trigger
        if hit_buy and hit_sell:
            return {
                "direction": None,
                "index": int(index),
                "time": pd.Timestamp(row["time"]).to_pydatetime(),
                "reason": "Both ORB sides broke in the same candle; skipped as ambiguous.",
            }
        if hit_buy:
            return {"direction": "BUY", "index": int(index), "time": pd.Timestamp(row["time"]).to_pydatetime()}
        if hit_sell:
            return {"direction": "SELL", "index": int(index), "time": pd.Timestamp(row["time"]).to_pydatetime()}
    return None


def confirmed_orb_signal(
    candles: pd.DataFrame,
    symbol: str,
    timeframe: str,
    settings: ORBSettings,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    now = now or datetime.now()
    context = build_orb_context(candles, settings, now=now)
    breakout = find_first_breakout(candles, context, now=now)
    if not context.get("ready") or breakout is None:
        return None
    direction = breakout.get("direction")
    if direction not in {"BUY", "SELL"}:
        return None
    breakout_time = breakout["time"]
    if now - breakout_time > timedelta(minutes=max(1, int(settings.max_signal_age_minutes))):
        return None

    df = to_frame(candles)
    signal_row = df.iloc[int(breakout["index"])]
    entry = float(signal_row["close"])
    if direction == "BUY":
        stop_loss = float(context["range_low"])
        trigger_price = float(context["buy_trigger"])
    else:
        stop_loss = float(context["range_high"])
        trigger_price = float(context["sell_trigger"])
    if entry <= 0 or stop_loss <= 0 or entry == stop_loss:
        return None
    take_profit = target_for(direction, entry, stop_loss, settings.reward_risk)
    range_atr = context.get("range_atr")
    score = 95
    if range_atr is not None and 0.5 <= float(range_atr) <= 2.0:
        score = 100
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "direction": direction,
        "setup_grade": "ORB",
        "setup_score": score,
        "profile_type": "Opening Range",
        "key_level": f"ORB {settings.range_minutes}m {settings.session_start}",
        "entry_model": "Opening Range Breakout",
        "execution_type": "MARKET",
        "trigger_price": trigger_price,
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "risk_reward": float(settings.reward_risk),
        "timestamp": breakout_time,
        "status": "allowed",
        "orb": {
            "session_start": context["session_start"].isoformat(sep=" ", timespec="seconds"),
            "range_end": context["range_end"].isoformat(sep=" ", timespec="seconds"),
            "session_end": context["session_end"].isoformat(sep=" ", timespec="seconds"),
            "session_timezone": settings.session_timezone,
            "data_timezone": settings.data_timezone,
            "range_high": context["range_high"],
            "range_low": context["range_low"],
            "range_width": context["range_width"],
            "range_atr": context.get("range_atr"),
            "buy_trigger": context["buy_trigger"],
            "sell_trigger": context["sell_trigger"],
        },
        "reasons": [
            f"{settings.range_minutes} minute opening range completed at {settings.session_start}.",
            f"ORB session is interpreted in {settings.session_timezone} and converted to {settings.data_timezone} candles.",
            f"{direction} breakout confirmed at {breakout_time.isoformat(sep=' ', timespec='seconds')}.",
        ],
    }


def pending_orb_signals(
    candles: pd.DataFrame,
    symbol: str,
    timeframe: str,
    settings: ORBSettings,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    now = now or now_naive(settings.data_timezone)
    context = build_orb_context(candles, settings, now=now)
    if not context.get("ready") or now > context["session_end"]:
        return []
    if find_first_breakout(candles, context, now=now):
        return []
    signals: list[dict[str, Any]] = []
    for direction, trigger, stop in (
        ("BUY", float(context["buy_trigger"]), float(context["range_low"])),
        ("SELL", float(context["sell_trigger"]), float(context["range_high"])),
    ):
        if trigger <= 0 or stop <= 0 or trigger == stop:
            continue
        signals.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "direction": direction,
                "setup_grade": "ORB",
                "setup_score": 95,
                "profile_type": "Opening Range",
                "key_level": f"ORB {settings.range_minutes}m {settings.session_start}",
                "entry_model": "Opening Range Breakout Pending Stop",
                "execution_type": "PENDING",
                "pending_order_type": f"{direction}_STOP",
                "trigger_price": trigger,
                "entry": trigger,
                "stop_loss": stop,
                "take_profit": target_for(direction, trigger, stop, settings.reward_risk),
                "risk_reward": float(settings.reward_risk),
                "timestamp": context["range_end"],
                "status": "preplace",
                "orb": {
                    "session_start": context["session_start"].isoformat(sep=" ", timespec="seconds"),
                    "range_end": context["range_end"].isoformat(sep=" ", timespec="seconds"),
                    "session_end": context["session_end"].isoformat(sep=" ", timespec="seconds"),
                    "session_timezone": settings.session_timezone,
                    "data_timezone": settings.data_timezone,
                    "range_high": context["range_high"],
                    "range_low": context["range_low"],
                    "range_width": context["range_width"],
                    "range_atr": context.get("range_atr"),
                    "buy_trigger": context["buy_trigger"],
                    "sell_trigger": context["sell_trigger"],
                },
                "reasons": [
                    f"{settings.range_minutes} minute opening range is complete.",
                    f"ORB session is interpreted in {settings.session_timezone} and converted to {settings.data_timezone} candles.",
                    f"Pending {direction}_STOP would enter only if price breaks the range.",
                ],
            }
        )
    return signals
