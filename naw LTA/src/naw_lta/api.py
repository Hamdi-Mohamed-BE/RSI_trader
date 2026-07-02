from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from .database import get_db
from .models import BacktestRun, OrderRecord, ScanSnapshot
from .schemas import BacktestRequest, ConfigEnvelope, RuntimeConfig
from .services.config_store import get_runtime_config, get_runtime_state, save_runtime_config
from .settings import settings
from .tasks import run_backtest, scan_market


router = APIRouter(prefix="/api")


@router.get("/config", response_model=ConfigEnvelope)
def read_config(db: Session = Depends(get_db)) -> ConfigEnvelope:
    return ConfigEnvelope(
        config=get_runtime_config(db),
        databento_key_configured=bool(settings.databento_api_key),
    )


@router.put("/config", response_model=ConfigEnvelope)
def update_config(config: RuntimeConfig, db: Session = Depends(get_db)) -> ConfigEnvelope:
    saved = save_runtime_config(db, config)
    return ConfigEnvelope(config=saved, databento_key_configured=bool(settings.databento_api_key))


@router.get("/worker")
def worker_status(db: Session = Depends(get_db)) -> dict:
    state = get_runtime_state(db)
    return {
        "enabled": state.worker_enabled,
        "last_scan_at": state.last_scan_at,
        "status": state.last_scan_status,
        "error": state.last_error,
        "databento_key_configured": bool(settings.databento_api_key),
    }


@router.post("/worker/{action}")
def set_worker(action: str, db: Session = Depends(get_db)) -> dict:
    if action not in {"start", "stop", "scan"}:
        raise HTTPException(status_code=400, detail="Action must be start, stop, or scan.")
    state = get_runtime_state(db)
    if action == "start":
        if not settings.databento_api_key:
            raise HTTPException(status_code=409, detail="Configure DATABENTO_API_KEY first.")
        state.worker_enabled = True
        state.last_scan_status = "queued"
        db.commit()
        task = scan_market.delay()
        return {"enabled": True, "task_id": task.id}
    if action == "stop":
        state.worker_enabled = False
        state.last_scan_status = "disabled"
        db.commit()
        return {"enabled": False}
    if not settings.databento_api_key:
        raise HTTPException(status_code=409, detail="Configure DATABENTO_API_KEY first.")
    task = scan_market.delay()
    return {"enabled": state.worker_enabled, "task_id": task.id}


@router.get("/scans")
def latest_scans(db: Session = Depends(get_db)) -> list[dict]:
    subquery = (
        select(ScanSnapshot.symbol, func.max(ScanSnapshot.id).label("max_id"))
        .group_by(ScanSnapshot.symbol)
        .subquery()
    )
    rows = db.scalars(
        select(ScanSnapshot)
        .join(subquery, ScanSnapshot.id == subquery.c.max_id)
        .order_by(ScanSnapshot.symbol)
    ).all()
    return [_scan_dict(row) for row in rows]


@router.get("/scans/{symbol}")
def latest_symbol_scan(symbol: str, db: Session = Depends(get_db)) -> dict:
    row = db.scalar(
        select(ScanSnapshot)
        .where(ScanSnapshot.symbol == symbol.upper())
        .order_by(desc(ScanSnapshot.id))
        .limit(1)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="No scan is available for this symbol.")
    return _scan_dict(row)


@router.get("/orders")
def orders(limit: int = 100, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(OrderRecord).order_by(desc(OrderRecord.id)).limit(min(limit, 500))).all()
    return [
        {
            "id": row.id,
            "symbol": row.symbol,
            "strategy": row.strategy,
            "side": row.side,
            "order_type": row.order_type,
            "status": row.status,
            "entry": row.entry,
            "stop_loss": row.stop_loss,
            "take_profit": row.take_profit,
            "quantity": row.quantity,
            "risk_amount": row.risk_amount,
            "score": row.score,
            "opened_at": row.opened_at,
            "closed_at": row.closed_at,
            "pnl": row.pnl,
            "metadata": row.metadata_json,
        }
        for row in rows
    ]


@router.post("/backtests")
def create_backtest(request: BacktestRequest, db: Session = Depends(get_db)) -> dict:
    if not settings.databento_api_key:
        raise HTTPException(status_code=409, detail="Configure DATABENTO_API_KEY first.")
    start, end = _period_dates(request)
    config = get_runtime_config(db)
    run = BacktestRun(
        status="queued",
        period=request.period,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        starting_balance=request.starting_balance,
        symbols=request.symbols,
        config_snapshot={
            **config.model_dump(mode="json"),
            "optimize": request.optimize,
        },
    )
    db.add(run)
    db.commit()
    task = run_backtest.delay(run.id)
    run.celery_task_id = task.id
    db.commit()
    return {"id": run.id, "task_id": task.id, "status": run.status}


@router.get("/backtests")
def list_backtests(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(BacktestRun).order_by(desc(BacktestRun.id)).limit(50)).all()
    return [_run_dict(row, include_results=False) for row in rows]


@router.get("/backtests/{run_id}")
def get_backtest(run_id: int, db: Session = Depends(get_db)) -> dict:
    run = db.scalar(
        select(BacktestRun)
        .options(selectinload(BacktestRun.results))
        .where(BacktestRun.id == run_id)
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Backtest not found.")
    return _run_dict(run, include_results=True)


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)) -> dict:
    state = get_runtime_state(db)
    latest = latest_scans(db)
    order_rows = orders(30, db)
    closed_today = [
        row for row in order_rows
        if row["closed_at"] and row["closed_at"].date() == datetime.now(timezone.utc).date()
    ]
    return {
        "worker": {
            "enabled": state.worker_enabled,
            "status": state.last_scan_status,
            "last_scan_at": state.last_scan_at,
            "error": state.last_error,
        },
        "summary": {
            "symbols_watched": len(latest),
            "a_plus_setups": sum(1 for row in latest if row["status"] == "A_PLUS"),
            "open_orders": sum(1 for row in order_rows if row["status"] in {"OPEN", "PENDING"}),
            "today_pnl": round(sum(row["pnl"] or 0.0 for row in closed_today), 2),
        },
        "scans": latest,
        "orders": order_rows,
    }


def _period_dates(request: BacktestRequest) -> tuple[date, date]:
    end = date.fromisoformat(request.end_date) if request.end_date else date.today()
    if request.period == "1m":
        return end - timedelta(days=30), end
    if request.period == "6m":
        return end - timedelta(days=183), end
    if not request.start_date:
        raise HTTPException(status_code=422, detail="start_date is required for a custom test.")
    return date.fromisoformat(request.start_date), end


def _scan_dict(row: ScanSnapshot) -> dict:
    return {
        "id": row.id,
        "symbol": row.symbol,
        "timestamp": row.timestamp,
        "price": row.price,
        "score": row.score,
        "direction": row.direction,
        "regime": row.regime,
        "status": row.status,
        "payload": row.payload,
    }


def _run_dict(run: BacktestRun, include_results: bool) -> dict:
    result = {
        "id": run.id,
        "task_id": run.celery_task_id,
        "status": run.status,
        "period": run.period,
        "start_date": run.start_date,
        "end_date": run.end_date,
        "starting_balance": run.starting_balance,
        "symbols": run.symbols,
        "aggregate": run.aggregate,
        "error": run.error,
        "created_at": run.created_at,
        "completed_at": run.completed_at,
    }
    if include_results:
        result["results"] = [
            {
                "symbol": row.symbol,
                "metrics": row.metrics,
                "monthly": row.monthly,
                "trades": row.trades,
                "equity": row.equity,
            }
            for row in run.results
        ]
    return result
