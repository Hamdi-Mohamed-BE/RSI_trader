from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import json
import os
from pathlib import Path
import sys
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.bpr_strategy import add_atr, generate_bpr_signals, settings_from_env
from app.bpr_strategy import BPRSettings
from app.adaptive_risk import (
    apply_dynamic_stop,
    dynamic_stop_settings,
    evaluate_setup_validity,
    smart_exit_settings,
)
from app.config import REPORTS_DIR, load_config
from app.models import TRADE_SYMBOLS
from app.mt5_client import MT5Client, TIMEFRAME_MINUTES


BPR_REPORT_DIR = REPORTS_DIR / "bpr_backtest"
BPR_REPORT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class BPRBacktestTrade:
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
    r_multiple: float
    spread_r: float
    spread_points: float
    setup_score: int
    bpr_low: float
    bpr_high: float
    reason: str


def _csv_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if not value:
        return default
    return tuple(item.strip().upper() for item in value.split(",") if item.strip())


def _csv_arg(value: str | None) -> tuple[str, ...] | None:
    if not value:
        return None
    items = tuple(item.strip().upper() for item in value.split(",") if item.strip())
    return items or None


def _float_map_env(name: str) -> dict[str, float]:
    value = os.getenv(name, "")
    result: dict[str, float] = {}
    for raw_item in value.split(","):
        item = raw_item.strip()
        if not item:
            continue
        separator = ":" if ":" in item else "=" if "=" in item else None
        if not separator:
            continue
        symbol, raw_value = item.split(separator, 1)
        try:
            result[symbol.strip().upper()] = float(raw_value.strip())
        except ValueError:
            continue
    return result


def _pair_float_map_env(name: str) -> dict[tuple[str, str], float]:
    value = os.getenv(name, "")
    result: dict[tuple[str, str], float] = {}
    for raw_item in value.split(","):
        item = raw_item.strip()
        if not item:
            continue
        separator = ":" if ":" in item else "=" if "=" in item else None
        if not separator:
            continue
        raw_key, raw_value = item.split(separator, 1)
        key_separator = "." if "." in raw_key else "@" if "@" in raw_key else None
        if not key_separator:
            continue
        symbol, timeframe = raw_key.split(key_separator, 1)
        try:
            result[(symbol.strip().upper(), timeframe.strip().upper())] = float(raw_value.strip())
        except ValueError:
            continue
    return result


def _symbol_timeframes_env(name: str) -> dict[str, tuple[str, ...]]:
    value = os.getenv(name, "")
    result: dict[str, tuple[str, ...]] = {}
    for raw_item in value.split(","):
        item = raw_item.strip()
        if not item:
            continue
        separator = ":" if ":" in item else "=" if "=" in item else None
        if not separator:
            continue
        symbol, raw_values = item.split(separator, 1)
        timeframes = tuple(part.strip().upper() for part in raw_values.replace(";", "|").split("|") if part.strip())
        if timeframes:
            result[symbol.strip().upper()] = timeframes
    return result


def _int_env(name: str, default: int) -> int:
    try:
        return int(float(os.getenv(name, str(default)) or default))
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


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


def spread_cost(row: pd.Series, symbol: str, risk_distance: float) -> tuple[float, float]:
    if risk_distance <= 0:
        return 0.0, 0.0
    try:
        points = max(0.0, float(row.get("spread") or 0.0))
    except (TypeError, ValueError):
        points = 0.0
    multiplier = max(0.0, _float_env("BACKTEST_SPREAD_MULTIPLIER", 1.0))
    spread_price = points * infer_point(symbol) * multiplier
    return spread_price / risk_distance, points


def simulate_trade(df: pd.DataFrame, signal: dict[str, Any], max_holding_bars: int) -> BPRBacktestTrade | None:
    start_index = int(signal.get("start_index") or 0)
    if start_index <= 0 or start_index >= len(df) - 1:
        return None
    signal = apply_dynamic_stop(
        signal,
        df.iloc[max(0, start_index - 160) : start_index + 1],
        dynamic_stop_settings("BPR"),
        last_bar_is_closed=True,
    )
    direction = str(signal.get("direction") or "").upper()
    entry = float(signal.get("entry") or 0.0)
    stop_loss = float(signal.get("stop_loss") or 0.0)
    take_profit = float(signal.get("take_profit") or 0.0)
    risk_distance = abs(entry - stop_loss)
    if direction not in {"BUY", "SELL"} or entry <= 0 or stop_loss <= 0 or take_profit <= 0 or risk_distance <= 0:
        return None

    first_row = df.iloc[start_index]
    spread_r, spread_points = spread_cost(first_row, str(signal["symbol"]), risk_distance)
    if str(os.getenv("BACKTEST_SPREAD_ADJUST", "true")).strip().lower() in {"1", "true", "yes", "on"}:
        max_spread_r = _float_env("BACKTEST_MAX_SPREAD_R", 0.10)
        if max_spread_r > 0 and spread_r > max_spread_r:
            return None
    else:
        spread_r = 0.0

    exit_price = float(df.iloc[min(len(df) - 1, start_index + max_holding_bars)]["close"])
    closed_at = pd.Timestamp(df.iloc[min(len(df) - 1, start_index + max_holding_bars)]["time"]).to_pydatetime()
    result = "TIME"
    gross_r = 0.0
    current_sl_r = -1.0
    stage = 0
    final_rr = float(signal.get("risk_reward") or 0.0)
    exit_settings = smart_exit_settings("BPR")
    opened_at = pd.Timestamp(signal.get("opened_at")).to_pydatetime()
    future = df.iloc[start_index + 1 : min(len(df), start_index + max_holding_bars + 1)]
    for row_index, row in future.iterrows():
        high = float(row["high"])
        low = float(row["low"])
        happened_at = pd.Timestamp(row["time"]).to_pydatetime()
        active_stop = entry + risk_distance * current_sl_r if direction == "BUY" else entry - risk_distance * current_sl_r
        if direction == "BUY":
            stop_hit = low <= active_stop
            tp_hit = high >= take_profit
            if stop_hit and tp_hit:
                exit_price = active_stop
                result = "SL_SAME_BAR"
                gross_r = current_sl_r
                closed_at = happened_at
                break
            if stop_hit:
                exit_price = active_stop
                result = "SL" if current_sl_r < -0.05 else "TRAIL"
                gross_r = current_sl_r
                closed_at = happened_at
                break
            if tp_hit:
                exit_price = take_profit
                result = "TP"
                gross_r = final_rr
                closed_at = happened_at
                break
            while stage < int(final_rr) and high >= entry + risk_distance * (stage + 1):
                stage += 1
                current_sl_r = max(current_sl_r, 0.0 if stage == 1 else float(stage - 1))
        else:
            stop_hit = high >= active_stop
            tp_hit = low <= take_profit
            if stop_hit and tp_hit:
                exit_price = active_stop
                result = "SL_SAME_BAR"
                gross_r = current_sl_r
                closed_at = happened_at
                break
            if stop_hit:
                exit_price = active_stop
                result = "SL" if current_sl_r < -0.05 else "TRAIL"
                gross_r = current_sl_r
                closed_at = happened_at
                break
            if tp_hit:
                exit_price = take_profit
                result = "TP"
                gross_r = final_rr
                closed_at = happened_at
                break
            while stage < int(final_rr) and low <= entry - risk_distance * (stage + 1):
                stage += 1
                current_sl_r = max(current_sl_r, 0.0 if stage == 1 else float(stage - 1))

        smart_exit_delay = TIMEFRAME_MINUTES.get(exit_settings.timeframe, 15) * exit_settings.min_bars_open * 60
        if exit_settings.enabled and (happened_at - opened_at).total_seconds() >= smart_exit_delay:
            close_price = float(row["close"])
            unrealized_r = (close_price - entry) / risk_distance if direction == "BUY" else (entry - close_price) / risk_distance
            validity = evaluate_setup_validity(
                df.iloc[max(0, int(row_index) - exit_settings.lookback_bars) : int(row_index) + 1],
                direction=direction,
                entry=entry,
                profit=unrealized_r,
                settings=exit_settings,
                last_bar_is_closed=True,
            )
            if validity.get("invalid"):
                exit_price = close_price
                result = "SMART_EXIT"
                gross_r = unrealized_r
                closed_at = happened_at
                break
    if result == "TIME":
        gross_r = (exit_price - entry) / risk_distance if direction == "BUY" else (entry - exit_price) / risk_distance

    bpr = signal.get("bpr") or {}
    return BPRBacktestTrade(
        symbol=str(signal["symbol"]),
        timeframe=str(signal["timeframe"]),
        month=opened_at.strftime("%Y-%m"),
        opened_at=opened_at.isoformat(sep=" ", timespec="seconds"),
        closed_at=closed_at.isoformat(sep=" ", timespec="seconds"),
        direction=direction,
        entry=round(entry, 5),
        stop_loss=round(stop_loss, 5),
        take_profit=round(take_profit, 5),
        exit_price=round(exit_price, 5),
        result=result,
        r_multiple=round(gross_r - spread_r, 4),
        spread_r=round(spread_r, 4),
        spread_points=round(spread_points, 2),
        setup_score=int(signal.get("setup_score") or 0),
        bpr_low=round(float(bpr.get("low") or 0.0), 5),
        bpr_high=round(float(bpr.get("high") or 0.0), 5),
        reason="; ".join(signal.get("reasons") or []),
    )


def select_trades(trades: list[BPRBacktestTrade], max_per_day: int) -> list[BPRBacktestTrade]:
    if max_per_day <= 0:
        return sorted(trades, key=lambda item: item.opened_at)
    by_day: dict[str, list[BPRBacktestTrade]] = {}
    for trade in trades:
        by_day.setdefault(trade.opened_at[:10], []).append(trade)
    selected: list[BPRBacktestTrade] = []
    for day in sorted(by_day):
        ranked = sorted(by_day[day], key=lambda item: (-item.setup_score, item.opened_at))
        selected.extend(ranked[:max_per_day])
    return sorted(selected, key=lambda item: item.opened_at)


def summarize(trades: list[BPRBacktestTrade], starting_balance: float, risk_pct: float) -> tuple[dict[str, Any], pd.DataFrame]:
    balance = float(starting_balance)
    peak = balance
    max_drawdown = 0.0
    rows: list[dict[str, Any]] = []
    for trade in sorted(trades, key=lambda item: item.opened_at):
        risk_amount = balance * (risk_pct / 100.0)
        pnl = risk_amount * float(trade.r_multiple)
        balance += pnl
        peak = max(peak, balance)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - balance) / peak)
        row = trade.__dict__.copy()
        row["pnl"] = round(pnl, 2)
        row["balance"] = round(balance, 2)
        rows.append(row)
    wins = sum(1 for item in trades if float(item.r_multiple) > 0)
    losses = sum(1 for item in trades if float(item.r_multiple) < 0)
    summary = {
        "starting_balance": round(float(starting_balance), 2),
        "ending_balance": round(balance, 2),
        "net_profit": round(balance - float(starting_balance), 2),
        "return_pct": round(((balance / float(starting_balance)) - 1.0) * 100.0, 2) if starting_balance else 0.0,
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / len(trades) * 100.0, 2) if trades else 0.0,
        "net_r": round(sum(float(item.r_multiple) for item in trades), 2),
        "avg_r": round(sum(float(item.r_multiple) for item in trades) / len(trades), 4) if trades else 0.0,
        "avg_spread_r": round(sum(float(item.spread_r) for item in trades) / len(trades), 4) if trades else 0.0,
        "max_drawdown_pct": round(max_drawdown * 100.0, 2),
    }
    return summary, pd.DataFrame(rows)


def grouped_summary(trades: list[BPRBacktestTrade], starting_balance: float, risk_pct: float, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    groups = sorted({tuple(getattr(item, key) for key in keys) for item in trades})
    for group in groups:
        subset = [item for item in trades if tuple(getattr(item, key) for key in keys) == group]
        summary, _ = summarize(subset, starting_balance, risk_pct)
        for key, value in zip(keys, group):
            summary[key] = value
        rows.append(summary)
    return rows


def run_bpr_backtest(
    days: int,
    starting_balance: float,
    risk_pct: float,
    start_day: date | None = None,
    end_day: date | None = None,
    symbols_override: tuple[str, ...] | None = None,
    timeframes_override: tuple[str, ...] | None = None,
    min_score_override: int | None = None,
    rr_override: float | None = None,
    max_trades_per_day_override: int | None = None,
) -> dict[str, Any]:
    load_config()
    symbols = symbols_override or _csv_env("BPR_SYMBOLS", TRADE_SYMBOLS)
    timeframes = timeframes_override or _csv_env("BPR_TIMEFRAMES", ("M15", "M30"))
    max_holding_bars = max(1, _int_env("BPR_BACKTEST_MAX_HOLDING_BARS", 96))
    max_per_day = max(0, int(max_trades_per_day_override)) if max_trades_per_day_override is not None else max(0, _int_env("BPR_MAX_TRADES_PER_DAY", 3))
    settings = settings_from_env()
    symbol_rr = _float_map_env("BPR_SYMBOL_RR")
    symbol_min_score = _float_map_env("BPR_SYMBOL_MIN_SCORE")
    timeframe_rr = _pair_float_map_env("BPR_TIMEFRAME_RR")
    timeframe_min_score = _pair_float_map_env("BPR_TIMEFRAME_MIN_SCORE")
    symbol_timeframes = _symbol_timeframes_env("BPR_SYMBOL_TIMEFRAMES")
    if min_score_override is not None or rr_override is not None:
        settings = BPRSettings(
            reward_risk=max(0.5, float(rr_override if rr_override is not None else settings.reward_risk)),
            min_score=max(0, int(min_score_override if min_score_override is not None else settings.min_score)),
            fvg_lookback_bars=settings.fvg_lookback_bars,
            min_gap_atr=settings.min_gap_atr,
            min_displacement_atr=settings.min_displacement_atr,
            stop_atr_buffer=settings.stop_atr_buffer,
            max_zone_atr=settings.max_zone_atr,
            allow_pending=settings.allow_pending,
            max_signal_age_bars=settings.max_signal_age_bars,
        )

    def settings_for_symbol(symbol: str, timeframe: str) -> BPRSettings:
        pair = (symbol.upper(), timeframe.upper())
        selected_rr = settings.reward_risk if rr_override is not None else symbol_rr.get(symbol.upper(), settings.reward_risk)
        selected_min_score = settings.min_score if min_score_override is not None else symbol_min_score.get(symbol.upper(), settings.min_score)
        if rr_override is None:
            selected_rr = timeframe_rr.get(pair, selected_rr)
        if min_score_override is None:
            selected_min_score = timeframe_min_score.get(pair, selected_min_score)
        return BPRSettings(
            reward_risk=max(0.5, float(selected_rr)),
            min_score=max(0, int(selected_min_score)),
            fvg_lookback_bars=settings.fvg_lookback_bars,
            min_gap_atr=settings.min_gap_atr,
            min_displacement_atr=settings.min_displacement_atr,
            stop_atr_buffer=settings.stop_atr_buffer,
            max_zone_atr=settings.max_zone_atr,
            allow_pending=settings.allow_pending,
            max_signal_age_bars=settings.max_signal_age_bars,
        )
    selected_end = end_day or date.today()
    selected_start = start_day or selected_end - timedelta(days=max(1, days))
    end_dt = datetime.combine(selected_end, time.max)
    start_dt = datetime.combine(selected_start, time.min)
    client = MT5Client()
    mt5_status = client.terminal_status()
    all_trades: list[BPRBacktestTrade] = []
    availability: list[dict[str, Any]] = []

    for symbol in symbols:
        selected_timeframes = timeframes if timeframes_override is not None else symbol_timeframes.get(symbol.upper(), timeframes)
        for timeframe in selected_timeframes:
            symbol_settings = settings_for_symbol(symbol, timeframe)
            candles = client.fetch_candles(symbol, timeframe, start_dt - timedelta(days=20), end_dt, max_bars=120000)
            if candles is None or len(candles) < 250:
                availability.append({"symbol": symbol, "timeframe": timeframe, "status": "no_history", "candles": 0 if candles is None else len(candles)})
                continue
            df = add_atr(candles)
            signals = [
                signal
                for signal in generate_bpr_signals(df, symbol, timeframe, symbol_settings, include_pending=False)
                if start_dt <= pd.Timestamp(signal.get("opened_at")).to_pydatetime() <= end_dt
            ]
            trades = [trade for signal in signals for trade in [simulate_trade(df, signal, max_holding_bars)] if trade is not None]
            all_trades.extend(trades)
            availability.append(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "status": "ok",
                    "candles": len(df),
                    "signals": len(signals),
                    "trades": len(trades),
                }
            )
    client.shutdown()

    selected = select_trades(all_trades, max_per_day)
    summary, trades_frame = summarize(selected, starting_balance, risk_pct)
    by_symbol = grouped_summary(selected, starting_balance, risk_pct, ("symbol",))
    by_timeframe = grouped_summary(selected, starting_balance, risk_pct, ("timeframe",))
    monthly_symbol = grouped_summary(selected, starting_balance, risk_pct, ("month", "symbol"))
    by_symbol.sort(key=lambda item: float(item["ending_balance"]), reverse=True)
    monthly_symbol.sort(key=lambda item: (item["month"], item["symbol"]))

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = BPR_REPORT_DIR / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    trades_path = out_dir / "bpr_trades.csv"
    by_symbol_path = out_dir / "bpr_by_symbol.csv"
    by_timeframe_path = out_dir / "bpr_by_timeframe.csv"
    monthly_path = out_dir / "bpr_monthly_symbol.csv"
    report_path = out_dir / "bpr_backtest_report.json"
    trades_frame.to_csv(trades_path, index=False)
    pd.DataFrame(by_symbol).to_csv(by_symbol_path, index=False)
    pd.DataFrame(by_timeframe).to_csv(by_timeframe_path, index=False)
    pd.DataFrame(monthly_symbol).to_csv(monthly_path, index=False)
    report = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "window_start": start_dt.date().isoformat(),
        "window_end": end_dt.date().isoformat(),
        "starting_balance": starting_balance,
        "risk_pct": risk_pct,
        "symbols": symbols,
        "timeframes": timeframes,
        "settings": settings.__dict__,
        "symbol_rr": symbol_rr,
        "symbol_min_score": symbol_min_score,
        "timeframe_rr": {f"{symbol}.{timeframe}": value for (symbol, timeframe), value in timeframe_rr.items()},
        "timeframe_min_score": {f"{symbol}.{timeframe}": value for (symbol, timeframe), value in timeframe_min_score.items()},
        "symbol_timeframes": {key: list(value) for key, value in symbol_timeframes.items()},
        "summary": summary,
        "by_symbol": by_symbol,
        "by_timeframe": by_timeframe,
        "monthly_symbol": monthly_symbol,
        "availability": availability,
        "mt5_status": mt5_status,
        "paths": {
            "trades": str(trades_path),
            "by_symbol": str(by_symbol_path),
            "by_timeframe": str(by_timeframe_path),
            "monthly_symbol": str(monthly_path),
        },
        "notes": [
            "BPR is modeled as overlapping opposite FVGs followed by first retest/rejection.",
            "Same-bar TP/SL collisions are counted pessimistically as stop losses.",
            "Historical MT5 spread is charged as an R-multiple cost when BACKTEST_SPREAD_ADJUST=true.",
        ],
    }
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    report["path"] = str(report_path)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest Balanced Price Range strategy.")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--balance", type=float, default=300.0)
    parser.add_argument("--risk-pct", type=float, default=5.0)
    parser.add_argument("--symbols", default=None, help="Comma-separated BPR symbols override, e.g. XAUUSD,US30.")
    parser.add_argument("--timeframes", default=None, help="Comma-separated BPR timeframes override, e.g. M15,M30.")
    parser.add_argument("--min-score", type=int, default=None)
    parser.add_argument("--rr", type=float, default=None)
    parser.add_argument("--max-trades-per-day", type=int, default=None)
    args = parser.parse_args()
    start_day = date.fromisoformat(args.start) if args.start else None
    end_day = date.fromisoformat(args.end) if args.end else None
    report = run_bpr_backtest(
        args.days,
        args.balance,
        args.risk_pct,
        start_day=start_day,
        end_day=end_day,
        symbols_override=_csv_arg(args.symbols),
        timeframes_override=_csv_arg(args.timeframes),
        min_score_override=args.min_score,
        rr_override=args.rr,
        max_trades_per_day_override=args.max_trades_per_day,
    )
    print(json.dumps({"summary": report["summary"], "path": report["path"]}, indent=2))


if __name__ == "__main__":
    main()
