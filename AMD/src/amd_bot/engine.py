from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
import math

import pandas as pd

from .config import Config


UTC = timezone.utc


@dataclass(slots=True)
class Trade:
    symbol: str
    session_date: str
    phase: str
    side: str
    signal_time: str
    entry_time: str
    exit_time: str
    entry: float
    initial_stop: float
    final_stop: float
    target: float
    exit_price: float
    initial_risk: float
    pnl_r: float
    mae_r: float
    exit_reason: str
    stop_locked: bool
    asia_high: float
    asia_low: float
    asia_range: float
    liquidity_level: float | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def combine(day: date, value: time) -> datetime:
    return datetime.combine(day, value, tzinfo=UTC)


def spread_price(row: pd.Series, point: float) -> float:
    return max(float(row.get("spread", 0.0)) * point, 0.0)


def ask(row: pd.Series, field: str, point: float) -> float:
    return float(row[field]) + spread_price(row, point)


def resample_ohlc(frame: pd.DataFrame, rule: str) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    work = frame.set_index("time")
    result = work.resample(rule, label="left", closed="left").agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "spread": "max",
            "tick_volume": "sum",
        }
    )
    return result.dropna(subset=["open", "high", "low", "close"]).reset_index()


def _find_limit_fill(
    frame: pd.DataFrame,
    side: str,
    entry: float,
    start: datetime,
    end: datetime,
    point: float,
) -> int | None:
    window = frame.loc[(frame["time"] >= start) & (frame["time"] < end)]
    for idx, row in window.iterrows():
        if side == "buy" and ask(row, "low", point) <= entry:
            return int(idx)
        if side == "sell" and float(row["high"]) >= entry:
            return int(idx)
    return None


def _find_stop_fill(
    frame: pd.DataFrame,
    side: str,
    entry: float,
    start: datetime,
    end: datetime,
    point: float,
) -> int | None:
    window = frame.loc[(frame["time"] >= start) & (frame["time"] < end)]
    for idx, row in window.iterrows():
        if side == "buy" and ask(row, "high", point) >= entry:
            return int(idx)
        if side == "sell" and float(row["low"]) <= entry:
            return int(idx)
    return None


def _simulate_open_trade(
    frame: pd.DataFrame,
    symbol: str,
    session_date: date,
    phase: str,
    side: str,
    signal_time: datetime,
    entry_idx: int,
    entry: float,
    stop: float,
    target: float,
    force_exit: datetime,
    point: float,
    config: Config,
    asia_high: float,
    asia_low: float,
    liquidity_level: float | None = None,
) -> Trade:
    risk = abs(entry - stop)
    if risk <= 0:
        raise ValueError("Trade risk must be positive")
    current_stop = stop
    locked = False
    mae_r = 0.0
    exit_idx = entry_idx
    exit_price = entry
    exit_reason = "force_exit"
    window = frame.loc[
        (frame.index >= entry_idx) & (frame["time"] < force_exit)
    ]
    for idx, row in window.iterrows():
        exit_idx = int(idx)
        if side == "buy":
            adverse = max(0.0, entry - float(row["low"])) / risk
            mae_r = max(mae_r, adverse)
            if float(row["low"]) <= current_stop:
                exit_price = current_stop
                exit_reason = "locked_stop" if locked else "stop"
                break
            if float(row["high"]) >= target:
                exit_price = target
                exit_reason = "target"
                break
            if (
                not locked
                and float(row["high"]) >= entry + config.lock_trigger_r * risk
            ):
                current_stop = entry + config.lock_profit_r * risk
                locked = True
        else:
            adverse = max(0.0, ask(row, "high", point) - entry) / risk
            mae_r = max(mae_r, adverse)
            if ask(row, "high", point) >= current_stop:
                exit_price = current_stop
                exit_reason = "locked_stop" if locked else "stop"
                break
            if ask(row, "low", point) <= target:
                exit_price = target
                exit_reason = "target"
                break
            if (
                not locked
                and ask(row, "low", point)
                <= entry - config.lock_trigger_r * risk
            ):
                current_stop = entry - config.lock_profit_r * risk
                locked = True
    else:
        eligible = frame.loc[
            (frame.index >= entry_idx) & (frame["time"] < force_exit)
        ]
        if not eligible.empty:
            exit_idx = int(eligible.index[-1])
            row = frame.loc[exit_idx]
            exit_price = (
                float(row["close"])
                if side == "buy"
                else ask(row, "close", point)
            )
    pnl_r = (
        (exit_price - entry) / risk
        if side == "buy"
        else (entry - exit_price) / risk
    )
    return Trade(
        symbol=symbol,
        session_date=session_date.isoformat(),
        phase=phase,
        side=side,
        signal_time=signal_time.isoformat(),
        entry_time=frame.at[entry_idx, "time"].isoformat(),
        exit_time=frame.at[exit_idx, "time"].isoformat(),
        entry=entry,
        initial_stop=stop,
        final_stop=current_stop,
        target=target,
        exit_price=exit_price,
        initial_risk=risk,
        pnl_r=pnl_r,
        mae_r=mae_r,
        exit_reason=exit_reason,
        stop_locked=locked,
        asia_high=asia_high,
        asia_low=asia_low,
        asia_range=asia_high - asia_low,
        liquidity_level=liquidity_level,
    )


def backtest_symbol(
    frame: pd.DataFrame,
    symbol: str,
    point: float,
    config: Config,
    start: datetime,
    end: datetime,
) -> list[Trade]:
    frame = frame.loc[(frame["time"] >= start) & (frame["time"] < end)].copy()
    frame = frame.reset_index(drop=True)
    trades: list[Trade] = []
    if frame.empty:
        return trades
    frame["_session_date"] = frame["time"].dt.date
    daily_frames = {
        day: group.drop(columns="_session_date").reset_index(drop=True)
        for day, group in frame.groupby("_session_date", sort=False)
    }
    dates = pd.date_range(start.date(), end.date(), freq="D", inclusive="left")
    for stamp in dates:
        day = stamp.date()
        day_frame = daily_frames.get(day)
        if day_frame is None or day_frame.empty:
            continue
        asia_start = combine(day, config.asia_start)
        asia_end = combine(day, config.asia_end)
        london_start = combine(day, config.london_start)
        london_end = combine(day, config.london_end)
        ny_start = combine(day, config.ny_start)
        ny_cutoff = combine(day, config.ny_cutoff)
        force_exit = combine(day, config.force_exit)
        asia = day_frame.loc[
            (day_frame["time"] >= asia_start)
            & (day_frame["time"] < asia_end)
        ]
        london = day_frame.loc[
            (day_frame["time"] >= london_start)
            & (day_frame["time"] < london_end)
        ]
        if len(asia) < 120 or len(london) < 30:
            continue
        asia_high = float(asia["high"].max())
        asia_low = float(asia["low"].min())
        asia_range = asia_high - asia_low
        if asia_range <= 0:
            continue
        london_close = float(london.iloc[-1]["close"])
        london_high = float(london["high"].max())
        london_low = float(london["low"].min())
        if london_close > asia_high:
            london_side = "buy"
        elif london_close < asia_low:
            london_side = "sell"
        else:
            continue

        # London is a directional reference only. No London order is placed.
        ny_side = "sell" if london_side == "buy" else "buy"
        liquidity = (
            max(asia_high, london_high)
            if ny_side == "sell"
            else min(asia_low, london_low)
        )
        fallback_time = ny_start + timedelta(
            minutes=config.ny_fallback_minutes
        )
        first_45 = day_frame.loc[
            (day_frame["time"] >= ny_start)
            & (day_frame["time"] < fallback_time)
        ]
        if len(first_45) < max(config.ny_fallback_minutes // 2, 10):
            continue
        median_spread = max(
            float(first_45["spread"].median()) * point,
            point,
        )
        stop_buffer = max(
            asia_range * config.ny_stop_buffer_fraction,
            median_spread * 2.0,
        )
        entry_mode = config.ny_entry_mode
        if entry_mode not in {
            "limit_only",
            "stop_only",
            "single_fallback",
            "dual",
        }:
            raise ValueError(f"Unsupported NY_ENTRY_MODE: {entry_mode}")

        # Preferred reversal entry: rest a limit at the opposite-side
        # Asia/London liquidity level. It remains valid until the NY cutoff.
        limit_entry = liquidity
        if ny_side == "buy":
            limit_stop = limit_entry - stop_buffer
            limit_risk = limit_entry - limit_stop
            limit_target = limit_entry + config.ny_rr * limit_risk
        else:
            limit_stop = limit_entry + stop_buffer
            limit_risk = limit_stop - limit_entry
            limit_target = limit_entry - config.ny_rr * limit_risk
        limit_fill: int | None = None
        if entry_mode in {"limit_only", "single_fallback", "dual"}:
            limit_fill = _find_limit_fill(
                day_frame,
                ny_side,
                limit_entry,
                ny_start,
                ny_cutoff
                if entry_mode in {"limit_only", "dual"}
                else fallback_time,
                point,
            )
        if limit_fill is not None and limit_risk > median_spread:
            trades.append(
                _simulate_open_trade(
                    day_frame,
                    symbol,
                    day,
                    "new_york_limit",
                    ny_side,
                    ny_start,
                    limit_fill,
                    limit_entry,
                    limit_stop,
                    limit_target,
                    force_exit,
                    point,
                    config,
                    asia_high,
                    asia_low,
                    liquidity,
                )
            )
            if entry_mode in {"limit_only", "single_fallback"}:
                continue
        if entry_mode == "limit_only":
            continue
        if entry_mode == "single_fallback" and limit_fill is not None:
            continue

        # At +45 minutes, add a momentum stop beyond the first 45-minute NY
        # range. In dual mode the limit remains active; in single_fallback
        # mode it is cancelled and replaced by the stop. Stop-only mode skips
        # the liquidity limit entirely.
        range_high = float(first_45["high"].max())
        range_low = float(first_45["low"].min())
        entry_buffer = max(
            median_spread * config.ny_entry_buffer_spreads,
            point,
        )
        if ny_side == "buy":
            stop_entry = range_high + entry_buffer
            fallback_stop = range_low - stop_buffer
            fallback_risk = stop_entry - fallback_stop
            fallback_target = (
                stop_entry + config.ny_fallback_rr * fallback_risk
            )
        else:
            stop_entry = range_low - entry_buffer
            fallback_stop = range_high + stop_buffer
            fallback_risk = fallback_stop - stop_entry
            fallback_target = (
                stop_entry - config.ny_fallback_rr * fallback_risk
            )
        stop_fill = _find_stop_fill(
            day_frame,
            ny_side,
            stop_entry,
            fallback_time,
            ny_cutoff,
            point,
        )
        if stop_fill is None or fallback_risk <= median_spread:
            continue
        trades.append(
            _simulate_open_trade(
                day_frame,
                symbol,
                day,
                "new_york_stop",
                ny_side,
                fallback_time,
                stop_fill,
                stop_entry,
                fallback_stop,
                fallback_target,
                force_exit,
                point,
                config,
                asia_high,
                asia_low,
                liquidity,
            )
        )
    return trades


def metrics(
    symbol: str,
    trades: list[Trade],
    starting_balance: float,
    risk_pct: float,
) -> dict[str, object]:
    if not trades:
        return {
            "symbol": symbol,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "net_r": 0.0,
            "ending_balance": starting_balance,
            "return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "london_trades": 0,
            "new_york_trades": 0,
            "new_york_limit_trades": 0,
            "new_york_stop_trades": 0,
            "new_york_limit_win_rate_pct": 0.0,
            "new_york_limit_profit_factor_r": 0.0,
            "new_york_limit_net_r": 0.0,
            "new_york_stop_win_rate_pct": 0.0,
            "new_york_stop_profit_factor_r": 0.0,
            "new_york_stop_net_r": 0.0,
            "both_filled_days": 0,
            "limit_only_days": 0,
            "stop_only_days": 0,
            "max_concurrent_trades": 0,
            "max_planned_exposure_pct": 0.0,
        }
    events: list[tuple[pd.Timestamp, int, int]] = []
    for idx, trade in enumerate(trades):
        events.append((pd.Timestamp(trade.entry_time), 1, idx))
        events.append((pd.Timestamp(trade.exit_time), -1, idx))
    events.sort(key=lambda item: (item[0], item[1]))
    balance = starting_balance
    peak = balance
    max_dd = 0.0
    risk_cash: dict[int, float] = {}
    cash_pnls: list[float] = []
    for _, kind, idx in events:
        if kind == 1:
            risk_cash[idx] = balance * risk_pct / 100.0
            continue
        pnl = risk_cash.pop(idx, balance * risk_pct / 100.0) * trades[idx].pnl_r
        cash_pnls.append(pnl)
        balance += pnl
        peak = max(peak, balance)
        if peak > 0:
            max_dd = max(max_dd, (peak - balance) / peak * 100.0)
    wins = [pnl for pnl in cash_pnls if pnl > 1e-9]
    losses = [pnl for pnl in cash_pnls if pnl < -1e-9]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    def phase_stats(phase: str) -> tuple[float, float, float]:
        values = [trade.pnl_r for trade in trades if trade.phase == phase]
        if not values:
            return 0.0, 0.0, 0.0
        positive = sum(value for value in values if value > 1e-9)
        negative = abs(sum(value for value in values if value < -1e-9))
        factor = positive / negative if negative else math.inf
        win_rate = sum(value > 1e-9 for value in values) / len(values) * 100.0
        return win_rate, factor, sum(values)

    limit_wr, limit_pf, limit_net_r = phase_stats("new_york_limit")
    stop_wr, stop_pf, stop_net_r = phase_stats("new_york_stop")
    phases_by_day: dict[str, set[str]] = {}
    for trade in trades:
        phases_by_day.setdefault(trade.session_date, set()).add(trade.phase)
    both_filled_days = sum(
        {"new_york_limit", "new_york_stop"}.issubset(phases)
        for phases in phases_by_day.values()
    )
    limit_only_days = sum(
        "new_york_limit" in phases and "new_york_stop" not in phases
        for phases in phases_by_day.values()
    )
    stop_only_days = sum(
        "new_york_stop" in phases and "new_york_limit" not in phases
        for phases in phases_by_day.values()
    )
    concurrency_events: list[tuple[pd.Timestamp, int]] = []
    for trade in trades:
        concurrency_events.append((pd.Timestamp(trade.entry_time), 1))
        concurrency_events.append((pd.Timestamp(trade.exit_time), -1))
    concurrency_events.sort(key=lambda item: (item[0], -item[1]))
    active_count = 0
    max_active_count = 0
    for _, delta in concurrency_events:
        active_count += delta
        max_active_count = max(max_active_count, active_count)
    return {
        "symbol": symbol,
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": len(wins) / len(trades) * 100.0,
        "profit_factor": (
            gross_profit / gross_loss if gross_loss else math.inf
        ),
        "net_r": sum(trade.pnl_r for trade in trades),
        "ending_balance": balance,
        "return_pct": (balance / starting_balance - 1.0) * 100.0,
        "max_drawdown_pct": max_dd,
        "london_trades": sum(trade.phase == "london" for trade in trades),
        "new_york_trades": sum(
            trade.phase.startswith("new_york") for trade in trades
        ),
        "new_york_limit_trades": sum(
            trade.phase == "new_york_limit" for trade in trades
        ),
        "new_york_stop_trades": sum(
            trade.phase == "new_york_stop" for trade in trades
        ),
        "new_york_limit_win_rate_pct": limit_wr,
        "new_york_limit_profit_factor_r": limit_pf,
        "new_york_limit_net_r": limit_net_r,
        "new_york_stop_win_rate_pct": stop_wr,
        "new_york_stop_profit_factor_r": stop_pf,
        "new_york_stop_net_r": stop_net_r,
        "both_filled_days": both_filled_days,
        "limit_only_days": limit_only_days,
        "stop_only_days": stop_only_days,
        "max_concurrent_trades": max_active_count,
        "max_planned_exposure_pct": max_active_count * risk_pct,
        "locked_stop_exits": sum(
            trade.exit_reason == "locked_stop" for trade in trades
        ),
    }
