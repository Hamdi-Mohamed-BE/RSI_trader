from datetime import UTC, datetime, timedelta

import pytest

from crypto_lab.container import Container
from crypto_lab.domain.errors import NotFoundError, ValidationError
from crypto_lab.infrastructure.db.session import unit_of_work
from crypto_lab.services.audit import Actor
from crypto_lab.web.charts import line_chart_svg

ACTOR = Actor("tester")


def test_chart_renders_path_and_escapes_label() -> None:
    t0 = datetime(2026, 9, 1, tzinfo=UTC)
    svg = line_chart_svg([(t0, 1005.0), (t0 + timedelta(days=1), 1010.0)], start_value=1000.0, label="<b>")
    assert svg.startswith("<svg") and "&lt;b&gt;" in svg and "<b>" not in svg
    assert "2026-09-01" in svg and "2026-09-02" in svg


def test_chart_empty_state() -> None:
    assert "No settled paper trades yet" in line_chart_svg([], start_value=1000.0)


async def test_vault_rotate_disable_delete_cycle(container: Container) -> None:
    async with unit_of_work(container.session_factory) as s:
        vault = container.vault(s)
        view = await vault.create(
            "telegram", "", "live", {"bot_token": "123456:ABCDEF-token-xyz", "chat_id": "42"}, ACTOR
        )
        assert view.label == "Telegram bot" and view.public_fields == {"chat_id": "42"} and view.hint == "…-xyz"
        rotated = await vault.rotate(view.id, {"bot_token": "999999:NEWTOKEN-abcd", "chat_id": "43"}, ACTOR)
        assert rotated.rotated_at is not None and rotated.hint == "…abcd"
        assert (await vault.reveal_for_worker(view.id))["bot_token"] == "999999:NEWTOKEN-abcd"
        await vault.set_enabled(view.id, False, ACTOR)
        assert (await vault.get(view.id)).enabled is False
        await vault.delete(view.id, ACTOR)
        with pytest.raises(NotFoundError):
            await vault.get(view.id)


async def test_vault_rejects_bad_input(container: Container) -> None:
    async with unit_of_work(container.session_factory) as s:
        vault = container.vault(s)
        with pytest.raises(ValidationError, match="Unknown environment"):
            await vault.create("helius", "", "prod", {"api_key": "k"}, ACTOR)
        with pytest.raises(ValidationError, match="80 characters"):
            await vault.create("helius", "x" * 81, "data", {"api_key": "k"}, ACTOR)
