from __future__ import annotations

from datetime import date, datetime, timedelta
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from .backtester import run_backtest
from .automation import LATEST_SCAN_PATH
from .config import PROJECT_ROOT, REPORTS_DIR, load_config
from .models import ALLOWED_SYMBOLS, ALLOWED_TIMEFRAMES, BacktestRequest
from .mt5_client import MT5Client


app = FastAPI(
    title="LTA A+ Setup Research Platform",
    description="Local FastAPI backtesting UI for LTA Concepts research. Live trading is disabled by default.",
    version="0.1.0",
)

templates = Jinja2Templates(directory=str(PROJECT_ROOT / "app" / "templates"))


def _default_context(request: Request, **extra):
    config = load_config()
    today = date.today()
    context = {
        "request": request,
        "symbols": ALLOWED_SYMBOLS,
        "timeframes": ALLOWED_TIMEFRAMES,
        "defaults": {
            "symbol": "ALL",
            "timeframe": "M15",
            "start": (today - timedelta(days=30)).isoformat(),
            "end": today.isoformat(),
            "starting_balance": config.starting_balance,
            "xau_lot": config.symbol_lots["XAUUSD"],
            "xag_lot": config.symbol_lots["XAGUSD"],
            "btc_lot": config.symbol_lots["BTCUSD"],
            "risk_per_trade_percent": config.max_risk_per_trade_percent,
            "max_daily_loss_percent": config.max_daily_loss_percent,
            "max_drawdown_percent": config.max_total_drawdown_percent,
            "max_trades_per_day": config.max_trades_per_day,
            "min_setup_score": config.min_setup_score,
            "min_risk_reward": config.min_risk_reward,
        },
        "live_trading": config.live_trading,
        "mt5_status": MT5Client().terminal_status(),
    }
    context.update(extra)
    return context


def _lot_for_symbol(symbol: str, form) -> float:
    if symbol == "ALL":
        return float(form.get("xau_lot") or 0.01)
    key = {"XAUUSD": "xau_lot", "XAGUSD": "xag_lot", "BTCUSD": "btc_lot"}[symbol]
    return float(form.get(key) or 0.01)


def _symbol_lots_from_form(form) -> dict[str, float]:
    return {
        "XAUUSD": float(form.get("xau_lot") or 0.01),
        "XAGUSD": float(form.get("xag_lot") or 0.01),
        "BTCUSD": float(form.get("btc_lot") or 0.01),
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", _default_context(request))


@app.post("/backtest", response_class=HTMLResponse)
async def backtest_form(request: Request):
    form = await request.form()
    try:
        symbol = str(form.get("symbol") or "XAUUSD")
        req = BacktestRequest(
            symbol=symbol,
            timeframe=str(form.get("timeframe") or "M15"),
            start=date.fromisoformat(str(form.get("start"))),
            end=date.fromisoformat(str(form.get("end"))),
            starting_balance=float(form.get("starting_balance") or 1000),
            lot_size=_lot_for_symbol(symbol, form),
            symbol_lots=_symbol_lots_from_form(form),
            risk_per_trade_percent=float(form.get("risk_per_trade_percent") or 1),
            max_daily_loss_percent=float(form.get("max_daily_loss_percent") or 3),
            max_drawdown_percent=float(form.get("max_drawdown_percent") or 8),
            max_trades_per_day=int(form.get("max_trades_per_day") or 3),
            min_setup_score=int(form.get("min_setup_score") or 90),
            min_risk_reward=float(form.get("min_risk_reward") or 2),
            use_demo_if_mt5_unavailable=str(form.get("use_demo_if_mt5_unavailable") or "") == "on",
        )
        report = run_backtest(req)
        return templates.TemplateResponse(request, "index.html", _default_context(request, result=report, submitted=req))
    except Exception as exc:
        return templates.TemplateResponse(request, "index.html", _default_context(request, error=str(exc)))


@app.post("/api/backtest")
async def api_backtest(request: BacktestRequest):
    report = run_backtest(request)
    return JSONResponse(jsonable_encoder(report))


@app.get("/api/mt5/status")
async def mt5_status():
    return MT5Client().terminal_status()


@app.get("/api/automation/latest")
async def automation_latest():
    if not LATEST_SCAN_PATH.exists():
        return {"status": "empty", "message": "Automation has not produced a scan yet."}
    return JSONResponse(content=json.loads(LATEST_SCAN_PATH.read_text(encoding="utf-8")))


@app.get("/reports/{filename}")
async def download_report(filename: str):
    safe_name = Path(filename).name
    if safe_name != filename:
        raise HTTPException(status_code=400, detail="Invalid report filename.")
    path = REPORTS_DIR / safe_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report not found.")
    media_type = "application/json" if path.suffix.lower() == ".json" else "text/csv"
    return FileResponse(path, media_type=media_type, filename=safe_name)


@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now().isoformat(), "live_trading": load_config().live_trading}
