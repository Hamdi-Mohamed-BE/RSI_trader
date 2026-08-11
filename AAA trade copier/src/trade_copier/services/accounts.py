from collections.abc import Callable
from contextlib import suppress

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..domain.enums import AccountRole, AccountState, AuditSeverity, ExecutionMode, JobStatus
from ..models import Account, CopyJob, RiskProfile, SourceTradeEvent, SystemState
from ..schemas import AccountCreate, AccountUpdate
from .audit import record_audit
from .credentials import CredentialVault
from .risk_profiles import ensure_default_risk_profile


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
    if session.scalar(
        select(Account).where(
            Account.login == data.login.strip(),
            Account.broker_server == data.broker_server.strip(),
        )
    ):
        raise ValueError("This MT5 login and broker server are already configured.")
    if data.risk_profile_id and session.get(RiskProfile, data.risk_profile_id) is None:
        raise ValueError("Selected risk profile does not exist.")

    risk_profile_id = data.risk_profile_id
    if data.role is AccountRole.FOLLOWER and risk_profile_id is None:
        risk_profile_id = ensure_default_risk_profile(
            session,
            actor=actor,
            assign_missing=False,
        ).id
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
        risk_profile_id=risk_profile_id,
    )
    session.add(account)
    session.flush()
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


def update_account(
    session: Session,
    account: Account,
    data: AccountUpdate,
    *,
    actor: str,
) -> Account:
    duplicate_name = session.scalar(
        select(Account.id).where(
            Account.display_name == data.display_name.strip(),
            Account.id != account.id,
        )
    )
    if duplicate_name:
        raise ValueError("An account with this display name already exists.")
    if data.risk_profile_id and session.get(RiskProfile, data.risk_profile_id) is None:
        raise ValueError("Selected risk profile does not exist.")
    if account.is_master and data.role is not AccountRole.MASTER_CANDIDATE:
        raise ValueError("Select another master before changing this account's role.")

    account.display_name = data.display_name.strip()
    account.broker_server = data.broker_server.strip()
    account.terminal_path = data.terminal_path
    account.role = data.role.value
    account.state = data.state.value
    account.trade_mode = data.trade_mode
    account.position_mode = data.position_mode
    risk_profile_id = data.risk_profile_id
    if data.role is AccountRole.FOLLOWER and risk_profile_id is None:
        risk_profile_id = ensure_default_risk_profile(
            session,
            actor=actor,
            assign_missing=False,
        ).id
    account.risk_profile_id = risk_profile_id
    record_audit(
        session,
        actor=actor,
        action="account.updated",
        target_type="account",
        target_id=account.id,
        message=f"Account {account.display_name} was updated.",
    )
    session.commit()
    session.refresh(account)
    return account


def replace_account_credential(
    session: Session,
    account: Account,
    password: str,
    *,
    vault: CredentialVault,
    actor: str,
) -> Account:
    """Replace an MT5 password without ever storing it in SQLite or audit details."""
    if not password:
        raise ValueError("Enter the MT5 password to configure automatic login.")
    previous_reference = account.credential_ref
    account.credential_ref = vault.store(password)
    record_audit(
        session,
        actor=actor,
        action="account.credential_updated",
        target_type="account",
        target_id=account.id,
        message=f"Secure automatic-login credential updated for {account.display_name}.",
    )
    session.commit()
    session.refresh(account)
    if previous_reference:
        with suppress(OSError):
            vault.delete(previous_reference)
    return account


def delete_account(
    session: Session,
    account: Account,
    *,
    vault: CredentialVault,
    actor: str,
    instance_remover: Callable[[Account], None] | None = None,
) -> None:
    has_source_history = session.scalar(
        select(func.count(SourceTradeEvent.id)).where(
            SourceTradeEvent.source_account_id == account.id
        )
    )
    has_follower_history = session.scalar(
        select(func.count(CopyJob.id)).where(CopyJob.follower_account_id == account.id)
    )
    if has_source_history or has_follower_history:
        raise ValueError(
            "Accounts with trade history cannot be deleted; disable the account instead."
        )

    if instance_remover is not None:
        instance_remover(account)
    if account.is_master:
        state = ensure_system_state(session)
        state.active_master_account_id = None
        state.global_pause = True
        state.execution_mode = ExecutionMode.MONITOR.value
        state.reason = "Master account removed"
    if account.credential_ref:
        vault.delete(account.credential_ref)
    display_name = account.display_name
    account_id = account.id
    session.delete(account)
    record_audit(
        session,
        actor=actor,
        action="account.deleted",
        target_type="account",
        target_id=account_id,
        severity=AuditSeverity.WARNING,
        message=f"Account {display_name} was deleted.",
    )
    session.commit()
