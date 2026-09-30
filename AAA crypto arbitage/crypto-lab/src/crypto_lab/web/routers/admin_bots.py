"""Admin: bot modes (OFF / SHADOW / PAPER / LIVE) and kill switch."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from starlette.responses import Response

from crypto_lab.domain.bots import BotMode
from crypto_lab.domain.errors import DomainError
from crypto_lab.web.deps import AdminDep, ContainerDep, CsrfAdminDep, DbDep, actor_for
from crypto_lab.web.templating import render

router = APIRouter(prefix="/admin/bots", tags=["admin:bots"])


async def _page(
    request: Request,
    container: ContainerDep,
    db: DbDep,
    admin: AdminDep,
    *,
    error: str | None = None,
    status_code: int = 200,
) -> Response:
    return render(
        request,
        "admin/bots.html",
        {
            "bots": await container.bots(db).list(),
            "modes": list(BotMode),
            "error": error,
            "live_enabled": container.settings.live_trading_enabled,
        },
        admin=admin,
        status_code=status_code,
    )


@router.get("")
async def list_bots(request: Request, container: ContainerDep, db: DbDep, admin: AdminDep) -> Response:
    return await _page(request, container, db, admin)


@router.post("/{slug}/mode")
async def change_mode(
    request: Request,
    slug: str,
    container: ContainerDep,
    db: DbDep,
    admin: CsrfAdminDep,
    mode: Annotated[str, Form()],
    confirmation: Annotated[str, Form(max_length=64)] = "",
    code: Annotated[str, Form(max_length=12)] = "",
) -> Response:
    two_factor_ok = bool(code) and container.auth(db).verify_totp(admin.user, code)
    try:
        await container.bots(db).change_mode(
            slug, mode, actor_for(admin, request), confirmation_text=confirmation, two_factor_verified=two_factor_ok
        )
    except DomainError as exc:  # the policy refuses before anything is mutated
        return await _page(request, container, db, admin, error=str(exc), status_code=422)
    await db.commit()
    return RedirectResponse("/admin/bots?flash=mode", status_code=303)


@router.post("/{slug}/kill")
async def kill(request: Request, slug: str, container: ContainerDep, db: DbDep, admin: CsrfAdminDep) -> Response:
    await container.bots(db).kill(slug, actor_for(admin, request))
    await db.commit()
    return RedirectResponse("/admin/bots?flash=killed", status_code=303)
