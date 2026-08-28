from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .config import INITIAL_BALANCE
from .regime import walk_forward_signals


@dataclass(frozen=True)
class RegimeEAConfig:
    window: int = 20
    threshold: float = 0.05
    signal_gate: float = 0.0
    atr_period: int = 14
    atr_multiple: float = 3.0
    reward_risk: float = 0.0
    risk_pct: float = 1.0
    max_leverage: float = 2.0
    direction_mode: str = "both"


def average_true_range(frame: pd.DataFrame, period: int) -> pd.Series:
    previous = frame["Close"].shift(1)
    true_range = pd.concat(
        [
            frame["High"] - frame["Low"],
            (frame["High"] - previous).abs(),
            (frame["Low"] - previous).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(period, min_periods=period).mean()


def _max_drawdown(equity: pd.Series) -> tuple[float, float]:
    if equity.empty:
        return 0.0, 0.0
    peaks = equity.cummax()
    amount = peaks - equity
    percent = amount / peaks.replace(0.0, np.nan) * 100.0
    return float(amount.max()), float(percent.max(skipna=True) or 0.0)


def calculate_metrics(
    equity: pd.Series,
    trades: list[dict[str, Any]],
    *,
    initial_balance: float = INITIAL_BALANCE,
) -> dict[str, Any]:
    if equity.empty:
        equity = pd.Series([initial_balance], index=[pd.Timestamp("1970-01-01")])
    nets = np.asarray([float(trade["net"]) for trade in trades], dtype=float)
    gross_profit = float(nets[nets > 0].sum()) if len(nets) else 0.0
    gross_loss = float(nets[nets < 0].sum()) if len(nets) else 0.0
    profit_factor = gross_profit / abs(gross_loss) if gross_loss else (999.0 if gross_profit else 0.0)
    wins = int((nets > 0).sum()) if len(nets) else 0
    dd_amount, dd_pct = _max_drawdown(equity)
    daily = equity.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    sharpe = 0.0
    if len(daily) > 1 and float(daily.std()) > 0:
        sharpe = float(math.sqrt(252.0) * daily.mean() / daily.std())
    final = float(equity.iloc[-1])
    return {
        "initial_balance": round(initial_balance, 2),
        "final_balance": round(final, 2),
        "net_profit": round(final - initial_balance, 2),
        "return_pct": round((final / initial_balance - 1.0) * 100.0, 4),
        "max_equity_dd_amount": round(dd_amount, 2),
        "max_equity_dd_pct": round(dd_pct, 4),
        "profit_factor": round(profit_factor, 4),
        "win_rate_pct": round(wins / len(nets) * 100.0 if len(nets) else 0.0, 4),
        "wins": wins,
        "losses": int(len(nets) - wins),
        "trades": int(len(nets)),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "largest_win": round(float(nets.max()), 2) if len(nets) else 0.0,
        "largest_loss": round(float(nets.min()), 2) if len(nets) else 0.0,
        "average_win": round(float(nets[nets > 0].mean()), 2) if wins else 0.0,
        "average_loss": round(float(nets[nets < 0].mean()), 2) if wins < len(nets) else 0.0,
        "sharpe": round(sharpe, 4),
    }


def simulate_regime_ea(
    frame: pd.DataFrame,
    config: RegimeEAConfig,
    *,
    start: str,
    end: str,
    roundtrip_cost_bps: float,
    initial_balance: float = INITIAL_BALANCE,
    prepared_signal: pd.Series | None = None,
    prepared_atr: pd.Series | None = None,
) -> dict[str, Any]:
    """Daily-bar execution model with explicit no-lookahead decisions.

    A signal formed at yesterday's close may enter at today's open. Stops and
    targets are checked pessimistically: if both are touched on one daily bar,
    the stop is assumed to fill first.
    """
    frame = frame.sort_index().copy()
    if prepared_signal is None:
        prepared_signal = walk_forward_signals(
            frame["Close"], window=config.window, threshold=config.threshold
        )["signal"]
    decision = prepared_signal.shift(1)
    atr = prepared_atr if prepared_atr is not None else average_true_range(frame, config.atr_period)
    atr_at_open = atr.shift(1)
    selected = frame.loc[pd.Timestamp(start) : pd.Timestamp(end)]
    if selected.empty:
        raise RuntimeError(f"No market rows inside {start} to {end}.")

    balance = float(initial_balance)
    position: dict[str, Any] | None = None
    trades: list[dict[str, Any]] = []
    equity_values: list[float] = []
    equity_dates: list[pd.Timestamp] = []
    half_cost = roundtrip_cost_bps / 20_000.0

    def close_position(when: pd.Timestamp, price: float, reason: str) -> None:
        nonlocal balance, position
        if position is None:
            return
        exit_cost = abs(price * position["units"]) * half_cost
        gross = position["direction"] * position["units"] * (price - position["entry"])
        balance += gross - exit_cost
        net = balance - position["balance_before"]
        trades.append(
            {
                "open_time": position["open_time"].isoformat(),
                "close_time": when.isoformat(),
                "direction": "long" if position["direction"] > 0 else "short",
                "entry": round(position["entry"], 8),
                "exit": round(float(price), 8),
                "units": round(position["units"], 8),
                "net": round(float(net), 8),
                "reason": reason,
            }
        )
        position = None

    for when, row in selected.iterrows():
        open_price = float(row["Open"])
        high = float(row["High"])
        low = float(row["Low"])
        close = float(row["Close"])

        # Gap risk is charged at the opening price, not the theoretical stop.
        if position is not None:
            if position["direction"] > 0 and open_price <= position["stop"]:
                close_position(when, open_price, "gap_stop")
            elif position["direction"] < 0 and open_price >= position["stop"]:
                close_position(when, open_price, "gap_stop")

        raw_signal = decision.get(when, np.nan)
        desired = 0
        if pd.notna(raw_signal):
            if float(raw_signal) > config.signal_gate:
                desired = 1
            elif float(raw_signal) < -config.signal_gate:
                desired = -1
        if config.direction_mode == "long_only" and desired < 0:
            desired = 0

        if position is not None and desired != position["direction"]:
            close_position(when, open_price, "signal_change")

        opening_atr = atr_at_open.get(when, np.nan)
        if position is None and desired and pd.notna(opening_atr) and balance > 0:
            stop_distance = float(opening_atr) * config.atr_multiple
            if stop_distance > 0 and open_price > 0:
                risk_budget = balance * config.risk_pct / 100.0
                risk_units = risk_budget / stop_distance
                leverage_units = balance * config.max_leverage / open_price
                units = min(risk_units, leverage_units)
                if units > 0:
                    balance_before = balance
                    entry_cost = abs(open_price * units) * half_cost
                    balance -= entry_cost
                    position = {
                        "direction": desired,
                        "entry": open_price,
                        "units": units,
                        "stop": open_price - desired * stop_distance,
                        "target": (
                            open_price + desired * stop_distance * config.reward_risk
                            if config.reward_risk > 0
                            else None
                        ),
                        "open_time": when,
                        "balance_before": balance_before,
                    }

        if position is not None:
            direction = position["direction"]
            stop_hit = low <= position["stop"] if direction > 0 else high >= position["stop"]
            target_hit = False
            if position["target"] is not None:
                target_hit = high >= position["target"] if direction > 0 else low <= position["target"]
            if stop_hit:
                close_position(when, float(position["stop"]), "stop")
            elif target_hit:
                close_position(when, float(position["target"]), "target")

        if position is not None:
            marked = balance + position["direction"] * position["units"] * (
                close - position["entry"]
            )
        else:
            marked = balance
        equity_dates.append(when)
        equity_values.append(float(marked))

        # A close-based trail becomes executable on the next bar.
        current_atr = atr.get(when, np.nan)
        if position is not None and pd.notna(current_atr):
            trail_distance = float(current_atr) * config.atr_multiple
            if position["direction"] > 0:
                position["stop"] = max(position["stop"], close - trail_distance)
            else:
                position["stop"] = min(position["stop"], close + trail_distance)

    if position is not None:
        last_when = selected.index[-1]
        close_position(last_when, float(selected.iloc[-1]["Close"]), "test_end")
        equity_values[-1] = balance

    equity = pd.Series(equity_values, index=pd.DatetimeIndex(equity_dates), name="Equity")
    return {
        "config": asdict(config),
        "period": {"start": start, "end": end},
        "metrics": calculate_metrics(equity, trades, initial_balance=initial_balance),
        "equity": equity,
        "trades": trades,
    }


def candidate_configs() -> Iterable[RegimeEAConfig]:
    for window in (10, 20, 40, 60):
        for threshold in (0.02, 0.05, 0.08):
            for gate in (0.0, 0.05, 0.10):
                for atr_multiple in (2.0, 3.0, 4.0):
                    for reward_risk in (0.0, 2.0, 3.0):
                        for mode in ("both", "long_only"):
                            yield RegimeEAConfig(
                                window=window,
                                threshold=threshold,
                                signal_gate=gate,
                                atr_multiple=atr_multiple,
                                reward_risk=reward_risk,
                                direction_mode=mode,
                            )


def _training_score(metrics: dict[str, Any]) -> float:
    if metrics["trades"] < 20 or metrics["final_balance"] <= 0:
        return -math.inf
    pf = max(0.01, min(float(metrics["profit_factor"]), 5.0))
    ret = float(metrics["return_pct"]) / 100.0
    dd = float(metrics["max_equity_dd_pct"]) / 100.0
    sharpe = max(-3.0, min(float(metrics["sharpe"]), 3.0))
    # Train-only score rewards return consistency and explicitly penalizes DD.
    return math.log(max(0.05, 1.0 + ret)) + 0.45 * math.log(pf) + 0.20 * sharpe - 1.25 * dd


def optimize_on_training(
    frame: pd.DataFrame,
    *,
    start: str,
    end: str,
    roundtrip_cost_bps: float,
) -> tuple[RegimeEAConfig, dict[str, Any], list[dict[str, Any]]]:
    rankings: list[dict[str, Any]] = []
    signal_cache = {
        (window, threshold): walk_forward_signals(
            frame["Close"], window=window, threshold=threshold
        )["signal"]
        for window in (10, 20, 40, 60)
        for threshold in (0.02, 0.05, 0.08)
    }
    atr_cache = average_true_range(frame, 14)
    for config in candidate_configs():
        result = simulate_regime_ea(
            frame,
            config,
            start=start,
            end=end,
            roundtrip_cost_bps=roundtrip_cost_bps,
            prepared_signal=signal_cache[(config.window, config.threshold)],
            prepared_atr=atr_cache,
        )
        score = _training_score(result["metrics"])
        rankings.append(
            {"score": score, "config": asdict(config), "metrics": result["metrics"]}
        )
    rankings.sort(key=lambda item: item["score"], reverse=True)
    if not rankings or not math.isfinite(float(rankings[0]["score"])):
        raise RuntimeError("No training candidate met the minimum robustness requirements.")
    best = RegimeEAConfig(**rankings[0]["config"])
    return best, rankings[0]["metrics"], rankings[:10]
