from __future__ import annotations

from datetime import date, datetime, timedelta
import json
from pathlib import Path

import subprocess
import sys

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from .backtester import run_backtest
from .automation import LATEST_SCAN_PATH
from .config import PROJECT_ROOT, REPORTS_DIR, load_config
from .models import ALLOWED_SYMBOLS, ALLOWED_TIMEFRAMES, TRADE_SYMBOLS, BacktestRequest
from .mt5_client import MT5Client
from .system_dashboard import bot_statuses, dashboard_summary, start_bot, stop_bot


app = FastAPI(
    title="LTA A+ Setup Research Platform",
    description="Local FastAPI backtesting UI for LTA Concepts research. Live trading is disabled by default.",
    version="0.1.0",
)

templates = Jinja2Templates(directory=str(PROJECT_ROOT / "app" / "templates"))


def _lot_field(symbol: str) -> str:
    return f"{symbol.lower()}_lot"


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
            "symbol_lots": config.symbol_lots,
            "lot_fields": [
                {"symbol": symbol, "field": _lot_field(symbol), "value": config.symbol_lots[symbol]}
                for symbol in TRADE_SYMBOLS
            ],
            "risk_per_trade_percent": config.max_risk_per_trade_percent,
            "max_daily_loss_percent": config.max_daily_loss_percent,
            "max_drawdown_percent": config.max_total_drawdown_percent,
            "max_trades_per_day": config.max_trades_per_day,
            "min_setup_score": config.min_setup_score,
            "min_risk_reward": config.min_risk_reward,
            "signal_stride": config.backtest_signal_stride,
        },
        "trade_symbols": TRADE_SYMBOLS,
        "live_trading": config.live_trading,
        "mt5_status": MT5Client().terminal_status(),
    }
    context.update(extra)
    return context


def _lot_for_symbol(symbol: str, form) -> float:
    lots = _symbol_lots_from_form(form)
    if symbol == "ALL":
        return lots[TRADE_SYMBOLS[0]]
    return lots.get(symbol, 0.01)


def _symbol_lots_from_form(form) -> dict[str, float]:
    lots: dict[str, float] = {}
    defaults = load_config().symbol_lots
    for symbol in TRADE_SYMBOLS:
        raw_value = form.get(_lot_field(symbol))
        lots[symbol] = float(raw_value or defaults.get(symbol) or 0.01)
    return lots


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", {"request": request})


@app.get("/legacy", response_class=HTMLResponse)
async def legacy_index(request: Request):
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
            min_risk_reward=float(form.get("min_risk_reward") or 5),
            signal_stride=int(form.get("signal_stride") or 3),
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


@app.get("/api/dashboard/summary")
async def api_dashboard_summary():
    return JSONResponse(jsonable_encoder(dashboard_summary()))


@app.get("/api/bots")
async def api_bots():
    return JSONResponse(jsonable_encoder({"bots": bot_statuses()}))


@app.post("/api/bots/{bot_id}/start")
async def api_start_bot(bot_id: str):
    return JSONResponse(jsonable_encoder(start_bot(bot_id)))


@app.post("/api/bots/{bot_id}/stop")
async def api_stop_bot(bot_id: str):
    return JSONResponse(jsonable_encoder(stop_bot(bot_id)))


@app.post("/api/reports/precompute")
async def api_precompute_reports():
    py = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    python = str(py) if py.exists() else sys.executable
    command = [
        python,
        "scripts\\system_backtest.py",
        "--days",
        "365",
        "--balance",
        "300",
        "--risk-pct",
        "5",
    ]
    subprocess.Popen(command, cwd=str(PROJECT_ROOT), close_fds=True)
    return {"ok": True, "message": "Last-year report precompute started. Refresh the dashboard in a few minutes."}


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
