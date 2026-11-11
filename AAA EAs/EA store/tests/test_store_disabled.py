"""With CALYX_STORE_ENABLED off (production default) the site is research only (owner 2026-11-09): no prices, no WhatsApp
or buy buttons, /pricing redirects to the research home, and no cart/checkout/admin/license routes. Runs in a fresh
interpreter because the switch is read at import."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = r'''
import json, re
from fastapi.testclient import TestClient
from app.main import app
from app.catalog import get_sellable_catalog
c = TestClient(app)
p = next(x for x in get_sellable_catalog() if x.slug == "3-way-gold")
pages = {path: c.get(path).text for path in ("/store", "/eas", "/eas/3-way-gold", "/portfolios", "/risk")}
pricing = c.get("/pricing", follow_redirects=False)
joined = "\n".join(pages.values())
print(json.dumps({
    "cart": c.get("/cart").status_code, "admin": c.get("/admin/login").status_code,
    "how": c.get("/how-it-works").status_code, "license": c.post("/api/license/check", json={}).status_code,
    "pricing": [pricing.status_code, pricing.headers.get("location")],
    "price_shown": bool(re.search(r"\$" + re.escape(f"{p.price:,}") + r"(?![\d.,])|\$1,990", joined)), "whatsapp": "wa.me" in joined or "WhatsApp" in joined,
    "buy": "Buy via" in joined or "/cart/add" in joined or 'href="/pricing"' in joined or 'href="/cart"' in joined,
    "research_label": all("Research only" in t or "RESEARCH ONLY" in t for t in pages.values()),
}))
'''


def test_store_off_is_research_only():
    env = dict(os.environ, CALYX_STORE_ENABLED="0", EA_STORE_DISABLE_MT5="1", CALYX_STORE_WATCHER="0")
    out = subprocess.run([sys.executable, "-c", PROBE], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, out.stderr[-3000:]
    r = json.loads(out.stdout.strip().splitlines()[-1])
    assert r["cart"] == r["admin"] == r["how"] == r["license"] == 404
    assert r["pricing"] == [307, "/store"]
    assert not r["price_shown"] and not r["whatsapp"] and not r["buy"]
    assert r["research_label"]
