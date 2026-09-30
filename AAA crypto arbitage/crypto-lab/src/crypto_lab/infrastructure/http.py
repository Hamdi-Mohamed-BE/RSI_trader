"""Async JSON HTTP client with a token-bucket rate limit and bounded retries on 429/5xx/network errors."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from types import TracebackType
from typing import Any

import httpx

logger = logging.getLogger(__name__)

RETRY_STATUS = frozenset({429, 500, 502, 503, 504})


class HttpError(Exception):
    """A request failed after all retries. The message never includes headers or credentials."""


class TokenBucket:
    def __init__(self, rate_per_second: float, burst: int | None = None) -> None:
        self._rate = rate_per_second
        self._capacity = float(burst or max(1, int(rate_per_second)))
        self._tokens = self._capacity
        self._updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                self._tokens = min(self._capacity, self._tokens + (now - self._updated) * self._rate)
                self._updated = now
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
                await asyncio.sleep((1 - self._tokens) / self._rate)


class JsonHttpClient:
    def __init__(
        self,
        base_url: str,
        *,
        rate_per_second: float = 5.0,
        timeout: float = 15.0,
        max_retries: int = 4,
        transport: httpx.AsyncBaseTransport | None = None,
        user_agent: str = "crypto-lab/0.1",
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
            headers={"User-Agent": user_agent, "Accept": "application/json"},
        )
        self._bucket = TokenBucket(rate_per_second)
        self._max_retries = max_retries

    async def request(self, method: str, path: str, *, params: dict[str, Any] | None = None, json: Any = None) -> Any:
        for attempt in range(self._max_retries + 1):
            await self._bucket.acquire()
            try:
                response = await self._client.request(method, path, params=params, json=json)
            except httpx.TransportError as exc:
                if attempt == self._max_retries:
                    raise HttpError(f"{method} {path}: network error ({type(exc).__name__})") from exc
            else:
                if response.status_code < 400:
                    return response.json()
                if response.status_code not in RETRY_STATUS or attempt == self._max_retries:
                    raise HttpError(f"{method} {path}: HTTP {response.status_code}")
            delay = min(30.0, 0.5 * 2**attempt) * (0.5 + random.random())  # noqa: S311 - jitter, not crypto
            logger.debug("Retrying %s %s in %.1fs (attempt %d)", method, path, delay, attempt + 1)
            await asyncio.sleep(delay)
        raise HttpError(f"{method} {path}: retries exhausted")  # pragma: no cover - loop always returns/raises

    async def get(self, path: str, **params: Any) -> Any:
        return await self.request("GET", path, params={k: v for k, v in params.items() if v is not None})

    async def post(self, path: str, json: Any) -> Any:
        return await self.request("POST", path, json=json)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> JsonHttpClient:
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        await self.aclose()
