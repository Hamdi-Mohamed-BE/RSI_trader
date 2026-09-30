"""Hook the store into the existing FastAPI app with minimal changes to app/main.py.

``install(app, templates, base_context)`` registers the routers and the Jinja
helpers used by the shared templates; ``startup()``/``shutdown()`` are called
from the main lifespan to prepare the database and run the payment watcher.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from . import cart, pricing
from .config import store_enabled
from .db import init_db
from .payments import watcher
from .routes_admin import router as admin_router
from .routes_public import router as public_router
from .web import state

log = logging.getLogger("calyx.store")


def _cart_count(request: Request) -> int:
    try:
        return len(cart.read(request))
    except Exception:  # never break a page because of a malformed cookie
        return 0


def install(app: FastAPI, templates: Jinja2Templates, base_context: Callable[[Request, str], dict[str, Any]]) -> None:
    state.templates = templates
    state.base_context = base_context
    env = templates.env
    env.globals["store_price"] = pricing.sale_price
    env.globals["store_cents"] = pricing.sale_cents
    env.globals["store_package_price"] = lambda: pricing.package_sale_cents() / 100
    env.globals["store_discount_percent"] = int(pricing.DISCOUNT_RATE * 100)
    env.globals["store_pack_rule"] = pricing.PACK_RULE_TEXT
    env.globals["store_cart_count"] = _cart_count
    env.globals["store_enabled"] = store_enabled()
    if not store_enabled():
        log.info("store disabled (CALYX_STORE_ENABLED is not set): checkout, license and admin routes not mounted")
        return
    app.include_router(public_router)
    app.include_router(admin_router)


def startup() -> None:
    if not store_enabled():
        return
    try:
        init_db()
    except Exception:  # the catalogue must stay online even if the store database is unavailable
        log.exception("store database initialisation failed")
        return
    watcher.start()


def shutdown() -> None:
    if store_enabled():
        watcher.stop()
