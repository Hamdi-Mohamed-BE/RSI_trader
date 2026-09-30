"""With CALYX_STORE_ENABLED off (production default) the site renders as before the store: list prices, WhatsApp
checkout, no cart/checkout/admin/license routes. Runs in a fresh interpreter because the switch is read at import."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = r'''
import json
from fastapi.testclient import TestClient
from app.main import app
from app.catalog import get_sellable_catalog
c = TestClient(app)
p = next(x for x in get_sellable_catalog() if x.slug == "3-way-gold")
detail = c.get("/eas/3-way-gold").text
pricing = c.get("/pricing").text
print(json.dumps({
    "cart": c.get("/cart").status_code, "admin": c.get("/admin/login").status_code,
    "how": c.get("/how-it-works").status_code, "license": c.post("/api/license/check", json={}).status_code,
    "detail_whatsapp": "Buy via WhatsApp" in detail, "detail_cart": "/cart/add" in detail,
    "detail_price": f"${p.price:,}" in detail, "nav_cart": 'href="/cart"' in c.get("/eas").text,
    "pricing_old": "$1,990" in pricing and "Choose 3 + bonus EA" in pricing, "pricing_usdt": "pay in USDT" in pricing,
}))
'''


def test_store_off_is_the_pre_store_site():
    env = dict(os.environ, CALYX_STORE_ENABLED="0", EA_STORE_DISABLE_MT5="1", CALYX_STORE_WATCHER="0")
    out = subprocess.run([sys.executable, "-c", PROBE], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, out.stderr[-3000:]
    r = json.loads(out.stdout.strip().splitlines()[-1])
    assert r["cart"] == r["admin"] == r["how"] == r["license"] == 404
    assert r["detail_whatsapp"] and not r["detail_cart"] and r["detail_price"]
    assert not r["nav_cart"]
    assert r["pricing_old"] and not r["pricing_usdt"]
