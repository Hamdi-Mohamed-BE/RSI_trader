from __future__ import annotations

from datetime import datetime, time, timezone

from .config import RiskConfig
from .mt5_client import MT5Client
from .state import StateStore


def daily_loss_setup_risk_cap(day_start_balance: float, max_daily_loss_pct: float) -> float:
    return round(day_start_balance * max_daily_loss_pct / 100.0, 2)


def resolve_day_start_balance(
    client: MT5Client,
    state: StateStore,
    risk_cfg: RiskConfig,
) -> float | None:
    if not risk_cfg.daily_loss_guard_active():
        return None

    now = datetime.now(timezone.utc).replace(microsecond=0)
    today = now.date().isoformat()
    account = client.account_snapshot()
    balance = float(account["balance"])
    stored = state.read().get("daily_risk", {})
    if stored.get("date") == today and stored.get("start_balance") is not None:
        return float(stored["start_balance"])

    day_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    realized_today = client.realized_pnl_since(day_start)
    start_balance = round(balance - realized_today, 2)
    if start_balance <= 0:
        start_balance = balance
    return start_balance
