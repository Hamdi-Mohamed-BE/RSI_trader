from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from trade_copier.domain.enums import Side
from trade_copier.models import Account, CopyTestRun
from trade_copier.schemas import CopyTestInput
from trade_copier.services.copy_test import CopyTestRunner
from trade_copier.services.demo import seed_demo

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
                master_volume=Decimal("1"),
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
        errors = {result.error for result in run.results if result.status == "failed"}
        assert any("paused" in error for error in errors)


def test_copy_test_ui_records_missing_master_error(
    logged_in_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    page = logged_in_client.get("/copy-test")
    assert page.status_code == 200
    assert "Run across all followers" in page.text
    assert "No live order" in page.text

    response = logged_in_client.post(
        "/copy-test",
        data={
            "csrf": extract_csrf(page.text),
            "symbol": "XAUUSD",
            "side": "buy",
            "master_volume": "0.10",
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
        assert "No active master" in run.error
