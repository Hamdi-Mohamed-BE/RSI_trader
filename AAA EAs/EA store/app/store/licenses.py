"""License keys, online activation checks and owner management actions.

A license belongs to one product (catalogue slug) and allows one live and one
demo MT5 account. Accounts can be entered at checkout or later on the order
page; an empty slot is bound automatically on the first successful activation
from an account of that type. The EA reports its build id and magic number,
which must match the product's store build and SET (several products share one
EX5 and differ only by SET, so the magic number identifies the product).
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Any

from .builds import build_secret, load_manifest
from .db import audit, iso, parse_iso, transaction, utcnow

KEY_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
KEY_RE = re.compile(r"^CLX(?:-[2-9A-HJ-NP-Z]{5}){4}$")
UPDATES_MONTHS = 12
NONCE_RE = re.compile(r"^[0-9a-f]{16,64}$")
BUILD_RE = re.compile(r"^[a-z0-9-]{3,120}$")
SAFE_TEXT_RE = re.compile(r'["\\\x00-\x1f]')

MESSAGES = {
    "ok": "license valid",
    "activated": "license activated for this account",
    "unknown_key": "license key not recognised - copy it again from your order page",
    "revoked": "this license has been revoked",
    "expired": "this license has expired",
    "order_unpaid": "the order for this license is not paid",
    "build_unknown": "this EA build is not recognised - download the current version from your order page",
    "product_mismatch": "this license is for a different Calyx EA",
    "magic_mismatch": "the magic number does not match the SET delivered with this license - load the Calyx SET",
    "live_limit": "this license is already activated on a different live account",
    "demo_limit": "this license is already activated on a different demo account",
    "server_mismatch": "this account number is bound to a different broker server",
    "rate_limited": "too many checks - try again later",
}


def generate_key() -> str:
    groups = ["".join(secrets.choice(KEY_ALPHABET) for _ in range(5)) for _ in range(4)]
    return "CLX-" + "-".join(groups)


def key_hint(key: str) -> str:
    return (key[:9] + "…") if key else ""


def _safe(text: str) -> str:
    return SAFE_TEXT_RE.sub(" ", text)[:200]


def issue_for_order(conn: sqlite3.Connection, order: sqlite3.Row, items: list[sqlite3.Row], *,
                    now: datetime | None = None) -> list[str]:
    """Create one license per order item (called inside the order's transaction)."""
    now = now or utcnow()
    existing = {row["order_item_id"] for row in conn.execute("SELECT order_item_id FROM licenses WHERE order_id = ?", (order["id"],))}
    keys: list[str] = []
    updates_until = now + timedelta(days=round(UPDATES_MONTHS * 365 / 12))
    for item in items:
        if item["id"] in existing:
            continue
        for _ in range(10):
            key = generate_key()
            if not conn.execute("SELECT 1 FROM licenses WHERE license_key = ?", (key,)).fetchone():
                break
        conn.execute(
            """INSERT INTO licenses(license_key, order_id, order_item_id, product_slug, label, email, status,
                   live_login, demo_login, created_at, updates_until)
               VALUES (?,?,?,?,?,?,'active',?,?,?,?)""",
            (key, order["id"], item["id"], item["product_slug"], item["label"], order["email"],
             order["live_login"], order["demo_login"], iso(now), iso(updates_until)),
        )
        keys.append(key)
    return keys


def for_order(conn: sqlite3.Connection, order_id: int) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM licenses WHERE order_id = ? ORDER BY id", (order_id,)))


def get(conn: sqlite3.Connection, license_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM licenses WHERE id = ?", (license_id,)).fetchone()


# ------------------------------------------------------------------ activation check

def sign_response(build: str, nonce: str, key: str, login: str, allowed: bool, code: str, ts: int,
                  secret_key: bytes | None = None) -> str:
    message = f"{nonce}|{key}|{login}|{build}|{'1' if allowed else '0'}|{code}|{ts}"
    return hmac.new(build_secret(build, secret_key).encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


class CheckRequest:
    def __init__(self, payload: dict[str, Any]):
        self.key = str(payload.get("key", "")).strip().upper()
        self.login = str(payload.get("login", "")).strip()
        self.server = str(payload.get("server", "")).strip()[:120]
        self.trade_mode = str(payload.get("trade_mode", "")).strip().lower()
        self.product = str(payload.get("product", "")).strip()[:120]
        self.build = str(payload.get("build", "")).strip()
        self.magic = str(payload.get("magic", "")).strip()
        self.nonce = str(payload.get("nonce", "")).strip().lower()

    def validation_error(self) -> str | None:
        if not self.login.isdigit() or not 1 <= len(self.login) <= 20:
            return "login must be a number"
        if self.trade_mode not in {"real", "demo", "contest"}:
            return "trade_mode must be real, demo or contest"
        if not BUILD_RE.match(self.build):
            return "invalid build"
        if not NONCE_RE.match(self.nonce):
            return "invalid nonce"
        if not re.fullmatch(r"-?\d{1,20}", self.magic):
            return "magic must be a number"
        if len(self.key) > 64:
            return "invalid key"
        return None


def _decide(conn: sqlite3.Connection, req: CheckRequest, manifest: dict[str, Any], now: datetime
            ) -> tuple[bool, str, sqlite3.Row | None]:
    lic = conn.execute("SELECT * FROM licenses WHERE license_key = ?", (req.key,)).fetchone() if KEY_RE.match(req.key) else None
    if lic is None:
        return False, "unknown_key", None
    if lic["status"] == "revoked":
        return False, "revoked", lic
    expires = parse_iso(lic["expires_at"])
    if expires is not None and now > expires:
        return False, "expired", lic
    order = conn.execute("SELECT status FROM orders WHERE id = ?", (lic["order_id"],)).fetchone()
    if order is None or order["status"] != "paid":
        return False, "order_unpaid", lic
    build = manifest.get("builds", {}).get(req.build)
    if build is None:
        return False, "build_unknown", lic
    if lic["product_slug"] not in build.get("products", []) or (req.product and req.product != lic["product_slug"]):
        return False, "product_mismatch", lic
    product = manifest.get("products", {}).get(lic["product_slug"])
    if product is None or product.get("magic") is None or str(product["magic"]) != req.magic:
        return False, "magic_mismatch", lic
    slot = "live" if req.trade_mode == "real" else "demo"
    bound_login, bound_server = lic[f"{slot}_login"], lic[f"{slot}_server"]
    if bound_login and bound_login != req.login:
        return False, f"{slot}_limit", lic
    if bound_login and bound_server and req.server and bound_server != req.server:
        return False, "server_mismatch", lic
    if not bound_login or not bound_server:
        conn.execute(
            f"UPDATE licenses SET {slot}_login = ?, {slot}_server = ?, activations = activations + 1 WHERE id = ?",
            (req.login, req.server or None, lic["id"]),
        )
        return True, "activated", lic
    return True, "ok", lic


def check(conn: sqlite3.Connection, payload: dict[str, Any], *, ip: str = "", now: datetime | None = None,
          manifest: dict[str, Any] | None = None, secret_key: bytes | None = None) -> tuple[int, dict[str, Any]]:
    """Evaluate an EA activation request. Returns (HTTP status, JSON body)."""
    now = now or utcnow()
    req = CheckRequest(payload if isinstance(payload, dict) else {})
    error = req.validation_error()
    if error:
        return 400, {"allowed": False, "code": "bad_request", "message": _safe(error)}
    manifest = manifest if manifest is not None else load_manifest()
    with transaction(conn):
        allowed, code, lic = _decide(conn, req, manifest, now)
        message = MESSAGES.get(code, code)
        conn.execute(
            """INSERT INTO license_checks(license_id, key_hint, login, server, trade_mode, build, product, magic, ip,
                   allowed, code, message, at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (lic["id"] if lic else None, key_hint(req.key), req.login, req.server, req.trade_mode, req.build,
             req.product, req.magic, ip[:64], 1 if allowed else 0, code, message, iso(now)),
        )
        if lic is not None:
            conn.execute("UPDATE licenses SET last_check_at = ?, last_check_result = ?, last_check_ip = ? WHERE id = ?",
                         (iso(now), code, ip[:64], lic["id"]))
    ts = int(now.timestamp()) if now else int(time.time())
    body = {
        "allowed": allowed,
        "code": code,
        "message": _safe(message),
        "ts": ts,
        "nonce": req.nonce,
        "sig": sign_response(req.build, req.nonce, req.key, req.login, allowed, code, ts, secret_key),
    }
    return 200, body


# ------------------------------------------------------------------ buyer / owner actions

class LicenseError(ValueError):
    pass


def set_accounts(conn: sqlite3.Connection, license_id: int, live: str | None, demo: str | None, actor: str) -> None:
    """Buyer may set an account while its slot is not activated yet; the owner may always."""
    with transaction(conn):
        lic = get(conn, license_id)
        if lic is None:
            raise LicenseError("License not found.")
        updates: dict[str, Any] = {}
        for slot, value in (("live", live), ("demo", demo)):
            if value is None:
                continue
            value = value.strip()
            if value and not re.fullmatch(r"\d{3,12}", value):
                raise LicenseError(f"{slot.title()} account must be digits only.")
            current = lic[f"{slot}_login"]
            if current and lic[f"{slot}_server"] and current != value and not actor.startswith("admin:"):
                raise LicenseError(f"The {slot} account is already activated. Ask support to reset it.")
            updates[f"{slot}_login"] = value or None
            if current != (value or None):
                updates[f"{slot}_server"] = None
        live_value = updates.get("live_login", lic["live_login"])
        demo_value = updates.get("demo_login", lic["demo_login"])
        if live_value and demo_value and live_value == demo_value:
            raise LicenseError("Live and demo account numbers must differ.")
        if updates:
            assignments = ", ".join(f"{column} = ?" for column in updates)
            conn.execute(f"UPDATE licenses SET {assignments} WHERE id = ?", (*updates.values(), license_id))
            audit(conn, actor, "license.accounts", lic["license_key"][:9], str(updates))


def revoke(conn: sqlite3.Connection, license_id: int, actor: str, reason: str) -> None:
    with transaction(conn):
        lic = get(conn, license_id)
        if lic is None:
            raise LicenseError("License not found.")
        conn.execute("UPDATE licenses SET status = 'revoked', revoked_at = ?, revoke_reason = ? WHERE id = ?",
                     (iso(utcnow()), reason[:500] or None, license_id))
        audit(conn, actor, "license.revoke", lic["license_key"][:9], reason)


def unrevoke(conn: sqlite3.Connection, license_id: int, actor: str) -> None:
    with transaction(conn):
        lic = get(conn, license_id)
        if lic is None:
            raise LicenseError("License not found.")
        conn.execute("UPDATE licenses SET status = 'active', revoked_at = NULL, revoke_reason = NULL WHERE id = ?",
                     (license_id,))
        audit(conn, actor, "license.unrevoke", lic["license_key"][:9])


def reset_accounts(conn: sqlite3.Connection, license_id: int, actor: str, slot: str = "both") -> None:
    if slot not in {"live", "demo", "both"}:
        raise LicenseError("Unknown account slot.")
    columns = ["live", "demo"] if slot == "both" else [slot]
    with transaction(conn):
        lic = get(conn, license_id)
        if lic is None:
            raise LicenseError("License not found.")
        assignments = ", ".join(f"{c}_login = NULL, {c}_server = NULL" for c in columns)
        conn.execute(f"UPDATE licenses SET {assignments} WHERE id = ?", (license_id,))
        audit(conn, actor, "license.reset_accounts", lic["license_key"][:9], slot)


def extend(conn: sqlite3.Connection, license_id: int, actor: str, days: int, *, target: str = "expiry") -> None:
    """Extend ``expiry`` (license use) or ``updates`` by ``days`` from max(now, current date).

    Licenses are perpetual by default (no expiry). Extending the expiry of a
    perpetual license is refused so it never becomes time-limited by accident;
    use :func:`set_expiry` for that.
    """
    if not 1 <= days <= 3650:
        raise LicenseError("Days must be between 1 and 3650.")
    if target not in {"expiry", "updates"}:
        raise LicenseError("Unknown extension target.")
    column = "expires_at" if target == "expiry" else "updates_until"
    with transaction(conn):
        lic = get(conn, license_id)
        if lic is None:
            raise LicenseError("License not found.")
        current = parse_iso(lic[column])
        if target == "expiry" and current is None:
            raise LicenseError("This license has no expiry (perpetual use). Set an expiry date instead.")
        now = utcnow()
        base = current if current and current > now else now
        new_value = base + timedelta(days=days)
        conn.execute(f"UPDATE licenses SET {column} = ? WHERE id = ?", (iso(new_value), license_id))
        audit(conn, actor, f"license.extend_{target}", lic["license_key"][:9], f"+{days}d -> {iso(new_value)}")


def set_expiry(conn: sqlite3.Connection, license_id: int, actor: str, when: datetime | None) -> None:
    """Set an explicit expiry (``None`` = perpetual)."""
    with transaction(conn):
        lic = get(conn, license_id)
        if lic is None:
            raise LicenseError("License not found.")
        conn.execute("UPDATE licenses SET expires_at = ? WHERE id = ?", (iso(when), license_id))
        audit(conn, actor, "license.set_expiry", lic["license_key"][:9], iso(when) or "perpetual")


def expire_now(conn: sqlite3.Connection, license_id: int, actor: str) -> None:
    with transaction(conn):
        lic = get(conn, license_id)
        if lic is None:
            raise LicenseError("License not found.")
        conn.execute("UPDATE licenses SET expires_at = ? WHERE id = ?", (iso(utcnow()), license_id))
        audit(conn, actor, "license.expire", lic["license_key"][:9])
