from __future__ import annotations

import logging
import threading
import traceback
from dataclasses import asdict
from datetime import datetime
from typing import Any

import pandas as pd

from .config import AppConfig, MT5Config
from .mt5_account_ops import handle_account_operation
from .mt5_account_store import Mt5AccountRecord, Mt5AccountStore
from .mt5_account_worker import account_state_path
from .mt5_client import MT5Client, _field
from .state import StateStore
from .strategy import Signal
from .symbols import market_key
from .trader import Outcome, TradeExecutor


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
    """Read-only MT5 facade backed by the primary account session."""

    TRADE_DONE = MT5Client.TRADE_DONE

    def __init__(self, pool: Mt5AccountPool, config: AppConfig):
        self._pool = pool
        self.config = config.mt5

    def initialize(self) -> None:
        self._pool.ensure_primary_session()
        status = self.connection_status()
        if not status.get("connected"):
            raise RuntimeError(status.get("error") or "MT5 primary account is not connected")

    def shutdown(self, force: bool = False) -> None:  # noqa: ARG002
        return None

    def connection_status(self) -> dict:
        return self._pool.connection_status()

    def _primary_op(self, op: str, payload: dict | None = None, *, timeout: float = 60) -> dict:
        return self._pool.invoke_primary(op, payload or {}, timeout=timeout)

    def rates(self, symbol: str, timeframe: str, bars: int) -> pd.DataFrame:
        return self._records_to_frame(
            self._primary_op("rates", {"symbol": symbol, "timeframe": timeframe, "bars": bars}, timeout=120)
        )

    def rates_range(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> pd.DataFrame:
        return self._records_to_frame(
            self._primary_op(
                "rates_range",
                {"symbol": symbol, "timeframe": timeframe, "start": start.isoformat(), "end": end.isoformat()},
                timeout=180,
            )
        )

    def symbol_info(self, symbol: str):
        response = self._primary_op("symbol_info", {"symbol": symbol}, timeout=30)
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
        response = self._primary_op("tick", {"symbol": symbol}, timeout=30)
        if not response.get("ok"):
            raise RuntimeError(response.get("error") or "tick request failed")
        return response.get("result") or {}

    def positions(self) -> list:
        return self._pool.positions_for_targets()

    def account_snapshot(self) -> dict:
        response = self._primary_op("account_snapshot", {}, timeout=30)
        if not response.get("ok"):
            raise RuntimeError(response.get("error") or "account snapshot failed")
        return response.get("result") or {}

    def realized_pnl_since(self, since: datetime) -> float:
        response = self._primary_op("realized_pnl_since", {"since": since.isoformat()}, timeout=60)
        if not response.get("ok"):
            raise RuntimeError(response.get("error") or "realized pnl request failed")
        return float(response.get("result") or 0.0)

    def live_snapshot(self, magic: int | None = None) -> dict:
        response = self._primary_op("live_snapshot", {"magic": magic}, timeout=60)
        if not response.get("ok"):
            raise RuntimeError(response.get("error") or "live snapshot failed")
        return response.get("result") or {}


def mt5_path_warnings(accounts: list[Mt5AccountRecord], default_path: str | None = None) -> list[str]:
    enabled = [item for item in accounts if item.enabled]
    if len(enabled) <= 1:
        return []
    paths = {
        (account.mt5_path or default_path or "").strip() or "__default_terminal__"
        for account in enabled
    }
    if len(paths) <= 1:
        return []
    return [
        "Multiple MT5 terminal paths configured. Sequential mode switches terminal only when paths differ."
    ]


class _AccountSessionState:
    def __init__(self) -> None:
        self.connected = False
        self.last_error: str | None = None
        self.last_ok_at: str | None = None


class Mt5AccountPool:
    """Single MT5 terminal session — logs into each account sequentially when trading."""

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
        self._lock = threading.RLock()
        self._started = False
        self._read_client: Mt5PoolReadClient | None = None
        self._client = MT5Client(config.mt5)
        self._executors: dict[int, TradeExecutor] = {}
        self._account_status: dict[int, _AccountSessionState] = {}
        self._active_account_id: int | None = None
        self._terminal_ready = False

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
            self._started = True
            self.logger.warning(
                "MT5 POOL sequential mode enabled accounts=%s — terminal only at startup; "
                "accounts login one-by-one when trades are placed",
                len(self.store.enabled_accounts()),
            )
            try:
                self._ensure_terminal()
            except Exception as exc:  # noqa: BLE001
                self.logger.warning("MT5 POOL terminal init deferred: %s", exc)

    def reload(self) -> None:
        with self._lock:
            if not self.active:
                self._reset_session()
                return
            stale_ids = set(self._executors) - {account.id for account in self.store.list_accounts()}
            for account_id in stale_ids:
                self._executors.pop(account_id, None)
                self._account_status.pop(account_id, None)
            self._started = True

    def stop(self) -> None:
        with self._lock:
            self._reset_session()

    def _reset_session(self) -> None:
        self._started = False
        self._terminal_ready = False
        self._active_account_id = None
        try:
            self._client.shutdown(force=True)
        except Exception:  # noqa: BLE001
            pass

    def runtime_status(self) -> dict:
        enabled = self.store.enabled_accounts()
        workers = []
        for account in sorted(enabled, key=lambda item: item.id):
            state = self._account_status.get(account.id, _AccountSessionState())
            workers.append(
                {
                    "account_id": account.id,
                    "pid": None,
                    "alive": self._started,
                    "connected": state.connected,
                    "error": state.last_error,
                    "last_ok_at": state.last_ok_at,
                    "active": self._active_account_id == account.id,
                }
            )
        payload = self.store.runtime_payload()
        payload["workers"] = workers
        payload["pool_active"] = self.active
        payload["session_mode"] = "sequential"
        payload["active_account_id_session"] = self._active_account_id
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

    def connected_accounts(self) -> list[Mt5AccountRecord]:
        return [account for account in self.target_accounts() if self._account_status.get(account.id, _AccountSessionState()).connected]

    def primary_account(self) -> Mt5AccountRecord | None:
        return self.store.primary_account()

    def ensure_primary_session(self) -> None:
        primary = self.primary_account()
        if primary is None or not primary.enabled:
            raise RuntimeError("no primary account configured")
        with self._lock:
            self._ensure_terminal()
            if self._active_account_id != primary.id:
                self._switch_to_account(primary)

    def _account_mt5_config(self, account: Mt5AccountRecord) -> MT5Config:
        return self.config.mt5.model_copy(
            update={
                "login": int(account.login),
                "password": str(account.password),
                "server": str(account.server),
                "path": account.mt5_path or self.config.mt5.path,
                "broker_symbol_suffix": str(account.symbol_suffix or ""),
            }
        )

    def _executor_for(self, account: Mt5AccountRecord) -> TradeExecutor:
        existing = self._executors.get(account.id)
        if existing is not None:
            return existing
        state = StateStore(account_state_path(self.runtime_dir, account.id))
        executor = TradeExecutor(self.config, self._client, state, self.logger)
        self._executors[account.id] = executor
        return executor

    def _status_for(self, account_id: int) -> _AccountSessionState:
        state = self._account_status.get(account_id)
        if state is None:
            state = _AccountSessionState()
            self._account_status[account_id] = state
        return state

    def _ensure_terminal(self) -> None:
        if self._terminal_ready:
            return
        base_cfg = self.config.mt5.model_copy(update={"login": None, "password": None, "server": None})
        self._client.config = base_cfg
        self._client.connection_key = self._client._connection_key_for(base_cfg)
        self._client.initialize_terminal()
        self._terminal_ready = True
        self.logger.info("MT5 POOL terminal ready path=%s", base_cfg.path or "default")

    def _switch_to_account(self, account: Mt5AccountRecord) -> None:
        mt5_cfg = self._account_mt5_config(account)
        self.logger.warning(
            "MT5 POOL login account_id=%s name=%s login=%s server=%s path=%s suffix=%s",
            account.id,
            account.name,
            account.login,
            account.server,
            mt5_cfg.path or "default",
            account.symbol_suffix or "",
        )
        self._client.switch_account(mt5_cfg)
        self._active_account_id = account.id

    def _restore_primary_session(self) -> None:
        primary = self.primary_account()
        if primary is None or not primary.enabled:
            return
        if self._active_account_id == primary.id:
            return
        try:
            self._switch_to_account(primary)
        except Exception as exc:  # noqa: BLE001
            self.logger.warning("MT5 POOL restore primary session failed: %s", exc)

    def _run_on_account(self, account: Mt5AccountRecord, op: str, payload: dict) -> dict:
        state = self._status_for(account.id)
        try:
            self._ensure_terminal()
            self._switch_to_account(account)
            executor = self._executor_for(account)
            result = handle_account_operation(
                op,
                payload,
                client=self._client,
                executor=executor,
                account=account,
            )
            state.connected = True
            state.last_error = None
            state.last_ok_at = datetime.now().isoformat(timespec="seconds")
            return {"ok": True, "result": result, "account_id": account.id}
        except Exception as exc:  # noqa: BLE001
            state.connected = False
            state.last_error = str(exc)
            self.logger.warning(
                "MT5 POOL account op failed account=%s name=%s op=%s error=%s",
                account.id,
                account.name,
                op,
                exc,
            )
            return {
                "ok": False,
                "error": str(exc),
                "traceback": traceback.format_exc(limit=3),
                "account_id": account.id,
            }

    def invoke_primary(self, op: str, payload: dict | None = None, *, timeout: float = 60) -> dict:  # noqa: ARG002
        primary = self.primary_account()
        if primary is None:
            return {"ok": False, "error": "no primary account configured"}
        return self.invoke(primary.id, op, payload or {}, timeout=timeout)

    def invoke(self, account_id: int, op: str, payload: dict | None = None, *, timeout: float = 120) -> dict:  # noqa: ARG002
        self.ensure_started()
        account = self.store.get_account(account_id)
        if account is None or not account.enabled:
            return {"ok": False, "error": f"account {account_id} is not enabled"}
        with self._lock:
            response = self._run_on_account(account, op, payload or {})
            primary = self.primary_account()
            if primary and account_id != primary.id:
                self._restore_primary_session()
        return response

    def dispatch(self, op: str, payload: dict | None = None, *, parallel: bool = False, timeout: float = 120) -> list[dict]:  # noqa: ARG002
        targets = self.target_accounts()
        if not targets:
            return []
        responses: list[dict] = []
        with self._lock:
            for account in targets:
                responses.append(self._run_on_account(account, op, payload or {}))
            self._restore_primary_session()
        return responses

    def _enrich_account_result(self, account: Mt5AccountRecord, response: dict) -> dict:
        if not response.get("ok"):
            return {
                "account_id": account.id,
                "account_name": account.name,
                "status": "failed",
                "error": response.get("error") or "account session request failed",
            }
        result = dict(response.get("result") or {})
        result.setdefault("account_id", account.id)
        result.setdefault("account_name", account.name)
        return result

    def place_signal(self, signal: Signal) -> Outcome:
        if not self.active:
            raise RuntimeError("account pool is not active")
        responses = self.dispatch("place_signal", {"signal": _signal_to_dict(signal)})
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
        targets = self.target_accounts()
        responses = self.dispatch("place_market_setup", dict(kwargs))
        account_results = []
        placed_any = False
        primary_result: dict | None = None
        account_by_id = {account.id: account for account in targets}
        for response in responses:
            account_id = int(response.get("account_id") or (response.get("result") or {}).get("account_id") or 0)
            account = account_by_id.get(account_id)
            if account is None:
                continue
            result = self._enrich_account_result(account, response)
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
        elif account_results and all(item.get("status") == "skipped" for item in account_results):
            merged["status"] = "skipped"
        return merged

    def place_test_trade(
        self,
        *,
        symbol: str = "XAUUSD",
        side: str = "buy",
        volume: float = 0.01,
    ) -> dict:
        targets = self.target_accounts()
        if not targets:
            return {
                "status": "failed",
                "reason": "no enabled MT5 accounts configured",
                "symbol": symbol,
                "side": side,
                "volume": volume,
                "account_results": [],
            }

        responses = self.dispatch(
            "place_test_trade",
            {"symbol": symbol, "side": side, "volume": volume},
        )
        account_results: list[dict] = []
        placed_any = False
        primary_result: dict | None = None
        account_by_id = {account.id: account for account in targets}
        for response in responses:
            account_id = int(response.get("account_id") or 0)
            account = account_by_id.get(account_id)
            if account is None:
                continue
            result = self._enrich_account_result(account, response)
            account_results.append(result)
            if result.get("status") in {"placed", "paper"}:
                placed_any = True
                if primary_result is None:
                    primary_result = result

        merged = dict(primary_result or (account_results[0] if account_results else {"status": "failed"}))
        merged["symbol"] = symbol
        merged["side"] = side
        merged["volume"] = volume
        merged["account_results"] = account_results
        if placed_any:
            merged["status"] = "placed" if any(item.get("status") == "placed" for item in account_results) else "paper"
        elif account_results and all(item.get("status") == "failed" for item in account_results):
            merged["status"] = "failed"
            merged["reason"] = "; ".join(
                f"{item.get('account_name')}: {item.get('reason') or item.get('error')}"
                for item in account_results
            )
        return merged

    def manage_tp_protection(self, enabled: bool = True) -> None:
        if not self.active:
            return
        self.dispatch("manage_tp_protection", {"enabled": enabled})

    def apply_breakeven(self, setup: dict) -> dict:
        if not self.active:
            return {"status": "skipped", "reason": "account pool is not active"}
        responses = self.dispatch("apply_breakeven", {"setup": setup})
        for response in responses:
            if response.get("ok"):
                result = response.get("result") or {}
                if result.get("status") in {"applied", "ok", "placed", "breakeven"}:
                    return result
        first = responses[0] if responses else {"ok": False, "error": "no accounts"}
        if first.get("ok"):
            return first.get("result") or {"status": "skipped"}
        return {"status": "failed", "error": first.get("error")}

    def positions_for_targets(self) -> list:
        positions: list = []
        for response in self.dispatch("positions", {}, timeout=30):
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
        primary = self.primary_account()
        if primary is None:
            return {"connected": False, "error": "no primary account configured"}
        try:
            self.ensure_primary_session()
            return self._client.connection_status()
        except Exception as exc:  # noqa: BLE001
            return {"connected": False, "error": str(exc)}
