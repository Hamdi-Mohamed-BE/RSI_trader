from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, timedelta, timezone
from typing import Iterable

import pandas as pd

from .config import Config


@dataclass(frozen=True, slots=True)
class Plan:
    session_date: date
    signal_time: datetime
    expiry: datetime
    side: int
    rank: str
    entry: float
    initial_stop: float
    d1_body_fraction: float
    h4_body_fraction: float
    reason: str = "D1+H4 aligned"
    h1_pattern: str = "none"
    reference_level: float | None = None
    target: float | None = None


@dataclass(frozen=True, slots=True)
class Trade:
    session_date: date
    side: int
    rank: str
    signal_time: datetime
    entry_time: datetime
    exit_time: datetime
    entry: float
    initial_stop: float
    exit_price: float
    r_multiple: float
    mae_r: float
    exit_reason: str
    risk_pct_used: float = 0.0
    cash_pnl: float = 0.0

    def row(self) -> dict[str, object]:
        result = asdict(self)
        for key in ("signal_time", "entry_time", "exit_time"):
            result[key] = result[key].isoformat()
        result["session_date"] = self.session_date.isoformat()
        result["direction"] = "BUY" if self.side > 0 else "SELL"
        return result


@dataclass(frozen=True, slots=True)
class Metrics:
    trades: int
    wins: int
    losses: int
    win_rate_pct: float
    profit_factor: float
    net_r: float
    ending_balance: float
    return_pct: float
    max_realized_dd_pct: float
    max_intratrade_dd_pct: float
    start: str
    end: str
    gross_profit_cash: float = 0.0
    gross_loss_cash: float = 0.0
    max_risk_pct_used: float = 0.0
    final_loss_streak: int = 0
    progression_enabled: bool = False
    trailing_enabled: bool = True
    target_rr: float = 1.7
    cash_weighted_profit_factor: float = 0.0


def loss_streak_from_results(results: Iterable[float]) -> int:
    """Return consecutive closed losses; wins reset and flat trades preserve it."""
    streak = 0
    for result in results:
        if result < 0:
            streak += 1
        elif result > 0:
            streak = 0
    return streak


def risk_pct_for_streak(
    base_risk_pct: float,
    loss_streak: int,
    multiplier: float = 1.6,
    cap_pct: float | None = None,
) -> float:
    """Exact research progression, optionally capped for live-account safety."""
    risk_pct = base_risk_pct * multiplier**max(0, loss_streak)
    return min(risk_pct, cap_pct) if cap_pct is not None else risk_pct


def _ohlc(frame: pd.DataFrame) -> tuple[float, float, float, float]:
    return (
        float(frame.iloc[0].open),
        float(frame.high.max()),
        float(frame.low.min()),
        float(frame.iloc[-1].close),
    )


def _direction(open_: float, high: float, low: float, close: float, minimum: float) -> tuple[int, float]:
    span = high - low
    fraction = abs(close - open_) / span if span > 0 else 0.0
    if fraction < minimum or close == open_:
        return 0, fraction
    return (1 if close > open_ else -1), fraction


def hourly_gain_failure(
    previous: tuple[float, float, float, float],
    current: tuple[float, float, float, float],
) -> tuple[int, float | None, str]:
    """Classify a closed H1 candle using body-level gain/failure logic."""
    previous_open, _, _, previous_close = previous
    _, current_high, current_low, current_close = current
    body_high = max(previous_open, previous_close)
    body_low = min(previous_open, previous_close)
    failed_high = current_high > body_high and current_close < body_high
    failed_low = current_low < body_low and current_close > body_low
    if failed_high and failed_low:
        return 0, None, "ambiguous_outside_bar"
    if current_close > body_high:
        return 1, body_high, "gain_high"
    if current_close < body_low:
        return -1, body_low, "gain_low"
    if failed_high:
        return -1, body_high, "fail_high"
    if failed_low:
        return 1, body_low, "fail_low"
    return 0, None, "inside_body"


def body_level_gain_failure(
    levels: list[float],
    current: tuple[float, float, float, float],
    side_hint: int = 0,
) -> tuple[int, float | None, str]:
    """Classify a closed H1 reaction at completed D1/W1/MN body levels."""
    current_open, current_high, current_low, current_close = current
    events: list[tuple[float, int, float, str]] = []
    for level in levels:
        if current_open <= level < current_close:
            events.append((abs(current_close - level), 1, level, "gain_high"))
        elif current_open >= level > current_close:
            events.append((abs(current_close - level), -1, level, "gain_low"))
        elif current_high > level and current_close < level:
            events.append((abs(current_close - level), -1, level, "fail_high"))
        elif current_low < level and current_close > level:
            events.append((abs(current_close - level), 1, level, "fail_low"))
    if side_hint:
        events = [event for event in events if event[1] == side_hint]
    if not events:
        return 0, None, "no_body_level_reaction"
    _, side, level, pattern = min(events, key=lambda event: event[0])
    return side, level, pattern


def completed_body_levels(
    work: pd.DataFrame,
    before: pd.Timestamp,
    config: Config,
) -> list[float]:
    """Build prior D1/W1/MN body levels without using future candles."""
    history = work.loc[work["local"] < before].copy()
    if history.empty:
        return []
    levels: list[float] = []

    def append_groups(
        source: pd.DataFrame, key: pd.Series, lookback: int
    ) -> None:
        groups = list(source.groupby(key, sort=True))[-lookback:]
        for _, group in groups:
            levels.extend(
                (float(group.iloc[0].open), float(group.iloc[-1].close))
            )

    daily = history.loc[history["local_date"] < before.date()]
    if not daily.empty:
        append_groups(
            daily, daily["local_date"], config.body_level_daily_lookback
        )

    iso = history["local"].dt.isocalendar()
    before_iso = before.isocalendar()
    week_number = iso["year"].astype(int) * 100 + iso["week"].astype(int)
    before_week = int(before_iso.year) * 100 + int(before_iso.week)
    weekly = history.loc[week_number < before_week]
    if not weekly.empty:
        weekly_iso = weekly["local"].dt.isocalendar()
        append_groups(
            weekly,
            weekly_iso["year"].astype(str)
            + "-"
            + weekly_iso["week"].astype(str),
            config.body_level_weekly_lookback,
        )

    before_month = before.strftime("%Y-%m")
    monthly = history.loc[history["local"].dt.strftime("%Y-%m") < before_month]
    if not monthly.empty:
        append_groups(
            monthly,
            monthly["local"].dt.strftime("%Y-%m"),
            config.body_level_monthly_lookback,
        )
    return sorted({round(value, 8) for value in levels})


def next_body_target(
    levels: list[float],
    entry: float,
    stop: float,
    side: int,
    minimum_r: float,
    maximum_r: float,
) -> float | None:
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    if side > 0:
        candidates = [value for value in levels if value > entry]
        ordered = sorted(candidates)
    else:
        candidates = [value for value in levels if value < entry]
        ordered = sorted(candidates, reverse=True)
    for value in ordered:
        target_r = abs(value - entry) / risk
        if minimum_r <= target_r <= maximum_r:
            return value
    return None


def build_plans(frame: pd.DataFrame, config: Config) -> list[Plan]:
    if frame.empty:
        return []
    work = frame.copy().sort_values("time")
    work["time"] = pd.to_datetime(work.time, utc=True)
    work["local"] = work.time.dt.tz_convert(config.timezone)
    work["local_date"] = work.local.dt.date
    dates = sorted(set(work.local_date))
    plans: list[Plan] = []
    for current in dates:
        prior_dates = [item for item in dates if item < current]
        if not prior_dates:
            continue
        previous = prior_dates[-1]
        daily = work[work.local_date == previous]
        if daily.empty:
            continue
        local_open = datetime.combine(current, config.ny_open, config.timezone)
        h4_start = local_open - timedelta(hours=config.h4_hours)
        h4 = work[(work.local >= h4_start) & (work.local < local_open)]
        if h4.empty or h4.time.nunique() < 120:
            continue
        d1 = _ohlc(daily)
        h4_values = _ohlc(h4)
        d1_side, d1_fraction = _direction(*d1, config.d1_min_body_fraction)
        h4_side, h4_fraction = _direction(*h4_values, config.h4_min_body_fraction)
        if d1_side == 0 or h4_side != d1_side:
            continue
        previous_h1_start = local_open - timedelta(hours=2)
        current_h1_start = local_open - timedelta(hours=1)
        previous_h1 = work[
            (work.local >= previous_h1_start)
            & (work.local < current_h1_start)
        ]
        current_h1 = work[
            (work.local >= current_h1_start) & (work.local < local_open)
        ]
        h1_side, reference_level, h1_pattern = 0, None, "none"
        levels: list[float] = []
        h1_complete = (
            previous_h1.time.nunique() >= 45
            and current_h1.time.nunique() >= 45
        )
        confirmation_mode = config.h1_confirmation_mode
        if confirmation_mode == "aligned":
            confirmation_mode = "previous_body"
        if confirmation_mode != "none":
            if not h1_complete:
                continue
            if confirmation_mode == "previous_body":
                h1_side, reference_level, h1_pattern = hourly_gain_failure(
                    _ohlc(previous_h1), _ohlc(current_h1)
                )
            else:
                levels = completed_body_levels(
                    work, pd.Timestamp(local_open), config
                )
                h1_side, reference_level, h1_pattern = body_level_gain_failure(
                    levels, _ohlc(current_h1), side_hint=d1_side
                )
            if h1_side != d1_side:
                continue
        close = h4_values[3]
        if config.entry_mode in {"h1_retest", "reaction_retest"}:
            if reference_level is None or h1_side != d1_side:
                continue
            entry = reference_level
        else:
            entry = (
                close - config.pullback_points
                if d1_side > 0
                else close + config.pullback_points
            )
        if config.stop_mode == "h1_structure":
            if not h1_complete:
                continue
            _, h1_high, h1_low, _ = _ohlc(current_h1)
            raw_stop = (
                h1_low - config.structure_stop_buffer_points
                if d1_side > 0
                else h1_high + config.structure_stop_buffer_points
            )
            stop_distance = abs(entry - raw_stop)
            if stop_distance > config.maximum_stop_points:
                continue
            stop_distance = max(stop_distance, config.minimum_stop_points)
            stop = entry - stop_distance if d1_side > 0 else entry + stop_distance
        else:
            stop = entry - config.stop_points if d1_side > 0 else entry + config.stop_points
        risk_distance = abs(entry - stop)
        fixed_target = entry + d1_side * config.target_rr * risk_distance
        target = fixed_target
        if config.target_mode == "next_body":
            if not levels:
                levels = completed_body_levels(
                    work, pd.Timestamp(local_open), config
                )
            body_target = next_body_target(
                levels,
                entry,
                stop,
                d1_side,
                config.minimum_target_r,
                config.maximum_target_r,
            )
            if body_target is None:
                continue
            body_r = abs(body_target - entry) / risk_distance
            target = body_target if body_r <= config.target_rr else fixed_target
        rank = "A+" if min(d1_fraction, h4_fraction) >= config.strong_body_fraction else "A"
        expiry = datetime.combine(current, config.pending_expiry, config.timezone)
        plans.append(
            Plan(
                session_date=current,
                signal_time=local_open.astimezone(timezone.utc),
                expiry=expiry.astimezone(timezone.utc),
                side=d1_side,
                rank=rank,
                entry=entry,
                initial_stop=stop,
                d1_body_fraction=d1_fraction,
                h4_body_fraction=h4_fraction,
                reason=(
                    "D1/H4 aligned"
                    if h1_pattern == "none"
                    else f"D1/H4 + H1 {h1_pattern}"
                ),
                h1_pattern=h1_pattern,
                reference_level=reference_level,
                target=target,
            )
        )
    return plans


def _simulate_plan(plan: Plan, frame: pd.DataFrame, config: Config, point: float) -> Trade | None:
    future = frame[(frame.time >= pd.Timestamp(plan.signal_time)) & (frame.time <= pd.Timestamp(plan.expiry))]
    if future.empty:
        return None
    entry_row = None
    for row in future.itertuples():
        spread_price = float(getattr(row, "spread", 0.0)) * point
        if plan.side > 0 and float(row.low) + spread_price <= plan.entry:
            entry_row = row
            break
        if plan.side < 0 and float(row.high) >= plan.entry:
            entry_row = row
            break
    if entry_row is None:
        return None
    entry_time = pd.Timestamp(entry_row.time).to_pydatetime()
    risk = abs(plan.entry - plan.initial_stop)
    maximum_end = entry_time + timedelta(hours=config.max_hold_hours)
    after = frame[(frame.time >= pd.Timestamp(entry_time)) & (frame.time <= pd.Timestamp(maximum_end))]
    stop = plan.initial_stop
    best = plan.entry
    worst_r = 0.0
    last = entry_row
    for row in after.itertuples():
        last = row
        spread_price = float(getattr(row, "spread", 0.0)) * point
        if plan.side > 0:
            adverse = (plan.entry - float(row.low)) / risk
            worst_r = max(worst_r, adverse)
            if float(row.low) <= stop:
                return Trade(plan.session_date, plan.side, plan.rank, plan.signal_time, entry_time, pd.Timestamp(row.time).to_pydatetime(), plan.entry, plan.initial_stop, stop, (stop - plan.entry) / risk, worst_r, "stop/trail")
            if plan.target is not None and float(row.high) >= plan.target:
                result = (plan.target - plan.entry) / risk
                reason = "next-body target" if config.target_mode == "next_body" else "fixed target"
                return Trade(plan.session_date, plan.side, plan.rank, plan.signal_time, entry_time, pd.Timestamp(row.time).to_pydatetime(), plan.entry, plan.initial_stop, plan.target, result, worst_r, reason)
            best = max(best, float(row.high))
            if config.trailing_enabled and best - plan.entry >= config.trail_start_r * risk:
                stop = max(stop, float(row.close) - config.trail_distance_r * risk)
        else:
            adverse = (float(row.high) - plan.entry) / risk
            worst_r = max(worst_r, adverse)
            if float(row.high) + spread_price >= stop:
                exit_price = stop + spread_price
                return Trade(plan.session_date, plan.side, plan.rank, plan.signal_time, entry_time, pd.Timestamp(row.time).to_pydatetime(), plan.entry, plan.initial_stop, exit_price, (plan.entry - exit_price) / risk, worst_r, "stop/trail")
            if plan.target is not None and float(row.low) <= plan.target:
                result = (plan.entry - plan.target) / risk
                reason = "next-body target" if config.target_mode == "next_body" else "fixed target"
                return Trade(plan.session_date, plan.side, plan.rank, plan.signal_time, entry_time, pd.Timestamp(row.time).to_pydatetime(), plan.entry, plan.initial_stop, plan.target, result, worst_r, reason)
            best = min(best, float(row.low))
            if config.trailing_enabled and plan.entry - best >= config.trail_start_r * risk:
                stop = min(stop, float(row.close) + config.trail_distance_r * risk)
    exit_price = float(last.close)
    result = (exit_price - plan.entry) / risk * plan.side
    return Trade(plan.session_date, plan.side, plan.rank, plan.signal_time, entry_time, pd.Timestamp(last.time).to_pydatetime(), plan.entry, plan.initial_stop, exit_price, result, worst_r, "max-hold/data-end")


def run_backtest(
    frame: pd.DataFrame,
    config: Config,
    *,
    point: float,
    start: datetime,
    end: datetime,
    starting_balance: float = 1000.0,
) -> tuple[list[Trade], Metrics]:
    work = frame.copy()
    work["time"] = pd.to_datetime(work.time, utc=True)
    plans = build_plans(work, config)
    trades: list[Trade] = []
    weekly: dict[tuple[int, int], int] = {}
    for plan in plans:
        if not (start <= plan.signal_time <= end):
            continue
        iso = plan.session_date.isocalendar()
        key = (iso.year, iso.week)
        if weekly.get(key, 0) >= config.max_trades_per_week:
            continue
        trade = _simulate_plan(plan, work, config, point)
        if trade is not None:
            weekly[key] = weekly.get(key, 0) + 1
            trades.append(trade)
    balance = starting_balance
    peak = balance
    max_dd = 0.0
    max_intra = 0.0
    loss_streak = 0
    sized_trades: list[Trade] = []
    gross_profit_cash = 0.0
    gross_loss_cash = 0.0
    max_risk_pct_used = 0.0
    for trade in sorted(trades, key=lambda item: item.exit_time):
        risk_pct = (
            risk_pct_for_streak(
                config.risk_pct,
                loss_streak,
                config.risk_progression_multiplier,
            )
            if config.risk_progression_enabled
            else config.risk_pct
        )
        max_risk_pct_used = max(max_risk_pct_used, risk_pct)
        risk_cash = balance * risk_pct / 100.0
        max_intra = max(max_intra, (peak - (balance - risk_cash * trade.mae_r)) / peak * 100.0)
        cash_pnl = risk_cash * trade.r_multiple
        balance += cash_pnl
        sized_trades.append(
            replace(trade, risk_pct_used=risk_pct, cash_pnl=cash_pnl)
        )
        if cash_pnl > 0:
            gross_profit_cash += cash_pnl
            loss_streak = 0
        elif cash_pnl < 0:
            gross_loss_cash += -cash_pnl
            loss_streak += 1
        peak = max(peak, balance)
        max_dd = max(max_dd, (peak - balance) / peak * 100.0)
    trades = sorted(sized_trades, key=lambda item: item.entry_time)
    wins = sum(item.r_multiple > 0 for item in trades)
    losses = sum(item.r_multiple <= 0 for item in trades)
    gross_win_r = sum(max(0.0, item.r_multiple) for item in trades)
    gross_loss_r = -sum(min(0.0, item.r_multiple) for item in trades)
    pf = (
        gross_win_r / gross_loss_r
        if gross_loss_r
        else (float("inf") if gross_win_r else 0.0)
    )
    cash_weighted_pf = (
        gross_profit_cash / gross_loss_cash
        if gross_loss_cash
        else (float("inf") if gross_profit_cash else 0.0)
    )
    metrics = Metrics(
        trades=len(trades),
        wins=wins,
        losses=losses,
        win_rate_pct=wins / len(trades) * 100.0 if trades else 0.0,
        profit_factor=pf,
        net_r=sum(item.r_multiple for item in trades),
        ending_balance=balance,
        return_pct=(balance / starting_balance - 1.0) * 100.0,
        max_realized_dd_pct=max_dd,
        max_intratrade_dd_pct=max_intra,
        start=start.isoformat(),
        end=end.isoformat(),
        gross_profit_cash=gross_profit_cash,
        gross_loss_cash=gross_loss_cash,
        max_risk_pct_used=max_risk_pct_used,
        final_loss_streak=loss_streak,
        progression_enabled=config.risk_progression_enabled,
        trailing_enabled=config.trailing_enabled,
        target_rr=config.target_rr,
        cash_weighted_profit_factor=cash_weighted_pf,
    )
    return trades, metrics


def idea_comment(rank: str, reason: str = "D1+H4 aligned") -> str:
    return f"DmC {rank} {reason}"[:31]
