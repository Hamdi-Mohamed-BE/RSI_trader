"""Temporary loopback-only paper access; normal auth remains available when disabled."""

from __future__ import annotations

from ipaddress import ip_address
from urllib.parse import urlsplit

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response


class LocalPaperBoundary(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            local = request.client is not None and ip_address(request.client.host).is_loopback
        except ValueError:
            local = False
        if not local or request.url.hostname not in {"localhost", "127.0.0.1", "::1"}:
            return PlainTextResponse("Local paper dashboard only.", status_code=403)
        origin = request.headers.get("origin")
        if request.headers.get("sec-fetch-site") == "cross-site" or (
            origin and urlsplit(origin).netloc != request.url.netloc
        ):
            return PlainTextResponse("Cross-origin access refused.", status_code=403)
        if request.url.path.startswith(("/account/", "/admin/keys")):
            return PlainTextResponse("Restore normal login to manage credentials or account security.", status_code=403)
        return await call_next(request)
