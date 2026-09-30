"""Polymarket arbitrage scanner (Model D).

One pass: load active events → fetch books → drop stale books → run detectors → upsert the opportunity feed.
In PAPER mode each *new* opportunity is re-priced from a second book fetch after ``paper_latency_ms`` and recorded
as a paper trade only if it is still profitable at the same size; otherwise it is recorded as *missed*. The ratio of
filled to missed detections is the scanner's most important honesty metric.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from crypto_lab.domain.bots import BotMode
from crypto_lab.domain.polymarket.arbitrage import (
    DEFAULT_DETECTORS,
    ArbitrageDetector,
    Opportunity,
    ScanConfig,
)
from crypto_lab.domain.polymarket.market import Event
from crypto_lab.domain.polymarket.orderbook import OrderBook
from crypto_lab.domain.polymarket.ports import BookSource, MarketCatalog
from crypto_lab.infrastructure.db.base import utcnow
from crypto_lab.infrastructure.db.models import Bot
from crypto_lab.infrastructure.db.paper_models import PaperAccount
from crypto_lab.infrastructure.db.polymarket_models import PmOpportunity, PmPaperTrade, PmScanRun
from crypto_lab.infrastructure.db.polymarket_repositories import ScannerRepository
from crypto_lab.infrastructure.db.session import unit_of_work
from crypto_lab.services.paper import lock_portfolio, portfolio

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ScannerSettings:
    max_events: int = 150
    min_volume_24h: float = 1_000.0
    paper_latency_ms: int = 1_500
    paper_cooldown_s: int = 300  # do not paper-trade the same opportunity again within this window
    paper_bankroll_usdc: Decimal = Decimal(100)
    tokens_per_fetch: int = 100  # books are fetched and checked in groups of about this many tokens
    scan: ScanConfig = field(default_factory=ScanConfig)


@dataclass(frozen=True, slots=True)
class ScanReport:
    events: int
    markets: int
    books: int
    stale_books: int
    opportunities: int
    new_opportunities: int
    paper_filled: int
    paper_missed: int
    duration_ms: int
    best_ask_sum: Decimal | None = None  # lowest top-of-book YES ask + NO ask seen (< 1 before fees = candidate)
    best_bid_sum: Decimal | None = None  # highest top-of-book YES bid + NO bid seen (> 1 before fees = candidate)


@dataclass(slots=True)
class NearMiss:
    """Tracks how close the market came to a complement arbitrage, before fees and depth."""

    best_ask_sum: Decimal | None = None
    best_bid_sum: Decimal | None = None

    def observe(self, events: Sequence[Event], books: Mapping[str, OrderBook]) -> None:
        for market in (m for e in events for m in e.markets if m.is_binary):
            yes, no = books.get(market.yes.token_id), books.get(market.no.token_id)
            if yes is None or no is None:
                continue
            if yes.best_ask is not None and no.best_ask is not None:
                total = yes.best_ask + no.best_ask
                self.best_ask_sum = total if self.best_ask_sum is None else min(self.best_ask_sum, total)
            if yes.best_bid is not None and no.best_bid is not None:
                total = yes.best_bid + no.best_bid
                self.best_bid_sum = total if self.best_bid_sum is None else max(self.best_bid_sum, total)


def _legs_json(opp: Opportunity) -> list[dict[str, str]]:
    return [
        {
            "token_id": leg.token_id,
            "outcome": leg.outcome,
            "market_slug": leg.market_slug,
            "side": leg.side,
            "shares": str(leg.shares),
            "avg_price": str(leg.average_price),
            "worst_price": str(leg.worst_price),
            "notional": str(leg.notional),
            "fee": str(leg.fee),
        }
        for leg in opp.legs
    ]


def event_groups(events: Sequence[Event], max_tokens: int) -> Iterator[list[Event]]:
    """Split events into groups of at most ``max_tokens`` tokens; an event is never split across groups."""
    group: list[Event] = []
    size = 0
    for event in events:
        tokens = len(event.token_ids())
        if group and size + tokens > max_tokens:
            yield group
            group, size = [], 0
        group.append(event)
        size += tokens
    if group:
        yield group


class ScannerService:
    def __init__(
        self,
        catalog: MarketCatalog,
        books: BookSource,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        settings: ScannerSettings | None = None,
        detectors: Sequence[ArbitrageDetector] = DEFAULT_DETECTORS,
        clock: Callable[[], datetime] = utcnow,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._catalog = catalog
        self._books = books
        self._sessions = session_factory
        self._settings = settings or ScannerSettings()
        self._detectors = {d.name: d for d in detectors}
        self._clock = clock
        self._sleep = sleep

    # --- pure-ish steps ------------------------------------------------------------------------------------------
    def _fresh(self, books: Mapping[str, OrderBook], now: datetime) -> tuple[dict[str, OrderBook], int]:
        cutoff_ms = int(now.timestamp() * 1000) - self._settings.scan.max_book_age_ms
        fresh = {k: b for k, b in books.items() if b.observed_ms >= cutoff_ms}
        return fresh, len(books) - len(fresh)

    def detect(
        self, events: Sequence[Event], books: Mapping[str, OrderBook], now: datetime, config: ScanConfig | None = None
    ) -> list[Opportunity]:
        config = config or self._settings.scan
        found: list[Opportunity] = []
        for event in events:
            for detector in self._detectors.values():
                found += detector.detect(event, books, config, now)
        return found

    # --- one pass -----------------------------------------------------------------------------------------------
    async def run_once(self, mode: BotMode) -> ScanReport:
        started = time.perf_counter()
        now = self._clock()
        events = await self._catalog.active_events(
            max_events=self._settings.max_events, min_volume_24h=self._settings.min_volume_24h
        )
        # Fetch and detect group by group so every book is judged moments after it arrived (a full pass takes
        # longer than the freshness window, so fetching everything first would age the early books out).
        opportunities: list[Opportunity] = []
        fetched = stale = 0
        near_miss = NearMiss()
        for group in event_groups(events, self._settings.tokens_per_fetch):
            raw_books = await self._books.books([t for e in group for t in e.token_ids()])
            fetched_at = self._clock()
            books, group_stale = self._fresh(raw_books, fetched_at)
            fetched, stale = fetched + len(raw_books), stale + group_stale
            near_miss.observe(group, books)
            opportunities += self.detect(group, books, fetched_at)

        async with unit_of_work(self._sessions) as session:
            repo = ScannerRepository(session)
            new = await self._upsert(repo, opportunities, now)
        filled = missed = 0
        if mode is BotMode.PAPER and new:
            filled, missed = await self._paper_trade(new, {e.event_id: e for e in events})

        report = ScanReport(
            events=len(events),
            markets=sum(len(e.markets) for e in events),
            books=fetched,
            stale_books=stale,
            opportunities=len(opportunities),
            new_opportunities=len(new),
            paper_filled=filled,
            paper_missed=missed,
            duration_ms=int((time.perf_counter() - started) * 1000),
            best_ask_sum=near_miss.best_ask_sum,
            best_bid_sum=near_miss.best_bid_sum,
        )
        async with unit_of_work(self._sessions) as session:
            await ScannerRepository(session).add_run(
                PmScanRun(
                    started_at=now,
                    finished_at=self._clock(),
                    mode=mode.value,
                    events_scanned=report.events,
                    markets_scanned=report.markets,
                    books_fetched=report.books,
                    stale_books=report.stale_books,
                    opportunities=report.opportunities,
                    paper_trades=filled,
                    duration_ms=report.duration_ms,
                    best_ask_sum=report.best_ask_sum,
                    best_bid_sum=report.best_bid_sum,
                )
            )
        logger.info("scan: %s", report)
        return report

    async def _upsert(
        self, repo: ScannerRepository, opportunities: Sequence[Opportunity], now: datetime
    ) -> list[Opportunity]:
        """Update or insert the feed; return opportunities that were not active before this pass."""
        new: list[Opportunity] = []
        for opp in opportunities:
            row = await repo.active_by_fingerprint(opp.fingerprint)
            if row is None:
                new.append(opp)
                await repo.add_opportunity(
                    PmOpportunity(
                        fingerprint=opp.fingerprint,
                        kind=opp.kind.value,
                        event_id=opp.event_id,
                        condition_id=opp.condition_id,
                        title=opp.title[:300],
                        first_seen_at=now,
                        last_seen_at=now,
                        shares=opp.shares,
                        capital=opp.capital,
                        payout=opp.payout,
                        fees=opp.fees,
                        net_edge=opp.net_edge,
                        best_net_edge=opp.net_edge,
                        edge_pct=opp.edge_pct,
                        holds_to_resolution=opp.holds_to_resolution,
                        resolves_at=opp.resolves_at,
                        book_age_ms=int(now.timestamp() * 1000) - opp.oldest_book_ms,
                        legs=_legs_json(opp),
                    )
                )
                continue
            row.last_seen_at = now
            row.seen_count += 1
            row.shares, row.capital, row.payout, row.fees = opp.shares, opp.capital, opp.payout, opp.fees
            row.net_edge, row.edge_pct, row.legs = opp.net_edge, opp.edge_pct, _legs_json(opp)
            row.best_net_edge = max(row.best_net_edge, opp.net_edge)
        await repo.deactivate_except({o.fingerprint for o in opportunities})
        return new

    # --- paper execution ------------------------------------------------------------------------------------------
    async def _paper_trade(self, detected: Sequence[Opportunity], events: Mapping[str, Event]) -> tuple[int, int]:
        await self._sleep(self._settings.paper_latency_ms / 1000)
        tokens = [leg.token_id for opp in detected for leg in opp.legs]
        later = self._clock()
        books, _ = self._fresh(await self._books.books(tokens), later)
        filled = missed = 0
        async with unit_of_work(self._sessions) as session:
            await lock_portfolio(session)
            repo = ScannerRepository(session)
            account = await session.get(PaperAccount, 1)
            control = await session.get(Bot, "poly-scanner")
            if account and (not control or control.mode != "paper" or control.kill_requested):
                return 0, 0
            balance = await portfolio(session, self._settings.paper_bankroll_usdc)
            free = balance.cash
            cooldown_since = later - timedelta(seconds=self._settings.paper_cooldown_s)
            for opp in detected:
                if await repo.paper_traded_recently(opp.fingerprint, cooldown_since):
                    continue
                repriced = self._reprice(opp, events.get(opp.event_id), books, later)
                note = ""
                if repriced is None:
                    note = "Edge gone after latency re-check."
                elif repriced.capital > free:
                    note = "Insufficient paper capital."
                elif account and repriced.capital > account.trade_limit:
                    note = "Entry exceeds the shared per-trade cap."
                if repriced is None or note:
                    missed += 1
                    await repo.add_paper_trade(self._paper_row(opp, "missed", later, note))
                    continue
                filled += 1
                status = "open" if repriced.holds_to_resolution else "settled"
                if status == "open":
                    free -= repriced.capital  # locked until resolution
                else:
                    free += repriced.net_edge  # merge/split trades settle immediately
                await repo.add_paper_trade(self._paper_row(repriced, status, later, "", detected_edge=opp.net_edge))
        return filled, missed

    def _reprice(
        self, opp: Opportunity, event: Event | None, books: Mapping[str, OrderBook], now: datetime
    ) -> Opportunity | None:
        detector = self._detectors.get(opp.kind.value)
        if event is None or detector is None:
            return None
        config = replace(self._settings.scan, share_sizes=(opp.shares,))
        return next((o for o in detector.detect(event, books, config, now) if o.fingerprint == opp.fingerprint), None)

    def _paper_row(
        self, opp: Opportunity, status: str, at: datetime, note: str, detected_edge: Decimal | None = None
    ) -> PmPaperTrade:
        return PmPaperTrade(
            source="scanner",
            opened_at=at,
            status=status,
            kind=opp.kind.value,
            fingerprint=opp.fingerprint,
            event_id=opp.event_id,
            condition_id=opp.condition_id,
            title=opp.title[:300],
            shares=opp.shares,
            capital=opp.capital,
            payout=opp.payout,
            fees=opp.fees,
            detected_edge=detected_edge if detected_edge is not None else opp.net_edge,
            realized_pnl=opp.net_edge if status == "settled" else None,
            latency_ms=self._settings.paper_latency_ms,
            resolves_at=opp.resolves_at,
            settled_at=at if status == "settled" else None,
            legs=_legs_json(opp),
            note=note,
        )
