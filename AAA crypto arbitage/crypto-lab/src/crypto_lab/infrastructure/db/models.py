"""ORM tables for platform state (admin, sessions, credential vault, bots, audit)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crypto_lab.infrastructure.db.base import Base, UTCDateTime, utcnow


class AdminUser(Base):
    __tablename__ = "admin_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    totp_nonce: Mapped[bytes | None] = mapped_column(LargeBinary)
    totp_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    sessions: Mapped[list[AdminSession]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def totp_enabled(self) -> bool:
        return self.totp_ciphertext is not None


class AdminSession(Base):
    __tablename__ = "admin_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("admin_user.id", ondelete="CASCADE"), index=True)
    token_digest: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(255), default="")

    user: Mapped[AdminUser] = relationship(back_populates="sessions", lazy="joined")


class ApiCredential(Base):
    __tablename__ = "api_credential"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider: Mapped[str] = mapped_column(String(40), index=True)
    label: Mapped[str] = mapped_column(String(80))
    environment: Mapped[str] = mapped_column(String(16))
    public_fields: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    secret_nonce: Mapped[bytes] = mapped_column(LargeBinary)
    secret_ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    hint: Mapped[str] = mapped_column(String(16), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    rotated_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_test_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_test_ok: Mapped[bool | None] = mapped_column(Boolean)
    last_test_message: Mapped[str] = mapped_column(String(255), default="")


class Bot(Base):
    __tablename__ = "bot"

    slug: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(8))
    description: Mapped[str] = mapped_column(Text, default="")
    mode: Mapped[str] = mapped_column(String(16), default="off")
    gate_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    kill_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    heartbeat_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_error: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    target: Mapped[str] = mapped_column(String(120), default="")
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    ip: Mapped[str] = mapped_column(String(64), default="")
