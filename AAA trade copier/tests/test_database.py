from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from trade_copier.database import create_schema


def test_create_schema_upgrades_existing_copy_test_history(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'existing.db'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE copy_test_runs ("
                "id VARCHAR(36) PRIMARY KEY, "
                "symbol VARCHAR(32), "
                "side VARCHAR(8), "
                "master_volume NUMERIC(16, 4), "
                "entry_price NUMERIC(20, 8), "
                "stop_loss NUMERIC(20, 8), "
                "take_profit NUMERIC(20, 8))"
            )
        )

    create_schema(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("copy_test_runs")}
    assert {"order_type", "market_price"} <= columns
    engine.dispose()
