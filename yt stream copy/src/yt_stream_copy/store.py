from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()
        self._init()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _init(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    channel TEXT NOT NULL DEFAULT 'Unknown',
                    title TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'stopped',
                    started_at TEXT NOT NULL,
                    stopped_at TEXT
                );
                CREATE TABLE IF NOT EXISTS transcripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    stream_seconds REAL,
                    text TEXT NOT NULL,
                    frame_path TEXT,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    symbol TEXT,
                    side TEXT,
                    entry REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    confidence REAL NOT NULL DEFAULT 0,
                    reason TEXT NOT NULL DEFAULT '',
                    evidence TEXT NOT NULL DEFAULT '[]',
                    frame_path TEXT,
                    broker_symbol TEXT,
                    risk_cash REAL,
                    volume REAL,
                    mt5_comment TEXT,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );
                CREATE TABLE IF NOT EXISTS screen_reads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    frame_path TEXT NOT NULL,
                    text TEXT NOT NULL DEFAULT '',
                    prices TEXT NOT NULL DEFAULT '[]',
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );
                """
            )

    def create_session(self, url: str, channel: str, title: str) -> int:
        with self._lock, self._connect() as db:
            db.execute("UPDATE sessions SET status='stopped', stopped_at=? WHERE status='running'", (utc_now(),))
            cursor = db.execute(
                "INSERT INTO sessions(url,channel,title,status,started_at) VALUES(?,?,?,?,?)",
                (url, channel or "Unknown", title or "", "running", utc_now()),
            )
            return int(cursor.lastrowid)

    def stop_session(self, session_id: int) -> None:
        with self._lock, self._connect() as db:
            db.execute("UPDATE sessions SET status='stopped', stopped_at=? WHERE id=?", (utc_now(), session_id))

    def add_transcript(self, session_id: int, text: str, frame_path: str | None = None) -> int:
        with self._lock, self._connect() as db:
            cursor = db.execute(
                "INSERT INTO transcripts(session_id,created_at,text,frame_path) VALUES(?,?,?,?)",
                (session_id, utc_now(), text.strip(), frame_path),
            )
            return int(cursor.lastrowid)

    def add_signal(self, session_id: int, data: dict[str, Any], frame_path: str | None = None) -> int:
        now = utc_now()
        with self._lock, self._connect() as db:
            cursor = db.execute(
                """INSERT INTO signals(
                    session_id,created_at,updated_at,status,symbol,side,entry,stop_loss,take_profit,
                    confidence,reason,evidence,frame_path,mt5_comment
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    session_id, now, now, data.get("status", "watching"), data.get("symbol"),
                    data.get("side"), data.get("entry"), data.get("stop_loss"), data.get("take_profit"),
                    float(data.get("confidence", 0)), data.get("reason", ""),
                    json.dumps(data.get("evidence", [])), frame_path, data.get("mt5_comment"),
                ),
            )
            return int(cursor.lastrowid)

    def update_signal(self, signal_id: int, changes: dict[str, Any]) -> None:
        allowed = {"status", "symbol", "side", "entry", "stop_loss", "take_profit", "confidence", "reason", "broker_symbol", "risk_cash", "volume", "mt5_comment"}
        values = {k: v for k, v in changes.items() if k in allowed}
        if not values:
            return
        values["updated_at"] = utc_now()
        columns = ",".join(f"{key}=?" for key in values)
        with self._lock, self._connect() as db:
            db.execute(f"UPDATE signals SET {columns} WHERE id=?", (*values.values(), signal_id))

    def recent_entry(self, session_id: int, symbol: str, side: str, seconds: int = 120) -> dict[str, Any] | None:
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat(timespec="seconds")
        with self._connect() as db:
            item = db.execute(
                """SELECT * FROM signals WHERE session_id=? AND symbol=? AND side=?
                AND status IN ('confirmed_entry','paper_open','paper_open_unprotected','paper_ready','approved')
                AND created_at >= ? ORDER BY id DESC LIMIT 1""",
                (session_id, symbol, side, cutoff),
            ).fetchone()
        return dict(item) if item else None

    def latest_open_signal(self, session_id: int, symbol: str | None = None) -> dict[str, Any] | None:
        query = """SELECT * FROM signals WHERE session_id=?
            AND status IN ('confirmed_entry','paper_open','paper_open_unprotected','paper_ready','approved')"""
        args: list[Any] = [session_id]
        if symbol:
            query += " AND symbol=?"
            args.append(symbol)
        query += " ORDER BY id DESC LIMIT 1"
        with self._connect() as db:
            item = db.execute(query, args).fetchone()
        return dict(item) if item else None

    def add_screen_read(self, session_id: int, frame_path: str, text: str, prices: list[float]) -> int:
        with self._lock, self._connect() as db:
            cursor = db.execute(
                "INSERT INTO screen_reads(session_id,created_at,frame_path,text,prices) VALUES(?,?,?,?,?)",
                (session_id, utc_now(), frame_path, text, json.dumps(prices)),
            )
            return int(cursor.lastrowid)

    def dashboard(self) -> dict[str, Any]:
        with self._connect() as db:
            session = db.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 1").fetchone()
            signals = db.execute("SELECT * FROM signals ORDER BY id DESC LIMIT 100").fetchall()
            transcripts = db.execute("SELECT * FROM transcripts ORDER BY id DESC LIMIT 100").fetchall()
            screen_reads = db.execute("SELECT * FROM screen_reads ORDER BY id DESC LIMIT 20").fetchall()
        def row(item: sqlite3.Row) -> dict[str, Any]:
            output = dict(item)
            if "evidence" in output:
                output["evidence"] = json.loads(output["evidence"] or "[]")
            if "prices" in output:
                output["prices"] = json.loads(output["prices"] or "[]")
            return output
        return {
            "session": row(session) if session else None,
            "signals": [row(item) for item in signals],
            "transcripts": [row(item) for item in transcripts],
            "screen_reads": [row(item) for item in screen_reads],
        }
