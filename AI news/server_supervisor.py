from __future__ import annotations

import ctypes
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TMP = ROOT / "tmp"
HEALTH_URL = os.getenv("GOLD_NEWS_HEALTH_URL", "http://127.0.0.1:8799/api/health")
PORT = os.getenv("APP_PORT", "8799")
CHECK_SECONDS = 5.0
MAX_FAILED_CHECKS = 3
MUTEX_NAME = "Local\\GoldNewsV9PredictionServerSupervisor"


def _stamp(message: str) -> str:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return f"{now} {message}\n"


def _healthy() -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
            bridge = payload.get("mt5_file_bridge", {})
            return (
                response.status == 200
                and payload.get("status") == "ok"
                and bridge.get("status") in {"starting", "ready"}
            )
    except (OSError, ValueError, urllib.error.URLError):
        return False


def _single_instance() -> bool:
    if os.name != "nt":
        return True
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not handle:
        return False
    return ctypes.windll.kernel32.GetLastError() != 183


def main() -> int:
    if not _single_instance():
        return 0

    TMP.mkdir(parents=True, exist_ok=True)
    supervisor_log = TMP / "gold-news-v9-supervisor.log"
    server_out = TMP / "gold-news-v9-server.out.log"
    server_err = TMP / "gold-news-v9-server.err.log"
    stopping = False
    child: subprocess.Popen[bytes] | None = None

    def request_stop(*_: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    with supervisor_log.open("a", encoding="utf-8") as log:
        log.write(_stamp("supervisor started"))
        log.flush()
        while not stopping:
            if child is None or child.poll() is not None:
                if child is not None:
                    log.write(_stamp(f"server exited with code {child.returncode}; restarting"))
                    log.flush()
                out_handle = server_out.open("ab")
                err_handle = server_err.open("ab")
                child = subprocess.Popen(
                    [
                        sys.executable,
                        "-u",
                        "-m",
                        "uvicorn",
                        "app:app",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        PORT,
                    ],
                    cwd=ROOT,
                    stdout=out_handle,
                    stderr=err_handle,
                )
                out_handle.close()
                err_handle.close()
                log.write(_stamp(f"server started with pid {child.pid}"))
                log.flush()

            failed_checks = 0
            while not stopping and child.poll() is None:
                if _healthy():
                    failed_checks = 0
                else:
                    failed_checks += 1
                    if failed_checks >= MAX_FAILED_CHECKS:
                        log.write(_stamp("server health failed three times; restarting"))
                        log.flush()
                        child.terminate()
                        try:
                            child.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            child.kill()
                            child.wait(timeout=5)
                        break
                time.sleep(CHECK_SECONDS)

            if not stopping:
                time.sleep(2)

        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
        log.write(_stamp("supervisor stopped"))
        log.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
