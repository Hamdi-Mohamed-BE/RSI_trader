from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class BPRSettings:
    reward_risk: float = 3.0
    min_score: int = 88
    fvg_lookback_bars: int = 80
    min_gap_atr: float = 0.05
    min_displacement_atr: float = 0.45
    stop_atr_buffer: float = 0.25
    max_zone_atr: float = 1.8
    allow_pending: bool = True
    max_signal_age_bars: int = 48


@dataclass(frozen=True)
class FVG:
    index: int
    time: datetime
    direction: str
    low: float
    high: float
    gap: float
    displacement_atr: float


@dataclass
class BPRZone:
    key: str
    symbol: str
    timeframe: str
    direction: str
    low: float
    high: float
    created_index: int
    created_at: datetime
    older_fvg: FVG
    newer_fvg: FVG
    touched: bool = False

    @property
    def midpoint(self) -> float:
        return (self.low + self.high) / 2.0

    @property
    def width(self) -> float:
        return max(0.0, self.high - self.low)


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(float(os.getenv(name, str(default)) or default))
    except ValueError:
        return default


def settings_from_env() -> BPRSettings:
    return BPRSettings(
        reward_risk=max(0.5, _float_env("BPR_RR", 3.0)),
        min_score=max(0, _int_env("BPR_MIN_SCORE", 88)),
        fvg_lookback_bars=max(10, _int_env("BPR_FVG_LOOKBACK_BARS", 80)),
        min_gap_atr=max(0.0, _float_env("BPR_MIN_GAP_ATR", 0.05)),
        min_displacement_atr=max(0.0, _float_env("BPR_MIN_DISPLACEMENT_ATR", 0.45)),
        stop_atr_buffer=max(0.0, _float_env("BPR_STOP_ATR_BUFFER", 0.25)),
        max_zone_atr=max(0.0, _float_env("BPR_MAX_ZONE_ATR", 1.8)),
        allow_pending=str(os.getenv("BPR_ALLOW_PENDING", "true")).strip().lower() in {"1", "true", "yes", "on"},
        max_signal_age_bars=max(1, _int_env("BPR_MAX_SIGNAL_AGE_BARS", 48)),
    )


def normalize_candles(candles: pd.DataFrame) -> pd.DataFrame:
    df = candles.copy()
    df["time"] = pd.to_datetime(df["time"])
    for column in ("open", "high", "low", "close"):
        df[column] = pd.to_numeric(df[column], errors="coerce")
    if "spread" not in df.columns:
        df["spread"] = 0.0
    df["spread"] = pd.to_numeric(df["spread"], errors="coerce").fillna(0.0)
    return df.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time").reset_index(drop=True)


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    out = normalize_candles(df)
    high = out["high"].astype(float)
    low = out["low"].astype(float)
    close = out["close"].astype(float)
    previous_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["atr"] = tr.rolling(period).mean().bfill().fillna(0.0)
    return out


def _fvg_at(df: pd.DataFrame, index: int, settings: BPRSettings) -> FVG | None:
    if index < 2 or index >= len(df):
        return None
    row = df.iloc[index]
    left = df.iloc[index - 2]
    atr = float(row.get("atr") or 0.0)
    if atr <= 0:
        return None

    open_price = float(row["open"])
    close_price = float(row["close"])
    displacement_atr = abs(close_price - open_price) / atr
    if displacement_atr < settings.min_displacement_atr:
        return None

    left_high = float(left["high"])
    left_low = float(left["low"])
    low = float(row["low"])
    high = float(row["high"])
    happened_at = pd.Timestamp(row["time"]).to_pydatetime()

    if low > left_high:
        gap = low - left_high
        if gap / atr >= settings.min_gap_atr:
            return FVG(index, happened_at, "BUY", left_high, low, gap, displacement_atr)
    if high < left_low:
        gap = left_low - high
        if gap / atr >= settings.min_gap_atr:
            return FVG(index, happened_at, "SELL", high, left_low, gap, displacement_atr)
    return None


def _zone_from_pair(symbol: str, timeframe: str, older: FVG, newer: FVG) -> BPRZone | None:
    if older.direction == newer.direction or older.index >= newer.index:
        return None
    low = max(older.low, newer.low)
    high = min(older.high, newer.high)
    if high <= low:
        return None
    return BPRZone(
        key=f"{symbol}|{timeframe}|{older.index}|{newer.index}|{newer.direction}",
        symbol=symbol,
        timeframe=timeframe,
        direction=newer.direction,
        low=low,
        high=high,
        created_index=newer.index,
        created_at=newer.time,
        older_fvg=older,
        newer_fvg=newer,
    )


def _score(zone: BPRZone, row: pd.Series, atr: float, touched: bool, pending: bool = False) -> int:
    if atr <= 0:
        return 0
    width_atr = zone.width / atr
    width_score = max(0, 16 - int(round(width_atr * 8)))
    displacement_score = min(12, int(round(zone.newer_fvg.displacement_atr * 4)))
    close = float(row["close"])
    open_price = float(row["open"])
    direction_score = 0
    if zone.direction == "BUY" and close > open_price:
        direction_score = 6
    elif zone.direction == "SELL" and close < open_price:
        direction_score = 6
    touch_score = 8 if touched else 3 if pending else 0
    return int(max(0, min(100, 72 + width_score + displacement_score + direction_score + touch_score)))


def _build_signal(
    zone: BPRZone,
    row: pd.Series,
    index: int,
    settings: BPRSettings,
    execution_type: str,
    pending_order_type: str | None = None,
    trigger_price: float | None = None,
) -> dict[str, Any] | None:
    atr = float(row.get("atr") or 0.0)
    if atr <= 0:
        return None
    if settings.max_zone_atr > 0 and zone.width / atr > settings.max_zone_atr:
        return None
    direction = zone.direction
    entry = float(trigger_price if trigger_price is not None else row["close"])
    if direction == "BUY":
        stop_loss = zone.low - atr * settings.stop_atr_buffer
        risk = entry - stop_loss
        if risk <= 0:
            return None
        take_profit = entry + risk * settings.reward_risk
    else:
        stop_loss = zone.high + atr * settings.stop_atr_buffer
        risk = stop_loss - entry
        if risk <= 0:
            return None
        take_profit = entry - risk * settings.reward_risk

    score = _score(zone, row, atr, touched=execution_type == "MARKET", pending=execution_type == "PENDING")
    if score < settings.min_score:
        return None
    happened_at = pd.Timestamp(row["time"]).to_pydatetime()
    tp1 = entry + risk if direction == "BUY" else entry - risk
    tp2 = entry + risk * 2 if direction == "BUY" else entry - risk * 2
    return {
        "symbol": zone.symbol,
        "timeframe": zone.timeframe,
        "direction": direction,
        "setup_grade": "BPR",
        "setup_score": score,
        "entry_model": "Balanced Price Range retest",
        "execution_type": execution_type,
        "pending_order_type": pending_order_type,
        "trigger_price": trigger_price,
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": take_profit,
        "risk_reward": settings.reward_risk,
        "configured_risk_reward": settings.reward_risk,
        "opened_at": happened_at,
        "start_index": index,
        "bpr": {
            "key": zone.key,
            "low": zone.low,
            "high": zone.high,
            "midpoint": zone.midpoint,
            "width": zone.width,
            "width_atr": zone.width / atr,
            "created_at": zone.created_at.isoformat(timespec="seconds"),
            "older_fvg_direction": zone.older_fvg.direction,
            "newer_fvg_direction": zone.newer_fvg.direction,
            "newer_displacement_atr": zone.newer_fvg.displacement_atr,
        },
        "reasons": [
            "Opposing FVGs overlap into a balanced price range.",
            "Entry waits for price to return into the BPR and reject it.",
            f"Stop is beyond BPR with {settings.stop_atr_buffer:g} ATR buffer.",
        ],
    }


def generate_bpr_signals(
    candles: pd.DataFrame,
    symbol: str,
    timeframe: str,
    settings: BPRSettings | None = None,
    include_pending: bool = False,
) -> list[dict[str, Any]]:
    settings = settings or settings_from_env()
    df = add_atr(candles)
    recent_fvgs: list[FVG] = []
    active_zones: dict[str, BPRZone] = {}
    signals: list[dict[str, Any]] = []

    for index in range(2, len(df)):
        row = df.iloc[index]
        atr = float(row.get("atr") or 0.0)
        if atr > 0:
            low = float(row["low"])
            high = float(row["high"])
            close = float(row["close"])
            for zone in list(active_zones.values()):
                if zone.touched or index <= zone.created_index:
                    continue
                if index - zone.created_index > settings.max_signal_age_bars:
                    zone.touched = True
                    continue
                touched = low <= zone.high and high >= zone.low
                if not touched:
                    continue
                confirmed = (zone.direction == "BUY" and close > zone.midpoint) or (
                    zone.direction == "SELL" and close < zone.midpoint
                )
                zone.touched = True
                if not confirmed:
                    continue
                signal = _build_signal(zone, row, index, settings, "MARKET")
                if signal:
                    signals.append(signal)

        fvg = _fvg_at(df, index, settings)
        if fvg is not None:
            recent_fvgs = [item for item in recent_fvgs if index - item.index <= settings.fvg_lookback_bars]
            for older in recent_fvgs:
                zone = _zone_from_pair(symbol, timeframe, older, fvg)
                if zone and zone.key not in active_zones:
                    active_zones[zone.key] = zone
            recent_fvgs.append(fvg)

    if include_pending and settings.allow_pending and len(df) > 10:
        row = df.iloc[-1]
        index = len(df) - 1
        close = float(row["close"])
        for zone in active_zones.values():
            if zone.touched or index <= zone.created_index or index - zone.created_index > settings.max_signal_age_bars:
                continue
            if zone.direction == "BUY" and close > zone.high:
                signal = _build_signal(zone, row, index, settings, "PENDING", "BUY_LIMIT", zone.high)
            elif zone.direction == "SELL" and close < zone.low:
                signal = _build_signal(zone, row, index, settings, "PENDING", "SELL_LIMIT", zone.low)
            else:
                signal = None
            if signal:
                signals.append(signal)

    return signals
