"""Repositories for Model D tables."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from crypto_lab.domain.polymarket.wallets import WalletTrade
from crypto_lab.infrastructure.db.polymarket_models import (
    PmOpportunity,
    PmPaperTrade,
    PmScanRun,
    PmWallet,
    PmWalletTrade,
)


@dataclass(frozen=True, slots=True)
class PaperSummary:
    trades: int
    settled: int
    open: int
    missed: int
    realized_pnl: Decimal
    locked_capital: Decimal
    first_at: datetime | None
    last_at: datetime | None


class ScannerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add_run(self, run: PmScanRun) -> PmScanRun:
        self._s.add(run)
        await self._s.flush()
        return run

    async def recent_runs(self, limit: int = 20) -> Sequence[PmScanRun]:
        stmt = select(PmScanRun).order_by(PmScanRun.started_at.desc()).limit(limit)
        return (await self._s.execute(stmt)).scalars().all()

    async def active_by_fingerprint(self, fingerprint: str) -> PmOpportunity | None:
        stmt = select(PmOpportunity).where(PmOpportunity.fingerprint == fingerprint, PmOpportunity.active.is_(True))
        return (await self._s.execute(stmt)).scalars().first()

    async def add_opportunity(self, row: PmOpportunity) -> PmOpportunity:
        self._s.add(row)
        await self._s.flush()
        return row

    async def deactivate_except(self, fingerprints: set[str]) -> int:
        """Mark opportunities not seen in the latest pass as gone. Returns how many closed."""
        stmt = update(PmOpportunity).where(PmOpportunity.active.is_(True))
        if fingerprints:
            stmt = stmt.where(PmOpportunity.fingerprint.not_in(fingerprints))
        result = await self._s.execute(stmt.values(active=False))
        return int(getattr(result, "rowcount", 0) or 0)

    async def opportunities(self, *, active_only: bool, limit: int = 200) -> Sequence[PmOpportunity]:
        stmt = select(PmOpportunity)
        if active_only:
            stmt = stmt.where(PmOpportunity.active.is_(True))
        stmt = stmt.order_by(PmOpportunity.last_seen_at.desc()).limit(limit)
        return (await self._s.execute(stmt)).scalars().all()

    async def add_paper_trade(self, row: PmPaperTrade) -> PmPaperTrade:
        self._s.add(row)
        await self._s.flush()
        return row

    async def paper_trades(self, limit: int = 200) -> Sequence[PmPaperTrade]:
        stmt = select(PmPaperTrade).order_by(PmPaperTrade.opened_at.desc()).limit(limit)
        return (await self._s.execute(stmt)).scalars().all()

    async def settled_paper_trades(self) -> Sequence[PmPaperTrade]:
        stmt = select(PmPaperTrade).where(PmPaperTrade.status == "settled").order_by(PmPaperTrade.settled_at)
        return (await self._s.execute(stmt)).scalars().all()

    async def open_paper_trades(self) -> Sequence[PmPaperTrade]:
        stmt = select(PmPaperTrade).where(PmPaperTrade.status == "open")
        return (await self._s.execute(stmt)).scalars().all()

    async def paper_traded_recently(self, fingerprint: str, since: datetime) -> bool:
        stmt = (
            select(func.count())
            .select_from(PmPaperTrade)
            .where(PmPaperTrade.fingerprint == fingerprint, PmPaperTrade.opened_at >= since)
        )
        return int((await self._s.execute(stmt)).scalar_one()) > 0

    async def paper_summary(self) -> PaperSummary:
        rows = (await self._s.execute(select(PmPaperTrade))).scalars().all()
        settled = [r for r in rows if r.status == "settled"]
        open_ = [r for r in rows if r.status == "open"]
        times = sorted(r.opened_at for r in rows if r.status != "missed")
        return PaperSummary(
            trades=len(settled) + len(open_),
            settled=len(settled),
            open=len(open_),
            missed=sum(1 for r in rows if r.status == "missed"),
            realized_pnl=sum((r.realized_pnl or Decimal(0) for r in settled), Decimal(0)),
            locked_capital=sum((r.capital for r in open_), Decimal(0)),
            first_at=times[0] if times else None,
            last_at=times[-1] if times else None,
        )


class WalletRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, address: str) -> PmWallet | None:
        return await self._s.get(PmWallet, address.lower())

    async def upsert(self, address: str) -> PmWallet:
        wallet = await self.get(address)
        if wallet is None:
            wallet = PmWallet(address=address.lower())
            self._s.add(wallet)
            await self._s.flush()
        return wallet

    async def list(self, *, tracked_only: bool = False, limit: int = 500) -> Sequence[PmWallet]:
        stmt = select(PmWallet)
        if tracked_only:
            stmt = stmt.where(PmWallet.tracked.is_(True))
        stmt = stmt.order_by(PmWallet.leaderboard_rank.is_(None), PmWallet.leaderboard_rank).limit(limit)
        return (await self._s.execute(stmt)).scalars().all()

    async def add_trades(self, trades: Sequence[WalletTrade]) -> int:
        """Insert trades, ignoring ones already stored. Returns the number of new rows."""
        if not trades:
            return 0
        values = [
            {
                "wallet": t.wallet,
                "tx_hash": t.tx_hash,
                "asset": t.asset,
                "condition_id": t.condition_id,
                "side": t.side,
                "size": t.size,
                "price": t.price,
                "outcome": t.outcome,
                "outcome_index": t.outcome_index,
                "title": t.title[:300],
                "slug": t.slug[:200],
                "event_slug": t.event_slug[:200],
                "at": t.at,
            }
            for t in trades
        ]
        stmt = sqlite_insert(PmWalletTrade).values(values).on_conflict_do_nothing()
        result = await self._s.execute(stmt)
        return int(getattr(result, "rowcount", 0) or 0)

    async def trades(self, address: str, limit: int = 200) -> Sequence[PmWalletTrade]:
        stmt = (
            select(PmWalletTrade)
            .where(PmWalletTrade.wallet == address.lower())
            .order_by(PmWalletTrade.at.desc())
            .limit(limit)
        )
        return (await self._s.execute(stmt)).scalars().all()
