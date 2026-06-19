from __future__ import annotations

import argparse
import bisect
import csv
import json
import math
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5

from sniper_entry_bot import (
    TIMEFRAMES,
    adx_series,
    as_dict,
    atr_series,
    ema_series,
    load_json,
    macd_values,
    rates_to_dicts,
    rsi_series,
    session_vwap,
    sma,
)


@dataclass
class Candidate:
    logical_symbol: str
    broker_symbol: str
    side: str
    signal_time: int
    entry_time: int
    exit_time: int
    entry: float
    sl: float
    tp1: float
    tp2: float
    tp5: float
    exit_price: float
    result: str
    r_multiple: float
    risk_per_lot: float
    bull_pct: float
    bear_pct: float
    bias: str
    atr: float
    spread: float


def utc_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def iso_from_ts(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_symbol(logical: str, aliases: list[str]) -> str | None:
    names = [symbol.name for symbol in (mt5.symbols_get() or [])]
    candidates: list[str] = []
    for alias in aliases:
        if alias in names and alias not in candidates:
            candidates.append(alias)
    for alias in aliases:
        upper = alias.upper()
        for name in names:
            if name.upper().startswith(upper) and name not in candidates:
                candidates.append(name)
    best_name = None
    best_score = -1
    for name in candidates:
        mt5.symbol_select(name, True)
        info = mt5.symbol_info(name)
        tick = mt5.symbol_info_tick(name)
        if not info:
            continue
        score = 0
        if getattr(info, "trade_mode", 0) == mt5.SYMBOL_TRADE_MODE_FULL:
            score += 100
        if tick and tick.bid and tick.ask:
            score += 20
        if getattr(info, "visible", False):
            score += 5
        if "VIP" in name.upper():
            score += 3
        if score > best_score:
            best_name = name
            best_score = score
    if best_name:
        mt5.symbol_select(best_name, True)
    return best_name


def fetch_rates(symbol: str, timeframe: int, start: datetime, end: datetime) -> list[dict[str, float]]:
    rates = mt5.copy_rates_range(symbol, timeframe, start, end)
    return rates_to_dicts(rates)


def point_for(info: Any) -> float:
    digits = int(getattr(info, "digits", 5) or 5)
    point = float(getattr(info, "point", 0.0) or 0.0)
    return point if point > 0 else 10 ** -digits


def spread_price(candle: dict[str, float], point: float) -> float:
    return max(0.0, float(candle.get("spread") or 0.0) * point)


def rolling_sma(values: list[float], index: int, period: int) -> float | None:
    if index + 1 < period:
        return None
    return sum(values[index - period + 1 : index + 1]) / period


def normalize_lot_down(info: Any, raw_lot: float) -> float:
    step = float(getattr(info, "volume_step", 0.01) or 0.01)
    min_lot = float(getattr(info, "volume_min", step) or step)
    max_lot = float(getattr(info, "volume_max", 100.0) or 100.0)
    if raw_lot < min_lot:
        return 0.0
    steps = math.floor((min(raw_lot, max_lot) - min_lot + 1e-12) / step)
    return round(min_lot + steps * step, 4)


def risk_per_lot(symbol: str, side: str, entry: float, sl: float, info: Any) -> tuple[float, str]:
    order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
    calc = mt5.order_calc_profit(order_type, symbol, 1.0, entry, sl)
    risk = abs(float(calc or 0.0))
    if risk > 0:
        return risk, "mt5_order_calc_profit"
    tick_size = float(getattr(info, "trade_tick_size", 0.0) or 0.0)
    tick_value = float(getattr(info, "trade_tick_value", 0.0) or 0.0)
    if tick_size <= 0 or tick_value <= 0:
        return 0.0, "unavailable"
    return abs(entry - sl) / tick_size * tick_value, "tick_value_fallback"


def latest_index_at_or_before(times: list[int], timestamp: int) -> int | None:
    index = bisect.bisect_right(times, timestamp) - 1
    return index if index >= 0 else None


def first_index_at_or_after(times: list[int], timestamp: int) -> int | None:
    index = bisect.bisect_left(times, timestamp)
    return index if index < len(times) else None


def build_candidate(
    logical: str,
    broker: str,
    side: str,
    signal_time: int,
    entry_index: int,
    m5: list[dict[str, float]],
    info: Any,
    risk_unit: float,
    bull_pct: float,
    bear_pct: float,
    bias: str,
    atr: float,
    end_ts: int,
    manage_tp2_to_tp1: bool,
) -> Candidate | None:
    point = point_for(info)
    entry_bar = m5[entry_index]
    entry_spread = spread_price(entry_bar, point)
    entry_bid = float(entry_bar["open"])
    entry = entry_bid + entry_spread if side == "BUY" else entry_bid
    if side == "BUY":
        sl = entry - risk_unit
        tp1 = entry + risk_unit
        tp2 = entry + 2 * risk_unit
        tp5 = entry + 5 * risk_unit
    else:
        sl = entry + risk_unit
        tp1 = entry - risk_unit
        tp2 = entry - 2 * risk_unit
        tp5 = entry - 5 * risk_unit

    current_sl = sl
    stage = 0
    exit_price = float(m5[-1]["close"])
    exit_time = int(m5[-1]["time"])
    result = "timeout"
    risk = abs(entry - sl)
    if risk <= 0:
        return None

    for bar in m5[entry_index:]:
        bar_time = int(bar["time"])
        if bar_time > end_ts:
            break
        spread = spread_price(bar, point)
        high_bid = float(bar["high"])
        low_bid = float(bar["low"])
        high_ask = high_bid + spread
        low_ask = low_bid + spread

        if side == "BUY":
            if low_bid <= current_sl:
                exit_price = current_sl
                exit_time = bar_time
                result = "loss" if current_sl <= sl + risk * 0.05 else "trail_stop"
                break
            if high_bid >= tp5:
                exit_price = tp5
                exit_time = bar_time
                result = "win"
                break
            if manage_tp2_to_tp1 and stage < 2 and high_bid >= tp2:
                current_sl = max(current_sl, tp1)
                stage = 2
        else:
            if high_ask >= current_sl:
                exit_price = current_sl
                exit_time = bar_time
                result = "loss" if current_sl >= sl - risk * 0.05 else "trail_stop"
                break
            if low_ask <= tp5:
                exit_price = tp5
                exit_time = bar_time
                result = "win"
                break
            if manage_tp2_to_tp1 and stage < 2 and low_ask <= tp2:
                current_sl = min(current_sl, tp1)
                stage = 2

    if side == "BUY":
        r_multiple = (exit_price - entry) / risk
    else:
        r_multiple = (entry - exit_price) / risk
    per_lot, _ = risk_per_lot(broker, side, entry, sl, info)
    if per_lot <= 0:
        return None
    return Candidate(
        logical_symbol=logical,
        broker_symbol=broker,
        side=side,
        signal_time=signal_time,
        entry_time=int(entry_bar["time"]),
        exit_time=exit_time,
        entry=round(entry, int(getattr(info, "digits", 5) or 5)),
        sl=round(sl, int(getattr(info, "digits", 5) or 5)),
        tp1=round(tp1, int(getattr(info, "digits", 5) or 5)),
        tp2=round(tp2, int(getattr(info, "digits", 5) or 5)),
        tp5=round(tp5, int(getattr(info, "digits", 5) or 5)),
        exit_price=round(exit_price, int(getattr(info, "digits", 5) or 5)),
        result=result,
        r_multiple=round(float(r_multiple), 4),
        risk_per_lot=round(float(per_lot), 6),
        bull_pct=round(bull_pct, 2),
        bear_pct=round(bear_pct, 2),
        bias=bias,
        atr=round(float(atr), int(getattr(info, "digits", 5) or 5)),
        spread=round(entry_spread, int(getattr(info, "digits", 5) or 5)),
    )


def generate_candidates(
    logical: str,
    broker: str,
    config: dict[str, Any],
    start: datetime,
    end: datetime,
) -> tuple[list[Candidate], dict[str, Any]]:
    timeframe_name = str(config.get("timeframe", "H4"))
    timeframe = TIMEFRAMES[timeframe_name]
    timeframe_seconds = {"M1": 60, "M5": 300, "M15": 900, "M30": 1800, "H1": 3600, "H4": 14400}[timeframe_name]
    warmup_start = start - timedelta(days=80)
    fetch_end = end + timedelta(days=10)
    htf = fetch_rates(broker, timeframe, warmup_start, fetch_end)
    m5 = fetch_rates(broker, mt5.TIMEFRAME_M5, warmup_start, fetch_end)
    info = mt5.symbol_info(broker)
    if not info or len(htf) < 90 or len(m5) < 100:
        return [], {"status": "not_enough_data", "h4_bars": len(htf), "m5_bars": len(m5)}

    closes = [float(candle["close"]) for candle in htf]
    volumes = [float(candle.get("tick_volume", 0.0)) for candle in htf]
    ema9 = ema_series(closes, 9)
    ema21 = ema_series(closes, 21)
    atr14 = atr_series(htf, 14)
    rsi14 = rsi_series(closes, 14)
    macd_line, macd_signal = macd_values(closes)
    adx = adx_series(htf, 14)
    m5_times = [int(candle["time"]) for candle in m5]
    m5_rsi = rsi_series([float(candle["close"]) for candle in m5], 14)

    start_ts = int(start.timestamp())
    end_ts = int(end.timestamp())
    point = point_for(info)
    max_spread_ratio = float(config.get("strategy", {}).get("max_spread_atr_ratio", 0.35))
    atr_multiplier = float(config.get("strategy", {}).get("atr_multiplier", 1.5))
    manage_tp2_to_tp1 = bool(config.get("execution", {}).get("move_sl_to_tp1_at_tp2", True))

    candidates: list[Candidate] = []
    state = 0
    stats = {
        "status": "ok",
        "h4_bars": len(htf),
        "m5_bars": len(m5),
        "crosses": 0,
        "spread_filtered": 0,
        "indicator_skips": 0,
        "no_m5_entry": 0,
    }
    for index in range(1, len(htf) - 1):
        prev = index - 1
        values = (ema9[prev], ema21[prev], ema9[index], ema21[index], atr14[index], rsi14[index], macd_line[index], macd_signal[index], adx[index])
        if any(value is None for value in values):
            stats["indicator_skips"] += 1
            continue

        bar_open_ts = int(htf[index]["time"])
        signal_time = bar_open_ts + timeframe_seconds
        m5_rsi_index = latest_index_at_or_before(m5_times, signal_time)
        if m5_rsi_index is None or m5_rsi[m5_rsi_index] is None:
            stats["indicator_skips"] += 1
            continue

        cross_up = ema9[prev] <= ema21[prev] and ema9[index] > ema21[index]
        cross_down = ema9[prev] >= ema21[prev] and ema9[index] < ema21[index]
        trigger_buy = cross_up and state <= 0
        trigger_sell = cross_down and state >= 0
        if trigger_buy:
            state = 1
        elif trigger_sell:
            state = -1
        if signal_time < start_ts or signal_time > end_ts:
            continue
        if not (trigger_buy or trigger_sell):
            continue
        stats["crosses"] += 1

        spread = spread_price(htf[index], point)
        spread_ratio = spread / float(atr14[index]) if atr14[index] else 999.0
        if spread_ratio > max_spread_ratio:
            stats["spread_filtered"] += 1
            continue

        vwap = session_vwap(htf[: index + 1], index)
        vol_avg = rolling_sma(volumes, index, 20)
        close = closes[index]
        open_price = float(htf[index]["open"])
        rsi5m = float(m5_rsi[m5_rsi_index])
        bull_score = 0
        bull_score += 1 if vwap is not None and close > vwap else 0
        bull_score += 1 if rsi14[index] > 50 else 0
        bull_score += 1 if macd_line[index] > macd_signal[index] else 0
        bull_score += 1 if ema9[index] > ema21[index] else 0
        bull_score += 1 if adx[index] > 25 and close > ema9[index] else 0
        bull_score += 1 if vol_avg and volumes[index] > vol_avg and close > open_price else 0
        bull_score += 1 if rsi5m > 50 else 0
        bear_score = 0
        bear_score += 1 if vwap is not None and close < vwap else 0
        bear_score += 1 if rsi14[index] < 50 else 0
        bear_score += 1 if macd_line[index] < macd_signal[index] else 0
        bear_score += 1 if ema9[index] < ema21[index] else 0
        bear_score += 1 if adx[index] > 25 and close < ema9[index] else 0
        bear_score += 1 if vol_avg and volumes[index] > vol_avg and close < open_price else 0
        bear_score += 1 if rsi5m < 50 else 0
        bull_pct = bull_score / 7.0 * 100.0
        bear_pct = bear_score / 7.0 * 100.0
        bias = (
            "STRONG BULL"
            if bull_pct - bear_pct >= 40
            else "STRONG BEAR"
            if bear_pct - bull_pct >= 40
            else "MILD BULL"
            if bull_pct > bear_pct
            else "MILD BEAR"
        )

        entry_index = first_index_at_or_after(m5_times, signal_time)
        if entry_index is None:
            stats["no_m5_entry"] += 1
            continue
        candidate = build_candidate(
            logical,
            broker,
            "BUY" if trigger_buy else "SELL",
            signal_time,
            entry_index,
            m5,
            info,
            float(atr14[index]) * atr_multiplier,
            bull_pct,
            bear_pct,
            bias,
            float(atr14[index]),
            end_ts,
            manage_tp2_to_tp1,
        )
        if candidate:
            candidates.append(candidate)
    return candidates, stats


def apply_portfolio(
    candidates: list[Candidate],
    starting_balance: float,
    risk_pct: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    balance = starting_balance
    peak = balance
    max_dd = 0.0
    open_until: dict[str, int] = {}
    trades: list[dict[str, Any]] = []
    skipped_open = 0
    skipped_lot = 0
    for candidate in sorted(candidates, key=lambda item: (item.entry_time, item.logical_symbol)):
        if open_until.get(candidate.logical_symbol, 0) > candidate.entry_time:
            skipped_open += 1
            continue
        info = mt5.symbol_info(candidate.broker_symbol)
        if not info:
            skipped_lot += 1
            continue
        risk_budget = balance * risk_pct / 100.0
        lot = normalize_lot_down(info, risk_budget / candidate.risk_per_lot)
        if lot <= 0:
            skipped_lot += 1
            continue
        actual_risk = candidate.risk_per_lot * lot
        pnl = actual_risk * candidate.r_multiple
        before = balance
        balance = max(0.0, balance + pnl)
        peak = max(peak, balance)
        max_dd = max(max_dd, (peak - balance) / peak if peak else 0.0)
        open_until[candidate.logical_symbol] = candidate.exit_time
        row = asdict(candidate)
        row.update(
            {
                "entry_time_iso": iso_from_ts(candidate.entry_time),
                "exit_time_iso": iso_from_ts(candidate.exit_time),
                "lot": lot,
                "risk_budget": round(risk_budget, 2),
                "actual_risk": round(actual_risk, 2),
                "pnl": round(pnl, 2),
                "balance_before": round(before, 2),
                "balance_after": round(balance, 2),
            }
        )
        trades.append(row)
    wins = sum(1 for trade in trades if trade["r_multiple"] > 0)
    losses = sum(1 for trade in trades if trade["r_multiple"] < 0)
    summary = {
        "starting_balance": round(starting_balance, 2),
        "ending_balance": round(balance, 2),
        "net_profit": round(balance - starting_balance, 2),
        "return_pct": round((balance / starting_balance - 1) * 100, 2) if starting_balance else 0.0,
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / len(trades) * 100, 2) if trades else 0.0,
        "net_r": round(sum(float(trade["r_multiple"]) for trade in trades), 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "skipped_same_symbol_open": skipped_open,
        "skipped_lot_too_small": skipped_lot,
    }
    return summary, trades


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest the sniper entry strategy on MT5 history.")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default="2026-06-19")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--balance", type=float, default=300.0)
    parser.add_argument("--risk-pct", type=float, default=None)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = root / config_path
    config = load_json(config_path)
    end = utc_datetime(args.end) + timedelta(days=1) - timedelta(seconds=1)
    start = utc_datetime(args.start) if args.start else end - timedelta(days=args.days)
    risk_pct = float(args.risk_pct if args.risk_pct is not None else config.get("risk", {}).get("balance_risk_pct", 5.0))

    mt5_path = config.get("mt5_path")
    ok = mt5.initialize(path=mt5_path) if mt5_path else mt5.initialize()
    if not ok:
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

    try:
        created_at = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_dir = root / "reports" / "sniper_backtest" / created_at
        out_dir.mkdir(parents=True, exist_ok=True)
        all_candidates: list[Candidate] = []
        availability: list[dict[str, Any]] = []
        for logical, aliases in config.get("symbols", {}).items():
            broker = resolve_symbol(logical, aliases)
            if not broker:
                availability.append({"logical_symbol": logical, "broker_symbol": None, "status": "unavailable"})
                continue
            candidates, stats = generate_candidates(logical, broker, config, start, end)
            all_candidates.extend(candidates)
            availability.append({"logical_symbol": logical, "broker_symbol": broker, "signals": len(candidates), **stats})

        portfolio_summary, portfolio_trades = apply_portfolio(all_candidates, args.balance, risk_pct)
        per_symbol: list[dict[str, Any]] = []
        per_symbol_trades: dict[str, list[dict[str, Any]]] = {}
        for logical in sorted({candidate.logical_symbol for candidate in all_candidates}):
            symbol_candidates = [candidate for candidate in all_candidates if candidate.logical_symbol == logical]
            summary, trades = apply_portfolio(symbol_candidates, args.balance, risk_pct)
            summary["symbol"] = logical
            per_symbol.append(summary)
            per_symbol_trades[logical] = trades
        per_symbol.sort(key=lambda item: float(item["ending_balance"]), reverse=True)

        trades_path = out_dir / "portfolio_trades.csv"
        with trades_path.open("w", newline="", encoding="utf-8") as handle:
            fieldnames = list(portfolio_trades[0].keys()) if portfolio_trades else [
                "logical_symbol",
                "broker_symbol",
                "side",
                "entry_time_iso",
                "exit_time_iso",
                "result",
                "r_multiple",
                "lot",
                "pnl",
                "balance_after",
            ]
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(portfolio_trades)

        per_symbol_path = out_dir / "per_symbol_summary.csv"
        with per_symbol_path.open("w", newline="", encoding="utf-8") as handle:
            fieldnames = list(per_symbol[0].keys()) if per_symbol else ["symbol", "ending_balance", "trades"]
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(per_symbol)

        report = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "window_start": start.isoformat(),
            "window_end": end.isoformat(),
            "strategy": {
                "timeframe": config.get("timeframe", "H4"),
                "entry": "EMA 9/21 cross on closed bar, entered at next M5 open",
                "stop": f"ATR(14) * {config.get('strategy', {}).get('atr_multiplier', 1.5)}",
                "target": "TP5 / 5R",
                "management": "If TP2 is hit, SL trails to TP1 when enabled.",
                "note": "Live max_signal_age/bootstrap filters are operational safeguards and are not applied to historical bars.",
            },
            "starting_balance": args.balance,
            "risk_pct": risk_pct,
            "portfolio_summary": portfolio_summary,
            "per_symbol_summary": per_symbol,
            "availability": availability,
            "paths": {
                "portfolio_trades": str(trades_path),
                "per_symbol_summary": str(per_symbol_path),
            },
        }
        report_path = out_dir / "sniper_backtest_report.json"
        report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        print(json.dumps({"report": str(report_path), "portfolio": portfolio_summary, "per_symbol": per_symbol}, indent=2))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
