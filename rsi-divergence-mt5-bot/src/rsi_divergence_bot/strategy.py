from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha1

import pandas as pd

from .config import RiskConfig, SymbolConfig
from .indicators import atr, ema, pivot_high, pivot_low, rsi
from .sessions import in_allowed_session, session_name


@dataclass(frozen=True)
class Signal:
    setup_id: str
    symbol: str
    market_key: str
    name: str
    side: str
    time: datetime
    entry: float
    sl: float
    tps: list[float]
    lot_per_leg: float
    risk_distance: float
    session: str
    reason: str


def prepare_frame(df: pd.DataFrame, cfg: SymbolConfig) -> pd.DataFrame:
    out = df.copy()
    out["rsi"] = rsi(out["close"], 14)
    out["atr"] = atr(out, 14)
    out["ema20"] = ema(out["close"], 20)
    out["ema50"] = ema(out["close"], 50)
    out["price_pivot_low"] = pivot_low(out["low"], cfg.pivot_len)
    out["price_pivot_high"] = pivot_high(out["high"], cfg.pivot_len)
    out["rsi_pivot_low"] = pivot_low(out["rsi"], cfg.pivot_len)
    out["rsi_pivot_high"] = pivot_high(out["rsi"], cfg.pivot_len)
    return out


def confirmation_ok(frame: pd.DataFrame, index: int, pivot_index: int, side: str, cfg: SymbolConfig) -> bool:
    row = frame.iloc[index]
    pivot = frame.iloc[pivot_index]
    mode = cfg.confirmation
    if mode == "off":
        return True
    if side == "buy":
        if mode == "ema":
            return row.close > row.ema20
        if mode == "trend_guard":
            return row.close >= row.ema50 or row.rsi >= 45
        if mode == "rsi_extreme":
            return pivot.rsi <= 38
        if mode == "strict":
            return row.close > row.ema20 and row.ema20 > row.ema50 and row.rsi > 45
    if side == "sell":
        if mode == "ema":
            return row.close < row.ema20
        if mode == "trend_guard":
            return row.close <= row.ema50 or row.rsi <= 55
        if mode == "rsi_extreme":
            return pivot.rsi >= 62
        if mode == "strict":
            return row.close < row.ema20 and row.ema20 < row.ema50 and row.rsi < 55
    return False


def _make_signal(
    frame: pd.DataFrame,
    index: int,
    side: str,
    pivot_price: float,
    cfg: SymbolConfig,
    risk_cfg: RiskConfig | None,
) -> Signal | None:
    row = frame.iloc[index]
    time_value = row.time.to_pydatetime() if hasattr(row.time, "to_pydatetime") else row.time
    if risk_cfg and not in_allowed_session(time_value, cfg.sessions):
        return None
    entry = float(row.close)
    atr_stop = entry - float(row.atr) * cfg.sl_atr_mult if side == "buy" else entry + float(row.atr) * cfg.sl_atr_mult
    structure_stop = pivot_price if side == "buy" else pivot_price
    sl = min(atr_stop, structure_stop) if side == "buy" else max(atr_stop, structure_stop)
    risk_distance = abs(entry - sl)
    if risk_distance <= 0:
        return None
    if risk_cfg and abs(entry - float(row.ema20)) > float(row.atr) * risk_cfg.max_extension_atr:
        return None
    tps = [entry + risk_distance * rr if side == "buy" else entry - risk_distance * rr for rr in cfg.rr]
    setup_key = f"{cfg.key}:{side}:{time_value.isoformat()}"
    return Signal(
        setup_id=sha1(setup_key.encode("utf-8")).hexdigest()[:8],
        symbol=cfg.symbol,
        market_key=cfg.key,
        name=cfg.name,
        side=side,
        time=time_value,
        entry=entry,
        sl=sl,
        tps=tps,
        lot_per_leg=cfg.lot_per_leg,
        risk_distance=risk_distance,
        session=session_name(time_value),
        reason=f"{cfg.name} {side} RSI divergence confirmed by {cfg.confirmation}",
    )


def generate_signals(df: pd.DataFrame, cfg: SymbolConfig, risk_cfg: RiskConfig | None = None) -> list[Signal]:
    frame = prepare_frame(df, cfg).reset_index(drop=True)
    signals: list[Signal] = []

    prev_price_low = prev_rsi_low = None
    prev_price_high = prev_rsi_high = None
    active: dict[str, float | int | str] | None = None

    for i in range(len(frame)):
        pivot_index = i - cfg.pivot_len
        if pivot_index < cfg.pivot_len or pd.isna(frame.iloc[i].atr):
            continue

        pivot = frame.iloc[pivot_index]
        if bool(pivot.price_pivot_low) and bool(pivot.rsi_pivot_low):
            if prev_price_low is not None and pivot.low < prev_price_low and pivot.rsi > prev_rsi_low:
                active = {"side": "buy", "start": i, "pivot_index": pivot_index, "pivot_price": float(pivot.low)}
            prev_price_low = float(pivot.low)
            prev_rsi_low = float(pivot.rsi)

        if bool(pivot.price_pivot_high) and bool(pivot.rsi_pivot_high):
            if prev_price_high is not None and pivot.high > prev_price_high and pivot.rsi < prev_rsi_high:
                active = {"side": "sell", "start": i, "pivot_index": pivot_index, "pivot_price": float(pivot.high)}
            prev_price_high = float(pivot.high)
            prev_rsi_high = float(pivot.rsi)

        if not active:
            continue

        side = str(active["side"])
        start = int(active["start"])
        pivot_price = float(active["pivot_price"])
        if i - start > cfg.max_wait_bars:
            active = None
            continue
        if side == "buy" and frame.iloc[i].close < pivot_price:
            active = None
            continue
        if side == "sell" and frame.iloc[i].close > pivot_price:
            active = None
            continue
        if confirmation_ok(frame, i, int(active["pivot_index"]), side, cfg):
            signal = _make_signal(frame, i, side, pivot_price, cfg, risk_cfg)
            if signal:
                signals.append(signal)
            active = None

    return signals


def signal_at_closed_index(
    df: pd.DataFrame,
    end_index: int,
    cfg: SymbolConfig,
    risk_cfg: RiskConfig,
) -> Signal | None:
    """Same rule as latest_closed_signal when the bar at end_index is the last closed bar."""
    if end_index < 0 or end_index >= len(df):
        return None
    closed = df.iloc[: end_index + 1]
    signals = generate_signals(closed, cfg, risk_cfg)
    if not signals:
        return None
    latest = signals[-1]
    row_time = closed.iloc[-1]["time"]
    if hasattr(row_time, "to_pydatetime"):
        row_time = row_time.to_pydatetime()
    return latest if latest.time == row_time else None


def latest_closed_signal(df: pd.DataFrame, cfg: SymbolConfig, risk_cfg: RiskConfig) -> Signal | None:
    # MT5 includes the still-forming bar. Drop it so the bot trades confirmed bars only.
    if len(df) < 2:
        return None
    closed = df.iloc[:-1]
    return signal_at_closed_index(closed, len(closed) - 1, cfg, risk_cfg)
