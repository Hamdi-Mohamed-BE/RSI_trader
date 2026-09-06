from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.catalog import (
    PACKAGE_ROOT,
    WHATSAPP_NUMBER,
    get_catalog,
    get_development_catalog,
    get_sellable_catalog,
    parse_installer_items,
)
from app.main import _display_catalog, app
from app.mt5_evidence_jobs import MAX_DAYS, _materialized_values, _native_trades, _same_setting, _set_values
from app.mt5_live import reconstruct_balance_history, reconstruct_trades
from app.trade_metrics import enrich_trades, pip_spec


client = TestClient(app)
STORE_ROOT = Path(__file__).resolve().parents[1]


def test_catalogue_is_synchronized_with_active_installer() -> None:
    installer_items = parse_installer_items()
    products = get_catalog()

    assert len(products) == len(installer_items)
    assert [product.installer_label for product in products] == [item["label"] for item in installer_items]
    assert len({product.slug for product in products}) == len(products)
    assert all("aaa" not in product.label.lower() for product in products)
    assert len(get_sellable_catalog()) == len(installer_items)
    assert len(get_development_catalog()) == 0


def test_every_active_entry_has_local_ea_and_set_files() -> None:
    missing: list[str] = []
    for product in get_catalog():
        for relative_path in (product.expert_source, product.set_source):
            if not relative_path or not (PACKAGE_ROOT / relative_path).is_file():
                missing.append(f"{product.label}: {relative_path or '<empty>'}")
    assert missing == []


def test_purchase_links_use_store_whatsapp_number() -> None:
    for product in get_sellable_catalog():
        parsed = urlparse(product.buy_url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "wa.me"
        assert parsed.path == f"/{WHATSAPP_NUMBER}"
        assert product.label in parse_qs(parsed.query)["text"][0]


def test_public_pages_render() -> None:
    for route in ("/", "/store", "/eas", "/portfolio", "/live", "/pricing", "/risk"):
        response = client.get(route)
        assert response.status_code == 200
        assert "Calyx" in response.text


def test_calyx_dns_installer_defaults_are_safe_and_complete() -> None:
    batch = (STORE_ROOT / "configDns.bat").read_text(encoding="utf-8")
    installer = (STORE_ROOT / "tools" / "Configure-DnsHttps.ps1").read_text(encoding="utf-8")

    assert "calyx.duckdns.org" in batch
    assert "51.91.121.15" in batch
    assert "RunAs" in batch
    assert "calyx.duckdns.org" in installer
    assert "1.1.1.1" in installer and "8.8.8.8" in installer
    assert "reverse_proxy 127.0.0.1:8080" in installer
    assert "Get-FileHash -Algorithm SHA512" in installer
    assert "FINAL LINK:" in installer
    assert "Calyx Caddy HTTPS" in installer
    assert "Calyx EA Store" in installer


def test_calyx_logo_is_used_for_branding_and_favicon() -> None:
    logo = STORE_ROOT / "static" / "images" / "calyx-logo.jpg"
    response = client.get("/eas")

    assert logo.is_file() and logo.stat().st_size > 0
    assert response.status_code == 200
    assert 'rel="icon" type="image/jpeg"' in response.text
    assert response.text.count("images/calyx-logo.jpg") >= 5
    assert "Calyx trading systems logo" in response.text


def test_live_installer_uses_simple_account_confirmation() -> None:
    installer_path = PACKAGE_ROOT / "_Auto Deploy" / "Install-BMTradingPortfolio.ps1"
    installer = installer_path.read_text(encoding="utf-8")

    assert '$expected = "RUN $login"' in installer
    assert "$confirmation = $confirmation.Trim()" in installer
    assert "$confirmation -ine $expected" in installer
    assert "MODE: STANDARD - current default/selective configuration." in installer
    assert "â€”" not in installer


def test_every_product_detail_page_renders() -> None:
    for product in get_sellable_catalog():
        response = client.get(f"/eas/{product.slug}")
        assert response.status_code == 200
        assert product.label in response.text
        assert product.buy_url.replace("&", "&amp;") in response.text


def test_sellable_logic_is_specific_and_audit_labeled() -> None:
    products = get_sellable_catalog()
    assert all(len(product.logic) == 6 for product in products)
    assert all(step.title and len(step.detail) >= 80 for product in products for step in product.logic)

    compiled_only: set[str] = set()
    assert {product.label for product in products if product.logic_audit == "Input-audited binary"} == compiled_only
    assert all(
        product.logic_audit == "Source-code verified"
        for product in products
        if product.label not in compiled_only
    )

    by_name = {product.label: product for product in products}
    assert "DmC" not in by_name
    assert "display" in by_name["ORB Volume Profile"].logic[2].title.lower()
    assert "all three profile entry filters are OFF" in by_name["ORB Volume Profile"].logic[2].detail
    assert "four times" in by_name["Nasdaq 5M Candle Momentum"].logic[2].detail
    assert "+1R" in by_name["Nasdaq 5M Candle Momentum"].logic[3].detail
    assert "15:55" in by_name["Nasdaq 5M Candle Momentum"].logic[5].detail
    assert "buy stop" in by_name["News Pulse XAU"].logic[2].detail
    assert "sell stop" in by_name["News Pulse XAU"].logic[2].detail
    assert "exactly 0.75%" in by_name["News Pulse XAU"].logic[3].detail
    assert "preceding twelve M15 bars" in by_name["BTC Top Down FVG Liquidity"].logic[1].detail
    assert "target is 4R" in by_name["ETH Top Down FVG Liquidity"].logic[5].detail
    assert "between 2R and 8R" in by_name["Engineered Liquidity XAU"].logic[4].detail


def test_recommended_exit_settings_are_synced_per_ea() -> None:
    products = get_sellable_catalog()
    assert len(products) == 24
    assert sum(product.exit_mode == "Dynamic 50/20" for product in products) == 8
    assert sum(product.exit_mode == "Dynamic 60/20 only" for product in products) == 1
    assert sum(product.exit_mode == "Current EA exits" for product in products) == 5
    assert sum(product.exit_mode == "Native 60-second exit" for product in products) == 3
    assert sum(product.exit_mode == "Fixed 5R / no trailing" for product in products) == 1
    assert sum(product.exit_mode == "Native 1.5R / BE at 0.5R" for product in products) == 1
    assert sum(product.exit_mode == "Native 1R / BE at 0.5R" for product in products) == 1
    assert sum(product.exit_mode == "Fixed 4R / no trailing" for product in products) == 1
    assert sum(product.exit_mode == "Nominal 6R / timed flat" for product in products) == 1
    assert sum(product.exit_mode == "Fixed 2R / BE at 1R" for product in products) == 1
    assert sum(product.exit_mode == "Fixed 3R / no trailing" for product in products) == 1
    standalone_orbs = {
        "XAU ORB New York M30",
        "XAU ORB London NY Overlap M30",
        "US100 ORB New York M30",
        "US100 H1 ORB 13UTC",
        "US100 Selective ORB V3",
    }
    assert all(
        product.deployment_session == "All day / native strategy window"
        for product in products
        if product.label != "BTC POC Fibonacci" and product.label not in standalone_orbs
    )
    ema3 = next(product for product in products if product.label == "EMA3")
    assert ema3.exit_mode == "Dynamic 60/20 only"
    assert "Native R-trailing is disabled" in ema3.logic[-1].detail
    weakness = next(product for product in products if product.label == "XAU Weakness")
    assert weakness.timeframe == "M30"
    assert weakness.exit_mode == "Dynamic 50/20"
    assert weakness.evidence is not None
    assert weakness.evidence.return_pct == 235.67
    assert weakness.evidence.profit_factor == 1.58
    assert weakness.evidence.win_rate_pct == 38.97
    overnight = next(product for product in products if product.label == "Nasdaq Overnight")
    assert not overnight.safe_filter_supported
    assert overnight.evidence is not None
    assert overnight.evidence.return_pct == 8.6671
    assert overnight.evidence.win_rate_pct == 63.89
    assert weakness.evidence.drawdown_pct == 13.25
    assert weakness.evidence.trades == 390
    assert weakness.safe_evidence is not None
    assert weakness.safe_evidence.return_pct == 134.07
    assert weakness.safe_evidence.profit_factor == 1.95
    poc_fib = next(product for product in products if product.label == "BTC POC Fibonacci")
    assert poc_fib.deployment_session == "New York broker-session window"
    assert poc_fib.safe_filter_supported is False
    assert poc_fib.evidence is not None
    assert poc_fib.evidence.status == "Demo watch"
    assert all("Applied BAT overlay" in product.logic[-1].detail for product in products if product.exit_mode == "Dynamic 50/20")
    assert all("Dynamic 50/20 overlay is disabled" in product.logic[-1].detail for product in products if product.exit_mode == "Current EA exits")
    assert all("Dynamic 50/20 overlay is disabled" in product.logic[-1].detail for product in products if product.exit_mode == "Native 60-second exit")
    news_products = [product for product in products if product.label.startswith("News Pulse ")]
    assert {product.label for product in news_products} == {"News Pulse XAU", "News Pulse XAG", "News Pulse EURUSD"}
    assert all(product.safe_filter_supported is False for product in news_products)
    assert all(product.evidence is not None for product in news_products)

    xau_ny = next(product for product in products if product.label == "XAU ORB New York M30")
    assert xau_ny.deployment_session == "09:30 New York / M30"
    assert xau_ny.exit_mode == "Native 1.5R / BE at 0.5R"
    assert xau_ny.safe_filter_supported is False
    assert xau_ny.evidence is not None
    assert round(xau_ny.evidence.return_pct, 4) == 2.4405
    assert xau_ny.evidence.profit_factor == 3.04
    assert xau_ny.evidence.trades == 11

    xau_overlap = next(product for product in products if product.label == "XAU ORB London NY Overlap M30")
    assert xau_overlap.deployment_session == "13:00-16:00 UTC overlap / M30"
    assert xau_overlap.exit_mode == "Native 1R / BE at 0.5R"
    assert xau_overlap.safe_filter_supported is False
    assert xau_overlap.evidence is not None
    assert round(xau_overlap.evidence.return_pct, 4) == 5.2103
    assert xau_overlap.evidence.profit_factor == 2.16
    assert xau_overlap.evidence.trades == 24

    us100_ny = next(product for product in products if product.label == "US100 ORB New York M30")
    assert us100_ny.deployment_session == "09:30 New York / M30"
    assert us100_ny.exit_mode == "Fixed 4R / no trailing"
    assert us100_ny.safe_filter_supported is False
    assert us100_ny.evidence is not None
    assert round(us100_ny.evidence.return_pct, 4) == 9.6588
    assert us100_ny.evidence.profit_factor == 1.68
    assert us100_ny.evidence.trades == 27

    us100_h1 = next(product for product in products if product.label == "US100 H1 ORB 13UTC")
    assert us100_h1.deployment_session == "13:00-20:00 UTC / M15"
    assert us100_h1.exit_mode == "Nominal 6R / timed flat"
    assert us100_h1.safe_filter_supported is False
    assert us100_h1.evidence is not None
    assert round(us100_h1.evidence.return_pct, 4) == 22.9981
    assert us100_h1.evidence.profit_factor == 1.72
    assert us100_h1.evidence.trades == 71

    selective_v3 = next(product for product in products if product.label == "US100 Selective ORB V3")
    assert selective_v3.deployment_session == "09:30-15:55 New York / M5"
    assert selective_v3.exit_mode == "Fixed 2R / BE at 1R"
    assert selective_v3.safe_filter_supported is False
    assert selective_v3.evidence is not None
    assert round(selective_v3.evidence.return_pct, 4) == 1.5376
    assert selective_v3.evidence.profit_factor == 1.53
    assert selective_v3.evidence.trades == 5
    recommended_bat = PACKAGE_ROOT / "BEST RECOMMENDED 2026-09-01.bat"
    assert recommended_bat.is_file()
    bat_text = recommended_bat.read_text(encoding="utf-8")
    assert "-SafetyMode STANDARD" in bat_text
    assert "-UseRecommendedSelections" in bat_text

    btc_fvg = next(product for product in products if product.label == "BTC Top Down FVG Liquidity")
    assert btc_fvg.deployment_session == "All day / native strategy window"
    assert btc_fvg.safe_set_source is None
    assert btc_fvg.safe_mode_label == "Full Safe"
    assert btc_fvg.safe_evidence is not None

    rsi_vwap = next(product for product in products if product.label == "XAU RSI VWAP")
    assert rsi_vwap.timeframe == "H1"
    assert rsi_vwap.exit_mode == "Current EA exits"
    assert rsi_vwap.safe_filter_supported is False
    assert "0.5 times initial risk" in rsi_vwap.logic[-1].detail

    trend = next(product for product in products if product.label == "XAU Trend Progression")
    assert trend.timeframe == "H4"
    assert trend.exit_mode == "Current EA exits"
    assert trend.safe_filter_supported is False
    assert trend.evidence is not None
    assert trend.evidence.return_pct == 16.1025
    assert trend.evidence.profit_factor == 2.74
    assert trend.evidence.trades == 25
    assert "default and validated value is 1%" in trend.logic[4].detail

    elliott = next(product for product in products if product.label == "XAU Elliott Wave 1-2-3")
    assert elliott.timeframe == "H4"
    assert elliott.exit_mode == "Fixed 3R / no trailing"
    assert elliott.safe_filter_supported is False
    assert elliott.evidence is not None
    assert elliott.evidence.return_pct == 23.8231
    assert elliott.evidence.profit_factor == 3.15
    assert elliott.evidence.win_rate_pct == 54.17
    assert elliott.evidence.drawdown_pct == 3.77
    assert elliott.evidence.trades == 24
    assert "default and validated value is 1%" in elliott.logic[4].detail

    overnight = next(product for product in products if product.label == "Nasdaq Overnight")
    assert overnight.exit_mode == "Current EA exits"
    assert overnight.evidence is not None
    assert overnight.evidence.return_pct == 8.6671
    assert overnight.evidence.profit_factor == 1.84
    assert overnight.evidence.win_rate_pct == 63.89
    assert overnight.evidence.drawdown_pct == 2.36
    assert overnight.evidence.trades == 72
    assert "16:00-to-09:29" in overnight.evidence.source_note


def test_nasdaq_overnight_uses_fresh_native_curve_and_active_inputs() -> None:
    product = next(product for product in get_sellable_catalog() if product.label == "Nasdaq Overnight")
    response = client.get(f"/api/evidence/{product.slug}/series")
    assert response.status_code == 200
    payload = response.json()
    assert payload["period_key"] == "3y"
    assert payload["available_from"] == "2023-09-05"
    assert payload["available_to"] == "2026-09-05"
    assert payload["source"] == "precomputed-native-mt5-cache"
    assert payload["stats"]["trades"] == payload["cached_trade_count"]

    active_set = (PACKAGE_ROOT / product.set_source).read_text(encoding="utf-8-sig")
    for setting in (
        "InpRequireNegativeDay=true",
        "InpEntryHour=16",
        "InpEntryMinute=0",
        "InpExitHour=9",
        "InpExitMinute=29",
        "InpEmergencyStopPercent=2",
        "InpRewardRisk=0",
        "InpUseDynamicTrailingSL=false",
    ):
        assert setting in active_set


def test_removed_dmc_detail_is_not_available() -> None:
    response = client.get("/eas/dmc-xau")
    assert response.status_code == 404


def test_api_and_evidence_chart() -> None:
    health = client.get("/api/health")
    assert health.status_code == 200
    expected = len(get_catalog())
    assert health.json()["active_entries"] == expected
    assert health.json()["available_entries"] == expected
    assert health.json()["development_entries"] == 0

    payload = client.get("/api/eas")
    assert payload.status_code == 200
    assert len(payload.json()) == expected
    assert all(not item["development"] for item in payload.json())

    product = next(item for item in get_catalog() if item.evidence and item.evidence.chart_path)
    chart = client.get(f"/evidence/{product.slug}.png")
    assert chart.status_code == 200
    assert chart.headers["content-type"] == "image/png"
    assert chart.headers["cache-control"].startswith("no-store")

    for item in get_sellable_catalog():
        series = client.get(f"/api/evidence/{item.slug}/series")
        assert series.status_code == 200, item.label
        payload = series.json()
        assert payload["label"] == item.label
        assert len(payload["series"]) >= 2
        assert all(set(point) >= {"time", "balance"} for point in payload["series"])
        assert series.headers["cache-control"].startswith("public")
        assert series.headers["x-evidence-cache"] == "HIT"

    detail = client.get(f"/eas/{product.slug}")
    assert f'/api/evidence/{product.slug}/series' in detail.text
    assert f'/evidence/{product.slug}.png' not in detail.text
    assert "/static/evidence.js" in detail.text


def test_portfolio_page_shows_fixed_cached_periods() -> None:
    response = client.get("/portfolio")
    assert response.status_code == 200
    assert "Precomputed recommended-portfolio evidence" in response.text
    assert "24 EAs, synchronized" in response.text
    assert "CACHED NATIVE MT5 DATA" in response.text
    assert "Dynamic 50/20" in response.text
    for value in ("6m", "1y", "3y", "5y"):
        assert f'value="{value}"' in response.text
    assert 'value="10y"' not in response.text
    assert 'data-chart-from' not in response.text
    assert 'data-chart-to' not in response.text
    chart = client.get("/portfolio/equity.png?period=1y")
    assert chart.status_code == 404
    series = client.get("/api/portfolio/equity-series")
    assert series.status_code == 200
    assert len(series.json()["series"]) >= 2
    assert series.json()["included_ea_count"] == 24
    assert series.headers["x-evidence-cache"] == "HIT"
    assert "/api/portfolio/equity-series" in response.text
    assert "/portfolio/equity.png" not in response.text
    assert "/static/evidence.js" in response.text


def test_every_public_ea_uses_supported_evidence_period() -> None:
    products = get_sellable_catalog()
    assert all(product.evidence is not None for product in products)
    for product in products:
        start_text, end_text = product.evidence.period.split(" to ")
        duration = (date.fromisoformat(end_text) - date.fromisoformat(start_text)).days
        assert 364 <= duration <= 3660
    assert all(product.one_year_evidence == product.evidence for product in products)
    for route in ("/", "/eas", "/portfolio", "/risk", *(f"/eas/{product.slug}" for product in products)):
        response = client.get(route)
        assert "five-year" not in response.text.lower()
        assert "2021-08-11" not in response.text


def test_missing_product_returns_branded_404() -> None:
    response = client.get("/eas/not-a-real-ea")
    assert response.status_code == 404
    assert "This setup is not in the active catalogue" in response.text


def test_home_ranks_all_available_eas_by_default_three_year_return() -> None:
    products = _display_catalog()
    returns = [product.one_year_return_pct for product in products]
    assert all(value is not None for value in returns)

    ranked = sorted(products, key=lambda product: product.one_year_return_pct or float("-inf"), reverse=True)
    response = client.get("/store")
    assert response.status_code == 200
    assert response.text.count("Three-year return") == len(products)
    positions = [response.text.index(f">{product.label}</h3>") for product in ranked]
    assert positions == sorted(positions)
    assert "Auction Market research engine" not in response.text
    assert "NOT FOR SALE" not in response.text
    assert "Auction Market XAU" not in response.text


def test_ea_catalogue_supports_metric_sorting_and_symbol_filtering() -> None:
    page = client.get("/eas")
    assert page.status_code == 200
    assert 'id="sort-filter"' in page.text
    assert "Highest profit factor" in page.text
    assert "Highest win rate" in page.text
    assert "Lowest drawdown" in page.text
    assert "Highest return" in page.text
    assert 'id="asset-filter"' in page.text
    assert "XAUUSD (14)" in page.text
    assert 'data-pf=' in page.text
    assert 'data-win=' in page.text
    assert 'data-dd=' in page.text

    xag = client.get("/eas", params={"symbol": "xagusd"})
    assert xag.status_code == 200
    assert "News Pulse XAG" in xag.text
    assert 'id="visible-count" class="text-white">1<' in xag.text

    pf_sorted = client.get("/eas", params={"sort": "pf-desc"})
    products = sorted(
        _display_catalog(),
        key=lambda product: product.evidence.profit_factor if product.evidence else float("-inf"),
        reverse=True,
    )
    positions = [pf_sorted.text.index(f">{product.label}</h3>") for product in products]
    assert positions == sorted(positions)


def test_development_builds_are_not_public_products() -> None:
    assert get_development_catalog() == []


def test_live_dashboard_and_read_only_api_render() -> None:
    for route in ("/", "/live"):
        page = client.get(route)
        assert page.status_code == 200
        assert "The account, as it trades" in page.text
        assert "Every reconstructed closed trade" in page.text
    store = client.get("/store")
    assert "Ranked by three-year return" in store.text
    api = client.get("/api/live/portfolio")
    assert api.status_code == 200
    assert api.headers["cache-control"].startswith("no-store")
    assert set(api.json()) >= {"connected", "account", "positions", "orders", "trades", "ea_summary", "equity_series"}
    assert "Balance history since first reaching $10,000" in client.get("/").text
    live_script = client.get("/static/live.js")
    assert live_script.status_code == 200
    assert "2026-08-01T00:00:00Z" in live_script.text
    assert "curveSinceFirstTenK" in live_script.text


def test_fixed_cached_evidence_periods_and_pricing_bundle() -> None:
    product = next(item for item in get_sellable_catalog() if item.evidence and item.evidence.trades > 20)
    response = client.get(
        f"/api/evidence/{product.slug}/series",
        params={"period": "6m"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["period_key"] == "6m"
    assert set(payload["stats"]) >= {"return_pct", "profit_factor", "win_rate_pct", "max_drawdown_pct", "trades", "sharpe_ratio", "recovery_factor"}
    assert all("source" in trade for trade in payload["trades"])

    portfolio = client.get(
        "/api/portfolio/equity-series",
        params={"mode": "standard", "period": "6m"},
    )
    assert portfolio.status_code == 200
    assert portfolio.json()["included_ea_count"] == len(get_sellable_catalog())
    assert set(portfolio.json()["analytics"]) >= {"trade_stats", "drawdown_series", "assets", "monthly_pnl", "directions"}

    detail = client.get(f"/eas/{product.slug}")
    assert 'data-chart-period' in detail.text
    assert 'data-backtest-trades-body' in detail.text
    assert 'Show cached period' in detail.text
    assert 'data-trade-chart-panel' in detail.text
    assert 'Price chart' in detail.text
    assert 'changing periods does not launch a tester job' in detail.text
    assert all(label in detail.text for label in ("Last 6 months", "Last 1 year", "Last 3 years", "Last 5 years"))
    assert 'value="3y" selected' in detail.text
    portfolio_page = client.get("/portfolio")
    assert all(label in portfolio_page.text for label in ("Last 6 months", "Last 1 year", "Last 3 years", "Last 5 years"))
    assert 'value="3y" selected' in portfolio_page.text
    assert MAX_DAYS == 366 * 5
    pricing = client.get("/pricing")
    assert "Choose 3 + bonus EA" in pricing.text
    assert "$499" in pricing.text


def test_cached_trades_include_price_move_and_estimated_r_without_mt5_rerun() -> None:
    rows = enrich_trades(
        [
            {
                "symbol": "XAUUSD",
                "side": "Long",
                "open_time": "2026-01-01T10:00:00",
                "close_time": "2026-01-01T11:00:00",
                "open_price": 2000.0,
                "close_price": 2001.0,
                "net_profit": 100.0,
            }
        ],
        "xau-test",
    )
    assert pip_spec("XAUUSD") == (0.1, "pips")
    assert pip_spec("BTCUSD") == (1.0, "points")
    assert rows[0]["price_move"] == 10.0
    assert rows[0]["estimated_r"] == 1.0
    assert rows[0]["r_is_estimate"] is True

    product = next(item for item in get_sellable_catalog() if item.label == "LTA Volume Profile")
    payload = client.get(f"/api/evidence/{product.slug}/series", params={"period": "3y"}).json()
    assert payload["trades"]
    assert all(set(trade) >= {"price_move", "price_move_unit", "estimated_r", "configured_risk_pct"} for trade in payload["trades"])

    evidence_js = (Path(__file__).resolve().parents[1] / "static" / "evidence.js").read_text(encoding="utf-8")
    assert "addEquityHover" in evidence_js
    assert "Hover or tap the equity curve" in evidence_js


def test_all_recommended_eas_and_portfolio_have_every_fixed_cache() -> None:
    products = get_sellable_catalog()
    assert len(products) == 24
    periods = ("6m", "1y", "3y", "5y")
    for period in periods:
        portfolio = client.get("/api/portfolio/equity-series", params={"period": period})
        assert portfolio.status_code == 200, period
        assert portfolio.json()["included_ea_count"] == len(products)
        assert portfolio.json()["stats"]["trades"] == portfolio.json()["cached_trade_count"]
    for product in products:
        for period in periods:
            response = client.get(f"/api/evidence/{product.slug}/series", params={"period": period})
            assert response.status_code == 200, f"{product.label} {period}"
            payload = response.json()
            assert payload["period_key"] == period
            assert payload["stats"]["trades"] == payload["cached_trade_count"]

    manifest = client.get("/api/evidence-cache/manifest")
    assert manifest.status_code == 200
    assert manifest.json()["recommended_ea_count"] == len(products)
    assert manifest.json()["failures"] == []


def test_balance_history_is_reconstructed_from_august_cash_flows() -> None:
    start = datetime(2026, 8, 1, tzinfo=timezone.utc)
    end = datetime(2026, 8, 5, tzinfo=timezone.utc)
    deals = [
        SimpleNamespace(time_msc=datetime(2026, 8, 2, tzinfo=timezone.utc).timestamp() * 1000, profit=100, commission=-2, swap=0, fee=0),
        SimpleNamespace(time_msc=datetime(2026, 8, 3, tzinfo=timezone.utc).timestamp() * 1000, profit=-50, commission=-1, swap=0, fee=0),
    ]
    series = reconstruct_balance_history(deals, 1047, start, end)
    assert series[0]["balance"] == 1000
    assert series[-1]["balance"] == 1047
    assert all(point["equity"] is None for point in series)


def test_mt5_deals_are_reconstructed_and_attributed() -> None:
    entry = SimpleNamespace(
        ticket=1, position_id=77, time_msc=1_000_000, time=1000, type=0, entry=0,
        magic=123, volume=0.2, price=100.0, profit=0.0, commission=-1.0,
        swap=0.0, fee=0.0, symbol="XAUUSD", comment="entry signal",
    )
    exit_deal = SimpleNamespace(
        ticket=2, position_id=77, time_msc=1_060_000, time=1060, type=1, entry=1,
        magic=123, volume=0.2, price=110.0, profit=200.0, commission=-1.0,
        swap=-0.5, fee=0.0, symbol="XAUUSD", comment="[tp]",
    )
    trades = reconstruct_trades([entry, exit_deal], {123: "Test EA"})
    assert len(trades) == 1
    assert trades[0]["ea"] == "Test EA"
    assert trades[0]["side"] == "Buy"
    assert trades[0]["net_profit"] == 197.5
    assert trades[0]["duration_seconds"] == 60


def test_custom_mt5_refresh_api_is_retired() -> None:
    product = next(item for item in get_sellable_catalog() if item.evidence)
    started = client.post(
        f"/api/evidence/{product.slug}/refresh",
    )
    assert started.status_code == 410
    assert "fixed 6m, 1y, 3y or 5y" in started.json()["detail"]


def test_native_deal_parser_includes_chart_coordinates() -> None:
    report = (
        PACKAGE_ROOT / "RSI VWAP Research 2026-09-02" / "Backtest Reports"
        / "Locked Last Year Every Tick 2025-2026" / "btcusd--h4--optimized--locked.htm"
    )
    if not report.is_file():
        return
    trades = _native_trades(report, "BTC Test")
    assert trades
    assert set(trades[0]) >= {"symbol", "side", "open_time", "close_time", "open_price", "close_price"}
    assert round(sum(row["net_profit"] for row in trades), 2) == -654.60


def test_mt5_set_materialization_preserves_selected_lta_inputs_and_windows_newlines() -> None:
    source = (
        PACKAGE_ROOT / "Selected Portfolio Settings 2026-09-01"
        / "01 LTA Volume Profile - CURRENT - ALL DAY.set"
    )
    materialized = _set_values(source, safe=False)
    values = _materialized_values(materialized)

    assert "\r" not in materialized
    assert materialized.endswith("\n")
    assert values["InpUseSwingProfile"] == "false"
    assert values["InpUsePOCFirstRetestConfirmation"] == "false"
    assert values["InpUseEM2InternalSwing"] == "false"
    assert values["InpUseEM3CME"] == "false"
    assert values["InpUseDynamicTrailingSL"] == "false"


def test_btc_defaults_all_day_and_safe_is_a_per_ea_markov_input() -> None:
    product = next(item for item in get_sellable_catalog() if item.label == "BTC Top Down FVG Liquidity")
    source = PACKAGE_ROOT / product.set_source
    materialized = _set_values(source, safe=True)
    values = _materialized_values(materialized)

    assert values["InpResearchSession"] == "0"
    assert values["InpRewardRisk"] == "2"
    assert values["InpBreakEvenAtR"] == "0"
    assert values["InpUseDynamicTrailingSL"] == "false"
    assert values["InpRiskPercent"] == "1.00"
    assert values["InpUseMarkovRegimeFilter"] == "true"

    response = client.get(f"/api/evidence/{product.slug}/series", params={"mode": "compare", "period": "1y"})
    assert response.status_code == 200
    datasets = response.json()["datasets"]
    assert datasets[1]["label"] == "Full Safe"


def test_eth_approved_four_r_dynamic_configuration_is_shared_by_standard_and_safe() -> None:
    product = next(item for item in get_sellable_catalog() if item.label == "ETH Top Down FVG Liquidity")
    source = PACKAGE_ROOT / product.set_source
    standard = _materialized_values(_set_values(source, safe=False))
    safe = _materialized_values(_set_values(source, safe=True))

    assert standard["InpRewardRisk"] == "4"
    assert standard["InpUseDynamicTrailingSL"] == "true"
    assert standard["InpDynamicTriggerFraction"] == "0.50"
    assert standard["InpDynamicLockFraction"] == "0.20"
    assert standard["InpResearchSession"] == "0"
    assert standard["InpRiskPercent"] == "1.00"
    assert safe["InpRewardRisk"] == "4"
    assert safe["InpUseDynamicTrailingSL"] == "true"
    assert safe["InpUseMarkovRegimeFilter"] == "true"


def test_mt5_setting_comparison_handles_numeric_formatting_but_not_changed_inputs() -> None:
    assert _same_setting("0.50", "0.5")
    assert _same_setting("false", "FALSE")
    assert not _same_setting("false", "true")
    assert not _same_setting("0.50", "0.65")
