"""Public store routes: cart, checkout, order page, downloads, license check, how-it-works."""

from __future__ import annotations

import json
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from app.prop_sim.ratelimit import SlidingWindowLimiter

from . import cart, config, downloads, licenses, orders, security
from .db import connect, parse_iso, utcnow
from .deliverables import product_by_slug, sellable_products
from .pricing import PACK_RULE_TEXT, PACK_SIZE, format_usd, package_sale_cents
from .qr import qr_svg
from .settings import NETWORK_LABELS, NETWORKS, USDT_CONTRACTS, activation_origin, enabled_networks, get_all
from .web import read_form, redirect, render, same_origin

router = APIRouter()
checkout_limiter = SlidingWindowLimiter(limit=8, window_seconds=600)
status_limiter = SlidingWindowLimiter(limit=120, window_seconds=60)
license_limiter = SlidingWindowLimiter(limit=30, window_seconds=60)
account_limiter = SlidingWindowLimiter(limit=20, window_seconds=600)


def demo_mode() -> bool:
    return (config.env("CALYX_STORE_DEMO", "0") or "0") in {"1", "true", "yes"}


def _safe_next(value: str) -> str:
    return value if value.startswith("/") and not value.startswith("//") and len(value) < 300 else "/cart"


# ------------------------------------------------------------------ cart

@router.get("/cart", name="store_cart")
async def cart_page(request: Request):
    slugs = cart.read(request)
    products = cart.products_for(slugs)
    quote = cart.quote_for(slugs)
    free = {line.slug for line in quote.lines if line.free}
    context = {
        "products": products,
        "quote": quote,
        "free_slugs": free,
        "pack_rule": PACK_RULE_TEXT,
        "pack_size": PACK_SIZE,
        "all_count": len(sellable_products()),
        "package_price": package_sale_cents(),
        "format_usd": format_usd,
    }
    return render(request, "store/cart.html", context, active="cart")


@router.post("/cart/add", name="store_cart_add")
async def cart_add(request: Request):
    form = await read_form(request)
    if not same_origin(request):
        return Response("Cross-site request refused.", status_code=403)
    slug = form.get("slug", "")
    slugs = cart.read(request)
    if product_by_slug(slug) and slug not in slugs:
        slugs.append(slug)
    response = redirect(_safe_next(form.get("next", "/cart")))
    cart.write(request, response, slugs)
    return response


@router.post("/cart/add-all", name="store_cart_add_all")
async def cart_add_all(request: Request):
    await read_form(request)
    if not same_origin(request):
        return Response("Cross-site request refused.", status_code=403)
    response = redirect("/cart")
    cart.write(request, response, [product.slug for product in sellable_products()])
    return response


@router.post("/cart/remove", name="store_cart_remove")
async def cart_remove(request: Request):
    form = await read_form(request)
    if not same_origin(request):
        return Response("Cross-site request refused.", status_code=403)
    response = redirect("/cart")
    cart.write(request, response, [slug for slug in cart.read(request) if slug != form.get("slug")])
    return response


@router.post("/cart/clear", name="store_cart_clear")
async def cart_clear(request: Request):
    await read_form(request)
    if not same_origin(request):
        return Response("Cross-site request refused.", status_code=403)
    response = redirect("/cart")
    cart.write(request, response, [])
    return response


# ------------------------------------------------------------------ checkout

def _checkout_context(request: Request, values: dict, **extra) -> dict:
    slugs = cart.read(request)
    return {
        "quote": cart.quote_for(slugs),
        "products": cart.products_for(slugs),
        "networks": enabled_networks(values),
        "network_labels": NETWORK_LABELS,
        "format_usd": format_usd,
        "pack_rule": PACK_RULE_TEXT,
        "expiry_minutes": values["order_expiry_minutes"],
        "demo_mode": demo_mode(),
        "form": {},
        "error": None,
    } | extra


@router.get("/checkout", name="store_checkout")
async def checkout_page(request: Request):
    with connect() as conn:
        values = get_all(conn)
    if not cart.read(request):
        return redirect("/cart")
    return render(request, "store/checkout.html", _checkout_context(request, values), active="cart")


@router.post("/checkout", name="store_checkout_submit")
async def checkout_submit(request: Request):
    form = await read_form(request)
    if not security.csrf_valid(request, form.get("csrf")):
        return Response("Your session expired. Go back, reload the page and try again.", status_code=400)
    ip = security.client_ip(request)
    with connect() as conn:
        values = get_all(conn)
        slugs = cart.read(request)
        if not slugs:
            return redirect("/cart")
        error = None
        if form.get("accept") != "yes":
            error = "Please confirm the license terms and the risk disclosure."
        elif not checkout_limiter.allow(ip):
            error = "Too many checkouts from your connection. Please wait a few minutes."
        if error is None:
            try:
                created = orders.create_order(
                    conn, cart.quote_for(slugs), email=form.get("email", ""), network=form.get("network", ""),
                    values=values, live_login=form.get("live_login"), demo_login=form.get("demo_login"), ip=ip,
                )
            except orders.OrderError as exc:
                error = str(exc)
        if error is not None:
            context = _checkout_context(request, values, form=form, error=error)
            return render(request, "store/checkout.html", context, active="cart", status_code=422)
    response = redirect(f"/order/{created.token}")
    cart.write(request, response, [])
    return response


# ------------------------------------------------------------------ order page

def _order_context(conn, order, token: str) -> dict:
    values = get_all(conn)
    order = orders.refresh_status(conn, order)
    now = utcnow()
    lic_rows = licenses.for_order(conn, order["id"]) if order["status"] == "paid" else []
    from .builds import product_build

    license_views = []
    for lic in lic_rows:
        build = product_build(lic["product_slug"])
        available = bool(build and build["build"].get("compiled"))
        license_views.append({
            "row": lic,
            "download_url": f"/download/{downloads.make_token(lic['id'], order['id'])}" if available and lic["status"] == "active" else None,
            "product": product_by_slug(lic["product_slug"]),
        })
    expires = parse_iso(order["expires_at"])
    return {
        "order": order,
        "token": token,
        "items": orders.items(conn, order["id"]),
        "pricing": orders.pricing(order),
        "amount": orders.format_amount(order["amount_cents"]),
        "network_label": NETWORK_LABELS.get(order["network"], order["network"]),
        "contract": USDT_CONTRACTS.get(order["network"], ""),
        "qr": qr_svg(order["deposit_address"], title=f"{order['network']} deposit address") if order["status"] == "pending" else "",
        "seconds_left": max(0, int((expires - now).total_seconds())) if expires else 0,
        "required_confirmations": values[f"{order['network'].lower()}_confirmations"],
        "licenses": license_views,
        "format_usd": format_usd,
        "pack_rule": PACK_RULE_TEXT,
        "activation_origin": activation_origin(values),
        "late_minutes": values["late_payment_minutes"],
        "demo_mode": demo_mode(),
        "flash": None,
    }


@router.get("/order/{token}", name="store_order")
async def order_page(request: Request, token: str):
    with connect() as conn:
        order = orders.get_by_token(conn, token)
        if order is None:
            return render(request, "store/message.html", {"title": "Order not found",
                          "message": "This order link is not valid. Check that you copied the complete link, or contact support."},
                          status_code=404)
        context = _order_context(conn, order, token)
        flash = request.query_params.get("saved")
        context["flash"] = "Account numbers saved." if flash == "1" else None
    response = render(request, "store/order.html", context)
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@router.get("/order/{token}/status", name="store_order_status")
async def order_status(request: Request, token: str):
    if not status_limiter.allow(security.client_ip(request)):
        return JSONResponse({"detail": "slow down"}, status_code=429)
    with connect() as conn:
        order = orders.get_by_token(conn, token)
        if order is None:
            return JSONResponse({"detail": "not found"}, status_code=404)
        order = orders.refresh_status(conn, order)
        values = get_all(conn)
    expires = parse_iso(order["expires_at"])
    return JSONResponse({
        "status": order["status"],
        "confirmations": order["confirmations"],
        "required": values[f"{order['network'].lower()}_confirmations"],
        "detected": bool(order["tx_hash"]),
        "seconds_left": max(0, int((expires - utcnow()).total_seconds())),
    }, headers={"Cache-Control": "no-store"})


@router.post("/order/{token}/accounts", name="store_order_accounts")
async def order_accounts(request: Request, token: str):
    form = await read_form(request)
    if not security.csrf_valid(request, form.get("csrf")):
        return Response("Your session expired. Reload the order page and try again.", status_code=400)
    if not account_limiter.allow(security.client_ip(request)):
        return Response("Too many changes. Please wait a few minutes.", status_code=429)
    with connect() as conn:
        order = orders.get_by_token(conn, token)
        if order is None or order["status"] != "paid":
            return Response("Order not found or not paid.", status_code=404)
        try:
            license_id = int(form.get("license_id", "0"))
        except ValueError:
            license_id = 0
        lic = licenses.get(conn, license_id)
        if lic is None or lic["order_id"] != order["id"]:
            return Response("License not found.", status_code=404)
        try:
            licenses.set_accounts(conn, license_id, form.get("live_login"), form.get("demo_login"), actor="buyer")
        except licenses.LicenseError as exc:
            context = _order_context(conn, order, token)
            context["flash"] = str(exc)
            return render(request, "store/order.html", context, status_code=422)
    return redirect(f"/order/{token}?saved=1#licenses")


# ------------------------------------------------------------------ downloads

@router.get("/download/{token}", name="store_download")
async def download(request: Request, token: str):
    payload = downloads.read_token(token)
    if payload is None:
        return render(request, "store/message.html", {"title": "Download link expired",
                      "message": "Download links are valid for two hours. Open your order page again to get a fresh link."},
                      status_code=410)
    with connect() as conn:
        lic = licenses.get(conn, payload["l"])
        order = orders.get(conn, payload["o"])
        if lic is None or order is None or lic["order_id"] != order["id"] or order["status"] != "paid":
            return Response("Not found.", status_code=404)
        if lic["status"] != "active":
            return Response("This license is not active.", status_code=403)
        values = get_all(conn)
    product = product_by_slug(lic["product_slug"])
    try:
        filename, data = downloads.build_zip(lic, order, origin=activation_origin(values),
                                             timeframe=product.timeframe if product else "")
    except LookupError as exc:
        return render(request, "store/message.html", {"title": "Download not ready", "message": str(exc) +
                      " Please contact support; your license is safe."}, status_code=503)
    return Response(data, media_type="application/zip", headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    })


# ------------------------------------------------------------------ license activation API

@router.post("/api/license/check", name="license_check")
async def license_check(request: Request):
    ip = security.client_ip(request)
    if not license_limiter.allow(ip):
        return JSONResponse({"allowed": False, "code": "rate_limited", "message": licenses.MESSAGES["rate_limited"]},
                            status_code=429)
    raw = await request.body()
    if len(raw) > 4096:
        return JSONResponse({"allowed": False, "code": "bad_request", "message": "request too large"}, status_code=413)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JSONResponse({"allowed": False, "code": "bad_request", "message": "invalid JSON"}, status_code=400)
    with connect() as conn:
        status, body = licenses.check(conn, payload, ip=ip)
    return JSONResponse(body, status_code=status, headers={"Cache-Control": "no-store"})


# ------------------------------------------------------------------ how it works

@router.get("/how-it-works", name="store_how_it_works")
async def how_it_works(request: Request):
    video_dir = config.STORE_ROOT / "static" / "video"
    video = video_dir / "calyx-how-it-works.mp4"
    context = {
        "video_available": video.is_file(),
        "video_version": int(video.stat().st_mtime) if video.is_file() else 0,
        "pack_rule": PACK_RULE_TEXT,
        "networks": NETWORKS,
    }
    return render(request, "store/how_it_works.html", context, active="how")
