"""Detached study queue (2026-09-25): In-Play ORB, then ATR Touch. One tester at a time (isolated tester only).
Each study: screen -> make_report (gate, writes native/ADVANCE.json) -> confirm -> make_report.
Logs: <study>/native/run.log, report-*.log; queue progress in this folder's native/queue.log."""
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

B = Path(r"C:\Users\hama101\Desktop\geek\ai trader\AAA EAs\BM Trading Robust Sets 2026-08-04")
QLOG = B / "ATR Touch Raw 2026-09-25" / "native" / "queue.log"
ENV = {**os.environ, "EA_STORE_DISABLE_MT5": "1", "PYTHONIOENCODING": "utf-8"}
STUDIES = [(a, b) for a, b in [("In Play ORB Raw 2026-09-25", "run_ip.py"), ("ATR Touch Raw 2026-09-25", "run_at.py")] if a.startswith(sys.argv[1] if len(sys.argv) > 1 else "")]


def log(msg: str) -> None:
    QLOG.parent.mkdir(parents=True, exist_ok=True)
    with QLOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}\n")


def run(folder: Path, args: list[str], out: str, append: bool = True) -> int:
    with (folder / "native" / out).open("a" if append else "w", encoding="utf-8") as f:
        return subprocess.run([sys.executable, *args], cwd=folder, env=ENV, stdout=f, stderr=subprocess.STDOUT,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).returncode


for name, runner in STUDIES:
    folder = B / name
    (folder / "native").mkdir(parents=True, exist_ok=True)
    log(f"START {name}")
    rc = run(folder, [runner, "screen", "summary"], "run.log")
    log(f"{name} screen exit {rc}")
    run(folder, ["make_report.py"], "report-screen.log", append=False)
    rc = run(folder, [runner, "confirm", "summary"], "run.log")
    log(f"{name} confirm exit {rc}")
    run(folder, ["make_report.py"], "report-final.log", append=False)
    log(f"DONE {name}")
log("QUEUE DONE")
