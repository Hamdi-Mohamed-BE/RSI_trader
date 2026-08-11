from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from trade_copier.models import Account, CopyJob, RiskProfile, SourceTradeEvent, SystemState
from trade_copier.services.demo import seed_demo
from trade_copier.services.demo_cleanup import remove_legacy_demo_seed
from trade_copier.services.mt5_discovery import DetectedMt5Account, import_detected_accounts


def detected(login: str, server: str, process_id: int) -> DetectedMt5Account:
    return DetectedMt5Account(
        login=login,
        server=server,
        account_name=f"Account {login}",
        currency="USD",
        trade_mode="demo",
        position_mode="hedging",
        balance=Decimal("10000"),
        equity=Decimal("9950"),
        free_margin=Decimal("9000"),
        terminal_path=rf"C:\MT5-{login}\terminal64.exe",
        process_id=process_id,
    )


def test_first_detected_account_becomes_master_and_others_start_paused(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    del client
    with session_factory() as session:
        accounts = import_detected_accounts(
            session,
            [detected("700001", "Broker-A", 100), detected("700002", "Broker-B", 200)],
            actor="test",
        )
        assert len(accounts) == 2
        master = session.scalar(select(Account).where(Account.is_master.is_(True)))
        follower = session.scalar(select(Account).where(Account.role == "follower"))
        state = session.get(SystemState, 1)
        assert master is not None and master.login == "700001"
        assert follower is not None and follower.state == "paused"
        assert state is not None and state.active_master_account_id == master.id
        assert state.global_pause is True

        again = import_detected_accounts(
            session,
            [detected("700001", "Broker-A", 101)],
            actor="test",
        )
        assert len(again) == 1
        assert session.scalar(select(func.count(Account.id))) == 2
        assert master.terminal is not None and master.terminal.process_id == 101


def test_legacy_demo_seed_is_removed_completely(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    del client
    with session_factory() as session:
        seed_demo(session)
        assert remove_legacy_demo_seed(session) is True
        assert session.scalar(select(func.count(Account.id))) == 0
        assert session.scalar(select(func.count(RiskProfile.id))) == 0
        assert session.scalar(select(func.count(SourceTradeEvent.id))) == 0
        assert session.scalar(select(func.count(CopyJob.id))) == 0
