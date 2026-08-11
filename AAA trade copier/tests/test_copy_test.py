from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from trade_copier.domain.enums import OrderType, Side
from trade_copier.models import Account, CopyTestRun
from trade_copier.routers import web as web_router
from trade_copier.schemas import CopyTestInput
from trade_copier.services.copy_test import CopyTestRunner
from trade_copier.services.copy_test_execution import CopyTestExecutionRunner
from trade_copier.services.demo import seed_demo
from trade_copier.services.demo_orders import (
    DemoOrderExecutor,
    DemoOrderOutcome,
    DemoOrderRequest,
)
from trade_copier.services.terminals import TerminalQuote

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

        assert run.total_followers == 3
        assert run.passed_followers == 2
        assert run.failed_followers == 1
        assert run.status == "completed_with_errors"
        assert run.order_type == "limit"
        assert run.market_price == Decimal("2410")
        errors = {result.error for result in run.results if result.status == "failed"}
        assert any("paused" in error for error in errors)


def test_copy_test_ui_reports_missing_active_master(
    logged_in_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    page = logged_in_client.get("/copy-test")
    assert page.status_code == 200
    assert "Run on master + followers" in page.text
    assert "Demo only" in page.text
    assert "Place on master and all ready followers" in page.text
    assert "Read automatically from active master MT5" in page.text
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
    assert "No+active+master+MT5" in response.headers["location"]
    with session_factory() as session:
        run = session.scalar(select(CopyTestRun))
        assert run is None


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
    with pytest.raises(ValidationError, match=r"Buy Limit entry.*live Ask"):
        CopyTestInput(
            symbol="XAUUSD",
            side=Side.BUY,
            order_type=OrderType.LIMIT,
            master_volume=Decimal("0.10"),
            market_price=Decimal("2400"),
            entry_price=Decimal("2410"),
            stop_loss=Decimal("2390"),
        )


class LiveQuoteTerminalManager:
    def prepare_copy_test(self, session: Session, symbol: str, *, actor: str) -> None:
        del session, symbol, actor

    @staticmethod
    def current_quote(account: Account, symbol: str) -> TerminalQuote:
        del account, symbol
        return TerminalQuote(
            symbol="XAUUSD",
            bid=Decimal("4371.80"),
            ask=Decimal("4372.10"),
        )


def test_copy_test_buy_limit_uses_live_master_ask_not_submitted_reference(
    logged_in_client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with session_factory() as session:
        seed_demo(session)

    manager = LiveQuoteTerminalManager()

    def terminal_manager(request: object) -> LiveQuoteTerminalManager:
        del request
        return manager

    monkeypatch.setattr(web_router, "_terminal_manager", terminal_manager)
    page = logged_in_client.get("/copy-test")
    response = logged_in_client.post(
        "/copy-test",
        data={
            "csrf": extract_csrf(page.text),
            "symbol": "XAUUSD",
            "side": "buy",
            "order_type": "limit",
            "master_volume": "0.10",
            "market_price": "4000",
            "entry_price": "4310",
            "stop_loss": "4300",
            "take_profit": "4400",
            "confirmation": "TEST",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    with session_factory() as session:
        run = session.scalar(select(CopyTestRun).order_by(CopyTestRun.created_at.desc()))
        assert run is not None
        assert run.market_price == Decimal("4372.10")
        assert run.entry_price == Decimal("4310")
        assert run.status == "passed"


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
        return DemoOrderOutcome(
            success=True,
            message="Demo position 123 placed and left open in MT5.",
            broker_order_id="123",
            broker_deal_id="456",
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

        assert len(executor.requests) == 3
        assert [account_name for account_name, _ in executor.requests] == [
            "Demo Master",
            "Follower Alpha",
            "Follower Bravo",
        ]
        assert run.execute_demo is True
        assert run.total_followers == 3
        assert run.passed_followers == 3
        assert run.failed_followers == 0
        assert run.status == "passed"
        completed = next(
            result
            for result in run.results
            if result.checks.get("execution_target") == "master"
        )
        assert completed.checks["broker_order_id"] == "123"
        assert completed.checks["cleanup_id"] == ""
        follower_results = [
            result
            for result in run.results
            if result.checks.get("execution_target") != "master"
        ]
        assert all(
            result.checks.get("execution_status") == "completed"
            for result in follower_results
        )
        assert all(result.checks.get("broker_order_id") == "123" for result in follower_results)

    page = logged_in_client.get("/copy-test")
    assert page.status_code == 200
    assert "Execution result" in page.text
    assert "Demo position 123 placed and left open in MT5." in page.text
    assert "Order remains active" in page.text
    assert "Follower readiness passed" not in page.text
    assert "Ready for copy routing" not in page.text
