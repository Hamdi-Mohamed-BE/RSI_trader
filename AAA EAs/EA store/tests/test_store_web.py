"""Web flows: cart → checkout → order page, admin auth + CSRF, signed downloads, ZIP contents."""

import io
import json
import re
import time
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.prop_sim.ratelimit import SlidingWindowLimiter
from app.store import admin_auth, builds, db, downloads, licenses, orders, routes_public, security, settings
from app.store.deliverables import sellable_products
from store_helpers import TEST_TRON, configure, fresh_db

ADMIN_USER = "owner-test"
ADMIN_PASSWORD = "test-only-password-1234"  # test credential, never used outside this suite


def csrf_of(html: str) -> str:
    match = re.search(r'name="csrf" value="([^"]+)"', html)
    assert match, "no csrf field"
    return match.group(1)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    fresh_db(tmp_path, monkeypatch)
    monkeypatch.setattr(routes_public, "checkout_limiter", SlidingWindowLimiter(100, 60))
    monkeypatch.setattr(routes_public, "license_limiter", SlidingWindowLimiter(1000, 60))
    return TestClient(app, base_url="http://127.0.0.1:8082")


@pytest.fixture()
def fake_builds(tmp_path, monkeypatch):
    """A tiny store-build folder: a dummy EX5 for the first two catalogue products."""
    root = tmp_path / "builds"
    root.mkdir()
    products = sellable_products()[:2]
    (root / "Calyx Test EA.ex5").write_bytes(b"EX5-DUMMY-BINARY")
    manifest = {"builds": {"calyx-test-ea-1234abcd": {"build_id": "calyx-test-ea-1234abcd", "ex5": "Calyx Test EA.ex5",
                                                       "compiled": True, "products": [p.slug for p in products]}},
                "products": {p.slug: {"build_id": "calyx-test-ea-1234abcd", "label": p.label, "symbol": p.canonical,
                                      "period_minutes": p.period_minutes, "magic": 4242 + i,
                                      "inputs": {"InpMagic": str(4242 + i), "InpRiskPercent": "1"}}
                             for i, p in enumerate(products)}}
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setenv("CALYX_STORE_BUILDS", str(root))
    return products


def checkout(client, slugs, **form):
    for slug in slugs:
        assert client.post("/cart/add", data={"slug": slug}, follow_redirects=False).status_code == 303
    page = client.get("/checkout")
    assert page.status_code == 200
    data = {"csrf": csrf_of(page.text), "email": "buyer@example.com", "network": "TRC20", "accept": "yes"} | form
    return client.post("/checkout", data=data, follow_redirects=False)


def test_checkout_shows_not_configured_until_owner_sets_an_address(client):
    slug = sellable_products()[0].slug
    client.post("/cart/add", data={"slug": slug})
    page = client.get("/checkout")
    assert "Payments are not configured yet" in page.text and "data-checkout-form" not in page.text


def test_full_checkout_to_paid_order_and_download(client, fake_builds):
    with db.connect() as conn:
        configure(conn, bep20_address="")
    catalog = sellable_products()
    slugs = [p.slug for p in catalog[:4]]
    response = checkout(client, slugs, live_login="5550001")
    assert response.status_code == 303 and response.headers["location"].startswith("/order/")
    order_url = response.headers["location"]
    token = order_url.rsplit("/", 1)[1]
    assert "calyx_cart" not in client.cookies or not client.get("/cart").text.count("data-cart-line")
    page = client.get(order_url)
    assert page.status_code == 200
    assert TEST_TRON in page.text and "<svg" in page.text and "Wrong network or wrong token = lost funds" in page.text
    assert "FREE · 3+1" in page.text and "Buy 3, get 1 free" in page.text
    with db.connect() as conn:
        order = orders.get_by_token(conn, token)
    assert re.search(re.escape(orders.format_amount(order["amount_cents"])), page.text)
    status = client.get(f"{order_url}/status").json()
    assert status["status"] == "pending" and status["required"] == 20 and not status["detected"]
    with db.connect() as conn:
        orders.mark_paid(conn, order["id"], paid_by="admin:test", note="test payment", tx_hash="tx-test")
    paid = client.get(order_url)
    assert "Payment confirmed" in paid.text and paid.text.count('data-license="') == 4
    links = re.findall(r'href="(/download/[^"]+)"', paid.text)
    assert len(links) == 2  # only the two products that have a (fake) store build
    zipped = client.get(links[0])
    assert zipped.status_code == 200 and zipped.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(zipped.content)).namelist()
    assert any(name.endswith(".ex5") for name in names) and any(name.endswith(".bat") for name in names)
    assert "Download for this bot is being prepared" in paid.text or "being prepared" in paid.text


def test_buyer_updates_accounts_with_csrf(client, fake_builds):
    with db.connect() as conn:
        configure(conn)
    response = checkout(client, [fake_builds[0].slug])
    order_url = response.headers["location"]
    token = order_url.rsplit("/", 1)[1]
    with db.connect() as conn:
        order = orders.get_by_token(conn, token)
        orders.mark_paid(conn, order["id"], paid_by="admin:test", note="test payment")
        lic = licenses.for_order(conn, order["id"])[0]
    page = client.get(order_url)
    bad = client.post(f"{order_url}/accounts", data={"license_id": lic["id"], "live_login": "1234567"})
    assert bad.status_code == 400
    ok = client.post(f"{order_url}/accounts", data={"csrf": csrf_of(page.text), "license_id": lic["id"],
                                                      "live_login": "1234567", "demo_login": "7654321"},
                     follow_redirects=False)
    assert ok.status_code == 303
    with db.connect() as conn:
        lic = licenses.get(conn, lic["id"])
    assert (lic["live_login"], lic["demo_login"]) == ("1234567", "7654321")


def test_checkout_requires_csrf_and_terms(client):
    with db.connect() as conn:
        configure(conn)
    client.post("/cart/add", data={"slug": sellable_products()[0].slug})
    page = client.get("/checkout")
    assert client.post("/checkout", data={"email": "a@b.co", "network": "TRC20", "accept": "yes"}).status_code == 400
    no_terms = client.post("/checkout", data={"csrf": csrf_of(page.text), "email": "a@b.co", "network": "TRC20"})
    assert no_terms.status_code == 422 and "confirm the license terms" in no_terms.text
    cross_site = client.post("/cart/add", data={"slug": "x"}, headers={"origin": "https://evil.example"})
    assert cross_site.status_code == 403


def test_signed_download_links_expire_and_resist_tampering():
    token = downloads.make_token(7, 3, ttl=60, now=1_000_000)
    assert downloads.read_token(token, now=1_000_030) == {"l": 7, "o": 3, "exp": 1_000_060}
    assert downloads.read_token(token, now=1_000_061) is None
    body, mac = token.split(".")
    forged = security._b64e(json.dumps({"l": 8, "o": 3, "exp": 9_999_999_999}).encode()) + "." + mac
    assert downloads.read_token(forged) is None
    assert downloads.read_token("garbage") is None


def test_download_refuses_revoked_and_unpaid(client, fake_builds):
    with db.connect() as conn:
        configure(conn)
    response = checkout(client, [fake_builds[0].slug])
    token = response.headers["location"].rsplit("/", 1)[1]
    with db.connect() as conn:
        order = orders.get_by_token(conn, token)
        orders.mark_paid(conn, order["id"], paid_by="admin:test", note="test payment")
        lic = licenses.for_order(conn, order["id"])[0]
        link = f"/download/{downloads.make_token(lic['id'], order['id'])}"
        assert client.get(link).status_code == 200
        licenses.revoke(conn, lic["id"], "admin:test", "test")
        assert client.get(link).status_code == 403
        wrong_order = f"/download/{downloads.make_token(lic['id'], order['id'] + 1)}"
        assert client.get(wrong_order).status_code == 404
    expired = f"/download/{downloads.make_token(lic['id'], order['id'], ttl=-5)}"
    assert client.get(expired).status_code == 410


def test_zip_contains_everything_with_the_key_prefilled(tmp_path, monkeypatch, fake_builds):
    fresh_db(tmp_path, monkeypatch)
    with db.connect() as conn:
        configure(conn)
        from store_helpers import make_order
        product = fake_builds[0]
        created = make_order(conn, [product])
        orders.mark_paid(conn, created.order_id, paid_by="admin:test", note="test payment")
        order = orders.get(conn, created.order_id)
        lic = licenses.for_order(conn, created.order_id)[0]
    filename, data = downloads.build_zip(lic, order, origin="https://calyx.duckdns.org", timeframe="M5")
    archive = zipfile.ZipFile(io.BytesIO(data))
    names = {Path(name).name for name in archive.namelist()}
    bot = downloads.safe_name(product.label)
    assert filename == f"Calyx {bot}.zip"
    assert names == {"Calyx Test EA.ex5", f"{bot} - Calyx.set", f"INSTALL {bot}.bat", "Install-CalyxBot.ps1",
                     "README.txt", "LICENSE.txt"}
    folder = f"Calyx {bot}/"
    set_text = archive.read(folder + f"{bot} - Calyx.set").decode("utf-16")
    assert set_text.startswith(f"InpCalyxLicenseKey={lic['license_key']}\r\nInpCalyxProduct={product.slug}\r\n")
    assert "InpMagic=4242" in set_text
    bat = archive.read(folder + f"INSTALL {bot}.bat").decode("ascii")
    assert "Install-CalyxBot.ps1" in bat and "-ExecutionPolicy Bypass" in bat and "https://calyx.duckdns.org" in bat
    assert f'-DefaultSymbol "{product.canonical}"' in bat
    license_txt = archive.read(folder + "LICENSE.txt").decode("utf-8-sig")
    assert lic["license_key"] in license_txt and "one live and one demo" in license_txt
    assert "72 hours" in archive.read(folder + "README.txt").decode("utf-8-sig")
    assert archive.read(folder + "Calyx Test EA.ex5") == b"EX5-DUMMY-BINARY"


# ------------------------------------------------------------------ admin

def login(client, password=ADMIN_PASSWORD, totp=""):
    page = client.get("/admin/login")
    return client.post("/admin/login", data={"csrf": csrf_of(page.text), "username": ADMIN_USER, "password": password,
                                             "totp": totp}, follow_redirects=False)


@pytest.fixture()
def admin_client(client):
    with db.connect() as conn:
        admin_auth.create_admin(conn, ADMIN_USER, ADMIN_PASSWORD)
    return client


def test_admin_pages_require_login(client):
    for path in ("/admin", "/admin/orders", "/admin/licenses", "/admin/settings", "/admin/checks", "/admin/transfers"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 303 and response.headers["location"] == "/admin/login", path
    assert client.post("/admin/orders/1/mark-paid", data={"note": "x"}, follow_redirects=False).status_code == 303


def test_admin_login_session_cookie_and_csrf(admin_client):
    assert login(admin_client, password="wrong-password-123").status_code == 401
    ok = login(admin_client)
    assert ok.status_code == 303
    cookie = ok.headers["set-cookie"]
    assert "calyx_admin=" in cookie and "HttpOnly" in cookie and "SameSite=strict" in cookie and "Path=/admin" in cookie
    dashboard = admin_client.get("/admin")
    assert dashboard.status_code == 200 and "Dashboard" in dashboard.text and "noindex" in dashboard.headers["x-robots-tag"]
    assert "No deposit address configured" in dashboard.text
    # POST without / with a wrong CSRF token is refused
    assert admin_client.post("/admin/settings", data={"trc20_address": TEST_TRON}).status_code == 403
    assert admin_client.post("/admin/settings", data={"csrf": "forged", "trc20_address": TEST_TRON}).status_code == 403
    settings_page = admin_client.get("/admin/settings")
    token = csrf_of(settings_page.text)
    form = {spec.key: str(spec.default) for spec in settings.SPECS if not spec.internal and spec.kind != "secret"}
    bad = admin_client.post("/admin/settings", data=form | {"csrf": token, "trc20_address": "TNotARealAddress123"})
    assert bad.status_code == 422 and "not a valid Tron address" in bad.text
    good = admin_client.post("/admin/settings", data=form | {"csrf": token, "trc20_address": TEST_TRON}, follow_redirects=False)
    assert good.status_code == 303
    with db.connect() as conn:
        assert settings.get(conn, "trc20_address") == TEST_TRON
    logout = admin_client.post("/admin/logout", data={"csrf": token}, follow_redirects=False)
    assert logout.status_code == 303 and admin_client.get("/admin", follow_redirects=False).status_code == 303


def test_admin_login_rate_limit(admin_client):
    for _ in range(admin_auth.MAX_FAILURES):
        assert login(admin_client, password="wrong-password-xyz").status_code == 401
    locked = login(admin_client)  # even the right password is refused while locked
    assert locked.status_code == 401 and "Too many failed attempts" in locked.text


def test_admin_totp_is_required_once_enabled(admin_client):
    with db.connect() as conn:
        admin_id = conn.execute("SELECT id FROM admins").fetchone()[0]
        secret = admin_auth.start_totp_setup(conn, admin_id)
        assert admin_auth.confirm_totp(conn, admin_id, security.totp_code(secret, int(time.time() // 30)), "admin:test")
    assert login(admin_client).status_code == 401  # no code
    code = security.totp_code(secret, int(time.time() // 30) + 1)
    assert login(admin_client, totp=code).status_code == 303
    admin_client.cookies.clear()
    assert login(admin_client, totp=code).status_code == 401  # replay of the same step refused


def test_admin_manual_payment_and_license_actions(admin_client):
    with db.connect() as conn:
        configure(conn)
    response = checkout(admin_client, [sellable_products()[0].slug])
    token = response.headers["location"].rsplit("/", 1)[1]
    with db.connect() as conn:
        order = orders.get_by_token(conn, token)
    login(admin_client)
    page = admin_client.get(f"/admin/orders/{order['id']}")
    csrf = csrf_of(page.text)
    short = admin_client.post(f"/admin/orders/{order['id']}/mark-paid", data={"csrf": csrf, "note": "ok"}, follow_redirects=True)
    assert "note of at least 5 characters" in short.text
    admin_client.post(f"/admin/orders/{order['id']}/mark-paid", data={"csrf": csrf, "note": "Paid via Binance Pay, checked by owner"})
    with db.connect() as conn:
        order = orders.get(conn, order["id"])
        lic = licenses.for_order(conn, order["id"])[0]
    assert order["status"] == "paid" and order["paid_by"] == f"admin:{ADMIN_USER}"
    admin_client.post(f"/admin/licenses/{lic['id']}/revoke", data={"csrf": csrf, "reason": "test"})
    with db.connect() as conn:
        assert licenses.get(conn, lic["id"])["status"] == "revoked"
    admin_client.post(f"/admin/licenses/{lic['id']}/unrevoke", data={"csrf": csrf})
    admin_client.post(f"/admin/licenses/{lic['id']}/extend", data={"csrf": csrf, "target": "updates", "days": "30"})
    admin_client.post(f"/admin/licenses/{lic['id']}/expiry", data={"csrf": csrf, "expires_on": "2030-01-31"})
    with db.connect() as conn:
        lic = licenses.get(conn, lic["id"])
        audit = [row["action"] for row in conn.execute("SELECT action FROM audit_log")]
    assert lic["status"] == "active" and lic["expires_at"].startswith("2030-01-31")
    assert {"order.paid", "license.revoke", "license.unrevoke", "license.extend_updates", "license.set_expiry"} <= set(audit)
    new_link = admin_client.post(f"/admin/orders/{order['id']}/new-link", data={"csrf": csrf})
    fresh = re.search(r"data-new-order-link>([^<]+)<", new_link.text).group(1)
    assert admin_client.get(f"/order/{token}").status_code == 404  # old link revoked
    assert admin_client.get(fresh.replace("http://127.0.0.1:8082", "")).status_code == 200
    for path in ("/admin/licenses", f"/admin/licenses/{lic['id']}", "/admin/checks", "/admin/transfers", "/admin/audit",
                 "/admin/security", "/admin/orders?status=paid"):
        assert admin_client.get(path).status_code == 200, path


def test_license_check_endpoint(client):
    response = client.post("/api/license/check", content=b"{bad json", headers={"content-type": "application/json"})
    assert response.status_code == 400
    response = client.post("/api/license/check", json={"key": "CLX-AAAAA-BBBBB-CCCCC-DDDDD", "login": 5550001,
                                                       "trade_mode": "demo", "build": "calyx-x-1", "magic": 1,
                                                       "nonce": "0" * 32, "server": "S"})
    body = response.json()
    assert response.status_code == 200 and body["allowed"] is False and body["code"] == "unknown_key"
    assert response.text.startswith('{"allowed":false,') and ": " not in response.text  # compact JSON for the MQL5 parser


def test_store_build_manifest_is_consistent_when_present():
    manifest = builds.load_manifest()
    if not manifest.get("builds"):
        pytest.skip("store builds not generated on this machine")
    current = {bid: b for bid, b in manifest["builds"].items() if b.get("current")}
    for slug, product in manifest["products"].items():
        assert product["build_id"] in current, slug
        assert slug in current[product["build_id"]]["products"]
        assert product["magic"] is not None
    for build in current.values():
        assert build["compiled"], build["name"]
        assert (builds.builds_root() / build["ex5"]).is_file()
