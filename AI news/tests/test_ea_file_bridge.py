from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ea_file_bridge


def test_write_snapshot_retries_transient_windows_lock(
    tmp_path: Path, monkeypatch
) -> None:
    destination = tmp_path / "GoldNewsV9EA" / "bridge.json"
    real_replace = ea_file_bridge.os.replace
    attempts = 0

    def flaky_replace(source: Path, target: Path) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise PermissionError("simulated MT5 read lock")
        real_replace(source, target)

    monkeypatch.setattr(ea_file_bridge.os, "replace", flaky_replace)
    monkeypatch.setattr(ea_file_bridge, "WRITE_RETRY_INTERVAL_SECONDS", 0.001)

    ea_file_bridge._write_snapshot(destination, {"heartbeat_epoch": 123})

    assert attempts == 3
    assert json.loads(destination.read_text(encoding="ascii")) == {
        "heartbeat_epoch": 123
    }
    assert list(destination.parent.glob("*.tmp")) == []
