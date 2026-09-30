"""Atomic shared paper spending; fees belong in capital/proceeds, not a separate hidden wallet."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from crypto_lab.infrastructure.db.base import utcnow
from crypto_lab.infrastructure.db.models import Bot
from crypto_lab.infrastructure.db.paper_models import PaperAccount, PaperEvent, PaperPosition, PaperState
from crypto_lab.infrastructure.db.polymarket_models import PmPaperTrade

ZERO = Decimal(0)


@dataclass(frozen=True)
class Portfolio:
    initial: Decimal
    limit: Decimal
    cash: Decimal
    locked: Decimal
    realized: Decimal
    marked_equity: Decimal | None


async def portfolio(session: AsyncSession, fallback: Decimal = Decimal(100)) -> Portfolio:
    account = await session.get(PaperAccount, 1)
    initial, limit = (account.initial, account.trade_limit) if account else (fallback, Decimal(10))
    positions = list(await session.scalars(select(PaperPosition)))
    pm = list(await session.scalars(select(PmPaperTrade).where(PmPaperTrade.status != "missed")))
    locked = sum((p.capital for p in positions if p.closed_at is None), ZERO)
    locked += sum((p.capital for p in pm if p.status == "open"), ZERO)
    realized = sum((p.proceeds - p.capital for p in positions if p.proceeds is not None), ZERO)
    realized += sum((p.realized_pnl or ZERO for p in pm if p.status == "settled"), ZERO)
    cash = initial + realized - locked
    open_positions = [p for p in positions if p.closed_at is None]
    stale = utcnow() - timedelta(minutes=5)
    unknown = any(p.mark is None or p.mark_at is None or p.mark_at < stale for p in open_positions)
    unknown |= any(p.status == "open" for p in pm)
    equity = None if unknown else cash + sum((p.mark or ZERO for p in open_positions), ZERO)
    return Portfolio(initial, limit, cash, locked, realized, equity)


async def state(session: AsyncSession, key: str) -> dict[str, Any]:
    row = await session.get(PaperState, key)
    return row.value if row else {}


async def save_state(session: AsyncSession, key: str, value: dict[str, Any]) -> None:
    row = await session.get(PaperState, key)
    if row:
        row.value = value
    else:
        session.add(PaperState(key=key, value=value))


async def open_position(session: AsyncSession, position: PaperPosition) -> str:
    """Call in a fresh BEGIN IMMEDIATE transaction; recheck control and budget at commit time."""
    bot = await session.get(Bot, position.bot)
    if not bot or bot.mode != "paper" or bot.kill_requested:
        return "Bot is not enabled for paper entries."
    if await session.scalar(select(PaperPosition.id).where(PaperPosition.key == position.key)):
        return "Signal already processed."
    held = list(
        await session.scalars(
            select(PaperPosition).where(PaperPosition.bot == position.bot, PaperPosition.closed_at.is_(None))
        )
    )
    caps = {"poly-copy": 3, "sol-rotation": 1, "cex-arb": 2}
    if len(held) >= caps.get(position.bot, 10):
        return "This bot's open-position limit is reached."
    if position.bot == "poly-copy" and any(r.detail.get("asset") == position.detail.get("asset") for r in held):
        return "Already holding this copied asset."
    p = await portfolio(session)
    if not position.capital.is_finite() or not ZERO < position.capital <= p.limit:
        return "Entry exceeds the 10 USDC all-in cap."
    if position.capital > p.cash:
        return "Shared paper cash is already committed."
    if not position.quantity.is_finite() or position.quantity <= 0:
        return "Invalid quantity."
    session.add(position)
    session.add(
        PaperEvent(
            bot=position.bot,
            status="opened",
            message=f"{position.symbol}: {position.capital:.4f} USDC committed (including entry costs).",
        )
    )
    await session.flush()
    return ""


async def close_position(session: AsyncSession, position_id: int, proceeds: Decimal, reason: str) -> bool:
    """Idempotent full close. Missing quotes must never be passed as zero proceeds."""
    row = await session.get(PaperPosition, position_id)
    if row is None or row.closed_at is not None:
        return False
    bot = await session.get(Bot, row.bot)
    if not bot or bot.mode != "paper" or bot.kill_requested:
        return False
    if not proceeds.is_finite() or proceeds < 0:
        raise ValueError("Invalid exit proceeds")
    row.proceeds, row.closed_at, row.mark, row.mark_at = proceeds, utcnow(), proceeds, utcnow()
    row.detail = {**row.detail, "exit_reason": reason}
    session.add(
        PaperEvent(
            bot=row.bot, status="closed", message=f"{row.symbol}: {reason}; net P/L {proceeds - row.capital:+.4f} USDC."
        )
    )
    await session.flush()
    return True


async def lock_portfolio(session: AsyncSession) -> None:
    # SQLite serializes competing workers/processes BEFORE they read the cash balance.
    await session.execute(text("BEGIN IMMEDIATE"))
