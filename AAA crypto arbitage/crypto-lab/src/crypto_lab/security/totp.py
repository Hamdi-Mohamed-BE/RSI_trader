"""Time-based one-time passwords (RFC 6238) for admin two-factor authentication."""

from __future__ import annotations

import pyotp


def new_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, account: str, issuer: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=account, issuer_name=issuer)


def verify(secret: str, code: str) -> bool:
    code = code.strip().replace(" ", "")
    if not (code.isdigit() and len(code) == 6):
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)
