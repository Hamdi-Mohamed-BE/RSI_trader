from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from .automation import HEARTBEAT_PATH as LTA_HEARTBEAT, MAGIC_NUMBER as LTA_MAGIC
from .bpr_bot import BPR_MAGIC, HEARTBEAT_PATH as BPR_HEARTBEAT
from .challenge_20pip import CHALLENGE_MAGIC, HEARTBEAT_PATH as CHALLENGE_HEARTBEAT
from .config import PROJECT_ROOT, REPORTS_DIR, load_config
from .orb_bot import HEARTBEAT_PATH as ORB_HEARTBEAT, ORB_MAGIC
from .telegram_signaler import HEARTBEAT_PATH as TELEGRAM_SIGNALER_HEARTBEAT


SNIPER_ROOT = PROJECT_ROOT.parent / "sniper entry"
BOT_CONTROL_DIR = REPORTS_DIR / "bot_control"
BOT_CONTROL_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class BotDefinition:
    bot_id: str
    name: str
    group: str
    command: tuple[str, ...]
    heartbeat: Path | None
    magic: int | None
    description: str
    experimental: bool = False


def python_exe() -> str:
    local = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if local.exists():
        return str(local)
    return sys.executable


def bot_definitions() -> dict[str, BotDefinition]:
    py = python_exe()
    definitions = {
        "telegram": BotDefinition(
            bot_id="telegram",
            name="Telegram Trade Signaler",
            group="service",
            command=(py, "-m", "app.telegram_signaler"),
            heartbeat=TELEGRAM_SIGNALER_HEARTBEAT,
            magic=None,
            description="Read-only MT5 watcher that posts chart signals and threaded trade updates.",
        ),
        "lta": BotDefinition(
            bot_id="lta",
            name="LTA A+ Bot",
            group="production",
            command=(py, "-m", "app.automation"),
            heartbeat=LTA_HEARTBEAT,
            magic=LTA_MAGIC,
            description="Book-based A+ setup engine with pre-place orders and TP1 protection.",
        ),
        "orb": BotDefinition(
            bot_id="orb",
            name="ORB Bot",
            group="production",
            command=(py, "-m", "app.orb_bot"),
            heartbeat=ORB_HEARTBEAT,
            magic=ORB_MAGIC,
            description="New York opening-range breakout engine.",
        ),
        "20pip": BotDefinition(
            bot_id="20pip",
            name="20 Pip Challenge",
            group="challenge",
            command=(py, "-m", "app.challenge_20pip"),
            heartbeat=CHALLENGE_HEARTBEAT,
            magic=CHALLENGE_MAGIC,
            description="Original aggressive challenge bank engine.",
        ),
        "bpr": BotDefinition(
            bot_id="bpr",
            name="BPR Bot",
            group="production",
            command=(py, "-m", "app.bpr_bot"),
            heartbeat=BPR_HEARTBEAT,
            magic=BPR_MAGIC,
            description="Balanced Price Range retest engine built from overlapping opposite FVGs.",
        ),
    }
    if SNIPER_ROOT.exists():
        definitions["sniper"] = BotDefinition(
            bot_id="sniper",
            name="Sniper Bot",
            group="production",
            command=(py, str(SNIPER_ROOT / "sniper_entry_bot.py")),
            heartbeat=SNIPER_ROOT / "state" / "sniper_state_H4_optimized.json",
            magic=26061515,
            description="BTCUSD H4 sniper entry with ATR stop and TP1 protection.",
        )
    return definitions


def _read_json(path: Path | None) -> dict[str, Any] | None:
    if not path or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _heartbeat_status(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {"state": "stopped", "age_seconds": None, "updated_at": None}
    age = max(0.0, time.time() - path.stat().st_mtime)
    data = _read_json(path) or {}
    state = "running" if age < 180 else "stale"
    return {
        "state": state,
        "age_seconds": round(age, 1),
        "updated_at": data.get("updated_at") or data.get("time") or data.get("created_at"),
        "payload": data,
    }


def bot_statuses() -> list[dict[str, Any]]:
    statuses = []
    for definition in bot_definitions().values():
        item = asdict(definition)
        item["command"] = " ".join(definition.command)
        item["heartbeat"] = str(definition.heartbeat) if definition.heartbeat else None
        item["status"] = _heartbeat_status(definition.heartbeat)
        statuses.append(item)
    return sorted(statuses, key=lambda item: (item["group"], item["name"]))


def start_bot(bot_id: str) -> dict[str, Any]:
    definitions = bot_definitions()
    if bot_id not in definitions:
        return {"ok": False, "message": f"Unknown bot: {bot_id}"}
    definition = definitions[bot_id]
    command = subprocess.list2cmdline(definition.command)
    shell_line = f'cd /d "{PROJECT_ROOT}" && title {definition.name} && {command}'
    creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    subprocess.Popen(
        ["cmd.exe", "/k", shell_line],
        cwd=str(PROJECT_ROOT),
        close_fds=True,
        creationflags=creationflags,
    )
    return {"ok": True, "message": f"{definition.name} start requested in a visible console."}


def stop_bot(bot_id: str) -> dict[str, Any]:
    definitions = bot_definitions()
    if bot_id not in definitions:
        return {"ok": False, "message": f"Unknown bot: {bot_id}"}
    definition = definitions[bot_id]
    fragments = [part for part in definition.command if part not in {python_exe(), sys.executable}]
    pattern = "*".join(fragments[-3:]) if fragments else definition.bot_id
    ps = (
        "$pattern = " + repr(f"*{pattern}*") + "; "
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -match 'python|cmd' -and $_.CommandLine -like $pattern } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; $_.ProcessId }"
    )
    result = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    stopped = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return {
        "ok": result.returncode == 0,
        "message": f"{definition.name} stop requested.",
        "stopped_processes": stopped,
        "stderr": result.stderr.strip(),
    }


def latest_report_file(pattern: str, root: Path = REPORTS_DIR) -> Path | None:
    matches = sorted(root.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def load_latest_reports() -> dict[str, Any]:
    reports: dict[str, Any] = {}
    dynamic = latest_report_file("dynamic_exit_backtest/*/dynamic_exit_backtest_report.json")
    combined = latest_report_file("dynamic_exit_backtest/*/combined_live_like_5mo_report.json")
    challenge = latest_report_file("20pip_challenge_backtest/*/orb_challenge_backtest_report.json")
    bpr = latest_report_file("bpr_backtest/*/bpr_backtest_report.json")
    sniper = latest_report_file("reports/sniper_backtest/*/sniper_backtest_report.json", root=SNIPER_ROOT) if SNIPER_ROOT.exists() else None
    for key, path in {"lta_orb": dynamic, "combined": combined, "challenge20": challenge, "bpr": bpr, "sniper": sniper}.items():
        if path and path.exists():
            try:
                reports[key] = json.loads(path.read_text(encoding="utf-8"))
                reports[key]["path"] = str(path)
            except Exception as exc:
                reports[key] = {"error": str(exc), "path": str(path)}
    return reports


def daily_trade_history(days: int = 7) -> dict[str, Any]:
    try:
        import MetaTrader5 as mt5  # type: ignore
    except Exception as exc:
        return {"ok": False, "message": f"MetaTrader5 package unavailable: {exc}", "trades": []}
    config = load_config()
    path = os.getenv("MT5_TERMINAL_PATH")
    ok = mt5.initialize(path=path) if path else mt5.initialize()
    if not ok:
        return {"ok": False, "message": f"MT5 initialize failed: {mt5.last_error()}", "trades": []}
    magic_to_bot = {
        LTA_MAGIC: "LTA",
        ORB_MAGIC: "ORB",
        CHALLENGE_MAGIC: "20pip",
        BPR_MAGIC: "BPR",
        26061515: "Sniper",
    }
    try:
        end = datetime.now()
        start = end - timedelta(days=max(1, int(days)))
        deals = mt5.history_deals_get(start, end) or []
        rows = []
        for deal in deals:
            item = deal._asdict()
            magic = int(item.get("magic") or 0)
            comment = str(item.get("comment") or "")
            bot = magic_to_bot.get(magic)
            if bot is None:
                upper = comment.upper()
                if "BPR" in upper:
                    bot = "BPR"
                else:
                    continue
            rows.append(
                {
                    "time": datetime.fromtimestamp(int(item.get("time") or 0)).isoformat(sep=" ", timespec="seconds"),
                    "bot": bot,
                    "symbol": item.get("symbol"),
                    "type": item.get("type"),
                    "entry": item.get("entry"),
                    "volume": item.get("volume"),
                    "price": item.get("price"),
                    "profit": round(float(item.get("profit") or 0.0) + float(item.get("commission") or 0.0) + float(item.get("swap") or 0.0), 2),
                    "magic": magic,
                    "comment": comment,
                    "ticket": item.get("ticket"),
                    "order": item.get("order"),
                }
            )
        rows.sort(key=lambda item: item["time"], reverse=True)
        by_day: dict[str, dict[str, Any]] = {}
        for row in rows:
            day = str(row["time"])[:10]
            bucket = by_day.setdefault(day, {"day": day, "trades": 0, "profit": 0.0, "bots": {}})
            bucket["trades"] += 1
            bucket["profit"] = round(float(bucket["profit"]) + float(row["profit"]), 2)
            bot_bucket = bucket["bots"].setdefault(row["bot"], {"trades": 0, "profit": 0.0})
            bot_bucket["trades"] += 1
            bot_bucket["profit"] = round(float(bot_bucket["profit"]) + float(row["profit"]), 2)
        return {"ok": True, "starting_balance": config.starting_balance, "trades": rows[:300], "by_day": list(by_day.values())}
    finally:
        mt5.shutdown()


def dashboard_summary() -> dict[str, Any]:
    reports = load_latest_reports()
    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "config": asdict(load_config()),
        "bots": bot_statuses(),
        "reports": reports,
        "suite_configs": {},
        "daily": daily_trade_history(days=14),
    }
