from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path


@dataclass
class State:
    processed: dict[str, dict] = field(default_factory=dict)
    active: dict[str, dict] = field(default_factory=dict)


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> State:
        if not self.path.exists():
            return State()
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return State(processed=dict(raw.get("processed", {})), active=dict(raw.get("active", {})))

    def save(self, state: State) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"processed": state.processed, "active": state.active}, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self.path)


def signal_hash(*parts: object) -> str:
    payload = "|".join(str(x) for x in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
