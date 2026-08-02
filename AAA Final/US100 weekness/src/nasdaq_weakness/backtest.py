from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
import math

import numpy as np
import pandas as pd

from .config import Config
from .models import BacktestResult, PlannedOrder, Stats, Trade
from .strategy import NY, plans_between, resample_bars


def _session_exit(ny_date: date, config: Config) -> pd.Timestamp:
    local = pd.Timestamp(
        year=ny_date.year,
        month=ny_date.month,
        day=ny_date.day,
        hour=config.session_exit_ny[0],
        minute=config.session_exit_ny[1],
        tz=NY,
    )
    return local.tz_convert("UTC")


def _spread_price(row, point: float, fallback: float) -> float:
    value = float(row["spread"]) * point
    return value if value > 0 else fallback


def _first_fill_index(
    bars: pd.DataFrame,
    order: PlannedOrder,
    point: float,
    fallback_spread: float,
    max_spread: float,
) -> int | None:
    times = bars["time"]
    left = int(times.searchsorted(pd.Timestamp(order.signal_time), side="left"))
    right = int(
        times.searchsorted(pd.Timestamp(order.expiry_time), side="left")
    )
    candidates = bars.iloc[left:right]
    for index, row in candidates.iterrows():
        spread = _spread_price(row, point, fallback_spread)
        if spread > max_spread:
            continue
        if order.kind == "MARKET":
            return int(index)
        if order.kind == "SELL_LIMIT" and float(row["high"]) >= order.entry:
            return int(index)
        if order.kind == "SELL_STOP" and float(row["low"]) <= order.entry:
            return int(index)
    return None


def _simulate_filled(
    bars: pd.DataFrame,
    m15: pd.DataFrame,
    symbol: str,
    ny_date: date,
    order: PlannedOrder,
    fill_index: int,
    point: float,
    fallback_spread: float,
    config: Config,
) -> Trade | None:
    fill = bars.loc[fill_index]
    planned = (
        float(fill["open"]) if order.kind == "MARKET" else order.entry
    )
    entry = planned - config.slippage_price
    if order.stop <= entry:
        return None
    initial_risk = order.stop - entry
    stop = order.stop
    target = order.target
    exit_limit = _session_exit(ny_date, config)
    end_index = int(
        bars["time"].searchsorted(exit_limit, side="left")
    )
    sample = bars.iloc[fill_index:end_index]
    last_m15_close = pd.Timestamp(order.signal_time)
    trail_history: list[float] = []
    closed_slice = m15.loc[
        (m15["time"] + pd.Timedelta(minutes=15) > last_m15_close)
        & (m15["time"] + pd.Timedelta(minutes=15) <= exit_limit)
    ].copy()
    closed_records = list(closed_slice.to_dict("records"))
    closed_pointer = 0

    def result(row, price: float, reason: str) -> Trade:
        risk_multiple = (entry - price) / initial_risk
        return Trade(
            symbol=symbol,
            ny_date=ny_date.isoformat(),
            setup=order.setup,
            order_kind=order.kind,
            entry_time=pd.Timestamp(fill["time"]).to_pydatetime(),
            exit_time=pd.Timestamp(row["time"]).to_pydatetime(),
            entry=entry,
            stop=order.stop,
            exit_price=price,
            target=target,
            risk_share=order.risk_share,
            r_multiple=float(risk_multiple),
            reason=reason,
        )

    for _, row in sample.iterrows():
        spread = _spread_price(row, point, fallback_spread)
        ask_high = float(row["high"]) + spread
        ask_low = float(row["low"]) + spread
        ask_close = float(row["close"]) + spread
        # Conservative same-minute ordering: a stop wins over a target.
        if ask_high >= stop:
            return result(row, stop, "STOP")
        if target is not None and ask_low <= target:
            return result(row, target, "TARGET")

        minute_close = pd.Timestamp(row["time"]) + pd.Timedelta(minutes=1)
        while closed_pointer < len(closed_records):
            closed = closed_records[closed_pointer]
            close_time = pd.Timestamp(closed["time"]) + pd.Timedelta(minutes=15)
            if close_time > minute_close:
                break
            closed_pointer += 1
            last_m15_close = close_time
            if float(closed["close"]) > order.invalidation_high:
                return result(row, ask_close, "BODY_INVALIDATION")
            if order.runner:
                trail_history.append(float(closed["high"]))
                if len(trail_history) >= config.runner_trail_bars:
                    candidate = (
                        trail_history[-config.runner_trail_bars]
                        + config.runner_buffer_points
                        * config.note_point_to_price
                        + spread
                    )
                    if candidate < stop:
                        if candidate <= ask_close:
                            return result(row, ask_close, "TRAIL_CROSSED")
                        stop = candidate

    if sample.empty:
        return None
    final = sample.iloc[-1]
    final_spread = _spread_price(final, point, fallback_spread)
    return result(
        final, float(final["close"]) + final_spread, "SESSION_EXIT"
    )


def _stats(
    trades: list[Trade],
    risk_pct: float,
    initial_balance: float,
) -> Stats:
    by_day: dict[str, list[Trade]] = defaultdict(list)
    for trade in trades:
        by_day[trade.ny_date].append(trade)
    idea_results = [
        sum(item.r_multiple * item.risk_share for item in by_day[key])
        for key in sorted(by_day)
    ]
    wins = sum(value > 1e-9 for value in idea_results)
    losses = sum(value < -1e-9 for value in idea_results)
    breakeven = len(idea_results) - wins - losses
    gross_win = sum(value for value in idea_results if value > 0)
    gross_loss = -sum(value for value in idea_results if value < 0)
    profit_factor = (
        gross_win / gross_loss
        if gross_loss > 0
        else (math.inf if gross_win > 0 else 0.0)
    )
    balance = initial_balance
    peak = balance
    max_drawdown = 0.0
    max_losses = 0
    loss_run = 0
    for value in idea_results:
        balance *= 1 + (risk_pct / 100) * value
        peak = max(peak, balance)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - balance) / peak * 100)
        if value < 0:
            loss_run += 1
            max_losses = max(max_losses, loss_run)
        else:
            loss_run = 0
    count = len(idea_results)
    return Stats(
        trades=count,
        wins=wins,
        losses=losses,
        breakeven=breakeven,
        win_rate=wins / count * 100 if count else 0.0,
        profit_factor=float(profit_factor),
        expectancy_r=float(np.mean(idea_results)) if count else 0.0,
        net_r=float(sum(idea_results)),
        net_profit=float(balance - initial_balance),
        ending_balance=float(balance),
        max_drawdown_pct=float(max_drawdown),
        max_consecutive_losses=max_losses,
    )


def run_backtest(
    frame_m1: pd.DataFrame,
    symbol: str,
    config: Config,
    *,
    point: float,
    start_date: date | None = None,
    end_date: date | None = None,
    initial_balance: float = 10_000.0,
) -> BacktestResult:
    frame = frame_m1.sort_values("time").reset_index(drop=True)
    positive_spreads = frame.loc[frame["spread"] > 0, "spread"]
    fallback = (
        float(positive_spreads.median()) * point
        if not positive_spreads.empty
        else min(1.0, config.max_spread_price)
    )
    m15 = resample_bars(frame, "15min")
    plans = plans_between(frame, symbol, config, start_date, end_date)
    trades: list[Trade] = []
    for plan in plans:
        ny_date = date.fromisoformat(plan.ny_date)
        fills: list[tuple[int, PlannedOrder]] = []
        for order in plan.orders:
            found = _first_fill_index(
                frame,
                order,
                point,
                fallback,
                config.max_spread_price,
            )
            if found is not None:
                fills.append((found, order))
        if not fills:
            continue
        if plan.setup != "S1" and config.pending_mode == "OCO":
            first_index = min(item[0] for item in fills)
            simultaneous = [item for item in fills if item[0] == first_index]
            # If sequence inside one M1 candle is unknowable, choose the
            # lower sell-stop fill as the conservative OCO assumption.
            selected = next(
                (
                    item
                    for item in simultaneous
                    if item[1].kind == "SELL_STOP"
                ),
                simultaneous[0],
            )
            fills = [selected]
        for fill_index, order in fills:
            trade = _simulate_filled(
                frame,
                m15,
                symbol,
                ny_date,
                order,
                fill_index,
                point,
                fallback,
                config,
            )
            if trade is not None:
                trades.append(trade)
    if start_date is None:
        start = pd.Timestamp(frame["time"].iloc[0]).to_pydatetime()
    else:
        start = datetime.combine(start_date, datetime.min.time(), tzinfo=NY)
    if end_date is None:
        end = pd.Timestamp(frame["time"].iloc[-1]).to_pydatetime()
    else:
        end = datetime.combine(end_date, datetime.max.time(), tzinfo=NY)
    parameters = {
        "risk_pct": config.risk_pct,
        "strategy_mode": config.strategy_mode,
        "note_point_to_price": config.note_point_to_price,
        "target_rr": config.target_rr,
        "pending_mode": config.pending_mode,
        "s2a_entry_model": config.s2a_entry_model,
        "s2b_entry_model": config.s2b_entry_model,
        "runner_trail_bars": config.runner_trail_bars,
        "runner_buffer_points": config.runner_buffer_points,
        "slippage_price": config.slippage_price,
        "max_spread_price": config.max_spread_price,
    }
    return BacktestResult(
        symbol=symbol,
        start=start,
        end=end,
        parameters=parameters,
        trades=tuple(trades),
        stats=_stats(trades, config.risk_pct, initial_balance),
    )
