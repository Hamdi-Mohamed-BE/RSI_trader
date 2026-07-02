from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import date, datetime, time, timedelta
import json
import math
import os
from pathlib import Path
import sys
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import REPORTS_DIR, load_config
from app.mt5_client import MT5Client, TIMEFRAME_MINUTES
from app.session_time import DEFAULT_DATA_TIMEZONE, DEFAULT_SESSION_TIMEZONE, as_aware
from app.strategy_engine import generate_preentry_candidate, generate_signal
from scripts.dynamic_exit_backtest import (
    Candidate,
    add_atr_columns,
    current_rr,
    in_allowed_sessions,
    normalize_candles,
    parse_csv,
    parse_rr_map,
    parse_sessions,
    simulate_managed_trade,
)


DEFAULT_SYMBOLS = (
    "XAUUSD",
    "XAGUSD",
    "BTCUSD",
    "ETHUSD",
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCHF",
    "USDCAD",
    "AUDUSD",
    "NZDUSD",
)
DEFAULT_TIMEFRAMES = ("M15", "M30", "H1")
PRODUCTION_POLICY = {"name": "production_current", "stop": "live_adaptive", "rr": "static"}


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def local_minutes(value: datetime, data_timezone: str, session_timezone: str) -> int:
    local = as_aware(value, data_timezone).astimezone(as_aware(datetime.now(), session_timezone).tzinfo)
    return local.hour * 60 + local.minute


def strict_pending_allowed(
    signal: dict[str, Any],
    signal_time: datetime,
    data_timezone: str,
    session_timezone: str,
) -> bool:
    ranges = parse_sessions(
        f"{os.getenv('AUTO_STRICT_SESSION_START', '10:00')}-{os.getenv('AUTO_STRICT_SESSION_END', '13:00')}"
    )
    if not ranges:
        return True
    start, end, _label = ranges[0]
    minutes = local_minutes(signal_time, data_timezone, session_timezone)
    in_window = start <= minutes < end if start < end else minutes >= start or minutes < end
    if not in_window:
        return True
    if int(signal.get("setup_score") or 0) < int(os.getenv("AUTO_STRICT_SESSION_PREPLACE_MIN_SCORE", "88") or 88):
        return False
    model = str(signal.get("entry_model") or "")
    pending_type = str(signal.get("pending_order_type") or "").upper()
    book_retest = pending_type in {"BUY_LIMIT", "SELL_LIMIT"} and bool(signal.get("book_aligned_retest"))
    require_internal = str(os.getenv("AUTO_STRICT_SESSION_REQUIRE_INTERNAL_BREAK", "true")).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if require_internal and "Internal Structure" not in model and not book_retest:
        return False
    if pending_type in {"BUY_LIMIT", "SELL_LIMIT"} and not book_retest:
        return False
    if (
        book_retest
        and str(signal.get("volume_regime") or "normal") == "low"
        and str(signal.get("timeframe") or "").upper() in {"M1", "M5", "M15"}
    ):
        return False
    return True


def pending_fill_index(
    df: pd.DataFrame,
    signal_index: int,
    signal: dict[str, Any],
    expiry_minutes: int,
) -> int | None:
    timeframe = str(signal.get("timeframe") or "M15").upper()
    bars = max(1, math.ceil(expiry_minutes / max(1, TIMEFRAME_MINUTES.get(timeframe, 15))))
    end_index = min(len(df) - 1, signal_index + bars)
    trigger = float(signal.get("trigger_price") or signal.get("entry") or 0.0)
    pending_type = str(signal.get("pending_order_type") or "").upper()
    for index in range(signal_index + 1, end_index + 1):
        row = df.iloc[index]
        high = float(row["high"])
        low = float(row["low"])
        if pending_type in {"BUY_LIMIT", "SELL_STOP"} and low <= trigger:
            return index
        if pending_type in {"SELL_LIMIT", "BUY_STOP"} and high >= trigger:
            return index
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest current LTA pending-entry models against MT5 candles.")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--timeframes", default=",".join(DEFAULT_TIMEFRAMES))
    parser.add_argument("--max-holding-bars", type=int, default=96)
    parser.add_argument("--lookback-bars", type=int, default=500)
    args = parser.parse_args()

    config = load_config()
    start = datetime.combine(date.fromisoformat(args.start), time.min)
    end = datetime.combine(date.fromisoformat(args.end), time.max)
    symbols = parse_csv(args.symbols, DEFAULT_SYMBOLS)
    timeframes = parse_csv(args.timeframes, DEFAULT_TIMEFRAMES)
    stride = max(1, int(os.getenv("BACKTEST_SIGNAL_STRIDE", "3") or 3))
    min_score = int(os.getenv("MIN_SETUP_SCORE", str(config.min_setup_score)) or config.min_setup_score)
    preplace_score = int(os.getenv("AUTO_PREPLACE_MIN_SCORE", "85") or 85)
    min_rr = float(os.getenv("MIN_RISK_REWARD", str(config.min_risk_reward)) or config.min_risk_reward)
    expiry_minutes = max(1, int(os.getenv("AUTO_PREPLACE_EXPIRY_MINUTES", "180") or 180))
    rr_map = parse_rr_map(os.getenv("AUTO_SYMBOL_RR"))
    allowed_sessions = parse_sessions(os.getenv("AUTO_ALLOWED_SESSIONS"))
    session_timezone = os.getenv("MARKET_SESSION_TIMEZONE", DEFAULT_SESSION_TIMEZONE)
    data_timezone = os.getenv("MARKET_DATA_TIMEZONE", DEFAULT_DATA_TIMEZONE)

    symbol_tag = "-".join(symbols)
    stamp = f"{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}-{symbol_tag}"
    output_dir = REPORTS_DIR / "lta_pending_backtest" / stamp
    output_dir.mkdir(parents=True, exist_ok=True)
    client = MT5Client()
    log(client.terminal_status().get("message") or "MT5 status unavailable")
    rows: list[dict[str, Any]] = []
    placements: list[dict[str, Any]] = []
    availability: list[dict[str, Any]] = []

    for symbol in symbols:
        resolved = client.resolve_symbol(symbol)
        if not resolved:
            availability.append({"symbol": symbol, "status": "unavailable"})
            continue
        for timeframe in timeframes:
            candles = client.fetch_candles(symbol, timeframe, start - timedelta(days=45), end, max_bars=200000)
            if candles is None or len(candles) < 160:
                availability.append(
                    {"symbol": symbol, "broker_symbol": resolved, "timeframe": timeframe, "status": "not_enough_data"}
                )
                continue
            df = add_atr_columns(normalize_candles(candles))
            availability.append(
                {
                    "symbol": symbol,
                    "broker_symbol": resolved,
                    "timeframe": timeframe,
                    "status": "ok",
                    "candles": len(df),
                }
            )
            log(f"{symbol} {timeframe}: scanning {len(df)} candles")
            generated_keys: dict[tuple[Any, ...], datetime] = {}
            first_index = max(120, min(240, len(df) // 5))
            for index in range(first_index, len(df) - 2, stride):
                signal_time = pd.Timestamp(df.iloc[index]["time"]).to_pydatetime()
                if signal_time < start:
                    continue
                if signal_time > end:
                    break
                if as_aware(signal_time, data_timezone).astimezone(as_aware(datetime.now(), session_timezone).tzinfo).weekday() >= 5:
                    continue
                if not in_allowed_sessions(signal_time, allowed_sessions, data_timezone, session_timezone):
                    continue
                context = df.iloc[max(0, index + 1 - max(120, args.lookback_bars)) : index + 1]
                market = generate_signal(context, symbol, timeframe, min_score=min_score, min_rr=min_rr)
                if market and market.get("status") == "allowed" and int(market.get("setup_score") or 0) >= min_score:
                    continue
                signal = generate_preentry_candidate(
                    context,
                    symbol,
                    timeframe,
                    min_score=preplace_score,
                    min_rr=min_rr,
                )
                if not signal or not strict_pending_allowed(signal, signal_time, data_timezone, session_timezone):
                    continue
                signal = {**signal, "symbol": symbol, "timeframe": timeframe}
                key = (
                    symbol,
                    str(signal.get("direction")),
                    str(signal.get("pending_order_type")),
                    round(float(signal.get("trigger_price") or 0.0), 5),
                )
                last_generated = generated_keys.get(key)
                if last_generated and signal_time - last_generated < timedelta(minutes=expiry_minutes):
                    continue
                generated_keys[key] = signal_time
                fill_index = pending_fill_index(df, index, signal, expiry_minutes)
                placement = {
                    "signal_time": signal_time.isoformat(sep=" ", timespec="seconds"),
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "direction": signal.get("direction"),
                    "pending_order_type": signal.get("pending_order_type"),
                    "trigger_price": signal.get("trigger_price"),
                    "stop_loss": signal.get("stop_loss"),
                    "setup_score": signal.get("setup_score"),
                    "entry_model": signal.get("entry_model"),
                    "filled": fill_index is not None,
                }
                placements.append(placement)
                if fill_index is None:
                    continue
                entry = float(signal.get("trigger_price") or signal.get("entry") or 0.0)
                stop = float(signal.get("stop_loss") or 0.0)
                direction = str(signal.get("direction") or "").upper()
                if entry <= 0 or stop <= 0 or direction not in {"BUY", "SELL"}:
                    continue
                filled_at = pd.Timestamp(df.iloc[fill_index]["time"]).to_pydatetime()
                candidate = Candidate(
                    bot="LTA",
                    symbol=symbol,
                    timeframe=timeframe,
                    series_key=f"LTA:{symbol}:{timeframe}",
                    start_index=fill_index,
                    opened_at=filled_at,
                    direction=direction,
                    entry=entry,
                    base_stop=stop,
                    configured_rr=current_rr(symbol, min_rr, rr_map),
                    setup_score=int(signal.get("setup_score") or 0),
                    atr=float(df.iloc[index].get("atr") or abs(entry - stop)),
                    atr_percentile=float(df.iloc[index].get("atr_percentile") or 0.5),
                    session_metric=None,
                    entry_model=str(signal.get("entry_model") or "Pending LTA setup"),
                )
                trade = simulate_managed_trade(df, candidate, PRODUCTION_POLICY, args.max_holding_bars, partial_fraction=0.0)
                if trade:
                    row = asdict(trade)
                    row.update(
                        {
                            "execution_type": "PENDING",
                            "pending_order_type": signal.get("pending_order_type"),
                            "signal_time": placement["signal_time"],
                            "book_aligned_retest": bool(signal.get("book_aligned_retest")),
                        }
                    )
                    rows.append(row)
            log(f"{symbol} {timeframe}: placements={sum(1 for item in placements if item['symbol'] == symbol and item['timeframe'] == timeframe)}")

    client.shutdown()
    trades_path = output_dir / "pending_trades.csv"
    placements_path = output_dir / "pending_placements.csv"
    availability_path = output_dir / "availability.csv"
    pd.DataFrame(rows).to_csv(trades_path, index=False)
    pd.DataFrame(placements).to_csv(placements_path, index=False)
    pd.DataFrame(availability).to_csv(availability_path, index=False)
    report = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "window_start": start.isoformat(sep=" "),
        "window_end": end.isoformat(sep=" "),
        "symbols": list(symbols),
        "timeframes": list(timeframes),
        "signal_stride": stride,
        "preplace_min_score": preplace_score,
        "expiry_minutes": expiry_minutes,
        "placements": len(placements),
        "filled": sum(1 for item in placements if item["filled"]),
        "simulated_trades": len(rows),
        "paths": {
            "trades": str(trades_path),
            "placements": str(placements_path),
            "availability": str(availability_path),
        },
    }
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(report_path), **report}, indent=2), flush=True)


if __name__ == "__main__":
    main()
