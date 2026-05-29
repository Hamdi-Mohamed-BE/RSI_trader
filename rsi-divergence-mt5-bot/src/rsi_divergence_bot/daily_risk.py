from __future__ import annotations

from datetime import datetime, time, timezone

from .config import RiskConfig
from .mt5_client import MT5Client
from .state import StateStore


def daily_loss_setup_risk_cap(reference_equity: float, max_daily_loss_pct: float) -> float:
    return round(reference_equity * max_daily_loss_pct / 100.0, 2)


def resolve_day_start_equity(
    client: MT5Client,
    state: StateStore,
    risk_cfg: RiskConfig,
    *,
    equity: float,
    now: datetime,
    stored: dict | None = None,
) -> float:
    """Resolve UTC day-start equity from MT5 snapshot or today's closed deal history."""
    today = now.date().isoformat()
    cached = stored if stored is not None else state.read().get("daily_risk", {})

    if cached.get("date") == today:
        if cached.get("start_equity") is not None:
            return float(cached["start_equity"])
        if cached.get("start_balance") is not None:
            return float(cached["start_balance"])

    day_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    closed_pnl = client.net_pnl_since(day_start)
    balance_adjustment = client.balance_adjustments_since(day_start)
    reconstructed = round(float(equity) - closed_pnl - balance_adjustment, 2)
    if reconstructed <= 0:
        return round(float(equity), 2)
    return reconstructed


def compute_daily_risk_status(
    client: MT5Client,
    state: StateStore,
    risk_cfg: RiskConfig,
) -> dict:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    today = now.date().isoformat()
    account = client.account_snapshot()
    equity = float(account["equity"])
    balance = float(account["balance"])
    floating_pnl = float(account.get("floating_pnl", 0.0) or 0.0)
    max_pct = risk_cfg.max_daily_loss_pct

    if not risk_cfg.daily_loss_guard_active():
        payload = {
            "enabled": False,
            "halted": False,
            "date": today,
            "start_equity": round(equity, 2),
            "start_balance": round(equity, 2),
            "equity": round(equity, 2),
            "balance": round(balance, 2),
            "floating_pnl": round(floating_pnl, 2),
            "daily_pnl": 0.0,
            "loss": 0.0,
            "loss_limit": 0.0,
            "loss_pct": 0.0,
            "remaining": 0.0,
            "use_daily_loss_guard": risk_cfg.use_daily_loss_guard,
            "max_daily_loss_pct": max_pct,
            "halted_at": None,
            "updated_at": now.isoformat(),
        }
        state.update_daily_risk(payload)
        return payload

    stored = state.read().get("daily_risk", {})
    if stored.get("date") != today:
        start_equity = round(equity, 2)
        peak_equity = start_equity
    else:
        start_equity = resolve_day_start_equity(
            client,
            state,
            risk_cfg,
            equity=equity,
            now=now,
            stored=stored,
        )
        stored_peak = stored.get("peak_equity")
        peak_equity = max(float(stored_peak) if stored_peak is not None else start_equity, round(equity, 2))

    loss_limit = round(peak_equity * float(max_pct) / 100.0, 2)
    daily_pnl = round(equity - start_equity, 2)
    loss = round(max(0.0, peak_equity - equity), 2)
    loss_pct = round((loss / peak_equity * 100.0) if peak_equity > 0 else 0.0, 2)
    remaining = round(max(0.0, loss_limit - loss), 2)
    halted = loss_limit > 0 and loss >= loss_limit

    payload: dict = {
        "enabled": True,
        "halted": halted,
        "date": today,
        "start_equity": start_equity,
        "start_balance": start_equity,
        "peak_equity": round(peak_equity, 2),
        "equity": round(equity, 2),
        "balance": round(balance, 2),
        "floating_pnl": round(floating_pnl, 2),
        "daily_pnl": daily_pnl,
        "loss": loss,
        "loss_limit": loss_limit,
        "loss_pct": loss_pct,
        "remaining": remaining,
        "use_daily_loss_guard": risk_cfg.use_daily_loss_guard,
        "max_daily_loss_pct": float(max_pct),
        "updated_at": now.isoformat(),
    }
    if stored.get("date") != today:
        payload["created_at"] = now.isoformat()
        payload["halted_at"] = now.isoformat() if halted else None
    else:
        if stored.get("created_at"):
            payload["created_at"] = stored["created_at"]
        if halted:
            payload["halted_at"] = stored.get("halted_at") or now.isoformat()
        else:
            payload["halted_at"] = None

    state.update_daily_risk(payload)
    return payload


def resolve_day_start_balance(
    client: MT5Client,
    state: StateStore,
    risk_cfg: RiskConfig,
) -> float | None:
    if not risk_cfg.daily_loss_guard_active():
        return None
    status = compute_daily_risk_status(client, state, risk_cfg)
    start_equity = status.get("start_equity")
    if start_equity is None:
        return None
    return float(start_equity)


def resolve_daily_loss_reference_equity(
    client: MT5Client,
    state: StateStore,
    risk_cfg: RiskConfig,
) -> float | None:
    if not risk_cfg.daily_loss_guard_active():
        return None
    status = compute_daily_risk_status(client, state, risk_cfg)
    reference = status.get("peak_equity", status.get("start_equity"))
    if reference is None:
        return None
    return float(reference)
