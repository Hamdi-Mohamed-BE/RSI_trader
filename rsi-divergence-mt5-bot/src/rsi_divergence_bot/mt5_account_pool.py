from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime
from multiprocessing import Process, Queue, get_context
from typing import Any

import pandas as pd

from .config import AppConfig
from .mt5_account_store import Mt5AccountRecord, Mt5AccountStore
from .mt5_account_worker import account_state_path, account_worker_main
from .mt5_client import MT5Client, _field
from .strategy import Signal
from .symbols import market_key
from .trader import Outcome


def _signal_to_dict(signal: Signal) -> dict:
    payload = asdict(signal)
    payload["time"] = signal.time.isoformat()
    return payload


def _aggregate_outcome(outcomes: list[str]) -> Outcome:
    priority = ("placed", "paper", "duplicate", "skipped")
    for item in priority:
        if item in outcomes:
            return item  # type: ignore[return-value]
    return "skipped"


class Mt5PoolReadClient:
    """Read-only MT5 facade that delegates to the primary account worker."""

    TRADE_DONE = MT5Client.TRADE_DONE

    def __init__(self, pool: Mt5AccountPool, config: AppConfig):
        self._pool = pool
        self.config = config.mt5

    def initialize(self) -> None:
        self._pool.ensure_started()
        status = self.connection_status()
        if not status.get("connected"):
            raise RuntimeError(status.get("error") or "MT5 primary account is not connected")

    def shutdown(self, force: bool = False) -> None:  # noqa: ARG002
        return None

    def connection_status(self) -> dict:
        response = self._pool.invoke_primary("connection_status", {}, timeout=30)
        if not response.get("ok"):
            return {"connected": False, "error": response.get("error") or "primary worker unavailable"}
        return response.get("result") or {"connected": False, "error": "empty status"}

    def rates(self, symbol: str, timeframe: str, bars: int) -> pd.DataFrame:
        return self._records_to_frame(
            self._pool.invoke_primary(
                "rates",
                {"symbol": symbol, "timeframe": timeframe, "bars": bars},
                timeout=120,
            )
        )

    def rates_range(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> pd.DataFrame:
        return self._records_to_frame(
            self._pool.invoke_primary(
                "rates_range",
                {"symbol": symbol, "timeframe": timeframe, "start": start.isoformat(), "end": end.isoformat()},
                timeout=180,
            )
        )

    def symbol_info(self, symbol: str):
        response = self._pool.invoke_primary("symbol_info", {"symbol": symbol}, timeout=30)
        if not response.get("ok"):
            raise RuntimeError(response.get("error") or "symbol_info request failed")
        return response.get("result")

    @staticmethod
    def _records_to_frame(response: dict) -> pd.DataFrame:
        if not response.get("ok"):
            raise RuntimeError(response.get("error") or "rates request failed")
        records = response.get("result") or []
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        df["time"] = pd.to_datetime(df["time"], utc=True)
        return df

    def tick(self, symbol: str) -> dict:
        response = self._pool.invoke_primary("tick", {"symbol": symbol}, timeout=30)
        if not response.get("ok"):
            raise RuntimeError(response.get("error") or "tick request failed")
        return response.get("result") or {}

    def positions(self) -> list:
        return self._pool.positions_for_targets()

    def account_snapshot(self) -> dict:
        response = self._pool.invoke_primary("account_snapshot", {}, timeout=30)
        if not response.get("ok"):
            raise RuntimeError(response.get("error") or "account snapshot failed")
        return response.get("result") or {}

    def realized_pnl_since(self, since: datetime) -> float:
        response = self._pool.invoke_primary(
            "realized_pnl_since",
            {"since": since.isoformat()},
            timeout=60,
        )
        if not response.get("ok"):
            raise RuntimeError(response.get("error") or "realized pnl request failed")
        return float(response.get("result") or 0.0)

    def live_snapshot(self, magic: int | None = None) -> dict:
        response = self._pool.invoke_primary("live_snapshot", {"magic": magic}, timeout=60)
        if not response.get("ok"):
            raise RuntimeError(response.get("error") or "live snapshot failed")
        return response.get("result") or {}


def mt5_path_warnings(accounts: list[Mt5AccountRecord], default_path: str | None = None) -> list[str]:
    enabled = [item for item in accounts if item.enabled]
    if len(enabled) <= 1:
        return []
    grouped: dict[str, list[str]] = {}
    path_labels: dict[str, str] = {}
    for account in enabled:
        raw_path = (account.mt5_path or default_path or "").strip()
        key = raw_path.casefold() if raw_path else "__default_terminal__"
        grouped.setdefault(key, []).append(account.name)
        path_labels[key] = raw_path or "default terminal"
    warnings: list[str] = []
    for key, names in grouped.items():
        if len(names) <= 1:
            continue
        label = path_labels[key]
        warnings.append(
            f"Accounts {', '.join(names)} share MT5 path '{label}'. "
            "Parallel mode needs one running terminal64.exe per account."
        )
    return warnings


class _WorkerHandle:
    def __init__(self, account_id: int, process: Process, cmd_queue: Queue):
        self.account_id = account_id
        self.process = process
        self.cmd_queue = cmd_queue
        self.connected = False
        self.last_error: str | None = None


class Mt5AccountPool:
    def __init__(
        self,
        store: Mt5AccountStore,
        config: AppConfig,
        runtime_dir,
        logger: logging.Logger,
    ):
        self.store = store
        self.config = config
        self.runtime_dir = runtime_dir
        self.logger = logger
        self._workers: dict[int, _WorkerHandle] = {}
        self._resp_queue: Queue = Queue()
        self._pending: dict[str, dict[str, Any]] = {}
        self._listener: threading.Thread | None = None
        self._lock = threading.RLock()
        self._started = False
        self._read_client: Mt5PoolReadClient | None = None
        self._ctx = get_context("spawn")
        self._worker_stagger_seconds = 5.0

    @property
    def active(self) -> bool:
        return bool(self.store.list_accounts())

    def read_client(self) -> Mt5PoolReadClient:
        if self._read_client is None:
            self._read_client = Mt5PoolReadClient(self, self.config)
        return self._read_client

    def ensure_started(self) -> None:
        with self._lock:
            if self._started:
                return
            self.start()

    def start(self) -> None:
        with self._lock:
            if not self.active or self._started:
                return
            if self._listener is None or not self._listener.is_alive():
                self._listener = threading.Thread(target=self._listen_responses, name="mt5-pool-listener", daemon=True)
                self._listener.start()
            self._started = True
            self._start_workers(self.store.enabled_accounts())

    def reload(self) -> None:
        with self._lock:
            if not self.active:
                self.stop()
                return
            enabled_ids = {account.id for account in self.store.enabled_accounts()}
            for account_id in list(self._workers):
                if account_id not in enabled_ids:
                    self._stop_worker(account_id)
            if self._listener is None or not self._listener.is_alive():
                self._listener = threading.Thread(target=self._listen_responses, name="mt5-pool-listener", daemon=True)
                self._listener.start()
            self._start_workers(self.store.enabled_accounts())
            self._started = True

    def stop(self) -> None:
        with self._lock:
            for account_id in list(self._workers):
                self._stop_worker(account_id)
            self._started = False

    def runtime_status(self) -> dict:
        enabled = self.store.enabled_accounts()
        workers = []
        for account_id, handle in sorted(self._workers.items()):
            alive = handle.process.is_alive()
            workers.append(
                {
                    "account_id": account_id,
                    "pid": handle.process.pid if alive else None,
                    "alive": alive,
                    "connected": handle.connected,
                    "error": handle.last_error,
                }
            )
        payload = self.store.runtime_payload()
        payload["workers"] = workers
        payload["pool_active"] = self.active
        payload["path_warnings"] = mt5_path_warnings(enabled, self.config.mt5.path)
        return payload

    def target_accounts(self) -> list[Mt5AccountRecord]:
        if not self.active:
            return []
        mode = self.store.trading_mode()
        if mode == "single":
            account_id = self.store.active_account_id()
            account = self.store.get_account(account_id) if account_id else None
            return [account] if account and account.enabled else []
        return self.store.enabled_accounts()

    def primary_account(self) -> Mt5AccountRecord | None:
        return self.store.primary_account()

    def invoke_primary(self, op: str, payload: dict | None = None, *, timeout: float = 60) -> dict:
        primary = self.primary_account()
        if primary is None:
            return {"ok": False, "error": "no primary account configured"}
        return self.invoke(primary.id, op, payload or {}, timeout=timeout)

    def invoke(self, account_id: int, op: str, payload: dict | None = None, *, timeout: float = 120) -> dict:
        self.ensure_started()
        return self._invoke_worker(account_id, op, payload or {}, timeout=timeout)

    def _invoke_worker(self, account_id: int, op: str, payload: dict, *, timeout: float) -> dict:
        handle = self._workers.get(account_id)
        if handle is None:
            account = self.store.get_account(account_id)
            if account is None or not account.enabled:
                return {"ok": False, "error": f"account {account_id} is not running"}
            self._ensure_worker(account)
            handle = self._workers.get(account_id)
        if handle is None:
            return {"ok": False, "error": f"failed to start worker for account {account_id}"}

        request_id = uuid.uuid4().hex
        event = threading.Event()
        with self._lock:
            self._pending[request_id] = {"event": event, "response": None}
        handle.cmd_queue.put({"request_id": request_id, "op": op, "payload": payload})
        if not event.wait(timeout):
            with self._lock:
                self._pending.pop(request_id, None)
            return {"ok": False, "error": f"timeout waiting for account {account_id} op={op}"}
        with self._lock:
            slot = self._pending.pop(request_id, None)
        if slot is None or slot.get("response") is None:
            return {"ok": False, "error": f"missing response for account {account_id} op={op}"}
        return slot["response"]

    def dispatch(self, op: str, payload: dict | None = None, *, parallel: bool = True, timeout: float = 120) -> list[dict]:
        targets = self.target_accounts()
        if not targets:
            return []
        if parallel and len(targets) > 1:
            results: list[dict] = []
            with ThreadPoolExecutor(max_workers=len(targets), thread_name_prefix="mt5-pool") as executor:
                futures = {
                    executor.submit(self.invoke, account.id, op, payload, timeout=timeout): account.id
                    for account in targets
                }
                for future in as_completed(futures):
                    try:
                        results.append(future.result())
                    except Exception as exc:  # noqa: BLE001
                        account_id = futures[future]
                        results.append({"ok": False, "error": str(exc), "account_id": account_id})
            return results
        return [self.invoke(account.id, op, payload or {}, timeout=timeout) for account in targets]

    def place_signal(self, signal: Signal) -> Outcome:
        if not self.active:
            raise RuntimeError("account pool is not active")
        responses = self.dispatch("place_signal", {"signal": _signal_to_dict(signal)}, parallel=True)
        outcomes: list[str] = []
        for response in responses:
            if not response.get("ok"):
                self.logger.warning("POOL place_signal account error: %s", response.get("error"))
                outcomes.append("skipped")
                continue
            result = response.get("result") or {}
            outcomes.append(str(result.get("outcome") or "skipped"))
        return _aggregate_outcome(outcomes)

    def place_market_setup(self, **kwargs) -> dict:
        if not self.active:
            raise RuntimeError("account pool is not active")
        responses = self.dispatch("place_market_setup", dict(kwargs), parallel=True)
        account_results = []
        placed_any = False
        primary_result: dict | None = None
        for response in responses:
            if not response.get("ok"):
                account_results.append({"status": "failed", "error": response.get("error")})
                continue
            result = response.get("result") or {}
            account_results.append(result)
            if result.get("status") == "placed":
                placed_any = True
                if primary_result is None:
                    primary_result = result
        if primary_result is None and account_results:
            primary_result = account_results[0]
        merged = dict(primary_result or {"status": "failed"})
        merged["account_results"] = account_results
        if placed_any:
            merged["status"] = "placed"
        return merged

    def manage_tp_protection(self, enabled: bool = True) -> None:
        if not self.active:
            return
        self.dispatch("manage_tp_protection", {"enabled": enabled}, parallel=True)

    def apply_breakeven(self, setup: dict) -> dict:
        if not self.active:
            return {"status": "skipped", "reason": "account pool is not active"}
        responses = self.dispatch("apply_breakeven", {"setup": setup}, parallel=True)
        for response in responses:
            if response.get("ok"):
                result = response.get("result") or {}
                if result.get("status") in {"applied", "ok", "placed"}:
                    return result
        first = responses[0] if responses else {"ok": False, "error": "no workers"}
        if first.get("ok"):
            return first.get("result") or {"status": "skipped"}
        return {"status": "failed", "error": first.get("error")}

    def positions_for_targets(self) -> list:
        positions: list = []
        for response in self.dispatch("positions", {}, parallel=True, timeout=30):
            if not response.get("ok"):
                continue
            positions.extend(response.get("result") or [])
        return positions

    def open_market_keys(self) -> set[str]:
        keys: set[str] = set()
        for pos in self.positions_for_targets():
            symbol = str(_field(pos, "symbol", ""))
            if symbol:
                keys.add(market_key(symbol))
        return keys

    def connection_status(self) -> dict:
        if not self.active:
            return {"connected": False, "error": "no configured accounts"}
        return self.read_client().connection_status()

    def _listen_responses(self) -> None:
        while True:
            try:
                message = self._resp_queue.get()
            except (EOFError, OSError):
                break
            if not isinstance(message, dict):
                continue
            request_id = str(message.get("request_id") or "")
            with self._lock:
                slot = self._pending.get(request_id)
                if slot is None:
                    continue
                slot["response"] = message
                slot["event"].set()

    def _start_workers(self, accounts: list[Mt5AccountRecord]) -> None:
        enabled = [item for item in accounts if item.enabled]
        for warning in mt5_path_warnings(enabled, self.config.mt5.path):
            self.logger.warning("MT5 POOL %s", warning)

        ordered: list[Mt5AccountRecord] = []
        primary = self.primary_account()
        if primary and primary.enabled:
            ordered.append(primary)
        for account in enabled:
            if account.id not in {item.id for item in ordered}:
                ordered.append(account)

        for index, account in enumerate(ordered):
            if index > 0:
                time.sleep(self._worker_stagger_seconds)
            self._ensure_worker(account)
            ready = self._wait_worker_ready(account.id, timeout=120)
            handle = self._workers.get(account.id)
            if handle is not None:
                handle.connected = ready
                if not ready and handle.last_error is None:
                    handle.last_error = "MT5 worker did not connect before timeout"

    def _wait_worker_ready(self, account_id: int, *, timeout: float = 120) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            handle = self._workers.get(account_id)
            if handle is None or not handle.process.is_alive():
                if handle is not None and handle.last_error:
                    return False
                time.sleep(0.5)
                continue
            response = self._invoke_worker(account_id, "connection_status", {}, timeout=30)
            if response.get("ok") and (response.get("result") or {}).get("connected"):
                if handle is not None:
                    handle.last_error = None
                return True
            error = response.get("error") or (response.get("result") or {}).get("error")
            if handle is not None and error:
                handle.last_error = str(error)
            time.sleep(2)
        return False

    def _ensure_worker(self, account: Mt5AccountRecord) -> None:
        existing = self._workers.get(account.id)
        if existing is not None and existing.process.is_alive():
            return
        if existing is not None:
            self._workers.pop(account.id, None)
        cmd_queue = self._ctx.Queue()
        process = self._ctx.Process(
            target=account_worker_main,
            args=(
                account.to_worker_dict(),
                self.config.model_dump(mode="python"),
                account_state_path(self.runtime_dir, account.id),
                cmd_queue,
                self._resp_queue,
            ),
            name=f"mt5-account-{account.id}",
            daemon=True,
        )
        process.start()
        self._workers[account.id] = _WorkerHandle(account.id, process, cmd_queue)
        self.logger.warning(
            "MT5 POOL worker started account_id=%s name=%s login=%s path=%s suffix=%s pid=%s",
            account.id,
            account.name,
            account.login,
            account.mt5_path or self.config.mt5.path or "default",
            account.symbol_suffix or "",
            process.pid,
        )

    def _stop_worker(self, account_id: int) -> None:
        handle = self._workers.pop(account_id, None)
        if handle is None:
            return
        try:
            handle.cmd_queue.put({"request_id": "shutdown", "op": "shutdown", "payload": {}})
        except Exception:  # noqa: BLE001
            pass
        handle.process.join(timeout=5)
        if handle.process.is_alive():
            handle.process.terminate()
            handle.process.join(timeout=2)
        self.logger.info("MT5 POOL worker stopped account_id=%s", account_id)
