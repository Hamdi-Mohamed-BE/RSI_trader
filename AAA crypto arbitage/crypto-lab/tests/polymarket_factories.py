"""Builders and fakes for Polymarket tests (Test Data Builder pattern)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

from crypto_lab.domain.polymarket.fees import NO_FEES, FeeSchedule
from crypto_lab.domain.polymarket.market import Event, Market, OutcomeToken
from crypto_lab.domain.polymarket.orderbook import OrderBook, PriceLevel

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
NOW_MS = int(NOW.timestamp() * 1000)
D = Decimal


def book(
    token: str, asks: Sequence[tuple[str, str]] = (), bids: Sequence[tuple[str, str]] = (), ts_ms: int = NOW_MS
) -> OrderBook:
    return OrderBook.build(
        token, [PriceLevel(D(p), D(s)) for p, s in bids], [PriceLevel(D(p), D(s)) for p, s in asks], ts_ms
    )


def market(
    cid: str, fees: FeeSchedule = NO_FEES, title: str = "", neg_risk: bool = False, min_size: str = "5"
) -> Market:
    return Market(
        condition_id=cid,
        question=title or f"Market {cid}?",
        slug=cid,
        tokens=(OutcomeToken(f"{cid}-yes", "Yes"), OutcomeToken(f"{cid}-no", "No")),
        event_id="ev",
        neg_risk=neg_risk,
        fees=fees,
        min_order_size=D(min_size),
        end_date=datetime(2026, 12, 31, tzinfo=UTC),
        group_item_title=title,
    )


def event(*markets: Market, neg_risk: bool = False, augmented: bool = False, event_id: str = "ev") -> Event:
    return Event(
        event_id=event_id,
        slug=event_id,
        title=f"Event {event_id}",
        markets=tuple(markets),
        neg_risk=neg_risk,
        neg_risk_augmented=augmented,
        end_date=datetime(2026, 12, 31, tzinfo=UTC),
        volume_24h=D(50_000),
    )


class FakeCatalog:
    def __init__(self, events: Sequence[Event]) -> None:
        self.events = list(events)

    async def active_events(self, *, max_events: int, min_volume_24h: float) -> Sequence[Event]:
        return self.events[:max_events]


class FakeBooks:
    """Returns successive snapshots: call N gets ``snapshots[min(N, last)]``."""

    def __init__(self, *snapshots: dict[str, OrderBook]) -> None:
        self.snapshots = list(snapshots)
        self.calls = 0

    async def books(self, token_ids: Sequence[str]) -> dict[str, OrderBook]:
        snap = self.snapshots[min(self.calls, len(self.snapshots) - 1)]
        self.calls += 1
        return {t: b for t, b in snap.items() if t in set(token_ids)}
