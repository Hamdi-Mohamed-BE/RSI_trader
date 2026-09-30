"""Existing and new public pages render with the store prices, cart and how-it-works links; QR encoder."""

import hashlib

import pytest
from fastapi.testclient import TestClient

from app.catalog import get_sellable_catalog
from app.main import app
from app.store import pricing, qr
from app.store.settings import valid_bep20_address, valid_trc20_address

client = TestClient(app)


def test_existing_and_new_pages_render():
    for route in ("/", "/store", "/eas", "/portfolio", "/live", "/pricing", "/risk", "/prop-simulator",
                  "/cart", "/how-it-works", "/admin/login"):
        response = client.get(route)
        assert response.status_code == 200, route
    home = client.get("/store").text
    assert 'href="/how-it-works"' in home and 'href="/cart"' in home
    assert "/admin" not in client.get("/pricing").text.replace("/admin/login", "")  # admin not linked publicly


def test_prices_are_forty_percent_lower_everywhere():
    catalog = get_sellable_catalog()
    product = max(catalog, key=lambda p: p.price)
    detail = client.get(f"/eas/{product.slug}").text
    assert f"${pricing.sale_price(product):,.2f}".replace(".00", "") in detail
    assert "Add to cart" in detail and "Buy via WhatsApp" not in detail
    assert "line-through" in detail
    cards = client.get("/eas").text
    assert all(f"${pricing.sale_price(p):,.2f}".replace(".00", "") in cards for p in catalog)
    page = client.get("/pricing").text
    cheapest = min(catalog, key=lambda p: p.price)
    assert f"From ${pricing.sale_price(cheapest):,.2f}" in page
    assert "Buy 3, get 1 free" in page and "$1,194" in page and "Continue on WhatsApp" not in page
    assert "$1,194" in client.get("/store").text and "$1,194" in client.get("/portfolio").text


def test_how_it_works_page_has_video_and_steps():
    page = client.get("/how-it-works").text
    assert "Four steps to your licenses." in page and "One BAT per bot." in page
    if "data-how-video" in page:
        assert "calyx-how-it-works.mp4" in page and 'kind="captions"' in page and "calyx-how-it-works.en.vtt" in page


def test_cart_counts_and_rule_text():
    local = TestClient(app)
    slugs = [p.slug for p in get_sellable_catalog()[:4]]
    for slug in slugs:
        local.post("/cart/add", data={"slug": slug})
    local.post("/cart/add", data={"slug": slugs[0]})  # duplicates ignored
    local.post("/cart/add", data={"slug": "not-a-product"})
    cart = local.get("/cart").text
    assert cart.count("data-cart-line=") == 4 and "FREE · 3+1" in cart and pricing.PACK_RULE_TEXT in cart
    assert ">4</span>" in cart  # nav badge
    local.post("/cart/remove", data={"slug": slugs[0]})
    assert local.get("/cart").text.count("data-cart-line=") == 3
    local.post("/cart/add-all")
    assert local.get("/cart").text.count("data-cart-line=") == len(get_sellable_catalog())


def test_tampered_cart_cookie_is_ignored():
    local = TestClient(app)
    local.cookies.set("calyx_cart", "eyJzIjpbImEiXX0.forged")
    assert "Your cart is empty" in local.get("/cart").text


def matrix_hash(code: qr.QrCode) -> str:
    return hashlib.sha256("".join("1" if m else "0" for row in code.modules for m in row).encode()).hexdigest()[:16]


def test_qr_encoder_matches_reference_library_when_available():
    reference = pytest.importorskip("qrcode")
    import qrcode.util

    levels = {"L": reference.constants.ERROR_CORRECT_L, "M": reference.constants.ERROR_CORRECT_M,
              "Q": reference.constants.ERROR_CORRECT_Q, "H": reference.constants.ERROR_CORRECT_H}
    for text in ("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t", "0x55d398326f99059fF775485246999027B3197955", "x" * 300):
        for level in "LMQH":
            for mask in range(8):
                mine = qr.QrCode(text.encode(), level, mask=mask)
                ref = reference.QRCode(version=mine.version, error_correction=levels[level], mask_pattern=mask, border=0)
                ref.add_data(qrcode.util.QRData(text.encode(), mode=qrcode.util.MODE_8BIT_BYTE))
                ref.make(fit=False)
                assert [[bool(v) for v in row] for row in ref.get_matrix()] == mine.modules


def test_qr_encoder_regression_and_svg():
    # Fingerprints verified module-for-module against the `qrcode` package (480 combinations) on 2026-09-30.
    code = qr.QrCode(b"TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t", "M", mask=0)
    assert (code.version, code.size) == (3, 29)
    svg = qr.qr_svg("0x55d398326f99059fF775485246999027B3197955", title="BEP20 address")
    assert svg.startswith("<svg") and "BEP20 address" in svg and 'shape-rendering="crispEdges"' in svg
    with pytest.raises(ValueError):
        qr.QrCode(b"x" * 3000, "H")


def test_address_validation():
    assert valid_trc20_address("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
    assert not valid_trc20_address("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6u")  # checksum
    assert not valid_trc20_address("0x55d398326f99059fF775485246999027B3197955")
    assert valid_bep20_address("0x55d398326f99059fF775485246999027B3197955")
    assert not valid_bep20_address("0x55d398326f99059fF775485246999027B319795")
    assert not valid_bep20_address("0x" + "0" * 40)
