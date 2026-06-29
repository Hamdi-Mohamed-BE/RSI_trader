from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import BrokerOrderResult, Direction, Signal, TradeRecord


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class Storage:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    source_id TEXT NOT NULL,
                    message_id INTEGER NOT NULL,
                    received_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reason TEXT,
                    raw_text TEXT,
                    PRIMARY KEY (source_id, message_id)
                );

                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_key TEXT NOT NULL UNIQUE,
                    source_id TEXT NOT NULL,
                    message_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    break_even_trigger REAL NOT NULL,
                    comment_prefix TEXT NOT NULL,
                    orders_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    break_even_done INTEGER NOT NULL DEFAULT 0,
                    raw_text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def has_message(self, source_id: str, message_id: int) -> bool:
        with self._connect() as db:
            row = db.execute(
                "SELECT 1 FROM messages WHERE source_id = ? AND message_id = ?",
                (source_id, message_id),
            ).fetchone()
            return row is not None

    def message_record(self, source_id: str, message_id: int) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT status, reason, raw_text FROM messages WHERE source_id = ? AND message_id = ?",
                (source_id, message_id),
            ).fetchone()
        return dict(row) if row is not None else None

    def delete_message(self, source_id: str, message_id: int) -> None:
        with self._connect() as db:
            db.execute(
                "DELETE FROM messages WHERE source_id = ? AND message_id = ?",
                (source_id, message_id),
            )

    def record_message(
        self,
        source_id: str,
        message_id: int,
        *,
        status: str,
        reason: str | None = None,
        raw_text: str | None = None,
    ) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO messages (source_id, message_id, received_at, status, reason, raw_text)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, message_id) DO UPDATE SET
                    status = excluded.status,
                    reason = excluded.reason,
                    raw_text = excluded.raw_text
                """,
                (source_id, message_id, _utc_now_iso(), status, reason, raw_text),
            )

    def record_trade(
        self,
        signal: Signal,
        *,
        broker_symbol: str,
        entry_price: float,
        take_profit: float,
        break_even_trigger: float,
        comment_prefix: str,
        order_results: list[BrokerOrderResult],
        status: str,
    ) -> None:
        orders = [
            {
                "ticket": result.ticket,
                "deal": result.deal,
                "retcode": result.retcode,
                "comment": result.comment,
            }
            for result in order_results
        ]
        now = _utc_now_iso()
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO trades (
                    signal_key, source_id, message_id, symbol, direction, entry_price,
                    stop_loss, take_profit, break_even_trigger, comment_prefix,
                    orders_json, status, break_even_done, raw_text, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                ON CONFLICT(signal_key) DO UPDATE SET
                    orders_json = excluded.orders_json,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (
                    signal.key,
                    signal.source_id,
                    signal.message_id,
                    broker_symbol,
                    signal.direction.value,
                    entry_price,
                    signal.stop_loss,
                    take_profit,
                    break_even_trigger,
                    comment_prefix,
                    json.dumps(orders),
                    status,
                    signal.raw_text,
                    now,
                    now,
                ),
            )

    def iter_active_trades(self) -> list[TradeRecord]:
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT * FROM trades
                WHERE status IN ('active', 'pending')
                ORDER BY created_at ASC
                """
            ).fetchall()
        return [self._row_to_trade(row) for row in rows]

    def mark_trade_status(self, trade_id: int, status: str) -> None:
        with self._connect() as db:
            db.execute(
                "UPDATE trades SET status = ?, updated_at = ? WHERE id = ?",
                (status, _utc_now_iso(), trade_id),
            )

    def mark_break_even_done(self, trade_id: int) -> None:
        with self._connect() as db:
            db.execute(
                """
                UPDATE trades
                SET break_even_done = 1, updated_at = ?
                WHERE id = ?
                """,
                (_utc_now_iso(), trade_id),
            )

    def trade_orders(self, trade: TradeRecord) -> list[dict[str, Any]]:
        try:
            data = json.loads(trade.orders_json)
        except json.JSONDecodeError:
            return []
        return data if isinstance(data, list) else []

    def _row_to_trade(self, row: sqlite3.Row) -> TradeRecord:
        return TradeRecord(
            id=int(row["id"]),
            signal_key=str(row["signal_key"]),
            message_id=int(row["message_id"]),
            source_id=str(row["source_id"]),
            symbol=str(row["symbol"]),
            direction=Direction(str(row["direction"])),
            entry_price=float(row["entry_price"]),
            stop_loss=float(row["stop_loss"]),
            take_profit=float(row["take_profit"]),
            break_even_trigger=float(row["break_even_trigger"]),
            comment_prefix=str(row["comment_prefix"]),
            orders_json=str(row["orders_json"]),
            status=str(row["status"]),
            break_even_done=bool(row["break_even_done"]),
            created_at=_dt(str(row["created_at"])),
        )
