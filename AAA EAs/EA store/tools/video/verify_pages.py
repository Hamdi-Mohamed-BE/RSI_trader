"""Screenshot the store pages at desktop and phone width from a LOCAL dev server (verification only).

    python tools/video/verify_pages.py http://127.0.0.1:8082 <out_dir> <preview-orders.json> [<preview-cred.json>]
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cdp import Browser, open_page  # noqa: E402

ADD = """(async () => { for (const s of %s) { await fetch('/cart/add', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:'slug='+s, redirect:'manual'}); } return document.cookie.length; })()"""


async def main(base: str, out: Path, orders_file: Path, cred_file: Path | None) -> None:
    orders = json.loads(orders_file.read_text())
    with Browser(9334) as browser:
        session, page = await open_page(browser)
        try:
            for label, (w, h, mobile) in {"desktop": (1440, 900, False), "mobile": (390, 844, True)}.items():
                await page.viewport(w, h, mobile)
                await page.goto(base + "/eas")
                await page.eval(ADD % json.dumps(["orb-volume-profile", "xau-weakness", "ema3", "asia-breakout", "3-way-gold"]))
                for name, path in [("pricing", "/pricing"), ("detail", "/eas/3-way-gold"), ("cart", "/cart"),
                                   ("checkout", "/checkout"), ("order-pending", f"/order/{orders['pending']}"),
                                   ("order-paid", f"/order/{orders['paid']}"), ("how", "/how-it-works"),
                                   ("admin-login", "/admin/login")]:
                    await page.goto(base + path)
                    await page.shot(out / f"{label}-{name}.png", full=True)
                    overflow = await page.eval("document.documentElement.scrollWidth > window.innerWidth + 1")
                    print(label, name, "horizontal-overflow" if overflow else "ok")
                if cred_file and label == "desktop":
                    cred = json.loads(cred_file.read_text())
                    await page.goto(base + "/admin/login")
                    await page.eval("document.querySelector('#username').value=%s; document.querySelector('#password').value=%s; document.querySelector('form').submit(); 1"
                                    % (json.dumps(cred["username"]), json.dumps(cred["password"])))
                    await asyncio.sleep(2)
                    for name, path in [("admin-dashboard", "/admin"), ("admin-orders", "/admin/orders"),
                                       ("admin-licenses", "/admin/licenses"), ("admin-settings", "/admin/settings")]:
                        await page.goto(base + path)
                        await page.shot(out / f"{label}-{name}.png", full=True)
                        print(label, name, await page.eval("document.title"))
        finally:
            await page.ws.close()
            await session.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]) if len(sys.argv) > 4 else None))
