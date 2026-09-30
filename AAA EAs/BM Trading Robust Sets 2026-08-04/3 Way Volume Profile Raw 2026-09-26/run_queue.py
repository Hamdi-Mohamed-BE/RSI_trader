"""Detached runner for the 3 Way Volume Profile raw grid (2026-09-26): all variants x symbols x last year, then report.
Isolated tester only; completed cases are skipped; waits for port 3000 inside the runner."""
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV = {**os.environ, "EA_STORE_DISABLE_MT5": "1", "PYTHONIOENCODING": "utf-8"}
QLOG = ROOT / "native" / "queue.log"


def log(msg: str) -> None:
    with QLOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}\n")


log("START grid")
with (ROOT / "native" / "run.log").open("a", encoding="utf-8") as f:
    rc = subprocess.run([sys.executable, "run_3wvp.py", "main", "summary"], cwd=ROOT, env=ENV, stdout=f,
                        stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).returncode
log(f"grid exit {rc}")
if (ROOT / "make_report.py").exists():
    with (ROOT / "native" / "report.log").open("w", encoding="utf-8") as f:
        rc = subprocess.run([sys.executable, "make_report.py"], cwd=ROOT, env=ENV, stdout=f, stderr=subprocess.STDOUT,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).returncode
    log(f"report exit {rc}")
log("QUEUE DONE")
