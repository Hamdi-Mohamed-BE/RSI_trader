from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import date, datetime, time, timedelta
import json
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
from app.mt5_client import MT5Client, TIMEFRAME_MINUTES
from app.orb_strategy import ORBSettings
from app.session_time import DEFAULT_DATA_TIMEZONE, DEFAULT_SESSION_TIMEZONE, date_in_timezone
from orb_backtest import ORBTrade, normalize_candles, session_parts, simulate_orb_day


DEFAULT_SYMBOLS = (
    "XAUUSD",
    "XAGUSD",
    "BTCUSD",
    "US30",
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCHF",
    "USDCAD",
    "AUDUSD",
    "NZDUSD",
)


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def parse_csv(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value:
        return default
    return tuple(item.strip().upper() for item in value.split(",") if item.strip())


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def level_for_balance(balance: float, start_balance: float, target_percent: float, max_levels: int) -> int:
    if balance <= start_balance:
        return 1
    level = 1
    target_multiplier = 1 + target_percent / 100
    running = start_balance
    while level < max_levels and balance >= running * target_multiplier:
        running *= target_multiplier
        level += 1
    return level


def compound_challenge(
    rows: pd.DataFrame,
    start_balance: float,
    risk_percent: float,
    target_percent: float,
    max_levels: int,
) -> tuple[dict[str, Any], pd.DataFrame]:
    risk_fraction = risk_percent / 100
    final_target = start_balance * ((1 + target_percent / 100) ** max_levels)
    balance = start_balance
    peak = balance
    min_balance = balance
    max_drawdown = 0.0
    reached_at: str | None = None
    equity_rows: list[dict[str, Any]] = []

    if rows.empty:
        return (
            {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "timeouts": 0,
                "win_rate": 0.0,
                "net_r": 0.0,
                "start_balance": round(start_balance, 2),
                "final_balance": round(balance, 2),
                "level": 1,
                "target_balance": round(final_target, 2),
                "target_reached": False,
                "target_reached_at": None,
                "max_drawdown_pct": 0.0,
                "min_balance": round(min_balance, 2),
            },
            pd.DataFrame(),
        )

    for _, row in rows.sort_values(["opened_at", "symbol"]).iterrows():
        r_multiple = float(row["r_multiple"])
        before = balance
        balance = max(0.0, balance * (1 + risk_fraction * r_multiple))
        peak = max(peak, balance)
        min_balance = min(min_balance, balance)
        max_drawdown = max(max_drawdown, (peak - balance) / peak if peak > 0 else 0.0)
        level = level_for_balance(balance, start_balance, target_percent, max_levels)
        equity_rows.append(
            {
                "date": row["date"],
                "opened_at": row["opened_at"],
                "closed_at": row["closed_at"],
                "symbol": row["symbol"],
                "direction": row["direction"],
                "result": row["result"],
                "r_multiple": round(r_multiple, 4),
                "balance_before": round(before, 2),
                "balance_after": round(balance, 2),
                "level_after": level,
            }
        )
        if reached_at is None and balance >= final_target:
            reached_at = str(row["closed_at"])
            break

    total = int(len(equity_rows))
    used = pd.DataFrame(equity_rows)
    summary = {
        "trades": total,
        "wins": int(sum(1 for item in equity_rows if item["result"] == "win")),
        "losses": int(sum(1 for item in equity_rows if item["result"] == "loss")),
        "timeouts": int(sum(1 for item in equity_rows if item["result"] == "timeout")),
        "win_rate": round((int(sum(1 for item in equity_rows if item["result"] == "win")) / total) * 100, 2)
        if total
        else 0.0,
        "net_r": round(float(used["r_multiple"].sum()), 2) if total else 0.0,
        "start_balance": round(start_balance, 2),
        "final_balance": round(balance, 2),
        "level": level_for_balance(balance, start_balance, target_percent, max_levels),
        "target_balance": round(final_target, 2),
        "target_reached": reached_at is not None,
        "target_reached_at": reached_at,
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "min_balance": round(min_balance, 2),
    }
    return summary, pd.DataFrame(equity_rows)


def one_open_trade_at_a_time(rows: pd.DataFrame, symbol_order: dict[str, int]) -> pd.DataFrame:
    if rows.empty:
        return rows.copy()
    selected = []
    flat_at = pd.Timestamp.min
    ranked = rows.assign(rank=rows["symbol"].map(symbol_order).fillna(999))
    for _, row in ranked.sort_values(["opened_at", "rank", "closed_at"]).iterrows():
        if row["opened_at"] >= flat_at:
            selected.append(row.drop(labels=["rank"]))
            flat_at = row["closed_at"]
    return pd.DataFrame(selected)


def one_trade_per_day(rows: pd.DataFrame, symbol_order: dict[str, int]) -> pd.DataFrame:
    if rows.empty:
        return rows.copy()
    selected = []
    ranked = rows.assign(rank=rows["symbol"].map(symbol_order).fillna(999))
    for _, group in ranked.sort_values(["opened_at", "rank", "closed_at"]).groupby("date"):
        selected.append(group.iloc[0].drop(labels=["rank"]))
    return pd.DataFrame(selected)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest 20 Pip Challenge progression using ORB entries.")
    parser.add_argument("--symbols", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--start", default=None)
    parser.add_argument("--days", type=int, default=61, help="Used when --start is omitted. Default is about two months.")
    parser.add_argument("--start-balance", type=float, default=None)
    parser.add_argument("--risk-percent", type=float, default=None)
    parser.add_argument("--target-percent", type=float, default=None)
    parser.add_argument("--levels", type=int, default=None)
    parser.add_argument("--session-start", default=None)
    parser.add_argument("--session-end", default=None)
    parser.add_argument("--session-timezone", default=None)
    parser.add_argument("--data-timezone", default=None)
    parser.add_argument("--range-minutes", type=int, default=None)
    parser.add_argument("--timeframe", default=None)
    args = parser.parse_args()

    load_config()
    env_symbols = parse_csv(os.getenv("CHALLENGE20_SYMBOLS") or os.getenv("ORB_SYMBOLS"), DEFAULT_SYMBOLS)
    symbols = parse_csv(args.symbols, env_symbols)
    end_day = date.fromisoformat(args.end) if args.end else date.today()
    start_day = date.fromisoformat(args.start) if args.start else end_day - timedelta(days=max(1, args.days))
    start = datetime.combine(start_day, time.min)
    end = datetime.combine(end_day, time.max)
    fetch_start = start - timedelta(days=7)

    start_balance = args.start_balance if args.start_balance is not None else env_float("CHALLENGE20_START_BALANCE", 20.0)
    risk_percent = args.risk_percent if args.risk_percent is not None else env_float("CHALLENGE20_RISK_PERCENT", 23.0)
    target_percent = args.target_percent if args.target_percent is not None else env_float("CHALLENGE20_TARGET_PERCENT", 30.0)
    max_levels = args.levels if args.levels is not None else env_int("CHALLENGE20_LEVELS", 30)
    reward_risk = target_percent / risk_percent if risk_percent > 0 else 0.0

    settings = ORBSettings(
        session_start=args.session_start or os.getenv("ORB_SESSION_START", "09:30"),
        session_end=args.session_end or os.getenv("ORB_SESSION_END", "16:00"),
        range_minutes=max(1, args.range_minutes or env_int("ORB_RANGE_MINUTES", 15)),
        reward_risk=max(0.5, reward_risk),
        buffer_atr=max(0.0, env_float("ORB_BREAK_BUFFER_ATR", 0.0)),
        min_range_atr=max(0.0, env_float("ORB_MIN_RANGE_ATR", 0.0)),
        max_range_atr=max(0.0, env_float("ORB_MAX_RANGE_ATR", 999.0)),
        session_timezone=args.session_timezone or os.getenv("ORB_SESSION_TIMEZONE", DEFAULT_SESSION_TIMEZONE),
        data_timezone=args.data_timezone or os.getenv("MARKET_DATA_TIMEZONE", DEFAULT_DATA_TIMEZONE),
    )
    timeframe = (args.timeframe or os.getenv("CHALLENGE20_ORB_TIMEFRAME") or os.getenv("ORB_TIMEFRAME", "M15")).upper()
    timeframe_minutes = TIMEFRAME_MINUTES.get(timeframe, 15)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = REPORTS_DIR / "20pip_challenge_backtest" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    client = MT5Client()
    status = client.terminal_status()
    log(f"MT5 status: {status.get('message')}")
    log(f"Window: {start_day} to {end_day}")
    log(
        f"Challenge: start=${start_balance:g}, risk={risk_percent:g}%, target={target_percent:g}% "
        f"({reward_risk:.2f}R)"
    )
    log(
        f"ORB: {settings.range_minutes}m, {settings.session_start}-{settings.session_end} "
        f"{settings.session_timezone}, timeframe={timeframe}"
    )
    log(f"Symbols: {', '.join(symbols)}")

    trades: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    availability: list[dict[str, Any]] = []

    for symbol in symbols:
        resolved = client.resolve_symbol(symbol)
        if not resolved:
            availability.append({"symbol": symbol, "broker_symbol": None, "candles": 0, "status": "unavailable"})
            log(f"{symbol}: unavailable")
            continue
        candles = client.fetch_candles(symbol, timeframe, fetch_start, end, max_bars=50000)
        if candles is None or len(candles) < 120:
            availability.append(
                {
                    "symbol": symbol,
                    "broker_symbol": resolved,
                    "candles": 0 if candles is None else len(candles),
                    "status": "no_history",
                }
            )
            log(f"{symbol}: skipped, no usable {timeframe} history")
            continue
        df = normalize_candles(candles)
        days = sorted(
            {
                date_in_timezone(pd.Timestamp(value).to_pydatetime(), settings.data_timezone, settings.session_timezone)
                for value in df["time"]
            }
        )
        days = [day for day in days if start_day <= day <= end_day]
        day_groups = {}
        prior_groups = {}
        for day in days:
            session_start, _, session_end = session_parts(day, settings)
            day_groups[day] = df[(df["time"] >= session_start) & (df["time"] <= session_end)].reset_index(drop=True)
            prior_groups[day] = df[df["time"] < session_start].tail(64).reset_index(drop=True)
        contract_size = client.contract_size(symbol)
        availability.append({"symbol": symbol, "broker_symbol": resolved, "candles": len(df), "days": len(days), "status": "ok"})
        log(f"{symbol}: {len(df)} {timeframe} candles, {len(days)} session days")
        for session_day in days:
            result = simulate_orb_day(
                df,
                symbol,
                session_day,
                settings,
                reward_risk,
                1.0,
                float(contract_size),
                timeframe_minutes=timeframe_minutes,
                day_candles=day_groups[session_day],
                prior_candles=prior_groups[session_day],
            )
            if isinstance(result, ORBTrade):
                row = asdict(result)
                if start <= pd.Timestamp(row["opened_at"]).to_pydatetime() <= end:
                    trades.append(row)
            elif isinstance(result, dict):
                skipped.append(result)

    client.shutdown()

    trade_frame = pd.DataFrame(trades)
    if not trade_frame.empty:
        trade_frame["opened_at"] = pd.to_datetime(trade_frame["opened_at"])
        trade_frame["closed_at"] = pd.to_datetime(trade_frame["closed_at"])
        trade_frame["r_multiple"] = pd.to_numeric(trade_frame["r_multiple"], errors="coerce")
        trade_frame = trade_frame.dropna(subset=["opened_at", "closed_at", "r_multiple"]).sort_values(["opened_at", "symbol"])

    symbol_order = {symbol: index for index, symbol in enumerate(symbols)}
    mode_frames = {
        "all_signals": trade_frame,
        "one_open_trade_at_a_time": one_open_trade_at_a_time(trade_frame, symbol_order),
        "one_trade_per_day": one_trade_per_day(trade_frame, symbol_order),
    }
    summaries: dict[str, Any] = {}
    equity_paths: dict[str, str] = {}
    for name, frame in mode_frames.items():
        summary, equity = compound_challenge(frame, start_balance, risk_percent, target_percent, max_levels)
        summaries[name] = summary
        equity_path = out_dir / f"{name}_equity.csv"
        equity.to_csv(equity_path, index=False)
        equity_paths[name] = str(equity_path)

    per_symbol: list[dict[str, Any]] = []
    per_symbol_paths: dict[str, str] = {}
    if not trade_frame.empty:
        for symbol, group in trade_frame.groupby("symbol"):
            summary, equity = compound_challenge(group, start_balance, risk_percent, target_percent, max_levels)
            summary["symbol"] = symbol
            per_symbol.append(summary)
            path = out_dir / f"{symbol}_equity.csv"
            equity.to_csv(path, index=False)
            per_symbol_paths[symbol] = str(path)
        per_symbol.sort(key=lambda item: float(item["final_balance"]), reverse=True)

    trade_path = out_dir / "orb_challenge_trades.csv"
    availability_path = out_dir / "availability.csv"
    skipped_path = out_dir / "skipped.csv"
    per_symbol_path = out_dir / "per_symbol_summary.csv"
    trade_frame.to_csv(trade_path, index=False)
    pd.DataFrame(availability).to_csv(availability_path, index=False)
    pd.DataFrame(skipped).to_csv(skipped_path, index=False)
    pd.DataFrame(per_symbol).to_csv(per_symbol_path, index=False)

    report = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "window_start": start.isoformat(sep=" ", timespec="seconds"),
        "window_end": end.isoformat(sep=" ", timespec="seconds"),
        "symbols": list(symbols),
        "strategy": "ORB + 20 Pip Challenge",
        "start_balance": start_balance,
        "risk_percent": risk_percent,
        "target_percent": target_percent,
        "reward_risk": round(reward_risk, 4),
        "levels": max_levels,
        "orb": {
            "timeframe": timeframe,
            "session_start": settings.session_start,
            "session_end": settings.session_end,
            "session_timezone": settings.session_timezone,
            "data_timezone": settings.data_timezone,
            "range_minutes": settings.range_minutes,
            "buffer_atr": settings.buffer_atr,
            "min_range_atr": settings.min_range_atr,
            "max_range_atr": settings.max_range_atr,
        },
        "summaries": summaries,
        "per_symbol": per_symbol,
        "availability": availability,
        "skipped_count": len(skipped),
        "paths": {
            "trades": str(trade_path),
            "availability": str(availability_path),
            "skipped": str(skipped_path),
            "per_symbol_summary": str(per_symbol_path),
            "equity": equity_paths,
            "per_symbol_equity": per_symbol_paths,
        },
    }
    report_path = out_dir / "orb_challenge_backtest_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    log(f"Done. Report: {report_path}")
    print(json.dumps({"report": str(report_path), "summaries": summaries, "top_symbols": per_symbol[:5]}, indent=2))


if __name__ == "__main__":
    main()
