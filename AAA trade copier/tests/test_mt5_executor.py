from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from trade_copier.domain.enums import JobStatus, OrderType, Side, TradeAction
from trade_copier.domain.messages import FollowerCommand
from trade_copier.services.credentials import MemoryCredentialVault
from trade_copier.services.mt5_executor import Mt5FollowerExecutor

from .test_demo_orders import FakeMt5, build_account


class LiveFollowerMt5(FakeMt5):
    def initialize(self, path: str, *, timeout: int, portable: bool) -> bool:
        del portable
        return bool(path and timeout)

    def positions_get(self, *, symbol: str | None = None) -> list[SimpleNamespace]:
        del symbol
        if not self.sent:
            return []
        return [
            SimpleNamespace(
                comment=self.sent[-1]["comment"],
                identifier=123,
                ticket=789,
                time_msc=1,
            )
        ]


def command(account_id: str) -> FollowerCommand:
    return FollowerCommand(
        job_uid=uuid4(),
        source_event_uid=uuid4(),
        follower_account_id=UUID(account_id),
        source_order_id="MASTER-ORDER-1",
        source_position_id="MASTER-POSITION-1",
        action=TradeAction.MARKET_OPEN,
        side=Side.BUY,
        order_type=OrderType.MARKET,
        symbol="XAUUSDm",
        volume=Decimal("0.05"),
        entry_price=Decimal("4350"),
        stop_loss=Decimal("4340"),
        max_slippage_points=30,
    )


def test_live_follower_requires_environment_permission(
    client: TestClient,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    del client
    vault = MemoryCredentialVault()
    connector = LiveFollowerMt5(trade_mode=1)
    with session_factory() as session:
        account = build_account(session, tmp_path, vault, trade_mode="live")
        result = Mt5FollowerExecutor(
            vault=vault,
            allow_live=False,
            mt5_module=connector,
            platform_name="nt",
        ).execute(session, account, command(account.id))

        assert result.status is JobStatus.FAILED
        assert "blocked by the environment safety gates" in result.error
        assert connector.sent == []


def test_live_follower_places_order_when_environment_permission_is_open(
    client: TestClient,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    del client
    vault = MemoryCredentialVault()
    connector = LiveFollowerMt5(trade_mode=1)
    with session_factory() as session:
        account = build_account(session, tmp_path, vault, trade_mode="live")
        result = Mt5FollowerExecutor(
            vault=vault,
            allow_live=True,
            mt5_module=connector,
            platform_name="nt",
        ).execute(session, account, command(account.id))

        assert result.status is JobStatus.FILLED
        assert result.broker_order_id == "123"
        assert result.broker_position_id == "789"
        assert len(connector.sent) == 1
