"""Password hashing (scrypt), TOTP, signed tokens, CSRF helpers and client IP."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
import time
from typing import Any
from urllib.parse import quote

from fastapi import Request

from . import config

# scrypt parameters: N=2^15, r=8, p=1 (≈32 MiB, ~0.1 s) — OWASP-recommended minimum class.
SCRYPT_N = 2**15
SCRYPT_R = 8
SCRYPT_P = 1
MIN_PASSWORD_LENGTH = 12


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str, *, n: int = SCRYPT_N) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=SCRYPT_R, p=SCRYPT_P,
                            maxmem=256 * 1024 * 1024, dklen=32)
    return f"scrypt${n}${SCRYPT_R}${SCRYPT_P}${_b64e(salt)}${_b64e(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        candidate = hashlib.scrypt(password.encode("utf-8"), salt=_b64d(salt), n=int(n), r=int(r), p=int(p),
                                   maxmem=256 * 1024 * 1024, dklen=32)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate, _b64d(digest))


_DUMMY_HASH: str | None = None


def burn_password_time(password: str) -> None:
    """Spend the same time as a real verification (unknown usernames)."""
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("dummy-password-for-timing")
    verify_password(password, _DUMMY_HASH)


# ---------------------------------------------------------------- TOTP (RFC 6238)

def new_totp_secret() -> str:
    return base64.b32encode(os.urandom(20)).decode("ascii").rstrip("=")


def totp_code(secret_b32: str, step: int, digits: int = 6) -> str:
    key = base64.b32decode(secret_b32 + "=" * (-len(secret_b32) % 8), casefold=True)
    mac = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    number = (struct.unpack(">I", mac[offset:offset + 4])[0] & 0x7FFFFFFF) % (10**digits)
    return str(number).zfill(digits)


def totp_verify(secret_b32: str, code: str, *, last_step: int = 0, now: float | None = None,
                window: int = 1) -> int | None:
    """Return the matched time step (to store against replay) or None."""
    code = (code or "").strip().replace(" ", "")
    if not code.isdigit() or len(code) != 6:
        return None
    current = int((now if now is not None else time.time()) // 30)
    for step in range(current - window, current + window + 1):
        if step > last_step and hmac.compare_digest(totp_code(secret_b32, step), code):
            return step
    return None


def totp_uri(secret_b32: str, username: str, issuer: str = "Calyx Admin") -> str:
    return (f"otpauth://totp/{quote(issuer)}:{quote(username)}?secret={secret_b32}"
            f"&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30")


# ---------------------------------------------------------------- signed tokens

def sign(payload: dict[str, Any], purpose: str, *, key: bytes | None = None) -> str:
    body = _b64e(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    mac = hmac.new(key or config.store_secret(), f"{purpose}.{body}".encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64e(mac)}"


def unsign(token: str, purpose: str, *, key: bytes | None = None, now: float | None = None) -> dict[str, Any] | None:
    try:
        body, mac = token.split(".", 1)
        expected = hmac.new(key or config.store_secret(), f"{purpose}.{body}".encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64d(mac)):
            return None
        payload = json.loads(_b64d(body))
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    exp = payload.get("exp")
    if exp is not None and float(exp) < (now if now is not None else time.time()):
        return None
    return payload


def hmac_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def random_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- requests

def client_ip(request: Request) -> str:
    """Client address; trusts X-Forwarded-For only from a configured local proxy (Caddy)."""
    host = request.client.host if request.client else "unknown"
    if host in config.trusted_proxies():
        forwarded = request.headers.get("x-forwarded-for", "")
        parts = [part.strip() for part in forwarded.split(",") if part.strip()]
        if parts:
            return parts[-1][:64]
    return host[:64]


def is_https(request: Request) -> bool:
    if request.url.scheme == "https":
        return True
    host = request.client.host if request.client else ""
    return host in config.trusted_proxies() and request.headers.get("x-forwarded-proto", "").lower() == "https"


def cookie_secure(request: Request) -> bool:
    mode = config.cookie_secure_mode()
    if mode in {"1", "true", "yes", "on"}:
        return True
    if mode in {"0", "false", "no", "off"}:
        return False
    return is_https(request)


CSRF_COOKIE = "calyx_csrf"


def csrf_token_for(request: Request) -> tuple[str, bool]:
    """Return the browser's CSRF token (double-submit), creating one if needed."""
    existing = request.cookies.get(CSRF_COOKIE, "")
    if existing and unsign(existing, "csrf"):
        return existing, False
    return sign({"n": secrets.token_hex(16)}, "csrf"), True


def csrf_valid(request: Request, submitted: str | None) -> bool:
    cookie = request.cookies.get(CSRF_COOKIE, "")
    if not cookie or not submitted or not unsign(cookie, "csrf"):
        return False
    return hmac.compare_digest(cookie, submitted)
