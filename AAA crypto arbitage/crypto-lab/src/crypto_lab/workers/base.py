"""Worker loop (Template Method).

The loop reads the bot's control row every cycle, so the dashboard's mode switch and kill button take effect without
restarting processes. Subclasses implement :meth:`BotWorker.run_cycle` only.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
import uuid
from abc import ABC, abstractmethod
from datetime import timedelta

from crypto_lab.container import Container
from crypto_lab.domain.bots import BotMode
from crypto_lab.infrastructure.db.base import utcnow
from crypto_lab.infrastructure.db.paper_models import PaperEvent, WorkerLease
from crypto_lab.infrastructure.db.session import unit_of_work
from crypto_lab.services.paper import lock_portfolio

logger = logging.getLogger(__name__)


class BotWorker(ABC):
    slug: str
    interval_s: float = 30.0
    idle_interval_s: float = 2.0

    def __init__(self, container: Container) -> None:
        self.container = container
        self._stop = asyncio.Event()
        self._owner = uuid.uuid4().hex

    @abstractmethod
    async def run_cycle(self, mode: BotMode) -> str:
        """Do one unit of work in ``mode`` (never OFF) and return a short status line."""

    async def aclose(self) -> None:  # noqa: B027 - optional hook
        """Release clients; override when the worker owns connections."""

    def stop(self) -> None:
        self._stop.set()

    async def _read_control(self) -> tuple[BotMode, bool]:
        async with unit_of_work(self.container.session_factory) as session:
            await lock_portfolio(session)
            lease = await session.get(WorkerLease, self.slug)
            now = utcnow()
            if lease and lease.owner != self._owner and lease.at > now - timedelta(seconds=30):
                raise RuntimeError("Another process already owns this worker")
            if lease:
                lease.owner, lease.at = self._owner, now
            else:
                session.add(WorkerLease(slug=self.slug, owner=self._owner, at=now))
            bot = await self.container.bots(session).heartbeat(self.slug)
            return BotMode(bot.mode), bot.kill_requested

    async def _report(self, error: str, status: str = "") -> None:
        async with unit_of_work(self.container.session_factory) as session:
            await self.container.bots(session).heartbeat(self.slug, error=error)
            session.add(
                PaperEvent(bot=self.slug, status="error" if error else "cycle", message=(error or status)[:2000])
            )

    async def run_once(self, mode: BotMode) -> str:
        if mode not in {BotMode.PAPER, BotMode.SHADOW}:
            return "Only paper and shadow research are supported."
        return await self.run_cycle(mode)

    async def run_forever(self) -> None:
        cycle: asyncio.Task[str] | None = None
        cycle_mode: BotMode | None = None
        due = 0.0
        try:
            while not self._stop.is_set():
                mode, kill = await self._read_control()
                if cycle and cycle.done():
                    try:
                        await self._report("", cycle.result())
                    except Exception as exc:
                        logger.exception("Cycle failed for %s", self.slug)
                        await self._report(f"{type(exc).__name__}: {exc}"[:500])
                    cycle = None
                    due = time.monotonic() + self.interval_s
                if kill:
                    break
                if cycle and mode != cycle_mode:
                    cycle.cancel()
                    await asyncio.gather(cycle, return_exceptions=True)
                    cycle, due = None, 0.0
                if mode in {BotMode.PAPER, BotMode.SHADOW} and cycle is None and time.monotonic() >= due:
                    cycle_mode = mode
                    cycle = asyncio.create_task(self.run_cycle(mode))
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(self._stop.wait(), timeout=self.idle_interval_s)
        finally:
            if cycle:
                cycle.cancel()
                await asyncio.gather(cycle, return_exceptions=True)
            async with unit_of_work(self.container.session_factory) as session:
                await lock_portfolio(session)
                lease = await session.get(WorkerLease, self.slug)
                if lease and lease.owner == self._owner:
                    await session.delete(lease)
            await self.aclose()
