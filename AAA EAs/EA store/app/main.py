from __future__ import annotations

import json
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .catalog import (
    INSTALLER_PATH,
    PACKAGE_ROOT,
    STORE_ROOT,
    WHATSAPP_NUMBER,
    Product,
    get_development_catalog,
    get_catalog,
    get_product,
    get_sellable_catalog,
    package_buy_url,
)
from .mt5_live import live_mt5


@asynccontextmanager
async def lifespan(_app: FastAPI):
    live_mt5.start()
    try:
        yield
    finally:
        live_mt5.stop()


app = FastAPI(
    title="HAMA Algo Systems",
    description="Evidence-first MT5 Expert Advisor catalogue synchronized with the active installer.",
    version="0.1.0",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=STORE_ROOT / "static"), name="static")
templates = Jinja2Templates(directory=STORE_ROOT / "templates")


def money(value: float | int) -> str:
    return f"${value:,.0f}" if float(value).is_integer() else f"${value:,.2f}"


def percent(value: float | int, signed: bool = False) -> str:
    prefix = "+" if signed and float(value) > 0 else ""
    return f"{prefix}{float(value):,.2f}%"


templates.env.filters["money"] = money
templates.env.filters["percent"] = percent


def _base_context(request: Request, active: str) -> dict[str, Any]:
    products = get_sellable_catalog()
    development = get_development_catalog()
    return {
        "request": request,
        "active": active,
        "product_count": len(products),
        "installer_product_count": len(products) + len(development),
        "development_count": len(development),
        "whatsapp_number": WHATSAPP_NUMBER,
        "whatsapp_display": "+216 93 830 957",
        "current_year": datetime.now().year,
        "installer_updated": datetime.fromtimestamp(INSTALLER_PATH.stat().st_mtime).strftime("%d %b %Y"),
    }


def _portfolio_audit() -> dict[str, Any]:
    path = PACKAGE_ROOT / "Active BAT Backtest 2026-08-12" / "portfolio-results.json"
    chart = PACKAGE_ROOT / "Active BAT Backtest 2026-08-12" / "Charts" / "combined-realized-balance.png"
    if not path.exists():
        return {"available": False, "chart": None}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    combined = data["combined"]
    return {
        "available": True,
        "tested_eas": int(combined["tested_eas"]),
        "initial": float(combined["initial"]),
        "final": float(combined["final"]),
        "net": float(combined["net"]),
        "return_pct": float(combined["return_pct"]),
        "profit_factor": float(combined["profit_factor"]),
        "win_rate_pct": float(combined["win_rate_pct"]),
        "trades": int(combined["trades"]),
        "realized_balance_dd_pct": float(combined["realized_balance_dd_pct"]),
        "verdict": "PROFITABLE ONE-YEAR OVERLAY",
        "period": "2025-08-11 to 2026-08-10",
        "chart": chart if chart.exists() else None,
    }


@app.get("/store", response_class=HTMLResponse)
async def storefront(request: Request) -> HTMLResponse:
    products = get_sellable_catalog()
    ranked_products = sorted(
        products,
        key=lambda product: product.one_year_return_pct if product.one_year_return_pct is not None else float("-inf"),
        reverse=True,
    )
    featured = ranked_products[:4]
    validated = sum(1 for product in products if product.evidence and product.evidence.status == "Validated evidence")
    context = _base_context(request, "store") | {
        "featured": featured,
        "ranked_products": ranked_products,
        "validated_count": validated,
        "asset_count": len({product.asset_group for product in products}),
        "portfolio": _portfolio_audit(),
        "package_url": package_buy_url("Complete Available EA Portfolio", 1990),
    }
    return templates.TemplateResponse(request=request, name="home.html", context=context)


@app.get("/eas", response_class=HTMLResponse)
async def catalogue(
    request: Request,
    q: str = Query(default="", max_length=80),
    asset: str = Query(default="all", pattern=r"^(all|metals|indices|crypto|stocks)$"),
    evidence: str = Query(default="all", pattern=r"^(all|validated|research|experimental)$"),
) -> HTMLResponse:
    products = get_sellable_catalog()
    query = q.strip().lower()
    if query:
        products = [
            product
            for product in products
            if query in " ".join([product.label, product.strategy, product.canonical, product.tagline]).lower()
        ]
    if asset != "all":
        products = [product for product in products if product.asset_group == asset]
    if evidence != "all":
        products = [
            product
            for product in products
            if product.evidence and product.evidence.status.lower().startswith(evidence)
        ]
    context = _base_context(request, "catalogue") | {
        "products": products,
        "query": q,
        "selected_asset": asset,
        "selected_evidence": evidence,
        "result_count": len(products),
        "groups": Counter(product.asset_group for product in get_sellable_catalog()),
    }
    return templates.TemplateResponse(request=request, name="catalogue.html", context=context)


@app.get("/eas/{slug}", response_class=HTMLResponse)
async def product_detail(request: Request, slug: str) -> HTMLResponse:
    product = get_product(slug)
    if product is None:
        raise HTTPException(status_code=404, detail="EA not found")
    related = [
        item for item in get_sellable_catalog() if item.slug != product.slug and item.asset_group == product.asset_group
    ][:3]
    context = _base_context(request, "catalogue") | {"product": product, "related": related}
    return templates.TemplateResponse(request=request, name="detail.html", context=context)


@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio(request: Request) -> HTMLResponse:
    products = get_sellable_catalog()
    groups: dict[str, list[Product]] = {}
    for product in products:
        groups.setdefault(product.category, []).append(product)
    context = _base_context(request, "portfolio") | {
        "products": products,
        "groups": groups,
        "portfolio": _portfolio_audit(),
        "full_price": sum(product.price for product in products),
        "package_price": 1990,
        "package_url": package_buy_url("Complete Available EA Portfolio", 1990),
    }
    return templates.TemplateResponse(request=request, name="portfolio.html", context=context)


@app.get("/pricing", response_class=HTMLResponse)
async def pricing(request: Request) -> HTMLResponse:
    products = get_sellable_catalog()
    packages = [
        {
            "name": "Choose one EA",
            "price": "From $149",
            "description": "One compiled EA, its active BAT preset and installation guidance.",
            "features": ["1 live + 1 demo MT5 account", "Compiled EX5 and SET", "12 months of updates", "WhatsApp setup support"],
            "url": package_buy_url("Individual EA License", 149),
            "featured": False,
        },
        {
            "name": "Complete Available Portfolio",
            "price": "$1,990",
            "description": f"All {len(products)} currently available EAs. Development builds are excluded.",
            "features": ["All available EAs and presets", "Installer and symbol mapping", "1 live + 1 demo MT5 account", "Priority WhatsApp setup support"],
            "url": package_buy_url("Complete Available EA Portfolio", 1990),
            "featured": True,
        },
    ]
    context = _base_context(request, "pricing") | {
        "packages": packages,
        "individual_total": sum(product.price for product in products),
        "package_price": 1990,
    }
    return templates.TemplateResponse(request=request, name="pricing.html", context=context)


@app.get("/risk", response_class=HTMLResponse)
async def risk(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="risk.html",
        context=_base_context(request, "risk") | {"portfolio": _portfolio_audit()},
    )


@app.get("/", response_class=HTMLResponse)
@app.get("/live", response_class=HTMLResponse)
async def live_portfolio(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="live.html",
        context=_base_context(request, "live"),
    )


@app.get("/evidence/{slug}.png", name="evidence_chart")
async def evidence_chart(slug: str) -> FileResponse:
    product = get_product(slug)
    if product is None or product.evidence is None or product.evidence.chart_path is None:
        raise HTTPException(status_code=404, detail="Evidence chart not found")
    path = product.evidence.chart_path.resolve()
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Evidence chart not found")
    return FileResponse(
        path,
        media_type="image/png",
        filename=f"{slug}-equity.png",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


@app.get("/portfolio/equity.png", name="portfolio_chart")
async def portfolio_chart() -> FileResponse:
    audit = _portfolio_audit()
    path: Path | None = audit.get("chart")
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="Portfolio chart not found")
    return FileResponse(
        path,
        media_type="image/png",
        filename="active-bat-portfolio-equity.png",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


@app.get("/api/eas")
async def api_eas() -> JSONResponse:
    payload = [product.model_dump(mode="json") for product in get_sellable_catalog()]
    for product in payload:
        evidence = product.get("evidence")
        if evidence:
            evidence.pop("chart_path", None)
            evidence["chart_url"] = f"/evidence/{product['slug']}.png?period=1y"
    return JSONResponse(payload)


@app.get("/api/health")
async def api_health() -> dict[str, Any]:
    products = get_catalog()
    sellable = get_sellable_catalog()
    live_state = live_mt5.snapshot()
    return {
        "status": "ok",
        "catalogue_source": str(INSTALLER_PATH),
        "active_entries": len(products),
        "available_entries": len(sellable),
        "development_entries": len(products) - len(sellable),
        "whatsapp_checkout": True,
        "live_mt5_telemetry": bool(live_state["connected"]),
        "live_mt5_last_update": live_state["last_update"],
    }


@app.get("/api/live/portfolio")
async def api_live_portfolio() -> JSONResponse:
    return JSONResponse(
        live_mt5.snapshot(),
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


@app.exception_handler(404)
async def not_found(request: Request, _exc: Exception) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="404.html",
        context=_base_context(request, "") | {},
        status_code=404,
    )
