from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings
from ..domain.enums import (
    AccountRole,
    AccountState,
    ExecutionMode,
    RiskMode,
    Side,
    TerminalHealth,
    TradeAction,
)
from ..domain.messages import SourceTradeMessage
from ..models import Account, AccountSymbolSpec, CopyJob, RiskProfile, SymbolMapping
from ..transport.base import TransportRouter
from ..transport.memory import DemoFollowerTransport
from .accounts import ensure_system_state
from .audit import record_audit
from .copier import CopierCore


def seed_demo(session: Session) -> None:
    if session.scalar(select(Account).limit(1)):
        return

    profile = RiskProfile(
        name="Demo 1% stop risk",
        mode=RiskMode.STOP_PERCENT.value,
        risk_percent=Decimal("1.0"),
        max_risk_per_trade_percent=Decimal("1.0"),
    )
    session.add(profile)
    session.flush()
    master = Account(
        display_name="Demo Master",
        login="100001",
        broker_server="AAA-Demo",
        role=AccountRole.MASTER_CANDIDATE.value,
        state=AccountState.ACTIVE.value,
        is_master=True,
        balance=Decimal("100000"),
        equity=Decimal("100000"),
        free_margin=Decimal("95000"),
        health=TerminalHealth.HEALTHY.value,
    )
    follower_a = Account(
        display_name="Follower Alpha",
        login="200001",
        broker_server="Broker-A-Demo",
        role=AccountRole.FOLLOWER.value,
        state=AccountState.ACTIVE.value,
        risk_profile_id=profile.id,
        balance=Decimal("10000"),
        equity=Decimal("10000"),
        free_margin=Decimal("9000"),
        health=TerminalHealth.HEALTHY.value,
    )
    follower_b = Account(
        display_name="Follower Bravo",
        login="300001",
        broker_server="Broker-B-Demo",
        role=AccountRole.FOLLOWER.value,
        state=AccountState.ACTIVE.value,
        risk_profile_id=profile.id,
        balance=Decimal("25000"),
        equity=Decimal("25000"),
        free_margin=Decimal("23000"),
        health=TerminalHealth.HEALTHY.value,
    )
    session.add_all([master, follower_a, follower_b])
    session.flush()
    for account, symbol in [(follower_a, "XAUUSD"), (follower_b, "GOLD")]:
        session.add(
            AccountSymbolSpec(
                account_id=account.id,
                symbol=symbol,
                tick_size=Decimal("0.01"),
                tick_value=Decimal("1.0"),
                volume_min=Decimal("0.01"),
                volume_max=Decimal("100"),
                volume_step=Decimal("0.01"),
                contract_size=Decimal("100"),
                spread_points=20,
            )
        )
    session.add(
        SymbolMapping(
            follower_account_id=follower_b.id,
            master_symbol="XAUUSD",
            follower_symbol="GOLD",
        )
    )
    state = ensure_system_state(session)
    state.active_master_account_id = master.id
    state.execution_mode = ExecutionMode.DEMO.value
    state.global_pause = False
    state.reason = "Demo simulator enabled"
    record_audit(
        session,
        action="demo.seeded",
        message="Safe demo master and follower accounts were created.",
    )
    session.commit()


async def simulate_market_trade(session: Session, settings: Settings) -> list[CopyJob]:
    master = session.scalar(select(Account).where(Account.is_master.is_(True)))
    if master is None:
        raise ValueError("No demo master exists.")
    followers = session.scalars(
        select(Account).where(Account.role == AccountRole.FOLLOWER.value)
    ).all()
    router = TransportRouter(DemoFollowerTransport())
    for follower in followers:
        router.register(follower.id, DemoFollowerTransport())
    core = CopierCore(settings=settings, transport=router)
    return await core.process(
        session,
        SourceTradeMessage(
            sequence=1,
            source_account_id=UUID(master.id),
            source_order_id="DEMO-MASTER-ORDER",
            source_position_id="DEMO-MASTER-POSITION",
            action=TradeAction.MARKET_OPEN,
            side=Side.BUY,
            symbol="XAUUSD",
            volume=Decimal("1.00"),
            entry_price=Decimal("2400.00"),
            stop_loss=Decimal("2390.00"),
            take_profit=Decimal("2420.00"),
            magic_number=10101,
            comment="Safe dashboard simulation",
        ),
    )
