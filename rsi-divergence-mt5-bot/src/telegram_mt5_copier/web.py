from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .settings import ROOT, load_settings, public_settings, update_env
from .telegram_api import BotApiSource
from .worker import WorkerManager


manager = WorkerManager()
templates = Jinja2Templates(directory=ROOT / "templates")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if load_settings().copier_enabled:
        await manager.start()
    yield
    await manager.stop()


app = FastAPI(title="Telegram MT5 Copier", version="1.0.0", lifespan=lifespan)


class SettingsUpdate(BaseModel):
    values: dict[str, object]


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204, headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/status")
def status() -> dict:
    return manager.status.to_dict()


@app.post("/api/start")
async def start() -> dict:
    return await manager.start()


@app.post("/api/stop")
async def stop() -> dict:
    return await manager.stop()


@app.get("/api/settings")
def get_settings() -> dict:
    return public_settings(load_settings())


@app.put("/api/settings")
async def save_settings(payload: SettingsUpdate) -> dict:
    try:
        saved = update_env(payload.values)
        saved.aliases
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await manager.restart()
    return public_settings(saved)


@app.get("/api/messages")
def messages(limit: int = 100) -> list[dict]:
    return manager.state.recent_messages(min(max(limit, 1), 500))


@app.post("/api/test-telegram")
async def test_telegram() -> dict:
    settings = load_settings()
    if settings.telegram_mode != "bot":
        return {"ok": bool(settings.telegram_api_id and settings.telegram_api_hash), "mode": "user"}
    source = BotApiSource(settings, manager.state)
    try:
        bot = await source.verify()
        return {"ok": True, "mode": "bot", "username": bot.get("username")}
    finally:
        await source.close()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
