"""Shared web helpers for the store and admin routers (templates, forms, cookies)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qs, urlsplit

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from . import security

MAX_FORM_BYTES = 20_000


class WebState:
    templates: Jinja2Templates | None = None
    base_context: Callable[[Request, str], dict[str, Any]] | None = None


state = WebState()


async def read_form(request: Request) -> dict[str, str]:
    """Parse an application/x-www-form-urlencoded body without python-multipart."""
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" not in content_type:
        return {}
    raw = await request.body()
    if len(raw) > MAX_FORM_BYTES:
        return {}
    parsed = parse_qs(raw.decode("utf-8", "replace"), keep_blank_values=True, max_num_fields=200)
    return {key: values[-1] for key, values in parsed.items()}


def same_origin(request: Request) -> bool:
    """Reject cross-site form posts when the browser tells us where they came from."""
    origin = request.headers.get("origin") or request.headers.get("referer")
    if not origin or origin == "null":
        return True
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    return urlsplit(origin).netloc.lower() == host.lower()


def render(request: Request, name: str, context: dict[str, Any], *, active: str = "", status_code: int = 200,
           csrf: bool = True, admin: bool = False) -> HTMLResponse:
    assert state.templates is not None and state.base_context is not None
    base = {} if admin else state.base_context(request, active)
    token, created = security.csrf_token_for(request) if csrf else ("", False)
    response = state.templates.TemplateResponse(
        request=request, name=name, context=base | {"request": request, "csrf_token": token} | context,
        status_code=status_code,
    )
    if created:
        set_csrf_cookie(request, response, token)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    if admin:
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def set_csrf_cookie(request: Request, response: Response, token: str) -> None:
    response.set_cookie(security.CSRF_COOKIE, token, max_age=7 * 24 * 3600, httponly=True, samesite="lax",
                        secure=security.cookie_secure(request), path="/")


def redirect(url: str) -> RedirectResponse:
    response = RedirectResponse(url, status_code=303)
    response.headers["Cache-Control"] = "no-store"
    return response
