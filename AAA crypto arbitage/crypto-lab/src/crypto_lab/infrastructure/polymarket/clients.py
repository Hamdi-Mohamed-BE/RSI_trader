"""Read-only adapters for Polymarket's public APIs (no keys needed).

* Gamma API  — events and markets (catalogue)
* CLOB API   — order books
* Data API   — leaderboard, wallet trades and closed positions
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any

import httpx

from crypto_lab.domain.polymarket.market import Event
from crypto_lab.domain.polymarket.orderbook import OrderBook
from crypto_lab.domain.polymarket.wallets import ClosedPosition, LeaderboardEntry, WalletTrade
from crypto_lab.infrastructure.http import JsonHttpClient
from crypto_lab.infrastructure.polymarket import mappers

GAMMA_URL = "https://gamma-api.polymarket.com"
CLOB_URL = "https://clob.polymarket.com"
DATA_URL = "https://data-api.polymarket.com"


def _rows(payload: Any) -> list[dict[str, Any]]:
    return [r for r in payload if isinstance(r, dict)] if isinstance(payload, list) else []


class GammaCatalog:
    """Implements :class:`~crypto_lab.domain.polymarket.ports.MarketCatalog`."""

    PAGE = 100

    def __init__(self, http: JsonHttpClient | None = None, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._http = http or JsonHttpClient(GAMMA_URL, rate_per_second=4, transport=transport)

    async def active_events(self, *, max_events: int, min_volume_24h: float) -> Sequence[Event]:
        events: list[Event] = []
        offset = 0
        while len(events) < max_events:
            page = _rows(
                await self._http.get(
                    "/events",
                    active="true",
                    closed="false",
                    archived="false",
                    order="volume24hr",
                    ascending="false",
                    limit=self.PAGE,
                    offset=offset,
                )
            )
            if not page:
                break
            for raw in page:
                event = mappers.event_from_gamma(raw)
                if event is None or not event.markets:
                    continue
                if float(event.volume_24h) < min_volume_24h:
                    return events  # sorted by volume: the rest are smaller
                events.append(event)
            offset += self.PAGE
        return events[:max_events]

    async def aclose(self) -> None:
        await self._http.aclose()


class ClobBooks:
    """Implements :class:`~crypto_lab.domain.polymarket.ports.BookSource` via the batch ``POST /books`` endpoint."""

    def __init__(
        self,
        http: JsonHttpClient | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        batch_size: int = 50,
    ) -> None:
        self._http = http or JsonHttpClient(CLOB_URL, rate_per_second=8, transport=transport)
        self._batch = batch_size

    async def books(self, token_ids: Sequence[str]) -> dict[str, OrderBook]:
        result: dict[str, OrderBook] = {}
        unique = list(dict.fromkeys(token_ids))
        for start in range(0, len(unique), self._batch):
            chunk = unique[start : start + self._batch]
            payload = await self._http.post("/books", [{"token_id": t} for t in chunk])
            received_ms = int(time.time() * 1000)
            for raw in _rows(payload):
                book = mappers.book_from_clob(raw, received_ms)
                if book is not None:
                    result[book.token_id] = book
        return result

    async def aclose(self) -> None:
        await self._http.aclose()


class DataApiWallets:
    """Implements :class:`~crypto_lab.domain.polymarket.ports.WalletDataSource`."""

    LEADERBOARD_PAGE = 50
    POSITIONS_PAGE = 50
    TRADES_PAGE = 500

    def __init__(self, http: JsonHttpClient | None = None, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._http = http or JsonHttpClient(DATA_URL, rate_per_second=4, transport=transport)

    async def leaderboard(self, *, period: str, order_by: str, limit: int) -> Sequence[LeaderboardEntry]:
        entries: list[LeaderboardEntry] = []
        offset = 0
        while len(entries) < limit:
            page = _rows(
                await self._http.get(
                    "/v1/leaderboard",
                    timePeriod=period.upper(),
                    orderBy=order_by.upper(),
                    limit=self.LEADERBOARD_PAGE,
                    offset=offset,
                )
            )
            entries += [e for e in map(mappers.leaderboard_entry, page) if e is not None]
            if len(page) < self.LEADERBOARD_PAGE:
                break
            offset += self.LEADERBOARD_PAGE
        return entries[:limit]

    async def closed_positions(self, wallet: str, *, max_rows: int) -> Sequence[ClosedPosition]:
        rows: list[ClosedPosition] = []
        offset = 0
        while len(rows) < max_rows:
            page = _rows(
                await self._http.get(
                    "/closed-positions",
                    user=wallet,
                    limit=self.POSITIONS_PAGE,
                    offset=offset,
                    sortBy="TIMESTAMP",
                    sortDirection="DESC",
                )
            )
            rows += [p for p in map(mappers.closed_position, page) if p is not None]
            if len(page) < self.POSITIONS_PAGE:
                break
            offset += self.POSITIONS_PAGE
        return rows[:max_rows]

    async def trades(self, wallet: str, *, max_rows: int) -> Sequence[WalletTrade]:
        rows: list[WalletTrade] = []
        offset = 0
        while len(rows) < max_rows:
            page = _rows(
                await self._http.get("/trades", user=wallet, limit=self.TRADES_PAGE, offset=offset, takerOnly="false")
            )
            rows += [t for t in map(mappers.wallet_trade, page) if t is not None]
            if len(page) < self.TRADES_PAGE:
                break
            offset += self.TRADES_PAGE
        return rows[:max_rows]

    async def aclose(self) -> None:
        await self._http.aclose()
