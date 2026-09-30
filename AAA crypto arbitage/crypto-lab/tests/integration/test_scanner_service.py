from dataclasses import replace
from decimal import Decimal

from sqlalchemy import select

from crypto_lab.container import Container
from crypto_lab.domain.bots import BotMode
from crypto_lab.domain.polymarket.arbitrage import ScanConfig
from crypto_lab.infrastructure.db.polymarket_models import PmOpportunity, PmPaperTrade, PmScanRun
from crypto_lab.services.polymarket.scanner import ScannerService, ScannerSettings, event_groups
from tests.polymarket_factories import NOW, NOW_MS, FakeBooks, FakeCatalog, book, event, market

D = Decimal
SETTINGS = ScannerSettings(
    scan=ScanConfig(share_sizes=(D(100),), min_net_edge_usdc=D("0.01"), min_edge_pct=D(0)), paper_latency_ms=0
)
PROFITABLE = {"c1-yes": book("c1-yes", asks=[("0.45", "500")]), "c1-no": book("c1-no", asks=[("0.50", "500")])}
FLAT = {"c1-yes": book("c1-yes", asks=[("0.50", "500")]), "c1-no": book("c1-no", asks=[("0.50", "500")])}


async def _no_sleep(_: float) -> None:
    return None


def _service(container: Container, books: FakeBooks, settings: ScannerSettings = SETTINGS) -> ScannerService:
    return ScannerService(
        FakeCatalog([event(market("c1"))]),
        books,
        container.session_factory,
        settings=settings,
        clock=lambda: NOW,
        sleep=_no_sleep,
    )


async def _all(container: Container, model: type) -> list:  # type: ignore[type-arg]
    async with container.session_factory() as s:
        return list((await s.execute(select(model))).scalars().all())


async def test_shadow_scan_records_then_deduplicates_then_closes(container: Container) -> None:
    books = FakeBooks(PROFITABLE, PROFITABLE, FLAT)
    service = _service(container, books)

    first = await service.run_once(BotMode.SHADOW)
    second = await service.run_once(BotMode.SHADOW)
    assert (first.opportunities, first.new_opportunities) == (1, 1)
    assert (second.opportunities, second.new_opportunities) == (1, 0)
    [row] = await _all(container, PmOpportunity)
    assert row.seen_count == 2 and row.active is True and row.net_edge == D("5.00")

    await service.run_once(BotMode.SHADOW)
    [row] = await _all(container, PmOpportunity)
    assert row.active is False
    assert len(await _all(container, PmScanRun)) == 3
    assert await _all(container, PmPaperTrade) == []  # shadow never paper-trades


async def test_paper_fill_uses_the_second_book_snapshot(container: Container) -> None:
    better = {"c1-yes": book("c1-yes", asks=[("0.44", "500")]), "c1-no": book("c1-no", asks=[("0.50", "500")])}
    report = await _service(container, FakeBooks(PROFITABLE, better)).run_once(BotMode.PAPER)
    assert (report.paper_filled, report.paper_missed) == (1, 0)
    [trade] = await _all(container, PmPaperTrade)
    assert trade.status == "settled"
    assert trade.detected_edge == D("5.00") and trade.realized_pnl == D("6.00")


async def test_paper_records_missed_when_edge_disappears(container: Container) -> None:
    report = await _service(container, FakeBooks(PROFITABLE, FLAT)).run_once(BotMode.PAPER)
    assert (report.paper_filled, report.paper_missed) == (0, 1)
    [trade] = await _all(container, PmPaperTrade)
    assert trade.status == "missed" and trade.realized_pnl is None and "gone" in trade.note


async def test_stale_books_are_ignored(container: Container) -> None:
    stale = {k: replace(b, received_ms=NOW_MS - 60_000) for k, b in PROFITABLE.items()}
    report = await _service(container, FakeBooks(stale)).run_once(BotMode.SHADOW)
    assert report.stale_books == 2 and report.opportunities == 0


async def test_paper_capital_limit_is_respected(container: Container) -> None:
    tiny = replace(SETTINGS, paper_bankroll_usdc=D(10))
    report = await _service(container, FakeBooks(PROFITABLE, PROFITABLE), tiny).run_once(BotMode.PAPER)
    assert report.paper_missed == 1
    [trade] = await _all(container, PmPaperTrade)
    assert "capital" in trade.note


def test_event_groups_never_split_an_event() -> None:
    events = [event(market(f"m{i}"), event_id=str(i)) for i in range(5)]  # 2 tokens each
    groups = list(event_groups(events, max_tokens=4))
    assert [len(g) for g in groups] == [2, 2, 1]
    big = event(*[market(f"b{i}") for i in range(4)], event_id="big")  # 8 tokens > limit
    assert [len(g) for g in event_groups([big, events[0]], max_tokens=4)] == [1, 1]


async def test_scan_reports_near_miss_sums(container: Container) -> None:
    report = await _service(container, FakeBooks(FLAT)).run_once(BotMode.SHADOW)
    assert report.best_ask_sum == D("1.00") and report.best_bid_sum is None


async def test_quiet_book_with_old_server_timestamp_is_not_stale(container: Container) -> None:
    """The CLOB timestamp is the last *change*; a quiet book received just now is current."""
    quiet = {k: replace(b, timestamp_ms=NOW_MS - 3_600_000, received_ms=NOW_MS) for k, b in PROFITABLE.items()}
    report = await _service(container, FakeBooks(quiet)).run_once(BotMode.SHADOW)
    assert report.stale_books == 0 and report.opportunities == 1
