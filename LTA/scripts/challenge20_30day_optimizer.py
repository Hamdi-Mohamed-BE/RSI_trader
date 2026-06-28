from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import date, datetime, time, timedelta
import itertools
import json
import math
import os
from pathlib import Path
import sys
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
for path in (ROOT, SCRIPT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.config import REPORTS_DIR, load_config
from app.mt5_client import MT5Client
from app.orb_strategy import ORBSettings
from app.pip_utils import parse_pip_size_map, pip_size_for
from app.session_time import DEFAULT_DATA_TIMEZONE, date_in_timezone
from orb_backtest import ORBTrade, normalize_candles, session_parts, simulate_orb_day


DEFAULT_SYMBOLS = (
    "AUDUSD",
    "EURUSD",
    "GBPUSD",
    "USDCAD",
    "USDCHF",
    "NZDUSD",
    "US100",
)
SESSIONS = {
    "Asia": ("19:00", "02:00"),
    "London": ("03:00", "12:00"),
    "NewYork": ("08:00", "17:00"),
    "NYCash": ("09:30", "16:00"),
}


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def parse_csv(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value:
        return default
    return tuple(item.strip().upper() for item in value.split(",") if item.strip())


def level_for_balance(balance: float, start_balance: float, target_percent: float, levels: int) -> int:
    if balance <= start_balance:
        return 1
    running = start_balance
    level = 1
    multiplier = 1 + target_percent / 100
    while level < levels and balance >= running * multiplier:
        running *= multiplier
        level += 1
    return level


def lot_for_risk(row: dict[str, Any], balance: float, risk_fraction: float) -> tuple[float, float]:
    requested = balance * risk_fraction
    risk_per_lot = float(row.get("risk_per_lot") or 0.0)
    lot_min = float(row.get("lot_min") or 0.01)
    lot_max = float(row.get("lot_max") or 100.0)
    lot_step = float(row.get("lot_step") or 0.01)
    if risk_per_lot <= 0 or lot_step <= 0:
        return 0.0, requested
    raw_lot = requested / risk_per_lot
    if raw_lot < lot_min:
        lot = lot_min
    else:
        steps = math.floor((min(raw_lot, lot_max) - lot_min + 1e-12) / lot_step)
        lot = min(lot_max, lot_min + steps * lot_step)
    return lot, risk_per_lot * lot


def simulate_portfolio(
    rows: list[dict[str, Any]],
    window_start: datetime,
    window_end: datetime,
    priority: tuple[str, ...],
    max_trades_per_day: int,
    max_open_positions: int,
    later_trade_min_score: int,
    start_balance: float,
    risk_percent: float,
    target_percent: float,
    levels: int,
) -> dict[str, Any]:
    priority_rank = {symbol: index for index, symbol in enumerate(priority)}
    selected_symbols = set(priority)
    entries = [
        row
        for row in rows
        if row["symbol"] in selected_symbols and window_start <= row["opened_at"] <= window_end
    ]
    entries.sort(
        key=lambda row: (
            row["opened_at"],
            priority_rank.get(row["symbol"], 999),
            -int(row.get("setup_score") or 0),
        )
    )
    target_balance = start_balance * ((1 + target_percent / 100) ** levels)
    balance = start_balance
    peak = balance
    max_drawdown = 0.0
    open_trades: list[dict[str, Any]] = []
    daily_counts: dict[str, int] = {}
    completed: list[dict[str, Any]] = []
    reached_at: datetime | None = None

    def settle(until: datetime) -> None:
        nonlocal balance, peak, max_drawdown, reached_at, open_trades
        closing = sorted(
            [trade for trade in open_trades if trade["closed_at"] <= until],
            key=lambda trade: (trade["closed_at"], priority_rank.get(trade["symbol"], 999)),
        )
        for trade in closing:
            if trade not in open_trades:
                continue
            before = balance
            pnl = float(trade["actual_risk"]) * float(trade["r_multiple"])
            balance = max(0.0, balance + pnl)
            peak = max(peak, balance)
            max_drawdown = max(max_drawdown, (peak - balance) / peak if peak else 0.0)
            completed.append(
                {
                    **trade,
                    "balance_before_close": before,
                    "pnl": pnl,
                    "balance_after": balance,
                }
            )
            open_trades.remove(trade)
            if reached_at is None and balance >= target_balance:
                reached_at = trade["closed_at"]

    for row in entries:
        settle(row["opened_at"])
        if reached_at is not None or balance <= 0:
            break
        day_key = row["opened_at"].date().isoformat()
        count = daily_counts.get(day_key, 0)
        if count >= max_trades_per_day:
            continue
        if count >= 1 and int(row.get("setup_score") or 0) < later_trade_min_score:
            continue
        if len(open_trades) >= max_open_positions:
            continue
        if any(trade["symbol"] == row["symbol"] for trade in open_trades):
            continue
        lot, actual_risk = lot_for_risk(row, balance, risk_percent / 100)
        if lot <= 0 or actual_risk <= 0:
            continue
        open_trades.append({**row, "lot": lot, "actual_risk": actual_risk})
        daily_counts[day_key] = count + 1

    settle(window_end)
    wins = sum(1 for trade in completed if trade["result"] == "win")
    losses = sum(1 for trade in completed if trade["result"] == "loss")
    return {
        "start_balance": round(start_balance, 2),
        "final_balance": round(balance, 2),
        "return_pct": round((balance / start_balance - 1) * 100, 2),
        "target_balance": round(target_balance, 2),
        "passed": reached_at is not None,
        "reached_at": reached_at.isoformat() if reached_at else None,
        "level": level_for_balance(balance, start_balance, target_percent, levels),
        "trades": len(completed),
        "wins": wins,
        "losses": losses,
        "timeouts": len(completed) - wins - losses,
        "win_rate": round(wins / len(completed) * 100, 2) if completed else 0.0,
        "max_drawdown_pct": round(max_drawdown * 100, 2),
    }


def candidate_priorities(symbol_scores: list[tuple[str, float]], limit: int = 5) -> list[tuple[str, ...]]:
    pool = tuple(symbol for symbol, _ in symbol_scores[:limit])
    priorities: set[tuple[str, ...]] = set()
    for length in range(1, min(4, len(pool)) + 1):
        priorities.update(itertools.permutations(pool[:4], length))
    if len(pool) >= 5:
        priorities.update((*order, pool[4]) for order in itertools.permutations(pool[:4]))
    return sorted(priorities)


def rolling_windows(start_day: date, end_day: date, step_days: int = 7) -> list[tuple[datetime, datetime]]:
    windows: list[tuple[datetime, datetime]] = []
    cursor = start_day
    while cursor + timedelta(days=29) <= end_day:
        finish = cursor + timedelta(days=29)
        windows.append((datetime.combine(cursor, time.min), datetime.combine(finish, time.max)))
        cursor += timedelta(days=step_days)
    latest_start = end_day - timedelta(days=29)
    latest = (datetime.combine(latest_start, time.min), datetime.combine(end_day, time.max))
    if latest not in windows:
        windows.append(latest)
    return windows


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimize a literal 20 Pip Challenge for 30-calendar-day windows.")
    parser.add_argument("--start", default=None, help="History start YYYY-MM-DD. Default: end minus 182 days.")
    parser.add_argument("--end", default=None, help="History end YYYY-MM-DD. Default: today.")
    parser.add_argument("--symbols", default=None)
    parser.add_argument("--sessions", default=None, help="Comma-separated session names.")
    parser.add_argument("--ranges", default=None, help="Comma-separated opening-range minutes.")
    parser.add_argument("--stops", default=None, help="Comma-separated fixed SL pips.")
    parser.add_argument("--risk-percent", type=float, default=None)
    parser.add_argument("--top", type=int, default=30)
    args = parser.parse_args()

    load_config()
    end_day = date.fromisoformat(args.end) if args.end else date.today()
    start_day = date.fromisoformat(args.start) if args.start else end_day - timedelta(days=182)
    history_start = datetime.combine(start_day, time.min)
    history_end = datetime.combine(end_day, time.max)
    fetch_start = history_start - timedelta(days=7)
    symbols = parse_csv(args.symbols, DEFAULT_SYMBOLS)
    timeframe = "M15"
    timeframe_minutes = 15
    start_balance = float(os.getenv("CHALLENGE20_START_BALANCE", "20") or 20)
    risk_percent = (
        float(args.risk_percent)
        if args.risk_percent is not None
        else float(os.getenv("CHALLENGE20_RISK_PERCENT", "23") or 23)
    )
    target_percent = float(os.getenv("CHALLENGE20_TARGET_PERCENT", "30") or 30)
    levels = int(os.getenv("CHALLENGE20_LEVELS", "30") or 30)
    take_profit_pips = 20.0
    pip_sizes = parse_pip_size_map(os.getenv("CHALLENGE20_SYMBOL_PIP_SIZE"))
    pip_sizes["US100"] = 4.0
    windows = rolling_windows(start_day, end_day)
    latest_window = windows[-1]

    client = MT5Client()
    status = client.terminal_status()
    log(f"MT5: {status.get('message')}")
    log(f"History: {start_day} to {end_day}; {len(windows)} rolling 30-day windows")
    market: dict[str, dict[str, Any]] = {}
    for symbol in symbols:
        broker = client.resolve_symbol(symbol)
        candles = client.fetch_candles(symbol, timeframe, fetch_start, history_end, max_bars=50000) if broker else None
        if candles is None or len(candles) < 120:
            log(f"{symbol}: unavailable")
            continue
        info = client.symbol_info(symbol) or {}
        market[symbol] = {
            "broker": broker,
            "frame": normalize_candles(candles),
            "contract_size": client.contract_size(symbol),
            "point": float(info.get("point") or 0.0),
            "digits": int(info.get("digits") or 0),
            "constraints": client.lot_constraints(symbol),
        }
        log(f"{symbol}: {len(candles)} candles as {broker}")

    base_results: list[dict[str, Any]] = []
    stop_values = tuple(float(item) for item in args.stops.split(",")) if args.stops else (15.0, 15.4, 16.0, 18.0, 20.0)
    range_values = tuple(int(item) for item in args.ranges.split(",")) if args.ranges else (15, 30, 60)
    requested_sessions = {item.strip().lower() for item in args.sessions.split(",")} if args.sessions else None
    sessions = {
        name: value
        for name, value in SESSIONS.items()
        if requested_sessions is None or name.lower() in requested_sessions
    }
    allowed_weekdays = {"MON", "TUE", "WED", "THU", "FRI"}

    for session_name, (session_start, session_end) in sessions.items():
        for range_minutes in range_values:
            for stop_loss_pips in stop_values:
                settings = ORBSettings(
                    session_start=session_start,
                    session_end=session_end,
                    range_minutes=range_minutes,
                    reward_risk=take_profit_pips / stop_loss_pips,
                    buffer_atr=0.0,
                    min_range_atr=0.0,
                    max_range_atr=999.0,
                    session_timezone="America/New_York",
                    data_timezone=os.getenv("MARKET_DATA_TIMEZONE", DEFAULT_DATA_TIMEZONE),
                )
                rows: list[dict[str, Any]] = []
                for symbol, data in market.items():
                    frame = data["frame"]
                    days = sorted(
                        {
                            date_in_timezone(
                                pd.Timestamp(value).to_pydatetime(),
                                settings.data_timezone,
                                settings.session_timezone,
                            )
                            for value in frame["time"]
                        }
                    )
                    days = [
                        day
                        for day in days
                        if start_day <= day <= end_day and day.strftime("%a").upper()[:3] in allowed_weekdays
                    ]
                    pip_size = pip_size_for(
                        symbol,
                        point=data["point"],
                        digits=data["digits"],
                        overrides=pip_sizes,
                    )
                    constraints = data["constraints"]
                    for session_day in days:
                        bounds = session_parts(session_day, settings)
                        day_frame = frame[(frame["time"] >= bounds[0]) & (frame["time"] <= bounds[2])].reset_index(drop=True)
                        prior = frame[frame["time"] < bounds[0]].tail(64).reset_index(drop=True)
                        result = simulate_orb_day(
                            frame,
                            symbol,
                            session_day,
                            settings,
                            take_profit_pips / stop_loss_pips,
                            1.0,
                            float(data["contract_size"]),
                            timeframe_minutes=timeframe_minutes,
                            day_candles=day_frame,
                            prior_candles=prior,
                            fixed_stop_distance=pip_size * stop_loss_pips,
                            fixed_target_distance=pip_size * take_profit_pips,
                            point_size=data["point"],
                        )
                        if not isinstance(result, ORBTrade):
                            continue
                        row = asdict(result)
                        row["opened_at"] = datetime.fromisoformat(row["opened_at"])
                        row["closed_at"] = datetime.fromisoformat(row["closed_at"])
                        if not (history_start <= row["opened_at"] <= history_end):
                            continue
                        risk = client.estimate_trade_risk(
                            symbol,
                            row["direction"],
                            1.0,
                            float(row["entry"]),
                            float(row["stop_loss"]),
                        )
                        row["risk_per_lot"] = float(risk.get("risk") or 0.0)
                        row["lot_min"] = float(constraints.get("min") or 0.01)
                        row["lot_max"] = float(constraints.get("max") or 100.0)
                        row["lot_step"] = float(constraints.get("step") or 0.01)
                        range_atr = row.get("range_atr")
                        row["setup_score"] = 100 if range_atr is not None and 0.5 <= float(range_atr) <= 2.0 else 95
                        rows.append(row)

                if not rows:
                    continue
                symbol_scores: list[tuple[str, float]] = []
                for symbol in market:
                    symbol_rows = [row for row in rows if row["symbol"] == symbol]
                    if not symbol_rows:
                        continue
                    result = simulate_portfolio(
                        symbol_rows,
                        history_start,
                        history_end,
                        (symbol,),
                        1,
                        1,
                        100,
                        start_balance,
                        risk_percent,
                        target_percent,
                        levels,
                    )
                    symbol_scores.append((symbol, float(result["final_balance"])))
                symbol_scores.sort(key=lambda item: item[1], reverse=True)

                candidates: list[dict[str, Any]] = []
                for priority in candidate_priorities(symbol_scores):
                    for max_trades in range(1, min(5, len(priority)) + 1):
                        for later_score in (95, 100):
                            latest = simulate_portfolio(
                                rows,
                                latest_window[0],
                                latest_window[1],
                                priority,
                                max_trades,
                                max_trades,
                                later_score,
                                start_balance,
                                risk_percent,
                                target_percent,
                                levels,
                            )
                            candidates.append(
                                {
                                    "priority": priority,
                                    "max_trades_per_day": max_trades,
                                    "max_open_positions": max_trades,
                                    "later_trade_min_score": later_score,
                                    "latest": latest,
                                }
                            )
                candidates.sort(
                    key=lambda item: (
                        bool(item["latest"]["passed"]),
                        float(item["latest"]["final_balance"]),
                        -float(item["latest"]["max_drawdown_pct"]),
                    ),
                    reverse=True,
                )
                for candidate in candidates[:3]:
                    rolling = [
                        simulate_portfolio(
                            rows,
                            window_start,
                            window_end,
                            tuple(candidate["priority"]),
                            int(candidate["max_trades_per_day"]),
                            int(candidate["max_open_positions"]),
                            int(candidate["later_trade_min_score"]),
                            start_balance,
                            risk_percent,
                            target_percent,
                            levels,
                        )
                        for window_start, window_end in windows
                    ]
                    finals = sorted(float(item["final_balance"]) for item in rolling)
                    candidate.update(
                        {
                            "session": session_name,
                            "session_start": session_start,
                            "session_end": session_end,
                            "range_minutes": range_minutes,
                            "take_profit_pips": take_profit_pips,
                            "stop_loss_pips": stop_loss_pips,
                            "symbols_ranked": symbol_scores,
                            "rolling_passes": sum(1 for item in rolling if item["passed"]),
                            "rolling_windows": len(rolling),
                            "rolling_median_final": round(finals[len(finals) // 2], 2),
                            "rolling_worst_final": round(finals[0], 2),
                            "rolling_best_final": round(finals[-1], 2),
                            "rolling": rolling,
                        }
                    )
                    base_results.append(candidate)
                log(
                    f"{session_name} range={range_minutes} SL={stop_loss_pips:g}: "
                    f"latest best ${candidates[0]['latest']['final_balance']:,.2f}"
                )

    client.shutdown()
    base_results.sort(
        key=lambda item: (
            int(item["rolling_passes"]),
            float(item["rolling_median_final"]),
            float(item["latest"]["final_balance"]),
            -float(item["latest"]["max_drawdown_pct"]),
        ),
        reverse=True,
    )
    latest_ranked = sorted(
        base_results,
        key=lambda item: (
            bool(item["latest"]["passed"]),
            float(item["latest"]["final_balance"]),
            -float(item["latest"]["max_drawdown_pct"]),
        ),
        reverse=True,
    )
    passers = [item for item in base_results if int(item["rolling_passes"]) > 0]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = REPORTS_DIR / "20pip_30day_optimizer" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "history_start": start_day.isoformat(),
        "history_end": end_day.isoformat(),
        "window_days": 30,
        "rolling_window_count": len(windows),
        "start_balance": start_balance,
        "risk_percent": risk_percent,
        "target_percent": target_percent,
        "levels": levels,
        "target_balance": round(start_balance * ((1 + target_percent / 100) ** levels), 2),
        "symbols": list(market),
        "sessions": sessions,
        "tested_ranges": list(range_values),
        "tested_stop_losses": list(stop_values),
        "take_profit_pips": take_profit_pips,
        "passer_count": len(passers),
        "best_robust": base_results[0] if base_results else None,
        "best_latest": latest_ranked[0] if latest_ranked else None,
        "top_robust": base_results[: max(1, args.top)],
        "top_latest": latest_ranked[: max(1, args.top)],
    }
    report_path = out_dir / "challenge20_30day_optimization.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(
        json.dumps(
            {
                "report": str(report_path),
                "passer_count": len(passers),
                "best_robust": report["best_robust"],
                "best_latest": report["best_latest"],
            },
            indent=2,
            default=str,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
