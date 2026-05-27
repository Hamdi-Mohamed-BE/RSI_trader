from __future__ import annotations

import logging
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import AppConfig, MT5Config
from .mt5_client import MT5Client
from .state import StateStore
from .strategy import Signal
from .symbols import preferred_broker_symbol
from .trader import TradeExecutor


def _signal_from_dict(payload: dict) -> Signal:
    data = dict(payload)
    time_value = data.pop("time")
    if isinstance(time_value, str):
        from datetime import datetime

        data["time"] = datetime.fromisoformat(time_value)
    return Signal(**data)


def _remap_symbol(symbol: str, suffix: str) -> str:
    return preferred_broker_symbol(symbol, suffix)


def _handle_command(
    command: dict,
    *,
    client: MT5Client,
    executor: TradeExecutor,
    account: dict,
) -> dict:
    op = str(command.get("op") or "")
    payload = command.get("payload") or {}

    if op == "ping":
        return {"ok": True, "result": {"status": "ok"}}

    if op == "connection_status":
        return {"ok": True, "result": client.connection_status()}

    if op == "rates":
        frame = client.rates(payload["symbol"], payload["timeframe"], int(payload["bars"]))
        if frame.empty:
            return {"ok": True, "result": []}
        out = frame.copy()
        out["time"] = out["time"].apply(lambda value: value.isoformat())
        return {"ok": True, "result": out.to_dict(orient="records")}

    if op == "rates_range":
        start = datetime.fromisoformat(payload["start"])
        end = datetime.fromisoformat(payload["end"])
        frame = client.rates_range(payload["symbol"], payload["timeframe"], start, end)
        if frame.empty:
            return {"ok": True, "result": []}
        out = frame.copy()
        out["time"] = out["time"].apply(lambda value: value.isoformat())
        return {"ok": True, "result": out.to_dict(orient="records")}

    if op == "symbol_info":
        return {"ok": True, "result": client.symbol_info(payload["symbol"])}

    if op == "tick":
        return {"ok": True, "result": client.tick(payload["symbol"])}

    if op == "positions":
        return {"ok": True, "result": list(client.positions() or [])}

    if op == "account_snapshot":
        return {"ok": True, "result": client.account_snapshot()}

    if op == "realized_pnl_since":
        since_value = payload.get("since")
        since = datetime.fromisoformat(since_value) if isinstance(since_value, str) else since_value
        return {"ok": True, "result": client.realized_pnl_since(since)}

    if op == "live_snapshot":
        return {"ok": True, "result": client.live_snapshot(payload.get("magic"))}

    if op == "manage_tp_protection":
        executor.manage_tp_protection(enabled=bool(payload.get("enabled", True)))
        return {"ok": True, "result": {"status": "ok"}}

    if op == "apply_breakeven":
        setup = payload.get("setup") or {}
        result = executor.apply_breakeven(setup)
        return {"ok": True, "result": result}

    if op == "place_signal":
        signal = _signal_from_dict(payload["signal"])
        suffix = str(account.get("symbol_suffix") or "")
        signal = Signal(
            setup_id=f"{signal.setup_id}:acct{account['id']}",
            symbol=_remap_symbol(signal.symbol, suffix),
            market_key=signal.market_key,
            name=signal.name,
            side=signal.side,
            time=signal.time,
            entry=signal.entry,
            sl=signal.sl,
            tps=list(signal.tps),
            lot_per_leg=signal.lot_per_leg,
            risk_distance=signal.risk_distance,
            session=signal.session,
            reason=signal.reason,
            algorithm=signal.algorithm,
            trail_atr_mult=signal.trail_atr_mult,
            ema_fast_len=signal.ema_fast_len,
            ema_slow_len=signal.ema_slow_len,
            atr_at_entry=signal.atr_at_entry,
        )
        outcome = executor.place_signal(signal)
        return {"ok": True, "result": {"outcome": outcome, "account_id": account["id"], "symbol": signal.symbol}}

    if op == "place_market_setup":
        kwargs = dict(payload)
        suffix = str(account.get("symbol_suffix") or "")
        kwargs["symbol"] = _remap_symbol(str(kwargs["symbol"]), suffix)
        kwargs["setup_id"] = f"{kwargs.get('setup_id', 'setup')}:acct{account['id']}"
        result = executor.place_market_setup(**kwargs)
        result["account_id"] = account["id"]
        return {"ok": True, "result": result}

    return {"ok": False, "error": f"unknown op: {op}"}


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
            try:
                response = _handle_command(command, client=client, executor=executor, account=account)
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
