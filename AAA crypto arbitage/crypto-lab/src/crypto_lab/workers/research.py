"""Shared helpers for quote-based paper workers. All HTTP clients are public/read-only."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from crypto_lab.infrastructure.db.base import utcnow
from crypto_lab.infrastructure.db.paper_models import PaperPosition
from crypto_lab.infrastructure.db.session import unit_of_work
from crypto_lab.services.paper import close_position, lock_portfolio, open_position
from crypto_lab.workers.base import BotWorker


class ResearchWorker(BotWorker):
    async def positions(self) -> list[PaperPosition]:
        async with self.container.session_factory() as s:
            return list(
                await s.scalars(
                    select(PaperPosition).where(PaperPosition.bot == self.slug, PaperPosition.closed_at.is_(None))
                )
            )

    async def enter(self, row: PaperPosition) -> str:
        async with unit_of_work(self.container.session_factory) as s:
            await lock_portfolio(s)
            return await open_position(s, row)

    async def mark_or_exit(self, row: PaperPosition, proceeds: Decimal, reason: str = "") -> None:
        async with unit_of_work(self.container.session_factory) as s:
            await lock_portfolio(s)
            current = await s.get(PaperPosition, row.id)
            if current and current.closed_at is None:
                current.mark, current.mark_at = proceeds, utcnow()
                if reason:
                    await close_position(s, row.id, proceeds, reason)
