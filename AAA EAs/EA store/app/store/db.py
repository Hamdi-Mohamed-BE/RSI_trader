"""SQLite storage for orders, licenses, admin users and settings.

One short-lived connection per unit of work; WAL mode lets the payment watcher
thread and web requests share the file. Schema changes are ordered migrations
recorded in ``schema_version``.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from . import config

MIGRATIONS: list[str] = [
    # 1 — initial schema
    """
    CREATE TABLE settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE TABLE admins (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        totp_secret TEXT,
        totp_enabled INTEGER NOT NULL DEFAULT 0,
        totp_last_step INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        last_login_at TEXT
    );
    CREATE TABLE admin_sessions (
        id_hash TEXT PRIMARY KEY,
        admin_id INTEGER NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
        csrf TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        ip TEXT,
        user_agent TEXT
    );
    CREATE TABLE login_attempts (
        id INTEGER PRIMARY KEY,
        ip TEXT NOT NULL,
        username TEXT NOT NULL,
        success INTEGER NOT NULL,
        at TEXT NOT NULL
    );
    CREATE INDEX login_attempts_at ON login_attempts(at);
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY,
        public_id TEXT NOT NULL UNIQUE,
        token_hash TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL,
        network TEXT NOT NULL,
        deposit_address TEXT NOT NULL,
        subtotal_cents INTEGER NOT NULL,
        discount_cents INTEGER NOT NULL,
        base_cents INTEGER NOT NULL,
        offset_cents INTEGER NOT NULL,
        amount_cents INTEGER NOT NULL,
        amount_units TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        paid_at TEXT,
        paid_by TEXT,
        tx_hash TEXT,
        tx_from TEXT,
        tx_block INTEGER,
        confirmations INTEGER NOT NULL DEFAULT 0,
        paid_units TEXT,
        manual_note TEXT,
        pricing_json TEXT NOT NULL,
        live_login TEXT,
        demo_login TEXT,
        buyer_ip TEXT
    );
    CREATE INDEX orders_status ON orders(status, expires_at);
    CREATE TABLE order_items (
        id INTEGER PRIMARY KEY,
        order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
        position INTEGER NOT NULL,
        product_slug TEXT NOT NULL,
        label TEXT NOT NULL,
        list_cents INTEGER NOT NULL,
        sale_cents INTEGER NOT NULL,
        charged_cents INTEGER NOT NULL,
        free INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE licenses (
        id INTEGER PRIMARY KEY,
        license_key TEXT NOT NULL UNIQUE,
        order_id INTEGER NOT NULL REFERENCES orders(id),
        order_item_id INTEGER REFERENCES order_items(id),
        product_slug TEXT NOT NULL,
        label TEXT NOT NULL,
        email TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        live_login TEXT,
        live_server TEXT,
        demo_login TEXT,
        demo_server TEXT,
        activations INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        expires_at TEXT,
        updates_until TEXT,
        revoked_at TEXT,
        revoke_reason TEXT,
        last_check_at TEXT,
        last_check_result TEXT,
        last_check_ip TEXT
    );
    CREATE INDEX licenses_order ON licenses(order_id);
    CREATE TABLE license_checks (
        id INTEGER PRIMARY KEY,
        license_id INTEGER REFERENCES licenses(id),
        key_hint TEXT,
        login TEXT,
        server TEXT,
        trade_mode TEXT,
        build TEXT,
        product TEXT,
        magic TEXT,
        ip TEXT,
        allowed INTEGER NOT NULL,
        code TEXT NOT NULL,
        message TEXT,
        at TEXT NOT NULL
    );
    CREATE INDEX license_checks_at ON license_checks(at);
    CREATE TABLE chain_transfers (
        id INTEGER PRIMARY KEY,
        network TEXT NOT NULL,
        tx_hash TEXT NOT NULL,
        log_index INTEGER NOT NULL DEFAULT 0,
        from_addr TEXT,
        to_addr TEXT NOT NULL,
        token TEXT NOT NULL,
        amount_units TEXT NOT NULL,
        block_number INTEGER,
        block_time TEXT,
        confirmations INTEGER NOT NULL DEFAULT 0,
        order_id INTEGER REFERENCES orders(id),
        status TEXT NOT NULL,
        note TEXT,
        seen_at TEXT NOT NULL,
        UNIQUE(network, tx_hash, log_index)
    );
    CREATE TABLE audit_log (
        id INTEGER PRIMARY KEY,
        actor TEXT NOT NULL,
        action TEXT NOT NULL,
        target TEXT,
        detail TEXT,
        at TEXT NOT NULL
    );
    """,
]

_init_lock = Lock()
_initialized: set[str] = set()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat() if value else None


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _open(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def init_db(path: Path | None = None) -> None:
    path = path or config.db_path()
    key = str(path.resolve())
    with _init_lock:
        if key in _initialized and path.exists():
            return
        conn = _open(path)
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
            row = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
            current = int(row["v"] or 0)
            for index, script in enumerate(MIGRATIONS, start=1):
                if index <= current:
                    continue
                conn.execute("BEGIN")
                try:
                    for statement in [part.strip() for part in script.split(";") if part.strip()]:
                        conn.execute(statement)
                    conn.execute("INSERT INTO schema_version(version) VALUES (?)", (index,))
                    conn.execute("COMMIT")
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
        finally:
            conn.close()
        _initialized.add(key)


@contextmanager
def connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Autocommit connection; use ``transaction(conn)`` for multi-statement writes."""
    path = path or config.db_path()
    init_db(path)
    conn = _open(path)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except Exception:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def audit(conn: sqlite3.Connection, actor: str, action: str, target: str = "", detail: str = "") -> None:
    conn.execute(
        "INSERT INTO audit_log(actor, action, target, detail, at) VALUES (?,?,?,?,?)",
        (actor, action, target, detail[:2000], iso(utcnow())),
    )
