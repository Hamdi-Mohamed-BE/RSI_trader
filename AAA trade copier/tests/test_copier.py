from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from trade_copier.config import Settings
from trade_copier.domain.enums import Side, TradeAction
from trade_copier.domain.messages import SourceTradeMessage
from trade_copier.models import Account, CopyJob, SourceTradeEvent, TradeLink
from trade_copier.services.copier import CopierCore
from trade_copier.services.demo import seed_demo
from trade_copier.transport.base import TransportRouter
from trade_copier.transport.memory import DemoFollowerTransport, RejectingTransport


@pytest.mark.asyncio
async def test_duplicate_source_event_never_dispatches_twice(
    client: TestClient,
    settings: Settings,
    session_factory: sessionmaker[Session],
) -> None:
    del client
    with session_factory() as session:
        seed_demo(session)
        master = session.scalar(select(Account).where(Account.is_master.is_(True)))
        assert master is not None
        followers = session.scalars(
            select(Account).where(Account.role == "follower").order_by(Account.display_name)
        ).all()
        transports = {follower.id: DemoFollowerTransport() for follower in followers}
        router = TransportRouter(RejectingTransport())
        for account_id, transport in transports.items():
            router.register(account_id, transport)

        message = SourceTradeMessage(
            event_uid=uuid4(),
            sequence=42,
            source_account_id=UUID(master.id),
            source_order_id="IDEMPOTENCY-ORDER",
            source_position_id="IDEMPOTENCY-POSITION",
            action=TradeAction.MARKET_OPEN,
            side=Side.BUY,
            symbol="XAUUSD",
            volume=Decimal("1"),
            entry_price=Decimal("2400"),
            stop_loss=Decimal("2390"),
        )
        core = CopierCore(settings=settings, transport=router)

        first = await core.process(session, message)
        second = await core.process(session, message)

        assert {job.id for job in first} == {job.id for job in second}
        assert session.scalar(select(func.count(SourceTradeEvent.id))) == 1
        assert session.scalar(select(func.count(CopyJob.id))) == 2
        assert sum(len(transport.commands) for transport in transports.values()) == 2


@pytest.mark.asyncio
async def test_complete_lifecycle_reuses_the_mapped_follower_position(
    client: TestClient,
    settings: Settings,
    session_factory: sessionmaker[Session],
) -> None:
    del client
    with session_factory() as session:
        seed_demo(session)
        master = session.scalar(select(Account).where(Account.is_master.is_(True)))
        assert master is not None
        followers = session.scalars(
            select(Account).where(Account.role == "follower").order_by(Account.display_name)
        ).all()
        transports = {follower.id: DemoFollowerTransport() for follower in followers}
        router = TransportRouter(RejectingTransport())
        for account_id, transport in transports.items():
            router.register(account_id, transport)
        core = CopierCore(settings=settings, transport=router)
        common = {
            "source_account_id": UUID(master.id),
            "source_order_id": "MASTER-100",
            "source_position_id": "POSITION-100",
            "side": Side.BUY,
            "symbol": "XAUUSD",
            "entry_price": Decimal("2400"),
        }

        await core.process(
            session,
            SourceTradeMessage(
                **common,
                sequence=1,
                action=TradeAction.MARKET_OPEN,
                volume=Decimal("1"),
                stop_loss=Decimal("2390"),
            ),
        )
        links = session.scalars(select(TradeLink).order_by(TradeLink.follower_account_id)).all()
        assert len(links) == 2
        assert all(link.follower_position_id.startswith("POS-") for link in links)

        await core.process(
            session,
            SourceTradeMessage(
                **common,
                sequence=2,
                action=TradeAction.MODIFY,
                volume=Decimal("1"),
                stop_loss=Decimal("2395"),
                take_profit=Decimal("2420"),
            ),
        )
        await core.process(
            session,
            SourceTradeMessage(
                **common,
                sequence=3,
                action=TradeAction.PARTIAL_CLOSE,
                volume=Decimal("0.4"),
                stop_loss=Decimal("2395"),
                take_profit=Decimal("2420"),
                metadata={"previous_volume": "1"},
            ),
        )
        await core.process(
            session,
            SourceTradeMessage(
                **common,
                sequence=4,
                action=TradeAction.CLOSE,
                volume=Decimal("0.6"),
                stop_loss=Decimal("2395"),
                take_profit=Decimal("2420"),
            ),
        )

        for transport in transports.values():
            assert [command.action for command in transport.commands] == [
                TradeAction.MARKET_OPEN,
                TradeAction.MODIFY,
                TradeAction.PARTIAL_CLOSE,
                TradeAction.CLOSE,
            ]
            opened_ticket = transport.commands[1].target_position_id
            assert opened_ticket
            assert all(
                command.target_position_id == opened_ticket for command in transport.commands[1:]
            )
        assert all(link.status == "closed" for link in links)


@pytest.mark.asyncio
async def test_pending_cancellation_targets_the_mapped_follower_order(
    client: TestClient,
    settings: Settings,
    session_factory: sessionmaker[Session],
) -> None:
    del client
    with session_factory() as session:
        seed_demo(session)
        master = session.scalar(select(Account).where(Account.is_master.is_(True)))
        follower = session.scalar(
            select(Account).where(Account.role == "follower").order_by(Account.display_name)
        )
        assert master is not None and follower is not None
        transport = DemoFollowerTransport()
        router = TransportRouter(RejectingTransport())
        router.register(follower.id, transport)
        core = CopierCore(settings=settings, transport=router)

        await core.process(
            session,
            SourceTradeMessage(
                sequence=1,
                source_account_id=UUID(master.id),
                source_order_id="PENDING-200",
                action=TradeAction.PENDING_CREATE,
                side=Side.BUY,
                symbol="XAUUSD",
                volume=Decimal("1"),
                entry_price=Decimal("2380"),
                stop_loss=Decimal("2370"),
                metadata={"order_type": "limit"},
            ),
        )
        await core.process(
            session,
            SourceTradeMessage(
                sequence=2,
                source_account_id=UUID(master.id),
                source_order_id="PENDING-200",
                action=TradeAction.MODIFY,
                side=Side.BUY,
                symbol="XAUUSD",
                volume=Decimal("1"),
                entry_price=Decimal("2385"),
                stop_loss=Decimal("2375"),
                metadata={"order_type": "limit"},
            ),
        )
        await core.process(
            session,
            SourceTradeMessage(
                sequence=3,
                source_account_id=UUID(master.id),
                source_order_id="PENDING-200",
                action=TradeAction.CANCEL,
                side=Side.BUY,
                symbol="XAUUSD",
                volume=Decimal("1"),
                entry_price=Decimal("2380"),
                stop_loss=Decimal("2370"),
                metadata={"order_type": "limit"},
            ),
        )

        assert [command.action for command in transport.commands] == [
            TradeAction.PENDING_CREATE,
            TradeAction.MODIFY,
            TradeAction.CANCEL,
        ]
        expected_order = f"DEMO-{str(transport.commands[0].job_uid)[:8]}"
        assert transport.commands[1].target_order_id == expected_order
        assert transport.commands[1].entry_price == Decimal("2385")
        assert transport.commands[2].target_order_id == expected_order
        link = session.scalar(
            select(TradeLink).where(TradeLink.follower_account_id == follower.id)
        )
        assert link is not None
        assert link.status == "cancelled"
