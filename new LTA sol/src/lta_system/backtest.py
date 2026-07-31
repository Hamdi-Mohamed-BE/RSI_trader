from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd

from .config import AppConfig
from .models import BacktestStats, Signal, Trade
from .profiles import build_completed_profile_maps, profiles_for_row
from .risk import cash_result, risk_cash
from .sessions import resample_ohlcv, timeframe_rule
from .strategy import evaluate_signals
from .structure import enrich_structure
from .zones import build_zone_timeline


@dataclass(frozen=True)
class BacktestResult:
    stats: BacktestStats
    trades: tuple[Trade, ...]
    h1: pd.DataFrame


def _simulate_trade(
    h1: pd.DataFrame,
    signal_index: int,
    signal: Signal,
    balance: float,
    risk_pct: float,
    spread_price: float,
    max_hold_bars: int = 48,
) -> Trade | None:
    entry_index = signal_index + 1
    if entry_index >= len(h1):
        return None
    direction = 1 if signal.direction == "buy" else -1
    entry = float(h1.iloc[entry_index]["open"]) + direction * spread_price / 2.0
    stop = signal.stop
    risk_distance = (entry - stop) * direction
    if risk_distance <= 0:
        return None
    target = entry + direction * signal.rr * risk_distance
    end = min(len(h1) - 1, entry_index + max_hold_bars)
    exit_price = float(h1.iloc[end]["close"])
    exit_index = end
    exit_reason = "TIME"
    mae = 0.0
    mfe = 0.0
    for bar_index in range(entry_index, end + 1):
        bar = h1.iloc[bar_index]
        adverse = (
            entry - float(bar["low"])
            if direction == 1
            else float(bar["high"]) - entry
        )
        favorable = (
            float(bar["high"]) - entry
            if direction == 1
            else entry - float(bar["low"])
        )
        mae = max(mae, adverse / risk_distance)
        mfe = max(mfe, favorable / risk_distance)
        stop_hit = (
            float(bar["low"]) <= stop
            if direction == 1
            else float(bar["high"]) >= stop
        )
        target_hit = (
            float(bar["high"]) >= target
            if direction == 1
            else float(bar["low"]) <= target
        )
        # Pessimistic same-bar resolution: the stop is assumed first.
        if stop_hit:
            exit_price = stop
            exit_index = bar_index
            exit_reason = "STOP"
            break
        if target_hit:
            exit_price = target
            exit_index = bar_index
            exit_reason = "TARGET"
            break
    result_r = direction * (exit_price - entry) / risk_distance
    if exit_reason == "TIME":
        result_r -= spread_price / max(risk_distance, 1e-9)
    at_risk = risk_cash(balance, risk_pct)
    pnl, balance_after = cash_result(balance, risk_pct, result_r)
    return Trade(
        signal_time=signal.time,
        entry_time=pd.Timestamp(h1.iloc[entry_index]["time"]).to_pydatetime(),
        exit_time=pd.Timestamp(h1.iloc[exit_index]["time"]).to_pydatetime(),
        symbol=signal.symbol,
        direction=signal.direction,
        model=signal.model,
        grade=signal.grade,
        entry=entry,
        stop=stop,
        target=target,
        exit_price=exit_price,
        result_r=result_r,
        risk_cash=at_risk,
        pnl_cash=pnl,
        balance_after=balance_after,
        exit_reason=exit_reason,
        mae_r=mae,
        mfe_r=mfe,
    )


def _statistics(
    trades: list[Trade],
    starting_balance: float,
) -> BacktestStats:
    results = [trade.result_r for trade in trades]
    wins = sum(value > 1e-9 for value in results)
    losses = sum(value < -1e-9 for value in results)
    breakeven = len(results) - wins - losses
    gross_win = sum(value for value in results if value > 0)
    gross_loss = abs(sum(value for value in results if value < 0))
    profit_factor = gross_win / gross_loss if gross_loss else math.inf if gross_win else 0.0
    ending = trades[-1].balance_after if trades else starting_balance
    peaks = [starting_balance]
    maximum = starting_balance
    max_drawdown = 0.0
    consecutive = 0
    max_consecutive = 0
    for trade in trades:
        maximum = max(maximum, trade.balance_after)
        peaks.append(maximum)
        drawdown = (
            (maximum - trade.balance_after) / maximum * 100.0
            if maximum > 0
            else 0.0
        )
        max_drawdown = max(max_drawdown, drawdown)
        if trade.result_r < 0:
            consecutive += 1
            max_consecutive = max(max_consecutive, consecutive)
        else:
            consecutive = 0
    return BacktestStats(
        trades=len(trades),
        wins=wins,
        losses=losses,
        breakeven=breakeven,
        win_rate=wins / len(trades) * 100.0 if trades else 0.0,
        profit_factor=profit_factor,
        expectancy_r=sum(results) / len(results) if results else 0.0,
        net_r=sum(results),
        net_profit=ending - starting_balance,
        ending_balance=ending,
        max_drawdown_pct=max_drawdown,
        max_consecutive_losses=max_consecutive,
    )


def run_backtest(
    m1: pd.DataFrame,
    symbol: str,
    config: AppConfig,
    starting_balance: float = 10_000.0,
    spread_multiplier: float = 1.0,
    profile_rows: int | None = None,
) -> BacktestResult:
    analysis = enrich_structure(
        resample_ohlcv(m1, timeframe_rule(config.analysis_timeframe))
    )
    execution = enrich_structure(
        resample_ohlcv(m1, timeframe_rule(config.execution_timeframe))
    )
    htf_columns = analysis[
        ["time", "trend", "structure_break", "ema20", "ema50"]
    ].rename(
        columns={
            "trend": "htf_trend",
            "structure_break": "htf_structure_break",
            "ema20": "htf_ema20",
            "ema50": "htf_ema50",
        }
    )
    execution = pd.merge_asof(
        execution.sort_values("time"),
        htf_columns.sort_values("time"),
        on="time",
        direction="backward",
    )
    execution["ltf_trend"] = execution["trend"]
    execution["ltf_structure_break"] = execution["structure_break"]
    execution["trend"] = execution["htf_trend"].fillna(execution["trend"])
    execution["structure_break"] = execution["htf_structure_break"].fillna(
        execution["structure_break"]
    )
    h1 = execution
    zone_timeline = build_zone_timeline(
        analysis,
        config.zone_lookback,
        config.zone_max_touches,
    )
    daily, weekly = build_completed_profile_maps(
        m1,
        profile_rows or config.profile_rows,
        config.value_area_pct,
    )
    price_changes = m1["close"].diff().abs()
    positive_changes = price_changes[price_changes > 0]
    point = (
        max(float(np.quantile(positive_changes, 0.01)), 1e-8)
        if not positive_changes.empty
        else 1e-5
    )
    spreads = m1.get("spread", pd.Series([0]))
    median_spread = float(spreads[spreads > 0].median()) if (spreads > 0).any() else 0.0
    spread_price = median_spread * point * spread_multiplier
    balance = starting_balance
    trades: list[Trade] = []
    next_available = 0
    loss_streak_day: object | None = None
    loss_streak = 0
    for index in range(80, len(h1) - 1):
        if index < next_available:
            continue
        row = h1.iloc[index]
        current_day = row["session_day"]
        if loss_streak_day != current_day:
            loss_streak_day = current_day
            loss_streak = 0
        if loss_streak >= 2:
            continue
        profiles = profiles_for_row(row, daily, weekly)
        if not profiles:
            continue
        analysis_times = analysis["time"].to_numpy()
        analysis_index = int(
            analysis["time"].searchsorted(row["time"], side="right") - 1
        )
        zones = (
            zone_timeline[analysis_index]
            if 0 <= analysis_index < len(zone_timeline)
            else ()
        )
        signals = evaluate_signals(
            h1,
            index,
            symbol,
            profiles,
            zones,
            config,
        )
        if not signals:
            continue
        trade = _simulate_trade(
            h1,
            index,
            signals[0],
            balance,
            config.risk_pct,
            spread_price,
            max_hold_bars=config.max_hold_bars,
        )
        if trade is None:
            continue
        trades.append(trade)
        balance = trade.balance_after
        exit_positions = h1.index[h1["time"] == pd.Timestamp(trade.exit_time)].tolist()
        next_available = (exit_positions[0] + 1) if exit_positions else index + 2
        loss_streak = loss_streak + 1 if trade.result_r < 0 else 0
    return BacktestResult(
        stats=_statistics(trades, starting_balance),
        trades=tuple(trades),
        h1=h1,
    )
