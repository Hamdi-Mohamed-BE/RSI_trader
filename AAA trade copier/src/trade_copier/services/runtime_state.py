from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.enums import AccountState, ExecutionMode
from ..models import Account, MasterTradeState, TradeLink
from .accounts import ensure_system_state
from .audit import record_audit


def recover_enabled_execution_mode(
    session: Session,
    *,
    live_execution_permitted: bool,
    snapshot_reconciled: bool = False,
) -> ExecutionMode | None:
    """Repair an enabled dashboard that was left in monitor mode.

    Older releases could clear the global pause without changing the execution
    mode. Live recovery still requires both environment gates. Master trades
    already present at recovery time become a baseline, preventing a restart
    from opening historical exposure on followers. The caller must confirm that
    a complete master snapshot was reconciled immediately before recovery;
    otherwise the safety transition is refused.
    """

    if not snapshot_reconciled:
        return None
    system = ensure_system_state(session)
    if system.global_pause or system.execution_mode != ExecutionMode.MONITOR.value:
        return None
    if not system.active_master_account_id:
        return None

    master = session.get(Account, system.active_master_account_id)
    if master is None or not master.is_master or master.state != AccountState.ACTIVE.value:
        return None

    active_accounts = session.scalars(
        select(Account).where(Account.state == AccountState.ACTIVE.value)
    ).all()
    if not active_accounts:
        return None
    has_live_account = any(account.trade_mode != "demo" for account in active_accounts)
    if has_live_account and not live_execution_permitted:
        return None
    target_mode = ExecutionMode.LIVE if has_live_account else ExecutionMode.DEMO

    baselined = 0
    states = session.scalars(
        select(MasterTradeState).where(
            MasterTradeState.master_account_id == master.id,
            MasterTradeState.status == "active",
        )
    ).all()
    for trade_state in states:
        linked = session.scalar(
            select(TradeLink.id).where(
                TradeLink.master_account_id == master.id,
                TradeLink.source_type == trade_state.source_type,
                TradeLink.source_ticket == trade_state.source_ticket,
                TradeLink.status == "active",
            )
        )
        if linked is not None:
            continue
        trade_state.status = "baseline"
        trade_state.last_dispatch_failed = False
        session.add(trade_state)
        baselined += 1

    system.execution_mode = target_mode.value
    system.reason = f"Recovered enabled {target_mode.value} copying after restart"
    session.add(system)
    record_audit(
        session,
        actor="copier-core",
        action="system.execution_mode_recovered",
        message=f"Recovered an enabled {target_mode.value} system left in monitor mode.",
        details={
            "baselined_master_trades": baselined,
            "execution_mode": target_mode.value,
        },
    )
    session.commit()
    return target_mode
