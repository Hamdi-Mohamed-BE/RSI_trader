from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from ..schemas import RuntimeConfig, SymbolConfig
from .indicators import adx, atr, rsi
from .profile import (
    VolumeProfile,
    build_bar_profile,
    build_trade_profile,
    order_book_metrics,
    trade_flow_metrics,
)


@dataclass
class SignalDecision:
    symbol: str
    timestamp: str
    direction: str
    status: str
    score: float
    regime: str
    order_type: str | None
    entry: float | None
    stop_loss: float | None
    take_profit: float | None
    reward_risk: float
    reasons: list[str]
    profile: dict
    order_book: dict
    trade_flow: dict
    indicators: dict

    def to_dict(self) -> dict:
        return asdict(self)


class LtaOrderFlowEngine:
    def __init__(self, config: RuntimeConfig):
        self.config = config

    def evaluate(
        self,
        symbol: str,
        bars: pd.DataFrame,
        trades: pd.DataFrame | None = None,
        depth: pd.DataFrame | None = None,
        profile_override: VolumeProfile | None = None,
    ) -> SignalDecision:
        if symbol not in self.config.symbols:
            raise ValueError(f"No configuration for {symbol}.")
        if len(bars) < 80:
            raise ValueError(f"At least 80 bars are required for {symbol}; received {len(bars)}.")
        symbol_config = self.config.symbols[symbol]
        frame = self.prepare(bars)
        current = frame.iloc[-1]
        previous = frame.iloc[-2]
        profile = profile_override or self._volume_profile(frame, trades)
        book = order_book_metrics(depth)
        tape = trade_flow_metrics(trades)
        direction, regime = self._market_direction(current)
        score, reasons = self._score(direction, frame, profile, book, tape)
        levels = self._levels(direction, frame, profile, symbol_config) if direction != "FLAT" else None
        threshold = symbol_config.minimum_score or self.config.minimum_score
        status = "A_PLUS" if score >= threshold and levels else "WATCH"
        order_type = None
        if levels:
            entry = levels["entry"]
            current_price = float(current["close"])
            tolerance = float(current["atr"]) * 0.15
            order_type = "MARKET" if abs(current_price - entry) <= tolerance else "LIMIT"
        else:
            entry = None
        if direction == "FLAT":
            reasons.append("Trend and value acceptance are not aligned.")
        if book["imbalance"] is None:
            reasons.append("Order-book confirmation is unavailable; no depth points awarded.")
        return SignalDecision(
            symbol=symbol,
            timestamp=frame.index[-1].isoformat(),
            direction=direction,
            status=status,
            score=round(score, 1),
            regime=regime,
            order_type=order_type,
            entry=round(entry, 8) if entry is not None else None,
            stop_loss=round(levels["stop"], 8) if levels else None,
            take_profit=round(levels["target"], 8) if levels else None,
            reward_risk=symbol_config.reward_risk,
            reasons=reasons,
            profile=asdict(profile),
            order_book=book,
            trade_flow=tape,
            indicators={
                "close": float(current["close"]),
                "atr": float(current["atr"]),
                "adx": float(current["adx"]),
                "rsi": float(current["rsi"]),
                "ema_fast": float(current["ema_fast"]),
                "ema_slow": float(current["ema_slow"]),
                "volume_ratio": float(current["volume_ratio"]),
                "previous_close": float(previous["close"]),
            },
        )

    def prepare(self, bars: pd.DataFrame) -> pd.DataFrame:
        required = {"atr", "rsi", "adx", "ema_fast", "ema_slow", "volume_ratio"}
        if required.issubset(bars.columns):
            return bars.dropna(subset=["atr", "ema_fast", "ema_slow"])
        return self._with_indicators(bars)

    def _with_indicators(self, bars: pd.DataFrame) -> pd.DataFrame:
        frame = bars.copy()
        frame["atr"] = atr(frame)
        frame["rsi"] = rsi(frame["close"])
        frame["adx"] = adx(frame)
        frame["ema_fast"] = frame["close"].ewm(span=20, adjust=False).mean()
        frame["ema_slow"] = frame["close"].ewm(span=50, adjust=False).mean()
        rolling_volume = frame["volume"].rolling(20, min_periods=5).mean().replace(0, np.nan)
        frame["volume_ratio"] = (frame["volume"] / rolling_volume).fillna(1.0)
        return frame.dropna(subset=["atr", "ema_fast", "ema_slow"])

    def _volume_profile(
        self, frame: pd.DataFrame, trades: pd.DataFrame | None
    ) -> VolumeProfile:
        if self.config.use_trade_tape_profile and trades is not None and not trades.empty:
            return build_trade_profile(
                trades, self.config.profile_bins, self.config.value_area_percent
            )
        lookback_bars = max(80, self.config.profile_lookback_days * 24 * 4)
        return build_bar_profile(
            frame.tail(lookback_bars), self.config.profile_bins, self.config.value_area_percent
        )

    @staticmethod
    def _market_direction(current: pd.Series) -> tuple[str, str]:
        trending = float(current["adx"]) >= 20.0
        if current["ema_fast"] > current["ema_slow"] and current["rsi"] >= 48:
            return "BUY", "TREND_UP" if trending else "BALANCED_UP"
        if current["ema_fast"] < current["ema_slow"] and current["rsi"] <= 52:
            return "SELL", "TREND_DOWN" if trending else "BALANCED_DOWN"
        return "FLAT", "BALANCED"

    def _score(
        self,
        direction: str,
        frame: pd.DataFrame,
        profile: VolumeProfile,
        book: dict,
        tape: dict,
    ) -> tuple[float, list[str]]:
        current, previous = frame.iloc[-1], frame.iloc[-2]
        price, average_range = float(current["close"]), max(float(current["atr"]), 1e-12)
        score = 0.0
        reasons: list[str] = []
        if direction == "FLAT":
            return score, reasons
        trend_ok = (
            direction == "BUY" and current["ema_fast"] > current["ema_slow"]
        ) or (direction == "SELL" and current["ema_fast"] < current["ema_slow"])
        if trend_ok:
            score += 20
            reasons.append("Fast and slow trend structure agree.")
        if float(current["adx"]) >= 22:
            score += 10
            reasons.append("Directional strength is above the trend threshold.")

        if direction == "BUY":
            distance = min(abs(price - profile.val), abs(price - profile.poc)) / average_range
            rejection = current["close"] > current["open"] and current["low"] <= previous["low"]
        else:
            distance = min(abs(price - profile.vah), abs(price - profile.poc)) / average_range
            rejection = current["close"] < current["open"] and current["high"] >= previous["high"]
        if distance <= 0.55:
            score += 25
            reasons.append("Price is testing a high-information profile level.")
        elif distance <= 1.0:
            score += 12
            reasons.append("Price is near the active value area.")
        if rejection:
            score += 20
            reasons.append("The latest candle rejected the profile level in trend direction.")
        if float(current["volume_ratio"]) >= self.config.volume_expansion_ratio:
            score += 15
            reasons.append("Participation expanded above its rolling baseline.")

        available_score = 90.0
        imbalance = book.get("imbalance")
        if imbalance is not None:
            available_score += 10.0
            aligned = (direction == "BUY" and imbalance >= self.config.orderbook_imbalance_threshold) or (
                direction == "SELL" and imbalance <= -self.config.orderbook_imbalance_threshold
            )
            if aligned:
                score += 10
                reasons.append("Top-of-book depth imbalance confirms the direction.")
            elif abs(imbalance) >= self.config.orderbook_imbalance_threshold:
                score -= 10
                reasons.append("Top-of-book pressure conflicts with the setup.")
        delta_ratio = tape.get("delta_ratio")
        if delta_ratio is not None:
            available_score += 10.0
            tape_aligned = (direction == "BUY" and delta_ratio >= 0.10) or (
                direction == "SELL" and delta_ratio <= -0.10
            )
            if tape_aligned:
                score += 10
                reasons.append("Aggressor trade delta confirms the setup.")
            elif abs(delta_ratio) >= 0.10:
                score -= 8
                reasons.append("Aggressor trade delta conflicts with the setup.")
        normalized = score / available_score * 100.0
        return max(0.0, min(100.0, normalized)), reasons

    def _levels(
        self,
        direction: str,
        frame: pd.DataFrame,
        profile: VolumeProfile,
        symbol_config: SymbolConfig,
    ) -> dict[str, float]:
        current = frame.iloc[-1]
        average_range = float(current["atr"])
        volatility_ratio = float(current["atr"] / frame["atr"].tail(50).median())
        volume_ratio = float(current["volume_ratio"])
        dynamic_multiplier = symbol_config.atr_stop_multiplier
        dynamic_multiplier *= min(1.5, max(0.85, volatility_ratio))
        if volume_ratio >= 1.5:
            dynamic_multiplier *= 1.12
        minimum_distance = average_range * symbol_config.min_stop_atr
        if direction == "BUY":
            entry = min(float(current["close"]), max(profile.val, profile.poc - average_range * 0.25))
            structural_stop = float(frame["low"].tail(8).min()) - average_range * 0.10
            distance = max(entry - structural_stop, average_range * dynamic_multiplier, minimum_distance)
            stop = entry - distance
            target = entry + distance * symbol_config.reward_risk
        else:
            entry = max(float(current["close"]), min(profile.vah, profile.poc + average_range * 0.25))
            structural_stop = float(frame["high"].tail(8).max()) + average_range * 0.10
            distance = max(structural_stop - entry, average_range * dynamic_multiplier, minimum_distance)
            stop = entry + distance
            target = entry - distance * symbol_config.reward_risk
        tick = symbol_config.tick_size
        return {
            "entry": round(entry / tick) * tick,
            "stop": round(stop / tick) * tick,
            "target": round(target / tick) * tick,
        }
