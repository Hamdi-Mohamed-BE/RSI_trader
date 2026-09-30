"""Admin accounts, login (scrypt + optional TOTP), sessions and login rate limiting."""

from __future__ import annotations

import re
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import Request

from . import security
from .db import audit, iso, parse_iso, transaction, utcnow

SESSION_COOKIE = "calyx_admin"
SESSION_HOURS = 12
MAX_FAILURES = 5
FAILURE_WINDOW = timedelta(minutes=15)
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,40}$")


class AuthError(ValueError):
    pass


@dataclass
class AdminSession:
    admin: sqlite3.Row
    session: sqlite3.Row

    @property
    def username(self) -> str:
        return str(self.admin["username"])

    @property
    def actor(self) -> str:
        return f"admin:{self.username}"

    @property
    def csrf(self) -> str:
        return str(self.session["csrf"])


def create_admin(conn: sqlite3.Connection, username: str, password: str) -> int:
    if not USERNAME_RE.match(username or ""):
        raise AuthError("Username: 3-40 letters, digits, dot, dash or underscore.")
    if conn.execute("SELECT 1 FROM admins WHERE username = ?", (username,)).fetchone():
        raise AuthError("That admin user already exists.")
    password_hash = security.hash_password(password)
    with transaction(conn):
        cursor = conn.execute("INSERT INTO admins(username, password_hash, created_at) VALUES (?,?,?)",
                              (username, password_hash, iso(utcnow())))
        audit(conn, "cli", "admin.create", username)
    return int(cursor.lastrowid)


def set_password(conn: sqlite3.Connection, admin_id: int, password: str, actor: str) -> None:
    password_hash = security.hash_password(password)
    with transaction(conn):
        conn.execute("UPDATE admins SET password_hash = ? WHERE id = ?", (password_hash, admin_id))
        conn.execute("DELETE FROM admin_sessions WHERE admin_id = ?", (admin_id,))
        audit(conn, actor, "admin.password", str(admin_id))


def locked_out(conn: sqlite3.Connection, ip: str, username: str, now: datetime | None = None) -> bool:
    since = iso((now or utcnow()) - FAILURE_WINDOW)
    by_ip = conn.execute("SELECT COUNT(*) FROM login_attempts WHERE ip = ? AND success = 0 AND at >= ?", (ip, since)).fetchone()[0]
    by_user = conn.execute("SELECT COUNT(*) FROM login_attempts WHERE username = ? AND success = 0 AND at >= ?",
                           (username.lower(), since)).fetchone()[0]
    return by_ip >= MAX_FAILURES or by_user >= MAX_FAILURES


def _record_attempt(conn: sqlite3.Connection, ip: str, username: str, success: bool, now: datetime) -> None:
    conn.execute("INSERT INTO login_attempts(ip, username, success, at) VALUES (?,?,?,?)",
                 (ip, username.lower()[:40], 1 if success else 0, iso(now)))
    conn.execute("DELETE FROM login_attempts WHERE at < ?", (iso(now - timedelta(days=30)),))


def login(conn: sqlite3.Connection, username: str, password: str, totp_code: str, *, ip: str, user_agent: str = "",
          now: datetime | None = None) -> str:
    """Return a new session token or raise AuthError (generic message)."""
    now = now or utcnow()
    username = (username or "").strip()
    if locked_out(conn, ip, username, now):
        raise AuthError("Too many failed attempts. Wait 15 minutes and try again.")
    admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
    ok = False
    if admin is None:
        security.burn_password_time(password or "")
    elif security.verify_password(password or "", admin["password_hash"]):
        if admin["totp_enabled"]:
            step = security.totp_verify(admin["totp_secret"], totp_code, last_step=int(admin["totp_last_step"] or 0),
                                        now=now.timestamp())
            if step is not None:
                conn.execute("UPDATE admins SET totp_last_step = ? WHERE id = ?", (step, admin["id"]))
                ok = True
        else:
            ok = True
    _record_attempt(conn, ip, username, ok, now)
    if not ok:
        raise AuthError("Invalid username, password or authentication code.")
    token = security.random_token(32)
    with transaction(conn):
        conn.execute(
            "INSERT INTO admin_sessions(id_hash, admin_id, csrf, created_at, expires_at, ip, user_agent) VALUES (?,?,?,?,?,?,?)",
            (security.token_hash(token), admin["id"], secrets.token_urlsafe(32), iso(now),
             iso(now + timedelta(hours=SESSION_HOURS)), ip[:64], user_agent[:200]),
        )
        conn.execute("UPDATE admins SET last_login_at = ? WHERE id = ?", (iso(now), admin["id"]))
        conn.execute("DELETE FROM admin_sessions WHERE expires_at < ?", (iso(now),))
        audit(conn, f"admin:{username}", "admin.login", ip)
    return token


def current(conn: sqlite3.Connection, request: Request, now: datetime | None = None) -> AdminSession | None:
    token = request.cookies.get(SESSION_COOKIE, "")
    if not token or len(token) > 200:
        return None
    session = conn.execute("SELECT * FROM admin_sessions WHERE id_hash = ?", (security.token_hash(token),)).fetchone()
    if session is None or parse_iso(session["expires_at"]) < (now or utcnow()):
        return None
    admin = conn.execute("SELECT * FROM admins WHERE id = ?", (session["admin_id"],)).fetchone()
    if admin is None:
        return None
    return AdminSession(admin, session)


def logout(conn: sqlite3.Connection, request: Request) -> None:
    token = request.cookies.get(SESSION_COOKIE, "")
    if token:
        conn.execute("DELETE FROM admin_sessions WHERE id_hash = ?", (security.token_hash(token),))


def start_totp_setup(conn: sqlite3.Connection, admin_id: int) -> str:
    secret = security.new_totp_secret()
    conn.execute("UPDATE admins SET totp_secret = ?, totp_enabled = 0 WHERE id = ?", (secret, admin_id))
    return secret


def confirm_totp(conn: sqlite3.Connection, admin_id: int, code: str, actor: str) -> bool:
    admin = conn.execute("SELECT * FROM admins WHERE id = ?", (admin_id,)).fetchone()
    if admin is None or not admin["totp_secret"]:
        return False
    step = security.totp_verify(admin["totp_secret"], code)
    if step is None:
        return False
    with transaction(conn):
        conn.execute("UPDATE admins SET totp_enabled = 1, totp_last_step = ? WHERE id = ?", (step, admin_id))
        audit(conn, actor, "admin.totp_enabled", admin["username"])
    return True


def disable_totp(conn: sqlite3.Connection, admin_id: int, actor: str) -> None:
    with transaction(conn):
        conn.execute("UPDATE admins SET totp_enabled = 0, totp_secret = NULL, totp_last_step = 0 WHERE id = ?", (admin_id,))
        audit(conn, actor, "admin.totp_disabled", str(admin_id))
