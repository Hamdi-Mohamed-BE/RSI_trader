from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.enums import AccountState, ExecutionMode
from ..models import Account, MasterTradeState, TradeLink
from .accounts import ensure_system_state
from .audit import record_audit


def recover_enabled_demo_mode(session: Session, *, snapshot_reconciled: bool = False) -> bool:
    """Repair an enabled dashboard that was left in monitor mode.

    Older releases could clear the global pause without changing the execution
    mode. Recovery is deliberately limited to demo-only installations. Master
    trades already present at recovery time become a baseline, preventing a
    restart from opening historical exposure on followers. The caller must
    confirm that a complete master snapshot was reconciled immediately before
    recovery; otherwise the safety transition is refused.
    """

    if not snapshot_reconciled:
        return False
    system = ensure_system_state(session)
    if system.global_pause or system.execution_mode != ExecutionMode.MONITOR.value:
        return False
    if not system.active_master_account_id:
        return False

    master = session.get(Account, system.active_master_account_id)
    if master is None or not master.is_master or master.state != AccountState.ACTIVE.value:
        return False

    active_accounts = session.scalars(
        select(Account).where(Account.state == AccountState.ACTIVE.value)
    ).all()
    if not active_accounts or any(account.trade_mode != "demo" for account in active_accounts):
        return False

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

    system.execution_mode = ExecutionMode.DEMO.value
    system.reason = "Recovered enabled demo copying after restart"
    session.add(system)
    record_audit(
        session,
        actor="copier-core",
        action="system.demo_mode_recovered",
        message="Recovered an enabled demo-only system that was left in monitor mode.",
        details={"baselined_master_trades": baselined},
    )
    session.commit()
    return True
