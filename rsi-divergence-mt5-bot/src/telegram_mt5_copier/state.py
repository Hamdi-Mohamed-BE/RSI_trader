from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .models import TelegramMessage, TradeSignal
from .settings import RUNTIME_DIR


class StateStore:
    def __init__(self, path: Path | None = None):
        self.path = path or RUNTIME_DIR / "copier.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def is_processed(self, message: TelegramMessage) -> bool:
        digest = self.message_hash(message.text)
        with self.connection() as db:
            row = db.execute(
                "SELECT content_hash, status FROM messages WHERE message_key = ?",
                (message.key,),
            ).fetchone()
        return bool(
            row
            and row[0] == digest
            and row[1] in {"COPIED", "IGNORED", "PREPARED"}
        )

    def record_message(
        self,
        message: TelegramMessage,
        status: str,
        signal: TradeSignal | None = None,
        error: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connection() as db:
            db.execute(
                """
                INSERT INTO messages (
                    message_key, chat_id, message_id, chat_name, message_date, text,
                    content_hash, status, signal_json, error, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(message_key) DO UPDATE SET
                    text=excluded.text, content_hash=excluded.content_hash,
                    status=excluded.status, signal_json=excluded.signal_json,
                    error=excluded.error, updated_at=excluded.updated_at
                """,
                (
                    message.key,
                    message.chat_id,
                    message.message_id,
                    message.chat_name,
                    message.date.isoformat(),
                    message.text,
                    self.message_hash(message.text),
                    status,
                    json.dumps(signal.to_dict()) if signal else None,
                    error,
                    now,
                ),
            )

    def record_trade(
        self,
        message_key: str,
        ticket: int,
        symbol: str,
        side: str,
        entry: float,
        stop_loss: float,
        tp1: float,
        final_tp: float,
        volume: float,
        status: str,
        detail: dict,
    ) -> None:
        with self.connection() as db:
            db.execute(
                """
                INSERT INTO trades (
                    message_key, ticket, symbol, side, entry, stop_loss, tp1,
                    final_tp, volume, status, detail_json, opened_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_key, ticket, symbol, side, entry, stop_loss, tp1,
                    final_tp, volume, status, json.dumps(detail),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def active_trades(self) -> list[dict]:
        with self.connection() as db:
            rows = db.execute(
                "SELECT id, ticket, symbol, side, entry, stop_loss, tp1, final_tp, status "
                "FROM trades WHERE status IN ('OPEN', 'PENDING', 'PROTECTED')"
            ).fetchall()
        keys = ("id", "ticket", "symbol", "side", "entry", "stop_loss", "tp1", "final_tp", "status")
        return [dict(zip(keys, row, strict=True)) for row in rows]

    def update_trade(self, trade_id: int, status: str, stop_loss: float | None = None) -> None:
        with self.connection() as db:
            if stop_loss is None:
                db.execute("UPDATE trades SET status = ? WHERE id = ?", (status, trade_id))
            else:
                db.execute(
                    "UPDATE trades SET status = ?, stop_loss = ? WHERE id = ?",
                    (status, stop_loss, trade_id),
                )

    def recent_messages(self, limit: int = 100) -> list[dict]:
        with self.connection() as db:
            rows = db.execute(
                "SELECT message_key, chat_name, message_date, text, status, signal_json, error, updated_at "
                "FROM messages ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        keys = ("key", "chat", "date", "text", "status", "signal", "error", "updated_at")
        return [dict(zip(keys, row, strict=True)) for row in rows]

    def get_meta(self, key: str, default: str = "") -> str:
        with self.connection() as db:
            row = db.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
        return str(row[0]) if row else default

    def set_meta(self, key: str, value: str) -> None:
        with self.connection() as db:
            db.execute(
                "INSERT INTO metadata (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path)
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def _initialize(self) -> None:
        with self.connection() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    message_key TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL,
                    message_id INTEGER NOT NULL,
                    chat_name TEXT,
                    message_date TEXT NOT NULL,
                    text TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    signal_json TEXT,
                    error TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_key TEXT NOT NULL,
                    ticket INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    tp1 REAL NOT NULL,
                    final_tp REAL NOT NULL,
                    volume REAL NOT NULL,
                    status TEXT NOT NULL,
                    detail_json TEXT NOT NULL,
                    opened_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def message_hash(text: str) -> str:
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
