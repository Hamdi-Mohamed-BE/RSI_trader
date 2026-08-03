from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import Iterable

import numpy as np

from weekend_direction_model import MarketSeries


@dataclass(frozen=True)
class HoldConfig:
    signal_policy: str
    lead_minutes: int
    stop_spec: str
    reward_risk: float
    max_hold_minutes: int


@dataclass(frozen=True)
class DirectionSignal:
    sample_index: int
    reopen_utc: str
    side: str


@dataclass(frozen=True)
class HoldTrade:
    sample_index: int
    reopen_utc: str
    side: str
    entry_time_utc: str
    exit_time_utc: str
    entry_price: float
    stop_loss: float
    take_profit: float
    exit_price: float
    stop_usd: float
    result_r: float
    outcome: str
    spread_usd_at_entry: float


def _ask(series: MarketSeries, index: int, field: str) -> float:
    values = getattr(series, field)
    return float(values[index]) + float(series.spread[index]) * series.point


def entry_index_for_lead(close_index: int, lead_minutes: int) -> int:
    if lead_minutes < 1:
        raise ValueError("lead_minutes must be at least 1")
    return close_index - lead_minutes + 1


def resolve_stop(series: MarketSeries, entry_index: int, stop_spec: str) -> float:
    if stop_spec.startswith("fixed_"):
        return float(stop_spec.split("_", 1)[1])
    end = entry_index - 1
    start = end - 59
    if start < 1:
        raise ValueError("At least 60 completed pre-entry bars are required")
    high = series.high[start : end + 1]
    low = series.low[start : end + 1]
    previous_close = series.close[start - 1 : end]
    if stop_spec.startswith("atr60_"):
        multiplier = float(stop_spec.split("_")[-1])
        true_range = np.maximum(high - low, np.maximum(np.abs(high - previous_close), np.abs(low - previous_close)))
        raw = float(np.mean(true_range)) * multiplier
    elif stop_spec.startswith("range60_"):
        multiplier = float(stop_spec.split("_")[-1])
        raw = float(np.max(high) - np.min(low)) * multiplier
    else:
        raise ValueError(f"Unknown stop specification: {stop_spec}")
    return float(np.clip(raw, 3.0, 30.0))


def simulate_trade(
    series: MarketSeries,
    signal: DirectionSignal,
    close_index: int,
    config: HoldConfig,
) -> HoldTrade:
    entry_index = entry_index_for_lead(close_index, config.lead_minutes)
    stop_usd = resolve_stop(series, entry_index, config.stop_spec)
    is_buy = signal.side == "BUY"
    entry_price = _ask(series, entry_index, "open") if is_buy else float(series.open[entry_index])
    stop = entry_price - stop_usd if is_buy else entry_price + stop_usd
    target = entry_price + stop_usd * config.reward_risk if is_buy else entry_price - stop_usd * config.reward_risk
    gap_offsets = np.flatnonzero(np.diff(series.time[entry_index:]) >= 24 * 60 * 60)
    if len(gap_offsets) == 0:
        raise RuntimeError(f"No weekly reopen found after {signal.reopen_utc}")
    reopen_index = entry_index + int(gap_offsets[0]) + 1
    final_index = (
        reopen_index
        if config.max_hold_minutes == 0
        else min(len(series.time) - 1, reopen_index + config.max_hold_minutes - 1)
    )
    exit_index = final_index
    outcome = "TIME"
    exit_price = float(series.close[final_index]) if is_buy else _ask(series, final_index, "close")

    for index in range(entry_index, final_index + 1):
        gap_open = index > entry_index and int(series.time[index]) - int(series.time[index - 1]) >= 24 * 60 * 60
        if is_buy:
            bid_open = float(series.open[index])
            if gap_open and bid_open <= stop:
                exit_index, exit_price, outcome = index, bid_open, "SL_GAP"
                break
            if gap_open and bid_open >= target:
                exit_index, exit_price, outcome = index, target, "TP_GAP"
                break
            stop_hit = float(series.low[index]) <= stop
            target_hit = float(series.high[index]) >= target
        else:
            ask_open = _ask(series, index, "open")
            if gap_open and ask_open >= stop:
                exit_index, exit_price, outcome = index, ask_open, "SL_GAP"
                break
            if gap_open and ask_open <= target:
                exit_index, exit_price, outcome = index, target, "TP_GAP"
                break
            stop_hit = _ask(series, index, "high") >= stop
            target_hit = _ask(series, index, "low") <= target
        if stop_hit:
            exit_index, exit_price, outcome = index, stop, "SL"
            break
        if target_hit:
            exit_index, exit_price, outcome = index, target, "TP"
            break
        if index == reopen_index and config.max_hold_minutes == 0:
            exit_index = index
            exit_price = float(series.open[index]) if is_buy else _ask(series, index, "open")
            outcome = "REOPEN"
            break

    result_r = (exit_price - entry_price) / stop_usd if is_buy else (entry_price - exit_price) / stop_usd
    return HoldTrade(
        sample_index=signal.sample_index,
        reopen_utc=signal.reopen_utc,
        side=signal.side,
        entry_time_utc=np.datetime_as_string(np.datetime64(int(series.time[entry_index]), "s"), timezone="UTC"),
        exit_time_utc=np.datetime_as_string(np.datetime64(int(series.time[exit_index]), "s"), timezone="UTC"),
        entry_price=round(entry_price, 6),
        stop_loss=round(stop, 6),
        take_profit=round(target, 6),
        exit_price=round(exit_price, 6),
        stop_usd=round(stop_usd, 6),
        result_r=round(float(result_r), 6),
        outcome=outcome,
        spread_usd_at_entry=round(float(series.spread[entry_index]) * series.point, 6),
    )


def calculate_metrics(trades: Iterable[HoldTrade]) -> dict:
    items = list(trades)
    values = [trade.result_r for trade in items]
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    equity = 0.0
    peak = 0.0
    drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return {
        "trades": len(items),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(100.0 * len(wins) / len(items), 2) if items else 0.0,
        "profit_factor": round(gross_profit / gross_loss, 3) if gross_loss else (inf if gross_profit else 0.0),
        "net_r": round(sum(values), 4),
        "average_r": round(sum(values) / len(items), 4) if items else 0.0,
        "gross_profit_r": round(gross_profit, 4),
        "gross_loss_r": round(gross_loss, 4),
        "max_drawdown_r": round(drawdown, 4),
        "gap_stop_count": sum(trade.outcome == "SL_GAP" for trade in items),
        "gap_target_count": sum(trade.outcome == "TP_GAP" for trade in items),
        "timeout_count": sum(trade.outcome == "TIME" for trade in items),
    }


def compounded_metrics(trades: Iterable[HoldTrade], risk_fraction: float) -> dict:
    equity = 1.0
    peak = 1.0
    drawdown = 0.0
    for trade in trades:
        equity *= max(0.0, 1.0 + risk_fraction * trade.result_r)
        peak = max(peak, equity)
        drawdown = max(drawdown, 1.0 - equity / peak)
    return {
        "risk_pct": round(100.0 * risk_fraction, 2),
        "return_pct": round(100.0 * (equity - 1.0), 2),
        "max_drawdown_pct": round(100.0 * drawdown, 2),
    }
