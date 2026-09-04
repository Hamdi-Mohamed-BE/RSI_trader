from __future__ import annotations

import json
from collections import Counter
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .catalog import (
    FILTERED_AUDIT_ROOT,
    INSTALLER_PATH,
    PACKAGE_ROOT,
    SELECTED_PORTFOLIO_ROOT,
    STORE_ROOT,
    WHATSAPP_NUMBER,
    Product,
    get_development_catalog,
    get_catalog,
    get_product,
    get_sellable_catalog,
    package_buy_url,
)
from .evidence_series import analyse_equity_series, portfolio_equity_series, product_equity_series
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


def _portfolio_audit(mode: str = "standard") -> dict[str, Any]:
    selected_path = SELECTED_PORTFOLIO_ROOT / "selected-portfolio-results.json"
    if selected_path.exists() and mode in {"standard", "current"}:
        data = json.loads(selected_path.read_text(encoding="utf-8-sig"))
        key = "selected_portfolio" if mode == "standard" else "same_12_all_current"
        combined = data[key]
        chart = SELECTED_PORTFOLIO_ROOT / "Charts" / "SELECTED PORTFOLIO - equity comparison.png"
        return {
            "available": True,
            "tested_eas": len(data.get("per_ea", [])),
            "initial": float(combined["starting_balance"]),
            "final": float(combined["final_balance"]),
            "net": float(combined["net_profit"]),
            "return_pct": float(combined["return_pct"]),
            "profit_factor": float(combined["profit_factor"]),
            "win_rate_pct": float(combined["win_rate_pct"]),
            "trades": int(combined["trades"]),
            "realized_balance_dd_pct": float(combined["realized_dd_pct"]),
            "sharpe_ratio": float(combined["sharpe_ratio"]),
            "recovery_factor": float(combined["recovery_factor"]),
            "verdict": "PROFITABLE LOCKED-YEAR OVERLAY",
            "period": f"{combined['start_date']} to {combined['end_date']}",
            "mode": mode,
            "label": "Applied per-EA configuration" if mode == "standard" else "Original audited 12 — original exits",
            "individually_filtered_eas": sum(1 for value in data.get("selected_setup", {}).values() if value == "dynamic-only") if mode == "standard" else 0,
            "safe_by_design_eas": 0,
            "vendor_unchanged_eas": 0,
            "caution": "Arithmetic overlay of separate locked MT5 tests; not a native shared-margin simultaneous run.",
            "chart": chart if chart.exists() else None,
        }
    modes_path = FILTERED_AUDIT_ROOT / "deployment-mode-results.json"
    path = modes_path if modes_path.exists() else FILTERED_AUDIT_ROOT / "portfolio-results.json"
    chart = FILTERED_AUDIT_ROOT / "selected-portfolio-equity.png"
    if not path.exists():
        return {"available": False, "chart": None}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    combined = data.get(mode, data.get("combined", {}))
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
        "period": str(combined.get("period", "2025-08-11 to 2026-08-21")),
        "mode": mode,
        "label": str(combined.get("label", "Standard current selective configuration")),
        "individually_filtered_eas": int(combined.get("individually_filtered_eas", 3)),
        "safe_by_design_eas": int(combined.get("safe_by_design_eas", 1)),
        "vendor_unchanged_eas": int(combined.get("vendor_unchanged_eas", 2)),
        "caution": combined.get("caution"),
        "chart": chart if chart.exists() else None,
    }


def _portfolio_monte_carlo() -> dict[str, Any]:
    path = SELECTED_PORTFOLIO_ROOT / "selected-portfolio-results.json"
    if not path.exists():
        return {"available": False}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    monte = data.get("monte_carlo", {})
    if not monte:
        return {"available": False}
    return {"available": True, **monte}


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
async def product_detail(
    request: Request,
    slug: str,
    mode: str = Query(default="standard", pattern=r"^(standard|safe)$"),
) -> HTMLResponse:
    product = get_product(slug)
    if product is None:
        raise HTTPException(status_code=404, detail="EA not found")
    related = [
        item for item in get_sellable_catalog() if item.slug != product.slug and item.asset_group == product.asset_group
    ][:3]
    if mode == "safe" and not product.safe_filter_supported:
        mode = "standard"
    display_evidence = product.safe_evidence if mode == "safe" else product.evidence
    context = _base_context(request, "catalogue") | {
        "product": product,
        "related": related,
        "selected_mode": mode,
        "display_evidence": display_evidence,
    }
    return templates.TemplateResponse(request=request, name="detail.html", context=context)


@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio(
    request: Request,
    mode: str = Query(default="standard", pattern=r"^(standard|current|safe)$"),
) -> HTMLResponse:
    products = get_sellable_catalog()
    groups: dict[str, list[Product]] = {}
    for product in products:
        groups.setdefault(product.category, []).append(product)
    context = _base_context(request, "portfolio") | {
        "products": products,
        "groups": groups,
        "portfolio": _portfolio_audit(mode),
        "standard_portfolio": _portfolio_audit("standard"),
        "current_portfolio": _portfolio_audit("current"),
        "monte_carlo": _portfolio_monte_carlo(),
        "selected_mode": mode,
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
            "name": "Choose 3 + bonus EA",
            "price": "$499",
            "description": "Choose any three available EAs and receive one additional available EA selected by us at no extra cost.",
            "features": ["4 EA licenses in total", "You choose the first 3", "One random available bonus EA", "WhatsApp compatibility check"],
            "url": package_buy_url("Choose 3 plus Random Bonus EA", 499),
            "featured": True,
        },
        {
            "name": "Complete Available Portfolio",
            "price": "$1,990",
            "description": f"All {len(products)} currently available EAs. Development builds are excluded.",
            "features": ["All available EAs and presets", "Installer and symbol mapping", "1 live + 1 demo MT5 account", "Priority WhatsApp setup support"],
            "url": package_buy_url("Complete Available EA Portfolio", 1990),
            "featured": False,
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


@app.get("/api/evidence/{slug}/series", name="evidence_series")
async def evidence_series(
    slug: str,
    mode: str = Query(default="standard", pattern=r"^(standard|safe|compare)$"),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
) -> JSONResponse:
    product = get_product(slug)
    if product is None or product.evidence is None:
        raise HTTPException(status_code=404, detail="Evidence series not found")
    if mode == "safe" and not product.safe_filter_supported:
        raise HTTPException(status_code=409, detail="This vendor binary does not support embedded Safe mode")
    selected_mode = "standard" if mode == "compare" else mode
    raw_series = product_equity_series(product, selected_mode)
    evidence = product.safe_evidence if selected_mode == "safe" and product.safe_evidence else product.evidence
    analysed = analyse_equity_series(
        raw_series,
        expected_trades=evidence.trades if evidence else None,
        label=product.label,
        from_date=from_date,
        to_date=to_date,
    )
    series = analysed["series"]
    if len(series) < 2:
        raise HTTPException(status_code=404, detail="Evidence series not found")
    payload: dict[str, Any] = {
        "label": product.label,
        "period": product.evidence.period,
        "currency": "USD",
        "series": series,
        "stats": analysed["stats"],
        "trades": analysed["trades"],
        "available_from": str(raw_series[0]["time"])[:10],
        "available_to": str(raw_series[-1]["time"])[:10],
    }
    if all(bool(point.get("summary")) for point in series):
        payload["series_kind"] = "summary"
        payload["notice"] = "Start-to-finish return line — the detailed trade-by-trade MT5 curve is not archived on this server."
    if mode == "compare" and product.safe_filter_supported:
        safe_raw = product_equity_series(product, "safe")
        safe_evidence = product.safe_evidence or product.evidence
        safe = analyse_equity_series(
            safe_raw,
            expected_trades=safe_evidence.trades if safe_evidence else None,
            label=f"{product.label} — Full Safe",
            from_date=from_date,
            to_date=to_date,
        )
        if len(safe["series"]) >= 2:
            payload["datasets"] = [
                {"label": "Standard", "color": "#7ef7c7", "series": series, "stats": analysed["stats"], "trades": analysed["trades"]},
                {"label": "Full Safe", "color": "#68a7ff", "series": safe["series"], "stats": safe["stats"], "trades": safe["trades"]},
            ]
    return JSONResponse(
        payload,
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


@app.get("/api/portfolio/equity-series", name="portfolio_equity_series")
async def api_portfolio_equity_series(
    mode: str = Query(default="compare", pattern=r"^(standard|current|safe|compare)$"),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
) -> JSONResponse:
    selected_mode = "standard" if mode == "compare" else mode
    audit = _portfolio_audit(selected_mode)
    raw_series = [dict(point) for point in portfolio_equity_series(selected_mode)]
    analysed = analyse_equity_series(
        raw_series,
        expected_trades=int(audit.get("trades", 0)),
        label="Active BAT portfolio",
        from_date=from_date,
        to_date=to_date,
    )
    series = analysed["series"]
    if len(series) < 2:
        raise HTTPException(status_code=404, detail="Portfolio equity series not found")
    payload: dict[str, Any] = {
        "label": "Active BAT portfolio",
        "period": _portfolio_audit(selected_mode).get("period"),
        "currency": "USD",
        "series": series,
        "stats": analysed["stats"],
        "trades": analysed["trades"],
        "available_from": str(raw_series[0]["time"])[:10],
        "available_to": str(raw_series[-1]["time"])[:10],
    }
    if mode == "compare":
        current_audit = _portfolio_audit("current")
        current_raw = [dict(point) for point in portfolio_equity_series("current")]
        current = analyse_equity_series(
            current_raw,
            expected_trades=int(current_audit.get("trades", 0)),
            label="Audited 12 — original exits",
            from_date=from_date,
            to_date=to_date,
        )
        payload["datasets"] = [
            {"label": "Applied per-EA setup", "color": "#7ef7c7", "series": series, "stats": analysed["stats"], "trades": analysed["trades"]},
            {"label": "Audited 12 — original exits", "color": "#68a7ff", "series": current["series"], "stats": current["stats"], "trades": current["trades"]},
        ]
    return JSONResponse(
        payload,
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


@app.get("/api/eas")
async def api_eas() -> JSONResponse:
    payload = [product.model_dump(mode="json") for product in get_sellable_catalog()]
    for product in payload:
        evidence = product.get("evidence")
        if evidence:
            evidence.pop("chart_path", None)
            evidence["series_url"] = f"/api/evidence/{product['slug']}/series"
        safe_evidence = product.get("safe_evidence")
        if safe_evidence:
            safe_evidence.pop("chart_path", None)
            safe_evidence["series_url"] = f"/api/evidence/{product['slug']}/series?mode=safe"
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
