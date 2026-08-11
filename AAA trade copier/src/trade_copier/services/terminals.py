import importlib
import json
import logging
import os
import re
import shutil
from contextlib import suppress
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psutil
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.enums import AccountRole, AccountState, AuditSeverity, TerminalHealth
from ..models import Account, AccountSymbolSpec, SymbolMapping, TerminalInstance
from .audit import record_audit
from .credentials import CredentialVault

logger = logging.getLogger(__name__)
ALLOWED_TERMINAL_NAMES = {"terminal.exe", "terminal64.exe"}
PROJECT_DIR = Path(__file__).resolve().parents[3]
SYMBOL_ALIASES: dict[str, set[str]] = {
    "BTCUSD": {"XBTUSD"},
    "GER40": {"DE40", "DAX", "DAX40"},
    "NAS100": {"NASDAQ", "NASDAQ100", "NDX", "US100", "USTEC", "USTECH"},
    "SPX500": {"SP500", "SPX", "US500"},
    "UK100": {"FTSE", "FTSE100"},
    "US30": {"DJ30", "DJI", "DOW", "WALLSTREET", "WS30"},
    "XAGUSD": {"SILVER"},
    "XAUUSD": {"GOLD"},
}


class SymbolResolutionError(ValueError):
    pass


class TerminalManager:
    """Builds, starts, logs into, and refreshes one isolated MT5 per account."""

    def __init__(
        self,
        *,
        instances_root: Path | None = None,
        vault: CredentialVault | None = None,
        default_template_path: str = "",
        mt5_module: Any | None = None,
        platform_name: str = os.name,
    ) -> None:
        self.instances_root = (instances_root or Path("storage/mt5_instances")).resolve()
        self.vault = vault
        self.default_template_path = default_template_path.strip()
        self.mt5_module = mt5_module
        self.platform_name = platform_name

    def _require_windows(self) -> None:
        if self.platform_name != "nt":
            raise RuntimeError("Managed MT5 instances are available only on Windows.")

    @staticmethod
    def _validated_executable_path(value: str) -> Path:
        executable = Path(value).expanduser().resolve(strict=True)
        if not executable.is_file() or executable.name.lower() not in ALLOWED_TERMINAL_NAMES:
            raise ValueError("MT5 template must point to terminal.exe or terminal64.exe.")
        return executable

    def _instance_directory(self, account: Account) -> Path:
        if Path(account.id).name != account.id:
            raise ValueError("Invalid account identity for an MT5 instance.")
        directory = (self.instances_root / account.id).resolve()
        if directory.parent != self.instances_root:
            raise ValueError("MT5 instance path escaped its managed storage directory.")
        return directory

    def _is_managed_executable(self, executable: Path, account: Account) -> bool:
        return executable.parent == self._instance_directory(account)

    def _has_managed_executable(self, account: Account) -> bool:
        if not account.terminal_path:
            return False
        executable = Path(account.terminal_path).expanduser().resolve()
        return executable.is_file() and self._is_managed_executable(executable, account)

    @staticmethod
    def _installed_terminal_candidates() -> list[Path]:
        candidates: set[Path] = set()
        for process in psutil.process_iter(["name", "exe"]):
            try:
                name = str(process.info.get("name") or "").lower()
                executable = process.info.get("exe")
                if name in ALLOWED_TERMINAL_NAMES and executable:
                    candidates.add(Path(str(executable)).resolve(strict=True))
            except (OSError, psutil.Error, ValueError):
                continue
        for variable in ("ProgramFiles", "ProgramFiles(x86)"):
            root_value = os.environ.get(variable)
            if not root_value:
                continue
            root = Path(root_value)
            for terminal_name in ALLOWED_TERMINAL_NAMES:
                for executable in root.glob(f"*/{terminal_name}"):
                    if executable.is_file():
                        candidates.add(executable.resolve())
        return sorted(candidates)

    @staticmethod
    def _broker_match_score(executable: Path, broker_server: str) -> tuple[int, int]:
        normalized_path = re.sub(r"[^a-z0-9]", "", str(executable.parent).lower())
        broker_parts = [
            part
            for part in re.split(r"[^a-z0-9]+", broker_server.lower())
            if len(part) >= 4 and part not in {"demo", "live", "server"}
        ]
        score = sum(10 for part in broker_parts if part in normalized_path)
        if executable.name.lower() == "terminal64.exe":
            score += 1
        return score, -len(str(executable))

    def _select_template(self, account: Account, requested_path: str = "") -> Path:
        explicit_paths = [requested_path, self.default_template_path]
        for value in explicit_paths:
            if value.strip():
                return self._validated_executable_path(value)

        if account.terminal_path:
            try:
                current = self._validated_executable_path(account.terminal_path)
            except (OSError, ValueError):
                current = None
            if current is not None:
                return current

        candidates = self._installed_terminal_candidates()
        if not candidates:
            raise ValueError(
                "No MT5 installation was found. Install MT5 or provide its terminal64.exe path."
            )
        return max(
            candidates,
            key=lambda item: self._broker_match_score(item, account.broker_server),
        )

    @staticmethod
    def _copy_runtime(source_directory: Path, target_directory: Path) -> None:
        def ignore_runtime_noise(directory: str, names: list[str]) -> set[str]:
            del directory
            ignored = {"logs", "crashlogs", "tester"}
            return {name for name in names if name.lower() in ignored}

        shutil.copytree(
            source_directory,
            target_directory,
            dirs_exist_ok=True,
            ignore=ignore_runtime_noise,
        )

    @staticmethod
    def _install_copier_agents(target_directory: Path) -> None:
        integration_dir = PROJECT_DIR / "mt5"
        experts_source = integration_dir / "Experts"
        include_source = integration_dir / "Include" / "AAA"
        experts_target = target_directory / "MQL5" / "Experts" / "AAA"
        include_target = target_directory / "MQL5" / "Include" / "AAA"
        experts_target.mkdir(parents=True, exist_ok=True)
        include_target.mkdir(parents=True, exist_ok=True)
        for extension in ("*.ex5", "*.mq5"):
            for source in experts_source.glob(extension):
                shutil.copy2(source, experts_target / source.name)
        if include_source.is_dir():
            shutil.copytree(include_source, include_target, dirs_exist_ok=True)

    def provision(
        self,
        session: Session,
        account: Account,
        *,
        actor: str,
        template_path: str = "",
    ) -> Path:
        """Create or update the account's own portable MT5 directory."""
        self._require_windows()
        source = self._select_template(account, template_path)
        target_directory = self._instance_directory(account)
        target_executable = target_directory / source.name

        if source != target_executable:
            self.instances_root.mkdir(parents=True, exist_ok=True)
            self._copy_runtime(source.parent, target_directory)
        self._install_copier_agents(target_directory)
        if not target_executable.is_file():
            raise ValueError("The managed MT5 copy does not contain its terminal executable.")

        marker = {
            "account_id": account.id,
            "login": account.login,
            "server": account.broker_server,
        }
        (target_directory / ".aaa-instance.json").write_text(
            json.dumps(marker, indent=2), encoding="utf-8"
        )
        terminal = account.terminal or TerminalInstance(account_id=account.id)
        terminal.portable_directory = str(target_directory)
        terminal.health = TerminalHealth.STARTING.value
        terminal.last_error = ""
        account.terminal_path = str(target_executable)
        account.health = TerminalHealth.STARTING.value
        session.add(terminal)
        record_audit(
            session,
            actor=actor,
            action="terminal.provisioned",
            target_type="account",
            target_id=account.id,
            message=f"Isolated portable MT5 instance prepared for {account.display_name}.",
            details={"directory": str(target_directory), "template": str(source)},
        )
        session.commit()
        session.refresh(account)
        return target_executable

    def _connector(self) -> Any:
        if self.mt5_module is not None:
            return self.mt5_module
        try:
            return importlib.import_module("MetaTrader5")
        except ImportError as exc:
            raise RuntimeError("The MetaTrader5 Python connector is not installed.") from exc

    @staticmethod
    def _last_error(connector: Any) -> str:
        try:
            return str(connector.last_error())
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return "unknown MT5 error"

    @staticmethod
    def _decimal_attribute(source: Any, *names: str) -> Decimal:
        for name in names:
            value = getattr(source, name, None)
            if value is None:
                continue
            result = Decimal(str(value))
            if result > 0:
                return result
        raise ValueError(f"MT5 did not provide a positive {names[0].replace('_', ' ')}.")

    @staticmethod
    def _process_id(executable: Path) -> int | None:
        for process in psutil.process_iter(["pid", "exe"]):
            try:
                process_path = process.info.get("exe")
                if process_path and Path(str(process_path)).resolve() == executable:
                    return int(process.info["pid"])
            except (OSError, psutil.Error, ValueError):
                continue
        return None

    @staticmethod
    def _normalized_symbol(value: str) -> str:
        return re.sub(r"[^A-Z0-9]", "", value.upper())

    @classmethod
    def _symbol_match_score(cls, requested: str, candidate: Any) -> int:
        target = cls._normalized_symbol(requested)
        name = cls._normalized_symbol(str(getattr(candidate, "name", "")))
        if not name:
            return 0
        aliases = {target, *SYMBOL_ALIASES.get(target, set())}
        score = 0
        for alias in aliases:
            if name == alias:
                score = max(score, 1_000)
            elif name.startswith(alias):
                score = max(score, 850 - (len(name) - len(alias)))
            elif name.endswith(alias):
                score = max(score, 825 - (len(name) - len(alias)))
            elif alias in name:
                score = max(score, 750 - (len(name) - len(alias)))

        if len(target) == 6:
            requested_base = target[:3].replace("XBT", "BTC")
            requested_profit = target[3:].replace("XBT", "BTC")
            candidate_base = cls._normalized_symbol(
                str(getattr(candidate, "currency_base", ""))
            ).replace("XBT", "BTC")
            candidate_profit = cls._normalized_symbol(
                str(getattr(candidate, "currency_profit", ""))
            ).replace("XBT", "BTC")
            if (candidate_base, candidate_profit) == (requested_base, requested_profit):
                score = max(score, 950)

        if bool(getattr(candidate, "visible", False)):
            score += 10
        if bool(getattr(candidate, "select", False)):
            score += 5
        return score

    @staticmethod
    def _is_tradable_symbol(connector: Any, info: Any) -> bool:
        disabled_mode = getattr(connector, "SYMBOL_TRADE_MODE_DISABLED", 0)
        return getattr(info, "trade_mode", disabled_mode) != disabled_mode

    def _resolve_symbol(self, connector: Any, requested: str) -> tuple[str, Any]:
        info = connector.symbol_info(requested)
        if info is not None and self._is_tradable_symbol(connector, info):
            resolved = str(getattr(info, "name", requested) or requested)
            if connector.symbol_select(resolved, True) or bool(
                getattr(info, "select", False)
            ):
                return resolved, connector.symbol_info(resolved) or info
        else:
            connector.symbol_select(requested, True)
            info = connector.symbol_info(requested)
            if info is not None and self._is_tradable_symbol(connector, info):
                return str(getattr(info, "name", requested) or requested), info

        try:
            available = connector.symbols_get() or ()
        except (AttributeError, RuntimeError, TypeError, ValueError):
            available = ()
        ranked = sorted(
            (
                (self._symbol_match_score(requested, candidate), candidate)
                for candidate in available
                if self._is_tradable_symbol(connector, candidate)
            ),
            key=lambda item: (
                item[0],
                -len(str(getattr(item[1], "name", ""))),
                str(getattr(item[1], "name", "")),
            ),
            reverse=True,
        )
        for score, candidate in ranked:
            if score < 700:
                break
            resolved = str(getattr(candidate, "name", ""))
            if not resolved or not connector.symbol_select(resolved, True):
                continue
            resolved_info = connector.symbol_info(resolved)
            if resolved_info is not None and self._is_tradable_symbol(
                connector, resolved_info
            ):
                return resolved, resolved_info
        raise SymbolResolutionError(
            f"No tradable broker symbol matching {requested} was found on this account."
        )

    @staticmethod
    def _save_auto_mapping(
        session: Session,
        account: Account,
        master_symbol: str,
        follower_symbol: str,
        *,
        actor: str,
    ) -> None:
        master_symbol = master_symbol.strip().upper()
        mapping = session.scalar(
            select(SymbolMapping).where(
                SymbolMapping.follower_account_id == account.id,
                SymbolMapping.master_symbol == master_symbol,
            )
        )
        previous_symbol = mapping.follower_symbol if mapping else ""
        if mapping is None:
            mapping = SymbolMapping(
                follower_account_id=account.id,
                master_symbol=master_symbol,
                follower_symbol=follower_symbol,
            )
        mapping.follower_symbol = follower_symbol
        mapping.enabled = True
        session.add(mapping)
        if previous_symbol != follower_symbol:
            record_audit(
                session,
                actor=actor,
                action="symbol_mapping.auto_detected",
                target_type="account",
                target_id=account.id,
                message=(
                    f"Automatically mapped {master_symbol} to {follower_symbol} for "
                    f"{account.display_name}."
                ),
                details={
                    "master_symbol": master_symbol,
                    "follower_symbol": follower_symbol,
                },
            )

    def _sync_symbol(
        self,
        session: Session,
        account: Account,
        connector: Any,
        symbol: str,
        fallback_symbol: str | None = None,
    ) -> str:
        try:
            resolved_symbol, info = self._resolve_symbol(connector, symbol)
        except ValueError:
            if not fallback_symbol or fallback_symbol.upper() == symbol.upper():
                raise
            resolved_symbol, info = self._resolve_symbol(connector, fallback_symbol)

        specification = session.scalar(
            select(AccountSymbolSpec).where(
                AccountSymbolSpec.account_id == account.id,
                AccountSymbolSpec.symbol == resolved_symbol,
            )
        )
        if specification is None:
            specification = AccountSymbolSpec(
                account_id=account.id,
                symbol=resolved_symbol,
            )
        specification.tick_size = self._decimal_attribute(info, "trade_tick_size", "point")
        specification.tick_value = self._decimal_attribute(
            info,
            "trade_tick_value_loss",
            "trade_tick_value",
            "trade_tick_value_profit",
        )
        specification.volume_min = self._decimal_attribute(info, "volume_min")
        specification.volume_max = self._decimal_attribute(info, "volume_max")
        specification.volume_step = self._decimal_attribute(info, "volume_step")
        specification.contract_size = self._decimal_attribute(info, "trade_contract_size")
        specification.spread_points = max(0, int(getattr(info, "spread", 0)))
        disabled_mode = getattr(connector, "SYMBOL_TRADE_MODE_DISABLED", 0)
        specification.trading_enabled = getattr(info, "trade_mode", disabled_mode) != disabled_mode
        session.add(specification)
        return resolved_symbol

    def _mark_failure(
        self,
        session: Session,
        account: Account,
        message: str,
        *,
        actor: str,
    ) -> None:
        terminal = account.terminal or TerminalInstance(account_id=account.id)
        terminal.health = TerminalHealth.DEGRADED.value
        terminal.last_error = message
        account.health = TerminalHealth.DEGRADED.value
        session.add(terminal)
        record_audit(
            session,
            actor=actor,
            action="terminal.login_failed",
            target_type="account",
            target_id=account.id,
            severity=AuditSeverity.WARNING,
            message=message,
        )
        session.commit()

    @staticmethod
    def _mark_symbol_failure(
        session: Session,
        account: Account,
        message: str,
        *,
        actor: str,
    ) -> None:
        terminal = account.terminal or TerminalInstance(account_id=account.id)
        terminal.health = TerminalHealth.HEALTHY.value
        terminal.last_error = message
        account.health = TerminalHealth.HEALTHY.value
        session.add(terminal)
        record_audit(
            session,
            actor=actor,
            action="symbol_mapping.auto_detect_failed",
            target_type="account",
            target_id=account.id,
            severity=AuditSeverity.WARNING,
            message=message,
        )
        session.commit()

    def connect(
        self,
        session: Session,
        account: Account,
        *,
        actor: str,
        symbol: str | None = None,
        master_symbol: str | None = None,
    ) -> TerminalInstance:
        """Start the account's terminal and log in through the MT5 API."""
        self._require_windows()
        if not account.terminal_path:
            raise ValueError("This account has no managed MT5 instance yet.")
        executable = self._validated_executable_path(account.terminal_path)
        connector = self._connector()
        try:
            initialized = bool(
                connector.initialize(
                    str(executable),
                    timeout=60_000,
                    portable=True,
                )
            )
            if not initialized:
                raise ValueError(f"MT5 could not start: {self._last_error(connector)}")

            if account.credential_ref:
                if self.vault is None:
                    raise ValueError("The secure MT5 credential vault is unavailable.")
                password = self.vault.retrieve(account.credential_ref)
                logged_in = bool(
                    connector.login(
                        int(account.login),
                        password=password,
                        server=account.broker_server,
                        timeout=60_000,
                    )
                )
                if not logged_in:
                    raise ValueError(f"MT5 login was rejected: {self._last_error(connector)}")

            account_info = connector.account_info()
            terminal_info = connector.terminal_info()
            if account_info is None or terminal_info is None:
                raise ValueError("MT5 started but did not return account or terminal information.")
            if not bool(getattr(terminal_info, "connected", False)):
                raise ValueError("MT5 started but is not connected to the broker.")
            if str(account_info.login) != account.login:
                raise ValueError(
                    "MT5 opened a different saved account. Enter this account's password to "
                    "replace the saved session."
                )

            account.account_currency = str(getattr(account_info, "currency", "USD") or "USD")
            account.balance = Decimal(str(account_info.balance))
            account.equity = Decimal(str(account_info.equity))
            account.free_margin = Decimal(str(account_info.margin_free))
            account.trade_mode = (
                "demo"
                if account_info.trade_mode == getattr(connector, "ACCOUNT_TRADE_MODE_DEMO", 0)
                else "live"
            )
            account.position_mode = (
                "hedging"
                if account_info.margin_mode
                == getattr(connector, "ACCOUNT_MARGIN_MODE_RETAIL_HEDGING", 2)
                else "netting"
            )
            now = datetime.now(UTC)
            account.health = TerminalHealth.HEALTHY.value
            account.last_heartbeat_at = now
            terminal = account.terminal or TerminalInstance(account_id=account.id)
            terminal.process_id = self._process_id(executable)
            terminal.portable_directory = str(executable.parent)
            terminal.terminal_build = str(getattr(terminal_info, "build", ""))
            terminal.algo_trading_enabled = bool(
                getattr(terminal_info, "trade_allowed", False)
            )
            terminal.health = TerminalHealth.HEALTHY.value
            terminal.last_error = ""
            terminal.last_seen_at = now
            session.add(terminal)
            resolved_symbol = ""
            if symbol:
                resolved_symbol = self._sync_symbol(
                    session,
                    account,
                    connector,
                    symbol,
                    master_symbol,
                )
                if master_symbol and account.role == AccountRole.FOLLOWER.value:
                    self._save_auto_mapping(
                        session,
                        account,
                        master_symbol,
                        resolved_symbol,
                        actor=actor,
                    )
            record_audit(
                session,
                actor=actor,
                action="terminal.logged_in",
                target_type="account",
                target_id=account.id,
                message=f"Managed MT5 logged into {account.masked_login}.",
                details={
                    "process_id": terminal.process_id,
                    "requested_symbol": symbol or "",
                    "resolved_symbol": resolved_symbol,
                },
            )
            session.commit()
            session.refresh(terminal)
            return terminal
        except SymbolResolutionError as exc:
            message = f"Automatic symbol discovery failed: {exc!s}"
            self._mark_symbol_failure(session, account, message, actor=actor)
            raise ValueError(message) from exc
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            message = f"Automatic MT5 connection failed: {exc!s}"
            self._mark_failure(session, account, message, actor=actor)
            raise ValueError(message) from exc
        finally:
            with suppress(AttributeError, RuntimeError):
                connector.shutdown()

    def provision_and_connect(
        self,
        session: Session,
        account: Account,
        *,
        actor: str,
        template_path: str = "",
        symbol: str | None = None,
        master_symbol: str | None = None,
    ) -> TerminalInstance:
        try:
            self.provision(session, account, actor=actor, template_path=template_path)
        except (OSError, RuntimeError, ValueError) as exc:
            message = f"Automatic MT5 instance build failed: {exc!s}"
            self._mark_failure(session, account, message, actor=actor)
            raise ValueError(message) from exc
        return self.connect(
            session,
            account,
            actor=actor,
            symbol=symbol,
            master_symbol=master_symbol,
        )

    def start(self, session: Session, account: Account, *, actor: str) -> TerminalInstance:
        """Compatibility action: build when needed, then start and log in."""
        executable = (
            Path(account.terminal_path).expanduser().resolve()
            if account.terminal_path
            else None
        )
        if (
            executable is None
            or not executable.is_file()
            or not self._is_managed_executable(executable, account)
        ):
            self.provision(session, account, actor=actor)
        return self.connect(session, account, actor=actor)

    def prepare_copy_test(self, session: Session, symbol: str, *, actor: str) -> None:
        """Refresh account snapshots and follower contract specs before a copy test."""
        accounts = session.scalars(select(Account).order_by(Account.is_master.desc())).all()
        for account in accounts:
            if account.state == AccountState.DISABLED.value:
                continue
            follower_symbol: str | None = None
            if account.role == AccountRole.FOLLOWER.value:
                mapping = session.scalar(
                    select(SymbolMapping).where(
                        SymbolMapping.follower_account_id == account.id,
                        SymbolMapping.master_symbol == symbol,
                        SymbolMapping.enabled.is_(True),
                    )
                )
                follower_symbol = mapping.follower_symbol if mapping else symbol
            try:
                if not account.credential_ref and not account.terminal_path:
                    message = (
                        "Automatic MT5 connection needs this account's password. "
                        "Open Accounts, then use Build and connect MT5."
                    )
                    self._mark_failure(session, account, message, actor=actor)
                    continue
                if account.credential_ref and not self._has_managed_executable(account):
                    self.provision_and_connect(
                        session,
                        account,
                        actor=actor,
                        template_path=account.terminal_path,
                        symbol=follower_symbol,
                        master_symbol=symbol,
                    )
                else:
                    self.connect(
                        session,
                        account,
                        actor=actor,
                        symbol=follower_symbol,
                        master_symbol=symbol,
                    )
            except (OSError, RuntimeError, ValueError) as exc:
                logger.warning(
                    "MT5 copy-test preparation failed account=%s error=%s",
                    account.id,
                    exc,
                )

    def ensure_symbol_routing(self, session: Session, symbol: str, *, actor: str) -> None:
        """Discover and persist missing follower symbol mappings before live routing."""
        followers = session.scalars(
            select(Account).where(
                Account.role == AccountRole.FOLLOWER.value,
                Account.state == AccountState.ACTIVE.value,
                Account.is_master.is_(False),
            )
        ).all()
        for account in followers:
            mapping = session.scalar(
                select(SymbolMapping).where(
                    SymbolMapping.follower_account_id == account.id,
                    SymbolMapping.master_symbol == symbol,
                    SymbolMapping.enabled.is_(True),
                )
            )
            follower_symbol = mapping.follower_symbol if mapping else symbol
            specification = session.scalar(
                select(AccountSymbolSpec).where(
                    AccountSymbolSpec.account_id == account.id,
                    AccountSymbolSpec.symbol == follower_symbol,
                    AccountSymbolSpec.trading_enabled.is_(True),
                )
            )
            if specification is not None:
                continue
            try:
                if account.credential_ref and not self._has_managed_executable(account):
                    self.provision_and_connect(
                        session,
                        account,
                        actor=actor,
                        template_path=account.terminal_path,
                        symbol=follower_symbol,
                        master_symbol=symbol,
                    )
                else:
                    self.connect(
                        session,
                        account,
                        actor=actor,
                        symbol=follower_symbol,
                        master_symbol=symbol,
                    )
            except (OSError, RuntimeError, ValueError) as exc:
                logger.warning(
                    "Automatic symbol routing failed account=%s symbol=%s error=%s",
                    account.id,
                    symbol,
                    exc,
                )

    def reconnect_managed_accounts(self, session: Session, *, actor: str) -> None:
        """Recover configured accounts after terminal or VPS restarts."""
        accounts = session.scalars(select(Account)).all()
        for account in accounts:
            if account.state == AccountState.DISABLED.value:
                continue
            terminal = account.terminal
            running = bool(
                terminal
                and terminal.process_id
                and self.is_running(terminal.process_id)
            )
            if account.health == TerminalHealth.HEALTHY.value and running:
                continue
            if terminal is not None and terminal.last_error:
                continue
            if not account.credential_ref and not account.terminal_path:
                continue
            try:
                if account.credential_ref and not self._has_managed_executable(account):
                    self.provision_and_connect(
                        session,
                        account,
                        actor=actor,
                        template_path=account.terminal_path,
                    )
                else:
                    self.connect(session, account, actor=actor)
            except (OSError, RuntimeError, ValueError) as exc:
                logger.warning("MT5 reconnect failed account=%s error=%s", account.id, exc)

    def remove_instance(self, account: Account) -> None:
        """Remove only the verified managed directory for a confirmed account deletion."""
        directory = self._instance_directory(account)
        if not directory.exists():
            return
        marker_path = directory / ".aaa-instance.json"
        try:
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError("Refusing to remove an unverified MT5 directory.") from exc
        if marker.get("account_id") != account.id:
            raise ValueError("Refusing to remove an MT5 directory owned by another account.")

        terminal = account.terminal
        if terminal is not None and terminal.process_id and psutil.pid_exists(terminal.process_id):
            process = psutil.Process(terminal.process_id)
            try:
                executable = Path(process.exe()).resolve()
                if executable.parent == directory:
                    process.terminate()
                    process.wait(timeout=10)
            except psutil.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            except (OSError, psutil.Error):
                pass
        shutil.rmtree(directory)

    @staticmethod
    def is_running(process_id: int) -> bool:
        if process_id <= 0:
            return False
        try:
            return psutil.pid_exists(process_id)
        except (OSError, psutil.Error):
            return False
