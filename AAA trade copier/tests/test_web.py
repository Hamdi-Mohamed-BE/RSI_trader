from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from trade_copier.models import Account, CopyJob

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


def test_demo_simulation_creates_two_filled_jobs(
    logged_in_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    page = logged_in_client.get("/")
    response = logged_in_client.post(
        "/demo/simulate",
        data={"csrf": extract_csrf(page.text)},
        follow_redirects=False,
    )
    assert response.status_code == 303
    with session_factory() as session:
        assert session.scalar(select(func.count(CopyJob.id))) == 2
        jobs = session.scalars(select(CopyJob).order_by(CopyJob.requested_volume)).all()
        assert [str(job.requested_volume) for job in jobs] == ["0.1000", "0.2500"]
        assert {job.status for job in jobs} == {"filled"}


def test_demo_accounts_are_masked_in_ui(logged_in_client: TestClient) -> None:
    response = logged_in_client.get("/accounts")
    assert "100001" not in response.text
    assert "Encrypted" not in response.text
    assert "Demo Master" in response.text


def test_status_api_reports_seeded_accounts(logged_in_client: TestClient) -> None:
    response = logged_in_client.get("/api/status")
    assert response.status_code == 200
    assert response.json()["accounts"] == 3
    assert response.json()["execution_mode"] == "demo"


def test_csrf_is_required_for_state_change(logged_in_client: TestClient) -> None:
    response = logged_in_client.post(
        "/system/pause",
        data={"csrf": "invalid", "reason": "test"},
        follow_redirects=False,
    )
    assert response.status_code == 403


def test_demo_seed_contains_single_master(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    # Entering TestClient runs the application lifespan, which creates and seeds
    # the isolated test database used by this assertion.
    del client
    with session_factory() as session:
        masters = session.scalars(select(Account).where(Account.is_master.is_(True))).all()
        assert len(masters) == 1
