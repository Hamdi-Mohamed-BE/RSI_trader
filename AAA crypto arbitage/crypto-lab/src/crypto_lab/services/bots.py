"""Bot registry and guarded mode changes. Workers read ``mode`` / ``kill_requested`` from the database."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from crypto_lab.domain.bots import DEFAULT_BOTS, BotDefinition, BotMode, ModeTransitionPolicy, TransitionRequest
from crypto_lab.domain.errors import NotFoundError, ValidationError
from crypto_lab.infrastructure.db.base import utcnow
from crypto_lab.infrastructure.db.models import Bot
from crypto_lab.infrastructure.db.repositories import BotRepository
from crypto_lab.services.audit import SYSTEM, Actor, AuditService


class BotService:
    def __init__(self, session: AsyncSession, policy: ModeTransitionPolicy, live_trading_enabled: bool) -> None:
        self._repo = BotRepository(session)
        self._audit = AuditService(session)
        self._policy = policy
        self._live_enabled = live_trading_enabled

    async def seed(self, definitions: Sequence[BotDefinition] = DEFAULT_BOTS, *, paper: bool = False) -> None:
        """Insert missing bots (idempotent); never changes the mode of an existing bot."""
        for definition in definitions:
            if await self._repo.get(definition.slug) is None:
                await self._repo.add(
                    Bot(
                        slug=definition.slug,
                        name=definition.name,
                        model=definition.model,
                        description=definition.description,
                        mode=BotMode.PAPER.value if paper else BotMode.OFF.value,
                    )
                )
                await self._audit.record(SYSTEM, "bot.seeded", definition.slug)

    async def list(self) -> Sequence[Bot]:
        return await self._repo.list()

    async def _require(self, slug: str) -> Bot:
        bot = await self._repo.get(slug)
        if bot is None:
            raise NotFoundError("Bot not found.")
        return bot

    async def change_mode(
        self, slug: str, target: str, actor: Actor, *, confirmation_text: str = "", two_factor_verified: bool = False
    ) -> Bot:
        bot = await self._require(slug)
        try:
            target_mode = BotMode(target)
        except ValueError as exc:
            raise ValidationError("Unknown mode.") from exc
        request = TransitionRequest(
            bot_slug=bot.slug,
            current=BotMode(bot.mode),
            target=target_mode,
            gate_passed=bot.gate_passed,
            live_trading_enabled=self._live_enabled,
            confirmation_text=confirmation_text,
            two_factor_verified=two_factor_verified,
        )
        self._policy.check(request)
        previous = bot.mode
        bot.mode = target_mode.value
        bot.kill_requested = False
        await self._audit.record(actor, "bot.mode_changed", slug, previous=previous, current=bot.mode)
        return bot

    async def kill(self, slug: str, actor: Actor) -> Bot:
        """Emergency stop: request the worker to cancel orders, reconcile and go OFF."""
        bot = await self._require(slug)
        previous = bot.mode
        bot.kill_requested = True
        bot.mode = BotMode.OFF.value
        await self._audit.record(actor, "bot.killed", slug, previous=previous)
        return bot

    async def heartbeat(self, slug: str, error: str | None = None) -> Bot:
        bot = await self._require(slug)
        bot.heartbeat_at = utcnow()
        if error is not None:
            bot.last_error = error[:2000]
        return bot
