from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
import hashlib
import json
from pathlib import Path
import time as time_module
from typing import Any

import numpy as np
import pandas as pd

from .config import REPORTS_DIR
from .models import TRADE_SYMBOLS, BacktestReport, BacktestRequest, Signal, TradeResult, model_to_dict
from .mt5_client import MT5Client, generate_demo_candles
from .risk_manager import RiskManager
from .strategy_engine import generate_signal


BACKTEST_CACHE_DIR = REPORTS_DIR / "backtest_cache"
BACKTEST_CACHE_VERSION = "2026-06-18-rr5-weekly-expanded-symbols-v1"
LIVE_CACHE_SECONDS = 180


def _date_bounds(request: BacktestRequest) -> tuple[datetime, datetime]:
    start = datetime.combine(request.start, time.min)
    end = datetime.combine(request.end, time.max)
    if end <= start:
        end = start + timedelta(days=1)
    return start, end


def _cache_path(request: BacktestRequest) -> Path:
    payload = model_to_dict(request)
    payload["cache_version"] = BACKTEST_CACHE_VERSION
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return BACKTEST_CACHE_DIR / f"{digest}.json"


def _cache_is_fresh(path: Path, request: BacktestRequest) -> bool:
    if request.end < date.today():
        return True
    age = time_module.time() - path.stat().st_mtime
    return age <= LIVE_CACHE_SECONDS


def _read_cached_report(request: BacktestRequest) -> BacktestReport | None:
    path = _cache_path(request)
    if not path.exists() or not _cache_is_fresh(path, request):
        return None
    report = BacktestReport.model_validate_json(path.read_text(encoding="utf-8"))
    report.warnings = list(dict.fromkeys([*report.warnings, "Loaded from the recent backtest cache."]))
    return report


def _write_cached_report(request: BacktestRequest, report: BacktestReport) -> None:
    BACKTEST_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(request).write_text(json.dumps(model_to_dict(report), indent=2, default=str), encoding="utf-8")


def _load_candles(request: BacktestRequest, mt5_client: MT5Client) -> tuple[pd.DataFrame, str, list[str]]:
    start, end = _date_bounds(request)
    warnings: list[str] = []
    candles = mt5_client.fetch_candles(request.symbol, request.timeframe, start, end)
    if candles is not None and len(candles) >= 120:
        return candles, "MT5", warnings

    if request.use_demo_if_mt5_unavailable:
        warnings.append("MT5 candles were unavailable, so this run used deterministic demo candles.")
        return generate_demo_candles(request.symbol, request.timeframe, start, end), "DEMO", warnings

    warnings.append("MT5 candles were unavailable and demo fallback was disabled.")
    return pd.DataFrame(), "NONE", warnings


def _simulate_trade(candles: pd.DataFrame, start_index: int, signal: dict[str, Any], max_holding_bars: int = 96) -> tuple[int, float, str, datetime]:
    direction = signal["direction"]
    entry = float(signal["entry"])
    stop = float(signal["stop_loss"])
    target = float(signal["take_profit"])
    end_index = min(len(candles) - 1, start_index + max_holding_bars)

    for idx in range(start_index + 1, end_index + 1):
        row = candles.iloc[idx]
        high = float(row["high"])
        low = float(row["low"])
        if direction == "BUY":
            hit_stop = low <= stop
            hit_target = high >= target
        else:
            hit_stop = high >= stop
            hit_target = low <= target

        # Conservative same-candle handling: stop is counted first.
        if hit_stop:
            return idx, stop, "loss", pd.Timestamp(row["time"]).to_pydatetime()
        if hit_target:
            return idx, target, "win", pd.Timestamp(row["time"]).to_pydatetime()

    row = candles.iloc[end_index]
    return end_index, float(row["close"]), "timeout", pd.Timestamp(row["time"]).to_pydatetime()


def _write_reports(report: BacktestReport) -> BacktestReport:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = f"{report.symbol}_{report.timeframe}_{stamp}"
    json_path = REPORTS_DIR / f"{base}.json"
    csv_path = REPORTS_DIR / f"{base}.csv"

    data = model_to_dict(report)
    data["json_report"] = json_path.name
    data["csv_report"] = csv_path.name
    json_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    trade_rows = [model_to_dict(t) for t in report.trades]
    if trade_rows:
        pd.DataFrame(trade_rows).to_csv(csv_path, index=False)
    else:
        pd.DataFrame(columns=["opened_at", "closed_at", "symbol", "direction", "entry", "exit_price", "pnl"]).to_csv(
            csv_path, index=False
        )

    report.json_report = json_path.name
    report.csv_report = csv_path.name
    return report


def _report_stats(trades: list[TradeResult]) -> dict[str, Any]:
    wins = sum(1 for t in trades if t.result == "win")
    losses = sum(1 for t in trades if t.result == "loss")
    timeouts = sum(1 for t in trades if t.result == "timeout")
    total = len(trades)
    win_rate = (wins / total * 100) if total else 0.0
    average_rr = sum((abs(t.take_profit - t.entry) / max(abs(t.entry - t.stop_loss), 1e-9)) for t in trades) / total if total else 0.0
    average_r = sum(t.r_multiple for t in trades) / total if total else 0.0
    gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
    gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
    profit_factor = gross_profit / gross_loss if gross_loss else (gross_profit if gross_profit else 0.0)
    winning_pnls = [t.pnl for t in trades if t.pnl > 0]
    losing_pnls = [t.pnl for t in trades if t.pnl < 0]
    average_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0.0
    average_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0.0
    r_values = np.array([t.r_multiple for t in trades], dtype=float)
    sharpe = float((r_values.mean() / r_values.std()) * np.sqrt(max(len(r_values), 1))) if len(r_values) > 1 and r_values.std() > 0 else 0.0
    return {
        "wins": wins,
        "losses": losses,
        "timeouts": timeouts,
        "total": total,
        "win_rate": win_rate,
        "average_risk_reward": average_rr,
        "average_r_multiple": average_r,
        "profit_factor": profit_factor,
        "average_win": average_win,
        "average_loss": average_loss,
        "sharpe_ratio": sharpe,
        "best_trade": max((t.pnl for t in trades), default=None),
        "worst_trade": min((t.pnl for t in trades), default=None),
    }


def _run_single_backtest(request: BacktestRequest, write_report: bool = True) -> BacktestReport:
    mt5_client = MT5Client()
    candles, data_source, warnings = _load_candles(request, mt5_client)
    if candles.empty:
        report = BacktestReport(
            symbol=request.symbol,
            timeframe=request.timeframe,
            start=request.start,
            end=request.end,
            data_source=data_source,
            starting_balance=request.starting_balance,
            ending_balance=request.starting_balance,
            net_profit=0.0,
            win_rate=0.0,
            total_trades=0,
            wins=0,
            losses=0,
            timeouts=0,
            max_drawdown=0.0,
            average_risk_reward=0.0,
            average_r_multiple=0.0,
            best_trade=None,
            worst_trade=None,
            a_plus_setups_taken=0,
            setups_rejected=0,
            rejected_reason_breakdown={},
            trades=[],
            rejected_setups=[],
            warnings=warnings,
        )
        return _write_reports(report) if write_report else report

    contract_size = mt5_client.contract_size(request.symbol) if data_source == "MT5" else None
    risk = RiskManager(
        symbol=request.symbol,
        lot_size=request.lot_size,
        starting_balance=request.starting_balance,
        max_risk_percent=request.risk_per_trade_percent,
        max_daily_loss_percent=request.max_daily_loss_percent,
        max_drawdown_percent=request.max_drawdown_percent,
        max_trades_per_day=request.max_trades_per_day,
        min_setup_score=request.min_setup_score,
        min_risk_reward=request.min_risk_reward,
        contract_size=contract_size,
    )

    balance = request.starting_balance
    equity_peak = balance
    equity_curve: list[float] = [round(float(balance), 2)]
    max_drawdown = 0.0
    daily_pnl: dict[Any, float] = defaultdict(float)
    daily_trades: dict[Any, int] = defaultdict(int)
    trades: list[TradeResult] = []
    rejected: list[Signal] = []
    reason_counter: Counter[str] = Counter()
    signal_stride = max(1, int(request.signal_stride))

    i = max(120, min(240, len(candles) // 5))
    while i < len(candles) - 2:
        history = candles.iloc[: i + 1]
        signal = generate_signal(
            history,
            symbol=request.symbol,
            timeframe=request.timeframe,
            min_score=request.min_setup_score,
            min_rr=request.min_risk_reward,
        )
        if signal is None:
            i += signal_stride
            continue

        signal_day = risk.day_key(pd.Timestamp(signal["timestamp"]).to_pydatetime())
        if signal["status"] != "allowed":
            rejected_signal = Signal(**signal)
            rejected.append(rejected_signal)
            for reason in signal.get("reasons", [])[:3]:
                reason_counter[reason] += 1
            i += signal_stride
            continue

        decision = risk.approve(signal, balance, equity_peak, daily_pnl[signal_day], daily_trades[signal_day])
        if not decision.approved:
            rejected_signal = Signal(**{**signal, "status": "rejected", "reasons": decision.reasons})
            rejected.append(rejected_signal)
            for reason in decision.reasons:
                reason_counter[reason] += 1
            i += signal_stride
            continue

        exit_index, exit_price, result, closed_at = _simulate_trade(candles, i, signal)
        pnl = risk.pnl(signal["direction"], float(signal["entry"]), exit_price)
        balance += pnl
        equity_curve.append(round(float(balance), 2))
        equity_peak = max(equity_peak, balance)
        drawdown = 0.0 if equity_peak <= 0 else (equity_peak - balance) / equity_peak * 100
        max_drawdown = max(max_drawdown, drawdown)
        daily_pnl[signal_day] += pnl
        daily_trades[signal_day] += 1
        risk_amount = max(decision.risk_amount, 1e-9)
        r_multiple = pnl / risk_amount

        trades.append(
            TradeResult(
                opened_at=pd.Timestamp(signal["timestamp"]).to_pydatetime(),
                closed_at=closed_at,
                symbol=request.symbol,
                timeframe=request.timeframe,
                direction=signal["direction"],
                entry=float(signal["entry"]),
                stop_loss=float(signal["stop_loss"]),
                take_profit=float(signal["take_profit"]),
                exit_price=float(exit_price),
                result=result,
                pnl=round(float(pnl), 2),
                r_multiple=round(float(r_multiple), 2),
                balance_after=round(float(balance), 2),
                setup_score=int(signal["setup_score"]),
                setup_grade=signal["setup_grade"],
                key_level=signal["key_level"] or "",
                entry_model=signal["entry_model"] or "",
                reasons=signal["reasons"],
            )
        )
        i = max(exit_index + 1, i + signal_stride)

    stats = _report_stats(trades)

    report = BacktestReport(
        symbol=request.symbol,
        timeframe=request.timeframe,
        start=request.start,
        end=request.end,
        data_source=data_source,
        starting_balance=round(request.starting_balance, 2),
        ending_balance=round(balance, 2),
        net_profit=round(balance - request.starting_balance, 2),
        total_return_percent=round(((balance - request.starting_balance) / request.starting_balance) * 100, 2),
        win_rate=round(stats["win_rate"], 2),
        total_trades=stats["total"],
        wins=stats["wins"],
        losses=stats["losses"],
        timeouts=stats["timeouts"],
        max_drawdown=round(max_drawdown, 2),
        profit_factor=round(stats["profit_factor"], 2),
        average_win=round(stats["average_win"], 2),
        average_loss=round(stats["average_loss"], 2),
        average_risk_reward=round(stats["average_risk_reward"], 2),
        average_r_multiple=round(stats["average_r_multiple"], 2),
        sharpe_ratio=round(stats["sharpe_ratio"], 2),
        best_trade=round(stats["best_trade"], 2) if stats["best_trade"] is not None else None,
        worst_trade=round(stats["worst_trade"], 2) if stats["worst_trade"] is not None else None,
        a_plus_setups_taken=sum(1 for t in trades if t.setup_grade == "A+"),
        setups_rejected=len(rejected),
        rejected_reason_breakdown=dict(reason_counter.most_common()),
        equity_curve=equity_curve,
        trades=trades,
        rejected_setups=rejected[-100:],
        warnings=warnings,
    )
    return _write_reports(report) if write_report else report


def _symbol_lot(request: BacktestRequest, symbol: str) -> float:
    lot = request.symbol_lots.get(symbol, request.lot_size)
    return float(lot or request.lot_size or 0.01)


def _portfolio_report(request: BacktestRequest) -> BacktestReport:
    reports: list[BacktestReport] = []
    warnings: list[str] = [
        f"All-symbol mode aggregates {', '.join(TRADE_SYMBOLS)} into one research dashboard using each symbol's configured lot."
    ]
    if request.signal_stride > 1:
        warnings.append(f"Fast mode scanned every {request.signal_stride} candles. Set scan step to 1 for the slow full scan.")

    for symbol in TRADE_SYMBOLS:
        symbol_request = request.model_copy(
            update={
                "symbol": symbol,
                "lot_size": _symbol_lot(request, symbol),
            }
        )
        reports.append(_run_single_backtest(symbol_request, write_report=False))

    all_trades = sorted((trade for report in reports for trade in report.trades), key=lambda trade: trade.opened_at)
    balance = request.starting_balance
    equity_peak = balance
    max_drawdown = 0.0
    equity_curve = [round(float(balance), 2)]
    combined_trades: list[TradeResult] = []

    for trade in all_trades:
        balance += trade.pnl
        equity_peak = max(equity_peak, balance)
        drawdown = 0.0 if equity_peak <= 0 else (equity_peak - balance) / equity_peak * 100
        max_drawdown = max(max_drawdown, drawdown)
        equity_curve.append(round(float(balance), 2))
        combined_trades.append(trade.model_copy(update={"balance_after": round(float(balance), 2)}))

    rejected = sorted(
        (setup for report in reports for setup in report.rejected_setups if setup.timestamp is not None),
        key=lambda setup: setup.timestamp,
    )[-150:]
    reason_counter: Counter[str] = Counter()
    for report in reports:
        reason_counter.update(report.rejected_reason_breakdown)
        warnings.extend(report.warnings)

    stats = _report_stats(combined_trades)
    data_sources = {report.data_source for report in reports}
    data_source = data_sources.pop() if len(data_sources) == 1 else "MIXED"
    net_profit = balance - request.starting_balance

    symbol_summaries = [
        {
            "symbol": report.symbol,
            "data_source": report.data_source,
            "lot_size": _symbol_lot(request, report.symbol),
            "total_trades": report.total_trades,
            "a_plus_setups_taken": report.a_plus_setups_taken,
            "setups_rejected": report.setups_rejected,
            "net_profit": report.net_profit,
            "total_return_percent": round((report.net_profit / request.starting_balance) * 100, 2),
            "win_rate": report.win_rate,
            "max_drawdown": report.max_drawdown,
            "best_trade": report.best_trade,
            "worst_trade": report.worst_trade,
        }
        for report in reports
    ]

    report = BacktestReport(
        symbol="ALL",
        timeframe=request.timeframe,
        start=request.start,
        end=request.end,
        data_source=data_source,
        starting_balance=round(request.starting_balance, 2),
        ending_balance=round(balance, 2),
        net_profit=round(net_profit, 2),
        total_return_percent=round((net_profit / request.starting_balance) * 100, 2),
        win_rate=round(stats["win_rate"], 2),
        total_trades=stats["total"],
        wins=stats["wins"],
        losses=stats["losses"],
        timeouts=stats["timeouts"],
        max_drawdown=round(max_drawdown, 2),
        profit_factor=round(stats["profit_factor"], 2),
        average_win=round(stats["average_win"], 2),
        average_loss=round(stats["average_loss"], 2),
        average_risk_reward=round(stats["average_risk_reward"], 2),
        average_r_multiple=round(stats["average_r_multiple"], 2),
        sharpe_ratio=round(stats["sharpe_ratio"], 2),
        best_trade=round(stats["best_trade"], 2) if stats["best_trade"] is not None else None,
        worst_trade=round(stats["worst_trade"], 2) if stats["worst_trade"] is not None else None,
        a_plus_setups_taken=sum(report.a_plus_setups_taken for report in reports),
        setups_rejected=sum(report.setups_rejected for report in reports),
        rejected_reason_breakdown=dict(reason_counter.most_common()),
        equity_curve=equity_curve,
        symbol_summaries=symbol_summaries,
        trades=combined_trades,
        rejected_setups=rejected,
        warnings=list(dict.fromkeys(warnings)),
    )
    return _write_reports(report)


def run_backtest(request: BacktestRequest) -> BacktestReport:
    cached = _read_cached_report(request)
    if cached:
        return cached

    if request.symbol == "ALL":
        report = _portfolio_report(request)
    else:
        report = _run_single_backtest(request, write_report=True)
        if request.signal_stride > 1:
            report.warnings = list(
                dict.fromkeys(
                    [
                        *report.warnings,
                        f"Fast mode scanned every {request.signal_stride} candles. Set scan step to 1 for the slow full scan.",
                    ]
                )
            )
    _write_cached_report(request, report)
    return report
