"""Capture the explainer-video frames (1920x1080) from a LOCAL dev server running in demo mode.

    python tools/video/capture_shots.py <base_url> <work_dir> <preview_db_path>

The preview database is re-created with obviously fake DEMO deposit addresses and demo orders; it must not be
the real store database. The dev server must run with CALYX_STORE_DEMO=1 and CALYX_STORE_WATCHER=0.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
from cdp import Browser, open_page  # noqa: E402
import mocks  # noqa: E402

DEMO_TRC20 = "TDEMOxxDEMOxxDEMOxxDEMOxxDEMOxxDEMO"
DEMO_BEP20 = "0xDEMO000000000000000000000000000000000000"
PICKS = ["orb-volume-profile", "xau-weakness", "ema3", "asia-breakout"]

HIGHLIGHT_JS = """(() => { const style = document.createElement('style');
style.textContent = '.vhl{outline:4px solid #7ef7c7 !important;outline-offset:6px;border-radius:14px;box-shadow:0 0 0 14px rgba(126,247,199,.16) !important}'
 + '.vcall{position:fixed;z-index:9999;padding:14px 20px;border-radius:14px;background:linear-gradient(135deg,#c4ff63,#7ef7c7);color:#06110e;font:800 24px Manrope,sans-serif;box-shadow:0 18px 50px rgba(0,0,0,.45)}';
document.head.appendChild(style);
document.querySelectorAll('.whatsapp-float').forEach(e => e.style.display='none');
return 1; })()"""


def seed(db_path: Path) -> dict:
    real = (ROOT / "data" / "store.sqlite3").resolve()
    if db_path.resolve() == real:
        raise SystemExit("Refusing to seed demo data into the real store database.")
    os.environ["CALYX_STORE_DB"] = str(db_path)
    os.environ["EA_STORE_DISABLE_MT5"] = "1"
    from app.catalog import get_sellable_catalog
    from app.store import db, orders, pricing, settings

    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(db_path) + suffix)
        if candidate.exists():
            candidate.unlink()
    db.init_db(db_path)
    with db.connect() as conn:
        settings.set_value(conn, "trc20_address", DEMO_TRC20)  # obviously fake, bypasses validation on purpose
        settings.set_value(conn, "bep20_address", DEMO_BEP20)
        catalog = {p.slug: p for p in get_sellable_catalog()}
        quote = pricing.quote([catalog[s] for s in PICKS])
        values = settings.get_all(conn)
        paid = orders.create_order(conn, quote, email="demo.buyer@example.com", network="TRC20", values=values)
        orders.mark_paid(conn, paid.order_id, paid_by="admin:demo", tx_hash="DEMO-TX-NOT-A-REAL-PAYMENT", note="DEMO order for the video")
        pending = orders.create_order(conn, quote, email="demo.buyer@example.com", network="TRC20", values=values)
    return {"paid": paid.token, "pending": pending.token}


def installer_output(work: Path) -> list[tuple[str, str]]:
    """Run the real installer against fake folders and return sanitized, colour-classified lines."""
    fake = work / "fake-mt5"
    shutil.rmtree(fake, ignore_errors=True)
    pkg = fake / "Calyx ORB Volume Profile"
    pkg.mkdir(parents=True)
    shutil.copyfile(ROOT / "app" / "store" / "installer" / "Install-CalyxBot.ps1", pkg / "Install-CalyxBot.ps1")
    (pkg / "Calyx ORB Volume Data EA.ex5").write_bytes(b"demo")
    (pkg / "ORB Volume Profile - Calyx.set").write_bytes("InpCalyxLicenseKey=CLX-DEMO0-DEMO0-DEMO0-DEMO0\r\nInpMagic=86080707\r\n".encode("utf-16"))
    root = fake / "Terminal"
    for name, origin in (("0A1B2C3D4E5F60718293A4B5C6D7E8F9", r"C:\Program Files\Example Broker MetaTrader 5"),
                         ("9F8E7D6C5B4A39281706F5E4D3C2B1A0", r"D:\MT5 Strategy Tester copy")):
        (root / name / "MQL5").mkdir(parents=True)
        (root / name / "origin.txt").write_bytes(origin.encode("utf-16"))
        (root / name / "config").mkdir()
        (root / name / "config" / "common.ini").write_bytes("[Experts]\r\nEnabled=0\r\nWebRequest=0\r\n".encode("utf-16"))
    ps = shutil.which("powershell.exe")
    result = subprocess.run([ps, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(pkg / "Install-CalyxBot.ps1"),
                             "-BotName", "ORB Volume Profile", "-DefaultSymbol", "XAUUSD", "-PeriodMinutes", "5",
                             "-AllowUrl", "https://calyx.duckdns.org", "-TerminalRoot", str(root), "-Symbol", "XAUUSD.r", "-Yes"],
                            capture_output=True, text=True, timeout=120)
    text = result.stdout.replace(str(root), r"C:\Users\you\AppData\Roaming\MetaQuotes\Terminal")
    lines: list[tuple[str, str]] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        cls = "c" if line.startswith("==") else "g" if re.search(r"(Selected|copied|updated|Calyx installer)", line) else \
            "y" if "skipped" in line else "d" if line.strip().startswith(("C:\\Users\\you", "0A1B")) else "w"
        lines.append((cls, line))
    shutil.rmtree(fake, ignore_errors=True)
    return lines[:34]


async def site_shots(base: str, out: Path, tokens: dict) -> None:
    with Browser(9335) as browser:
        session, page = await open_page(browser)
        try:
            await page.viewport(1920, 1080)

            async def shot(name: str, url: str, js: str = "", scroll: str | None = None):
                await page.goto(base + url, settle=1.6)
                await page.eval(HIGHLIGHT_JS)
                if scroll:
                    await page.eval(f"(() => {{ const e=document.querySelector({json.dumps(scroll)}); if(e) window.scrollTo(0, e.getBoundingClientRect().top + window.scrollY - 110); return 1; }})()")
                if js:
                    await page.eval(js)
                await asyncio.sleep(0.5)
                await page.shot(out / f"{name}.png")
                print("shot", name, flush=True)

            await shot("02-store", "/store")
            await shot("03-catalogue", "/eas", scroll="[data-order]",
                       js="document.querySelectorAll('.product-card').forEach((c,i)=>{ if(i<3) c.classList.add('vhl'); }); 1")
            await shot("04-detail", "/eas/orb-volume-profile",
                       js="(() => { const p=document.querySelector('.buy-panel'); p.classList.add('vhl'); const r=p.getBoundingClientRect(); const c=document.createElement('div'); c.className='vcall'; c.textContent='40% lower price · Add to cart'; c.style.left=(r.left-40)+'px'; c.style.top=(r.bottom+24)+'px'; document.body.appendChild(c); return 1; })()")
            await page.eval("(async () => { await fetch('/cart/clear', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:'', redirect:'manual'}); for (const s of %s) { await fetch('/cart/add', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:'slug='+s, redirect:'manual'}); } return 1; })()" % json.dumps(PICKS))
            await shot("05-cart", "/cart", scroll="[data-cart]",
                       js="(() => { document.querySelector('.store-free').closest('.store-row').classList.add('vhl'); document.querySelector('aside.store-panel').classList.add('vhl'); return 1; })()")
            await shot("06-checkout", "/checkout", scroll=".demo-ribbon",
                       js="(() => { document.querySelector('#email').value='demo.buyer@example.com'; document.querySelector('[name=accept]').checked=true; document.querySelector('[data-checkout-form] fieldset').classList.add('vhl'); return 1; })()")
            await shot("07-pay", f"/order/{tokens['pending']}", scroll=".demo-ribbon",
                       js="(() => { document.querySelector('.pay-amount').classList.add('vhl'); document.querySelector('.network-warning').classList.add('vhl'); return 1; })()")
            await shot("08-paid", f"/order/{tokens['paid']}", scroll=".success-banner",
                       js="(() => { document.querySelector('[data-license]').classList.add('vhl'); return 1; })()")
            await page.eval("(async () => { await fetch('/cart/clear', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:'', redirect:'manual'}); return 1; })()")

            logo = (base + "/static/images/calyx-logo.jpg")
            mock_pages = {
                "01-title": mocks.title_card(logo),
                "09-zip": mocks.zip_listing("ORB Volume Profile", "Calyx ORB Volume Data EA.ex5"),
                "10-installer": mocks.installer_console(installer_output(out.parent)),
                "11-webrequest": mocks.mt5_webrequest(),
                "12-profile": mocks.mt5_profiles(),
                "13-algo": mocks.mt5_algo(),
                "14-chart": mocks.mt5_chart(),
                "15-outro": mocks.outro_card(logo),
            }
            for name, html in mock_pages.items():
                path = out.parent / "mocks" / f"{name}.html"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(html, encoding="utf-8")
                await page.goto(path.resolve().as_uri(), settle=1.5)
                await page.shot(out / f"{name}.png")
                print("shot", name, flush=True)
        finally:
            await page.ws.close()
            await session.close()


def main() -> None:
    base, work, db_path = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    tokens = seed(db_path)
    (work / "shots").mkdir(parents=True, exist_ok=True)
    asyncio.run(site_shots(base, work / "shots", tokens))


if __name__ == "__main__":
    main()
