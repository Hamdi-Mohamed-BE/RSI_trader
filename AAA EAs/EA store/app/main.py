from __future__ import annotations

import json
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
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
from .evidence_cache import (
    DEFAULT_PERIOD,
    PERIOD_OPTIONS,
    cache_manifest,
    load_cached_trade,
    load_portfolio_cache,
    load_portfolio_summary,
    load_product_cache,
    load_product_summary,
    validate_period,
)
from .mt5_live import live_mt5
from .mt5_evidence_jobs import mt5_evidence_jobs


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


def _cached_display_product(product: Product, period: str = DEFAULT_PERIOD) -> Product:
    cached = load_product_summary(product.slug, "standard", period)
    if not cached or not cached.get("stats") or product.evidence is None:
        return product
    stats = cached["stats"]
    evidence = product.evidence.model_copy(
        update={
            "label": f"Precomputed {next(option['label'] for option in PERIOD_OPTIONS if option['value'] == period)} — active recommended configuration",
            "period": str(cached["period"]),
            "return_pct": float(stats.get("return_pct") or 0),
            "profit_factor": float(stats.get("profit_factor") or 0),
            "win_rate_pct": float(stats.get("win_rate_pct") or 0),
            "drawdown_pct": float(stats.get("max_drawdown_pct") or 0),
            "trades": int(stats.get("trades") or 0),
            "sharpe_ratio": stats.get("sharpe_ratio"),
            "recovery_factor": stats.get("recovery_factor"),
            "history_quality": str(cached.get("history_quality") or "Native MT5 report"),
            "source_note": str(cached.get("notice")),
        }
    )
    changes: dict[str, Any] = {"evidence": evidence}
    if period == DEFAULT_PERIOD:
        changes.update({"one_year_evidence": evidence, "one_year_return_pct": evidence.return_pct})
    return product.model_copy(update=changes)


def _display_catalog(period: str = DEFAULT_PERIOD) -> list[Product]:
    return [_cached_display_product(product, period) for product in get_sellable_catalog()]


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


def _portfolio_audit(mode: str = "standard", period: str = DEFAULT_PERIOD) -> dict[str, Any]:
    cached = load_portfolio_summary("standard", period) if mode == "standard" else None
    if cached and cached.get("stats"):
        combined = cached["stats"]
        return {
            "available": True,
            "tested_eas": int(cached.get("included_ea_count", 0)),
            "initial": float(combined["initial_balance"]),
            "final": float(combined["final_balance"]),
            "net": float(combined["net_profit"]),
            "return_pct": float(combined["return_pct"]),
            "profit_factor": float(combined["profit_factor"] or 0),
            "win_rate_pct": float(combined["win_rate_pct"] or 0),
            "trades": int(combined["trades"]),
            "realized_balance_dd_pct": float(combined["max_drawdown_pct"]),
            "sharpe_ratio": float(combined.get("sharpe_ratio") or 0),
            "recovery_factor": float(combined.get("recovery_factor") or 0),
            "verdict": "PRECOMPUTED RECOMMENDED PORTFOLIO",
            "period": str(cached["period"]),
            "mode": mode,
            "label": "Recommended active configuration",
            "individually_filtered_eas": sum(1 for product in get_sellable_catalog() if product.exit_mode == "Dynamic 50/20"),
            "safe_by_design_eas": 0,
            "vendor_unchanged_eas": 0,
            "caution": cached.get("notice"),
            "chart": None,
        }
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


def _portfolio_monte_carlo(period: str = DEFAULT_PERIOD) -> dict[str, Any]:
    cached = load_portfolio_summary("standard", period)
    if not cached or not cached.get("monte_carlo"):
        return {"available": False}
    return {"available": True, **cached["monte_carlo"]}


def _cached_portfolio_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for option in PERIOD_OPTIONS:
        payload = load_portfolio_summary("standard", option["value"])
        if payload and payload.get("stats"):
            rows.append({"key": option["value"], "label": option["label"], **payload["stats"]})
    return rows


@app.get("/store", response_class=HTMLResponse)
async def storefront(request: Request) -> HTMLResponse:
    products = _display_catalog()
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
    asset: str = Query(default="all", pattern=r"^(all|metals|indices|crypto|forex|stocks)$"),
    symbol: str = Query(default="all", max_length=20),
    evidence: str = Query(default="all", pattern=r"^(all|validated|research|experimental)$"),
    sort: str = Query(
        default="recommended",
        pattern=r"^(recommended|pf-desc|win-desc|dd-asc|return-desc|sharpe-desc|recovery-desc|trades-desc|name-asc)$",
    ),
) -> HTMLResponse:
    all_products = _display_catalog()
    catalogue_order = {product.slug: index for index, product in enumerate(all_products)}
    products = list(all_products)
    query = q.strip().lower()
    selected_symbol = symbol.strip().upper()
    if query:
        products = [
            product
            for product in products
            if query in " ".join([product.label, product.strategy, product.canonical, product.tagline]).lower()
        ]
    if asset != "all":
        products = [product for product in products if product.asset_group == asset]
    if selected_symbol != "ALL":
        products = [product for product in products if product.canonical.upper() == selected_symbol]
    if evidence != "all":
        products = [
            product
            for product in products
            if product.evidence and product.evidence.status.lower().startswith(evidence)
        ]
    sort_rules = {
        "pf-desc": (lambda product: product.evidence.profit_factor if product.evidence else float("-inf"), True),
        "win-desc": (lambda product: product.evidence.win_rate_pct if product.evidence else float("-inf"), True),
        "dd-asc": (lambda product: product.evidence.drawdown_pct if product.evidence else float("inf"), False),
        "return-desc": (lambda product: product.evidence.return_pct if product.evidence else float("-inf"), True),
        "sharpe-desc": (lambda product: product.evidence.sharpe_ratio if product.evidence and product.evidence.sharpe_ratio is not None else float("-inf"), True),
        "recovery-desc": (lambda product: product.evidence.recovery_factor if product.evidence and product.evidence.recovery_factor is not None else float("-inf"), True),
        "trades-desc": (lambda product: product.evidence.trades if product.evidence else -1, True),
        "name-asc": (lambda product: product.label.lower(), False),
    }
    if sort in sort_rules:
        sort_key, reverse = sort_rules[sort]
        products.sort(key=sort_key, reverse=reverse)
    context = _base_context(request, "catalogue") | {
        "products": products,
        "query": q,
        "selected_asset": asset,
        "selected_symbol": selected_symbol.lower(),
        "selected_evidence": evidence,
        "selected_sort": sort,
        "result_count": len(products),
        "groups": Counter(product.asset_group for product in all_products),
        "symbols": Counter(product.canonical for product in all_products),
        "catalogue_order": catalogue_order,
    }
    return templates.TemplateResponse(request=request, name="catalogue.html", context=context)


@app.get("/eas/{slug}", response_class=HTMLResponse)
async def product_detail(
    request: Request,
    slug: str,
    mode: str = Query(default="standard", pattern=r"^(standard|safe)$"),
    period: str = Query(default=DEFAULT_PERIOD, pattern=r"^(6m|1y|3y|5y)$"),
) -> HTMLResponse:
    product = get_product(slug)
    if product is None:
        raise HTTPException(status_code=404, detail="EA not found")
    related = [
        item for item in _display_catalog() if item.slug != product.slug and item.asset_group == product.asset_group
    ][:3]
    if mode == "safe" and not product.safe_filter_supported:
        mode = "standard"
    display_evidence = product.safe_evidence if mode == "safe" else product.evidence
    cached = load_product_summary(product.slug, mode, period)
    if cached and cached.get("stats") and display_evidence is not None:
        stats = cached["stats"]
        display_evidence = display_evidence.model_copy(
            update={
                "label": f"Precomputed {next(option['label'] for option in PERIOD_OPTIONS if option['value'] == period)} — active recommended configuration",
                "period": str(cached["period"]),
                "return_pct": float(stats.get("return_pct") or 0),
                "profit_factor": float(stats.get("profit_factor") or 0),
                "win_rate_pct": float(stats.get("win_rate_pct") or 0),
                "drawdown_pct": float(stats.get("max_drawdown_pct") or 0),
                "trades": int(stats.get("trades") or 0),
                "sharpe_ratio": stats.get("sharpe_ratio"),
                "recovery_factor": stats.get("recovery_factor"),
                "history_quality": str(cached.get("history_quality") or "Native MT5 report"),
                "source_note": str(cached.get("notice")),
            }
        )
    context = _base_context(request, "catalogue") | {
        "product": product,
        "related": related,
        "selected_mode": mode,
        "selected_period": period,
        "period_options": PERIOD_OPTIONS,
        "display_evidence": display_evidence,
    }
    return templates.TemplateResponse(request=request, name="detail.html", context=context)


@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio(
    request: Request,
    mode: str = Query(default="standard", pattern=r"^(standard|current|safe)$"),
    period: str = Query(default=DEFAULT_PERIOD, pattern=r"^(6m|1y|3y|5y)$"),
) -> HTMLResponse:
    products = _display_catalog(period)
    groups: dict[str, list[Product]] = {}
    for product in products:
        groups.setdefault(product.category, []).append(product)
    context = _base_context(request, "portfolio") | {
        "products": products,
        "groups": groups,
        "portfolio": _portfolio_audit("standard", period),
        "standard_portfolio": _portfolio_audit("standard", period),
        "current_portfolio": _portfolio_audit("current"),
        "monte_carlo": _portfolio_monte_carlo(period),
        "selected_mode": "standard",
        "selected_period": period,
        "period_options": PERIOD_OPTIONS,
        "portfolio_period_rows": _cached_portfolio_rows(),
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
    period: str = Query(default=DEFAULT_PERIOD, pattern=r"^(6m|1y|3y|5y)$"),
) -> JSONResponse:
    product = get_product(slug)
    if product is None or product.evidence is None:
        raise HTTPException(status_code=404, detail="Evidence series not found")
    if mode == "safe" and not product.safe_filter_supported:
        raise HTTPException(status_code=409, detail="This vendor binary does not support embedded Safe mode")
    selected_mode = "standard" if mode == "compare" else mode
    payload = load_product_cache(product.slug, selected_mode, period)
    if payload is None:
        raise HTTPException(status_code=503, detail=f"The {period} {selected_mode} evidence cache is not ready yet.")
    if mode == "compare" and product.safe_filter_supported:
        safe = load_product_cache(product.slug, "safe", period)
        if safe is not None:
            payload["datasets"] = [
                {"label": "Standard", "color": "#7ef7c7", "series": payload["series"], "stats": payload["stats"], "trades": payload["trades"]},
                {"label": product.safe_mode_label, "color": "#68a7ff", "series": safe["series"], "stats": safe["stats"], "trades": safe["trades"]},
            ]
    return JSONResponse(
        payload,
        headers={"Cache-Control": "public, max-age=300", "X-Evidence-Cache": "HIT"},
    )


@app.post("/api/evidence/{slug}/refresh", name="refresh_evidence")
async def refresh_evidence(slug: str) -> JSONResponse:
    if get_product(slug) is None:
        raise HTTPException(status_code=404, detail="EA not found")
    raise HTTPException(
        status_code=410,
        detail="Custom MT5 date-range refreshes were retired. Use the fixed 6m, 1y, 3y or 5y evidence cache.",
    )


@app.get("/api/evidence/jobs/{job_id}", name="evidence_job")
async def evidence_job(job_id: str) -> JSONResponse:
    job = mt5_evidence_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Evidence job not found")
    return JSONResponse(job, headers={"Cache-Control": "no-store"})


@app.get("/api/evidence/jobs/{job_id}/trades/{trade_number}/chart", name="evidence_trade_chart")
async def evidence_trade_chart(job_id: str, trade_number: int) -> JSONResponse:
    trade = mt5_evidence_jobs.get_trade(job_id, trade_number)
    if trade is None:
        raise HTTPException(status_code=404, detail="Fresh MT5 trade not found. Run Update from MT5 first.")
    try:
        opened = datetime.fromisoformat(str(trade["open_time"])).replace(tzinfo=timezone.utc)
        closed = datetime.fromisoformat(str(trade["close_time"])).replace(tzinfo=timezone.utc)
        duration = max(closed - opened, timedelta(minutes=5))
        timeframe = "M1" if duration <= timedelta(hours=3) else "M5" if duration <= timedelta(days=1) else "M15"
        padding = max(timedelta(minutes=30), min(duration / 4, timedelta(days=1)))
        market = live_mt5.price_bars(str(trade["symbol"]), timeframe, opened - padding, closed + padding)
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return JSONResponse(
        {**market, "trade": trade},
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


@app.get("/api/evidence/{slug}/cached-trades/{period}/{trade_number}/chart", name="cached_evidence_trade_chart")
async def cached_evidence_trade_chart(
    slug: str,
    period: str,
    trade_number: int,
    mode: str = Query(default="standard", pattern=r"^(standard|safe)$"),
) -> JSONResponse:
    try:
        validate_period(period)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    trade = load_cached_trade(slug, mode, period, trade_number)
    if trade is None:
        raise HTTPException(status_code=404, detail="Cached MT5 trade not found.")
    try:
        opened = datetime.fromisoformat(str(trade["open_time"])).replace(tzinfo=timezone.utc)
        closed = datetime.fromisoformat(str(trade["close_time"])).replace(tzinfo=timezone.utc)
        duration = max(closed - opened, timedelta(minutes=5))
        timeframe = "M1" if duration <= timedelta(hours=3) else "M5" if duration <= timedelta(days=1) else "M15"
        padding = max(timedelta(minutes=30), min(duration / 4, timedelta(days=1)))
        market = live_mt5.price_bars(str(trade["symbol"]), timeframe, opened - padding, closed + padding)
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return JSONResponse({**market, "trade": trade}, headers={"Cache-Control": "no-store"})


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
    mode: str = Query(default="standard", pattern=r"^(standard)$"),
    period: str = Query(default=DEFAULT_PERIOD, pattern=r"^(6m|1y|3y|5y)$"),
) -> JSONResponse:
    payload = load_portfolio_cache(mode, period)
    if payload is None:
        raise HTTPException(status_code=503, detail=f"The recommended portfolio {period} cache is not ready yet.")
    return JSONResponse(
        payload,
        headers={"Cache-Control": "public, max-age=300", "X-Evidence-Cache": "HIT"},
    )


@app.get("/api/eas")
async def api_eas() -> JSONResponse:
    payload = [product.model_dump(mode="json") for product in _display_catalog()]
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


@app.get("/api/evidence-cache/manifest")
async def api_evidence_cache_manifest() -> JSONResponse:
    manifest = cache_manifest()
    if manifest is None:
        raise HTTPException(status_code=503, detail="Evidence cache generation has not completed.")
    return JSONResponse(manifest, headers={"Cache-Control": "public, max-age=300", "X-Evidence-Cache": "HIT"})


@app.get("/api/health")
async def api_health() -> dict[str, Any]:
    products = get_catalog()
    sellable = get_sellable_catalog()
    live_state = live_mt5.snapshot()
    manifest = cache_manifest() or {}
    return {
        "status": "ok",
        "catalogue_source": str(INSTALLER_PATH),
        "active_entries": len(products),
        "available_entries": len(sellable),
        "development_entries": len(products) - len(sellable),
        "whatsapp_checkout": True,
        "live_mt5_telemetry": bool(live_state["connected"]),
        "live_mt5_last_update": live_state["last_update"],
        "evidence_cache_generated_at": manifest.get("generated_at"),
        "evidence_cache_recommended_eas": manifest.get("recommended_ea_count"),
        "evidence_cache_failures": len(manifest.get("failures", [])),
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
