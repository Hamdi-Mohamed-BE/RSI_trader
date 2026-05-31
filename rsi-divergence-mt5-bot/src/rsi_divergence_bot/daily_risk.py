from __future__ import annotations

from datetime import datetime, time, timezone

from .config import RiskConfig
from .mt5_client import MT5Client
from .state import StateStore


def daily_loss_setup_risk_cap(start_equity: float, max_daily_loss_pct: float) -> float:
    """Max $ risk per setup from daily start balance and loss-guard percent."""
    return round(float(start_equity) * float(max_daily_loss_pct) / 100.0, 2)


def _utc_day_start(now: datetime) -> datetime:
    return datetime.combine(now.date(), time.min, tzinfo=timezone.utc)


def daily_risk_account_key(account: dict) -> str:
    login = account.get("login")
    server = account.get("server") or ""
    if login is None:
        return ""
    return f"{int(login)}@{server}"


def loss_from_day_start(start_equity: float, current_equity: float, balance_adjustment: float = 0.0) -> float:
    """USD below day-start equity (deposits/withdrawals excluded)."""
    adjusted_equity = float(current_equity) - float(balance_adjustment)
    return round(max(0.0, float(start_equity) - adjusted_equity), 2)


def _disabled_daily_risk_payload(
    *,
    today: str,
    equity: float,
    balance: float,
    floating_pnl: float,
    risk_cfg: RiskConfig,
    now: datetime,
    account_key: str,
) -> dict:
    return {
        "enabled": False,
        "halted": False,
        "halt_reason": None,
        "date": today,
        "account_key": account_key,
        "data_source": "mt5",
        "start_equity": round(equity, 2),
        "start_balance": round(equity, 2),
        "equity": round(equity, 2),
        "balance": round(balance, 2),
        "floating_pnl": round(floating_pnl, 2),
        "daily_pnl": 0.0,
        "gain": 0.0,
        "loss": 0.0,
        "loss_limit": 0.0,
        "loss_pct": 0.0,
        "loss_remaining": 0.0,
        "win_target": 0.0,
        "win_goal_equity": round(equity, 2),
        "win_remaining": 0.0,
        "loss_guard_enabled": False,
        "win_guard_enabled": False,
        "loss_halted": False,
        "win_halted": False,
        "use_daily_loss_guard": risk_cfg.use_daily_loss_guard,
        "max_daily_loss_pct": risk_cfg.max_daily_loss_pct,
        "use_daily_win_guard": risk_cfg.use_daily_win_guard,
        "daily_win_target_mode": risk_cfg.daily_win_target_mode,
        "max_daily_win_pct": risk_cfg.max_daily_win_pct,
        "max_daily_win_usd": risk_cfg.max_daily_win_usd,
        "halted_at": None,
        "win_halted_at": None,
        "updated_at": now.isoformat(),
    }


def compute_daily_risk_status(
    client: MT5Client,
    state: StateStore,
    risk_cfg: RiskConfig,
) -> dict:
    """
    Daily guards (UTC day, per account):

    - Loss: stop when equity is down >= max_daily_loss_pct of day-start (e.g. 20% of $300 = $60).
    - Win: stop when profit from day-start >= win target (e.g. +$200 → $500 on a $300 start).
    """
    now = datetime.now(timezone.utc).replace(microsecond=0)
    today = now.date().isoformat()
    account = client.account_snapshot()
    account_key = daily_risk_account_key(account)
    equity = float(account["equity"])
    balance = float(account["balance"])
    floating_pnl = float(account.get("floating_pnl", 0.0) or 0.0)
    loss_guard_enabled = risk_cfg.daily_loss_guard_active()
    win_guard_enabled = risk_cfg.daily_win_guard_active()
    any_guard = loss_guard_enabled or win_guard_enabled

    if not any_guard:
        payload = _disabled_daily_risk_payload(
            today=today,
            equity=equity,
            balance=balance,
            floating_pnl=floating_pnl,
            risk_cfg=risk_cfg,
            now=now,
            account_key=account_key,
        )
        state.update_daily_risk(payload)
        return payload

    stored = state.read().get("daily_risk", {})
    same_context = stored.get("date") == today and stored.get("account_key") == account_key

    day_start = _utc_day_start(now)
    balance_adjustment = client.balance_adjustments_since(day_start)

    if same_context:
        start_equity = round(float(stored.get("start_equity", equity)), 2)
    else:
        start_equity = round(equity, 2)

    daily_pnl = round(equity - start_equity - balance_adjustment, 2)
    gain = round(max(0.0, daily_pnl), 2)

    max_loss_pct = float(risk_cfg.max_daily_loss_pct or 0.0)
    loss_limit = round(start_equity * max_loss_pct / 100.0, 2) if loss_guard_enabled else 0.0
    loss = loss_from_day_start(start_equity, equity, balance_adjustment) if loss_guard_enabled else 0.0
    loss_pct = round((loss / start_equity * 100.0) if start_equity > 0 and loss_guard_enabled else 0.0, 2)
    loss_remaining = round(max(0.0, loss_limit - loss), 2) if loss_guard_enabled else 0.0
    loss_floor_equity = round(start_equity - loss_limit, 2) if loss_guard_enabled else start_equity
    loss_halted = loss_guard_enabled and loss_limit > 0 and loss >= loss_limit

    win_target = float(risk_cfg.effective_daily_win_target_usd(start_equity) or 0.0) if win_guard_enabled else 0.0
    win_goal_equity = round(start_equity + win_target, 2) if win_guard_enabled else start_equity
    win_remaining = round(max(0.0, win_target - gain), 2) if win_guard_enabled else 0.0
    win_halted = win_guard_enabled and win_target > 0 and gain >= win_target

    halted = loss_halted or win_halted
    halt_reason: str | None = None
    if win_halted:
        halt_reason = "win"
    elif loss_halted:
        halt_reason = "loss"

    payload: dict = {
        "enabled": True,
        "halted": halted,
        "halt_reason": halt_reason,
        "date": today,
        "account_key": account_key,
        "data_source": "mt5",
        "start_equity": start_equity,
        "start_balance": start_equity,
        "equity": round(equity, 2),
        "balance": round(balance, 2),
        "floating_pnl": round(floating_pnl, 2),
        "daily_pnl": daily_pnl,
        "gain": gain,
        "loss": loss,
        "loss_limit": loss_limit,
        "loss_pct": loss_pct,
        "loss_floor_equity": loss_floor_equity,
        "remaining": loss_remaining,
        "loss_remaining": loss_remaining,
        "win_target": win_target,
        "win_goal_equity": win_goal_equity,
        "win_remaining": win_remaining,
        "loss_guard_enabled": loss_guard_enabled,
        "win_guard_enabled": win_guard_enabled,
        "loss_halted": loss_halted,
        "win_halted": win_halted,
        "use_daily_loss_guard": risk_cfg.use_daily_loss_guard,
        "max_daily_loss_pct": risk_cfg.max_daily_loss_pct,
        "use_daily_win_guard": risk_cfg.use_daily_win_guard,
        "daily_win_target_mode": risk_cfg.daily_win_target_mode,
        "max_daily_win_pct": risk_cfg.max_daily_win_pct,
        "max_daily_win_usd": risk_cfg.max_daily_win_usd,
        "updated_at": now.isoformat(),
    }
    if not same_context:
        payload["created_at"] = now.isoformat()
        payload["halted_at"] = now.isoformat() if loss_halted else None
        payload["win_halted_at"] = now.isoformat() if win_halted else None
    else:
        if stored.get("created_at"):
            payload["created_at"] = stored["created_at"]
        if loss_halted:
            payload["halted_at"] = stored.get("halted_at") or now.isoformat()
        else:
            payload["halted_at"] = None
        if win_halted:
            payload["win_halted_at"] = stored.get("win_halted_at") or now.isoformat()
        else:
            payload["win_halted_at"] = None

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
    reference = status.get("start_equity")
    if reference is None:
        return None
    return float(reference)
