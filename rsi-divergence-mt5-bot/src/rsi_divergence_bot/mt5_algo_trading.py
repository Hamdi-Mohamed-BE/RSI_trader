from __future__ import annotations

import configparser
import logging
import sys
import time
from pathlib import Path
from typing import Any

from .config import MT5Config

logger = logging.getLogger(__name__)

EXPERTS_DEFAULTS = {
    "AllowLiveTrading": "1",
    "Enabled": "1",
    "Account": "0",
    "Profile": "0",
}


def _terminal_info_dict(client: Any) -> dict[str, Any]:
    info = client.mt5.terminal_info()
    if info is None:
        return {}
    if isinstance(info, dict):
        return info
    if hasattr(info, "_asdict"):
        return info._asdict()
    return {key: getattr(info, key) for key in dir(info) if not key.startswith("_")}


def is_algo_trading_enabled(client: Any) -> bool | None:
    """Return True when MT5 allows automated/Python trading, None if unknown."""
    info = _terminal_info_dict(client)
    if not info:
        return None
    trade_allowed = info.get("trade_allowed")
    tradeapi_disabled = info.get("tradeapi_disabled")
    if trade_allowed is False:
        return False
    if tradeapi_disabled is True:
        return False
    if trade_allowed is True and tradeapi_disabled is False:
        return True
    return None


def terminal_common_ini_path(client: Any) -> Path | None:
    info = _terminal_info_dict(client)
    data_path = str(info.get("data_path") or "").strip()
    if not data_path:
        return None
    return Path(data_path) / "config" / "common.ini"


def patch_experts_ini(ini_path: Path, *, values: dict[str, str] | None = None) -> bool:
    """Ensure [Experts] allows algo trading and does not disable on account switch."""
    if not ini_path.parent.exists():
        return False
    ini_path.parent.mkdir(parents=True, exist_ok=True)
    parser = configparser.ConfigParser()
    parser.optionxform = str
    if ini_path.exists():
        parser.read(ini_path, encoding="utf-8")
    if "Experts" not in parser:
        parser["Experts"] = {}
    section = parser["Experts"]
    changed = False
    for key, value in (values or EXPERTS_DEFAULTS).items():
        if section.get(key) != value:
            section[key] = value
            changed = True
    if changed or not ini_path.exists():
        with ini_path.open("w", encoding="utf-8") as handle:
            parser.write(handle)
        return True
    return False


def _send_algo_trading_hotkey() -> bool:
    """Toggle MT5 Algo Trading via Ctrl+E on the terminal window (Windows only)."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:  # pragma: no cover
        return False

    user32 = ctypes.windll.user32
    found: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.lower()
        if "metatrader" in title:
            found.append(int(hwnd))
        return True

    user32.EnumWindows(_enum, 0)
    if not found:
        return False

    hwnd = found[0]
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.05)

    KEYEVENTF_KEYUP = 0x0002
    VK_CONTROL = 0x11
    VK_E = 0x45
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_E, 0, 0, 0)
    user32.keybd_event(VK_E, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
    return True


def ensure_algo_trading(
    client: Any,
    *,
    config: MT5Config | None = None,
    log: logging.Logger | None = None,
) -> bool:
    """
    Enable MT5 algo trading after login/account switch.

    MT5 often disables the Algo Trading button when the account changes (Experts: Account=1).
    We patch common.ini to keep it enabled and send Ctrl+E if the terminal still blocks API trades.
    """
    active_log = log or logger
    if config is not None and not config.auto_enable_algo_trading:
        return True

    if is_algo_trading_enabled(client) is True:
        return True

    ini_path = terminal_common_ini_path(client)
    if ini_path is not None:
        try:
            if patch_experts_ini(ini_path):
                active_log.info("MT5 patched Experts config at %s", ini_path)
        except OSError as exc:
            active_log.warning("MT5 could not patch Experts config: %s", exc)

    if is_algo_trading_enabled(client) is True:
        return True

    if is_algo_trading_enabled(client) is False and (config is None or config.mode == "native_windows"):
        if _send_algo_trading_hotkey():
            time.sleep(0.2)
            active_log.info("MT5 sent Algo Trading hotkey (Ctrl+E)")

    enabled = is_algo_trading_enabled(client)
    if enabled is True:
        return True

    if enabled is False:
        active_log.warning(
            "MT5 algo trading is still disabled after login. "
            "Enable the Algo Trading toolbar button manually in MetaTrader 5."
        )
        return False
    return True
