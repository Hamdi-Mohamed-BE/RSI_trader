"""Order-book value objects and depth-walking fills.

Prices are probabilities in USDC per share (0 < p < 1); sizes are shares. Everything uses :class:`~decimal.Decimal`
so fee and edge maths are exact to the cent.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

ZERO = Decimal(0)
ONE = Decimal(1)


@dataclass(frozen=True, slots=True)
class PriceLevel:
    price: Decimal
    size: Decimal


@dataclass(frozen=True, slots=True)
class Fill:
    """Result of walking the book for a quantity. ``takes`` are the (price, shares) matched at each level."""

    takes: tuple[PriceLevel, ...]

    @property
    def shares(self) -> Decimal:
        return sum((t.size for t in self.takes), ZERO)

    @property
    def notional(self) -> Decimal:
        """USDC paid (buy) or received (sell), before fees."""
        return sum((t.size * t.price for t in self.takes), ZERO)

    @property
    def levels_used(self) -> int:
        return len(self.takes)

    @property
    def worst_price(self) -> Decimal:
        return self.takes[-1].price

    @property
    def average_price(self) -> Decimal:
        shares = self.shares
        return self.notional / shares if shares else ZERO


@dataclass(frozen=True, slots=True)
class OrderBook:
    """A token's book with bids sorted high→low and asks sorted low→high (normalised on construction)."""

    token_id: str
    bids: tuple[PriceLevel, ...]
    asks: tuple[PriceLevel, ...]
    timestamp_ms: int  # server time of the last book change (quiet books can be minutes old and still current)
    tick_size: Decimal = Decimal("0.01")
    min_order_size: Decimal = Decimal(5)
    received_ms: int = 0  # local time we received this snapshot; 0 = unknown (e.g. hand-built in tests)

    @property
    def observed_ms(self) -> int:
        """When this snapshot was known to be current: receive time if known, else the server timestamp."""
        return self.received_ms or self.timestamp_ms

    @classmethod
    def build(
        cls,
        token_id: str,
        bids: Iterable[PriceLevel],
        asks: Iterable[PriceLevel],
        timestamp_ms: int,
        *,
        tick_size: Decimal = Decimal("0.01"),
        min_order_size: Decimal = Decimal(5),
        received_ms: int = 0,
    ) -> OrderBook:
        clean_bids = sorted(
            (lv for lv in bids if lv.size > 0 and ZERO < lv.price < ONE), key=lambda lv: lv.price, reverse=True
        )
        clean_asks = sorted((lv for lv in asks if lv.size > 0 and ZERO < lv.price < ONE), key=lambda lv: lv.price)
        return cls(token_id, tuple(clean_bids), tuple(clean_asks), timestamp_ms, tick_size, min_order_size, received_ms)

    @property
    def best_bid(self) -> Decimal | None:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> Decimal | None:
        return self.asks[0].price if self.asks else None

    def buy(self, shares: Decimal) -> Fill | None:
        """Cost of buying ``shares`` by lifting asks; ``None`` if the book is too thin."""
        return _walk(self.asks, shares)

    def sell(self, shares: Decimal) -> Fill | None:
        """Proceeds of selling ``shares`` into bids; ``None`` if the book is too thin."""
        return _walk(self.bids, shares)

    def depth(self, side: str) -> Decimal:
        levels = self.asks if side == "ask" else self.bids
        return sum((lv.size for lv in levels), ZERO)


def _walk(levels: tuple[PriceLevel, ...], shares: Decimal) -> Fill | None:
    if shares <= 0:
        raise ValueError("shares must be positive")
    remaining = shares
    takes: list[PriceLevel] = []
    for level in levels:
        take = min(remaining, level.size)
        takes.append(PriceLevel(level.price, take))
        remaining -= take
        if remaining == 0:
            return Fill(tuple(takes))
    return None
