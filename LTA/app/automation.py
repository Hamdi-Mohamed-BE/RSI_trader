from __future__ import annotations

import argparse
import atexit
from datetime import datetime, timedelta
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from .config import REPORTS_DIR, load_config
from .models import TRADE_SYMBOLS
from .mt5_client import MT5Client
from .scanner import DEFAULT_SCAN_TIMEFRAMES, scan_market


AUTOMATION_DIR = REPORTS_DIR / "automation"
LATEST_SCAN_PATH = AUTOMATION_DIR / "latest_scan.json"
PREPARED_ORDERS_PATH = AUTOMATION_DIR / "prepared_orders.jsonl"
PLACED_ORDERS_PATH = AUTOMATION_DIR / "placed_orders.jsonl"
SEEN_SIGNALS_PATH = AUTOMATION_DIR / "seen_signals.json"
TRADE_STATE_PATH = AUTOMATION_DIR / "trade_state.json"
BLOCKED_ORDERS_PATH = AUTOMATION_DIR / "blocked_orders.jsonl"
INSTANCE_LOCK_PATH = AUTOMATION_DIR / "automation.lock"
HEARTBEAT_PATH = AUTOMATION_DIR / "automation_heartbeat.json"
MAGIC_NUMBER = 27032024


def _env_bool(name: str, default: bool) -> bool:
    import os

    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    import os

    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_list(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    import os

    value = os.getenv(name)
    if not value:
        return default
    return tuple(item.strip().upper() for item in value.split(",") if item.strip())


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _heartbeat_is_fresh(max_age_seconds: int) -> bool:
    if not HEARTBEAT_PATH.exists():
        return False
    age = time.time() - HEARTBEAT_PATH.stat().st_mtime
    return age <= max_age_seconds


def _write_heartbeat(status: str = "running") -> None:
    _write_json(
        HEARTBEAT_PATH,
        {
            "pid": os.getpid(),
            "status": status,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        },
    )


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str) + "\n")


def _read_seen_signals() -> dict[str, str]:
    if not SEEN_SIGNALS_PATH.exists():
        return {}
    try:
        data = json.loads(SEEN_SIGNALS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _write_seen_signals(seen: dict[str, str]) -> None:
    SEEN_SIGNALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEEN_SIGNALS_PATH.write_text(json.dumps(seen, indent=2), encoding="utf-8")


def _default_trade_state() -> dict[str, Any]:
    return {"consumed_signals": {}, "last_updated": None}


def _read_trade_state() -> dict[str, Any]:
    if not TRADE_STATE_PATH.exists():
        return _default_trade_state()
    try:
        data = json.loads(TRADE_STATE_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _default_trade_state()
        data.setdefault("consumed_signals", {})
        return data
    except json.JSONDecodeError:
        return _default_trade_state()


def _write_trade_state(state: dict[str, Any]) -> None:
    state["last_updated"] = datetime.now().isoformat(timespec="seconds")
    TRADE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRADE_STATE_PATH.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def _signal_key(signal: dict[str, Any]) -> str:
    return "|".join(
        [
            str(signal.get("symbol")),
            str(signal.get("timeframe")),
            str(signal.get("direction")),
            str(signal.get("key_level")),
            str(signal.get("entry_model")),
            str(signal.get("last_candle_time") or signal.get("timestamp")),
        ]
    )


def _legacy_signal_key(signal: dict[str, Any]) -> str:
    return "|".join(
        [
            str(signal.get("symbol")),
            str(signal.get("timeframe")),
            str(signal.get("direction")),
            str(signal.get("key_level")),
            str(signal.get("entry_model")),
        ]
    )


def _migrate_placed_orders_to_state(state: dict[str, Any]) -> None:
    consumed = state.setdefault("consumed_signals", {})
    if not PLACED_ORDERS_PATH.exists():
        return
    with PLACED_ORDERS_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            signal = payload.get("signal") or {}
            if not signal:
                continue
            for key in (_signal_key(signal), _legacy_signal_key(signal)):
                consumed.setdefault(
                    key,
                    {
                        "status": "placed_before_state_tracking",
                        "created_at": payload.get("created_at"),
                        "symbol": signal.get("symbol"),
                        "timeframe": signal.get("timeframe"),
                        "direction": signal.get("direction"),
                        "key_level": signal.get("key_level"),
                        "last_candle_time": signal.get("last_candle_time") or signal.get("timestamp"),
                    },
                )


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _other_automation_pids() -> list[int]:
    command = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.ExecutablePath -like '*python.exe' -and $_.CommandLine -like '*-m app.automation*' } | "
        "Select-Object -ExpandProperty ProcessId"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return []
    current_pid = os.getpid()
    pids: list[int] = []
    for line in result.stdout.splitlines():
        try:
            pid = int(line.strip())
        except ValueError:
            continue
        if pid != current_pid:
            pids.append(pid)
    return pids


class SingleInstanceLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.acquired = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stale_seconds = _env_int("AUTO_LOCK_STALE_SECONDS", 180)
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                pid = int(data.get("pid") or 0)
            except (json.JSONDecodeError, ValueError):
                pid = 0
            if _pid_is_running(pid) or _heartbeat_is_fresh(stale_seconds):
                raise RuntimeError("Automation worker is already running or heartbeat is still fresh.")
            self.path.unlink(missing_ok=True)

        self.path.write_text(
            json.dumps({"pid": os.getpid(), "started_at": datetime.now().isoformat(timespec="seconds")}, indent=2),
            encoding="utf-8",
        )
        self.acquired = True
        atexit.register(self.release)

    def release(self) -> None:
        if self.acquired:
            _write_heartbeat("stopped")
            self.path.unlink(missing_ok=True)
            self.acquired = False


class TradeAutomation:
    def __init__(self) -> None:
        self.config = load_config()
        self.client = MT5Client()
        self.timeframes = _env_list("AUTO_SCAN_TIMEFRAMES", DEFAULT_SCAN_TIMEFRAMES)
        self.interval_seconds = _env_int("AUTO_SCAN_INTERVAL_SECONDS", 60)
        self.cooldown_minutes = _env_int("AUTO_SIGNAL_COOLDOWN_MINUTES", 120)
        self.auto_place_trades = _env_bool("AUTO_PLACE_TRADES", False)
        self.one_position_per_symbol = _env_bool("AUTO_ONE_POSITION_PER_SYMBOL", True)
        self.seen: dict[str, datetime] = {
            key: datetime.fromisoformat(value) for key, value in _read_seen_signals().items()
        }
        self.trade_state = _read_trade_state()
        _migrate_placed_orders_to_state(self.trade_state)
        _write_trade_state(self.trade_state)

    def lot_for_symbol(self, symbol: str) -> float:
        return float(self.config.symbol_lots.get(symbol, 0.01))

    def _cooldown_active(self, key: str, now: datetime) -> bool:
        seen_at = self.seen.get(key)
        if not seen_at:
            return False
        return now - seen_at < timedelta(minutes=self.cooldown_minutes)

    def _mark_consumed(self, signal: dict[str, Any], ticket: dict[str, Any], placement: dict[str, Any] | None) -> None:
        consumed = self.trade_state.setdefault("consumed_signals", {})
        payload = {
            "status": "placed",
            "created_at": ticket.get("created_at"),
            "symbol": signal.get("symbol"),
            "broker_symbol": signal.get("broker_symbol"),
            "timeframe": signal.get("timeframe"),
            "direction": signal.get("direction"),
            "key_level": signal.get("key_level"),
            "entry_model": signal.get("entry_model"),
            "last_candle_time": signal.get("last_candle_time") or signal.get("timestamp"),
            "placement": placement,
        }
        consumed[_signal_key(signal)] = payload
        consumed[_legacy_signal_key(signal)] = payload
        _write_trade_state(self.trade_state)

    def run_once(self) -> dict[str, Any]:
        now = datetime.now()
        _write_heartbeat("scanning")
        scan = scan_market(
            symbols=TRADE_SYMBOLS,
            timeframes=self.timeframes,
            min_score=self.config.min_setup_score,
            min_rr=self.config.min_risk_reward,
        )
        prepared: list[dict[str, Any]] = []
        placed: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []

        for signal in scan["allowed"]:
            key = _signal_key(signal)
            legacy_key = _legacy_signal_key(signal)
            open_positions_any = self.client.open_positions(signal["symbol"])
            open_positions_magic = self.client.open_positions(signal["symbol"], magic=MAGIC_NUMBER)
            block_reasons: list[str] = []

            if key in self.trade_state.get("consumed_signals", {}) or legacy_key in self.trade_state.get("consumed_signals", {}):
                block_reasons.append("This signal was already placed and saved in trade_state.json.")
            if self._cooldown_active(key, now) or self._cooldown_active(legacy_key, now):
                block_reasons.append("Signal is still inside the cooldown window.")
            if self.one_position_per_symbol and open_positions_any:
                block_reasons.append("An open position already exists on this symbol.")
            elif open_positions_magic:
                block_reasons.append("An open LTA automation position already exists on this symbol.")

            if block_reasons:
                blocked_ticket = {
                    "created_at": now.isoformat(timespec="seconds"),
                    "status": "blocked_duplicate_or_open_position",
                    "duplicate_key": key,
                    "legacy_key": legacy_key,
                    "setup_score": signal.get("setup_score"),
                    "setup_grade": signal.get("setup_grade"),
                    "signal": signal,
                    "reasons": block_reasons,
                    "safety": {
                        "open_positions_same_symbol_any": len(open_positions_any),
                        "open_positions_same_symbol_magic": len(open_positions_magic),
                        "one_position_per_symbol": self.one_position_per_symbol,
                    },
                }
                blocked.append(blocked_ticket)
                _append_jsonl(BLOCKED_ORDERS_PATH, blocked_ticket)
                continue

            lot = self.lot_for_symbol(signal["symbol"])
            order = self.client.prepare_order(
                signal,
                lot=lot,
                live_trading=self.config.live_trading and self.auto_place_trades,
            )
            ticket = {
                "created_at": now.isoformat(timespec="seconds"),
                "status": "prepared",
                "duplicate_key": key,
                "legacy_key": legacy_key,
                "setup_score": signal.get("setup_score"),
                "setup_grade": signal.get("setup_grade"),
                "signal": signal,
                "order": order,
                "safety": {
                    "live_trading": self.config.live_trading,
                    "auto_place_trades": self.auto_place_trades,
                    "open_positions_same_symbol_any": len(open_positions_any),
                    "open_positions_same_symbol_magic": len(open_positions_magic),
                    "one_position_per_symbol": self.one_position_per_symbol,
                    "will_send_to_mt5": self.config.live_trading and self.auto_place_trades,
                },
            }
            prepared.append(ticket)
            _append_jsonl(PREPARED_ORDERS_PATH, ticket)
            self.seen[key] = now
            self.seen[legacy_key] = now
            _write_seen_signals({item_key: item_value.isoformat() for item_key, item_value in self.seen.items()})

            if self.config.live_trading and self.auto_place_trades:
                placement = self.client.place_order(order)
                placed_payload = {**ticket, "status": "sent_to_mt5", "placement": placement}
                placed.append(placed_payload)
                _append_jsonl(PLACED_ORDERS_PATH, placed_payload)
                if placement.get("placed"):
                    self._mark_consumed(signal, ticket, placement)

        payload = {
            "checked_at": now.isoformat(timespec="seconds"),
            "interval_seconds": self.interval_seconds,
            "timeframes": list(self.timeframes),
            "lots": {symbol: self.lot_for_symbol(symbol) for symbol in TRADE_SYMBOLS},
            "live_trading": self.config.live_trading,
            "auto_place_trades": self.auto_place_trades,
            "one_position_per_symbol": self.one_position_per_symbol,
            "prepared_count": len(prepared),
            "placed_count": len(placed),
            "blocked_count": len(blocked),
            "prepared": prepared,
            "placed": placed,
            "blocked": blocked,
            "scan": scan,
        }
        _write_json(LATEST_SCAN_PATH, payload)
        _write_heartbeat("waiting")
        return payload

    def run_forever(self) -> None:
        print("LTA automation worker started.")
        print(f"Scanning {', '.join(TRADE_SYMBOLS)} on {', '.join(self.timeframes)} every {self.interval_seconds}s.")
        print(f"Lots: XAUUSD={self.lot_for_symbol('XAUUSD')}, XAGUSD={self.lot_for_symbol('XAGUSD')}, BTCUSD={self.lot_for_symbol('BTCUSD')}")
        print(f"Live trading: {self.config.live_trading}; AUTO_PLACE_TRADES: {self.auto_place_trades}")
        print(f"One position per symbol: {self.one_position_per_symbol}")
        print("Press Ctrl+C to stop.")
        while True:
            payload = self.run_once()
            allowed = len(payload["scan"]["allowed"])
            near = len(payload["scan"]["near_misses"])
            prepared = payload["prepared_count"]
            print(
                f"[{payload['checked_at']}] A+={allowed} near={near} prepared={prepared} placed={payload['placed_count']} blocked={payload['blocked_count']}"
            )
            time.sleep(self.interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="LTA A+ setup automation worker.")
    parser.add_argument("--once", action="store_true", help="Run one scan and exit.")
    args = parser.parse_args()

    lock = SingleInstanceLock(INSTANCE_LOCK_PATH)
    lock.acquire()
    worker = TradeAutomation()
    if args.once:
        payload = worker.run_once()
        print(json.dumps(payload, indent=2, default=str))
        return
    worker.run_forever()


if __name__ == "__main__":
    main()
