from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .symbols import normalize_broker_symbol_suffix


@dataclass(frozen=True)
class Mt5AccountRecord:
    id: int
    name: str
    login: int
    password: str
    server: str
    symbol_suffix: str
    mt5_path: str | None
    enabled: bool
    is_primary: bool
    is_demo: bool
    created_at: str
    updated_at: str

    def to_worker_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "login": self.login,
            "password": self.password,
            "server": self.server,
            "symbol_suffix": self.symbol_suffix,
            "mt5_path": self.mt5_path,
            "is_demo": self.is_demo,
        }

    def public_dict(self, *, include_secrets: bool = False) -> dict:
        payload = {
            "id": self.id,
            "name": self.name,
            "login": self.login,
            "server": self.server,
            "symbol_suffix": self.symbol_suffix,
            "mt5_path": self.mt5_path,
            "enabled": self.enabled,
            "is_primary": self.is_primary,
            "is_demo": self.is_demo,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if include_secrets:
            payload["password"] = self.password
        else:
            payload["password_configured"] = bool(self.password)
        return payload


def default_db_path(config_dir: Path) -> Path:
    return (config_dir / "runtime" / "mt5_accounts.db").resolve()


class Mt5AccountStore:
    def __init__(self, path: Path):
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS mt5_accounts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        login INTEGER NOT NULL,
                        password TEXT NOT NULL,
                        server TEXT NOT NULL,
                        symbol_suffix TEXT NOT NULL DEFAULT '',
                        mt5_path TEXT,
                        enabled INTEGER NOT NULL DEFAULT 1,
                        is_primary INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS mt5_runtime_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    );
                    """
                )
                columns = {row[1] for row in conn.execute("PRAGMA table_info(mt5_accounts)").fetchall()}
                if "is_demo" not in columns:
                    conn.execute("ALTER TABLE mt5_accounts ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 1")
                conn.commit()
            finally:
                conn.close()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> Mt5AccountRecord:
        return Mt5AccountRecord(
            id=int(row["id"]),
            name=str(row["name"]),
            login=int(row["login"]),
            password=str(row["password"]),
            server=str(row["server"]),
            symbol_suffix=str(row["symbol_suffix"] or ""),
            mt5_path=str(row["mt5_path"]) if row["mt5_path"] else None,
            enabled=bool(row["enabled"]),
            is_primary=bool(row["is_primary"]),
            is_demo=bool(row["is_demo"]) if "is_demo" in row.keys() else True,
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def list_accounts(self) -> list[Mt5AccountRecord]:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute("SELECT * FROM mt5_accounts ORDER BY is_primary DESC, id ASC").fetchall()
                return [self._row_to_record(row) for row in rows]
            finally:
                conn.close()

    def get_account(self, account_id: int) -> Mt5AccountRecord | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute("SELECT * FROM mt5_accounts WHERE id = ?", (account_id,)).fetchone()
                return self._row_to_record(row) if row else None
            finally:
                conn.close()

    def add_account(
        self,
        *,
        name: str,
        login: int,
        password: str,
        server: str,
        symbol_suffix: str = "",
        mt5_path: str | None = None,
        enabled: bool = True,
        is_primary: bool = False,
        is_demo: bool = True,
    ) -> Mt5AccountRecord:
        cleaned_name = name.strip()
        cleaned_server = server.strip()
        cleaned_password = password.strip()
        if not cleaned_name:
            raise ValueError("Account name is required")
        if not cleaned_server:
            raise ValueError("Server is required")
        if not cleaned_password:
            raise ValueError("Password is required")
        if login <= 0:
            raise ValueError("Login must be a positive integer")
        suffix = normalize_broker_symbol_suffix(symbol_suffix or "")
        now = self._now_iso()
        with self._lock:
            conn = self._connect()
            try:
                if is_primary:
                    conn.execute("UPDATE mt5_accounts SET is_primary = 0")
                cur = conn.execute(
                    """
                    INSERT INTO mt5_accounts
                    (name, login, password, server, symbol_suffix, mt5_path, enabled, is_primary, is_demo, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cleaned_name,
                        int(login),
                        cleaned_password,
                        cleaned_server,
                        suffix,
                        mt5_path.strip() if mt5_path else None,
                        1 if enabled else 0,
                        1 if is_primary else 0,
                        1 if is_demo else 0,
                        now,
                        now,
                    ),
                )
                account_id = int(cur.lastrowid)
                if not conn.execute("SELECT COUNT(*) FROM mt5_accounts WHERE is_primary = 1").fetchone()[0]:
                    conn.execute("UPDATE mt5_accounts SET is_primary = 1 WHERE id = ?", (account_id,))
                conn.commit()
                row = conn.execute("SELECT * FROM mt5_accounts WHERE id = ?", (account_id,)).fetchone()
                return self._row_to_record(row)
            finally:
                conn.close()

    def update_account(
        self,
        account_id: int,
        *,
        name: str | None = None,
        login: int | None = None,
        password: str | None = None,
        server: str | None = None,
        symbol_suffix: str | None = None,
        mt5_path: str | None = None,
        enabled: bool | None = None,
        is_primary: bool | None = None,
        is_demo: bool | None = None,
    ) -> Mt5AccountRecord:
        account = self.get_account(account_id)
        if account is None:
            raise ValueError("Account not found")
        updates: dict[str, object] = {"updated_at": self._now_iso()}
        if name is not None:
            cleaned = name.strip()
            if not cleaned:
                raise ValueError("Account name cannot be empty")
            updates["name"] = cleaned
        if login is not None:
            if login <= 0:
                raise ValueError("Login must be a positive integer")
            updates["login"] = int(login)
        if password is not None:
            cleaned = password.strip()
            if not cleaned:
                raise ValueError("Password cannot be empty")
            updates["password"] = cleaned
        if server is not None:
            cleaned = server.strip()
            if not cleaned:
                raise ValueError("Server cannot be empty")
            updates["server"] = cleaned
        if symbol_suffix is not None:
            updates["symbol_suffix"] = normalize_broker_symbol_suffix(symbol_suffix)
        if mt5_path is not None:
            updates["mt5_path"] = mt5_path.strip() or None
        if enabled is not None:
            updates["enabled"] = 1 if enabled else 0
        if is_primary is not None:
            updates["is_primary"] = 1 if is_primary else 0
        if is_demo is not None:
            updates["is_demo"] = 1 if is_demo else 0
        if not updates:
            return account
        with self._lock:
            conn = self._connect()
            try:
                if is_primary:
                    conn.execute("UPDATE mt5_accounts SET is_primary = 0")
                assignments = ", ".join(f"{key} = ?" for key in updates)
                conn.execute(
                    f"UPDATE mt5_accounts SET {assignments} WHERE id = ?",
                    (*updates.values(), account_id),
                )
                if not conn.execute("SELECT COUNT(*) FROM mt5_accounts WHERE is_primary = 1").fetchone()[0]:
                    conn.execute("UPDATE mt5_accounts SET is_primary = 1 WHERE id = ?", (account_id,))
                conn.commit()
                row = conn.execute("SELECT * FROM mt5_accounts WHERE id = ?", (account_id,)).fetchone()
                return self._row_to_record(row)
            finally:
                conn.close()

    def delete_account(self, account_id: int) -> Mt5AccountRecord:
        account = self.get_account(account_id)
        if account is None:
            raise ValueError("Account not found")
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM mt5_accounts WHERE id = ?", (account_id,))
                if account.is_primary:
                    row = conn.execute("SELECT id FROM mt5_accounts ORDER BY id ASC LIMIT 1").fetchone()
                    if row:
                        conn.execute("UPDATE mt5_accounts SET is_primary = 1 WHERE id = ?", (int(row["id"]),))
                conn.commit()
                return account
            finally:
                conn.close()

    def enabled_accounts(self) -> list[Mt5AccountRecord]:
        return [item for item in self.list_accounts() if item.enabled]

    def primary_account(self) -> Mt5AccountRecord | None:
        accounts = self.list_accounts()
        for item in accounts:
            if item.enabled and item.is_primary:
                return item
        for item in accounts:
            if item.enabled:
                return item
        return accounts[0] if accounts else None

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute("SELECT value FROM mt5_runtime_settings WHERE key = ?", (key,)).fetchone()
                if row is None:
                    return default
                return str(row["value"])
            finally:
                conn.close()

    def set_setting(self, key: str, value: str) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO mt5_runtime_settings (key, value) VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (key, value),
                )
                conn.commit()
            finally:
                conn.close()

    def trading_mode(self) -> str:
        mode = (self.get_setting("trading_mode", "parallel") or "parallel").strip().lower()
        return mode if mode in {"parallel", "single"} else "parallel"

    def set_trading_mode(self, mode: str) -> str:
        normalized = mode.strip().lower()
        if normalized not in {"parallel", "single"}:
            raise ValueError("trading_mode must be parallel or single")
        self.set_setting("trading_mode", normalized)
        return normalized

    def active_account_id(self) -> int | None:
        raw = self.get_setting("active_account_id")
        if not raw:
            primary = self.primary_account()
            return primary.id if primary else None
        try:
            return int(raw)
        except ValueError:
            return None

    def set_active_account_id(self, account_id: int) -> None:
        if self.get_account(account_id) is None:
            raise ValueError("Account not found")
        self.set_setting("active_account_id", str(account_id))

    def runtime_payload(self) -> dict:
        accounts = self.list_accounts()
        return {
            "trading_mode": self.trading_mode(),
            "active_account_id": self.active_account_id(),
            "accounts": [item.public_dict() for item in accounts],
            "enabled_count": sum(1 for item in accounts if item.enabled),
        }
