"""Shared fixtures: isolated temp database, static vault key, ASGI test client. No real network calls."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest

from crypto_lab.config import Settings
from crypto_lab.container import Container
from crypto_lab.infrastructure.db.migrations import upgrade_to_head
from crypto_lab.infrastructure.db.session import unit_of_work
from crypto_lab.security.crypto import ChainedKeyProvider, StaticKeyProvider, encode_key
from crypto_lab.web.app import create_app

TEST_KEY = encode_key(b"k" * 32)
ADMIN_USER = "admin"
ADMIN_PASSWORD = "correct-horse-battery-staple"  # test-only credential


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        data_dir=tmp_path,
        allow_dev_key_file=False,
        login_rate_per_minute=100,
        login_max_failures=3,
    )


@pytest.fixture
async def container(settings: Settings) -> AsyncIterator[Container]:
    c = Container.build(settings, key_provider=ChainedKeyProvider([StaticKeyProvider(TEST_KEY)]))
    await upgrade_to_head(c.engine)
    async with unit_of_work(c.session_factory) as session:
        await c.bots(session).seed()
    yield c
    await c.dispose()


@pytest.fixture
async def client(settings: Settings, container: Container) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(settings, container=container)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http:
            yield http


@pytest.fixture
async def admin_client(client: httpx.AsyncClient, container: Container) -> httpx.AsyncClient:
    async with unit_of_work(container.session_factory) as session:
        await container.auth(session).create_admin(ADMIN_USER, ADMIN_PASSWORD)
    response = await client.post("/login", data={"username": ADMIN_USER, "password": ADMIN_PASSWORD})
    assert response.status_code == 303
    return client


CSRF_RE = re.compile(r'name="csrf_token" value="([^"]+)"')


async def csrf_from(client: httpx.AsyncClient, path: str) -> str:
    page = await client.get(path)
    match = CSRF_RE.search(page.text)
    assert match, f"no CSRF token on {path}"
    return match.group(1)
