from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from trade_copier.domain.enums import ExecutionMode
from trade_copier.models import Account, RiskProfile
from trade_copier.services.accounts import ensure_system_state
from trade_copier.services.demo import seed_demo

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


def test_status_indicator_uses_http_polling_without_websocket_rejection_spam(
    client: TestClient,
) -> None:
    response = client.get("/static/js/app.js")
    assert response.status_code == 200
    assert 'window.fetch("/api/status"' in response.text
    assert "new WebSocket" not in response.text


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


def test_live_copying_is_locked_when_environment_gates_are_closed(
    logged_in_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        seed_demo(session)
        follower = session.scalar(select(Account).where(Account.role == "follower"))
        assert follower is not None
        follower.trade_mode = "live"
        system = ensure_system_state(session)
        system.global_pause = True
        system.execution_mode = ExecutionMode.MONITOR.value
        session.commit()

    page = logged_in_client.get("/")
    assert "Live execution locked" in page.text
    response = logged_in_client.post(
        "/system/unpause",
        data={"csrf": extract_csrf(page.text), "confirmation": "ENABLE LIVE"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "safety+gates" in response.headers["location"]
    with session_factory() as session:
        system = ensure_system_state(session)
        assert system.global_pause is True
        assert system.execution_mode == ExecutionMode.MONITOR.value


def test_live_copying_requires_strong_confirmation_and_opens_live_mode(
    logged_in_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    logged_in_client.app.state.settings.safe_mode = False
    logged_in_client.app.state.settings.live_execution_enabled = True
    with session_factory() as session:
        seed_demo(session)
        follower = session.scalar(select(Account).where(Account.role == "follower"))
        assert follower is not None
        follower.trade_mode = "live"
        system = ensure_system_state(session)
        system.global_pause = True
        system.execution_mode = ExecutionMode.MONITOR.value
        session.commit()

    page = logged_in_client.get("/")
    assert "Type ENABLE LIVE" in page.text
    rejected = logged_in_client.post(
        "/system/unpause",
        data={"csrf": extract_csrf(page.text), "confirmation": "ENABLE"},
        follow_redirects=False,
    )
    assert rejected.status_code == 303
    assert "Type+ENABLE+LIVE" in rejected.headers["location"]

    page = logged_in_client.get("/")
    enabled = logged_in_client.post(
        "/system/unpause",
        data={"csrf": extract_csrf(page.text), "confirmation": "ENABLE LIVE"},
        follow_redirects=False,
    )
    assert enabled.status_code == 303
    with session_factory() as session:
        system = ensure_system_state(session)
        assert system.global_pause is False
        assert system.execution_mode == ExecutionMode.LIVE.value
        assert system.reason == "Live copying enabled by administrator"
