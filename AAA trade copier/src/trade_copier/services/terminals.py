import os
import subprocess
from pathlib import Path

from sqlalchemy.orm import Session

from ..domain.enums import TerminalHealth
from ..models import Account, TerminalInstance
from .audit import record_audit

ALLOWED_TERMINAL_NAMES = {"terminal.exe", "terminal64.exe"}


class TerminalManager:
    """Starts a previously prepared portable MT5 terminal without exposing secrets.

    Account credentials are deliberately never added to command-line arguments.
    The portable terminal must already contain an MT5-managed saved session.
    """

    @staticmethod
    def _validated_executable(account: Account) -> Path:
        if os.name != "nt":
            raise RuntimeError("MT5 terminal management is available only on Windows.")
        if not account.terminal_path:
            raise ValueError("No terminal executable is configured for this account.")
        executable = Path(account.terminal_path).expanduser().resolve(strict=True)
        if not executable.is_file() or executable.name.lower() not in ALLOWED_TERMINAL_NAMES:
            raise ValueError("Terminal path must point to terminal.exe or terminal64.exe.")
        return executable

    def start(self, session: Session, account: Account, *, actor: str) -> TerminalInstance:
        executable = self._validated_executable(account)
        terminal = account.terminal or TerminalInstance(account_id=account.id)
        if terminal.process_id and self.is_running(terminal.process_id):
            raise ValueError("This terminal process is already running.")

        process = subprocess.Popen(
            [str(executable), "/portable"],
            cwd=executable.parent,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        terminal.process_id = process.pid
        terminal.portable_directory = str(executable.parent)
        terminal.health = TerminalHealth.STARTING.value
        session.add(terminal)
        record_audit(
            session,
            actor=actor,
            action="terminal.started",
            target_type="account",
            target_id=account.id,
            message=f"Portable terminal started for {account.display_name}.",
            details={"process_id": process.pid},
        )
        session.commit()
        session.refresh(terminal)
        return terminal

    @staticmethod
    def is_running(process_id: int) -> bool:
        if process_id <= 0:
            return False
        try:
            os.kill(process_id, 0)
        except OSError:
            return False
        return True
