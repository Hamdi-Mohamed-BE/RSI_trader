"""Polymarket taker fees.

Each market publishes a ``feeSchedule`` (``rate``, ``exponent``, ``takerOnly``). The documented taker fee is
``shares × rate × (p × (1 − p)) ^ exponent``, rounded to 5 decimals; makers pay nothing when ``takerOnly`` is true.
Markets with fees disabled use :data:`NO_FEES`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from crypto_lab.domain.polymarket.orderbook import ONE, ZERO, Fill

FEE_QUANTUM = Decimal("0.00001")


@dataclass(frozen=True, slots=True)
class FeeSchedule:
    rate: Decimal = ZERO
    exponent: int = 1
    taker_only: bool = True

    def taker_fee_at(self, shares: Decimal, price: Decimal) -> Decimal:
        if self.rate == 0 or shares == 0:
            return ZERO
        fee = shares * self.rate * (price * (ONE - price)) ** self.exponent
        return fee.quantize(FEE_QUANTUM, rounding=ROUND_HALF_UP)

    def taker_fee(self, fill: Fill) -> Decimal:
        """Fee for a depth-walked fill: each matched level is charged at its own price."""
        return sum((self.taker_fee_at(t.size, t.price) for t in fill.takes), ZERO)

    def maker_fee(self, shares: Decimal, price: Decimal) -> Decimal:
        return ZERO if self.taker_only else self.taker_fee_at(shares, price)


NO_FEES = FeeSchedule()
