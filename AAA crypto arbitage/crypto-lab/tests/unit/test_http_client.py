import httpx
import pytest

from crypto_lab.infrastructure.http import HttpError, JsonHttpClient


def _client(handler: httpx.MockTransport, retries: int = 3) -> JsonHttpClient:
    return JsonHttpClient("https://api.test", rate_per_second=1000, max_retries=retries, transport=handler)


async def test_retries_on_429_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("crypto_lab.infrastructure.http.asyncio.sleep", _instant)
    calls = {"n": 0}

    def handle(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429) if calls["n"] < 3 else httpx.Response(200, json={"ok": True})

    async with _client(httpx.MockTransport(handle)) as http:
        assert await http.get("/x") == {"ok": True}
    assert calls["n"] == 3


async def test_client_errors_are_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("crypto_lab.infrastructure.http.asyncio.sleep", _instant)
    calls = {"n": 0}

    def handle(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(404)

    async with _client(httpx.MockTransport(handle)) as http:
        with pytest.raises(HttpError, match="HTTP 404"):
            await http.get("/missing")
    assert calls["n"] == 1


async def test_gives_up_after_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("crypto_lab.infrastructure.http.asyncio.sleep", _instant)

    async with _client(httpx.MockTransport(lambda r: httpx.Response(503)), retries=2) as http:
        with pytest.raises(HttpError, match="HTTP 503"):
            await http.get("/down")


async def _instant(_: float) -> None:
    return None
