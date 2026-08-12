from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from trade_copier.config import Settings
from trade_copier.models import Account
from trade_copier.services.accounts import ensure_system_state
from trade_copier.services.mt5_agents import Mt5AgentBootstrapper


class FakeAgentMt5:
    def __init__(self, *, data_path: Path, login: int) -> None:
        self.data_path = data_path
        self.login = login
        self.shutdown_called = False

    def initialize(self, path: str, **kwargs: Any) -> bool:
        del path, kwargs
        return True

    def account_info(self) -> SimpleNamespace:
        return SimpleNamespace(login=self.login)

    def terminal_info(self) -> SimpleNamespace:
        return SimpleNamespace(connected=True, data_path=str(self.data_path))

    @staticmethod
    def positions_get() -> tuple[SimpleNamespace, ...]:
        return (SimpleNamespace(symbol="XAUUSD"),)

    @staticmethod
    def orders_get() -> tuple[()]:
        return ()

    @staticmethod
    def last_error() -> tuple[int, str]:
        return 1, "Success"

    def shutdown(self) -> None:
        self.shutdown_called = True


def test_bootstrap_installs_and_configures_master_publisher(
    client: TestClient,
    settings: Settings,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    del client
    terminal_dir = tmp_path / "Broker MT5"
    terminal_dir.mkdir()
    executable = terminal_dir / "terminal64.exe"
    executable.write_bytes(b"terminal")
    data_path = tmp_path / "Broker Data"
    connector = FakeAgentMt5(data_path=data_path, login=12345678)
    restarted: list[tuple[Path, Path, bool]] = []

    with session_factory() as session:
        master = Account(
            display_name="VPS Master",
            login="12345678",
            broker_server="Broker-Demo",
            terminal_path=str(executable),
            role="master_candidate",
            state="active",
            is_master=True,
            trade_mode="demo",
            position_mode="hedging",
        )
        session.add(master)
        session.commit()
        state = ensure_system_state(session)
        state.active_master_account_id = master.id
        session.commit()
        bootstrapper = Mt5AgentBootstrapper(
            settings=settings,
            mt5_module=connector,
            platform_name="nt",
        )
        monkeypatch.setattr(
            bootstrapper,
            "_restart_with_config",
            lambda terminal, config, *, portable: restarted.append(
                (terminal, config, portable)
            ),
        )

        results = bootstrapper.bootstrap(session, actor="test")

    assert len(results) == 1
    assert results[0].attached is True
    assert results[0].terminal_restarted is True
    assert connector.shutdown_called is True
    assert (data_path / "MQL5" / "Experts" / "AAA" / "AAA_Master_Publisher.ex5").is_file()
    preset = data_path / "MQL5" / "Presets" / f"AAA_Master_{master.id}.set"
    preset_text = preset.read_text(encoding="utf-8")
    assert "InpPublisherEnabled=true" in preset_text
    assert f"InpSourceAccountId={master.id}" in preset_text
    assert "password" not in preset_text.casefold()
    config = settings.storage_dir / "mt5_agents" / f"master-{master.id}.ini"
    config_text = config.read_text(encoding="utf-8")
    assert "Expert=AAA\\AAA_Master_Publisher" in config_text
    assert "Symbol=XAUUSD" in config_text
    assert "Password=" not in config_text
    assert restarted == [(executable, config.resolve(), False)]
