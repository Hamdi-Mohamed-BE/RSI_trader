from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from ..domain.enums import ExecutionMode
from ..models import (
    Account,
    AuditEvent,
    CopyJob,
    RiskProfile,
    SourceTradeEvent,
    SystemState,
)

LEGACY_DEMO_IDENTITIES = {
    ("Demo Master", "100001", "AAA-Demo"),
    ("Follower Alpha", "200001", "Broker-A-Demo"),
    ("Follower Bravo", "300001", "Broker-B-Demo"),
}


def remove_legacy_demo_seed(session: Session) -> bool:
    """Remove only the exact sample records created by early development builds."""

    candidates = session.scalars(select(Account)).all()
    demo_accounts = [
        account
        for account in candidates
        if (account.display_name, account.login, account.broker_server) in LEGACY_DEMO_IDENTITIES
    ]
    if not demo_accounts:
        return False

    account_ids = [account.id for account in demo_accounts]
    source_event_ids = session.scalars(
        select(SourceTradeEvent.id).where(SourceTradeEvent.source_account_id.in_(account_ids))
    ).all()
    session.execute(delete(CopyJob).where(CopyJob.follower_account_id.in_(account_ids)))
    session.execute(
        delete(SourceTradeEvent).where(SourceTradeEvent.source_account_id.in_(account_ids))
    )
    for account in demo_accounts:
        session.delete(account)
    session.flush()

    profile = session.scalar(select(RiskProfile).where(RiskProfile.name == "Demo 1% stop risk"))
    if profile is not None and not profile.accounts:
        session.delete(profile)

    audit_targets = [*account_ids, *source_event_ids]
    session.execute(
        delete(AuditEvent).where(
            or_(
                AuditEvent.action.like("demo.%"),
                AuditEvent.target_id.in_(audit_targets),
            )
        )
    )
    state = session.get(SystemState, 1)
    if state is not None and state.active_master_account_id in account_ids:
        state.active_master_account_id = None
        state.global_pause = True
        state.execution_mode = ExecutionMode.MONITOR.value
        state.reason = "Fresh workspace; waiting for connected MT5"
    session.commit()
    return True
