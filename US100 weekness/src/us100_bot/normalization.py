from __future__ import annotations

from dataclasses import dataclass
import math

from .models import SymbolSpec


@dataclass(frozen=True, slots=True)
class PriceNormalizer:
    spec: SymbolSpec
    pip_size: float = 1.0

    def pips_to_price(self, pips: float) -> float:
        return pips * self.pip_size

    def price_to_pips(self, price_distance: float) -> float:
        return price_distance / self.pip_size

    def pips_to_broker_points(self, pips: float) -> float:
        return self.pips_to_price(pips) / self.spec.point

    def pips_to_ticks(self, pips: float) -> float:
        return self.pips_to_price(pips) / self.spec.tick_size

    def risk_per_lot(self, stop_pips: float) -> float:
        ticks = self.pips_to_ticks(stop_pips)
        if self.spec.tick_value <= 0:
            raise ValueError(f"Broker tick value is invalid for {self.spec.name}")
        return ticks * self.spec.tick_value

    def money_for_move(self, volume: float, price_distance: float) -> float:
        ticks = price_distance / self.spec.tick_size
        return ticks * self.spec.tick_value * volume

    def round_price(self, price: float) -> float:
        ticks = round(price / self.spec.tick_size)
        return round(ticks * self.spec.tick_size, self.spec.digits)

    def round_volume(self, volume: float) -> float:
        step = self.spec.volume_step
        floored = math.floor((volume + 1e-12) / step) * step
        bounded = min(max(floored, self.spec.volume_min), self.spec.volume_max)
        decimals = max(0, -int(math.floor(math.log10(step)))) if step < 1 else 0
        return round(bounded, decimals)

    @property
    def minimum_stop_price(self) -> float:
        return self.spec.stops_level_points * self.spec.point

    def describe(self) -> dict[str, float | str]:
        return {
            "symbol": self.spec.name,
            "strategy_pip_price_units": self.pip_size,
            "broker_point_price_units": self.spec.point,
            "tick_size": self.spec.tick_size,
            "broker_points_per_strategy_pip": self.pips_to_broker_points(1),
            "ticks_per_strategy_pip": self.pips_to_ticks(1),
            "money_per_strategy_pip_per_lot": self.risk_per_lot(1),
        }

