from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..engine.strategy import SignalDecision
from ..models import OrderRecord
from ..schemas import RuntimeConfig


ACTIVE_STATUSES = ("PENDING", "OPEN")


def reconcile_orders(
    db: Session, symbol: str, candle: dict, config: RuntimeConfig
) -> list[OrderRecord]:
    orders = db.scalars(
        select(OrderRecord).where(
            OrderRecord.symbol == symbol, OrderRecord.status.in_(ACTIVE_STATUSES)
        )
    ).all()
    changed: list[OrderRecord] = []
    high, low = float(candle["high"]), float(candle["low"])
    for order in orders:
        if order.status == "PENDING":
            if low <= order.entry <= high:
                order.status = "OPEN"
                order.opened_at = datetime.now(timezone.utc)
                changed.append(order)
            continue
        risk_distance = abs(order.entry - order.metadata_json.get("initial_stop", order.stop_loss))
        if not risk_distance:
            continue
        if order.side == "BUY":
            if low <= order.stop_loss:
                _close(order, order.stop_loss, risk_distance, "STOP")
            elif high >= order.take_profit:
                _close(order, order.take_profit, risk_distance, "TARGET")
            elif config.trail_enabled:
                favorable_r = (high - order.entry) / risk_distance
                _trail(order, favorable_r, risk_distance, config, 1)
        else:
            if high >= order.stop_loss:
                _close(order, order.stop_loss, risk_distance, "STOP")
            elif low <= order.take_profit:
                _close(order, order.take_profit, risk_distance, "TARGET")
            elif config.trail_enabled:
                favorable_r = (order.entry - low) / risk_distance
                _trail(order, favorable_r, risk_distance, config, -1)
        if order in db.dirty:
            changed.append(order)
    if changed:
        db.commit()
    return changed


def create_order_from_signal(
    db: Session, decision: SignalDecision, config: RuntimeConfig
) -> OrderRecord | None:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    daily_count = db.scalar(
        select(func.count(OrderRecord.id)).where(OrderRecord.opened_at >= start)
    ) or 0
    if daily_count >= config.max_trades_per_day:
        return None
    duplicate = db.scalar(
        select(OrderRecord).where(
            OrderRecord.symbol == decision.symbol,
            OrderRecord.side == decision.direction,
            OrderRecord.status.in_(ACTIVE_STATUSES),
        )
    )
    if duplicate is not None or decision.status != "A_PLUS":
        return None
    risk_amount = config.account_balance * config.risk_percent / 100
    distance = abs(float(decision.entry) - float(decision.stop_loss))
    quantity = risk_amount / distance if distance else 0.0
    order = OrderRecord(
        symbol=decision.symbol,
        side=decision.direction,
        order_type=decision.order_type or "LIMIT",
        status="OPEN" if decision.order_type == "MARKET" else "PENDING",
        entry=float(decision.entry),
        stop_loss=float(decision.stop_loss),
        take_profit=float(decision.take_profit),
        quantity=quantity,
        risk_amount=risk_amount,
        score=decision.score,
        metadata_json={
            "initial_stop": float(decision.stop_loss),
            "reward_risk": decision.reward_risk,
            "reasons": decision.reasons,
            "paper": True,
        },
    )
    db.add(order)
    db.commit()
    return order


def _trail(order: OrderRecord, favorable_r: float, risk: float, config: RuntimeConfig, sign: int) -> None:
    if favorable_r < config.trail_step_r:
        return
    steps = int(favorable_r // config.trail_step_r)
    locked_r = max(0.0, (steps - 1) * config.trail_step_r)
    candidate = order.entry + sign * locked_r * risk
    if order.side == "BUY":
        order.stop_loss = max(order.stop_loss, candidate)
    else:
        order.stop_loss = min(order.stop_loss, candidate)


def _close(order: OrderRecord, exit_price: float, risk: float, reason: str) -> None:
    multiple = (
        (exit_price - order.entry) / risk
        if order.side == "BUY"
        else (order.entry - exit_price) / risk
    )
    order.status = "CLOSED"
    order.closed_at = datetime.now(timezone.utc)
    order.pnl = order.risk_amount * multiple
    metadata = dict(order.metadata_json)
    metadata["exit_reason"] = reason
    metadata["exit_price"] = exit_price
    order.metadata_json = metadata
