from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from trade_copier.models import Account, RiskProfile

from .conftest import extract_csrf


def test_health_is_public_and_safe(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["safe_mode"] is True


def test_compiled_stylesheet_is_served(client: TestClient) -> None:
    response = client.get("/static/css/app.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    assert len(response.content) > 10_000


def test_dashboard_requires_login(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_login_rejects_invalid_password(client: TestClient) -> None:
    page = client.get("/login")
    response = client.post(
        "/login",
        data={
            "email": "admin@test.local",
            "password": "wrong-password",
            "csrf": extract_csrf(page.text),
        },
    )
    assert response.status_code == 400
    assert "incorrect" in response.text


def test_authenticated_pages_render(logged_in_client: TestClient) -> None:
    for path, expected in [
        ("/", "Copy control and account health"),
        ("/accounts", "Accounts and master selection"),
        ("/trades", "Master-to-follower trade tree"),
        ("/configuration", "Risk profiles and symbol routing"),
        ("/audit", "Configuration and decision audit"),
    ]:
        response = logged_in_client.get(path)
        assert response.status_code == 200
        assert expected in response.text


def test_fresh_workspace_has_no_trading_accounts(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    del client
    with session_factory() as session:
        assert session.scalar(select(func.count(Account.id))) == 0


def test_account_page_exposes_discovery_and_manual_onboarding(
    logged_in_client: TestClient,
) -> None:
    response = logged_in_client.get("/accounts")
    assert "Detect connected MT5" in response.text
    assert "Add another account" in response.text
    assert "Add, build and connect" in response.text
    assert "encrypted with Windows DPAPI" in response.text
    assert "No MT5 accounts configured" in response.text


def test_manual_account_can_be_created_updated_and_deleted(
    logged_in_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    page = logged_in_client.get("/accounts")
    response = logged_in_client.post(
        "/accounts",
        data={
            "csrf": extract_csrf(page.text),
            "display_name": "Follower One",
            "login": "900001",
            "broker_server": "Broker-Demo",
            "terminal_path": "",
            "role": "follower",
            "state": "paused",
            "trade_mode": "demo",
            "position_mode": "hedging",
            "risk_profile_id": "",
            "mt5_password": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    with session_factory() as session:
        account = session.scalar(select(Account).where(Account.login == "900001"))
        assert account is not None
        profile = session.get(RiskProfile, account.risk_profile_id)
        assert profile is not None and profile.risk_percent == 1
        account_id = account.id

    page = logged_in_client.get("/accounts")
    response = logged_in_client.post(
        f"/accounts/{account_id}/update",
        data={
            "csrf": extract_csrf(page.text),
            "display_name": "Follower Renamed",
            "broker_server": "Broker-Demo",
            "terminal_path": "",
            "role": "follower",
            "state": "active",
            "trade_mode": "demo",
            "position_mode": "hedging",
            "risk_profile_id": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    page = logged_in_client.get("/accounts")
    response = logged_in_client.post(
        f"/accounts/{account_id}/delete",
        data={"csrf": extract_csrf(page.text), "confirmation": "DELETE"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    with session_factory() as session:
        assert session.get(Account, account_id) is None


def test_status_api_reports_fresh_workspace(logged_in_client: TestClient) -> None:
    response = logged_in_client.get("/api/status")
    assert response.status_code == 200
    assert response.json()["accounts"] == 0
    assert response.json()["execution_mode"] == "monitor"


def test_csrf_is_required_for_state_change(logged_in_client: TestClient) -> None:
    response = logged_in_client.post(
        "/system/pause",
        data={"csrf": "invalid", "reason": "test"},
        follow_redirects=False,
    )
    assert response.status_code == 403
