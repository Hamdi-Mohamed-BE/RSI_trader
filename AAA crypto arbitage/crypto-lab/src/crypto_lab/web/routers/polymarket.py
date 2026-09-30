"""Model D pages: scanner feed, paper ledger with the standard results table, wallet tracker."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from starlette.responses import Response

from crypto_lab.domain.errors import DomainError, NotFoundError
from crypto_lab.domain.performance import ClosedTrade, performance_table
from crypto_lab.infrastructure.db.polymarket_repositories import ScannerRepository, WalletRepository
from crypto_lab.services.polymarket.scanner import ScannerSettings
from crypto_lab.services.polymarket.wallet_tracker import set_wallet_tracked, validate_address
from crypto_lab.web.charts import line_chart_svg
from crypto_lab.web.deps import AdminDep, CsrfAdminDep, DbDep, actor_for
from crypto_lab.web.routers.paper import paper_dashboard
from crypto_lab.web.templating import render

router = APIRouter(prefix="/polymarket", tags=["polymarket"])


@router.get("/scanner")
async def scanner(request: Request, db: DbDep, admin: AdminDep, show: str = "active") -> Response:
    repo = ScannerRepository(db)
    return render(
        request,
        "polymarket/scanner.html",
        {
            "opportunities": await repo.opportunities(active_only=show != "all"),
            "runs": await repo.recent_runs(15),
            "show": show,
        },
        admin=admin,
    )


@router.get("/paper")
async def combined_paper(request: Request, db: DbDep, admin: AdminDep) -> Response:
    return await paper_dashboard(request, db, admin)


@router.get("/paper/scanner-detail")
async def paper(request: Request, db: DbDep, admin: AdminDep) -> Response:
    repo = ScannerRepository(db)
    bankroll = ScannerSettings().paper_bankroll_usdc
    settled = await repo.settled_paper_trades()
    closed = [ClosedTrade(t.settled_at or t.opened_at, t.realized_pnl or Decimal(0)) for t in settled]
    table = performance_table(closed, bankroll)
    chart = line_chart_svg([(at, float(value)) for at, value in table.balance_curve], start_value=float(bankroll))
    return render(
        request,
        "polymarket/paper.html",
        {
            "table": table,
            "summary": await repo.paper_summary(),
            "trades": await repo.paper_trades(200),
            "bankroll": bankroll,
            "chart": chart,
        },
        admin=admin,
    )


async def _wallets_page(
    request: Request, db: DbDep, admin: AdminDep, error: str | None = None, status_code: int = 200
) -> Response:
    return render(
        request,
        "polymarket/wallets.html",
        {"wallets": await WalletRepository(db).list(), "error": error},
        admin=admin,
        status_code=status_code,
    )


@router.get("/wallets")
async def wallets(request: Request, db: DbDep, admin: AdminDep) -> Response:
    return await _wallets_page(request, db, admin)


@router.get("/wallets/{address}")
async def wallet_detail(request: Request, address: str, db: DbDep, admin: AdminDep) -> Response:
    repo = WalletRepository(db)
    wallet = await repo.get(validate_address(address))
    if wallet is None:
        raise NotFoundError("Wallet not tracked yet.")
    return render(
        request,
        "polymarket/wallet_detail.html",
        {"wallet": wallet, "trades": await repo.trades(wallet.address, 200)},
        admin=admin,
    )


@router.post("/wallets/track")
async def track_wallet(
    request: Request,
    db: DbDep,
    admin: CsrfAdminDep,
    address: Annotated[str, Form(max_length=64)],
    tracked: Annotated[bool, Form()] = True,
) -> Response:
    try:
        await set_wallet_tracked(db, address, tracked, actor_for(admin, request))
    except DomainError as exc:
        return await _wallets_page(request, db, admin, error=str(exc), status_code=422)
    await db.commit()
    return RedirectResponse("/polymarket/wallets?flash=saved", status_code=303)
