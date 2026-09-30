from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from crypto_lab.container import Container
from crypto_lab.domain.bots import BotMode
from crypto_lab.domain.errors import ValidationError
from crypto_lab.domain.polymarket.wallets import ClosedPosition, LeaderboardEntry, WalletTrade
from crypto_lab.infrastructure.db.models import Bot
from crypto_lab.infrastructure.db.polymarket_models import PmWallet, PmWalletTrade
from crypto_lab.infrastructure.db.session import unit_of_work
from crypto_lab.services.audit import Actor
from crypto_lab.services.polymarket.wallet_tracker import (
    WalletTrackerService,
    set_wallet_tracked,
    validate_address,
)
from crypto_lab.workers.base import BotWorker

LEADER = "0x" + "1" * 40
WATCHED = "0x" + "2" * 40
BROKEN = "0x" + "3" * 40


class FakeWalletSource:
    async def leaderboard(self, *, period: str, order_by: str, limit: int) -> Sequence[LeaderboardEntry]:
        return [LeaderboardEntry(1, LEADER, "leader", Decimal(1000), Decimal(50_000))]

    async def closed_positions(self, wallet: str, *, max_rows: int) -> Sequence[ClosedPosition]:
        if wallet == BROKEN:
            raise RuntimeError("upstream error")
        return [
            ClosedPosition(
                wallet, "a", "c", Decimal("0.4"), Decimal(10), Decimal(6), Decimal(1), "Y", "t", "s", "e", None
            )
        ]

    async def trades(self, wallet: str, *, max_rows: int) -> Sequence[WalletTrade]:
        at = datetime(2026, 9, 1, tzinfo=UTC)
        return [
            WalletTrade(wallet, "0xtx", "a", "c", "BUY", Decimal(10), Decimal("0.4"), "Y", 0, "t", "s", "e", at),
        ]


async def test_run_once_refreshes_leaders_and_watchlist_and_is_idempotent(container: Container) -> None:
    async with unit_of_work(container.session_factory) as s:
        await set_wallet_tracked(s, WATCHED, True, Actor("tester"))
        await set_wallet_tracked(s, BROKEN, True, Actor("tester"))
    service = WalletTrackerService(FakeWalletSource(), container.session_factory)

    report = await service.run_once()
    again = await service.run_once()

    assert (report.leaderboard_wallets, report.wallets_refreshed, report.new_trades, report.errors) == (1, 2, 2, 1)
    assert again.new_trades == 0  # duplicate fills are ignored
    async with container.session_factory() as s:
        wallets = {w.address: w for w in (await s.execute(select(PmWallet))).scalars()}
        trades = (await s.execute(select(PmWalletTrade))).scalars().all()
    assert wallets[LEADER].leaderboard_rank == 1 and wallets[LEADER].stats["wins"] == 1
    assert wallets[WATCHED].tracked is True and len(trades) == 2


def test_address_validation() -> None:
    assert validate_address(" 0x" + "AB" * 20 + " ") == "0x" + "ab" * 20
    for bad in ("0x123", "ab" * 21, "0x" + "zz" * 20):
        with pytest.raises(ValidationError):
            validate_address(bad)


class CountingWorker(BotWorker):
    slug = "poly-scanner"
    interval_s = 0.01
    idle_interval_s = 0.01

    def __init__(self, container: Container) -> None:
        super().__init__(container)
        self.cycles: list[BotMode] = []
        self.closed = False

    async def run_cycle(self, mode: BotMode) -> str:
        self.cycles.append(mode)
        if len(self.cycles) == 2:
            raise RuntimeError("transient")
        if len(self.cycles) >= 3:
            async with unit_of_work(self.container.session_factory) as s:
                bot = await s.get(Bot, self.slug)
                assert bot is not None
                bot.kill_requested = True
        return "ok"

    async def aclose(self) -> None:
        self.closed = True


async def test_worker_loop_runs_in_mode_survives_errors_and_stops_on_kill(container: Container) -> None:
    async with unit_of_work(container.session_factory) as s:
        await container.bots(s).change_mode("poly-scanner", "paper", Actor("tester"))
    worker = CountingWorker(container)
    await worker.run_forever()
    assert worker.cycles == [BotMode.PAPER] * 3 and worker.closed is True
    async with container.session_factory() as s:
        bot = await s.get(Bot, "poly-scanner")
    assert bot is not None and bot.heartbeat_at is not None and bot.last_error == ""


async def test_worker_idles_when_off_and_can_be_stopped(container: Container) -> None:
    worker = CountingWorker(container)
    worker.stop()
    await worker.run_forever()
    assert worker.cycles == [] and worker.closed is True
