from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import csv
import json
from pathlib import Path

import pandas as pd

from .config import load_config
from .mt5 import initialize, rates, resolve_symbol, shutdown, symbol_info
from .strategy import analyze_day, atr, load_news_blackouts, simulate_trade


def _metrics(trades, starting_balance: float) -> dict:
    wins = [trade for trade in trades if trade.pnl > 0]
    losses = [trade for trade in trades if trade.pnl < 0]
    gross_profit = sum(trade.pnl for trade in wins)
    gross_loss = abs(sum(trade.pnl for trade in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (
        float("inf") if gross_profit > 0 else 0.0
    )
    ending_balance = trades[-1].balance_after if trades else starting_balance
    equity = [starting_balance] + [trade.balance_after for trade in trades]
    peak = equity[0]
    max_drawdown = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - value) / peak * 100.0)
    return {
        "starting_balance": round(starting_balance, 2),
        "ending_balance": round(ending_balance, 2),
        "net_profit": round(ending_balance - starting_balance, 2),
        "return_percent": round((ending_balance / starting_balance - 1) * 100.0, 2),
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": len(trades) - len(wins) - len(losses),
        "win_rate": round(len(wins) / len(trades) * 100.0, 2) if trades else 0.0,
        "profit_factor": round(profit_factor, 3) if profit_factor != float("inf") else "inf",
        "average_r": round(sum(t.r_multiple for t in trades) / len(trades), 3)
        if trades
        else 0.0,
        "max_drawdown_percent": round(max_drawdown, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
    }


def run() -> dict:
    config = load_config()
    end_date = config.backtest_end or datetime.now(config.timezone).date()
    start_date = config.backtest_start or (end_date - timedelta(days=config.backtest_days))
    start_utc = datetime.combine(start_date - timedelta(days=10), datetime.min.time(), tzinfo=timezone.utc)
    end_utc = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)

    initialize(config)
    try:
        symbol = resolve_symbol(config.symbol)
        info = symbol_info(symbol)
        m5 = rates(symbol, "M5", start_utc, end_utc)
        h1 = rates(symbol, "H1", start_utc - timedelta(days=10), end_utc)
    finally:
        shutdown()
    if m5.empty or h1.empty:
        raise RuntimeError("MT5 history is empty for the selected period.")
    m5["_atr"] = atr(m5)

    news = load_news_blackouts(config.news_blackout_csv, config.timezone)
    local = m5.tz_convert(config.timezone)
    session_dates = sorted(
        day for day in set(local.index.date) if start_date <= day <= end_date
    )

    balance = config.starting_balance
    trades = []
    analyses = []
    for session_date in session_dates:
        analysis = analyze_day(m5, h1, session_date, config, info.point, news)
        analyses.append(analysis)
        if analysis.setup is None:
            continue
        day_frame = m5[m5.index.tz_convert(config.timezone).date == session_date]
        trade = simulate_trade(day_frame, analysis.setup, config, info.point, balance)
        if trade is None:
            analysis.status = "rejected"
            analysis.reason = "entry_stop_not_triggered"
            continue
        balance = trade.balance_after
        trades.append(trade)

    metrics = _metrics(trades, config.starting_balance)
    report = {
        "strategy": "15m ORB + H1 bias + confirmed breakout + retest",
        "symbol_requested": config.symbol,
        "symbol_broker": symbol,
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "data_source": "MetaTrader 5 broker M5/H1 bars",
        "configuration": {
            "timezone": config.timezone_name,
            "opening_range": f"{config.range_start:%H:%M}-{config.range_end:%H:%M}",
            "last_breakout_time": f"{config.last_breakout_time:%H:%M}",
            "h1_min_score": config.h1_min_score,
            "require_vwap": config.require_vwap,
            "min_relative_volume": config.min_relative_volume,
            "allow_double_sweep": config.allow_double_sweep,
            "risk_percent": config.risk_percent,
            "partial": f"{config.partial_percent:.0f}% at {config.partial_r:g}R",
            "runner": f"{config.runner_r:g}R",
            "move_stop_to_be": config.move_sl_to_be,
            "max_trades_per_day": config.max_trades_per_day,
            "spread_limit_points": config.max_spread_points,
            "slippage_points": config.slippage_points,
            "news_blackout_rows": len(news),
        },
        "metrics": metrics,
        "outcomes": dict(Counter(trade.outcome for trade in trades)),
        "directions": dict(Counter(trade.direction for trade in trades)),
        "screening": {
            "sessions_seen": len(analyses),
            "setups_found": sum(analysis.setup is not None for analysis in analyses),
            "reasons": dict(Counter(analysis.reason for analysis in analyses)),
        },
        "trades": [trade.to_dict() for trade in trades],
        "warnings": [
            "Historical news filtering uses data/news_blackouts.csv only.",
            "Intrabar target/stop ambiguity is handled conservatively: stop first.",
            "Backtest uses broker spread plus configured slippage, but not commissions or swaps.",
            "Percentage-risk results assume ideal fractional sizing; live trading blocks an order when the broker minimum lot exceeds the configured risk cap.",
        ],
    }

    reports = config.root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = reports / f"orb_{symbol}_{start_date}_{end_date}_{stamp}.json"
    csv_path = reports / f"orb_{symbol}_{start_date}_{end_date}_{stamp}.csv"
    json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = list(trades[0].to_dict()) if trades else [
            "session_date", "direction", "entry_time", "exit_time", "entry",
            "stop", "tp1", "tp2", "outcome", "r_multiple", "risk_amount",
            "pnl", "balance_after", "spread_points",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(trade.to_dict() for trade in trades)
    report["report_files"] = {"json": str(json_path), "csv": str(csv_path)}
    return report


def main() -> None:
    report = run()
    print(json.dumps({**report["metrics"], **report["screening"], **report["report_files"]}, indent=2))


if __name__ == "__main__":
    main()
