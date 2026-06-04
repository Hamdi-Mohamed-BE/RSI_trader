from __future__ import annotations

import sys


def playwright_runtime_error(exc: BaseException) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()
    if "greenlet" in lowered or "_greenlet" in lowered:
        reinstall = "uv pip install --force-reinstall greenlet playwright && playwright install chromium"
        if sys.platform == "win32":
            return (
                "Playwright could not load greenlet (native DLL missing). "
                "Install Microsoft Visual C++ 2015-2022 Redistributable (x64), then run: "
                f"{reinstall}"
            )
        return f"Playwright could not load greenlet. Reinstall dependencies: {reinstall}"
    return f"Playwright is not available: {message}"


def ensure_playwright_runtime() -> tuple[bool, str | None]:
    try:
        import greenlet  # noqa: F401
    except ImportError as exc:
        return False, playwright_runtime_error(exc)

    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError as exc:
        return False, playwright_runtime_error(exc)

    return True, None


def load_sync_playwright():
    ok, error = ensure_playwright_runtime()
    if not ok:
        raise RuntimeError(error or "Playwright is not available")
    from playwright.sync_api import sync_playwright

    return sync_playwright
