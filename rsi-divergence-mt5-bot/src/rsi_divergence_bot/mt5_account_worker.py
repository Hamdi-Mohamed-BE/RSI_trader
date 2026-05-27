from __future__ import annotations

import logging
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import AppConfig
from .mt5_account_ops import handle_account_operation
from .mt5_client import MT5Client
from .state import StateStore
from .trader import TradeExecutor


def _initialize_client(client: MT5Client, logger: logging.Logger, *, attempts: int = 8, delay_seconds: float = 4.0) -> None:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            client.initialize()
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning(
                "MT5 ACCOUNT WORKER initialize attempt %s/%s failed: %s",
                attempt,
                attempts,
                exc,
            )
            try:
                client.shutdown(force=True)
            except Exception:  # noqa: BLE001
                pass
            if attempt < attempts:
                time.sleep(delay_seconds)
    if last_error is not None:
        raise last_error
    raise RuntimeError("MT5 initialize failed")


def account_worker_main(
    account: dict,
    config_dict: dict,
    state_path: str,
    cmd_queue,
    resp_queue,
) -> None:
    logger = logging.getLogger(f"mt5-account-{account.get('id')}")
    client: MT5Client | None = None
    try:
        config = AppConfig.model_validate(config_dict)
        mt5_cfg = config.mt5.model_copy(
            update={
                "login": int(account["login"]),
                "password": str(account["password"]),
                "server": str(account["server"]),
                "path": account.get("mt5_path") or config.mt5.path,
                "broker_symbol_suffix": str(account.get("symbol_suffix") or ""),
            }
        )
        client = MT5Client(mt5_cfg)
        state = StateStore(state_path)
        executor = TradeExecutor(config, client, state, logger)
        logger.warning(
            "MT5 ACCOUNT WORKER connecting id=%s name=%s login=%s server=%s path=%s suffix=%s",
            account.get("id"),
            account.get("name"),
            account.get("login"),
            account.get("server"),
            mt5_cfg.path or "default",
            account.get("symbol_suffix") or "",
        )
        _initialize_client(client, logger)
        logger.warning(
            "MT5 ACCOUNT WORKER ready id=%s name=%s login=%s suffix=%s",
            account.get("id"),
            account.get("name"),
            account.get("login"),
            account.get("symbol_suffix") or "",
        )
        while True:
            command = cmd_queue.get()
            if command is None:
                break
            op = str(command.get("op") or "")
            if op == "shutdown":
                break
            request_id = str(command.get("request_id") or "")
            payload = command.get("payload") or {}
            if op == "ping":
                response = {"ok": True, "result": {"status": "ok"}}
            else:
                try:
                    response_payload = handle_account_operation(
                        op,
                        payload,
                        client=client,
                        executor=executor,
                        account=account,
                    )
                    response = {"ok": True, "result": response_payload}
                except Exception as exc:  # noqa: BLE001
                    response = {"ok": False, "error": str(exc), "traceback": traceback.format_exc(limit=3)}
            resp_queue.put({"request_id": request_id, **response})
    except Exception as exc:  # noqa: BLE001
        logger.exception("MT5 ACCOUNT WORKER failed to start: %s", exc)
        resp_queue.put({"request_id": "startup", "ok": False, "error": str(exc), "traceback": traceback.format_exc(limit=3)})
    finally:
        if client is not None:
            try:
                client.shutdown(force=True)
            except Exception:  # noqa: BLE001
                pass
        logger.info("MT5 ACCOUNT WORKER stopped id=%s", account.get("id"))


def account_state_path(runtime_dir: Path, account_id: int) -> str:
    return str((runtime_dir / f"state-account-{account_id}.json").resolve())
