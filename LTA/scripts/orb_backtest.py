from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import REPORTS_DIR, load_config
from app.models import TRADE_SYMBOLS
from app.mt5_client import MT5Client
from app.orb_strategy import ORBSettings, atr, session_bounds as orb_session_bounds, target_for
from app.risk_manager import DEFAULT_CONTRACT_SIZES
from app.session_time import DEFAULT_DATA_TIMEZONE, DEFAULT_SESSION_TIMEZONE, date_in_timezone


DISABLED_FOREX_SYMBOLS = (
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCHF",
    "USDCAD",
    "AUDUSD",
    "NZDUSD",
    "EURGBP",
    "EURJPY",
    "GBPJPY",
)
DEFAULT_SYMBOLS = (*TRADE_SYMBOLS, *DISABLED_FOREX_SYMBOLS)
DEFAULT_RANGE_MINUTES = (15, 30, 60)
DEFAULT_RRS = (1, 2, 3, 4, 5, 6)


@dataclass
class ORBTrade:
    symbol: str
    range_minutes: int
    rr: float
    month: str
    date: str
    opened_at: str
    closed_at: str
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    exit_price: float
    result: str
    r_multiple: float
    spread_r: float
    spread_points: float
    pnl: float
    range_high: float
    range_low: float
    range_atr: float | None


def parse_csv(value: str | None, default: tuple[Any, ...], cast=str) -> tuple[Any, ...]:
    if not value:
        return default
    return tuple(cast(item.strip()) for item in value.split(",") if item.strip())


def date_window(end_date: date | None) -> tuple[datetime, datetime]:
    end_day = end_date or date.today()
    start_day = end_day - timedelta(days=365)
    return datetime.combine(start_day, time.min), datetime.combine(end_day, time.max)


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def normalize_candles(candles: pd.DataFrame) -> pd.DataFrame:
    df = candles.copy()
    df["time"] = pd.to_datetime(df["time"])
    for column in ("open", "high", "low", "close"):
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time").reset_index(drop=True)


def session_parts(session_day: date, settings: ORBSettings) -> tuple[datetime, datetime, datetime]:
    return orb_session_bounds(session_day, settings)


def pnl_for(symbol: str, direction: str, lot: float, contract_size: float, entry: float, exit_price: float) -> float:
    if direction == "BUY":
        return (exit_price - entry) * contract_size * lot
    return (entry - exit_price) * contract_size * lot


def infer_point(symbol: str) -> float:
    upper = symbol.upper()
    if upper.endswith("JPY") and len(upper) == 6:
        return 0.001
    if len(upper) == 6 and upper[:3].isalpha() and upper[3:].isalpha():
        return 0.00001
    if upper == "XAUUSD":
        return 0.01
    if upper == "XAGUSD":
        return 0.001
    if upper == "BTCUSD":
        return 0.01
    if upper in {"US30", "US300"}:
        return 0.1
    return 0.01


def spread_cost_r(
    row: pd.Series,
    symbol: str,
    risk: float,
    point_size: float | None = None,
) -> tuple[float, float]:
    if risk <= 0:
        return 0.0, 0.0
    try:
        points = max(0.0, float(row.get("spread") or 0.0))
    except (TypeError, ValueError):
        points = 0.0
    try:
        multiplier = max(0.0, float(os.getenv("BACKTEST_SPREAD_MULTIPLIER", "1") or 1.0))
    except ValueError:
        multiplier = 1.0
    spread_price = points * float(point_size or infer_point(symbol)) * multiplier
    return spread_price / risk, points


def simulate_orb_day(
    df: pd.DataFrame,
    symbol: str,
    session_day: date,
    settings: ORBSettings,
    rr: float,
    lot: float,
    contract_size: float,
    timeframe_minutes: int = 15,
    day_candles: pd.DataFrame | None = None,
    prior_candles: pd.DataFrame | None = None,
    fixed_stop_distance: float | None = None,
    fixed_target_distance: float | None = None,
    point_size: float | None = None,
) -> ORBTrade | dict[str, Any] | None:
    session_start, range_end, session_end = session_parts(session_day, settings)
    source = day_candles if day_candles is not None else df
    needed_bars = max(1, settings.range_minutes // timeframe_minutes)
    range_bars = source[(source["time"] >= session_start) & (source["time"] < range_end)]
    if len(range_bars) < needed_bars:
        return None

    prior = prior_candles if prior_candles is not None else df[df["time"] < session_start].tail(64)
    atr_value = atr(prior, 14)
    range_high = float(range_bars["high"].max())
    range_low = float(range_bars["low"].min())
    range_width = range_high - range_low
    if range_width <= 0:
        return None
    range_atr = range_width / atr_value if atr_value > 0 else None
    if range_atr is not None and range_atr < settings.min_range_atr:
        return None
    if range_atr is not None and range_atr > settings.max_range_atr:
        return None

    buffer = max(0.0, settings.buffer_atr) * max(0.0, atr_value)
    buy_trigger = range_high + buffer
    sell_trigger = range_low - buffer
    post = source[(source["time"] >= range_end) & (source["time"] <= session_end)]
    if post.empty:
        return None

    trigger_position: int | None = None
    direction: str | None = None
    entry = 0.0
    stop = 0.0
    for position, (_, row) in enumerate(post.iterrows()):
        high = float(row["high"])
        low = float(row["low"])
        hit_buy = high >= buy_trigger
        hit_sell = low <= sell_trigger
        if hit_buy and hit_sell:
            return {"skipped": "ambiguous_breakout", "symbol": symbol, "date": session_day.isoformat()}
        if hit_buy:
            trigger_position = position
            direction = "BUY"
            entry = buy_trigger
            stop = range_low
            break
        if hit_sell:
            trigger_position = position
            direction = "SELL"
            entry = sell_trigger
            stop = range_high
            break

    if trigger_position is None or direction is None:
        return None

    if fixed_stop_distance and fixed_stop_distance > 0:
        stop = entry - fixed_stop_distance if direction == "BUY" else entry + fixed_stop_distance
    if fixed_target_distance and fixed_target_distance > 0:
        target = entry + fixed_target_distance if direction == "BUY" else entry - fixed_target_distance
    else:
        target = target_for(direction, entry, stop, rr)
    exit_price = float(post.iloc[-1]["close"])
    result = "timeout"
    closed_at = pd.Timestamp(post.iloc[-1]["time"]).to_pydatetime()
    trade_path = post.iloc[trigger_position:].reset_index(drop=True)

    for _, row in trade_path.iterrows():
        high = float(row["high"])
        low = float(row["low"])
        happened_at = pd.Timestamp(row["time"]).to_pydatetime()
        if direction == "BUY":
            if low <= stop:
                exit_price = stop
                result = "loss"
                closed_at = happened_at
                break
            if high >= target:
                exit_price = target
                result = "win"
                closed_at = happened_at
                break
        else:
            if high >= stop:
                exit_price = stop
                result = "loss"
                closed_at = happened_at
                break
            if low <= target:
                exit_price = target
                result = "win"
                closed_at = happened_at
                break

    risk = max(abs(entry - stop), 1e-9)
    r_multiple = ((exit_price - entry) / risk) if direction == "BUY" else ((entry - exit_price) / risk)
    spread_r, spread_points = spread_cost_r(trade_path.iloc[0], symbol, risk, point_size=point_size)
    spread_enabled = str(os.getenv("BACKTEST_SPREAD_ADJUST", "true")).strip().lower() in {"1", "true", "yes", "on"}
    max_spread_r = float(os.getenv("BACKTEST_MAX_SPREAD_R", "0") or 0.0)
    if spread_enabled and max_spread_r > 0 and spread_r > max_spread_r:
        return None
    if spread_enabled:
        r_multiple -= spread_r
    opened_at = pd.Timestamp(trade_path.iloc[0]["time"]).to_pydatetime()
    pnl = pnl_for(symbol, direction, lot, contract_size, entry, exit_price)
    return ORBTrade(
        symbol=symbol,
        range_minutes=settings.range_minutes,
        rr=rr,
        month=opened_at.strftime("%Y-%m"),
        date=session_day.isoformat(),
        opened_at=opened_at.isoformat(sep=" ", timespec="seconds"),
        closed_at=closed_at.isoformat(sep=" ", timespec="seconds"),
        direction=direction,
        entry=round(entry, 6),
        stop_loss=round(stop, 6),
        take_profit=round(target, 6),
        exit_price=round(float(exit_price), 6),
        result=result,
        r_multiple=round(float(r_multiple), 4),
        spread_r=round(float(spread_r if spread_enabled else 0.0), 4),
        spread_points=round(float(spread_points), 2),
        pnl=round(float(pnl), 2),
        range_high=round(range_high, 6),
        range_low=round(range_low, 6),
        range_atr=round(float(range_atr), 4) if range_atr is not None else None,
    )


def summarize(rows: list[dict[str, Any]], groups: list[str]) -> pd.DataFrame:
    columns = [
        *groups,
        "trades",
        "wins",
        "losses",
        "timeouts",
        "win_rate",
        "net_r",
        "avg_r",
        "profit_factor",
        "net_pnl",
    ]
    if not rows:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(rows)
    out: list[dict[str, Any]] = []
    for key, group in frame.groupby(groups, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        r_values = group["r_multiple"].astype(float)
        gross_r = float(r_values[r_values > 0].sum())
        loss_r = abs(float(r_values[r_values < 0].sum()))
        total = int(len(group))
        wins = int((group["result"] == "win").sum())
        row = dict(zip(groups, key))
        row.update(
            {
                "trades": total,
                "wins": wins,
                "losses": int((group["result"] == "loss").sum()),
                "timeouts": int((group["result"] == "timeout").sum()),
                "win_rate": round(wins / total * 100, 2) if total else 0.0,
                "net_r": round(float(r_values.sum()), 2),
                "avg_r": round(float(r_values.mean()), 3) if total else 0.0,
                "profit_factor": round(gross_r / loss_r, 2) if loss_r else round(gross_r, 2),
                "net_pnl": round(float(group["pnl"].sum()), 2),
            }
        )
        out.append(row)
    return pd.DataFrame(out, columns=columns).sort_values(groups).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest ORB against MT5 history.")
    parser.add_argument("--symbols", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--session-start", default="09:30")
    parser.add_argument("--session-end", default="16:00")
    parser.add_argument("--session-timezone", default=DEFAULT_SESSION_TIMEZONE)
    parser.add_argument("--data-timezone", default=DEFAULT_DATA_TIMEZONE)
    parser.add_argument("--ranges", default=None, help="Comma-separated opening range minutes. Default: 15,30,60")
    parser.add_argument("--rrs", default=None, help="Comma-separated RR values. Default: 1,2,3,4,5,6")
    parser.add_argument("--buffer-atr", type=float, default=0.0)
    parser.add_argument("--min-range-atr", type=float, default=0.0)
    parser.add_argument("--max-range-atr", type=float, default=999.0)
    args = parser.parse_args()

    config = load_config()
    symbols = parse_csv(args.symbols, DEFAULT_SYMBOLS, str)
    ranges = parse_csv(args.ranges, DEFAULT_RANGE_MINUTES, int)
    rrs = parse_csv(args.rrs, DEFAULT_RRS, int)
    end_date = date.fromisoformat(args.end) if args.end else date.today()
    start, end = date_window(end_date)
    lots = {symbol: 1.0 for symbol in DISABLED_FOREX_SYMBOLS}
    lots.update({"XAUUSD": 0.05, "XAGUSD": 0.05, "BTCUSD": 0.08, "US30": 1.0})
    lots.update({key: float(value) for key, value in config.symbol_lots.items() if key in lots})

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = REPORTS_DIR / "orb_backtest" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    client = MT5Client()
    status = client.terminal_status()
    log(f"MT5 status: {status.get('message')}")
    log(
        f"Window: {start.date()} to {end.date()} | "
        f"session={args.session_start}-{args.session_end} {args.session_timezone}"
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
        candles = client.fetch_candles(symbol, "M15", start, end, max_bars=200000)
        if candles is None or len(candles) < 120:
            availability.append({"symbol": symbol, "broker_symbol": resolved, "candles": 0 if candles is None else len(candles), "status": "no_m15_history"})
            log(f"{symbol}: skipped, no usable M15 history")
            continue
        df = normalize_candles(candles)
        base_df = df
        base_settings = ORBSettings(
            session_start=args.session_start,
            session_end=args.session_end,
            range_minutes=max(ranges),
            session_timezone=args.session_timezone,
            data_timezone=args.data_timezone,
        )
        days = sorted(
            {
                date_in_timezone(pd.Timestamp(value).to_pydatetime(), args.data_timezone, args.session_timezone)
                for value in base_df["time"]
            }
        )
        day_groups = {}
        prior_groups = {}
        for day in days:
            session_start, _, session_end = session_parts(day, base_settings)
            day_groups[day] = base_df[(base_df["time"] >= session_start) & (base_df["time"] <= session_end)].reset_index(drop=True)
            prior_groups[day] = base_df[base_df["time"] < session_start].tail(64).reset_index(drop=True)
        lot = float(lots.get(symbol, 1.0))
        contract_size = client.contract_size(symbol) or DEFAULT_CONTRACT_SIZES.get(symbol, 1.0)
        availability.append({"symbol": symbol, "broker_symbol": resolved, "candles": len(df), "status": "ok"})
        log(f"{symbol}: {len(df)} M15 candles, {len(days)} days")
        for range_minutes in ranges:
            for rr in rrs:
                settings = ORBSettings(
                    session_start=args.session_start,
                    session_end=args.session_end,
                    range_minutes=int(range_minutes),
                    reward_risk=float(rr),
                    buffer_atr=max(0.0, float(args.buffer_atr)),
                    min_range_atr=max(0.0, float(args.min_range_atr)),
                    max_range_atr=max(0.0, float(args.max_range_atr)),
                    session_timezone=args.session_timezone,
                    data_timezone=args.data_timezone,
                )
                for session_day in days:
                    result = simulate_orb_day(
                        base_df,
                        symbol,
                        session_day,
                        settings,
                        int(rr),
                        lot,
                        float(contract_size),
                        day_candles=day_groups[session_day],
                        prior_candles=prior_groups[session_day],
                    )
                    if isinstance(result, ORBTrade):
                        trades.append(asdict(result))
                    elif isinstance(result, dict):
                        skipped.append({**result, "range_minutes": range_minutes, "rr": rr})

    client.shutdown()

    trade_frame = pd.DataFrame(trades)
    availability_frame = pd.DataFrame(availability)
    skipped_frame = pd.DataFrame(skipped)
    rr_summary = summarize(trades, ["range_minutes", "rr"])
    symbol_summary = summarize(trades, ["range_minutes", "rr", "symbol"])
    monthly_symbol = summarize(trades, ["range_minutes", "rr", "symbol", "month"])

    trade_path = out_dir / "orb_trades.csv"
    availability_path = out_dir / "availability.csv"
    skipped_path = out_dir / "skipped.csv"
    rr_summary_path = out_dir / "orb_rr_summary.csv"
    symbol_summary_path = out_dir / "orb_symbol_summary.csv"
    monthly_path = out_dir / "orb_monthly_symbol_breakdown.csv"
    trade_frame.to_csv(trade_path, index=False)
    availability_frame.to_csv(availability_path, index=False)
    skipped_frame.to_csv(skipped_path, index=False)
    rr_summary.to_csv(rr_summary_path, index=False)
    symbol_summary.to_csv(symbol_summary_path, index=False)
    monthly_symbol.to_csv(monthly_path, index=False)

    best = None
    best_symbol_rows: list[dict[str, Any]] = []
    pivot_path = out_dir / "orb_monthly_best_pivot.csv"
    if not rr_summary.empty:
        best_row = rr_summary.sort_values(["net_r", "profit_factor", "trades"], ascending=[False, False, False]).iloc[0]
        best = {"range_minutes": int(best_row["range_minutes"]), "rr": int(best_row["rr"])}
        best_symbols = symbol_summary[
            (symbol_summary["range_minutes"] == best["range_minutes"]) & (symbol_summary["rr"] == best["rr"])
        ].sort_values(["net_r", "profit_factor"], ascending=[False, False])
        best_symbol_rows = best_symbols.to_dict(orient="records")
        pivot = monthly_symbol[
            (monthly_symbol["range_minutes"] == best["range_minutes"]) & (monthly_symbol["rr"] == best["rr"])
        ].pivot(index="symbol", columns="month", values="net_r").fillna(0.0)
        if not best_symbols.empty:
            pivot = pivot.reindex(best_symbols["symbol"].tolist())
        pivot.to_csv(pivot_path)
    else:
        pd.DataFrame().to_csv(pivot_path, index=False)

    report = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "window_start": start.isoformat(sep=" ", timespec="seconds"),
        "window_end": end.isoformat(sep=" ", timespec="seconds"),
        "symbols": list(symbols),
        "session_start": args.session_start,
        "session_end": args.session_end,
        "session_timezone": args.session_timezone,
        "data_timezone": args.data_timezone,
        "timeframe": "M15",
        "range_minutes_tested": list(ranges),
        "rrs_tested": list(rrs),
        "buffer_atr": args.buffer_atr,
        "min_range_atr": args.min_range_atr,
        "max_range_atr": args.max_range_atr,
        "best_by_net_r": best,
        "paths": {
            "trades": str(trade_path),
            "availability": str(availability_path),
            "skipped": str(skipped_path),
            "rr_summary": str(rr_summary_path),
            "symbol_summary": str(symbol_summary_path),
            "monthly_symbol_breakdown": str(monthly_path),
            "monthly_best_pivot": str(pivot_path),
        },
        "rr_summary": rr_summary.to_dict(orient="records"),
        "best_symbol_summary": best_symbol_rows,
        "availability": availability,
        "skipped_count": len(skipped),
    }
    report_path = out_dir / "orb_backtest_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    log(f"Done. Report: {report_path}")
    print(json.dumps({"best": best, "report": str(report_path), "rr_summary": report["rr_summary"]}, indent=2))


if __name__ == "__main__":
    main()
