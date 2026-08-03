from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable, Iterable


@dataclass(frozen=True)
class FrozenRange:
    high: float
    low: float
    atr: float
    last_spread: float
    first_utc: str
    last_utc: str

    @property
    def height(self) -> float:
        return self.high - self.low


def entry_buffer(*, broker_min: float, configured_min: float, spread: float, spread_multiplier: float, atr: float, atr_multiplier: float) -> float:
    return max(broker_min, configured_min, spread * spread_multiplier, atr * atr_multiplier)


def floor_step(value: float, minimum: float, maximum: float, step: float) -> float:
    if step <= 0:
        raise ValueError("step must be positive")
    units = math.floor((min(value, maximum) - minimum + 1e-12) / step)
    return round(max(minimum, minimum + max(0, units) * step), 8)


def risk_sized_volume(*, cash_risk: float, loss_per_lot: float, minimum: float, maximum: float, step: float) -> float | None:
    if cash_risk <= 0 or loss_per_lot <= 0:
        return None
    if loss_per_lot * minimum > cash_risk + 1e-8:
        return None
    volume = floor_step(cash_risk / loss_per_lot, minimum, maximum, step)
    return volume if volume * loss_per_lot <= cash_risk + 1e-8 else None


def discover_gold_symbol(symbols: Iterable[object]) -> object:
    ranked: list[tuple[int, object]] = []
    for info in symbols:
        name = str(getattr(info, "name", ""))
        description = str(getattr(info, "description", "")).lower()
        path = str(getattr(info, "path", "")).lower()
        upper = name.upper()
        gold = "gold" in description or upper.startswith("XAUUSD") or upper == "GOLD"
        usd = "usd" in upper or "us dollar" in description or "usd" in path
        if not gold or not usd or getattr(info, "trade_mode", 0) == 0:
            continue
        score = 0 if upper == "XAUUSD" else 1 if upper.startswith("XAUUSD") else 2
        ranked.append((score, info))
    if not ranked:
        raise RuntimeError("No tradable Gold-versus-USD symbol was found in the connected MT5 account")
    return min(ranked, key=lambda item: (item[0], str(getattr(item[1], "name", ""))))[1]


def oco_comment(reason: str) -> str:
    return f"NewsPulse B+ {reason}"[:31]
