from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from trade_copier.domain.enums import ExecutionMode, OrderType, Side, TradeAction
from trade_copier.models import Account, MasterTradeState, TradeLink
from trade_copier.services.accounts import ensure_system_state
from trade_copier.services.continuous_copier import (
    ContinuousTradeCopier,
    ObservedMasterTrade,
)
from trade_copier.services.demo import seed_demo
from trade_copier.services.runtime_state import recover_enabled_demo_mode


class SequenceReader:
    def __init__(self, snapshots: list[list[ObservedMasterTrade]]) -> None:
        self.snapshots = snapshots

    def read(self, account: Account) -> list[ObservedMasterTrade]:
        del account
        return self.snapshots.pop(0)


class RecordingCore:
    def __init__(self) -> None:
        self.messages: list[Any] = []

    async def process(self, session: Session, message: Any) -> list[Any]:
        del session
        self.messages.append(message)
        return []


class FailingCore(RecordingCore):
    async def process(self, session: Session, message: Any) -> list[Any]:
        del session
        self.messages.append(message)
        return [SimpleNamespace(status="failed", rejection_reason="terminal offline")]


class NoopTerminalManager:
    def ensure_symbol_routing(self, *args: Any, **kwargs: Any) -> None:
        del args, kwargs


def observed(*, stop_loss: str = "2390") -> ObservedMasterTrade:
    return ObservedMasterTrade(
        source_type="position",
        source_ticket="MASTER-POSITION-1",
        broker_ticket="7001",
        symbol="XAUUSD",
        side=Side.BUY,
        order_type=OrderType.MARKET,
        broker_order_type=0,
        volume=Decimal("1"),
        entry_price=Decimal("2400"),
        stop_loss=Decimal(stop_loss),
        take_profit=Decimal("2420"),
    )


@pytest.mark.asyncio
async def test_master_reconciliation_emits_open_modify_and_close(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    del client
    core = RecordingCore()
    reader = SequenceReader([[observed()], [observed(stop_loss="2395")], []])
    copier = ContinuousTradeCopier(
        core=core,  # type: ignore[arg-type]
        reader=reader,  # type: ignore[arg-type]
        terminal_manager=NoopTerminalManager(),  # type: ignore[arg-type]
    )
    with session_factory() as session:
        seed_demo(session)

        await copier.poll_once(session)
        await copier.poll_once(session)
        await copier.poll_once(session)

        assert [message.action for message in core.messages] == [
            TradeAction.MARKET_OPEN,
            TradeAction.MODIFY,
            TradeAction.CLOSE,
        ]
        state = session.scalar(select(MasterTradeState))
        assert state is not None
        assert state.status == "closed"


@pytest.mark.asyncio
async def test_failed_close_keeps_mapping_active_for_a_bounded_retry(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    del client
    core = FailingCore()
    reader = SequenceReader([[], []])
    copier = ContinuousTradeCopier(
        core=core,  # type: ignore[arg-type]
        reader=reader,  # type: ignore[arg-type]
        terminal_manager=NoopTerminalManager(),  # type: ignore[arg-type]
    )
    with session_factory() as session:
        seed_demo(session)
        master = session.scalar(select(Account).where(Account.is_master.is_(True)))
        follower = session.scalar(select(Account).where(Account.role == "follower"))
        assert master is not None and follower is not None
        trade = observed()
        state = MasterTradeState(
            master_account_id=master.id,
            source_type=trade.source_type,
            source_ticket=trade.source_ticket,
            broker_ticket=trade.broker_ticket,
            symbol=trade.symbol,
            side=trade.side.value,
            order_type=trade.broker_order_type,
            volume=trade.volume,
            entry_price=trade.entry_price,
            stop_loss=trade.stop_loss,
            take_profit=trade.take_profit,
            fingerprint=trade.fingerprint,
        )
        link = TradeLink(
            master_account_id=master.id,
            follower_account_id=follower.id,
            source_type="position",
            source_ticket=trade.source_ticket,
            source_order_id=trade.source_ticket,
            source_position_id=trade.source_ticket,
            follower_symbol="XAUUSD",
            follower_order_id="9001",
            follower_position_id="9001",
            side="buy",
            source_volume=Decimal("1"),
            follower_volume=Decimal("0.1"),
            entry_price=Decimal("2400"),
            stop_loss=Decimal("2390"),
            status="active",
        )
        session.add_all([state, link])
        session.commit()

        await copier.poll_once(session)
        await copier.poll_once(session)

        assert [message.action for message in core.messages] == [TradeAction.CLOSE]
        assert state.status == "active"
        assert state.last_dispatch_failed is True


@pytest.mark.asyncio
async def test_monitor_mode_baselines_master_trade_without_dispatching(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    del client
    core = RecordingCore()
    copier = ContinuousTradeCopier(
        core=core,  # type: ignore[arg-type]
        reader=SequenceReader([[observed()], [observed()]]),  # type: ignore[arg-type]
        terminal_manager=NoopTerminalManager(),  # type: ignore[arg-type]
    )
    with session_factory() as session:
        seed_demo(session)
        system = ensure_system_state(session)
        system.execution_mode = ExecutionMode.MONITOR.value
        system.global_pause = False
        session.commit()

        await copier.poll_once(session)
        await copier.poll_once(session)

        state = session.scalar(select(MasterTradeState))
        assert state is not None
        assert state.status == "baseline"
        assert core.messages == []


@pytest.mark.asyncio
async def test_baseline_trade_stays_ignored_after_demo_mode_is_enabled(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    del client
    second_trade = observed(stop_loss="2380")
    second_trade = ObservedMasterTrade(
        **{
            **second_trade.__dict__,
            "source_ticket": "MASTER-POSITION-2",
            "broker_ticket": "7002",
        }
    )
    core = RecordingCore()
    copier = ContinuousTradeCopier(
        core=core,  # type: ignore[arg-type]
        reader=SequenceReader([[observed()], [observed(), second_trade]]),  # type: ignore[arg-type]
        terminal_manager=NoopTerminalManager(),  # type: ignore[arg-type]
    )
    with session_factory() as session:
        seed_demo(session)
        system = ensure_system_state(session)
        system.execution_mode = ExecutionMode.MONITOR.value
        system.global_pause = False
        session.commit()

        await copier.poll_once(session)
        assert recover_enabled_demo_mode(session, snapshot_reconciled=True) is True
        await copier.poll_once(session)

        assert [message.source_order_id for message in core.messages] == [
            "MASTER-POSITION-2"
        ]
