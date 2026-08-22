from __future__ import annotations

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
from app.main import app
from app.mt5_live import reconstruct_trades


client = TestClient(app)


def test_catalogue_is_synchronized_with_active_installer() -> None:
    installer_items = parse_installer_items()
    products = get_catalog()

    assert len(installer_items) == 27
    assert len(products) == len(installer_items)
    assert [product.installer_label for product in products] == [item["label"] for item in installer_items]
    assert len({product.slug for product in products}) == len(products)
    assert all("aaa" not in product.label.lower() for product in products)
    assert len(get_sellable_catalog()) == 13
    assert len(get_development_catalog()) == 14


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
        assert "HAMA Algo Systems" in response.text


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

    compiled_only = {"ATR Candle Breakout", "Go Long", "Turnaround Tuesday"}
    assert {product.label for product in products if product.logic_audit == "Input-audited binary"} == compiled_only
    assert all(
        product.logic_audit == "Source-code verified"
        for product in products
        if product.label not in compiled_only
    )

    by_name = {product.label: product for product in products}
    assert "previous D1 open and close" in by_name["DmC"].logic[0].detail
    assert "display" in by_name["ORB Volume Profile"].logic[2].title.lower()
    assert "all three profile entry filters are OFF" in by_name["ORB Volume Profile"].logic[2].detail
    assert "ATR(14)" in by_name["Nasdaq 5M Open EMA ATR"].logic[2].detail
    assert "sell side is disabled" in by_name["News Pulse"].logic[2].detail


def test_detail_page_renders_code_based_logic_details() -> None:
    dmc = next(product for product in get_sellable_catalog() if product.label == "DmC")
    response = client.get(f"/eas/{dmc.slug}")
    assert response.status_code == 200
    assert "How the installed version actually works" in response.text
    assert "Source-code verified" in response.text
    assert "Map yesterday&#39;s real body" in response.text
    assert "22.5 XAUUSD price units" in response.text
    assert "The exact thresholds and trade-management values are supplied" not in response.text


def test_api_and_evidence_chart() -> None:
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["active_entries"] == 27
    assert health.json()["available_entries"] == 13
    assert health.json()["development_entries"] == 14

    payload = client.get("/api/eas")
    assert payload.status_code == 200
    assert len(payload.json()) == 13
    assert all(not item["development"] for item in payload.json())

    product = next(item for item in get_catalog() if item.evidence and item.evidence.chart_path)
    chart = client.get(f"/evidence/{product.slug}.png")
    assert chart.status_code == 200
    assert chart.headers["content-type"] == "image/png"
    assert chart.headers["cache-control"].startswith("no-store")


def test_portfolio_page_shows_one_year_only() -> None:
    response = client.get("/portfolio")
    assert response.status_code == 200
    assert "One-year combined core audit" in response.text
    assert "+295.61%" in response.text
    assert "$39,561.18" in response.text
    assert "PROFITABLE PERIOD" in response.text
    assert "five-year" not in response.text.lower()
    assert "2021-08-11" not in response.text
    assert "Longer-history risk context" not in response.text
    chart = client.get("/portfolio/equity.png?period=1y")
    assert chart.status_code == 200
    assert chart.headers["cache-control"].startswith("no-store")


def test_every_public_ea_uses_the_same_one_year_window() -> None:
    products = get_sellable_catalog()
    assert all(product.evidence is not None for product in products)
    assert all(product.evidence.period == "2025-08-11 to 2026-08-10" for product in products if product.evidence)
    assert all(product.one_year_evidence == product.evidence for product in products)
    for route in ("/", "/eas", "/portfolio", "/risk", *(f"/eas/{product.slug}" for product in products)):
        response = client.get(route)
        assert "five-year" not in response.text.lower()
        assert "2021-08-11" not in response.text


def test_missing_product_returns_branded_404() -> None:
    response = client.get("/eas/not-a-real-ea")
    assert response.status_code == 404
    assert "This setup is not in the active catalogue" in response.text


def test_home_ranks_all_available_eas_by_last_year_return() -> None:
    products = get_sellable_catalog()
    returns = [product.one_year_return_pct for product in products]
    assert all(value is not None for value in returns)

    ranked = sorted(products, key=lambda product: product.one_year_return_pct or float("-inf"), reverse=True)
    response = client.get("/store")
    assert response.status_code == 200
    assert response.text.count("Last-year return") == 13
    positions = [response.text.index(f">{product.label}</h3>") for product in ranked]
    assert positions == sorted(positions)
    assert "Auction Market research engine" in response.text
    assert "NOT FOR SALE" in response.text
    assert "Auction Market XAU" not in response.text


def test_development_builds_are_not_public_products() -> None:
    product = get_development_catalog()[0]
    assert product.buy_url == ""
    assert client.get(f"/eas/{product.slug}").status_code == 404


def test_live_dashboard_and_read_only_api_render() -> None:
    for route in ("/", "/live"):
        page = client.get(route)
        assert page.status_code == 200
        assert "The account, as it trades" in page.text
        assert "Every reconstructed closed trade" in page.text
    store = client.get("/store")
    assert "Ranked by last-year return" in store.text
    api = client.get("/api/live/portfolio")
    assert api.status_code == 200
    assert api.headers["cache-control"].startswith("no-store")
    assert set(api.json()) >= {"connected", "account", "positions", "orders", "trades", "ea_summary", "equity_series"}


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
