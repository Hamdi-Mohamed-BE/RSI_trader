import httpx
import pytest
from sqlalchemy import select

from crypto_lab.container import Container
from crypto_lab.infrastructure.db.models import ApiCredential
from crypto_lab.infrastructure.db.session import unit_of_work
from tests.conftest import ADMIN_PASSWORD, ADMIN_USER, csrf_from

SECRET = "sk_live_THIS_MUST_NEVER_BE_RENDERED_9f2c"


async def test_pages_require_login(client: httpx.AsyncClient) -> None:
    for path in ("/", "/admin/keys", "/admin/bots", "/polymarket/scanner", "/polymarket/wallets"):
        response = await client.get(path)
        assert response.status_code == 303
        assert response.headers["location"].startswith("/login?next=")


async def test_security_headers_are_set(client: httpx.AsyncClient) -> None:
    response = await client.get("/login")
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"


async def test_login_sets_http_only_strict_cookie(client: httpx.AsyncClient, container: Container) -> None:
    async with unit_of_work(container.session_factory) as s:
        await container.auth(s).create_admin(ADMIN_USER, ADMIN_PASSWORD)
    response = await client.post("/login", data={"username": ADMIN_USER, "password": ADMIN_PASSWORD})
    cookie = response.headers["set-cookie"].lower()
    assert response.status_code == 303 and "httponly" in cookie and "samesite=strict" in cookie


async def test_wrong_password_is_generic_and_locks_after_limit(client: httpx.AsyncClient, container: Container) -> None:
    async with unit_of_work(container.session_factory) as s:
        await container.auth(s).create_admin(ADMIN_USER, ADMIN_PASSWORD)
    unknown = await client.post("/login", data={"username": "ghost", "password": "whatever-123456"})
    wrong = await client.post("/login", data={"username": ADMIN_USER, "password": "wrong-password-1"})
    assert unknown.status_code == wrong.status_code == 401
    assert "Invalid username, password or code." in unknown.text and "Invalid username" in wrong.text
    for _ in range(2):  # login_max_failures=3 in tests
        await client.post("/login", data={"username": ADMIN_USER, "password": "wrong-password-1"})
    locked = await client.post("/login", data={"username": ADMIN_USER, "password": ADMIN_PASSWORD})
    assert locked.status_code == 401 and "Too many failed attempts" in locked.text


async def test_open_redirect_is_blocked(client: httpx.AsyncClient, container: Container) -> None:
    async with unit_of_work(container.session_factory) as s:
        await container.auth(s).create_admin(ADMIN_USER, ADMIN_PASSWORD)
    response = await client.post(
        "/login", data={"username": ADMIN_USER, "password": ADMIN_PASSWORD, "next": "//evil.example"}
    )
    assert response.headers["location"] == "/"


async def test_post_without_csrf_is_rejected(admin_client: httpx.AsyncClient) -> None:
    response = await admin_client.post("/admin/bots/poly-scanner/mode", data={"mode": "shadow"})
    assert response.status_code == 403


async def test_credential_secret_is_encrypted_and_never_rendered(
    admin_client: httpx.AsyncClient, container: Container
) -> None:
    token = await csrf_from(admin_client, "/admin/keys/new?provider=binance")
    response = await admin_client.post(
        "/admin/keys",
        data={
            "csrf_token": token,
            "provider": "binance",
            "environment": "testnet",
            "label": "bn test",
            "field_api_key": "public-looking-key-1234",
            "field_api_secret": SECRET,
        },
    )
    assert response.status_code == 303

    page = await admin_client.get("/admin/keys")
    assert "bn test" in page.text and "…1234" in page.text
    assert SECRET not in page.text and "public-looking-key-1234" not in page.text

    async with container.session_factory() as s:
        row = (await s.execute(select(ApiCredential))).scalar_one()
        assert SECRET.encode() not in row.secret_ciphertext
        revealed = await container.vault(s).reveal_for_worker(row.id)
    assert revealed == {"api_key": "public-looking-key-1234", "api_secret": SECRET}

    audit = await admin_client.get("/admin/audit")
    assert "credential.created" in audit.text and SECRET not in audit.text


async def test_invalid_credential_environment_shows_error(admin_client: httpx.AsyncClient) -> None:
    token = await csrf_from(admin_client, "/admin/keys/new?provider=binance")
    response = await admin_client.post(
        "/admin/keys",
        data={
            "csrf_token": token,
            "provider": "binance",
            "environment": "demo",
            "field_api_key": "k",
            "field_api_secret": "s",
        },
    )
    assert response.status_code == 422 and "does not support" in response.text


@pytest.mark.parametrize(("target", "status", "text"), [("shadow", 303, None), ("live", 422, "through PAPER")])
async def test_bot_mode_changes_follow_policy(
    admin_client: httpx.AsyncClient, target: str, status: int, text: str | None
) -> None:
    token = await csrf_from(admin_client, "/admin/bots")
    response = await admin_client.post("/admin/bots/poly-scanner/mode", data={"csrf_token": token, "mode": target})
    assert response.status_code == status
    if text:
        assert text in response.text


async def test_wallet_watchlist_validates_address(admin_client: httpx.AsyncClient) -> None:
    token = await csrf_from(admin_client, "/polymarket/wallets")
    bad = await admin_client.post("/polymarket/wallets/track", data={"csrf_token": token, "address": "0x123"})
    assert bad.status_code == 422
    good = await admin_client.post("/polymarket/wallets/track", data={"csrf_token": token, "address": "0x" + "ab" * 20})
    assert good.status_code == 303
    page = await admin_client.get("/polymarket/wallets")
    assert "watchlist" in page.text


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/polymarket/scanner",
        "/polymarket/paper",
        "/polymarket/wallets",
        "/admin/bots",
        "/admin/keys",
        "/admin/audit",
        "/account/2fa",
    ],
)
async def test_every_page_renders_for_admin(admin_client: httpx.AsyncClient, path: str) -> None:
    response = await admin_client.get(path)
    assert response.status_code == 200, response.text[:500]


async def test_logout_clears_session(admin_client: httpx.AsyncClient) -> None:
    token = await csrf_from(admin_client, "/")
    response = await admin_client.post("/logout", data={"csrf_token": token})
    assert response.status_code == 303
    assert (await admin_client.get("/")).status_code == 303
