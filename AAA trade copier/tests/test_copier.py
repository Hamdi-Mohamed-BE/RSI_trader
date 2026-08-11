from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from trade_copier.config import Settings
from trade_copier.domain.enums import Side, TradeAction
from trade_copier.domain.messages import SourceTradeMessage
from trade_copier.models import Account, CopyJob, SourceTradeEvent
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
