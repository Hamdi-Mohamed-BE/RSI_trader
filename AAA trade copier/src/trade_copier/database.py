from collections.abc import Generator

from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import Settings, get_settings


class Base(DeclarativeBase):
    pass


def build_engine(settings: Settings | None = None) -> Engine:
    active_settings = settings or get_settings()
    connect_args: dict[str, object] = {}
    if active_settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(
        active_settings.database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )

    if active_settings.database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def configure_sqlite(dbapi_connection: object, connection_record: object) -> None:
            del connection_record
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    return engine


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def get_session() -> Generator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_schema(active_engine: Engine | None = None) -> None:
    from . import models  # noqa: F401

    selected_engine = active_engine or engine
    Base.metadata.create_all(selected_engine)
    _upgrade_copy_test_schema(selected_engine)
    _upgrade_terminal_schema(selected_engine)


def _upgrade_copy_test_schema(selected_engine: Engine) -> None:
    """Preserve existing local history while adding new copy-test fields."""
    with selected_engine.begin() as connection:
        columns = {
            column["name"] for column in inspect(connection).get_columns("copy_test_runs")
        }
        if "order_type" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE copy_test_runs ADD COLUMN order_type "
                    "VARCHAR(16) NOT NULL DEFAULT 'market'"
                )
            )
        if "market_price" not in columns:
            connection.execute(
                text("ALTER TABLE copy_test_runs ADD COLUMN market_price NUMERIC(20, 8)")
            )


def _upgrade_terminal_schema(selected_engine: Engine) -> None:
    """Add managed-terminal diagnostics to existing local databases."""
    with selected_engine.begin() as connection:
        columns = {
            column["name"] for column in inspect(connection).get_columns("terminal_instances")
        }
        if "last_error" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE terminal_instances ADD COLUMN last_error "
                    "TEXT NOT NULL DEFAULT ''"
                )
            )
