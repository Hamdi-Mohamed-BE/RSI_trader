"""Cart kept in a signed cookie (list of product slugs, no server state)."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import Response

from . import pricing, security
from .deliverables import sellable_products

COOKIE = "calyx_cart"
MAX_ITEMS = 60


def read(request: Request) -> list[str]:
    payload = security.unsign(request.cookies.get(COOKIE, ""), "cart") or {}
    slugs = payload.get("s") if isinstance(payload.get("s"), list) else []
    valid = {product.slug for product in sellable_products()}
    return [slug for slug in pricing.dedupe(str(s) for s in slugs) if slug in valid][:MAX_ITEMS]


def write(request: Request, response: Response, slugs: list[str]) -> None:
    slugs = pricing.dedupe(slugs)[:MAX_ITEMS]
    if not slugs:
        response.delete_cookie(COOKIE, path="/")
        return
    response.set_cookie(COOKIE, security.sign({"s": slugs}, "cart"), max_age=30 * 24 * 3600, httponly=True,
                        samesite="lax", secure=security.cookie_secure(request), path="/")


def products_for(slugs: list[str]):
    by_slug = {product.slug: product for product in sellable_products()}
    return [by_slug[slug] for slug in slugs if slug in by_slug]


def quote_for(slugs: list[str]) -> pricing.Quote:
    return pricing.quote(products_for(slugs), [product.slug for product in sellable_products()])
