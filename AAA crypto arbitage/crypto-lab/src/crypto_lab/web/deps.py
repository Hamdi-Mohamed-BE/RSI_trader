"""FastAPI dependencies (typed with ``Annotated``) shared by all routers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession

from crypto_lab.container import Container
from crypto_lab.infrastructure.db.models import AdminSession
from crypto_lab.security.tokens import constant_time_equals
from crypto_lab.services.audit import Actor

SESSION_COOKIE = "cl_session"


class LoginRequiredError(Exception):
    """Raised when a page needs an authenticated admin; handled by a redirect to /login."""

    def __init__(self, next_path: str = "/") -> None:
        super().__init__(next_path)
        self.next_path = next_path


class CsrfError(Exception):
    """Raised when a form's CSRF token is missing or wrong."""


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


async def get_db(container: ContainerDep) -> AsyncIterator[AsyncSession]:
    """One session per request. Mutating routes commit explicitly; anything uncommitted is rolled back."""
    async with container.session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


DbDep = Annotated[AsyncSession, Depends(get_db)]


def client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


async def optional_admin(request: Request, container: ContainerDep, db: DbDep) -> AdminSession | None:
    if container.settings.local_paper_access:
        local: AdminSession = request.app.state.local_admin
        return local
    return await container.auth(db).resolve(request.cookies.get(SESSION_COOKIE))


async def require_admin(
    request: Request, admin: Annotated[AdminSession | None, Depends(optional_admin)]
) -> AdminSession:
    if admin is None:
        raise LoginRequiredError(request.url.path)
    return admin


AdminDep = Annotated[AdminSession, Depends(require_admin)]


def actor_for(admin: AdminSession, request: Request) -> Actor:
    return Actor(admin.user.username, client_ip(request))


async def verify_csrf(admin: AdminDep, csrf_token: Annotated[str, Form()] = "") -> AdminSession:
    if not csrf_token or not constant_time_equals(csrf_token, admin.csrf_token):
        raise CsrfError
    return admin


CsrfAdminDep = Annotated[AdminSession, Depends(verify_csrf)]
