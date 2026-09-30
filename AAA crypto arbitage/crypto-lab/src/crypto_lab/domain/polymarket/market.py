"""Polymarket catalogue entities (events, markets, outcome tokens)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from crypto_lab.domain.polymarket.fees import NO_FEES, FeeSchedule


@dataclass(frozen=True, slots=True)
class OutcomeToken:
    token_id: str
    outcome: str


@dataclass(frozen=True, slots=True)
class Market:
    """A binary market: exactly two outcome tokens whose payouts sum to $1."""

    condition_id: str
    question: str
    slug: str
    tokens: tuple[OutcomeToken, ...]
    event_id: str = ""
    neg_risk: bool = False
    fees: FeeSchedule = NO_FEES
    fee_type: str = ""
    tick_size: Decimal = Decimal("0.01")
    min_order_size: Decimal = Decimal(5)
    end_date: datetime | None = None
    volume_24h: Decimal = Decimal(0)
    liquidity: Decimal = Decimal(0)
    accepting_orders: bool = True
    group_item_title: str = ""

    @property
    def is_binary(self) -> bool:
        return len(self.tokens) == 2

    @property
    def yes(self) -> OutcomeToken:
        return self.tokens[0]

    @property
    def no(self) -> OutcomeToken:
        return self.tokens[1]


@dataclass(frozen=True, slots=True)
class Event:
    """A group of markets. With ``neg_risk`` true the markets are mutually exclusive: exactly one YES pays $1."""

    event_id: str
    slug: str
    title: str
    markets: tuple[Market, ...] = field(default_factory=tuple)
    neg_risk: bool = False
    neg_risk_augmented: bool = False  # placeholder/"other" outcomes may be missing from the listed set
    end_date: datetime | None = None
    volume_24h: Decimal = Decimal(0)
    tags: tuple[str, ...] = ()

    @property
    def is_complete_basket(self) -> bool:
        """True when buying YES on every listed market is guaranteed to pay exactly $1."""
        return self.neg_risk and not self.neg_risk_augmented and len(self.markets) >= 2

    def token_ids(self) -> list[str]:
        return [t.token_id for m in self.markets for t in m.tokens]
