from __future__ import annotations

from dataclasses import asdict, replace
from datetime import date, datetime, time, timedelta
import argparse
import json
import math
import os
from pathlib import Path
from typing import Any

import pandas as pd

from .config import REPORTS_DIR, load_config
from .mt5_client import MT5Client
from .sats_strategy import SatsSettings, simulate_sats_three_leg_trades, simulate_sats_trades


REPORT_DIR = REPORTS_DIR / "sats_backtest"
CACHE_DIR = REPORT_DIR / "cache"


def _parse_csv(value: str | None, cast, defaults: tuple) -> tuple:
    if not value:
        return defaults
    parsed = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            parsed.append(cast(item))
        except ValueError:
            continue
    return tuple(parsed) or defaults


def _cache_path(symbol: str, timeframe: str, start: date, end: date) -> Path:
    safe = symbol.replace("/", "_").replace("\\", "_")
    return CACHE_DIR / f"{safe}_{timeframe}_{start.isoformat()}_{end.isoformat()}.pkl"


def fetch_history(
    client: MT5Client,
    symbol: str,
    timeframe: str,
    start: date,
    end: date,
    refresh: bool = False,
) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(symbol, timeframe, start, end)
    resolved = client.resolve_symbol(symbol)
    info = client.symbol_info(symbol) if resolved else None
    meta = {
        "symbol": symbol,
        "timeframe": timeframe,
        "broker_symbol": resolved,
        "point": float((info or {}).get("point") or 0.01),
        "digits": int((info or {}).get("digits") or 2),
    }
    if not resolved:
        return None, {**meta, "status": "symbol_unavailable"}
    if path.exists() and not refresh:
        frame = pd.read_pickle(path)
        return frame, {**meta, "status": "cache", "bars": len(frame)}

    start_dt = datetime.combine(start, time.min)
    end_dt = datetime.combine(end + timedelta(days=1), time.min)
    frame = client.fetch_candles(symbol, timeframe, start_dt, end_dt, max_bars=200000)
    if frame is None or frame.empty:
        return None, {**meta, "status": "no_history"}
    frame.to_pickle(path)
    return frame, {
        **meta,
        "status": "mt5",
        "bars": len(frame),
        "first": str(frame.iloc[0]["time"]),
        "last": str(frame.iloc[-1]["time"]),
        "volume_source": str(frame.iloc[-1].get("volume_source") or "unknown"),
    }


def _apply_spread_costs(trades: list[dict[str, Any]], candles: pd.DataFrame, point: float, multiplier: float) -> list[dict[str, Any]]:
    if not trades or candles.empty or multiplier <= 0:
        return trades
    by_time = {str(row["time"]): row for _, row in candles.iterrows()}
    adjusted: list[dict[str, Any]] = []
    for trade in trades:
        row = by_time.get(str(trade["entry_time"]))
        spread_points = float(row.get("spread") or 0.0) if row is not None else 0.0
        spread_distance = spread_points * float(point) * multiplier
        risk_distance = abs(float(trade["entry"]) - float(trade["stop_loss"]))
        spread_r = spread_distance / risk_distance if risk_distance > 0 else 0.0
        item = dict(trade)
        item["raw_r_multiple"] = float(item["r_multiple"])
        item["spread_r_cost"] = spread_r
        item["r_multiple"] = float(item["r_multiple"]) - spread_r
        adjusted.append(item)
    return adjusted


def _portfolio_result(
    trades: list[dict[str, Any]],
    start: date,
    end: date,
    starting_balance: float,
    risk_percent: float,
) -> dict[str, Any]:
    balance = float(starting_balance)
    peak = balance
    max_drawdown = 0.0
    rows: list[dict[str, Any]] = []
    equity = [{"time": str(start), "balance": balance}]

    for trade in sorted(trades, key=lambda item: str(item["exit_time"])):
        risk_fraction = float(trade.get("risk_fraction") or 1.0)
        risk_cash = balance * (risk_percent / 100.0) * risk_fraction
        pnl = risk_cash * float(trade["r_multiple"])
        before = balance
        balance += pnl
        peak = max(peak, balance)
        drawdown = (peak - balance) / peak * 100.0 if peak > 0 else 0.0
        max_drawdown = max(max_drawdown, drawdown)
        rows.append({**trade, "balance_before": before, "risk_cash": risk_cash, "pnl": pnl, "balance_after": balance})
        equity.append({"time": str(trade["exit_time"]), "balance": balance})

    wins = [item for item in rows if float(item["pnl"]) > 0]
    losses = [item for item in rows if float(item["pnl"]) < 0]
    gross_profit = sum(float(item["pnl"]) for item in wins)
    gross_loss = abs(sum(float(item["pnl"]) for item in losses))
    idea_ids = {
        str(item.get("idea_id"))
        for item in rows
        if item.get("idea_id") is not None
    }
    return {
        "start": str(start),
        "end": str(end),
        "starting_balance": starting_balance,
        "ending_balance": balance,
        "net_profit": balance - starting_balance,
        "return_percent": (balance / starting_balance - 1.0) * 100.0 if starting_balance > 0 else 0.0,
        "max_drawdown_percent": max_drawdown,
        "trades": len(rows),
        "ideas": len(idea_ids) if idea_ids else len(rows),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_percent": len(wins) / len(rows) * 100.0 if rows else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0),
        "total_r": sum(float(item["r_multiple"]) for item in rows),
        "average_r": sum(float(item["r_multiple"]) for item in rows) / len(rows) if rows else 0.0,
        "trade_rows": rows,
        "equity_curve": equity,
    }


def _summary(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key not in {"trade_rows", "equity_curve"}}


def _score_result(result: dict[str, Any]) -> float:
    if int(result["trades"]) < 3:
        return -1e9
    return (
        float(result["return_percent"])
        + float(result["average_r"]) * 10.0
        + min(5.0, max(0.0, float(result["profit_factor"]) - 1.0))
        - float(result["max_drawdown_percent"]) * 0.25
    )


def _env_settings() -> SatsSettings:
    tp_mode = os.getenv("SATS_TP_MODE", "Fixed")
    if tp_mode.lower() not in {"fixed", "dynamic"}:
        tp_mode = "Fixed"
    return SatsSettings(
        min_score=float(os.getenv("SATS_MIN_SCORE", "60") or 60),
        min_tqi=float(os.getenv("SATS_MIN_TQI", "0.35") or 0.35),
        tp_mode=tp_mode,
        trade_timeout_bars=int(os.getenv("SATS_TRADE_TIMEOUT_BARS", "100") or 100),
    )


def run_backtest(
    symbols: tuple[str, ...],
    days: int = 60,
    starting_balance: float = 300.0,
    timeframes: tuple[str, ...] = ("M15", "M30", "H1"),
    score_values: tuple[float, ...] = (40.0, 60.0, 80.0),
    tqi_values: tuple[float, ...] = (0.35, 0.50, 0.70),
    tp_modes: tuple[str, ...] = ("Fixed", "Dynamic"),
    entry_mode: str = "SINGLE_AVERAGED",
    refresh: bool = False,
) -> dict[str, Any]:
    config = load_config()
    end = date.today()
    start = end - timedelta(days=max(1, days))
    history_start = start - timedelta(days=35)
    risk_percent = float(os.getenv("SATS_RISK_PERCENT", str(config.max_lot_risk_pct)) or config.max_lot_risk_pct)
    spread_multiplier = float(os.getenv("SATS_SPREAD_MULTIPLIER", os.getenv("BACKTEST_SPREAD_MULTIPLIER", "1.0")) or 1.0)
    entry_mode = entry_mode.strip().upper()
    if entry_mode not in {"SINGLE_AVERAGED", "THREE_LEG_SPLIT"}:
        entry_mode = "SINGLE_AVERAGED"

    client = MT5Client()
    histories: dict[tuple[str, str], pd.DataFrame] = {}
    metadata: dict[tuple[str, str], dict[str, Any]] = {}
    availability: list[dict[str, Any]] = []
    for symbol in symbols:
        for timeframe in timeframes:
            frame, meta = fetch_history(client, symbol, timeframe, history_start, end, refresh=refresh)
            availability.append(meta)
            if frame is not None and len(frame) >= 300:
                histories[(symbol, timeframe)] = frame
                metadata[(symbol, timeframe)] = meta
    client.shutdown()
    if not histories:
        raise RuntimeError("No MT5 history was available for the requested SATS symbols/timeframes.")

    base_settings = _env_settings()
    grid_rows: list[dict[str, Any]] = []
    trade_sets: dict[tuple[str, str, float, float, str], list[dict[str, Any]]] = {}
    for (symbol, timeframe), frame in histories.items():
        for min_score in score_values:
            for min_tqi in tqi_values:
                for tp_mode in tp_modes:
                    settings = replace(base_settings, min_score=float(min_score), min_tqi=float(min_tqi), tp_mode=tp_mode)
                    if entry_mode == "THREE_LEG_SPLIT":
                        trades, _signal_frame = simulate_sats_three_leg_trades(frame, symbol, settings)
                    else:
                        trades, _signal_frame = simulate_sats_trades(frame, symbol, settings)
                    trades = [
                        item
                        for item in trades
                        if pd.Timestamp(item["entry_time"]).date() >= start
                        and pd.Timestamp(item["entry_time"]).date() <= end
                    ]
                    trades = _apply_spread_costs(trades, frame, float(metadata[(symbol, timeframe)]["point"]), spread_multiplier)
                    key = (symbol, timeframe, float(min_score), float(min_tqi), tp_mode)
                    trade_sets[key] = trades
                    result = _portfolio_result(trades, start, end, starting_balance, risk_percent)
                    grid_rows.append(
                        {
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "min_score": min_score,
                            "min_tqi": min_tqi,
                            "tp_mode": tp_mode,
                            "selection_score": _score_result(result),
                            **_summary(result),
                        }
                    )

    grid_rows.sort(key=lambda item: (float(item["selection_score"]), float(item["return_percent"])), reverse=True)
    best_per_symbol: list[dict[str, Any]] = []
    selected_trades: list[dict[str, Any]] = []
    for symbol in symbols:
        candidates = [item for item in grid_rows if item["symbol"] == symbol]
        if not candidates:
            continue
        best = candidates[0]
        best_per_symbol.append(best)
        key = (symbol, best["timeframe"], float(best["min_score"]), float(best["min_tqi"]), best["tp_mode"])
        selected_trades.extend(trade_sets.get(key, []))

    combined = _portfolio_result(selected_trades, start, end, starting_balance, risk_percent)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = REPORT_DIR / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(grid_rows).to_csv(out_dir / "optimization_grid.csv", index=False)
    pd.DataFrame(best_per_symbol).to_csv(out_dir / "best_per_symbol.csv", index=False)
    pd.DataFrame(combined["trade_rows"]).to_csv(out_dir / "combined_trades.csv", index=False)
    pd.DataFrame(combined["equity_curve"]).to_csv(out_dir / "combined_equity.csv", index=False)
    report = {
        "strategy": "Self-Aware Trend System [WillyAlgoTrader] Python SATS port",
        "notes": [
            "Visual dashboard and experimental self-learning state are not ported.",
            "Signals use completed MT5 candles, adaptive SuperTrend flips, TQI, score/TQI filters, ATR stops, TP ladder, flip exits, timeout exits, and spread-cost R adjustment.",
            "Optimization is in-sample over the requested period; treat this as research, not a production guarantee.",
        ],
        "requested": {
            "symbols": list(symbols),
            "days": days,
            "start": str(start),
            "end": str(end),
            "starting_balance": starting_balance,
            "risk_percent_per_trade": risk_percent,
            "timeframes": list(timeframes),
            "score_values": list(score_values),
            "tqi_values": list(tqi_values),
            "tp_modes": list(tp_modes),
            "spread_multiplier": spread_multiplier,
            "entry_mode": entry_mode,
        },
        "availability": availability,
        "best_per_symbol": best_per_symbol,
        "combined_best_per_symbol_result": _summary(combined),
        "top_configs": grid_rows[:20],
        "output_directory": str(out_dir),
    }
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    (out_dir / "summary.md").write_text(_markdown(report), encoding="utf-8")
    return report


def _markdown(report: dict[str, Any]) -> str:
    result = report["combined_best_per_symbol_result"]
    lines = [
        "# SATS Backtest Report",
        "",
        f"Period: {report['requested']['start']} to {report['requested']['end']}",
        f"Starting balance: ${report['requested']['starting_balance']:.2f}",
        f"Risk per trade: {report['requested']['risk_percent_per_trade']:.2f}%",
        f"Entry mode: {report['requested'].get('entry_mode', 'SINGLE_AVERAGED')}",
        "",
        "## Combined Best Per Symbol",
        "",
        f"- Ending balance: ${result['ending_balance']:.2f}",
        f"- Return: {result['return_percent']:.2f}%",
        f"- Trades: {result['trades']}",
        f"- Ideas: {result.get('ideas', result['trades'])}",
        f"- Win rate: {result['win_rate_percent']:.2f}%",
        f"- Max drawdown: {result['max_drawdown_percent']:.2f}%",
        f"- Profit factor: {result['profit_factor']:.2f}" if math.isfinite(float(result["profit_factor"])) else "- Profit factor: inf",
        "",
        "## Best Per Symbol",
        "",
    ]
    for row in report["best_per_symbol"]:
        lines.append(
            f"- {row['symbol']}: {row['timeframe']}, score>={row['min_score']}, "
            f"TQI>={row['min_tqi']}, {row['tp_mode']} TP, "
            f"{row['trades']} trades, {row['return_percent']:.2f}% return, "
            f"{row['max_drawdown_percent']:.2f}% DD"
        )
    lines.extend(
        [
            "",
            "This is an in-sample optimization over the requested period. Use forward demo testing before live use.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest the Self-Aware Trend System SATS port on MT5 symbols.")
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--balance", type=float, default=300.0)
    parser.add_argument("--symbols", default="BTCUSD,XAUUSD,US30,US100")
    parser.add_argument("--timeframes", default="M15,M30,H1")
    parser.add_argument("--scores", default="40,60,80")
    parser.add_argument("--tqi", default="0.35,0.5,0.7")
    parser.add_argument("--tp-modes", default="Fixed,Dynamic")
    parser.add_argument("--entry-mode", default="SINGLE_AVERAGED", choices=["SINGLE_AVERAGED", "THREE_LEG_SPLIT"])
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    report = run_backtest(
        symbols=tuple(item.strip().upper() for item in args.symbols.split(",") if item.strip()),
        days=args.days,
        starting_balance=args.balance,
        timeframes=tuple(item.strip().upper() for item in args.timeframes.split(",") if item.strip()),
        score_values=_parse_csv(args.scores, float, (0.0, 40.0, 60.0, 80.0)),
        tqi_values=_parse_csv(args.tqi, float, (0.0, 0.35, 0.5, 0.7)),
        tp_modes=tuple(item.strip().title() for item in args.tp_modes.split(",") if item.strip()),
        entry_mode=args.entry_mode,
        refresh=args.refresh,
    )
    result = report["combined_best_per_symbol_result"]
    print(f"SATS report: {report['output_directory']}")
    print(
        f"Combined: ${result['starting_balance']:.2f} -> ${result['ending_balance']:.2f} "
        f"({result['return_percent']:.2f}%), trades={result['trades']}, "
        f"WR={result['win_rate_percent']:.2f}%, DD={result['max_drawdown_percent']:.2f}%"
    )
    for row in report["best_per_symbol"]:
        print(
            f"{row['symbol']}: {row['timeframe']} score>={row['min_score']} "
            f"TQI>={row['min_tqi']} {row['tp_mode']} "
            f"return={row['return_percent']:.2f}% trades={row['trades']} DD={row['max_drawdown_percent']:.2f}%"
        )


if __name__ == "__main__":
    main()
