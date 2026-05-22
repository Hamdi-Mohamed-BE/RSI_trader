from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StateStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.write({"setups": [], "seen_signals": []})

    def read(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def write(self, state: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def add_setup(self, setup: dict[str, Any]) -> None:
        state = self.read()
        state.setdefault("setups", []).append(setup)
        state.setdefault("seen_signals", []).append(setup["setup_id"])
        self.write(state)

    def is_seen(self, setup_id: str) -> bool:
        state = self.read()
        return setup_id in set(state.get("seen_signals", []))

    def mark_seen(self, setup_id: str) -> None:
        state = self.read()
        seen = state.setdefault("seen_signals", [])
        if setup_id not in seen:
            seen.append(setup_id)
        state["seen_signals"] = seen[-500:]
        self.write(state)

    def update_setups(self, setups: list[dict[str, Any]]) -> None:
        state = self.read()
        state["setups"] = setups
        self.write(state)

    def update_setup(self, setup_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        state = self.read()
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
        self.write(state)
        return updated

    def update_daily_risk(self, daily_risk: dict[str, Any]) -> None:
        state = self.read()
        state["daily_risk"] = daily_risk
        self.write(state)

    def set_auto_loop_enabled(self, enabled: bool) -> None:
        state = self.read()
        state["auto_loop_enabled"] = enabled
        self.write(state)

    def auto_loop_enabled(self) -> bool:
        return bool(self.read().get("auto_loop_enabled"))

    def upsert_telegram_message(self, message_id: str, payload: dict[str, Any]) -> None:
        state = self.read()
        messages = state.setdefault("telegram_messages", [])
        next_messages = [item for item in messages if item.get("message_id") != message_id]
        next_messages.append({"message_id": message_id, **payload})
        state["telegram_messages"] = next_messages[-500:]
        self.write(state)

    def recent_telegram_messages(self, limit: int = 50) -> list[dict[str, Any]]:
        state = self.read()
        return list(state.get("telegram_messages", []))[-limit:]

    def clear_telegram_history(self) -> dict[str, int]:
        state = self.read()
        messages_removed = len(state.get("telegram_messages", []))
        seen = state.get("seen_signals", [])
        seen_removed = sum(1 for item in seen if str(item).startswith("telegram:"))
        state["telegram_messages"] = []
        state["seen_signals"] = [item for item in seen if not str(item).startswith("telegram:")]
        self.write(state)
        return {"messages_removed": messages_removed, "seen_removed": seen_removed}
