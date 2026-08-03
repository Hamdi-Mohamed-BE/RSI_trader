from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass
class State:
    processed_weeks: dict[str, dict] = field(default_factory=dict)
    active: dict[str, dict] = field(default_factory=dict)


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> State:
        if not self.path.exists():
            return State()
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return State(dict(data.get("processed_weeks", {})), dict(data.get("active", {})))

    def save(self, state: State) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps({"processed_weeks": state.processed_weeks, "active": state.active}, indent=2, sort_keys=True), encoding="utf-8")
        temp.replace(self.path)
