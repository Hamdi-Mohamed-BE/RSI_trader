"""Fee-aware arbitrage detectors (Strategy pattern).

Every detector prices opportunities at *executable depth* for a set of share sizes and keeps the size with the
largest positive net edge. Nothing here places orders; detections feed the scanner feed and the paper engine.

Kinds implemented:

* ``complement_buy_merge``  — buy YES and NO of one binary market for < $1 per pair; merge the pair back into $1
  USDC immediately (CTF merge) or hold to resolution.
* ``complement_split_sell`` — split $1 USDC into YES+NO and sell both into the bids for > $1 per pair.
* ``neg_risk_basket_buy``   — in a mutually exclusive (neg-risk) event, buy YES on every outcome for < $1 per set;
  exactly one pays $1 at resolution. Capital is locked until then.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from crypto_lab.domain.polymarket.market import Event, Market
from crypto_lab.domain.polymarket.orderbook import ONE, ZERO, OrderBook


class OpportunityKind(StrEnum):
    COMPLEMENT_BUY_MERGE = "complement_buy_merge"
    COMPLEMENT_SPLIT_SELL = "complement_split_sell"
    NEG_RISK_BASKET_BUY = "neg_risk_basket_buy"


@dataclass(frozen=True, slots=True)
class ScanConfig:
    share_sizes: tuple[Decimal, ...] = tuple(Decimal(s) for s in (5, 10, 25, 50, 100, 250, 1000))
    min_net_edge_usdc: Decimal = Decimal("0.05")
    min_edge_pct: Decimal = Decimal("0.001")  # 0.1% of capital
    extra_cost_per_leg_usdc: Decimal = ZERO  # allowance for gas/relayer or slippage not visible in the book
    max_book_age_ms: int = 15_000
    max_capital_usdc: Decimal | None = None  # ignore sizes that would need more capital than this (paper bankroll)


@dataclass(frozen=True, slots=True)
class Leg:
    token_id: str
    outcome: str
    market_slug: str
    side: str  # "buy" | "sell"
    shares: Decimal
    average_price: Decimal
    worst_price: Decimal
    notional: Decimal
    fee: Decimal


@dataclass(frozen=True, slots=True)
class Opportunity:
    kind: OpportunityKind
    event_id: str
    condition_id: str  # empty for event-level baskets
    title: str
    shares: Decimal
    legs: tuple[Leg, ...]
    capital: Decimal  # USDC committed (cost + fees for buys; $1 x shares for split-sell)
    payout: Decimal  # USDC returned (merge/resolution payout, or sale proceeds net of fees)
    fees: Decimal
    detected_at: datetime
    oldest_book_ms: int
    resolves_at: datetime | None = None
    holds_to_resolution: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def net_edge(self) -> Decimal:
        return self.payout - self.capital

    @property
    def edge_pct(self) -> Decimal:
        return self.net_edge / self.capital if self.capital else ZERO

    def days_locked(self) -> Decimal | None:
        if not self.holds_to_resolution:
            return ZERO
        if self.resolves_at is None:
            return None
        seconds = max((self.resolves_at - self.detected_at).total_seconds(), 3600.0)
        return Decimal(str(seconds / 86400))

    def annualised_pct(self) -> Decimal | None:
        days = self.days_locked()
        if days is None or days == 0:
            return None
        return self.edge_pct * Decimal(365) / days

    @property
    def fingerprint(self) -> str:
        return f"{self.kind.value}:{self.condition_id or self.event_id}"


class ArbitrageDetector(Protocol):
    name: str

    def detect(
        self, event: Event, books: Mapping[str, OrderBook], config: ScanConfig, now: datetime
    ) -> list[Opportunity]:
        """Return profitable opportunities in ``event`` (possibly none)."""


def _passes(opp: Opportunity, config: ScanConfig) -> bool:
    affordable = config.max_capital_usdc is None or opp.capital <= config.max_capital_usdc
    return affordable and opp.net_edge >= config.min_net_edge_usdc and opp.edge_pct >= config.min_edge_pct


def _best(candidates: Sequence[Opportunity], config: ScanConfig) -> list[Opportunity]:
    passing = [c for c in candidates if _passes(c, config)]
    return [max(passing, key=lambda o: o.net_edge)] if passing else []


def _usable(market: Market) -> bool:
    return market.is_binary and market.accepting_orders


class ComplementBuyMergeDetector:
    name = OpportunityKind.COMPLEMENT_BUY_MERGE.value

    def detect(
        self, event: Event, books: Mapping[str, OrderBook], config: ScanConfig, now: datetime
    ) -> list[Opportunity]:
        found: list[Opportunity] = []
        for market in filter(_usable, event.markets):
            yes_book, no_book = books.get(market.yes.token_id), books.get(market.no.token_id)
            if yes_book is None or no_book is None:
                continue
            candidates: list[Opportunity] = []
            for size in config.share_sizes:
                if size < market.min_order_size:
                    continue
                yes_fill, no_fill = yes_book.buy(size), no_book.buy(size)
                if yes_fill is None or no_fill is None:
                    break  # deeper sizes cannot fill either
                legs = tuple(
                    Leg(
                        tok.token_id,
                        tok.outcome,
                        market.slug,
                        "buy",
                        size,
                        f.average_price,
                        f.worst_price,
                        f.notional,
                        market.fees.taker_fee(f),
                    )
                    for tok, f in ((market.yes, yes_fill), (market.no, no_fill))
                )
                fees = sum((leg.fee for leg in legs), ZERO)
                extra = config.extra_cost_per_leg_usdc * len(legs)
                candidates.append(
                    Opportunity(
                        kind=OpportunityKind.COMPLEMENT_BUY_MERGE,
                        event_id=event.event_id,
                        condition_id=market.condition_id,
                        title=market.question,
                        shares=size,
                        legs=legs,
                        capital=yes_fill.notional + no_fill.notional + fees + extra,
                        payout=size * ONE,
                        fees=fees,
                        detected_at=now,
                        oldest_book_ms=min(yes_book.observed_ms, no_book.observed_ms),
                        resolves_at=market.end_date,
                        holds_to_resolution=False,
                        notes=("Merge YES+NO into USDC right after both fills.",),
                    )
                )
            found += _best(candidates, config)
        return found


class ComplementSplitSellDetector:
    name = OpportunityKind.COMPLEMENT_SPLIT_SELL.value

    def detect(
        self, event: Event, books: Mapping[str, OrderBook], config: ScanConfig, now: datetime
    ) -> list[Opportunity]:
        found: list[Opportunity] = []
        for market in filter(_usable, event.markets):
            yes_book, no_book = books.get(market.yes.token_id), books.get(market.no.token_id)
            if yes_book is None or no_book is None:
                continue
            candidates: list[Opportunity] = []
            for size in config.share_sizes:
                if size < market.min_order_size:
                    continue
                yes_fill, no_fill = yes_book.sell(size), no_book.sell(size)
                if yes_fill is None or no_fill is None:
                    break
                legs = tuple(
                    Leg(
                        tok.token_id,
                        tok.outcome,
                        market.slug,
                        "sell",
                        size,
                        f.average_price,
                        f.worst_price,
                        f.notional,
                        market.fees.taker_fee(f),
                    )
                    for tok, f in ((market.yes, yes_fill), (market.no, no_fill))
                )
                fees = sum((leg.fee for leg in legs), ZERO)
                extra = config.extra_cost_per_leg_usdc * len(legs)
                candidates.append(
                    Opportunity(
                        kind=OpportunityKind.COMPLEMENT_SPLIT_SELL,
                        event_id=event.event_id,
                        condition_id=market.condition_id,
                        title=market.question,
                        shares=size,
                        legs=legs,
                        capital=size * ONE + extra,
                        payout=yes_fill.notional + no_fill.notional - fees,
                        fees=fees,
                        detected_at=now,
                        oldest_book_ms=min(yes_book.observed_ms, no_book.observed_ms),
                        resolves_at=market.end_date,
                        holds_to_resolution=False,
                        notes=("Split USDC into YES+NO first, then sell both.",),
                    )
                )
            found += _best(candidates, config)
        return found


class NegRiskBasketBuyDetector:
    name = OpportunityKind.NEG_RISK_BASKET_BUY.value

    def detect(
        self, event: Event, books: Mapping[str, OrderBook], config: ScanConfig, now: datetime
    ) -> list[Opportunity]:
        if not event.is_complete_basket or not all(_usable(m) for m in event.markets):
            return []
        yes_books = [books.get(m.yes.token_id) for m in event.markets]
        if any(b is None for b in yes_books):
            return []  # a missing outcome breaks the $1 guarantee
        candidates: list[Opportunity] = []
        for size in config.share_sizes:
            if any(size < m.min_order_size for m in event.markets):
                continue
            legs: list[Leg] = []
            for market, book in zip(event.markets, yes_books, strict=True):
                fill = book.buy(size) if book is not None else None
                if fill is None:
                    break
                legs.append(
                    Leg(
                        market.yes.token_id,
                        market.group_item_title or market.question,
                        market.slug,
                        "buy",
                        size,
                        fill.average_price,
                        fill.worst_price,
                        fill.notional,
                        market.fees.taker_fee(fill),
                    )
                )
            if len(legs) != len(event.markets):
                break
            fees = sum((leg.fee for leg in legs), ZERO)
            cost = sum((leg.notional for leg in legs), ZERO)
            extra = config.extra_cost_per_leg_usdc * len(legs)
            candidates.append(
                Opportunity(
                    kind=OpportunityKind.NEG_RISK_BASKET_BUY,
                    event_id=event.event_id,
                    condition_id="",
                    title=event.title,
                    shares=size,
                    legs=tuple(legs),
                    capital=cost + fees + extra,
                    payout=size * ONE,
                    fees=fees,
                    detected_at=now,
                    oldest_book_ms=min(b.observed_ms for b in yes_books if b),
                    resolves_at=event.end_date,
                    holds_to_resolution=True,
                    notes=("Exactly one outcome resolves YES; capital is locked until resolution.",),
                )
            )
        return _best(candidates, config)


DEFAULT_DETECTORS: tuple[ArbitrageDetector, ...] = (
    ComplementBuyMergeDetector(),
    ComplementSplitSellDetector(),
    NegRiskBasketBuyDetector(),
)
