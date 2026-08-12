import importlib
import json
import os
import shutil
import subprocess
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psutil
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import Account
from .accounts import ensure_system_state
from .audit import record_audit

PROJECT_DIR = Path(__file__).resolve().parents[3]
AGENT_VERSION = 1
TERMINAL_NAMES = {"terminal.exe", "terminal64.exe"}


@dataclass(frozen=True)
class AgentBootstrapResult:
    account_id: str
    display_name: str
    role: str
    installed: bool
    attached: bool
    terminal_restarted: bool
    message: str


class Mt5AgentBootstrapper:
    """Installs MT5 agents and auto-attaches the publisher to the active master."""

    def __init__(
        self,
        *,
        settings: Settings,
        mt5_module: Any | None = None,
        platform_name: str = os.name,
    ) -> None:
        self.settings = settings
        self.mt5_module = mt5_module
        self.platform_name = platform_name

    def _connector(self) -> Any:
        if self.mt5_module is not None:
            return self.mt5_module
        try:
            return importlib.import_module("MetaTrader5")
        except ImportError as exc:
            raise RuntimeError("The MetaTrader5 Python connector is not installed.") from exc

    @staticmethod
    def _terminal_path(account: Account) -> Path:
        if not account.terminal_path:
            raise ValueError(f"{account.display_name} has no MT5 terminal assigned.")
        executable = Path(account.terminal_path).expanduser().resolve(strict=True)
        if not executable.is_file() or executable.name.lower() not in TERMINAL_NAMES:
            raise ValueError(f"{account.display_name} has an invalid MT5 terminal path.")
        return executable

    @staticmethod
    def _portable(executable: Path) -> bool:
        return (executable.parent / ".aaa-instance.json").is_file()

    @staticmethod
    def _choose_symbol(connector: Any) -> str:
        positions = connector.positions_get() or ()
        if positions:
            return str(positions[0].symbol)
        orders = connector.orders_get() or ()
        if orders:
            return str(orders[0].symbol)
        for preferred in ("EURUSD", "XAUUSD", "GBPUSD", "USDJPY"):
            info = connector.symbol_info(preferred)
            if info is not None and connector.symbol_select(preferred, True):
                return preferred
        symbols = connector.symbols_get() or ()
        for symbol in symbols:
            name = str(getattr(symbol, "name", "") or "")
            if name and bool(getattr(symbol, "visible", False)):
                return name
        if symbols:
            return str(getattr(symbols[0], "name", "") or "")
        raise ValueError("MT5 has no available symbol for the publisher control chart.")

    def _terminal_details(self, account: Account) -> tuple[Path, Path, str, bool]:
        executable = self._terminal_path(account)
        portable = self._portable(executable)
        connector = self._connector()
        try:
            if not connector.initialize(str(executable), timeout=30_000, portable=portable):
                raise ValueError(
                    f"Could not connect to {account.display_name}: {connector.last_error()}"
                )
            account_info = connector.account_info()
            terminal_info = connector.terminal_info()
            if account_info is None or terminal_info is None:
                raise ValueError(f"{account.display_name} did not return its MT5 state.")
            if str(account_info.login) != account.login:
                raise ValueError(
                    f"{account.display_name} MT5 is logged into account {account_info.login}, "
                    f"not {account.login}."
                )
            if not bool(getattr(terminal_info, "connected", False)):
                raise ValueError(f"{account.display_name} MT5 is disconnected.")
            data_path = Path(str(terminal_info.data_path)).resolve()
            symbol = self._choose_symbol(connector)
            return executable, data_path, symbol, portable
        finally:
            with suppress(AttributeError, RuntimeError):
                connector.shutdown()

    @staticmethod
    def _install_files(data_path: Path) -> None:
        source = PROJECT_DIR / "mt5"
        experts_target = data_path / "MQL5" / "Experts" / "AAA"
        include_target = data_path / "MQL5" / "Include" / "AAA"
        experts_target.mkdir(parents=True, exist_ok=True)
        include_target.mkdir(parents=True, exist_ok=True)
        for name in (
            "AAA_Master_Publisher.ex5",
            "AAA_Master_Publisher.mq5",
            "AAA_Follower_Executor.ex5",
            "AAA_Follower_Executor.mq5",
        ):
            candidate = source / "Experts" / name
            if not candidate.is_file():
                raise ValueError(f"Required MT5 agent is missing: {candidate}")
            shutil.copy2(candidate, experts_target / name)
        shutil.copy2(
            source / "Include" / "AAA" / "CopierProtocol.mqh",
            include_target / "CopierProtocol.mqh",
        )

    def _publisher_files(
        self,
        *,
        account: Account,
        data_path: Path,
        symbol: str,
        portable: bool,
    ) -> tuple[Path, Path, Path]:
        preset_name = f"AAA_Master_{account.id}.set"
        preset_path = data_path / "MQL5" / "Presets" / preset_name
        preset_path.parent.mkdir(parents=True, exist_ok=True)
        preset_path.write_text(
            "\n".join(
                (
                    "InpPublisherEnabled=true",
                    f"InpSourceAccountId={account.id}",
                    f"InpMasterPipeName={self.settings.master_pipe_name}",
                    "InpReconnectMs=250",
                    "",
                )
            ),
            encoding="utf-8",
        )

        config_root = self.settings.storage_dir / "mt5_agents"
        config_root.mkdir(parents=True, exist_ok=True)
        config_path = (config_root / f"master-{account.id}.ini").resolve()
        config_path.write_text(
            "\n".join(
                (
                    "[Common]",
                    f"Login={account.login}",
                    "KeepPrivate=1",
                    "",
                    "[Experts]",
                    "AllowLiveTrading=1",
                    "AllowDllImport=0",
                    "Enabled=1",
                    "Account=0",
                    "Profile=0",
                    "",
                    "[StartUp]",
                    "Expert=AAA\\AAA_Master_Publisher",
                    f"ExpertParameters={preset_name}",
                    f"Symbol={symbol}",
                    "Period=M1",
                    "ShutdownTerminal=0",
                    "",
                )
            ),
            encoding="utf-8",
        )
        marker_path = data_path / ".aaa-master-agent.json"
        marker_payload = {
            "version": AGENT_VERSION,
            "account_id": account.id,
            "login": account.login,
            "pipe": self.settings.master_pipe_name,
            "symbol": symbol,
            "portable": portable,
            "config": str(config_path),
        }
        marker_path.write_text(json.dumps(marker_payload, indent=2), encoding="utf-8")
        return preset_path, config_path, marker_path

    @staticmethod
    def _terminal_processes(executable: Path) -> list[psutil.Process]:
        matches: list[psutil.Process] = []
        for process in psutil.process_iter(["pid", "exe", "create_time"]):
            try:
                process_path = process.info.get("exe")
                if process_path and Path(str(process_path)).resolve() == executable:
                    matches.append(process)
            except (OSError, psutil.Error, ValueError):
                continue
        return matches

    @classmethod
    def _attachment_is_current(
        cls,
        executable: Path,
        marker_path: Path,
        *,
        account_id: str,
        pipe_name: str,
        config_path: Path,
    ) -> bool:
        if not marker_path.is_file():
            return False
        try:
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            return False
        if marker.get("version") != AGENT_VERSION:
            return False
        if marker.get("account_id") != account_id or marker.get("pipe") != pipe_name:
            return False
        processes = cls._terminal_processes(executable)
        if not processes:
            return False
        expected = f"/config:{config_path}".casefold()
        for process in processes:
            try:
                arguments = [str(value).casefold() for value in process.cmdline()]
                if expected in arguments:
                    return True
            except (OSError, psutil.Error):
                continue
        return False

    @classmethod
    def _restart_with_config(
        cls,
        executable: Path,
        config_path: Path,
        *,
        portable: bool,
    ) -> None:
        processes = cls._terminal_processes(executable)
        for process in processes:
            process.terminate()
        _, alive = psutil.wait_procs(processes, timeout=15)
        for process in alive:
            process.kill()
        arguments = [str(executable), f"/config:{config_path}"]
        if portable:
            arguments.append("/portable")
        subprocess.Popen(
            arguments,
            cwd=str(executable.parent),
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )

    def bootstrap(self, session: Session, *, actor: str) -> list[AgentBootstrapResult]:
        if self.platform_name != "nt":
            raise RuntimeError("MT5 agent bootstrap is available only on Windows.")
        state = ensure_system_state(session)
        accounts = session.scalars(select(Account).order_by(Account.is_master.desc())).all()
        if not accounts:
            return []
        results: list[AgentBootstrapResult] = []
        for account in accounts:
            try:
                executable, data_path, symbol, portable = self._terminal_details(account)
                self._install_files(data_path)
                if account.id != state.active_master_account_id or not account.is_master:
                    results.append(
                        AgentBootstrapResult(
                            account_id=account.id,
                            display_name=account.display_name,
                            role="follower",
                            installed=True,
                            attached=False,
                            terminal_restarted=False,
                            message="Executor files installed; Python execution needs no chart EA.",
                        )
                    )
                    continue

                marker_path = data_path / ".aaa-master-agent.json"
                config_path = (
                    self.settings.storage_dir / "mt5_agents" / f"master-{account.id}.ini"
                ).resolve()
                current = self._attachment_is_current(
                    executable,
                    marker_path,
                    account_id=account.id,
                    pipe_name=self.settings.master_pipe_name,
                    config_path=config_path,
                )
                _, written_config_path, marker_path = self._publisher_files(
                    account=account,
                    data_path=data_path,
                    symbol=symbol,
                    portable=portable,
                )
                if written_config_path != config_path:
                    raise RuntimeError("The generated MT5 startup configuration path changed.")
                if current:
                    message = "Master Publisher is already attached to the running MT5."
                    restarted = False
                else:
                    self._restart_with_config(
                        executable,
                        config_path,
                        portable=portable,
                    )
                    time.sleep(2)
                    message = "Master MT5 restarted with AAA Master Publisher attached."
                    restarted = True
                record_audit(
                    session,
                    actor=actor,
                    action="mt5_agent.master_bootstrapped",
                    target_type="account",
                    target_id=account.id,
                    message=message,
                    details={
                        "data_path": str(data_path),
                        "symbol": symbol,
                        "restarted": restarted,
                        "marker": str(marker_path),
                    },
                )
                session.commit()
                results.append(
                    AgentBootstrapResult(
                        account_id=account.id,
                        display_name=account.display_name,
                        role="master",
                        installed=True,
                        attached=True,
                        terminal_restarted=restarted,
                        message=message,
                    )
                )
            except (OSError, psutil.Error, RuntimeError, TypeError, ValueError) as exc:
                results.append(
                    AgentBootstrapResult(
                        account_id=account.id,
                        display_name=account.display_name,
                        role="master" if account.is_master else "follower",
                        installed=False,
                        attached=False,
                        terminal_restarted=False,
                        message=str(exc),
                    )
                )
        return results
