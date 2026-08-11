import re
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from trade_copier.app import create_app
from trade_copier.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        app_env="test",
        app_secret_key="test-secret-key-with-more-than-thirty-two-characters",
        database_url="sqlite://",
        safe_mode=True,
        live_execution_enabled=False,
        demo_mode=True,
        admin_email="admin@test.local",
        admin_password="correct-horse-battery-staple",
        storage_dir=tmp_path / "storage",
    )


@pytest.fixture
def session_factory() -> Generator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    yield factory
    engine.dispose()


@pytest.fixture
def client(
    settings: Settings,
    session_factory: sessionmaker[Session],
) -> Generator[TestClient]:
    active_engine = session_factory.kw["bind"]
    application = create_app(
        settings=settings,
        active_engine=active_engine,
        session_factory=session_factory,
    )
    with TestClient(application) as test_client:
        yield test_client


def extract_csrf(html: str) -> str:
    match = re.search(r'name="csrf" value="([^"]+)"', html)
    assert match
    return match.group(1)


@pytest.fixture
def logged_in_client(client: TestClient) -> TestClient:
    login_page = client.get("/login")
    response = client.post(
        "/login",
        data={
            "email": "admin@test.local",
            "password": "correct-horse-battery-staple",
            "csrf": extract_csrf(login_page.text),
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    return client
