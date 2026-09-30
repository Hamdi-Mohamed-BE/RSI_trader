"""Alembic environment. Uses a connection handed over by the app, or the configured database URL (CLI)."""

from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection

from crypto_lab.config import get_settings
from crypto_lab.infrastructure.db import models as _models  # noqa: F401  (register tables)
from crypto_lab.infrastructure.db import paper_models as _paper_models  # noqa: F401
from crypto_lab.infrastructure.db import polymarket_models as _pm_models  # noqa: F401
from crypto_lab.infrastructure.db.base import Base

target_metadata = Base.metadata


def _configure_and_run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = context.config.attributes.get("connection")
    if connection is not None:
        _configure_and_run(connection)
        return
    sync_url = get_settings().resolved_database_url.replace("+aiosqlite", "")
    engine = create_engine(sync_url)
    with engine.begin() as conn:
        _configure_and_run(conn)
    engine.dispose()


def run_migrations_offline() -> None:
    context.configure(
        url=get_settings().resolved_database_url.replace("+aiosqlite", ""),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
