"""Detached runner for the ORB trade-count audit (2026-09-29): parity (1y) then diagnostic 5y runs.
Isolated tester only; completed cases are skipped; waits for port 3000 inside the runner.
Shares the isolated tester with other research sessions: waits until no isolated terminal64 and no other
`run.py` research runner has been seen for IDLE_SECONDS, and retries if the runner refuses a busy tester."""
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV = {**os.environ, "EA_STORE_DISABLE_MT5": "1", "PYTHONIOENCODING": "utf-8"}
QLOG = ROOT / "native" / "queue.log"
QLOG.parent.mkdir(parents=True, exist_ok=True)
ISOLATED = "_Backtests\\MT5-DMC-20260811\\terminal64.exe".lower()
IDLE_SECONDS = 240
MAX_ATTEMPTS = 40


def log(msg: str) -> None:
    with QLOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}\n")


def tester_busy() -> bool:
    ps = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -in 'terminal64.exe','metatester64.exe','python.exe' } "
          "| ForEach-Object { $_.Name + '|' + $_.CommandLine }")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.lower()
    for line in out.splitlines():
        if ISOLATED in line or line.startswith("metatester64.exe"):
            return True
        if line.startswith("python.exe") and " run.py " in f"{line} ":
            return True
    return False


def wait_idle() -> None:
    quiet_since = None
    while True:
        if tester_busy():
            quiet_since = None
        elif quiet_since is None:
            quiet_since = time.time()
        elif time.time() - quiet_since >= IDLE_SECONDS:
            return
        time.sleep(20)


log("START audit (shared-tester wait mode)")
for attempt in range(1, MAX_ATTEMPTS + 1):
    log(f"WAIT tester idle (attempt {attempt})")
    wait_idle()
    log("tester idle; running audit")
    with (ROOT / "native" / "run.log").open("a", encoding="utf-8") as f:
        rc = subprocess.run([sys.executable, "run_orbaudit.py", "parity", "main", "summary"], cwd=ROOT, env=ENV, stdout=f,
                            stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).returncode
    log(f"audit exit {rc}")
    tail = (ROOT / "native" / "run.log").read_text(encoding="utf-8", errors="replace")[-1500:]
    if rc == 0 or "already running" not in tail:
        break
    log("tester was taken by another session; waiting again")
log("QUEUE DONE")
