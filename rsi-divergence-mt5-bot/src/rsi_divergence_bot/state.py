from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_STATE: dict[str, Any] = {"setups": [], "seen_signals": []}


class StateStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if not self.path.exists():
            self.write(DEFAULT_STATE.copy())

    def read(self) -> dict[str, Any]:
        with self._lock:
            return self._read_unlocked()

    def write(self, state: dict[str, Any]) -> None:
        with self._lock:
            self._write_unlocked(state)

    def _read_unlocked(self) -> dict[str, Any]:
        try:
            raw = self.path.read_text(encoding="utf-8").strip()
            if not raw:
                logger.warning("State file %s is empty; using defaults", self.path)
                return DEFAULT_STATE.copy()
            return json.loads(raw)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("State file %s unreadable (%s); using defaults", self.path, exc)
            return DEFAULT_STATE.copy()

    def _write_unlocked(self, state: dict[str, Any]) -> None:
        payload = json.dumps(state, indent=2)
        tmp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        tmp_path.write_text(payload, encoding="utf-8")
        tmp_path.replace(self.path)

    def add_setup(self, setup: dict[str, Any]) -> None:
        with self._lock:
            state = self._read_unlocked()
            state.setdefault("setups", []).append(setup)
            state.setdefault("seen_signals", []).append(setup["setup_id"])
            self._write_unlocked(state)

    def is_seen(self, setup_id: str) -> bool:
        with self._lock:
            state = self._read_unlocked()
            return setup_id in set(state.get("seen_signals", []))

    def mark_seen(self, setup_id: str) -> None:
        with self._lock:
            state = self._read_unlocked()
            seen = state.setdefault("seen_signals", [])
            if setup_id not in seen:
                seen.append(setup_id)
            state["seen_signals"] = seen[-500:]
            self._write_unlocked(state)

    def update_setups(self, setups: list[dict[str, Any]]) -> None:
        with self._lock:
            state = self._read_unlocked()
            state["setups"] = setups
            self._write_unlocked(state)

    def update_setup(self, setup_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        with self._lock:
            state = self._read_unlocked()
            setups = state.get("setups", [])
            updated: dict[str, Any] | None = None
            for index, setup in enumerate(setups):
                if setup.get("setup_id") != setup_id:
                    continue
                updated = {**setup, **updates}
                setups[index] = updated
                break
            if updated is None:
                return None
            state["setups"] = setups
            self._write_unlocked(state)
            return updated

    def update_daily_risk(self, daily_risk: dict[str, Any]) -> None:
        with self._lock:
            state = self._read_unlocked()
            state["daily_risk"] = daily_risk
            self._write_unlocked(state)

    def set_auto_loop_enabled(self, enabled: bool) -> None:
        with self._lock:
            state = self._read_unlocked()
            state["auto_loop_enabled"] = enabled
            self._write_unlocked(state)

    def auto_loop_enabled(self) -> bool:
        with self._lock:
            state = self._read_unlocked()
            return bool(state.get("auto_loop_enabled"))

    def upsert_telegram_message(self, message_id: str, payload: dict[str, Any]) -> None:
        with self._lock:
            state = self._read_unlocked()
            messages = state.setdefault("telegram_messages", [])
            existing = next((item for item in messages if item.get("message_id") == message_id), None)
            if existing is not None:
                merged = {**existing, **payload}
                if payload.get("parsed") is None and existing.get("parsed") is not None:
                    merged["parsed"] = existing["parsed"]
                if payload.get("result") is None and existing.get("result") is not None:
                    merged["result"] = existing["result"]
                if payload.get("text") is None and existing.get("text") is not None:
                    merged["text"] = existing["text"]
                payload = merged
            next_messages = [item for item in messages if item.get("message_id") != message_id]
            next_messages.append({"message_id": message_id, **payload})
            state["telegram_messages"] = next_messages[-500:]
            self._write_unlocked(state)

    def get_telegram_message(self, message_id: str) -> dict[str, Any] | None:
        with self._lock:
            state = self._read_unlocked()
            for item in state.get("telegram_messages", []):
                if item.get("message_id") == message_id:
                    return dict(item)
            return None

    def find_telegram_message_by_key(self, message_key: str) -> dict[str, Any] | None:
        if not message_key:
            return None
        with self._lock:
            state = self._read_unlocked()
            matches = [
                dict(item)
                for item in state.get("telegram_messages", [])
                if str(item.get("message_key") or "") == str(message_key)
            ]
            if not matches:
                return None
            return max(matches, key=lambda item: str(item.get("updated_at") or item.get("last_seen_at") or ""))

    def recent_telegram_messages(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            state = self._read_unlocked()
            return list(state.get("telegram_messages", []))[-limit:]

    def clear_telegram_history(self) -> dict[str, int]:
        with self._lock:
            state = self._read_unlocked()
            messages_removed = len(state.get("telegram_messages", []))
            trades_removed = len(state.get("telegram_processed_trades", []))
            seen = state.get("seen_signals", [])
            seen_removed = sum(1 for item in seen if str(item).startswith("telegram:"))
            state["telegram_messages"] = []
            state["telegram_processed_trades"] = []
            state["seen_signals"] = [item for item in seen if not str(item).startswith("telegram:")]
            self._write_unlocked(state)
            return {
                "messages_removed": messages_removed,
                "seen_removed": seen_removed,
                "trade_hashes_removed": trades_removed,
            }

    def is_telegram_trade_processed(self, trade_hash: str) -> bool:
        with self._lock:
            state = self._read_unlocked()
            known = {str(item.get("hash")) for item in state.get("telegram_processed_trades", [])}
            return trade_hash in known

    def mark_telegram_trade_processed(self, trade_hash: str, payload: dict[str, Any]) -> None:
        with self._lock:
            state = self._read_unlocked()
            entries = state.setdefault("telegram_processed_trades", [])
            next_entries = [item for item in entries if item.get("hash") != trade_hash]
            next_entries.append({"hash": trade_hash, **payload})
            state["telegram_processed_trades"] = next_entries[-500:]
            self._write_unlocked(state)
