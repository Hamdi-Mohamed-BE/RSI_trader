from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates

from .security import csrf_token

PACKAGE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=PACKAGE_DIR / "templates")


def page_context(request: Request, **values: Any) -> dict[str, Any]:
    return {
        "request": request,
        "csrf_token": csrf_token(request),
        "app_name": request.app.state.settings.app_name,
        "safe_mode": request.app.state.settings.safe_mode,
        **values,
    }
