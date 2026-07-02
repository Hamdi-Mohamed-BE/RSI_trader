from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RuntimeState(Base):
    __tablename__ = "runtime_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    worker_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    last_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_scan_status: Mapped[str] = mapped_column(String(32), default="idle")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class StrategyConfig(Base):
    __tablename__ = "strategy_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ScanSnapshot(Base):
    __tablename__ = "scan_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    price: Mapped[float] = mapped_column(Float)
    score: Mapped[float] = mapped_column(Float)
    direction: Mapped[str] = mapped_column(String(12))
    regime: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(24))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class OrderRecord(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    strategy: Mapped[str] = mapped_column(String(32), default="LTA_ORDER_FLOW")
    side: Mapped[str] = mapped_column(String(8))
    order_type: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(24), index=True)
    entry: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float)
    take_profit: Mapped[float] = mapped_column(Float)
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    risk_amount: Mapped[float] = mapped_column(Float, default=0.0)
    score: Mapped[float] = mapped_column(Float)
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    period: Mapped[str] = mapped_column(String(16))
    start_date: Mapped[str] = mapped_column(String(10))
    end_date: Mapped[str] = mapped_column(String(10))
    starting_balance: Mapped[float] = mapped_column(Float, default=300.0)
    symbols: Mapped[list[str]] = mapped_column(JSON, default=list)
    config_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    aggregate: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    results: Mapped[list["BacktestSymbolResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class BacktestSymbolResult(Base):
    __tablename__ = "backtest_symbol_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(16))
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    monthly: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    trades: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    equity: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    run: Mapped[BacktestRun] = relationship(back_populates="results")
