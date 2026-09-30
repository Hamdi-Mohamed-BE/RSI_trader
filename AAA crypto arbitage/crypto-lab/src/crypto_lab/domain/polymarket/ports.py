"""Ports (interfaces) the Polymarket application services depend on. Infrastructure provides the adapters."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from crypto_lab.domain.polymarket.market import Event
from crypto_lab.domain.polymarket.orderbook import OrderBook
from crypto_lab.domain.polymarket.wallets import ClosedPosition, LeaderboardEntry, WalletTrade


class MarketCatalog(Protocol):
    async def active_events(self, *, max_events: int, min_volume_24h: float) -> Sequence[Event]:
        """Open, order-book-enabled events sorted by 24h volume (descending)."""


class BookSource(Protocol):
    async def books(self, token_ids: Sequence[str]) -> dict[str, OrderBook]:
        """Current books keyed by token id. Missing or empty books are omitted."""


class WalletDataSource(Protocol):
    async def leaderboard(self, *, period: str, order_by: str, limit: int) -> Sequence[LeaderboardEntry]:
        """Top wallets for ``period`` (DAY/WEEK/MONTH/ALL) ranked by ``order_by`` (PNL/VOL)."""

    async def closed_positions(self, wallet: str, *, max_rows: int) -> Sequence[ClosedPosition]:
        """Most recent closed positions of ``wallet``."""

    async def trades(self, wallet: str, *, max_rows: int) -> Sequence[WalletTrade]:
        """Most recent trades of ``wallet``."""
