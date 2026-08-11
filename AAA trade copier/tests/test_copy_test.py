from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from trade_copier.domain.enums import OrderType, Side
from trade_copier.models import Account, CopyTestRun
from trade_copier.schemas import CopyTestInput
from trade_copier.services.copy_test import CopyTestRunner
from trade_copier.services.copy_test_execution import CopyTestExecutionRunner
from trade_copier.services.demo import seed_demo
from trade_copier.services.demo_orders import (
    DemoOrderExecutor,
    DemoOrderOutcome,
    DemoOrderRequest,
)

from .conftest import extract_csrf


def test_copy_test_calculates_every_follower_and_reports_errors(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    del client
    with session_factory() as session:
        seed_demo(session)
        follower = session.scalar(select(Account).where(Account.display_name == "Follower Bravo"))
        assert follower is not None
        follower.state = "paused"
        session.commit()

        run = CopyTestRunner().run(
            session,
            CopyTestInput(
                symbol="XAUUSD",
                side=Side.BUY,
                order_type=OrderType.LIMIT,
                master_volume=Decimal("1"),
                market_price=Decimal("2410"),
                entry_price=Decimal("2400"),
                stop_loss=Decimal("2390"),
                take_profit=Decimal("2420"),
            ),
            actor="test",
        )

        assert run.total_followers == 2
        assert run.passed_followers == 1
        assert run.failed_followers == 1
        assert run.status == "completed_with_errors"
        assert run.order_type == "limit"
        assert run.market_price == Decimal("2410")
        errors = {result.error for result in run.results if result.status == "failed"}
        assert any("paused" in error for error in errors)


def test_copy_test_ui_records_missing_master_error(
    logged_in_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    page = logged_in_client.get("/copy-test")
    assert page.status_code == 200
    assert "Run across all followers" in page.text
    assert "Demo only" in page.text
    assert "Place and auto-clean demo orders" in page.text
    assert 'name="order_type"' in page.text
    assert "Buy Limit" in page.text
    assert "Sell Stop" in page.text

    response = logged_in_client.post(
        "/copy-test",
        data={
            "csrf": extract_csrf(page.text),
            "symbol": "XAUUSD",
            "side": "buy",
            "order_type": "stop",
            "master_volume": "0.10",
            "market_price": "2395",
            "entry_price": "2400",
            "stop_loss": "2390",
            "take_profit": "2420",
            "confirmation": "TEST",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    with session_factory() as session:
        run = session.scalar(select(CopyTestRun))
        assert run is not None
        assert run.status == "failed"
        assert run.order_type == "stop"
        assert "No active master" in run.error


@pytest.mark.parametrize(
    ("side", "order_type", "market_price", "entry_price"),
    [
        (Side.BUY, OrderType.LIMIT, "2400", "2390"),
        (Side.SELL, OrderType.LIMIT, "2400", "2410"),
        (Side.BUY, OrderType.STOP, "2400", "2410"),
        (Side.SELL, OrderType.STOP, "2400", "2390"),
    ],
)
def test_copy_test_accepts_valid_pending_orders(
    side: Side,
    order_type: OrderType,
    market_price: str,
    entry_price: str,
) -> None:
    entry = Decimal(entry_price)
    data = CopyTestInput(
        symbol="XAUUSD",
        side=side,
        order_type=order_type,
        master_volume=Decimal("0.10"),
        market_price=Decimal(market_price),
        entry_price=entry,
        stop_loss=entry - Decimal("10") if side is Side.BUY else entry + Decimal("10"),
        take_profit=entry + Decimal("20") if side is Side.BUY else entry - Decimal("20"),
    )

    assert data.order_type is order_type


def test_copy_test_rejects_invalid_buy_limit() -> None:
    with pytest.raises(ValidationError, match="buy limit entry must be below"):
        CopyTestInput(
            symbol="XAUUSD",
            side=Side.BUY,
            order_type=OrderType.LIMIT,
            master_volume=Decimal("0.10"),
            market_price=Decimal("2400"),
            entry_price=Decimal("2410"),
            stop_loss=Decimal("2390"),
        )


class RecordingDemoExecutor(DemoOrderExecutor):
    def __init__(self) -> None:
        self.requests: list[tuple[str, DemoOrderRequest]] = []

    def execute(
        self,
        session: Session,
        account: Account,
        request: DemoOrderRequest,
        *,
        actor: str,
    ) -> DemoOrderOutcome:
        del session, actor
        self.requests.append((account.display_name, request))
        if account.display_name == "Follower Bravo":
            return DemoOrderOutcome(success=False, message="Broker retcode 10030: invalid fill")
        return DemoOrderOutcome(
            success=True,
            message="Demo order 123 placed and automatically closed.",
            broker_order_id="123",
            broker_deal_id="456",
            cleanup_id="789",
            broker_retcode=10009,
        )


def test_copy_test_demo_execution_records_real_outcomes(
    logged_in_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        seed_demo(session)
        run = CopyTestRunner().run(
            session,
            CopyTestInput(
                symbol="XAUUSD",
                side=Side.BUY,
                order_type=OrderType.MARKET,
                master_volume=Decimal("0.10"),
                entry_price=Decimal("2400"),
                stop_loss=Decimal("2390"),
                execute_demo=True,
            ),
            actor="test",
        )
        executor = RecordingDemoExecutor()

        run = CopyTestExecutionRunner(executor).execute(session, run, actor="test")

        assert len(executor.requests) == 2
        assert run.execute_demo is True
        assert run.passed_followers == 1
        assert run.failed_followers == 1
        assert run.status == "completed_with_errors"
        completed = next(result for result in run.results if result.status == "passed")
        failed = next(result for result in run.results if result.status == "failed")
        assert completed.checks["broker_order_id"] == "123"
        assert completed.checks["cleanup_id"] == "789"
        assert "10030" in failed.error

    page = logged_in_client.get("/copy-test")
    assert page.status_code == 200
    assert "Execution result" in page.text
    assert "Demo order 123 placed and automatically closed." in page.text
    assert "Ready for copy routing" not in page.text
