"""Dashboard-owned workers; kill/off settings survive restarts."""

from __future__ import annotations

import asyncio
import contextlib
import logging

from crypto_lab.container import Container
from crypto_lab.infrastructure.db.models import Bot
from crypto_lab.workers import available_workers, create_worker

logger = logging.getLogger(__name__)


class WorkerManager:
    def __init__(self, container: Container) -> None:
        self.container = container
        self.tasks: dict[str, asyncio.Task[None]] = {}
        self.supervisor: asyncio.Task[None] | None = None

    def start(self) -> None:
        self.supervisor = asyncio.create_task(self.run())

    async def run(self) -> None:
        while True:
            for slug in available_workers():
                task = self.tasks.get(slug)
                if task and not task.done():
                    continue
                if task and not task.cancelled() and task.exception():
                    logger.warning("%s worker exited: %s", slug, task.exception())
                async with self.container.session_factory() as s:
                    bot = await s.get(Bot, slug)
                    enabled = bot and not bot.kill_requested and bot.mode in {"paper", "shadow"}
                if enabled:
                    self.tasks[slug] = asyncio.create_task(create_worker(slug, self.container).run_forever())
            await asyncio.sleep(5)

    async def stop(self) -> None:
        if self.supervisor:
            self.supervisor.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.supervisor
        for task in self.tasks.values():
            task.cancel()
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
