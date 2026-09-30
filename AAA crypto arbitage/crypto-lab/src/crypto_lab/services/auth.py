"""Admin authentication: password + optional TOTP, lockout, server-side sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from crypto_lab.config import Settings
from crypto_lab.domain.errors import AccountLockedError, AuthenticationError, ValidationError
from crypto_lab.infrastructure.db.base import utcnow
from crypto_lab.infrastructure.db.models import AdminSession, AdminUser
from crypto_lab.infrastructure.db.repositories import AdminUserRepository, SessionRepository
from crypto_lab.security import tokens, totp
from crypto_lab.security.crypto import AesGcmCipher, EncryptedBlob
from crypto_lab.security.passwords import PasswordHasher
from crypto_lab.services.audit import Actor, AuditService

GENERIC_LOGIN_ERROR = "Invalid username, password or code."


@dataclass(frozen=True, slots=True)
class IssuedSession:
    token: str  # raw cookie value; only its digest is stored
    session: AdminSession


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings, hasher: PasswordHasher, cipher: AesGcmCipher) -> None:
        self._users = AdminUserRepository(session)
        self._sessions = SessionRepository(session)
        self._audit = AuditService(session)
        self._settings = settings
        self._hasher = hasher
        self._cipher = cipher

    # --- users -----------------------------------------------------------------------------------------------
    async def create_admin(self, username: str, password: str) -> AdminUser:
        username = username.strip()
        if not (3 <= len(username) <= 64) or not username.replace("_", "").replace("-", "").isalnum():
            raise ValidationError("Username must be 3-64 letters, digits, '-' or '_'.")
        if await self._users.by_username(username):
            raise ValidationError("That username already exists.")
        try:
            password_hash = self._hasher.hash(password)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        user = await self._users.add(AdminUser(username=username, password_hash=password_hash))
        await self._audit.record(Actor("cli"), "admin.created", username)
        return user

    async def has_admin(self) -> bool:
        return await self._users.count() > 0

    # --- login / sessions --------------------------------------------------------------------------------------
    async def login(self, username: str, password: str, code: str, ip: str, user_agent: str) -> IssuedSession:
        now = utcnow()
        user = await self._users.by_username(username.strip())
        password_ok = self._hasher.verify(user.password_hash if user else None, password)
        actor = Actor(username.strip()[:64] or "?", ip)

        if user is None:
            await self._audit.record(actor, "login.failed", reason="unknown_user")
            raise AuthenticationError(GENERIC_LOGIN_ERROR)
        if user.locked_until and user.locked_until > now:
            await self._audit.record(actor, "login.locked")
            raise AccountLockedError("Too many failed attempts. Try again later.")

        code_ok = True
        if user.totp_enabled:
            code_ok = totp.verify(self.decrypt_totp(user), code)
        if not (password_ok and code_ok):
            user.failed_logins += 1
            if user.failed_logins >= self._settings.login_max_failures:
                user.locked_until = now + timedelta(minutes=self._settings.login_lockout_minutes)
                user.failed_logins = 0
            await self._audit.record(actor, "login.failed", reason="bad_credentials")
            raise AuthenticationError(GENERIC_LOGIN_ERROR)

        if self._hasher.needs_rehash(user.password_hash):
            user.password_hash = self._hasher.hash(password)
        user.failed_logins = 0
        user.locked_until = None
        user.last_login_at = now
        await self._sessions.delete_expired(now)

        raw = tokens.new_token()
        admin_session = await self._sessions.add(
            AdminSession(
                user_id=user.id,
                token_digest=tokens.token_digest(raw),
                csrf_token=tokens.new_token(24),
                expires_at=now + timedelta(minutes=self._settings.session_ttl_minutes),
                ip=ip[:64],
                user_agent=user_agent[:255],
            )
        )
        await self._audit.record(actor, "login.succeeded")
        return IssuedSession(token=raw, session=admin_session)

    async def resolve(self, raw_token: str | None) -> AdminSession | None:
        if not raw_token:
            return None
        admin_session = await self._sessions.by_digest(tokens.token_digest(raw_token))
        if admin_session is None or admin_session.expires_at <= utcnow():
            return None
        return admin_session

    async def logout(self, raw_token: str | None, actor: Actor) -> None:
        if raw_token:
            await self._sessions.delete_by_digest(tokens.token_digest(raw_token))
            await self._audit.record(actor, "logout")

    # --- two-factor --------------------------------------------------------------------------------------------
    def _totp_aad(self, user: AdminUser) -> bytes:
        return f"totp:{user.id}".encode()

    def decrypt_totp(self, user: AdminUser) -> str:
        if user.totp_nonce is None or user.totp_ciphertext is None:
            raise ValidationError("Two-factor authentication is not enabled for this user.")
        blob = EncryptedBlob(user.totp_nonce, user.totp_ciphertext)
        return self._cipher.decrypt(blob, self._totp_aad(user)).decode("ascii")

    async def enable_totp(self, user: AdminUser, secret: str, code: str, actor: Actor) -> None:
        if not totp.verify(secret, code):
            raise ValidationError("That code does not match. Check your authenticator's clock and try again.")
        blob = self._cipher.encrypt(secret.encode("ascii"), self._totp_aad(user))
        user.totp_nonce, user.totp_ciphertext = blob.nonce, blob.ciphertext
        await self._audit.record(actor, "totp.enabled", user.username)

    def verify_totp(self, user: AdminUser, code: str) -> bool:
        return user.totp_enabled and totp.verify(self.decrypt_totp(user), code)
