from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from trade_copier.models import Account, AccountSymbolSpec
from trade_copier.services.credentials import MemoryCredentialVault
from trade_copier.services.terminals import TerminalManager


class FakeMt5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    ACCOUNT_MARGIN_MODE_RETAIL_HEDGING = 2
    SYMBOL_TRADE_MODE_DISABLED = 0

    def __init__(self, *, login_succeeds: bool = True) -> None:
        self.login_succeeds = login_succeeds
        self.initialized_path = ""
        self.login_password = ""
        self.shutdown_called = False

    def initialize(self, path: str, **kwargs: Any) -> bool:
        assert kwargs["portable"] is True
        self.initialized_path = path
        return True

    def login(self, login: int, **kwargs: Any) -> bool:
        assert login == 472077113
        self.login_password = str(kwargs["password"])
        return self.login_succeeds

    @staticmethod
    def account_info() -> SimpleNamespace:
        return SimpleNamespace(
            login=472077113,
            currency="USD",
            balance=10000,
            equity=9950,
            margin_free=9000,
            trade_mode=0,
            margin_mode=2,
        )

    @staticmethod
    def terminal_info() -> SimpleNamespace:
        return SimpleNamespace(connected=True, build=5000, trade_allowed=True)

    @staticmethod
    def symbol_select(symbol: str, selected: bool) -> bool:
        return symbol == "XAUUSD" and selected

    @staticmethod
    def symbol_info(symbol: str) -> SimpleNamespace | None:
        if symbol != "XAUUSD":
            return None
        return SimpleNamespace(
            trade_tick_size=Decimal("0.01"),
            trade_tick_value_loss=Decimal("1"),
            volume_min=Decimal("0.01"),
            volume_max=Decimal("100"),
            volume_step=Decimal("0.01"),
            trade_contract_size=Decimal("100"),
            spread=20,
            trade_mode=4,
        )

    @staticmethod
    def last_error() -> tuple[int, str]:
        return 100, "test login rejected"

    def shutdown(self) -> None:
        self.shutdown_called = True


def test_manager_builds_isolated_instance_logs_in_and_syncs_symbol(
    client: TestClient,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    del client
    template_dir = tmp_path / "Broker MT5"
    template_dir.mkdir()
    template_executable = template_dir / "terminal64.exe"
    template_executable.write_bytes(b"fake terminal")
    (template_dir / "terminal.ico").write_bytes(b"icon")
    vault = MemoryCredentialVault()
    credential_ref = vault.store("broker-password")
    connector = FakeMt5()

    with session_factory() as session:
        account = Account(
            display_name="Follower 472077113",
            login="472077113",
            broker_server="Broker-Demo",
            role="follower",
            state="active",
            credential_ref=credential_ref,
        )
        session.add(account)
        session.commit()
        session.refresh(account)
        manager = TerminalManager(
            instances_root=tmp_path / "instances",
            vault=vault,
            default_template_path=str(template_executable),
            mt5_module=connector,
            platform_name="nt",
        )

        terminal = manager.provision_and_connect(
            session,
            account,
            actor="test",
            symbol="XAUUSD",
        )

        managed_executable = tmp_path / "instances" / account.id / "terminal64.exe"
        assert managed_executable.read_bytes() == b"fake terminal"
        assert Path(account.terminal_path) == managed_executable
        assert connector.initialized_path == str(managed_executable)
        assert connector.login_password == "broker-password"
        assert terminal.health == "healthy"
        assert terminal.last_error == ""
        assert account.health == "healthy"
        assert account.equity == Decimal("9950")
        assert connector.shutdown_called is True
        assert (managed_executable.parent / "MQL5" / "Experts" / "AAA").is_dir()
        marker = (managed_executable.parent / ".aaa-instance.json").read_text("utf-8")
        assert "broker-password" not in marker
        specification = session.scalar(
            select(AccountSymbolSpec).where(AccountSymbolSpec.account_id == account.id)
        )
        assert specification is not None
        assert specification.symbol == "XAUUSD"
        assert specification.tick_size == Decimal("0.01")

        manager.remove_instance(account)
        assert not managed_executable.parent.exists()
