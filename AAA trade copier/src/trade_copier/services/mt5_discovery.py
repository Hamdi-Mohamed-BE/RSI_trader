import importlib
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psutil
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.enums import (
    AccountRole,
    AccountState,
    ExecutionMode,
    TerminalHealth,
)
from ..models import Account, TerminalInstance
from .accounts import ensure_system_state
from .audit import record_audit

logger = logging.getLogger(__name__)
TERMINAL_NAMES = {"terminal.exe", "terminal64.exe"}


@dataclass(frozen=True)
class DetectedMt5Account:
    login: str
    server: str
    account_name: str
    currency: str
    trade_mode: str
    position_mode: str
    balance: Decimal
    equity: Decimal
    free_margin: Decimal
    terminal_path: str
    process_id: int


def _running_terminals() -> list[tuple[int, Path]]:
    terminals: list[tuple[int, Path]] = []
    if os.name != "nt":
        return terminals
    for process in psutil.process_iter(["pid", "name", "exe"]):
        try:
            name = str(process.info.get("name") or "").lower()
            executable = process.info.get("exe")
            if name not in TERMINAL_NAMES or not executable:
                continue
            path = Path(str(executable)).resolve(strict=True)
            terminals.append((int(process.info["pid"]), path))
        except (OSError, psutil.Error, ValueError):
            continue
    return sorted(set(terminals), key=lambda item: item[0])


def discover_running_mt5_accounts() -> list[DetectedMt5Account]:
    """Read logged-in accounts from MT5 processes that are already running."""

    terminals = _running_terminals()
    if not terminals:
        return []
    try:
        mt5: Any = importlib.import_module("MetaTrader5")
    except ImportError:
        logger.warning("MetaTrader5 package is unavailable; connected-account detection skipped.")
        return []

    detected: list[DetectedMt5Account] = []
    seen: set[tuple[str, str]] = set()
    for process_id, executable in terminals:
        try:
            portable = (executable.parent / ".aaa-instance.json").is_file()
            if not mt5.initialize(str(executable), timeout=5000, portable=portable):
                continue
            account = mt5.account_info()
            terminal = mt5.terminal_info()
            if account is None or terminal is None or not bool(terminal.connected):
                continue
            login = str(account.login)
            server = str(account.server or "Unknown server")
            identity = (login, server)
            if identity in seen:
                continue
            seen.add(identity)
            trade_mode = (
                "demo"
                if account.trade_mode == getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)
                else "live"
            )
            position_mode = (
                "hedging"
                if account.margin_mode == getattr(mt5, "ACCOUNT_MARGIN_MODE_RETAIL_HEDGING", 2)
                else "netting"
            )
            detected.append(
                DetectedMt5Account(
                    login=login,
                    server=server,
                    account_name=str(account.name or ""),
                    currency=str(account.currency or "USD"),
                    trade_mode=trade_mode,
                    position_mode=position_mode,
                    balance=Decimal(str(account.balance)),
                    equity=Decimal(str(account.equity)),
                    free_margin=Decimal(str(account.margin_free)),
                    terminal_path=str(executable),
                    process_id=process_id,
                )
            )
        except (OSError, RuntimeError, ValueError) as exc:
            logger.warning("Could not inspect MT5 process %s: %s", process_id, exc)
        finally:
            mt5.shutdown()
    return detected


def _unique_display_name(session: Session, detected: DetectedMt5Account) -> str:
    base = detected.account_name.strip() or f"MT5 {detected.server}"
    candidate = base[:120]
    suffix = 2
    while session.scalar(select(Account.id).where(Account.display_name == candidate)):
        marker = f" {suffix}"
        candidate = f"{base[: 120 - len(marker)]}{marker}"
        suffix += 1
    return candidate


def import_detected_accounts(
    session: Session,
    detected_accounts: list[DetectedMt5Account],
    *,
    actor: str,
) -> list[Account]:
    imported: list[Account] = []
    active_master = session.scalar(select(Account).where(Account.is_master.is_(True)))
    state = ensure_system_state(session)
    now = datetime.now(UTC)

    for detected in detected_accounts:
        account = session.scalar(
            select(Account).where(
                Account.login == detected.login,
                Account.broker_server == detected.server,
            )
        )
        is_new = account is None
        becomes_master = active_master is None and not imported
        if account is None:
            account = Account(
                display_name=_unique_display_name(session, detected),
                login=detected.login,
                broker_server=detected.server,
                role=(
                    AccountRole.MASTER_CANDIDATE.value
                    if becomes_master
                    else AccountRole.FOLLOWER.value
                ),
                state=(AccountState.ACTIVE.value if becomes_master else AccountState.PAUSED.value),
                is_master=becomes_master,
            )
            session.add(account)
            session.flush()

        account.terminal_path = detected.terminal_path
        account.account_currency = detected.currency
        account.trade_mode = detected.trade_mode
        account.position_mode = detected.position_mode
        account.balance = detected.balance
        account.equity = detected.equity
        account.free_margin = detected.free_margin
        account.health = TerminalHealth.HEALTHY.value
        account.last_heartbeat_at = now

        terminal = account.terminal
        if terminal is None:
            terminal = TerminalInstance(account_id=account.id)
            account.terminal = terminal
        terminal.process_id = detected.process_id
        terminal.portable_directory = str(Path(detected.terminal_path).parent)
        terminal.health = TerminalHealth.HEALTHY.value
        terminal.last_error = ""
        terminal.last_seen_at = now
        session.add(terminal)

        if becomes_master:
            account.role = AccountRole.MASTER_CANDIDATE.value
            account.state = AccountState.ACTIVE.value
            account.is_master = True
            active_master = account
            state.active_master_account_id = account.id
            state.global_pause = True
            state.execution_mode = ExecutionMode.MONITOR.value
            state.reason = "Connected MT5 detected as master; review and enable explicitly"

        if is_new:
            record_audit(
                session,
                actor=actor,
                action="account.auto_detected",
                target_type="account",
                target_id=account.id,
                message=(
                    f"Detected connected MT5 account {account.masked_login} "
                    f"on {account.broker_server}."
                ),
                details={"master": becomes_master, "process_id": detected.process_id},
            )
        imported.append(account)

    session.commit()
    return imported


def detect_and_import_running_accounts(session: Session, *, actor: str) -> list[Account]:
    return import_detected_accounts(session, discover_running_mt5_accounts(), actor=actor)
