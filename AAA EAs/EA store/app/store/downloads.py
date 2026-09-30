"""Signed, expiring download links and the per-bot ZIP package."""

from __future__ import annotations

import io
import re
import sqlite3
import time
import zipfile
from datetime import datetime
from typing import Any

from . import config
from .builds import build_ex5_path, product_build
from .security import sign, unsign

LINK_TTL_SECONDS = 2 * 3600
PURPOSE = "download"
UNSAFE_FILENAME = re.compile(r'[\\/:*?"<>|%&^!\r\n\t]+')


def make_token(license_id: int, order_id: int, *, ttl: int = LINK_TTL_SECONDS, now: float | None = None) -> str:
    return sign({"l": int(license_id), "o": int(order_id), "exp": int((now or time.time()) + ttl)}, PURPOSE)


def read_token(token: str, *, now: float | None = None) -> dict[str, Any] | None:
    payload = unsign(token, PURPOSE, now=now)
    if not payload or not isinstance(payload.get("l"), int) or not isinstance(payload.get("o"), int):
        return None
    return payload


def safe_name(text: str) -> str:
    cleaned = UNSAFE_FILENAME.sub("-", text).strip(" .-")
    return re.sub(r"\s+", " ", cleaned)[:80] or "Calyx EA"


def set_file_text(license_key: str, product_slug: str, inputs: dict[str, str]) -> str:
    lines = [f"InpCalyxLicenseKey={license_key}", f"InpCalyxProduct={product_slug}"]
    lines += [f"{key}={value}" for key, value in inputs.items() if key not in {"InpCalyxLicenseKey", "InpCalyxProduct"}]
    return "\r\n".join(lines) + "\r\n"


def bat_text(bot: str, ex5: str, set_name: str, symbol: str, period: int, origin: str) -> str:
    return (
        "@echo off\r\n"
        "setlocal\r\n"
        f"title Calyx installer - {bot}\r\n"
        "cd /d \"%~dp0\"\r\n"
        f"echo Installing {bot} into MetaTrader 5 ...\r\n"
        "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"%~dp0Install-CalyxBot.ps1\" "
        f"-BotName \"{bot}\" -ExpertFile \"{ex5}\" -SetFile \"{set_name}\" -DefaultSymbol \"{symbol}\" "
        f"-PeriodMinutes {period} -AllowUrl \"{origin}\"\r\n"
        "echo.\r\n"
        "pause\r\n"
    )


def readme_text(*, bot: str, symbol: str, timeframe: str, ex5: str, set_name: str, bat: str, origin: str,
                order_id: str, license_key: str) -> str:
    return f"""Calyx - {bot}
{'=' * (8 + len(bot))}

Order {order_id} · License {license_key[:9]}-****-****-****
Symbol {symbol} · Timeframe {timeframe}

Files
  {ex5}          compiled Expert Advisor (Calyx store build with online license check)
  {set_name}     settings with your license key already filled in
  {bat}          one-click installer (runs Install-CalyxBot.ps1 with PowerShell)
  Install-CalyxBot.ps1  the installer itself (PowerShell only, no Python needed)

Install
  1. Right-click the ZIP > Extract All. Do not run the installer from inside the ZIP.
  2. Double-click "{bat}".
  3. Pick your MetaTrader 5 terminal from the list and type your broker's symbol name
     (for example XAUUSD, XAUUSD.r or GOLD - check Market Watch).
  4. The installer copies the EA to MQL5\\Experts\\Calyx, the SET to MQL5\\Presets and
     creates the chart profile "Calyx - {bot}". It adds {origin} to the WebRequest list
     only if MT5 is closed; otherwise it prints the manual steps.

In MetaTrader 5
  * Tools > Options > Expert Advisors > tick "Allow WebRequest for listed URL" and make sure
    {origin} is listed (needed for license activation).
  * File > Profiles > "Calyx - {bot}".
  * On the chart press F7 > Common > tick "Allow Algo Trading", then switch on the
    Algo Trading toolbar button. The installer never does this for you.
  * Experts tab: "Calyx license: activated for account ..." confirms activation.

License behaviour
  * 1 live + 1 demo MT5 account per license. The first activation from an account binds it.
  * The EA checks the license when it starts and every 24 hours. If the server cannot be
    reached it keeps working for up to 72 hours after the last successful check.
  * If the license is refused (revoked, other account, wrong SET) the EA prints the reason and
    removes itself from the chart. Positions it opened are then no longer managed by it.
  * Strategy Tester runs are not checked, so backtests behave like the original EA.

Risk
  Trading leveraged products can lose all deposited capital. Historical tests are not a
  forecast or guarantee. Test on the demo account first.
"""


def license_text(*, bot: str, license_key: str, order_id: str, email: str, issued: str, updates_until: str) -> str:
    return f"""Calyx single-EA license

Product:        {bot}
License key:    {license_key}
Order:          {order_id}
Licensee:       {email}
Issued:         {issued}
Updates until:  {updates_until}

1. This license lets the licensee use the compiled Expert Advisor on one live and one demo
   MetaTrader 5 account. Account changes are made by Calyx support.
2. The software is licensed, not sold. No source code is included. Copying, resale,
   sharing of the license key or files, decompiling or circumventing the license check is
   not permitted.
3. Updates for the purchased version are provided for 12 months from purchase.
4. The license may be revoked for misuse (for example key sharing or chargeback-like disputes).
5. No guarantee of profit. Trading involves substantial risk of loss. Historical results,
   including backtests, do not predict future results. The licensee is responsible for all
   trading decisions, settings and broker compatibility.
6. The software is provided "as is", without warranty of any kind, to the extent permitted by law.
"""


def build_zip(lic: sqlite3.Row, order: sqlite3.Row, *, origin: str, timeframe: str = "") -> tuple[str, bytes]:
    """Return (filename, zip bytes) for one license. Raises LookupError when no store build exists."""
    mapping = product_build(lic["product_slug"])
    if mapping is None:
        raise LookupError("No store build for this product yet.")
    build, product = mapping["build"], mapping["product"]
    ex5_path = build_ex5_path(build)
    if not build.get("compiled") or not ex5_path.is_file():
        raise LookupError("The store build for this product is not compiled yet.")
    bot = safe_name(lic["label"])
    folder = f"Calyx {bot}"
    ex5 = build["ex5"]
    set_name = f"{bot} - Calyx.set"
    bat = f"INSTALL {bot}.bat"
    set_bytes = set_file_text(lic["license_key"], lic["product_slug"], product["inputs"]).encode("utf-16")  # BOM + UTF-16LE
    installer = (config.INSTALLER_TEMPLATE_ROOT / "Install-CalyxBot.ps1").read_bytes()
    period = int(product.get("period_minutes") or 60)
    symbol = str(product.get("symbol") or "XAUUSD")
    issued = str(lic["created_at"])[:10]
    updates = str(lic["updates_until"] or "")[:10]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        stamp = datetime.now().timetuple()[:6]

        def add(name: str, data: bytes) -> None:
            info = zipfile.ZipInfo(f"{folder}/{name}", date_time=stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)

        add(ex5, ex5_path.read_bytes())
        add(set_name, set_bytes)
        add(bat, bat_text(bot, ex5, set_name, symbol, period, origin).encode("ascii", "replace"))
        add("Install-CalyxBot.ps1", installer)
        add("README.txt", readme_text(bot=bot, symbol=symbol, timeframe=timeframe or f"{period} min", ex5=ex5,
                                      set_name=set_name, bat=bat, origin=origin, order_id=order["public_id"],
                                      license_key=lic["license_key"]).encode("utf-8-sig"))
        add("LICENSE.txt", license_text(bot=lic["label"], license_key=lic["license_key"], order_id=order["public_id"],
                                        email=order["email"], issued=issued, updates_until=updates).encode("utf-8-sig"))
    return f"{folder}.zip", buffer.getvalue()
