"""Repositories: the only place that builds SQL queries for platform tables (Repository pattern)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from crypto_lab.infrastructure.db.models import AdminSession, AdminUser, ApiCredential, AuditEvent, Bot


class AdminUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, user_id: int) -> AdminUser | None:
        return await self._s.get(AdminUser, user_id)

    async def by_username(self, username: str) -> AdminUser | None:
        return (await self._s.execute(select(AdminUser).where(AdminUser.username == username))).scalar_one_or_none()

    async def count(self) -> int:
        return int((await self._s.execute(select(func.count()).select_from(AdminUser))).scalar_one())

    async def add(self, user: AdminUser) -> AdminUser:
        self._s.add(user)
        await self._s.flush()
        return user


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, admin_session: AdminSession) -> AdminSession:
        self._s.add(admin_session)
        await self._s.flush()
        return admin_session

    async def by_digest(self, digest: str) -> AdminSession | None:
        stmt = select(AdminSession).where(AdminSession.token_digest == digest)
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def delete_by_digest(self, digest: str) -> None:
        await self._s.execute(delete(AdminSession).where(AdminSession.token_digest == digest))

    async def delete_expired(self, now: datetime) -> None:
        await self._s.execute(delete(AdminSession).where(AdminSession.expires_at <= now))


class CredentialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def list(self) -> Sequence[ApiCredential]:
        stmt = select(ApiCredential).order_by(ApiCredential.provider, ApiCredential.label)
        return (await self._s.execute(stmt)).scalars().all()

    async def get(self, credential_id: str) -> ApiCredential | None:
        return await self._s.get(ApiCredential, credential_id)

    async def enabled_for(self, provider: str, environment: str) -> Sequence[ApiCredential]:
        stmt = select(ApiCredential).where(
            ApiCredential.provider == provider,
            ApiCredential.environment == environment,
            ApiCredential.enabled.is_(True),
        )
        return (await self._s.execute(stmt)).scalars().all()

    async def add(self, credential: ApiCredential) -> ApiCredential:
        self._s.add(credential)
        await self._s.flush()
        return credential

    async def delete(self, credential: ApiCredential) -> None:
        await self._s.delete(credential)
        await self._s.flush()


class BotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def list(self) -> Sequence[Bot]:
        return (await self._s.execute(select(Bot).order_by(Bot.model, Bot.slug))).scalars().all()

    async def get(self, slug: str) -> Bot | None:
        return await self._s.get(Bot, slug)

    async def add(self, bot: Bot) -> Bot:
        self._s.add(bot)
        await self._s.flush()
        return bot


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, event: AuditEvent) -> None:
        self._s.add(event)
        await self._s.flush()

    async def recent(self, limit: int = 100) -> Sequence[AuditEvent]:
        stmt = select(AuditEvent).order_by(AuditEvent.at.desc(), AuditEvent.id.desc()).limit(limit)
        return (await self._s.execute(stmt)).scalars().all()
