"""Two-factor enrolment, 2FA login and the complete LIVE unlock path."""

import re
from pathlib import Path

import httpx
import pyotp
from sqlalchemy import update

from crypto_lab.config import Settings
from crypto_lab.container import Container
from crypto_lab.infrastructure.db.models import Bot
from crypto_lab.infrastructure.db.session import unit_of_work
from crypto_lab.web.app import create_app
from tests.conftest import ADMIN_PASSWORD, ADMIN_USER, TEST_KEY, csrf_from

SECRET_RE = re.compile(r'name="secret" value="([A-Z2-7]+)"')


async def _enable_totp(client: httpx.AsyncClient) -> str:
    page = await client.get("/account/2fa")
    match = SECRET_RE.search(page.text)
    assert match is not None and "<svg" in page.text
    secret = match.group(1)
    token = await csrf_from(client, "/account/2fa")
    bad = await client.post("/account/2fa", data={"csrf_token": token, "secret": secret, "code": "000000"})
    assert bad.status_code == 422
    ok = await client.post(
        "/account/2fa", data={"csrf_token": token, "secret": secret, "code": pyotp.TOTP(secret).now()}
    )
    assert ok.status_code == 303
    return secret


async def test_enabling_2fa_makes_login_require_a_code(admin_client: httpx.AsyncClient) -> None:
    secret = await _enable_totp(admin_client)
    assert "2FA is on" in (await admin_client.get("/account/2fa")).text
    token = await csrf_from(admin_client, "/")
    await admin_client.post("/logout", data={"csrf_token": token})

    no_code = await admin_client.post("/login", data={"username": ADMIN_USER, "password": ADMIN_PASSWORD})
    assert no_code.status_code == 401
    with_code = await admin_client.post(
        "/login", data={"username": ADMIN_USER, "password": ADMIN_PASSWORD, "code": pyotp.TOTP(secret).now()}
    )
    assert with_code.status_code == 303


async def test_live_mode_unlocks_only_with_flag_gate_confirmation_and_code(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        data_dir=tmp_path,
        allow_dev_key_file=False,
        master_key=TEST_KEY,
        live_trading_enabled=True,
    )
    container = Container.build(settings)
    app = create_app(settings, container=container)
    async with app.router.lifespan_context(app):
        async with unit_of_work(container.session_factory) as s:
            await container.auth(s).create_admin(ADMIN_USER, ADMIN_PASSWORD)
            await s.execute(update(Bot).where(Bot.slug == "poly-scanner").values(mode="paper", gate_passed=True))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client:
            await client.post("/login", data={"username": ADMIN_USER, "password": ADMIN_PASSWORD})
            secret = await _enable_totp(client)
            token = await csrf_from(client, "/admin/bots")

            wrong_confirm = await client.post(
                "/admin/bots/poly-scanner/mode",
                data={"csrf_token": token, "mode": "live", "confirmation": "nope", "code": pyotp.TOTP(secret).now()},
            )
            assert wrong_confirm.status_code == 422 and "Type the bot id" in wrong_confirm.text

            live = await client.post(
                "/admin/bots/poly-scanner/mode",
                data={
                    "csrf_token": token,
                    "mode": "live",
                    "confirmation": "poly-scanner",
                    "code": pyotp.TOTP(secret).now(),
                },
            )
            assert live.status_code == 303

            killed = await client.post("/admin/bots/poly-scanner/kill", data={"csrf_token": token})
            assert killed.status_code == 303
            page = await client.get("/admin/bots")
            assert "set" in page.text  # kill flag shown
    await container.dispose()
