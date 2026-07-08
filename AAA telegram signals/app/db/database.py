import os
from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text

from app.core.config import settings

# Parse the database URL to make sure parent folder exists
if settings.DATABASE_URL.startswith("sqlite:///"):
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
    echo=False
)

def init_db():
    """Initializes the database, creating all tables if they do not exist."""
    # Import models here to ensure they are registered with SQLModel.metadata
    from app.db import models
    SQLModel.metadata.create_all(engine)
    _migrate_sqlite()


def _migrate_sqlite():
    """Small additive migrations for local SQLite databases."""
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    managed_trade_columns = {
        "take_profits_json": "TEXT DEFAULT '[]'",
        "tp2_partial_done": "BOOLEAN DEFAULT 0",
        "tp2_partial_done_at": "DATETIME",
        "tp2_partial_volume": "FLOAT",
    }
    order_attempt_columns = {
        "signal_hash": "TEXT",
    }
    with engine.begin() as conn:
        existing = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(managed_trades)")).fetchall()
        }
        for name, definition in managed_trade_columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE managed_trades ADD COLUMN {name} {definition}"))

        existing = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(order_attempts)")).fetchall()
        }
        for name, definition in order_attempt_columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE order_attempts ADD COLUMN {name} {definition}"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_order_attempts_signal_hash ON order_attempts (signal_hash)"))

def get_db():
    """Dependency for database session context."""
    with Session(engine) as session:
        yield session
