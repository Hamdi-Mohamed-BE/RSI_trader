"""Jinja2 environment and a render helper that injects the admin context."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates
from jinja2 import Undefined
from starlette.responses import Response

from crypto_lab.config import PACKAGE_ROOT
from crypto_lab.infrastructure.db.models import AdminSession

templates = Jinja2Templates(directory=PACKAGE_ROOT / "web" / "templates")

# Flash messages are looked up from fixed codes so no free text from the URL is ever rendered.
FLASH_MESSAGES: dict[str, tuple[str, str]] = {
    "saved": ("good", "Saved."),
    "rotated": ("good", "Credential rotated. Run a connection test again."),
    "deleted": ("warn", "Credential deleted."),
    "enabled": ("good", "Enabled."),
    "disabled": ("warn", "Disabled."),
    "mode": ("good", "Bot mode updated."),
    "killed": ("bad", "Worker stopped. Existing paper holdings stay recorded and resume management when restarted."),
    "totp_on": ("good", "Two-factor authentication is on."),
    "logged_out": ("neutral", "Signed out."),
}


def _fmt_dt(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M UTC") if value else "—"


def _missing(value: object) -> bool:
    """Missing data renders as an em dash, never as zero."""
    return value is None or value == "" or isinstance(value, Undefined)


def _fmt_money(value: Decimal | float | str | None, places: int = 2) -> str:
    return "—" if _missing(value) else f"{Decimal(str(value)):,.{places}f}"


def _fmt_pct(value: Decimal | float | str | None, places: int = 2) -> str:
    """Format a fraction (0.0123) as a percentage (1.23%)."""
    return "—" if _missing(value) else f"{float(value) * 100:,.{places}f}%"  # type: ignore[arg-type]


def _fmt_num(value: float | None, places: int = 2) -> str:
    return "—" if _missing(value) else f"{value:,.{places}f}"


templates.env.filters.update(dt=_fmt_dt, money=_fmt_money, pct=_fmt_pct, num=_fmt_num)
MODE_BADGE = {"off": "badge-neutral", "shadow": "badge-safe", "paper": "badge-warn", "live": "badge-bad"}
templates.env.globals["mode_badge"] = MODE_BADGE


def render(
    request: Request,
    name: str,
    context: dict[str, Any] | None = None,
    *,
    admin: AdminSession | None = None,
    status_code: int = 200,
) -> Response:
    ctx: dict[str, Any] = {
        "app_name": request.app.state.container.settings.app_name,
        "admin": admin,
        "csrf_token": admin.csrf_token if admin else "",
        "flash": FLASH_MESSAGES.get(request.query_params.get("flash", "")),
        "path": request.url.path,
        "local_paper_access": request.app.state.container.settings.local_paper_access,
        "autostart_workers": request.app.state.container.settings.autostart_workers,
    }
    ctx.update(context or {})
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)
