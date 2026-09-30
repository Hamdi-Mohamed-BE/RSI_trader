"""Shared, persistent paper portfolio. No exchange credentials or execution adapters."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from crypto_lab.infrastructure.db.base import Base, DecimalText, UTCDateTime, utcnow


class PaperAccount(Base):
    __tablename__ = "paper_account"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    initial: Mapped[Decimal] = mapped_column(DecimalText)
    trade_limit: Mapped[Decimal] = mapped_column(DecimalText)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class PaperPosition(Base):
    __tablename__ = "paper_position"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot: Mapped[str] = mapped_column(String(40), index=True)
    key: Mapped[str] = mapped_column(String(250), unique=True)
    symbol: Mapped[str] = mapped_column(String(160))
    venue: Mapped[str] = mapped_column(String(40))
    quantity: Mapped[Decimal] = mapped_column(DecimalText)
    capital: Mapped[Decimal] = mapped_column(DecimalText)
    proceeds: Mapped[Decimal | None] = mapped_column(DecimalText)
    mark: Mapped[Decimal | None] = mapped_column(DecimalText)
    mark_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    opened_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class PaperState(Base):
    __tablename__ = "paper_state"
    key: Mapped[str] = mapped_column(String(250), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class WorkerLease(Base):
    __tablename__ = "worker_lease"
    slug: Mapped[str] = mapped_column(String(40), primary_key=True)
    owner: Mapped[str] = mapped_column(String(64))
    at: Mapped[datetime] = mapped_column(UTCDateTime)


class PaperEvent(Base):
    __tablename__ = "paper_event"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    bot: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(24))
    message: Mapped[str] = mapped_column(Text)
