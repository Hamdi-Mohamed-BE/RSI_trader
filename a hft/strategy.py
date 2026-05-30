"""Fast tick + EMA scalping signals (no copy_ticks_from — it hangs on some brokers)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum

import MetaTrader5 as mt5
import numpy as np

import config as cfg
from mt5_client import tick_min_points


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    FLAT = "FLAT"


@dataclass
class Signal:
    side: Side
    score: int
    reason: str
    symbol: str = ""


_TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
}

_mid_histories: dict[str, deque[float]] = {}


def _history(symbol: str) -> deque[float]:
    if symbol not in _mid_histories:
        _mid_histories[symbol] = deque(maxlen=max(cfg.TICK_MOMENTUM_COUNT, 2))
    return _mid_histories[symbol]


def _timeframe():
    return _TIMEFRAME_MAP.get(cfg.TIMEFRAME, mt5.TIMEFRAME_M1)


def update_live_tick(symbol: str) -> bool:
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return False
    _history(symbol).append((tick.bid + tick.ask) / 2.0)
    return True


def warm_up(symbols: list[str], samples: int | None = None) -> None:
    count = samples or max(cfg.TICK_MOMENTUM_COUNT, 3)
    for _ in range(count):
        for symbol in symbols:
            update_live_tick(symbol)


def _ema(values: np.ndarray, period: int) -> float:
    if len(values) < period:
        return float(values[-1])
    alpha = 2.0 / (period + 1)
    ema = float(values[0])
    for v in values[1:]:
        ema = alpha * float(v) + (1 - alpha) * ema
    return ema


def _rsi(closes: np.ndarray, period: int) -> float:
    if len(closes) < period + 1:
        return 50.0
    deltas = np.diff(closes[-(period + 1) :])
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = float(np.mean(gains))
    avg_loss = float(np.mean(losses))
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _bar_fallback(symbol: str) -> Signal | None:
    rates = mt5.copy_rates_from_pos(symbol, _timeframe(), 0, 3)
    if rates is None or len(rates) < 2:
        return None
    last_close = float(rates["close"][-1])
    prev_close = float(rates["close"][-2])
    if last_close > prev_close:
        return Signal(Side.BUY, 1, "bar_up", symbol)
    if last_close < prev_close:
        return Signal(Side.SELL, 1, "bar_down", symbol)
    return None


def _tick_signal(symbol: str) -> tuple[int, float, str]:
    history = _history(symbol)
    if len(history) < 2:
        return 0, 0.0, "warming"

    info = mt5.symbol_info(symbol)
    point = info.point if info and info.point else 0.01

    mids = list(history)
    move = float(mids[-1] - mids[0])
    move_points = move / point
    min_move = tick_min_points(symbol)

    if abs(move_points) < min_move:
        return 0, move_points, f"flat({move_points:.0f}pt)"

    last_move = float(mids[-1] - mids[-2])
    if abs(last_move) >= abs(move) * 0.5:
        if last_move > 0:
            return 1, move_points, f"burst_up({move_points:.0f}pt)"
        if last_move < 0:
            return -1, move_points, f"burst_down({move_points:.0f}pt)"

    if move > 0:
        return 1, move_points, f"tick_up({move_points:.0f}pt)"
    if move < 0:
        return -1, move_points, f"tick_down({move_points:.0f}pt)"
    return 0, move_points, "flat"


def get_scalp_signal(symbol: str) -> Signal:
    update_live_tick(symbol)
    tick_dir, _move_pts, tick_label = _tick_signal(symbol)

    if cfg.FAST_MODE and cfg.USE_TICK_FIRST and tick_dir != 0:
        side = Side.BUY if tick_dir > 0 else Side.SELL
        return Signal(side, 2, tick_label, symbol)

    if tick_dir == 0 and cfg.FAST_MODE:
        fallback = _bar_fallback(symbol)
        if fallback is not None:
            return fallback

    rates = mt5.copy_rates_from_pos(
        symbol, _timeframe(), 0, max(cfg.SLOW_EMA_PERIOD, cfg.RSI_PERIOD) + 10
    )
    if rates is None or len(rates) < cfg.SLOW_EMA_PERIOD + 2:
        if tick_dir != 0:
            side = Side.BUY if tick_dir > 0 else Side.SELL
            return Signal(side, 1, f"{tick_label}_only", symbol)
        fallback = _bar_fallback(symbol)
        return fallback or Signal(Side.FLAT, 0, "not enough bars", symbol)

    closes = rates["close"].astype(float)
    fast = _ema(closes, cfg.FAST_EMA_PERIOD)
    slow = _ema(closes, cfg.SLOW_EMA_PERIOD)
    rsi = _rsi(closes, cfg.RSI_PERIOD)

    buy_score = 0
    sell_score = 0
    reasons: list[str] = []

    if tick_dir > 0:
        buy_score += 2 if cfg.FAST_MODE else 1
        reasons.append(tick_label)
    elif tick_dir < 0:
        sell_score += 2 if cfg.FAST_MODE else 1
        reasons.append(tick_label)

    if fast > slow:
        buy_score += 1
        reasons.append("ema_up")
    elif fast < slow:
        sell_score += 1
        reasons.append("ema_down")

    if rsi < cfg.RSI_BUY_BELOW:
        buy_score += 1
        reasons.append(f"rsi={rsi:.0f}")
    if rsi > cfg.RSI_SELL_ABOVE:
        sell_score += 1
        reasons.append(f"rsi={rsi:.0f}")

    min_score = cfg.MIN_SIGNAL_SCORE
    if buy_score >= min_score and buy_score > sell_score:
        return Signal(Side.BUY, buy_score, "+".join(reasons), symbol)
    if sell_score >= min_score and sell_score > buy_score:
        return Signal(Side.SELL, sell_score, "+".join(reasons), symbol)

    fallback = _bar_fallback(symbol)
    if fallback is not None and cfg.FAST_MODE:
        return fallback

    return Signal(Side.FLAT, max(buy_score, sell_score), "no edge", symbol)


def best_signal(symbols: list[str]) -> Signal:
    """Scan all symbols and return the strongest non-flat signal."""
    best = Signal(Side.FLAT, 0, "no edge", "")
    for symbol in symbols:
        sig = get_scalp_signal(symbol)
        if sig.side == Side.FLAT:
            continue
        if sig.score > best.score or best.side == Side.FLAT:
            best = sig
    return best
