from __future__ import annotations

from datetime import datetime
from typing import Any

from .mt5_client import MT5Client
from .mt5_account_store import Mt5AccountRecord
from .strategy import Signal
from .symbols import preferred_broker_symbol
from .trader import TradeExecutor


def _signal_from_dict(payload: dict) -> Signal:
    data = dict(payload)
    time_value = data.pop("time")
    if isinstance(time_value, str):
        data["time"] = datetime.fromisoformat(time_value)
    return Signal(**data)


def _remap_symbol(symbol: str, suffix: str) -> str:
    return preferred_broker_symbol(symbol, suffix)


def _account_payload(account: Mt5AccountRecord | dict) -> dict:
    if isinstance(account, Mt5AccountRecord):
        return account.to_worker_dict()
    return dict(account)


def handle_account_operation(
    op: str,
    payload: dict | None,
    *,
    client: MT5Client,
    executor: TradeExecutor,
    account: Mt5AccountRecord | dict,
) -> dict:
    payload = payload or {}
    account_data = _account_payload(account)
    op = str(op or "")

    if op == "connection_status":
        return client.connection_status()

    if op == "rates":
        frame = client.rates(payload["symbol"], payload["timeframe"], int(payload["bars"]))
        if frame.empty:
            return []
        out = frame.copy()
        out["time"] = out["time"].apply(lambda value: value.isoformat())
        return out.to_dict(orient="records")

    if op == "rates_range":
        start = datetime.fromisoformat(payload["start"])
        end = datetime.fromisoformat(payload["end"])
        frame = client.rates_range(payload["symbol"], payload["timeframe"], start, end)
        if frame.empty:
            return []
        out = frame.copy()
        out["time"] = out["time"].apply(lambda value: value.isoformat())
        return out.to_dict(orient="records")

    if op == "symbol_info":
        return client.symbol_info(payload["symbol"])

    if op == "tick":
        return client.tick(payload["symbol"])

    if op == "positions":
        return list(client.positions() or [])

    if op == "account_snapshot":
        return client.account_snapshot()

    if op == "realized_pnl_since":
        since_value = payload.get("since")
        since = datetime.fromisoformat(since_value) if isinstance(since_value, str) else since_value
        return client.realized_pnl_since(since)

    if op == "live_snapshot":
        return client.live_snapshot(payload.get("magic"))

    if op == "manage_tp_protection":
        executor.manage_tp_protection(enabled=bool(payload.get("enabled", True)))
        return {"status": "ok"}

    if op == "apply_breakeven":
        setup = payload.get("setup") or {}
        return executor.apply_breakeven(setup)

    if op == "place_signal":
        signal = _signal_from_dict(payload["signal"])
        suffix = str(account_data.get("symbol_suffix") or "")
        signal = Signal(
            setup_id=f"{signal.setup_id}:acct{account_data['id']}",
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
        return {"outcome": outcome, "account_id": account_data["id"], "symbol": signal.symbol}

    if op == "place_market_setup":
        kwargs = dict(payload)
        suffix = str(account_data.get("symbol_suffix") or "")
        kwargs["symbol"] = _remap_symbol(str(kwargs["symbol"]), suffix)
        kwargs["setup_id"] = f"{kwargs.get('setup_id', 'setup')}:acct{account_data['id']}"
        result = executor.place_market_setup(**kwargs)
        result["account_id"] = account_data["id"]
        result["account_name"] = account_data.get("name")
        return result

    if op == "place_test_trade":
        symbol = _remap_symbol(str(payload.get("symbol") or "XAUUSD"), str(account_data.get("symbol_suffix") or ""))
        side = str(payload.get("side") or "buy")
        volume = float(payload.get("volume") or 0.01)
        result = executor.place_test_trade(symbol, side, volume)
        result["account_id"] = account_data["id"]
        result["account_name"] = account_data.get("name")
        return result

    raise ValueError(f"unknown op: {op}")
