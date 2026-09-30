"""Audit trail for every admin mutation. Details must never contain secret values."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from crypto_lab.infrastructure.db.models import AuditEvent
from crypto_lab.infrastructure.db.repositories import AuditRepository


@dataclass(frozen=True, slots=True)
class Actor:
    username: str
    ip: str = ""


SYSTEM = Actor("system")


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = AuditRepository(session)

    async def record(self, actor: Actor, action: str, target: str = "", **detail: Any) -> None:
        await self._repo.add(AuditEvent(actor=actor.username, action=action, target=target, detail=detail, ip=actor.ip))

    async def recent(self, limit: int = 100) -> Sequence[AuditEvent]:
        return await self._repo.recent(limit)
