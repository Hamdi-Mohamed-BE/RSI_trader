"""Combined paper portfolio and the work each bot actually did."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from crypto_lab.domain.performance import ClosedTrade, performance_table
from crypto_lab.infrastructure.db.base import utcnow
from crypto_lab.infrastructure.db.models import Bot
from crypto_lab.infrastructure.db.paper_models import PaperEvent, PaperPosition, WorkerLease
from crypto_lab.infrastructure.db.polymarket_models import PmPaperTrade
from crypto_lab.services.paper import portfolio, state
from crypto_lab.web.charts import line_chart_svg
from crypto_lab.web.deps import AdminDep, DbDep
from crypto_lab.web.templating import render

router = APIRouter(tags=["paper"])


async def activity_context(db: AsyncSession) -> dict[str, Any]:
    bots = list(await db.scalars(select(Bot).order_by(Bot.slug)))
    recent = list(await db.scalars(select(PaperEvent).order_by(PaperEvent.id.desc()).limit(200)))
    latest = {}
    for b in bots:
        event = await db.scalar(
            select(PaperEvent).where(PaperEvent.bot == b.slug).order_by(PaperEvent.id.desc()).limit(1)
        )
        latest[b.slug] = event
    leases = {item.slug: item for item in await db.scalars(select(WorkerLease))}
    health = {}
    for b in bots:
        lease = leases.get(b.slug)
        if b.mode == "off" or b.kill_requested:
            health[b.slug] = "Stopped"
        elif not lease or lease.at < utcnow() - timedelta(seconds=30):
            health[b.slug] = "Not running"
        elif b.last_error:
            health[b.slug] = "Running · retrying an error"
        else:
            health[b.slug] = "Running"
    return {"bots": bots, "activity": recent, "latest": latest, "health": health}


@router.get("/paper")
async def paper_dashboard(request: Request, db: DbDep, admin: AdminDep) -> Response:
    p = await portfolio(db)
    positions = list(await db.scalars(select(PaperPosition).order_by(PaperPosition.id.desc())))
    scanner = list(await db.scalars(select(PmPaperTrade).order_by(PmPaperTrade.id.desc())))
    ctx = await activity_context(db)
    closed = [
        ClosedTrade(r.closed_at, r.proceeds - r.capital) for r in positions if r.closed_at and r.proceeds is not None
    ]
    closed += [
        ClosedTrade(r.settled_at or r.opened_at, r.realized_pnl or Decimal(0)) for r in scanner if r.status == "settled"
    ]
    table = performance_table(closed, p.initial)
    rows = []
    for b in ctx["bots"]:
        owned = [r for r in positions if r.bot == b.slug]
        realized = sum((r.proceeds - r.capital for r in owned if r.proceeds is not None), Decimal(0))
        open_count, closed_count = sum(r.closed_at is None for r in owned), sum(r.closed_at is not None for r in owned)
        if b.slug == "poly-scanner":
            realized += sum((r.realized_pnl or Decimal(0) for r in scanner if r.status == "settled"), Decimal(0))
            open_count += sum(r.status == "open" for r in scanner)
            closed_count += sum(r.status == "settled" for r in scanner)
        rows.append({"bot": b, "realized": realized, "open": open_count, "closed": closed_count})
    return render(
        request,
        "paper.html",
        {
            **ctx,
            "portfolio": p,
            "positions": positions[:200],
            "scanner_trades": scanner[:100],
            "rows": rows,
            "table": table,
            "selection": await state(db, "copy-selection"),
            "chart": line_chart_svg([(at, float(v)) for at, v in table.balance_curve], start_value=float(p.initial)),
        },
        admin=admin,
    )


@router.get("/activity")
async def activity(request: Request, db: DbDep, admin: AdminDep) -> Response:
    return render(request, "activity.html", await activity_context(db), admin=admin)
