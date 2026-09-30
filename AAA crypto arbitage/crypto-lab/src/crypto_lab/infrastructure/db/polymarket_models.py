"""ORM tables for Model D (Polymarket scanner, paper ledger, wallet tracker)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from crypto_lab.infrastructure.db.base import Base, DecimalText, UTCDateTime, utcnow

MONEY = DecimalText()


class PmScanRun(Base):
    """One scanner pass: coverage and health, so gaps are visible instead of silently missing."""

    __tablename__ = "pm_scan_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    mode: Mapped[str] = mapped_column(String(16))
    events_scanned: Mapped[int] = mapped_column(Integer, default=0)
    markets_scanned: Mapped[int] = mapped_column(Integer, default=0)
    books_fetched: Mapped[int] = mapped_column(Integer, default=0)
    stale_books: Mapped[int] = mapped_column(Integer, default=0)
    opportunities: Mapped[int] = mapped_column(Integer, default=0)
    paper_trades: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    best_ask_sum: Mapped[Decimal | None] = mapped_column(MONEY)
    best_bid_sum: Mapped[Decimal | None] = mapped_column(MONEY)
    error: Mapped[str] = mapped_column(Text, default="")


class PmOpportunity(Base):
    """A detected arbitrage. Repeated detections of the same fingerprint update one row (first/last seen)."""

    __tablename__ = "pm_opportunity"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(120), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    event_id: Mapped[str] = mapped_column(String(32))
    condition_id: Mapped[str] = mapped_column(String(80), default="")
    title: Mapped[str] = mapped_column(String(300))
    first_seen_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    seen_count: Mapped[int] = mapped_column(Integer, default=1)
    shares: Mapped[Decimal] = mapped_column(MONEY)
    capital: Mapped[Decimal] = mapped_column(MONEY)
    payout: Mapped[Decimal] = mapped_column(MONEY)
    fees: Mapped[Decimal] = mapped_column(MONEY)
    net_edge: Mapped[Decimal] = mapped_column(MONEY)
    best_net_edge: Mapped[Decimal] = mapped_column(MONEY)
    edge_pct: Mapped[Decimal] = mapped_column(MONEY)
    holds_to_resolution: Mapped[bool] = mapped_column(Boolean, default=False)
    resolves_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    book_age_ms: Mapped[int] = mapped_column(Integer, default=0)
    legs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class PmPaperTrade(Base):
    """Simulated execution. Scanner trades are priced from a *second* book fetch after the modelled latency."""

    __tablename__ = "pm_paper_trade"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(16), default="scanner")  # scanner | copy
    opened_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)  # settled | open | missed
    kind: Mapped[str] = mapped_column(String(32))
    fingerprint: Mapped[str] = mapped_column(String(120), index=True)
    event_id: Mapped[str] = mapped_column(String(32))
    condition_id: Mapped[str] = mapped_column(String(80), default="")
    title: Mapped[str] = mapped_column(String(300))
    shares: Mapped[Decimal] = mapped_column(MONEY)
    capital: Mapped[Decimal] = mapped_column(MONEY)
    payout: Mapped[Decimal] = mapped_column(MONEY)
    fees: Mapped[Decimal] = mapped_column(MONEY)
    detected_edge: Mapped[Decimal] = mapped_column(MONEY)
    realized_pnl: Mapped[Decimal | None] = mapped_column(MONEY)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    resolves_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    settled_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    legs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    note: Mapped[str] = mapped_column(String(300), default="")


class PmWallet(Base):
    __tablename__ = "pm_wallet"

    address: Mapped[str] = mapped_column(String(42), primary_key=True)
    user_name: Mapped[str] = mapped_column(String(80), default="")
    first_seen_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    leaderboard_period: Mapped[str] = mapped_column(String(8), default="")
    leaderboard_rank: Mapped[int | None] = mapped_column(Integer)
    leaderboard_pnl: Mapped[Decimal | None] = mapped_column(MONEY)
    leaderboard_volume: Mapped[Decimal | None] = mapped_column(MONEY)
    tracked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    stats: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    stats_updated_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    note: Mapped[str] = mapped_column(String(300), default="")


class PmWalletTrade(Base):
    __tablename__ = "pm_wallet_trade"
    __table_args__ = (UniqueConstraint("wallet", "tx_hash", "asset", "side", "size", name="uq_pm_wallet_trade_fill"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet: Mapped[str] = mapped_column(String(42), index=True)
    tx_hash: Mapped[str] = mapped_column(String(80))
    asset: Mapped[str] = mapped_column(String(90))
    condition_id: Mapped[str] = mapped_column(String(80))
    side: Mapped[str] = mapped_column(String(4))
    size: Mapped[Decimal] = mapped_column(MONEY)
    price: Mapped[Decimal] = mapped_column(MONEY)
    outcome: Mapped[str] = mapped_column(String(80))
    outcome_index: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(300))
    slug: Mapped[str] = mapped_column(String(200))
    event_slug: Mapped[str] = mapped_column(String(200))
    at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
