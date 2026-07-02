from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .api import router
from .database import init_db
from .settings import ROOT


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="NAW LTA", version="0.1.0", lifespan=lifespan)
app.include_router(router)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "templates")


def render(request: Request, template: str, page: str) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name=template,
        context={"page": page},
    )


@app.get("/", response_class=HTMLResponse)
def dashboard_page(request: Request) -> HTMLResponse:
    return render(request, "dashboard.html", "dashboard")


@app.get("/scanner", response_class=HTMLResponse)
def scanner_page(request: Request) -> HTMLResponse:
    return render(request, "scanner.html", "scanner")


@app.get("/backtests", response_class=HTMLResponse)
def backtests_page(request: Request) -> HTMLResponse:
    return render(request, "backtests.html", "backtests")


@app.get("/config", response_class=HTMLResponse)
def config_page(request: Request) -> HTMLResponse:
    return render(request, "config.html", "config")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
