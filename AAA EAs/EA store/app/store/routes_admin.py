"""Owner admin panel (/admin): orders, licenses, activation log, transfers, settings, security.

Not linked from the public navigation. Every page requires a session created by
``/admin/login``; every POST requires the session's CSRF token.
"""

from __future__ import annotations

import inspect
import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import Response

from . import admin_auth, licenses, orders, security
from .builds import load_manifest, license_key_fingerprint
from .db import audit, connect, iso, utcnow
from .payments import watcher
from .pricing import format_usd
from .qr import qr_svg
from .settings import NETWORK_LABELS, SPECS, get_all, set_value, validate
from .web import read_form, redirect, render

router = APIRouter(prefix="/admin")
PAGE_SIZE = 50


def _cookie(request: Request, response: Response, token: str | None) -> None:
    if token is None:
        response.delete_cookie(admin_auth.SESSION_COOKIE, path="/admin")
        return
    response.set_cookie(admin_auth.SESSION_COOKIE, token, max_age=admin_auth.SESSION_HOURS * 3600, httponly=True,
                        samesite="strict", secure=security.cookie_secure(request), path="/admin")


def _page(request: Request, name: str, session: admin_auth.AdminSession, context: dict[str, Any], *,
          status_code: int = 200) -> Response:
    base = {"admin": session, "admin_csrf": session.csrf, "nav": name.split("/")[-1].removesuffix(".html"),
            "format_usd": format_usd, "network_labels": NETWORK_LABELS, "flash": request.query_params.get("msg")}
    return render(request, name, base | context, admin=True, status_code=status_code)


def requires_admin(post: bool = False) -> Callable:
    def decorator(handler: Callable) -> Callable:
        @wraps(handler)
        async def wrapper(request: Request, *args: Any, **kwargs: Any) -> Response:
            with connect() as conn:
                session = admin_auth.current(conn, request)
                if session is None:
                    return redirect("/admin/login")
                form: dict[str, str] = {}
                if post:
                    form = await read_form(request)
                    if not form.get("csrf") or not security.hmac_equal(form.get("csrf", ""), session.csrf):
                        return Response("CSRF check failed. Reload the page and try again.", status_code=403)
                return await handler(request, conn, session, form, *args, **kwargs)

        signature = inspect.signature(handler)
        params = list(signature.parameters.values())
        # FastAPI sees only the request and path parameters; conn/session/form are injected here.
        wrapper.__signature__ = signature.replace(parameters=[params[0], *params[4:]])  # type: ignore[attr-defined]
        return wrapper

    return decorator


def _msg(url: str, text: str) -> Response:
    from urllib.parse import quote

    return redirect(f"{url}{'&' if '?' in url else '?'}msg={quote(text)}")


# ------------------------------------------------------------------ login

@router.get("/login", name="admin_login")
async def login_page(request: Request):
    with connect() as conn:
        if admin_auth.current(conn, request):
            return redirect("/admin")
        has_admin = conn.execute("SELECT 1 FROM admins LIMIT 1").fetchone() is not None
    return render(request, "admin/login.html", {"error": None, "has_admin": has_admin}, admin=True)


@router.post("/login", name="admin_login_submit")
async def login_submit(request: Request):
    form = await read_form(request)
    if not security.csrf_valid(request, form.get("csrf")):
        return render(request, "admin/login.html", {"error": "Session expired - please try again.", "has_admin": True},
                      admin=True, status_code=400)
    with connect() as conn:
        try:
            token = admin_auth.login(conn, form.get("username", ""), form.get("password", ""), form.get("totp", ""),
                                     ip=security.client_ip(request), user_agent=request.headers.get("user-agent", ""))
        except admin_auth.AuthError as exc:
            return render(request, "admin/login.html", {"error": str(exc), "has_admin": True}, admin=True, status_code=401)
    response = redirect("/admin")
    _cookie(request, response, token)
    return response


@router.post("/logout", name="admin_logout")
@requires_admin(post=True)
async def logout(request: Request, conn: sqlite3.Connection, session, form):
    admin_auth.logout(conn, request)
    response = redirect("/admin/login")
    _cookie(request, response, None)
    return response


# ------------------------------------------------------------------ dashboard

@router.get("", name="admin_dashboard")
@router.get("/", include_in_schema=False)
@requires_admin()
async def dashboard(request: Request, conn: sqlite3.Connection, session, form):
    orders.expire_orders(conn)
    values = get_all(conn)
    counts = {row["status"]: row["n"] for row in conn.execute("SELECT status, COUNT(*) AS n FROM orders GROUP BY status")}
    revenue = conn.execute("SELECT COALESCE(SUM(amount_cents),0) FROM orders WHERE status='paid'").fetchone()[0]
    manifest = load_manifest()
    warnings = []
    if not values["trc20_address"] and not values["bep20_address"]:
        warnings.append("No deposit address configured: checkout shows 'payments not configured'. Set them in Settings.")
    if not manifest.get("builds"):
        warnings.append("No store builds found. Run: uv run python tools/build_store_eas.py")
    elif manifest.get("license_key_fingerprint") != license_key_fingerprint():
        warnings.append("Store builds were compiled with a different CALYX_LICENSE_SECRET: activation will fail. Rebuild them.")
    missing = [p["label"] for slug, p in manifest.get("products", {}).items()
               if not manifest["builds"].get(p["build_id"], {}).get("compiled")]
    if missing:
        warnings.append(f"Products without a compiled store build: {', '.join(missing)}")
    if values["activation_url"] != manifest.get("activation_url", values["activation_url"]):
        warnings.append("The activation URL differs from the one compiled into the store builds.")
    if not watcher.running:
        warnings.append("The payment watcher is not running (CALYX_STORE_WATCHER=0 or not started): payments are not confirmed automatically.")
    context = {
        "counts": counts,
        "revenue": revenue,
        "licenses_total": conn.execute("SELECT COUNT(*) FROM licenses").fetchone()[0],
        "licenses_revoked": conn.execute("SELECT COUNT(*) FROM licenses WHERE status='revoked'").fetchone()[0],
        "checks_24h": conn.execute("SELECT COUNT(*), COALESCE(SUM(allowed),0) FROM license_checks WHERE at >= ?",
                                   (iso(utcnow() - timedelta(days=1)),)).fetchone(),
        "unmatched": conn.execute("SELECT COUNT(*) FROM chain_transfers WHERE status='unmatched'").fetchone()[0],
        "recent_orders": list(conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 8")),
        "warnings": warnings,
        "watcher": watcher,
        "manifest": manifest,
        "values": values,
    }
    return _page(request, "admin/dashboard.html", session, context)


# ------------------------------------------------------------------ orders

@router.get("/orders", name="admin_orders")
@requires_admin()
async def orders_list(request: Request, conn: sqlite3.Connection, session, form):
    orders.expire_orders(conn)
    status = request.query_params.get("status", "")
    q = request.query_params.get("q", "").strip()[:80]
    sql, params = "SELECT * FROM orders WHERE 1=1", []
    if status in {"pending", "paid", "expired", "cancelled"}:
        sql += " AND status = ?"
        params.append(status)
    if q:
        sql += " AND (public_id LIKE ? OR email LIKE ? OR tx_hash LIKE ?)"
        params += [f"%{q}%"] * 3
    rows = list(conn.execute(sql + f" ORDER BY id DESC LIMIT {PAGE_SIZE}", params))
    return _page(request, "admin/orders.html", session, {"rows": rows, "status": status, "q": q})


@router.get("/orders/{order_id}", name="admin_order")
@requires_admin()
async def order_detail(request: Request, conn: sqlite3.Connection, session, form, order_id: int):
    order = orders.get(conn, order_id)
    if order is None:
        return Response("Order not found", status_code=404)
    order = orders.refresh_status(conn, order)
    context = {
        "order": order,
        "items": orders.items(conn, order_id),
        "licenses": licenses.for_order(conn, order_id),
        "transfers": list(conn.execute("SELECT * FROM chain_transfers WHERE order_id = ? ORDER BY id", (order_id,))),
        "pricing": orders.pricing(order),
        "amount": orders.format_amount(order["amount_cents"]),
        "new_link": None,
    }
    return _page(request, "admin/order_detail.html", session, context)


@router.post("/orders/{order_id}/mark-paid", name="admin_order_mark_paid")
@requires_admin(post=True)
async def order_mark_paid(request: Request, conn: sqlite3.Connection, session, form, order_id: int):
    note = form.get("note", "").strip()
    if len(note) < 5:
        return _msg(f"/admin/orders/{order_id}", "A note of at least 5 characters is required (e.g. tx hash, reason).")
    tx = form.get("tx_hash", "").strip()[:120] or None
    try:
        changed = orders.mark_paid(conn, order_id, paid_by=session.actor, tx_hash=tx, note=note[:1000])
    except LookupError:
        return Response("Order not found", status_code=404)
    return _msg(f"/admin/orders/{order_id}", "Order marked paid; licenses issued." if changed else "Order was already paid.")


@router.post("/orders/{order_id}/cancel", name="admin_order_cancel")
@requires_admin(post=True)
async def order_cancel(request: Request, conn: sqlite3.Connection, session, form, order_id: int):
    try:
        orders.cancel(conn, order_id, session.actor, form.get("note", "")[:500])
    except orders.OrderError as exc:
        return _msg(f"/admin/orders/{order_id}", str(exc))
    return _msg(f"/admin/orders/{order_id}", "Order cancelled.")


@router.post("/orders/{order_id}/new-link", name="admin_order_new_link")
@requires_admin(post=True)
async def order_new_link(request: Request, conn: sqlite3.Connection, session, form, order_id: int):
    try:
        token = orders.regenerate_token(conn, order_id, session.actor)
    except LookupError:
        return Response("Order not found", status_code=404)
    order = orders.get(conn, order_id)
    context = {
        "order": order,
        "items": orders.items(conn, order_id),
        "licenses": licenses.for_order(conn, order_id),
        "transfers": list(conn.execute("SELECT * FROM chain_transfers WHERE order_id = ? ORDER BY id", (order_id,))),
        "pricing": orders.pricing(order),
        "amount": orders.format_amount(order["amount_cents"]),
        "new_link": f"{str(request.base_url).rstrip('/')}/order/{token}",
    }
    return _page(request, "admin/order_detail.html", session, context)


# ------------------------------------------------------------------ licenses

@router.get("/licenses", name="admin_licenses")
@requires_admin()
async def licenses_list(request: Request, conn: sqlite3.Connection, session, form):
    q = request.query_params.get("q", "").strip()[:80]
    status = request.query_params.get("status", "")
    sql = ("SELECT l.*, o.public_id FROM licenses l JOIN orders o ON o.id = l.order_id WHERE 1=1")
    params: list[Any] = []
    if status in {"active", "revoked"}:
        sql += " AND l.status = ?"
        params.append(status)
    if q:
        sql += (" AND (l.license_key LIKE ? OR l.email LIKE ? OR l.product_slug LIKE ? OR l.live_login LIKE ?"
                " OR l.demo_login LIKE ? OR o.public_id LIKE ?)")
        params += [f"%{q}%"] * 6
    rows = list(conn.execute(sql + f" ORDER BY l.id DESC LIMIT {PAGE_SIZE}", params))
    return _page(request, "admin/licenses.html", session, {"rows": rows, "q": q, "status": status})


@router.get("/licenses/{license_id}", name="admin_license")
@requires_admin()
async def license_detail(request: Request, conn: sqlite3.Connection, session, form, license_id: int):
    lic = licenses.get(conn, license_id)
    if lic is None:
        return Response("License not found", status_code=404)
    order = orders.get(conn, lic["order_id"])
    checks = list(conn.execute("SELECT * FROM license_checks WHERE license_id = ? ORDER BY id DESC LIMIT 50", (license_id,)))
    product = load_manifest().get("products", {}).get(lic["product_slug"], {})
    return _page(request, "admin/license_detail.html", session,
                 {"lic": lic, "order": order, "checks": checks, "product": product})


def _license_action(action: Callable[[], None], license_id: int, done: str) -> Response:
    try:
        action()
    except licenses.LicenseError as exc:
        return _msg(f"/admin/licenses/{license_id}", str(exc))
    return _msg(f"/admin/licenses/{license_id}", done)


@router.post("/licenses/{license_id}/revoke", name="admin_license_revoke")
@requires_admin(post=True)
async def license_revoke(request: Request, conn, session, form, license_id: int):
    return _license_action(lambda: licenses.revoke(conn, license_id, session.actor, form.get("reason", "").strip()),
                           license_id, "License revoked. The EA stops at its next check (at the latest ~24 h, or 72 h grace if offline).")


@router.post("/licenses/{license_id}/unrevoke", name="admin_license_unrevoke")
@requires_admin(post=True)
async def license_unrevoke(request: Request, conn, session, form, license_id: int):
    return _license_action(lambda: licenses.unrevoke(conn, license_id, session.actor), license_id, "License re-activated.")


@router.post("/licenses/{license_id}/reset", name="admin_license_reset")
@requires_admin(post=True)
async def license_reset(request: Request, conn, session, form, license_id: int):
    slot = form.get("slot", "both")
    return _license_action(lambda: licenses.reset_accounts(conn, license_id, session.actor, slot), license_id,
                           "Account binding reset. The next activation binds the new account.")


@router.post("/licenses/{license_id}/accounts", name="admin_license_accounts")
@requires_admin(post=True)
async def license_accounts(request: Request, conn, session, form, license_id: int):
    return _license_action(lambda: licenses.set_accounts(conn, license_id, form.get("live_login"), form.get("demo_login"),
                                                         session.actor), license_id, "Accounts saved.")


@router.post("/licenses/{license_id}/extend", name="admin_license_extend")
@requires_admin(post=True)
async def license_extend(request: Request, conn, session, form, license_id: int):
    try:
        days = int(form.get("days", "0"))
    except ValueError:
        days = 0
    target = form.get("target", "expiry")
    return _license_action(lambda: licenses.extend(conn, license_id, session.actor, days, target=target), license_id,
                           f"Extended {target} by {days} days.")


@router.post("/licenses/{license_id}/expiry", name="admin_license_expiry")
@requires_admin(post=True)
async def license_expiry(request: Request, conn, session, form, license_id: int):
    raw = form.get("expires_on", "").strip()

    def action() -> None:
        if not raw:
            licenses.set_expiry(conn, license_id, session.actor, None)
            return
        try:
            when = datetime.strptime(raw, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        except ValueError as exc:
            raise licenses.LicenseError("Use the date format YYYY-MM-DD, or leave empty for perpetual.") from exc
        licenses.set_expiry(conn, license_id, session.actor, when)

    return _license_action(action, license_id, "Expiry updated." if raw else "License is now perpetual (no expiry).")


# ------------------------------------------------------------------ logs

@router.get("/checks", name="admin_checks")
@requires_admin()
async def checks(request: Request, conn: sqlite3.Connection, session, form):
    only = request.query_params.get("only", "")
    sql = "SELECT c.*, l.label FROM license_checks c LEFT JOIN licenses l ON l.id = c.license_id"
    if only == "denied":
        sql += " WHERE c.allowed = 0"
    rows = list(conn.execute(sql + " ORDER BY c.id DESC LIMIT 200"))
    return _page(request, "admin/checks.html", session, {"rows": rows, "only": only})


@router.get("/transfers", name="admin_transfers")
@requires_admin()
async def transfers(request: Request, conn: sqlite3.Connection, session, form):
    rows = list(conn.execute(
        "SELECT t.*, o.public_id FROM chain_transfers t LEFT JOIN orders o ON o.id = t.order_id ORDER BY t.id DESC LIMIT 200"))
    return _page(request, "admin/transfers.html", session, {"rows": rows, "watcher": watcher})


@router.get("/audit", name="admin_audit")
@requires_admin()
async def audit_log(request: Request, conn: sqlite3.Connection, session, form):
    rows = list(conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 300"))
    return _page(request, "admin/audit.html", session, {"rows": rows})


# ------------------------------------------------------------------ settings

@router.get("/settings", name="admin_settings")
@requires_admin()
async def settings_page(request: Request, conn: sqlite3.Connection, session, form):
    return _page(request, "admin/settings.html", session,
                 {"specs": [s for s in SPECS if not s.internal], "values": get_all(conn), "errors": [], "form": {}})


@router.post("/settings", name="admin_settings_save")
@requires_admin(post=True)
async def settings_save(request: Request, conn: sqlite3.Connection, session, form):
    specs = [s for s in SPECS if not s.internal]
    cleaned: dict[str, Any] = {}
    errors: list[str] = []
    current = get_all(conn)
    for spec in specs:
        if spec.kind == "secret" and form.get(spec.key, "") == "" and form.get(f"{spec.key}__clear") != "1":
            continue  # keep the stored secret unless explicitly cleared or replaced
        try:
            cleaned[spec.key] = validate(spec.key, form.get(spec.key, ""))
        except ValueError as exc:
            errors.append(str(exc))
    if errors:
        return _page(request, "admin/settings.html", session,
                     {"specs": specs, "values": current | {k: form.get(k, "") for k in cleaned}, "errors": errors,
                      "form": form}, status_code=422)
    changed = [key for key, value in cleaned.items() if str(current.get(key)) != str(value)]
    for key in changed:
        set_value(conn, key, cleaned[key])
    if "bsc_rpc_url" in changed or "bep20_address" in changed:
        set_value(conn, "bsc_cursor", 0)
    audit(conn, session.actor, "settings.update", ",".join(changed))
    return _msg("/admin/settings", f"Saved ({len(changed)} changed).")


# ------------------------------------------------------------------ security (password / TOTP)

@router.get("/security", name="admin_security")
@requires_admin()
async def security_page(request: Request, conn: sqlite3.Connection, session, form):
    admin = session.admin
    setup_qr = setup_uri = None
    if admin["totp_secret"] and not admin["totp_enabled"]:
        setup_uri = security.totp_uri(admin["totp_secret"], admin["username"])
        setup_qr = qr_svg(setup_uri, title="Authenticator setup")
    return _page(request, "admin/security.html", session, {"setup_qr": setup_qr, "setup_uri": setup_uri,
                                                          "secret": admin["totp_secret"] if setup_uri else None})


@router.post("/security/totp/start", name="admin_totp_start")
@requires_admin(post=True)
async def totp_start(request: Request, conn, session, form):
    admin_auth.start_totp_setup(conn, session.admin["id"])
    return redirect("/admin/security")


@router.post("/security/totp/confirm", name="admin_totp_confirm")
@requires_admin(post=True)
async def totp_confirm(request: Request, conn, session, form):
    ok = admin_auth.confirm_totp(conn, session.admin["id"], form.get("code", ""), session.actor)
    return _msg("/admin/security", "Two-factor authentication enabled." if ok else "Code not accepted - try again.")


@router.post("/security/totp/disable", name="admin_totp_disable")
@requires_admin(post=True)
async def totp_disable(request: Request, conn, session, form):
    if not security.verify_password(form.get("password", ""), session.admin["password_hash"]):
        return _msg("/admin/security", "Password incorrect.")
    admin_auth.disable_totp(conn, session.admin["id"], session.actor)
    return _msg("/admin/security", "Two-factor authentication disabled.")


@router.post("/security/password", name="admin_password")
@requires_admin(post=True)
async def change_password(request: Request, conn, session, form):
    if not security.verify_password(form.get("current", ""), session.admin["password_hash"]):
        return _msg("/admin/security", "Current password incorrect.")
    if form.get("new", "") != form.get("confirm", ""):
        return _msg("/admin/security", "New passwords do not match.")
    try:
        admin_auth.set_password(conn, session.admin["id"], form.get("new", ""), session.actor)
    except ValueError as exc:
        return _msg("/admin/security", str(exc))
    response = redirect("/admin/login")
    _cookie(request, response, None)
    return response
