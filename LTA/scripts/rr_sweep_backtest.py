from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
import argparse
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import REPORTS_DIR, load_config
from app.mt5_client import MT5Client
from app.risk_manager import DEFAULT_CONTRACT_SIZES
from app.strategy_engine import generate_signal


ACTIVE_SYMBOLS = ("XAUUSD", "XAGUSD", "BTCUSD", "US30")
DISABLED_FOREX_SYMBOLS = (
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCAD",
    "AUDUSD",
    "NZDUSD",
    "EURGBP",
    "EURJPY",
    "GBPJPY",
)
OTHER_PREVIOUS_SYMBOLS = ("US300",)
DEFAULT_SYMBOLS = (*ACTIVE_SYMBOLS, *OTHER_PREVIOUS_SYMBOLS, *DISABLED_FOREX_SYMBOLS)
DEFAULT_TIMEFRAMES = ("M5", "M15", "M30", "H1", "H4", "D1", "W1")


@dataclass(frozen=True)
class Candidate:
    index: int
    signal: dict[str, Any]


@dataclass
class Trade:
    rr: int
    symbol: str
    timeframe: str
    month: str
    opened_at: str
    closed_at: str
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    exit_price: float
    result: str
    pnl: float
    r_multiple: float
    setup_score: int
    entry_model: str


def parse_csv(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value:
        return default
    return tuple(item.strip().upper() for item in value.split(",") if item.strip())


def date_bounds(end: date | None) -> tuple[datetime, datetime]:
    end_date = end or date.today()
    start_date = end_date - timedelta(days=365)
    return datetime.combine(start_date, time.min), datetime.combine(end_date, time.max)


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def target_for_rr(signal: dict[str, Any], rr: int) -> float:
    direction = str(signal["direction"]).upper()
    entry = float(signal["entry"])
    stop = float(signal["stop_loss"])
    risk = abs(entry - stop)
    return entry + risk * rr if direction == "BUY" else entry - risk * rr


def simulate_trade(
    candles: pd.DataFrame,
    start_index: int,
    signal: dict[str, Any],
    rr: int,
    max_holding_bars: int,
) -> tuple[int, float, str, datetime]:
    direction = str(signal["direction"]).upper()
    stop = float(signal["stop_loss"])
    target = target_for_rr(signal, rr)
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

        # Match the app backtester: if both levels touch in the same candle, count the stop first.
        if hit_stop:
            return idx, stop, "loss", pd.Timestamp(row["time"]).to_pydatetime()
        if hit_target:
            return idx, target, "win", pd.Timestamp(row["time"]).to_pydatetime()

    row = candles.iloc[end_index]
    return end_index, float(row["close"]), "timeout", pd.Timestamp(row["time"]).to_pydatetime()


def pnl_for(symbol: str, direction: str, lot: float, contract_size: float, entry: float, exit_price: float) -> float:
    if direction == "BUY":
        return (exit_price - entry) * contract_size * lot
    return (entry - exit_price) * contract_size * lot


def collect_candidates(
    candles: pd.DataFrame,
    symbol: str,
    timeframe: str,
    min_score: int,
    stride: int,
    signal_lookback_bars: int,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    i = max(120, min(240, len(candles) // 5))
    checked = 0
    while i < len(candles) - 2:
        start_index = max(0, i + 1 - signal_lookback_bars)
        signal = generate_signal(
            candles.iloc[start_index : i + 1],
            symbol=symbol,
            timeframe=timeframe,
            min_score=min_score,
            min_rr=1.0,
        )
        if signal and signal.get("status") == "allowed" and int(signal.get("setup_score") or 0) >= min_score:
            if signal.get("entry") is not None and signal.get("stop_loss") is not None:
                candidates.append(Candidate(index=i, signal=signal))
        i += stride
        checked += 1
        if checked % 1000 == 0:
            log(f"{symbol} {timeframe}: checked {checked} points, candidates={len(candidates)}")
    return candidates


def replay_rr(
    candles: pd.DataFrame,
    candidates: list[Candidate],
    symbol: str,
    timeframe: str,
    rr: int,
    lot: float,
    contract_size: float,
    stride: int,
    max_holding_bars: int,
) -> list[Trade]:
    trades: list[Trade] = []
    next_allowed_index = 0
    for candidate in candidates:
        if candidate.index < next_allowed_index:
            continue
        signal = candidate.signal
        entry = float(signal["entry"])
        stop = float(signal["stop_loss"])
        if entry <= 0 or stop <= 0 or entry == stop:
            continue
        exit_index, exit_price, result, closed_at = simulate_trade(candles, candidate.index, signal, rr, max_holding_bars)
        direction = str(signal["direction"]).upper()
        pnl = pnl_for(symbol, direction, lot, contract_size, entry, exit_price)
        risk_amount = max(abs(entry - stop) * contract_size * lot, 1e-9)
        r_multiple = pnl / risk_amount
        opened_at = pd.Timestamp(signal["timestamp"]).to_pydatetime()
        trades.append(
            Trade(
                rr=rr,
                symbol=symbol,
                timeframe=timeframe,
                month=opened_at.strftime("%Y-%m"),
                opened_at=opened_at.isoformat(sep=" ", timespec="seconds"),
                closed_at=closed_at.isoformat(sep=" ", timespec="seconds"),
                direction=direction,
                entry=round(entry, 6),
                stop_loss=round(stop, 6),
                take_profit=round(target_for_rr(signal, rr), 6),
                exit_price=round(float(exit_price), 6),
                result=result,
                pnl=round(float(pnl), 2),
                r_multiple=round(float(r_multiple), 4),
                setup_score=int(signal.get("setup_score") or 0),
                entry_model=str(signal.get("entry_model") or ""),
            )
        )
        next_allowed_index = max(exit_index + 1, candidate.index + stride)
    return trades


def summarize_trades(trades: list[dict[str, Any]], group_cols: list[str]) -> pd.DataFrame:
    columns = [
        *group_cols,
        "trades",
        "wins",
        "losses",
        "timeouts",
        "win_rate",
        "net_r",
        "avg_r",
        "gross_r",
        "loss_r",
        "profit_factor",
        "net_pnl",
        "avg_pnl",
    ]
    if not trades:
        return pd.DataFrame(columns=columns)

    frame = pd.DataFrame(trades)
    rows: list[dict[str, Any]] = []
    for keys, group in frame.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        r_values = group["r_multiple"].astype(float)
        pnl_values = group["pnl"].astype(float)
        gross_r = float(r_values[r_values > 0].sum())
        loss_r = abs(float(r_values[r_values < 0].sum()))
        wins = int((group["result"] == "win").sum())
        losses = int((group["result"] == "loss").sum())
        timeouts = int((group["result"] == "timeout").sum())
        total = int(len(group))
        row = dict(zip(group_cols, keys))
        row.update(
            {
                "trades": total,
                "wins": wins,
                "losses": losses,
                "timeouts": timeouts,
                "win_rate": round(wins / total * 100, 2) if total else 0.0,
                "net_r": round(float(r_values.sum()), 2),
                "avg_r": round(float(r_values.mean()), 3) if total else 0.0,
                "gross_r": round(gross_r, 2),
                "loss_r": round(loss_r, 2),
                "profit_factor": round(gross_r / loss_r, 2) if loss_r else round(gross_r, 2),
                "net_pnl": round(float(pnl_values.sum()), 2),
                "avg_pnl": round(float(pnl_values.mean()), 2) if total else 0.0,
            }
        )
        rows.append(row)
    return pd.DataFrame(rows, columns=columns).sort_values(group_cols).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep forced RR exits from 1R to 6R over MT5 history.")
    parser.add_argument("--symbols", default=None, help="Comma-separated symbols. Defaults to active plus disabled forex.")
    parser.add_argument("--timeframes", default=None, help="Comma-separated timeframes. Defaults to AUTO_SCAN style set.")
    parser.add_argument("--end", default=None, help="End date in YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--stride", type=int, default=None, help="Signal scan step. Defaults to BACKTEST_SIGNAL_STRIDE.")
    parser.add_argument("--min-score", type=int, default=None, help="A+ minimum score. Defaults to MIN_SETUP_SCORE.")
    parser.add_argument("--max-holding-bars", type=int, default=96)
    parser.add_argument(
        "--signal-lookback-bars",
        type=int,
        default=500,
        help="Candles fed into each signal check. The full year is still walked; this bounds each local LTA context.",
    )
    args = parser.parse_args()

    config = load_config()
    symbols = parse_csv(args.symbols, DEFAULT_SYMBOLS)
    timeframes = parse_csv(args.timeframes, DEFAULT_TIMEFRAMES)
    stride = max(1, int(args.stride if args.stride is not None else config.backtest_signal_stride))
    min_score = max(1, int(args.min_score if args.min_score is not None else config.min_setup_score))
    end_date = date.fromisoformat(args.end) if args.end else date.today()
    start, end = date_bounds(end_date)

    symbol_lots: dict[str, float] = {
        "XAUUSD": 0.05,
        "XAGUSD": 0.05,
        "BTCUSD": 0.08,
        "US30": 1.0,
        "US300": 1.0,
        **{symbol: 1.0 for symbol in DISABLED_FOREX_SYMBOLS},
    }
    symbol_lots.update({key: float(value) for key, value in config.symbol_lots.items() if key in symbol_lots})

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = REPORTS_DIR / "rr_sweep" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    client = MT5Client()
    status = client.terminal_status()
    log(f"MT5 status: {status.get('message')}")
    log(f"Window: {start.date()} to {end.date()} | stride={stride} | min_score={min_score}")
    log(f"Symbols: {', '.join(symbols)}")
    log(f"Timeframes: {', '.join(timeframes)}")

    trades: list[dict[str, Any]] = []
    availability: list[dict[str, Any]] = []

    for symbol in symbols:
        resolved = client.resolve_symbol(symbol)
        if not resolved:
            availability.append({"symbol": symbol, "broker_symbol": None, "timeframe": None, "candles": 0, "status": "unavailable"})
            log(f"{symbol}: unavailable in MT5")
            continue
        lot = float(symbol_lots.get(symbol, 1.0))
        contract_size = client.contract_size(symbol) or DEFAULT_CONTRACT_SIZES.get(symbol, 1.0)
        for timeframe in timeframes:
            candles = client.fetch_candles(symbol, timeframe, start, end, max_bars=200000)
            candle_count = 0 if candles is None else len(candles)
            if candles is None or candle_count < 120:
                availability.append(
                    {
                        "symbol": symbol,
                        "broker_symbol": resolved,
                        "timeframe": timeframe,
                        "candles": candle_count,
                        "status": "skipped_not_enough_candles",
                    }
                )
                log(f"{symbol} {timeframe}: skipped ({candle_count} candles)")
                continue

            availability.append(
                {
                    "symbol": symbol,
                    "broker_symbol": resolved,
                    "timeframe": timeframe,
                    "candles": candle_count,
                    "status": "ok",
                }
            )
            log(f"{symbol} {timeframe}: generating candidates from {candle_count} candles")
            candidates = collect_candidates(
                candles,
                symbol,
                timeframe,
                min_score,
                stride,
                max(120, int(args.signal_lookback_bars)),
            )
            log(f"{symbol} {timeframe}: {len(candidates)} A+ candidates")
            for rr in range(1, 7):
                rr_trades = replay_rr(
                    candles,
                    candidates,
                    symbol,
                    timeframe,
                    rr,
                    lot,
                    float(contract_size),
                    stride,
                    int(args.max_holding_bars),
                )
                trades.extend(asdict(item) for item in rr_trades)

    client.shutdown()

    trades_frame = pd.DataFrame(trades)
    trade_path = out_dir / "trades_all_rr.csv"
    trades_frame.to_csv(trade_path, index=False)

    availability_frame = pd.DataFrame(availability)
    availability_path = out_dir / "availability.csv"
    availability_frame.to_csv(availability_path, index=False)

    rr_summary = summarize_trades(trades, ["rr"])
    symbol_summary = summarize_trades(trades, ["rr", "symbol"])
    monthly_symbol = summarize_trades(trades, ["rr", "symbol", "month"])
    monthly_timeframe = summarize_trades(trades, ["rr", "symbol", "timeframe", "month"])

    rr_summary_path = out_dir / "rr_summary.csv"
    symbol_summary_path = out_dir / "symbol_summary_by_rr.csv"
    monthly_symbol_path = out_dir / "monthly_symbol_breakdown_by_rr.csv"
    monthly_timeframe_path = out_dir / "monthly_symbol_timeframe_breakdown_by_rr.csv"
    rr_summary.to_csv(rr_summary_path, index=False)
    symbol_summary.to_csv(symbol_summary_path, index=False)
    monthly_symbol.to_csv(monthly_symbol_path, index=False)
    monthly_timeframe.to_csv(monthly_timeframe_path, index=False)

    best_rr = None
    if not rr_summary.empty:
        best_row = rr_summary.sort_values(["net_r", "profit_factor", "trades"], ascending=[False, False, False]).iloc[0]
        best_rr = int(best_row["rr"])
        best_monthly = monthly_symbol[monthly_symbol["rr"] == best_rr]
        pivot = best_monthly.pivot(index="symbol", columns="month", values="net_r").fillna(0.0).reset_index()
        pivot_path = out_dir / f"monthly_symbol_net_r_best_rr_{best_rr}.csv"
        pivot.to_csv(pivot_path, index=False)
    else:
        pivot_path = out_dir / "monthly_symbol_net_r_best_rr_none.csv"
        pd.DataFrame().to_csv(pivot_path, index=False)

    report = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "window_start": start.isoformat(sep=" ", timespec="seconds"),
        "window_end": end.isoformat(sep=" ", timespec="seconds"),
        "symbols": list(symbols),
        "active_symbols": list(ACTIVE_SYMBOLS),
        "disabled_forex_symbols_counted": list(DISABLED_FOREX_SYMBOLS),
        "other_previous_symbols": list(OTHER_PREVIOUS_SYMBOLS),
        "timeframes_requested": list(timeframes),
        "timeframes_used": sorted(availability_frame[availability_frame["status"] == "ok"]["timeframe"].dropna().unique().tolist())
        if not availability_frame.empty
        else [],
        "stride": stride,
        "min_score": min_score,
        "max_holding_bars": int(args.max_holding_bars),
        "signal_lookback_bars": max(120, int(args.signal_lookback_bars)),
        "lot_assumptions": symbol_lots,
        "best_rr_by_net_r": best_rr,
        "paths": {
            "trades": str(trade_path),
            "availability": str(availability_path),
            "rr_summary": str(rr_summary_path),
            "symbol_summary_by_rr": str(symbol_summary_path),
            "monthly_symbol_breakdown_by_rr": str(monthly_symbol_path),
            "monthly_symbol_timeframe_breakdown_by_rr": str(monthly_timeframe_path),
            "best_rr_monthly_pivot": str(pivot_path),
        },
        "rr_summary": rr_summary.to_dict(orient="records"),
        "best_rr_symbol_summary": symbol_summary[symbol_summary["rr"] == best_rr]
        .sort_values(["net_r", "profit_factor"], ascending=[False, False])
        .to_dict(orient="records")
        if best_rr is not None
        else [],
        "availability": availability,
    }
    report_path = out_dir / "rr_sweep_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    log(f"Done. Report: {report_path}")
    print(json.dumps({"best_rr": best_rr, "report": str(report_path), "rr_summary": report["rr_summary"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
