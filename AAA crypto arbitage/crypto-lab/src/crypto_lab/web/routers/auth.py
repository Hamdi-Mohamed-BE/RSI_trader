"""Login / logout."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from starlette.responses import Response

from crypto_lab.domain.errors import AuthenticationError
from crypto_lab.services.audit import Actor
from crypto_lab.web.deps import SESSION_COOKIE, ContainerDep, CsrfAdminDep, DbDep, client_ip
from crypto_lab.web.templating import render

router = APIRouter(tags=["auth"])


def _safe_next(next_path: str) -> str:
    """Only allow local absolute paths to prevent open redirects."""
    return next_path if next_path.startswith("/") and not next_path.startswith("//") else "/"


@router.get("/login")
async def login_form(request: Request, container: ContainerDep, db: DbDep, next: str = "/") -> Response:
    if container.settings.local_paper_access:
        return RedirectResponse("/", status_code=303)
    has_admin = await container.auth(db).has_admin()
    return render(request, "login.html", {"next": _safe_next(next), "has_admin": has_admin, "error": None})


@router.post("/login")
async def login(
    request: Request,
    container: ContainerDep,
    db: DbDep,
    username: Annotated[str, Form(max_length=64)],
    password: Annotated[str, Form(max_length=256)],
    code: Annotated[str, Form(max_length=12)] = "",
    next: Annotated[str, Form(max_length=200)] = "/",
) -> Response:
    ip = client_ip(request)
    auth = container.auth(db)
    if not container.login_limiter.allow(ip):
        return render(
            request,
            "login.html",
            {"next": _safe_next(next), "has_admin": True, "error": "Too many attempts. Wait a minute and try again."},
            status_code=429,
        )
    try:
        issued = await auth.login(username, password, code, ip, request.headers.get("user-agent", ""))
    except AuthenticationError as exc:
        await db.commit()  # persist failure counters and audit rows
        return render(
            request, "login.html", {"next": _safe_next(next), "has_admin": True, "error": str(exc)}, status_code=401
        )
    await db.commit()
    response = RedirectResponse(_safe_next(next), status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        issued.token,
        httponly=True,
        samesite="strict",
        secure=container.settings.cookie_secure,
        max_age=container.settings.session_ttl_minutes * 60,
        path="/",
    )
    return response


@router.post("/logout")
async def logout(request: Request, container: ContainerDep, db: DbDep, admin: CsrfAdminDep) -> Response:
    await container.auth(db).logout(request.cookies.get(SESSION_COOKIE), Actor(admin.user.username, client_ip(request)))
    await db.commit()
    response = RedirectResponse("/login?flash=logged_out", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response
