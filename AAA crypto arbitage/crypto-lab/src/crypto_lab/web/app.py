"""FastAPI application factory."""

from __future__ import annotations

import logging
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response

from crypto_lab.config import PACKAGE_ROOT, Settings, get_settings
from crypto_lab.container import Container
from crypto_lab.domain.errors import DomainError, NotFoundError
from crypto_lab.infrastructure.db.migrations import upgrade_to_head
from crypto_lab.infrastructure.db.models import AdminSession, AdminUser
from crypto_lab.infrastructure.db.paper_models import PaperAccount
from crypto_lab.infrastructure.db.session import unit_of_work
from crypto_lab.web.deps import CsrfError, LoginRequiredError
from crypto_lab.web.local_access import LocalPaperBoundary
from crypto_lab.web.middleware import SecurityHeadersMiddleware
from crypto_lab.web.routers import admin_bots, admin_keys, auth, pages, paper, polymarket
from crypto_lab.web.templating import render
from crypto_lab.workers.manager import WorkerManager

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        c = container or Container.build(settings)
        await upgrade_to_head(c.engine)
        async with unit_of_work(c.session_factory) as session:
            await c.bots(session).seed(paper=settings.default_paper_mode)
            account = await session.get(PaperAccount, 1)
            if account is None:
                session.add(
                    PaperAccount(id=1, initial=settings.paper_balance_usdc, trade_limit=settings.paper_trade_limit_usdc)
                )
            else:
                account.trade_limit = settings.paper_trade_limit_usdc
        app.state.container = c
        app.state.local_admin = AdminSession(
            user=AdminUser(id=0, username="local-paper", password_hash=secrets.token_hex(32)),
            csrf_token=secrets.token_hex(32),
        )
        manager = WorkerManager(c)
        if settings.autostart_workers:
            manager.start()
        try:
            yield
        finally:
            await manager.stop()
            await c.dispose()

    app = FastAPI(title=settings.app_name, lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.cookie_secure)
    if settings.local_paper_access:
        app.add_middleware(LocalPaperBoundary)
    app.mount("/static", StaticFiles(directory=PACKAGE_ROOT / "web" / "static"), name="static")
    for module in (pages, auth, admin_keys, admin_bots, polymarket, paper):
        app.include_router(module.router)

    @app.exception_handler(LoginRequiredError)
    async def _login_required(request: Request, exc: LoginRequiredError) -> Response:
        return RedirectResponse(f"/login?next={quote(exc.next_path, safe='/')}", status_code=303)

    @app.exception_handler(CsrfError)
    async def _csrf(request: Request, exc: CsrfError) -> Response:
        return render(
            request,
            "error.html",
            {
                "title": "Form expired",
                "message": "The security token was missing or out of date. Go back, reload the page and try again.",
            },
            status_code=403,
        )

    @app.exception_handler(NotFoundError)
    async def _not_found(request: Request, exc: NotFoundError) -> Response:
        return render(request, "error.html", {"title": "Not found", "message": str(exc)}, status_code=404)

    @app.exception_handler(DomainError)
    async def _domain(request: Request, exc: DomainError) -> Response:
        return render(request, "error.html", {"title": "Request refused", "message": str(exc)}, status_code=422)

    return app
