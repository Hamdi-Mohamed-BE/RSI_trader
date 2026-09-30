"""Domain-level exceptions. The web layer maps these to HTTP responses without leaking internals."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for expected, user-facing errors."""


class NotFoundError(DomainError):
    """A requested entity does not exist."""


class ValidationError(DomainError):
    """Input failed a domain rule."""


class AuthenticationError(DomainError):
    """Credentials or session are invalid. The message is intentionally generic."""


class AccountLockedError(AuthenticationError):
    """Too many failed logins; the account is temporarily locked."""


class ModeTransitionError(DomainError):
    """A bot mode change was refused by the transition policy."""
