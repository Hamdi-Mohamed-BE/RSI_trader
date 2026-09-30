"""Admin password hashing with Argon2id (one-way; never reversible)."""

from __future__ import annotations

from argon2 import PasswordHasher as _Argon2Hasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

MIN_PASSWORD_LENGTH = 12


class PasswordHasher:
    """Thin wrapper so the rest of the code does not depend on argon2 directly."""

    def __init__(self) -> None:
        self._hasher = _Argon2Hasher()
        # Pre-computed hash used to equalise timing when the username does not exist.
        self._dummy_hash = self._hasher.hash("timing-equaliser-not-a-password")

    def hash(self, password: str) -> str:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
        return self._hasher.hash(password)

    def verify(self, password_hash: str | None, password: str) -> bool:
        """Constant-effort verification; a missing hash still performs a full Argon2 check."""
        try:
            matched = self._hasher.verify(password_hash or self._dummy_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
        return matched and password_hash is not None

    def needs_rehash(self, password_hash: str) -> bool:
        return self._hasher.check_needs_rehash(password_hash)
