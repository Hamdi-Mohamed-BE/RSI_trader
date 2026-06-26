from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "reports" / "orb_bot" / "orb.lock"


def _read_payload() -> dict:
    try:
        payload = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _orb_process_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        script = (
            f"$p = Get-CimInstance Win32_Process -Filter \"ProcessId = {pid}\" "
            "-ErrorAction SilentlyContinue; "
            "if ($p) { $p.CommandLine }"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True,
                text=True,
                timeout=3,
            )
        except Exception:
            return False
        command_line = (result.stdout or "").lower()
        return "app.orb_bot" in command_line or "orb_bot.py" in command_line
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def main() -> int:
    if not LOCK_PATH.exists():
        return 0

    payload = _read_payload()
    try:
        pid = int(payload.get("pid") or 0)
    except Exception:
        pid = 0

    if _orb_process_is_alive(pid):
        print(f"ORB lock is active; existing ORB PID {pid} is still running.")
        return 0

    try:
        LOCK_PATH.unlink()
    except FileNotFoundError:
        return 0
    print("Removed stale ORB lock.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
