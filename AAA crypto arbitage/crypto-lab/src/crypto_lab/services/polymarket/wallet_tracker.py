"""Wallet tracker (Model D): leaderboard ingest, trade history and descriptive wallet statistics."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from crypto_lab.domain.errors import ValidationError
from crypto_lab.domain.polymarket.ports import WalletDataSource
from crypto_lab.domain.polymarket.wallets import WalletStats, compute_wallet_stats
from crypto_lab.infrastructure.db.base import utcnow
from crypto_lab.infrastructure.db.polymarket_repositories import WalletRepository
from crypto_lab.infrastructure.db.session import unit_of_work
from crypto_lab.services.audit import Actor, AuditService

logger = logging.getLogger(__name__)

ADDRESS_LEN = 42


@dataclass(frozen=True, slots=True)
class WalletTrackerSettings:
    period: str = "MONTH"
    order_by: str = "PNL"
    top_n: int = 50
    max_closed_positions: int = 500
    max_trades: int = 1_000


@dataclass(frozen=True, slots=True)
class TrackerReport:
    leaderboard_wallets: int
    wallets_refreshed: int
    new_trades: int
    errors: int


def stats_to_json(stats: WalletStats) -> dict[str, Any]:
    def convert(value: Any) -> Any:
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Enum):
            return value.value
        return value

    return {k: convert(v) for k, v in asdict(stats).items()}


def validate_address(address: str) -> str:
    address = address.strip().lower()
    if (
        len(address) != ADDRESS_LEN
        or not address.startswith("0x")
        or not all(c in "0123456789abcdef" for c in address[2:])
    ):
        raise ValidationError("Enter a 0x-prefixed 40-hex-character wallet address.")
    return address


class WalletTrackerService:
    def __init__(
        self,
        source: WalletDataSource,
        session_factory: async_sessionmaker[AsyncSession],
        settings: WalletTrackerSettings | None = None,
    ) -> None:
        self._source = source
        self._sessions = session_factory
        self._settings = settings or WalletTrackerSettings()

    async def refresh_leaderboard(self) -> list[str]:
        s = self._settings
        entries = await self._source.leaderboard(period=s.period, order_by=s.order_by, limit=s.top_n)
        async with unit_of_work(self._sessions) as session:
            repo = WalletRepository(session)
            for entry in entries:
                wallet = await repo.upsert(entry.wallet)
                wallet.user_name = entry.user_name[:80]
                wallet.leaderboard_period = s.period
                wallet.leaderboard_rank = entry.rank
                wallet.leaderboard_pnl = entry.pnl
                wallet.leaderboard_volume = entry.volume
        return [e.wallet for e in entries]

    async def refresh_wallet(self, address: str) -> tuple[WalletStats, int]:
        address = validate_address(address)
        closed = await self._source.closed_positions(address, max_rows=self._settings.max_closed_positions)
        trades = await self._source.trades(address, max_rows=self._settings.max_trades)
        stats = compute_wallet_stats(closed, trades)
        async with unit_of_work(self._sessions) as session:
            repo = WalletRepository(session)
            wallet = await repo.upsert(address)
            new_trades = await repo.add_trades(trades)
            wallet.stats = stats_to_json(stats)
            wallet.stats_updated_at = utcnow()
        return stats, new_trades

    async def run_once(self) -> TrackerReport:
        leaders = await self.refresh_leaderboard()
        async with unit_of_work(self._sessions) as session:
            tracked = [w.address for w in await WalletRepository(session).list(tracked_only=True)]
        refreshed = new_trades = errors = 0
        for address in dict.fromkeys([*tracked, *leaders]):
            try:
                _, added = await self.refresh_wallet(address)
            except Exception:  # one bad wallet must not stop the pass; logged with context
                logger.exception("Wallet refresh failed for %s", address)
                errors += 1
                continue
            refreshed += 1
            new_trades += added
        return TrackerReport(len(leaders), refreshed, new_trades, errors)


async def set_wallet_tracked(session: AsyncSession, address: str, tracked: bool, actor: Actor) -> None:
    """Add/remove a wallet from the watchlist (the tracker refreshes tracked wallets every pass)."""
    address = validate_address(address)
    wallet = await WalletRepository(session).upsert(address)
    wallet.tracked = tracked
    await AuditService(session).record(actor, "wallet.tracked" if tracked else "wallet.untracked", address)
