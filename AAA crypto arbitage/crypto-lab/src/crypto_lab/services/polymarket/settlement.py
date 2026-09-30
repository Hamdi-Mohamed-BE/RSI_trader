"""Release held basket capital only after explicit binary resolution, never just an end date."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from crypto_lab.container import Container
from crypto_lab.infrastructure.db.base import utcnow
from crypto_lab.infrastructure.db.models import Bot
from crypto_lab.infrastructure.db.paper_models import PaperEvent
from crypto_lab.infrastructure.db.polymarket_models import PmPaperTrade
from crypto_lab.infrastructure.db.session import unit_of_work
from crypto_lab.infrastructure.http import JsonHttpClient
from crypto_lab.services.paper import lock_portfolio
from crypto_lab.workers.copy import resolved_price


async def settle_baskets(container: Container, gamma: JsonHttpClient) -> int:
    async with container.session_factory() as s:
        holdings = list(await s.scalars(select(PmPaperTrade).where(PmPaperTrade.status == "open")))
    count = 0
    for row in holdings:
        payouts = []
        for leg in row.legs:
            markets = await gamma.get("/markets", clob_token_ids=leg["token_id"])
            prices = [resolved_price(m, leg["token_id"]) for m in markets]
            price = next((p for p in prices if p is not None), None)
            if price is None or leg["side"].lower() != "buy":
                break
            payouts.append(Decimal(leg["shares"]) * price)
        if not row.legs or len(payouts) != len(row.legs):
            continue
        async with unit_of_work(container.session_factory) as s:
            await lock_portfolio(s)
            control = await s.get(Bot, "poly-scanner")
            current = await s.get(PmPaperTrade, row.id)
            if not control or control.mode != "paper" or control.kill_requested:
                return count
            if current and current.status == "open":
                current.payout = sum(payouts, Decimal(0))
                current.realized_pnl = current.payout - current.capital
                current.status, current.settled_at = "settled", utcnow()
                current.note = "All basket legs explicitly resolved; no date-based settlement assumption."
                s.add(
                    PaperEvent(
                        bot="poly-scanner",
                        status="settled",
                        message=f"Basket {row.id}: {current.realized_pnl:+.4f} USDC net.",
                    )
                )
                count += 1
    return count
