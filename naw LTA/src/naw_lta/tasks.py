from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
from celery.utils.log import get_task_logger
from .celery_app import celery_app
from .database import SessionLocal, init_db
from .engine.backtest import Backtester, in_enabled_session, optimize_symbol
from .engine.indicators import resample_ohlcv
from .engine.profile import VolumeProfile, build_bar_profile
from .engine.strategy import LtaOrderFlowEngine
from .models import BacktestRun, BacktestSymbolResult, ScanSnapshot
from .providers import DatabentoProvider
from .settings import settings
from .services.config_store import get_runtime_config, get_runtime_state, save_runtime_config
from .services.live_data import LiveDataStore
from .services.mt5_execution import MT5Bridge
from .services.paper_execution import create_order_from_signal, reconcile_orders


logger = get_task_logger(__name__)


@celery_app.task(name="naw_lta.scan_market")
def scan_market() -> dict[str, Any]:
    init_db()
    with SessionLocal() as db:
        state = get_runtime_state(db)
        config = get_runtime_config(db)
        if settings.force_live_execution:
            config = config.model_copy(
                update={
                    "execution_mode": "mt5",
                    "mt5_live_orders_enabled": True,
                }
            )
        if not state.worker_enabled:
            return {"status": "disabled"}
        now = datetime.now(timezone.utc)
        if state.last_scan_at:
            last_scan = state.last_scan_at
            if last_scan.tzinfo is None:
                last_scan = last_scan.replace(tzinfo=timezone.utc)
            if (now - last_scan).total_seconds() < config.scan_interval_seconds:
                return {"status": "not_due"}
        state.last_scan_status = "running"
        state.last_error = None
        db.commit()
        try:
            provider = DatabentoProvider(config.dataset)
            store = LiveDataStore(provider)
            engine = LtaOrderFlowEngine(config)
            decisions: list[dict] = []
            for symbol, symbol_config in config.symbols.items():
                if not symbol_config.enabled:
                    continue
                order = None
                basis = 0.0
                if config.execution_mode == "mt5":
                    with MT5Bridge() as bridge:
                        raw_bars = bridge.bars(symbol_config.mt5_symbol)
                        historical = provider.bars(
                            symbol_config.provider_symbol,
                            now - timedelta(days=config.profile_lookback_days + 3),
                            now,
                        )
                        composite_profile = build_bar_profile(
                            historical.tail(config.profile_lookback_days * 24 * 60),
                            config.profile_bins,
                            config.value_area_percent,
                        )
                        basis = _overlap_basis(historical, raw_bars)
                        basis_bps = abs(basis) / max(float(raw_bars.iloc[-1]["close"]), 1e-9) * 10_000
                        if basis_bps > config.max_basis_bps:
                            raise RuntimeError(
                                f"CME/MT5 basis is {basis_bps:.1f} bps for {symbol}, above the "
                                f"{config.max_basis_bps:.1f} bps safety limit."
                            )
                        composite_profile = _shift_profile(composite_profile, basis)
                        bars = resample_ohlcv(raw_bars, config.signal_timeframe_minutes)
                        decision = engine.evaluate(
                            symbol, bars, profile_override=composite_profile
                        )
                        bridge.reconcile(db, config, symbol_config)
                        if in_enabled_session(pd.Timestamp(now), config, symbol):
                            order = bridge.place(
                                db, decision, config, symbol_config, basis
                            )
                else:
                    raw_bars = store.bars(
                        symbol_config.provider_symbol, config.profile_lookback_days
                    )
                    bars = resample_ohlcv(raw_bars, config.signal_timeframe_minutes)
                    trades = (
                        store.recent_trades(symbol_config.provider_symbol, minutes=180)
                        if config.use_trade_tape_profile
                        else None
                    )
                    depth = (
                        store.recent_depth(symbol_config.provider_symbol)
                        if config.use_order_book
                        else None
                    )
                    profile_bars = raw_bars.tail(config.profile_lookback_days * 24 * 60)
                    composite_profile = build_bar_profile(
                        profile_bars, config.profile_bins, config.value_area_percent
                    )
                    decision = engine.evaluate(
                        symbol,
                        bars,
                        trades=trades,
                        depth=depth,
                        profile_override=composite_profile,
                    )
                    candle = raw_bars.iloc[-1].to_dict()
                    reconcile_orders(db, symbol, candle, config)
                    if (
                        config.execution_mode == "paper"
                        and in_enabled_session(pd.Timestamp(now), config, symbol)
                    ):
                        order = create_order_from_signal(db, decision, config)
                payload = decision.to_dict()
                payload["candles"] = _candles(raw_bars.tail(240))
                payload["created_order_id"] = order.id if order else None
                payload["cme_mt5_basis"] = basis
                payload["market_data_mode"] = (
                    "MT5 live + Databento historical profile"
                    if config.execution_mode == "mt5"
                    else "Databento historical/delayed"
                )
                db.add(
                    ScanSnapshot(
                        symbol=symbol,
                        timestamp=now,
                        price=float(raw_bars.iloc[-1]["close"]),
                        score=decision.score,
                        direction=decision.direction,
                        regime=decision.regime,
                        status=decision.status,
                        payload=payload,
                    )
                )
                db.commit()
                decisions.append(payload)
            state.last_scan_at = now
            state.last_scan_status = "complete"
            state.updated_at = now
            db.commit()
            return {"status": "complete", "symbols": len(decisions), "decisions": decisions}
        except Exception as exc:
            logger.exception("Market scan failed")
            state.last_scan_status = "error"
            state.last_error = str(exc)
            state.updated_at = now
            db.commit()
            return {"status": "error", "error": str(exc)}


@celery_app.task(name="naw_lta.run_backtest")
def run_backtest(run_id: int) -> dict[str, Any]:
    init_db()
    with SessionLocal() as db:
        run = db.get(BacktestRun, run_id)
        if run is None:
            return {"status": "missing", "run_id": run_id}
        run.status = "running"
        db.commit()
        try:
            config = get_runtime_config(db)
            provider = DatabentoProvider(config.dataset)
            start = datetime.fromisoformat(run.start_date).replace(tzinfo=timezone.utc)
            end = datetime.fromisoformat(run.end_date).replace(tzinfo=timezone.utc) + timedelta(days=1)
            data_start = start - timedelta(days=config.profile_lookback_days + 2)
            aggregate_results: list[dict] = []
            optimized = deepcopy(config)
            for symbol in run.symbols:
                symbol_config = config.symbols[symbol]
                estimated_cost = provider.estimated_uncached_bars_cost(
                    symbol_config.provider_symbol, data_start, min(end, datetime.now(timezone.utc))
                )
                if estimated_cost is None:
                    raise RuntimeError(
                        f"Could not estimate the Databento cost for {symbol}; no data was downloaded."
                    )
                if estimated_cost > config.max_data_cost_usd:
                    raise RuntimeError(
                        f"Databento estimate for {symbol} is ${estimated_cost:.2f}, above the "
                        f"${config.max_data_cost_usd:.2f} safety cap."
                    )
                bars = provider.bars(symbol_config.provider_symbol, data_start, end)
                if run.config_snapshot.get("optimize"):
                    best_config, result = optimize_symbol(
                        symbol, bars, config, run.starting_balance, test_start=start
                    )
                    optimized.symbols[symbol] = best_config.symbols[symbol]
                else:
                    result = Backtester(config).run_symbol(
                        symbol, bars, run.starting_balance, test_start=start
                    )
                db.add(
                    BacktestSymbolResult(
                        run_id=run.id,
                        symbol=symbol,
                        metrics=result["metrics"],
                        monthly=result["monthly"],
                        trades=result["trades"],
                        equity=result["equity"],
                    )
                )
                db.commit()
                aggregate_results.append(result)
            if run.config_snapshot.get("optimize"):
                save_runtime_config(db, optimized)
            run.aggregate = _aggregate(aggregate_results, run.starting_balance)
            run.status = "complete"
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
            return {"status": "complete", "run_id": run.id, "aggregate": run.aggregate}
        except Exception as exc:
            logger.exception("Backtest %s failed", run_id)
            run.status = "error"
            run.error = str(exc)
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
            return {"status": "error", "run_id": run.id, "error": str(exc)}


def _candles(frame) -> list[dict]:
    result = []
    for timestamp, row in frame.iterrows():
        result.append(
            {
                "time": int(timestamp.timestamp()),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume", 0.0)),
            }
        )
    return result


def _aggregate(results: list[dict], starting_balance: float) -> dict:
    if not results:
        return {}
    metrics = [result["metrics"] for result in results]
    best = max(metrics, key=lambda item: item["return_percent"])
    worst = min(metrics, key=lambda item: item["return_percent"])
    return {
        "symbols": len(results),
        "starting_balance_per_symbol": starting_balance,
        "average_return_percent": round(
            sum(item["return_percent"] for item in metrics) / len(metrics), 2
        ),
        "total_net_profit_independent_accounts": round(
            sum(item["net_profit"] for item in metrics), 2
        ),
        "total_trades": sum(item["trades"] for item in metrics),
        "best_return_percent": best["return_percent"],
        "worst_return_percent": worst["return_percent"],
        "note": "Each symbol is tested independently from the same starting balance.",
    }


def _overlap_basis(historical, mt5_bars) -> float:
    timestamp = historical.index[-1]
    location = mt5_bars.index.get_indexer([timestamp], method="nearest", tolerance=pd.Timedelta("5min"))[0]
    if location < 0:
        raise RuntimeError("MT5 does not have a bar overlapping the latest cached CME minute.")
    return float(mt5_bars.iloc[location]["close"] - historical.iloc[-1]["close"])


def _shift_profile(profile: VolumeProfile, basis: float) -> VolumeProfile:
    return VolumeProfile(
        poc=profile.poc + basis,
        vah=profile.vah + basis,
        val=profile.val + basis,
        hvns=[level + basis for level in profile.hvns],
        lvns=[level + basis for level in profile.lvns],
        total_volume=profile.total_volume,
        source=f"{profile.source}+mt5_basis",
    )
