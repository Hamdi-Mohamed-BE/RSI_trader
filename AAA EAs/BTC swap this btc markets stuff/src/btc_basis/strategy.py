from __future__ import annotations

import calendar
from dataclasses import asdict, dataclass
from typing import Literal

import numpy as np
import pandas as pd


Mode = Literal["directional", "hedged"]


@dataclass(frozen=True)
class StrategyConfig:
    mode: Mode = "directional"
    lookback_hours: int = 336
    minimum_gap_hours: float = 30.0
    minimum_spot_move: float = 0.01
    entry_z: float = 1.0
    exit_z: float = 0.25
    stop_z_extension: float = 1.5
    maximum_hold_hours: int = 24
    stop_return: float = 0.015
    risk_per_trade: float = 0.01
    maximum_position_fraction: float = 1.0
    round_trip_cost_bps: float = 12.0
    roll_exclusion_days: int = 7
    legacy_cutoff: str = "2026-05-29 00:00:00+00:00"

    def serializable(self) -> dict:
        return asdict(self)


def _row_at_or_before(frame: pd.DataFrame, when: pd.Timestamp) -> pd.Series | None:
    location = frame.index.get_indexer([when], method="pad")[0]
    if location < 0:
        return None
    return frame.iloc[location]


def _days_to_month_end(when: pd.Timestamp) -> int:
    return calendar.monthrange(when.year, when.month)[1] - when.day


def detect_reopen_events(
    spot: pd.DataFrame,
    futures: pd.DataFrame,
    config: StrategyConfig,
) -> pd.DataFrame:
    """Detect qualifying legacy weekend reopen events without using future bars."""

    cutoff = pd.Timestamp(config.legacy_cutoff)
    gaps = futures.index.to_series().diff().dt.total_seconds().div(3600)
    reopen_times = futures.index[(gaps >= config.minimum_gap_hours).to_numpy()]
    rows: list[dict] = []
    for entry_time in reopen_times:
        if entry_time >= cutoff or _days_to_month_end(entry_time) <= config.roll_exclusion_days:
            continue
        entry_location = futures.index.get_loc(entry_time)
        if entry_location <= 0:
            continue
        previous_time = futures.index[entry_location - 1]
        previous_future = futures.iloc[entry_location - 1]
        entry_future = futures.iloc[entry_location]
        previous_spot = _row_at_or_before(spot, previous_time)
        entry_spot = _row_at_or_before(spot, entry_time)
        if previous_spot is None or entry_spot is None:
            continue

        history_start = entry_time - pd.Timedelta(hours=config.lookback_hours)
        history_future = futures.loc[(futures.index >= history_start) & (futures.index < entry_time), "close"]
        history_spot = spot["close"].reindex(history_future.index, method="ffill", tolerance=pd.Timedelta(hours=2))
        history_basis = history_future.div(history_spot).sub(1.0).dropna()
        minimum_observations = max(30, int(config.lookback_hours * 0.35))
        if len(history_basis) < minimum_observations:
            continue
        basis_mean = float(history_basis.mean())
        basis_std = float(history_basis.std(ddof=1))
        if not np.isfinite(basis_std) or basis_std <= 1e-6:
            continue

        future_open = float(entry_future["open"])
        spot_open = float(entry_spot["open"])
        spot_move = spot_open / float(previous_spot["close"]) - 1.0
        basis_open = future_open / spot_open - 1.0
        basis_z = (basis_open - basis_mean) / basis_std
        direction = 0
        if spot_move >= config.minimum_spot_move and basis_z >= config.entry_z:
            direction = -1
        elif spot_move <= -config.minimum_spot_move and basis_z <= -config.entry_z:
            direction = 1
        rows.append(
            {
                "entry_time": entry_time,
                "previous_time": previous_time,
                "gap_hours": (entry_time - previous_time).total_seconds() / 3600,
                "days_to_month_end": _days_to_month_end(entry_time),
                "previous_future_close": float(previous_future["close"]),
                "entry_future": future_open,
                "previous_spot_close": float(previous_spot["close"]),
                "entry_spot": spot_open,
                "spot_move": spot_move,
                "basis_open": basis_open,
                "basis_mean": basis_mean,
                "basis_std": basis_std,
                "basis_z": basis_z,
                "direction": direction,
            }
        )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("entry_time").sort_index()


def _trade_path_return(
    mode: Mode,
    direction: int,
    future_price: float,
    entry_future: float,
    spot_price: float,
    entry_spot: float,
) -> float:
    future_return = future_price / entry_future - 1.0
    if mode == "directional":
        return direction * future_return
    spot_return = spot_price / entry_spot - 1.0
    return direction * (future_return - spot_return)


def backtest(
    spot: pd.DataFrame,
    futures: pd.DataFrame,
    config: StrategyConfig,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
) -> pd.DataFrame:
    events = detect_reopen_events(spot, futures, config)
    if events.empty:
        return pd.DataFrame()
    if start is not None:
        events = events.loc[events.index >= pd.Timestamp(start)]
    if end is not None:
        events = events.loc[events.index < pd.Timestamp(end)]

    trades: list[dict] = []
    position_fraction = min(
        config.maximum_position_fraction,
        config.risk_per_trade / max(config.stop_return, 1e-9),
    )
    for entry_time, event in events.loc[events["direction"] != 0].iterrows():
        direction = int(event["direction"])
        end_time = entry_time + pd.Timedelta(hours=config.maximum_hold_hours)
        future_path = futures.loc[(futures.index >= entry_time) & (futures.index <= end_time)]
        if future_path.empty:
            continue
        exit_time = future_path.index[-1]
        exit_reason = "time"
        exit_future = float(future_path.iloc[-1]["close"])
        final_spot_row = _row_at_or_before(spot, exit_time)
        if final_spot_row is None:
            continue
        exit_spot = float(final_spot_row["close"])
        gross_return = _trade_path_return(
            config.mode,
            direction,
            exit_future,
            float(event["entry_future"]),
            exit_spot,
            float(event["entry_spot"]),
        )

        for timestamp, future_bar in future_path.iterrows():
            spot_bar = _row_at_or_before(spot, timestamp)
            if spot_bar is None:
                continue
            future_close = float(future_bar["close"])
            spot_close = float(spot_bar["close"])
            basis = future_close / spot_close - 1.0
            current_z = (basis - float(event["basis_mean"])) / float(event["basis_std"])
            path_return = _trade_path_return(
                config.mode,
                direction,
                future_close,
                float(event["entry_future"]),
                spot_close,
                float(event["entry_spot"]),
            )
            normalized = (direction < 0 and current_z <= config.exit_z) or (
                direction > 0 and current_z >= -config.exit_z
            )
            basis_stopped = (direction < 0 and current_z >= float(event["basis_z"]) + config.stop_z_extension) or (
                direction > 0 and current_z <= float(event["basis_z"]) - config.stop_z_extension
            )
            price_stopped = path_return <= -config.stop_return
            if normalized or basis_stopped or price_stopped:
                exit_time = timestamp
                exit_future = future_close
                exit_spot = spot_close
                gross_return = path_return
                exit_reason = "mean" if normalized else ("basis_stop" if basis_stopped else "price_stop")
                break

        net_return = gross_return - config.round_trip_cost_bps / 10_000.0
        account_return = net_return * position_fraction
        trades.append(
            {
                **event.to_dict(),
                "entry_time": entry_time,
                "exit_time": exit_time,
                "side": "long" if direction > 0 else "short",
                "exit_future": exit_future,
                "exit_spot": exit_spot,
                "holding_hours": (exit_time - entry_time).total_seconds() / 3600,
                "exit_reason": exit_reason,
                "gross_return": gross_return,
                "net_return": net_return,
                "position_fraction": position_fraction,
                "account_return": account_return,
            }
        )
    if not trades:
        return pd.DataFrame()
    result = pd.DataFrame(trades).sort_values("entry_time").reset_index(drop=True)
    result["equity"] = (1.0 + result["account_return"]).cumprod()
    result["drawdown"] = result["equity"].div(result["equity"].cummax()).sub(1.0)
    return result


def performance_metrics(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {
            "trades": 0,
            "return_pct": 0.0,
            "profit_factor": 0.0,
            "win_rate_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe": 0.0,
            "recovery_factor": 0.0,
            "average_trade_pct": 0.0,
            "maximum_loss_streak": 0,
        }
    returns = trades["account_return"].astype(float)
    gains = returns[returns > 0].sum()
    losses = -returns[returns < 0].sum()
    total_return = float(trades["equity"].iloc[-1] - 1.0)
    max_drawdown = float(-trades["drawdown"].min())
    sharpe = 0.0 if returns.std(ddof=1) <= 0 else float(returns.mean() / returns.std(ddof=1) * np.sqrt(52))
    streak = maximum_streak = 0
    for value in returns:
        streak = streak + 1 if value <= 0 else 0
        maximum_streak = max(maximum_streak, streak)
    return {
        "trades": int(len(trades)),
        "return_pct": total_return * 100,
        "profit_factor": float(gains / losses) if losses > 0 else (999.0 if gains > 0 else 0.0),
        "win_rate_pct": float((returns > 0).mean() * 100),
        "max_drawdown_pct": max_drawdown * 100,
        "sharpe": sharpe,
        "recovery_factor": float(total_return / max_drawdown) if max_drawdown > 0 else 0.0,
        "average_trade_pct": float(returns.mean() * 100),
        "maximum_loss_streak": int(maximum_streak),
    }

