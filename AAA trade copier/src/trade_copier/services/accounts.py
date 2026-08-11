from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..domain.enums import AccountRole, AccountState, AuditSeverity, ExecutionMode, JobStatus
from ..models import Account, CopyJob, RiskProfile, SystemState
from ..schemas import AccountCreate
from .audit import record_audit
from .credentials import CredentialVault


def ensure_system_state(session: Session) -> SystemState:
    state = session.get(SystemState, 1)
    if state is None:
        state = SystemState(id=1)
        session.add(state)
        session.commit()
        session.refresh(state)
    return state


def create_account(
    session: Session,
    data: AccountCreate,
    *,
    vault: CredentialVault,
    actor: str,
) -> Account:
    if session.scalar(select(Account).where(Account.display_name == data.display_name.strip())):
        raise ValueError("An account with this display name already exists.")
    if data.risk_profile_id and session.get(RiskProfile, data.risk_profile_id) is None:
        raise ValueError("Selected risk profile does not exist.")

    credential_ref = vault.store(data.password) if data.password else ""
    account = Account(
        display_name=data.display_name.strip(),
        login=data.login.strip(),
        broker_server=data.broker_server.strip(),
        terminal_path=data.terminal_path,
        role=data.role.value,
        state=data.state.value,
        credential_ref=credential_ref,
        trade_mode=data.trade_mode,
        position_mode=data.position_mode,
        risk_profile_id=data.risk_profile_id,
    )
    session.add(account)
    record_audit(
        session,
        actor=actor,
        action="account.created",
        target_type="account",
        target_id=account.id,
        message=f"Account {account.display_name} was created.",
        details={"role": account.role, "server": account.broker_server},
    )
    session.commit()
    session.refresh(account)
    return account


def select_master(session: Session, account_id: str, *, actor: str) -> Account:
    account = session.get(Account, account_id)
    if account is None:
        raise ValueError("Account not found.")
    if account.role != AccountRole.MASTER_CANDIDATE.value:
        raise ValueError("Only a master-candidate account can become the active master.")

    state = ensure_system_state(session)
    active_jobs = session.scalar(
        select(func.count(CopyJob.id)).where(
            CopyJob.status.in_([JobStatus.QUEUED.value, JobStatus.DISPATCHED.value])
        )
    )
    if active_jobs:
        raise ValueError("Copy queues must be idle before changing the master.")

    session.execute(update(Account).values(is_master=False))
    account.is_master = True
    account.state = AccountState.ACTIVE.value
    state.active_master_account_id = account.id
    state.global_pause = True
    state.execution_mode = ExecutionMode.MONITOR.value
    state.reason = "Master changed; explicit unpause required"
    record_audit(
        session,
        actor=actor,
        action="master.changed",
        target_type="account",
        target_id=account.id,
        severity=AuditSeverity.WARNING,
        message=f"{account.display_name} is now the active master; copying remains paused.",
    )
    session.commit()
    session.refresh(account)
    return account


def set_global_pause(session: Session, *, paused: bool, reason: str, actor: str) -> SystemState:
    state = ensure_system_state(session)
    state.global_pause = paused
    state.reason = reason.strip() or ("Paused by administrator" if paused else "Enabled")
    record_audit(
        session,
        actor=actor,
        action="system.paused" if paused else "system.unpaused",
        message=state.reason,
        severity=AuditSeverity.WARNING if paused else AuditSeverity.INFO,
    )
    session.commit()
    session.refresh(state)
    return state
