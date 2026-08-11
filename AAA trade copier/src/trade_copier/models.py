from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .domain.enums import (
    AccountRole,
    AccountState,
    AuditSeverity,
    ExecutionMode,
    JobStatus,
    OrderType,
    RiskMode,
    TerminalHealth,
)


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_uuid() -> str:
    return str(uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class AdminUser(TimestampMixin, Base):
    __tablename__ = "admin_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120), default="Administrator")
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RiskProfile(TimestampMixin, Base):
    __tablename__ = "risk_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    mode: Mapped[str] = mapped_column(String(32), default=RiskMode.STOP_PERCENT.value)
    risk_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("1.0"))
    fixed_cash_risk: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    fixed_lots: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    max_risk_per_trade_percent: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), default=Decimal("1.0")
    )
    max_total_open_risk_percent: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), default=Decimal("5.0")
    )
    max_daily_loss_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("3.0"))
    max_spread_points: Mapped[int] = mapped_column(Integer, default=50)
    max_slippage_points: Mapped[int] = mapped_column(Integer, default=30)
    max_open_positions: Mapped[int] = mapped_column(Integer, default=10)
    reject_without_stop: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    accounts: Mapped[list["Account"]] = relationship(back_populates="risk_profile")


class Account(TimestampMixin, Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    display_name: Mapped[str] = mapped_column(String(120), unique=True)
    login: Mapped[str] = mapped_column(String(32), index=True)
    broker_server: Mapped[str] = mapped_column(String(160))
    terminal_path: Mapped[str] = mapped_column(String(500), default="")
    role: Mapped[str] = mapped_column(String(32), default=AccountRole.FOLLOWER.value)
    state: Mapped[str] = mapped_column(String(32), default=AccountState.DISABLED.value)
    is_master: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    credential_ref: Mapped[str] = mapped_column(String(255), default="")
    account_currency: Mapped[str] = mapped_column(String(12), default="USD")
    trade_mode: Mapped[str] = mapped_column(String(32), default="demo")
    position_mode: Mapped[str] = mapped_column(String(32), default="hedging")
    balance: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal("0"))
    equity: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal("0"))
    free_margin: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal("0"))
    health: Mapped[str] = mapped_column(String(24), default=TerminalHealth.UNKNOWN.value)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    risk_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("risk_profiles.id", ondelete="SET NULL"), nullable=True
    )

    risk_profile: Mapped[RiskProfile | None] = relationship(back_populates="accounts")
    symbol_mappings: Mapped[list["SymbolMapping"]] = relationship(
        back_populates="follower_account", cascade="all, delete-orphan"
    )
    terminal: Mapped["TerminalInstance | None"] = relationship(
        back_populates="account", cascade="all, delete-orphan", uselist=False
    )
    symbol_specs: Mapped[list["AccountSymbolSpec"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )

    @property
    def masked_login(self) -> str:
        if len(self.login) <= 4:
            return "•" * len(self.login)
        return f"{'•' * (len(self.login) - 4)}{self.login[-4:]}"


class TerminalInstance(TimestampMixin, Base):
    __tablename__ = "terminal_instances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), unique=True
    )
    process_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    portable_directory: Mapped[str] = mapped_column(String(500), default="")
    terminal_build: Mapped[str] = mapped_column(String(32), default="")
    algo_trading_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    health: Mapped[str] = mapped_column(String(24), default=TerminalHealth.UNKNOWN.value)
    last_error: Mapped[str] = mapped_column(Text, default="")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    account: Mapped[Account] = relationship(back_populates="terminal")


class SymbolMapping(TimestampMixin, Base):
    __tablename__ = "symbol_mappings"
    __table_args__ = (
        UniqueConstraint("follower_account_id", "master_symbol", name="uq_follower_master_symbol"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    follower_account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    master_symbol: Mapped[str] = mapped_column(String(32))
    follower_symbol: Mapped[str] = mapped_column(String(32))
    price_offset: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("0"))
    preserve_relative_stops: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    follower_account: Mapped[Account] = relationship(back_populates="symbol_mappings")


class AccountSymbolSpec(TimestampMixin, Base):
    __tablename__ = "account_symbol_specs"
    __table_args__ = (UniqueConstraint("account_id", "symbol", name="uq_account_symbol"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    symbol: Mapped[str] = mapped_column(String(32))
    tick_size: Mapped[Decimal] = mapped_column(Numeric(20, 10))
    tick_value: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    volume_min: Mapped[Decimal] = mapped_column(Numeric(16, 4))
    volume_max: Mapped[Decimal] = mapped_column(Numeric(16, 4))
    volume_step: Mapped[Decimal] = mapped_column(Numeric(16, 4))
    contract_size: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("1"))
    spread_points: Mapped[int] = mapped_column(Integer, default=0)
    trading_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    account: Mapped[Account] = relationship(back_populates="symbol_specs")


class SystemState(TimestampMixin, Base):
    __tablename__ = "system_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    active_master_account_id: Mapped[str | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    global_pause: Mapped[bool] = mapped_column(Boolean, default=True)
    execution_mode: Mapped[str] = mapped_column(String(24), default=ExecutionMode.MONITOR.value)
    reason: Mapped[str] = mapped_column(String(255), default="Initial safe state")


class SourceTradeEvent(TimestampMixin, Base):
    __tablename__ = "source_trade_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    event_uid: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    source_account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    source_order_id: Mapped[str] = mapped_column(String(64))
    source_position_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(32))
    side: Mapped[str] = mapped_column(String(8))
    symbol: Mapped[str] = mapped_column(String(32))
    volume: Mapped[Decimal] = mapped_column(Numeric(16, 4))
    entry_price: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    magic_number: Mapped[int] = mapped_column(Integer, default=0)
    comment: Mapped[str] = mapped_column(String(255), default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    jobs: Mapped[list["CopyJob"]] = relationship(
        back_populates="source_event", cascade="all, delete-orphan"
    )


class CopyJob(TimestampMixin, Base):
    __tablename__ = "copy_jobs"
    __table_args__ = (
        UniqueConstraint("source_event_id", "follower_account_id", name="uq_event_follower"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    job_uid: Mapped[str] = mapped_column(String(36), unique=True, default=new_uuid, index=True)
    source_event_id: Mapped[str] = mapped_column(
        ForeignKey("source_trade_events.id", ondelete="CASCADE"), index=True
    )
    follower_account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(24), default=JobStatus.QUEUED.value)
    follower_symbol: Mapped[str] = mapped_column(String(32))
    requested_volume: Mapped[Decimal] = mapped_column(Numeric(16, 4))
    requested_price: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    risk_cash: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal("0"))
    rejection_reason: Mapped[str] = mapped_column(Text, default="")
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    local_latency_ms: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    broker_latency_ms: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)

    source_event: Mapped[SourceTradeEvent] = relationship(back_populates="jobs")
    follower_account: Mapped[Account] = relationship()
    acknowledgement: Mapped["ExecutionAcknowledgement | None"] = relationship(
        back_populates="job", cascade="all, delete-orphan", uselist=False
    )


class ExecutionAcknowledgement(TimestampMixin, Base):
    __tablename__ = "execution_acknowledgements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    copy_job_id: Mapped[str] = mapped_column(
        ForeignKey("copy_jobs.id", ondelete="CASCADE"), unique=True
    )
    status: Mapped[str] = mapped_column(String(24))
    broker_order_id: Mapped[str] = mapped_column(String(64), default="")
    broker_position_id: Mapped[str] = mapped_column(String(64), default="")
    broker_result_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    filled_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    filled_volume: Mapped[Decimal | None] = mapped_column(Numeric(16, 4), nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped[CopyJob] = relationship(back_populates="acknowledgement")


class AuditEvent(TimestampMixin, Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    actor: Mapped[str] = mapped_column(String(254), default="system")
    action: Mapped[str] = mapped_column(String(120), index=True)
    target_type: Mapped[str] = mapped_column(String(80), default="system")
    target_id: Mapped[str] = mapped_column(String(64), default="")
    severity: Mapped[str] = mapped_column(String(16), default=AuditSeverity.INFO.value)
    message: Mapped[str] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str] = mapped_column(String(64), default="")


class CopyTestRun(TimestampMixin, Base):
    __tablename__ = "copy_test_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    master_account_id: Mapped[str | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(32))
    side: Mapped[str] = mapped_column(String(8))
    order_type: Mapped[str] = mapped_column(String(16), default=OrderType.MARKET.value)
    master_volume: Mapped[Decimal] = mapped_column(Numeric(16, 4))
    market_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    stop_loss: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="running")
    total_followers: Mapped[int] = mapped_column(Integer, default=0)
    passed_followers: Mapped[int] = mapped_column(Integer, default=0)
    failed_followers: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    results: Mapped[list["CopyTestResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class CopyTestResult(TimestampMixin, Base):
    __tablename__ = "copy_test_results"
    __table_args__ = (
        UniqueConstraint("run_id", "follower_account_id", name="uq_copy_test_follower"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("copy_test_runs.id", ondelete="CASCADE"), index=True
    )
    follower_account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(24))
    follower_symbol: Mapped[str] = mapped_column(String(32), default="")
    calculated_volume: Mapped[Decimal | None] = mapped_column(Numeric(16, 4), nullable=True)
    calculated_risk_cash: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    checks: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    run: Mapped[CopyTestRun] = relationship(back_populates="results")
    follower_account: Mapped[Account] = relationship()


def as_uuid(value: str) -> UUID:
    return UUID(value)


__all__ = [
    "Account",
    "AccountSymbolSpec",
    "AdminUser",
    "AuditEvent",
    "CopyJob",
    "CopyTestResult",
    "CopyTestRun",
    "ExecutionAcknowledgement",
    "RiskProfile",
    "SourceTradeEvent",
    "SymbolMapping",
    "SystemState",
    "TerminalInstance",
    "as_uuid",
]
