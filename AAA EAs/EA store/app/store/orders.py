"""Orders: creation with a unique USDT amount, expiry, payment confirmation."""

from __future__ import annotations

import json
import re
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from . import licenses
from .db import audit, iso, parse_iso, transaction, utcnow
from .pricing import Quote
from .security import random_token, token_hash
from .settings import NETWORKS, USDT_DECIMALS, deposit_address

MAX_OFFSET_CENTS = 99  # unique amount = base price + 0.01 … 0.99 USDT
EMAIL_RE = re.compile(r"^[^@\s<>\"']{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,24}$")
LOGIN_RE = re.compile(r"^\d{3,12}$")
_CODE_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


class OrderError(ValueError):
    """Validation problem shown to the buyer."""


@dataclass
class CreatedOrder:
    order_id: int
    public_id: str
    token: str  # secret order-page token; only its hash is stored


def normalize_email(value: str) -> str:
    email = (value or "").strip()
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise OrderError("Enter a valid email address (used for your license record).")
    return email


def normalize_login(value: str | None, label: str) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    if not LOGIN_RE.match(text):
        raise OrderError(f"{label} must be the MT5 account number (digits only).")
    return text


def amount_units(amount_cents: int, network: str) -> str:
    return str(amount_cents * 10 ** (USDT_DECIMALS[network] - 2))


def format_amount(amount_cents: int) -> str:
    return f"{amount_cents // 100}.{amount_cents % 100:02d}"


def _public_id() -> str:
    return "CLX-" + "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))


def reserved_amounts(conn: sqlite3.Connection, now: datetime, late_minutes: int) -> set[int]:
    """Amounts that could still be matched by an incoming transfer (open or within the late window)."""
    cutoff = iso(now - timedelta(minutes=late_minutes + 5))
    rows = conn.execute(
        "SELECT amount_cents FROM orders WHERE status = 'pending' OR (status = 'expired' AND expires_at >= ?)",
        (cutoff,),
    )
    return {int(row["amount_cents"]) for row in rows}


def choose_offset(base_cents: int, reserved: set[int]) -> int:
    for offset in range(1, MAX_OFFSET_CENTS + 1):
        if base_cents + offset not in reserved:
            return offset
    raise OrderError("Too many checkouts are open at this price right now. Please try again in a few minutes.")


def create_order(conn: sqlite3.Connection, quote: Quote, *, email: str, network: str, values: dict[str, Any],
                 live_login: str | None = None, demo_login: str | None = None, ip: str = "",
                 now: datetime | None = None) -> CreatedOrder:
    now = now or utcnow()
    if network not in NETWORKS:
        raise OrderError("Choose TRC20 or BEP20.")
    address = deposit_address(values, network)
    if not address:
        raise OrderError(f"{network} payments are not configured yet.")
    if not quote.lines:
        raise OrderError("Your cart is empty.")
    if quote.total_cents <= 0:
        raise OrderError("Order total must be above zero.")
    email = normalize_email(email)
    live = normalize_login(live_login, "Live account")
    demo = normalize_login(demo_login, "Demo account")
    if live and demo and live == demo:
        raise OrderError("Live and demo account numbers must differ.")
    token = random_token(32)
    expires = now + timedelta(minutes=int(values["order_expiry_minutes"]))
    with transaction(conn):
        reserved = reserved_amounts(conn, now, int(values["late_payment_minutes"]))
        offset = choose_offset(quote.total_cents, reserved)
        amount = quote.total_cents + offset
        for _ in range(5):
            public_id = _public_id()
            if not conn.execute("SELECT 1 FROM orders WHERE public_id = ?", (public_id,)).fetchone():
                break
        cursor = conn.execute(
            """INSERT INTO orders(public_id, token_hash, email, network, deposit_address, subtotal_cents, discount_cents,
                   base_cents, offset_cents, amount_cents, amount_units, status, created_at, expires_at, pricing_json,
                   live_login, demo_login, buyer_ip)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,'pending',?,?,?,?,?,?)""",
            (public_id, token_hash(token), email, network, address, quote.sale_total_cents, quote.discount_cents,
             quote.total_cents, offset, amount, amount_units(amount, network), iso(now), iso(expires),
             json.dumps(quote.as_dict()), live, demo, ip[:64]),
        )
        order_id = int(cursor.lastrowid)
        for position, line in enumerate(quote.lines):
            conn.execute(
                """INSERT INTO order_items(order_id, position, product_slug, label, list_cents, sale_cents, charged_cents, free)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (order_id, position, line.slug, line.label, line.list_cents, line.sale_cents, line.charged_cents,
                 1 if line.free else 0),
            )
        audit(conn, "buyer", "order.create", public_id, f"{network} {format_amount(amount)} USDT, {len(quote.lines)} bots")
    return CreatedOrder(order_id, public_id, token)


def get_by_token(conn: sqlite3.Connection, token: str) -> sqlite3.Row | None:
    if not token or len(token) > 200:
        return None
    return conn.execute("SELECT * FROM orders WHERE token_hash = ?", (token_hash(token),)).fetchone()


def get(conn: sqlite3.Connection, order_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()


def items(conn: sqlite3.Connection, order_id: int) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM order_items WHERE order_id = ? ORDER BY position", (order_id,)))


def expire_orders(conn: sqlite3.Connection, now: datetime | None = None) -> int:
    now = now or utcnow()
    cursor = conn.execute("UPDATE orders SET status = 'expired' WHERE status = 'pending' AND expires_at < ?", (iso(now),))
    return cursor.rowcount


def refresh_status(conn: sqlite3.Connection, order: sqlite3.Row, now: datetime | None = None) -> sqlite3.Row:
    now = now or utcnow()
    if order["status"] == "pending" and parse_iso(order["expires_at"]) < now:
        conn.execute("UPDATE orders SET status = 'expired' WHERE id = ? AND status = 'pending'", (order["id"],))
        return get(conn, order["id"])
    return order


def mark_paid(conn: sqlite3.Connection, order_id: int, *, paid_by: str, tx_hash: str | None = None,
              tx_from: str | None = None, tx_block: int | None = None, confirmations: int = 0,
              paid_units: str | None = None, note: str | None = None, now: datetime | None = None) -> bool:
    """Mark an order paid and issue its licenses. Idempotent: returns False if it was already paid."""
    now = now or utcnow()
    with transaction(conn):
        order = get(conn, order_id)
        if order is None:
            raise LookupError(order_id)
        if order["status"] == "paid":
            return False
        if order["status"] == "cancelled" and not paid_by.startswith("admin:"):
            return False
        conn.execute(
            """UPDATE orders SET status = 'paid', paid_at = ?, paid_by = ?, tx_hash = COALESCE(?, tx_hash),
                   tx_from = COALESCE(?, tx_from), tx_block = COALESCE(?, tx_block), confirmations = ?,
                   paid_units = COALESCE(?, paid_units), manual_note = COALESCE(?, manual_note)
               WHERE id = ?""",
            (iso(now), paid_by, tx_hash, tx_from, tx_block, confirmations, paid_units, note, order_id),
        )
        licenses.issue_for_order(conn, get(conn, order_id), items(conn, order_id), now=now)
        audit(conn, paid_by, "order.paid", order["public_id"], note or (tx_hash or ""))
    return True


def cancel(conn: sqlite3.Connection, order_id: int, actor: str, note: str = "") -> None:
    with transaction(conn):
        order = get(conn, order_id)
        if order is None or order["status"] == "paid":
            raise OrderError("Only unpaid orders can be cancelled.")
        conn.execute("UPDATE orders SET status = 'cancelled', manual_note = ? WHERE id = ?", (note or None, order_id))
        audit(conn, actor, "order.cancel", order["public_id"], note)


def regenerate_token(conn: sqlite3.Connection, order_id: int, actor: str) -> str:
    token = random_token(32)
    with transaction(conn):
        order = get(conn, order_id)
        if order is None:
            raise LookupError(order_id)
        conn.execute("UPDATE orders SET token_hash = ? WHERE id = ?", (token_hash(token), order_id))
        audit(conn, actor, "order.new_link", order["public_id"])
    return token


def record_detection(conn: sqlite3.Connection, order_id: int, tx_hash: str, tx_from: str | None, block: int | None,
                     confirmations: int) -> None:
    conn.execute(
        "UPDATE orders SET tx_hash = ?, tx_from = ?, tx_block = ?, confirmations = ? WHERE id = ? AND status != 'paid'",
        (tx_hash, tx_from, block, confirmations, order_id),
    )


def pricing(order: sqlite3.Row) -> dict[str, Any]:
    return json.loads(order["pricing_json"])
