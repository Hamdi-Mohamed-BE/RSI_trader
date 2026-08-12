from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from trade_copier.domain.enums import ExecutionMode
from trade_copier.models import Account, MasterTradeState
from trade_copier.services.accounts import ensure_system_state
from trade_copier.services.demo import seed_demo
from trade_copier.services.runtime_state import recover_enabled_demo_mode


def _master_state(master: Account) -> MasterTradeState:
    return MasterTradeState(
        master_account_id=master.id,
        source_type="position",
        source_ticket="OPEN-BEFORE-RECOVERY",
        broker_ticket="7001",
        symbol="XAUUSD",
        side="buy",
        order_type=0,
        volume=Decimal("0.1"),
        entry_price=Decimal("2400"),
        stop_loss=Decimal("2390"),
        fingerprint="existing-master-position",
        last_dispatch_failed=True,
    )


def test_demo_recovery_baselines_existing_unlinked_master_trades(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    del client
    with session_factory() as session:
        seed_demo(session)
        master = session.scalar(select(Account).where(Account.is_master.is_(True)))
        assert master is not None
        trade_state = _master_state(master)
        session.add(trade_state)
        system = ensure_system_state(session)
        system.execution_mode = ExecutionMode.MONITOR.value
        system.global_pause = False
        session.commit()

        assert recover_enabled_demo_mode(session, snapshot_reconciled=True) is True

        assert system.execution_mode == ExecutionMode.DEMO.value
        assert system.global_pause is False
        assert trade_state.status == "baseline"
        assert trade_state.last_dispatch_failed is False


def test_demo_recovery_does_not_enable_when_an_active_account_is_live(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    del client
    with session_factory() as session:
        seed_demo(session)
        follower = session.scalar(select(Account).where(Account.role == "follower"))
        assert follower is not None
        follower.trade_mode = "live"
        system = ensure_system_state(session)
        system.execution_mode = ExecutionMode.MONITOR.value
        system.global_pause = False
        session.commit()

        assert recover_enabled_demo_mode(session, snapshot_reconciled=True) is False
        assert system.execution_mode == ExecutionMode.MONITOR.value


def test_demo_recovery_requires_a_completed_master_snapshot(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    del client
    with session_factory() as session:
        seed_demo(session)
        system = ensure_system_state(session)
        system.execution_mode = ExecutionMode.MONITOR.value
        system.global_pause = False
        session.commit()

        assert recover_enabled_demo_mode(session) is False
        assert system.execution_mode == ExecutionMode.MONITOR.value
