"""Minimal Chrome DevTools Protocol driver (aiohttp) for deterministic site screenshots.

Starts a throw-away headless Chrome profile; never uses the person's browser profile.
"""
from __future__ import annotations

import asyncio
import base64
import itertools
import json
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import aiohttp

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


class Browser:
    def __init__(self, port: int = 9333):
        self.port = port
        self.proc: subprocess.Popen | None = None
        self.profile = Path(tempfile.mkdtemp(prefix="calyx-video-chrome-"))

    def __enter__(self) -> "Browser":
        exe = next(p for p in CHROME_CANDIDATES if Path(p).exists())
        self.proc = subprocess.Popen([exe, "--headless=new", f"--remote-debugging-port={self.port}",
                                      f"--user-data-dir={self.profile}", "--hide-scrollbars", "--no-first-run",
                                      "--no-default-browser-check", "--disable-extensions", "--force-color-profile=srgb",
                                      "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/version", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        return self

    def __exit__(self, *exc) -> None:
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        shutil.rmtree(self.profile, ignore_errors=True)

    def page_ws(self) -> str:
        targets = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/list").read())
        page = next(t for t in targets if t["type"] == "page")
        return page["webSocketDebuggerUrl"]


class Page:
    def __init__(self, ws: aiohttp.ClientWebSocketResponse):
        self.ws = ws
        self.ids = itertools.count(1)
        self.events: list[dict] = []

    async def call(self, method: str, **params):
        msg_id = next(self.ids)
        await self.ws.send_str(json.dumps({"id": msg_id, "method": method, "params": params}))
        while True:
            msg = json.loads((await self.ws.receive()).data)
            if msg.get("id") == msg_id:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
            self.events.append(msg)

    async def viewport(self, width: int, height: int, mobile: bool = False, scale: float = 1.0):
        await self.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=scale,
                        mobile=mobile)

    async def goto(self, url: str, settle: float = 1.2):
        await self.call("Page.navigate", url=url)
        for _ in range(200):
            state = await self.eval("document.readyState")
            if state == "complete":
                break
            await asyncio.sleep(0.1)
        await asyncio.sleep(settle)  # Tailwind CDN + fonts

    async def eval(self, expression: str):
        result = await self.call("Runtime.evaluate", expression=expression, awaitPromise=True, returnByValue=True)
        return result.get("result", {}).get("value")

    async def shot(self, path: Path, full: bool = False):
        params = {"format": "png"}
        if full:
            metrics = await self.call("Page.getLayoutMetrics")
            size = metrics["cssContentSize"]
            params.update(captureBeyondViewport=True,
                          clip={"x": 0, "y": 0, "width": size["width"], "height": size["height"], "scale": 1})
        data = await self.call("Page.captureScreenshot", **params)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(data["data"]))


async def open_page(browser: Browser):
    session = aiohttp.ClientSession()
    ws = await session.ws_connect(browser.page_ws(), max_msg_size=200 * 1024 * 1024)
    page = Page(ws)
    await page.call("Page.enable")
    await page.call("Runtime.enable")
    return session, page
