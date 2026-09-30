"""Overview, audit log, account (2FA) and health."""

from __future__ import annotations

from typing import Annotated

import segno
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from starlette.responses import Response

from crypto_lab.domain.errors import DomainError
from crypto_lab.security import totp
from crypto_lab.services.audit import AuditService
from crypto_lab.services.paper import portfolio
from crypto_lab.web.deps import AdminDep, ContainerDep, CsrfAdminDep, DbDep, actor_for
from crypto_lab.web.routers.paper import activity_context
from crypto_lab.web.templating import render

router = APIRouter(tags=["pages"])


@router.get("/healthz", include_in_schema=False)
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/")
async def overview(request: Request, container: ContainerDep, db: DbDep, admin: AdminDep) -> Response:
    bots = await container.bots(db).list()
    credentials = await container.vault(db).list()
    events = await AuditService(db).recent(8)
    return render(
        request,
        "overview.html",
        {
            **await activity_context(db),
            "portfolio": await portfolio(db),
            "bots": bots,
            "credentials": credentials,
            "events": events,
            "live_enabled": container.settings.live_trading_enabled,
        },
        admin=admin,
    )


@router.get("/admin/audit")
async def audit_log(request: Request, db: DbDep, admin: AdminDep) -> Response:
    return render(request, "admin/audit.html", {"events": await AuditService(db).recent(200)}, admin=admin)


def _totp_context(container: ContainerDep, username: str, secret: str) -> dict[str, object]:
    uri = totp.provisioning_uri(secret, username, container.settings.app_name)
    qr_svg = segno.make(uri, error="m").svg_inline(scale=5, dark="#07100f", light="#ffffff")
    return {"secret": secret, "qr_svg": qr_svg}


@router.get("/account/2fa")
async def totp_form(request: Request, container: ContainerDep, admin: AdminDep) -> Response:
    ctx = {} if admin.user.totp_enabled else _totp_context(container, admin.user.username, totp.new_secret())
    return render(request, "account/totp.html", {**ctx, "error": None}, admin=admin)


@router.post("/account/2fa")
async def totp_enable(
    request: Request,
    container: ContainerDep,
    db: DbDep,
    admin: CsrfAdminDep,
    secret: Annotated[str, Form(max_length=64)],
    code: Annotated[str, Form(max_length=12)],
) -> Response:
    try:
        await container.auth(db).enable_totp(admin.user, secret, code, actor_for(admin, request))
    except DomainError as exc:
        return render(
            request,
            "account/totp.html",
            {**_totp_context(container, admin.user.username, secret), "error": str(exc)},
            admin=admin,
            status_code=422,
        )
    await db.commit()
    return RedirectResponse("/account/2fa?flash=totp_on", status_code=303)
