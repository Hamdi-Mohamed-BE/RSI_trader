import asyncio
from datetime import timedelta
from decimal import Decimal

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import select

from crypto_lab.config import Settings
from crypto_lab.infrastructure.db.base import utcnow
from crypto_lab.infrastructure.db.models import Bot
from crypto_lab.infrastructure.db.paper_models import PaperAccount, PaperPosition, WorkerLease
from crypto_lab.infrastructure.db.session import unit_of_work
from crypto_lab.services.paper import close_position, lock_portfolio, open_position, portfolio
from crypto_lab.web.app import create_app
from tests.conftest import csrf_from
from tests.integration.test_wallet_tracker_and_worker import CountingWorker

D = Decimal


async def prepare(container):
    async with unit_of_work(container.session_factory) as s:
        s.add(PaperAccount(id=1, initial=D(100), trade_limit=D(10)))
        for bot in await s.scalars(select(Bot)):
            bot.mode = "paper"


def position(key, amount="10", bot="poly-scanner"):
    return PaperPosition(
        bot=bot, key=key, symbol=key, venue="test", quantity=D(1), capital=D(amount), detail={"asset": key}
    )


async def enter(container, row):
    async with unit_of_work(container.session_factory) as s:
        await lock_portfolio(s)
        return await open_position(s, row)


async def test_shared_cash_is_atomic_under_simultaneous_entries(container):
    await prepare(container)
    notes = await asyncio.gather(*(enter(container, position(str(i))) for i in range(15)))
    assert notes.count("") == 10
    async with container.session_factory() as s:
        p = await portfolio(s)
        assert p.cash == 0 and p.locked == 100 and p.marked_equity is None


async def test_cap_fees_duplicate_and_close_accounting(container):
    await prepare(container)
    assert "cap" in await enter(container, position("over", "10.001"))
    row = position("good")
    assert await enter(container, row) == ""
    assert "already" in await enter(container, position("good"))
    async with unit_of_work(container.session_factory) as s:
        await lock_portfolio(s)
        assert await close_position(s, row.id, D("11.25"), "test net of costs")
        assert not await close_position(s, row.id, D(1000), "duplicate")
    async with container.session_factory() as s:
        p = await portfolio(s)
        assert (p.cash, p.locked, p.realized, p.marked_equity) == (D("101.25"), 0, D("1.25"), D("101.25"))


async def test_stopped_bot_cannot_open_or_close_and_holdings_remain(container):
    await prepare(container)
    row = position("held")
    await enter(container, row)
    async with unit_of_work(container.session_factory) as s:
        bot = await s.get(Bot, "poly-scanner")
        bot.kill_requested = True
        bot.mode = "off"
    assert "not enabled" in await enter(container, position("new"))
    async with unit_of_work(container.session_factory) as s:
        await lock_portfolio(s)
        assert not await close_position(s, row.id, D(9), "must not fill")
        assert (await portfolio(s)).locked == 10


async def test_stale_marks_are_not_reported_as_current_equity(container):
    await prepare(container)
    row = position("stale")
    row.mark, row.mark_at = D(9), utcnow() - timedelta(minutes=6)
    await enter(container, row)
    async with container.session_factory() as s:
        assert (await portfolio(s)).marked_equity is None


async def test_bot_position_caps(container):
    await prepare(container)
    assert await enter(container, position("sol1", bot="sol-rotation")) == ""
    assert "limit" in await enter(container, position("sol2", bot="sol-rotation"))
    assert await enter(container, position("copy1", bot="poly-copy")) == ""
    dup = position("copy2", bot="poly-copy")
    dup.detail = {"asset": "copy1"}
    assert "Already holding" in await enter(container, dup)


async def test_lease_prevents_two_workers_and_error_not_cleared_by_heartbeat(container):
    first, second = CountingWorker(container), CountingWorker(container)
    await first._read_control()
    with pytest.raises(RuntimeError, match="already owns"):
        await second._read_control()
    await first._report("feed failed")
    await first._read_control()
    async with container.session_factory() as s:
        assert (await s.get(Bot, first.slug)).last_error == "feed failed"
    async with unit_of_work(container.session_factory) as s:
        lease = await s.get(WorkerLease, first.slug)
        lease.at = utcnow() - timedelta(seconds=35)
    await second._read_control()


async def test_local_bypass_keeps_csrf_host_boundary_and_live_lock(container, settings):
    settings.local_paper_access = True
    app = create_app(settings, container)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8090") as c:
            assert (await c.get("/")).status_code == 200
            assert (await c.get("/login")).headers["location"] == "/"
            for path in ("/paper", "/activity", "/polymarket/paper"):
                assert (await c.get(path)).status_code == 200
            assert (await c.get("/", headers={"Host": "evil.example"})).status_code == 403
            assert (await c.get("/", headers={"Origin": "https://evil.example"})).status_code == 403
            assert (await c.get("/admin/keys")).status_code == 403
            assert (await c.post("/admin/bots/poly-copy/mode", data={"mode": "paper"})).status_code == 403
            csrf = await csrf_from(c, "/admin/bots")
            assert (
                await c.post("/admin/bots/poly-copy/mode", data={"mode": "paper", "csrf_token": csrf})
            ).status_code == 303
            assert (
                await c.post("/admin/bots/poly-copy/mode", data={"mode": "live", "csrf_token": csrf})
            ).status_code == 422
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("192.168.1.30", 1000)), base_url="http://127.0.0.1:8090"
        ) as remote:
            assert (await remote.get("/")).status_code == 403


@pytest.mark.parametrize(
    "extra",
    [
        {"live_trading_enabled": True},
        {"host": "0.0.0.0"},  # noqa: S104 - rejection test
        {"environment": "production"},
    ],
)
def test_unsafe_bypass_config_rejected(extra):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, local_paper_access=True, **extra)
