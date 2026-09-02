from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from .strategy import StrategyConfig, backtest, performance_metrics


def monte_carlo(trades: pd.DataFrame, simulations: int = 10_000, seed: int = 20260902) -> dict:
    """Bootstrap the observed trade returns without inventing additional trades."""

    if trades.empty:
        return {
            "simulations": simulations,
            "trades": 0,
            "loss_probability_pct": 0.0,
            "return_p5_pct": 0.0,
            "return_median_pct": 0.0,
            "return_p95_pct": 0.0,
            "max_drawdown_median_pct": 0.0,
            "max_drawdown_p95_pct": 0.0,
        }
    values = trades["account_return"].to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, size=(simulations, len(values)), replace=True)
    curves = np.cumprod(1.0 + samples, axis=1)
    peaks = np.maximum.accumulate(curves, axis=1)
    endings = curves[:, -1] - 1.0
    drawdowns = np.max(1.0 - curves / peaks, axis=1)
    return {
        "simulations": simulations,
        "trades": int(len(values)),
        "loss_probability_pct": float(np.mean(endings < 0.0) * 100.0),
        "return_p5_pct": float(np.percentile(endings, 5) * 100.0),
        "return_median_pct": float(np.percentile(endings, 50) * 100.0),
        "return_p95_pct": float(np.percentile(endings, 95) * 100.0),
        "max_drawdown_median_pct": float(np.percentile(drawdowns, 50) * 100.0),
        "max_drawdown_p95_pct": float(np.percentile(drawdowns, 95) * 100.0),
    }


def evaluate_grid(
    spot: pd.DataFrame,
    futures: pd.DataFrame,
    base: StrategyConfig,
    parameter_grid: list[dict],
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    rows: list[dict] = []
    for parameters in parameter_grid:
        config = replace(base, **parameters)
        trades = backtest(spot, futures, config, start=start, end=end)
        metrics = performance_metrics(trades)
        trade_penalty = max(0, 6 - metrics["trades"]) * 2.0
        score = (
            metrics["return_pct"]
            - 1.5 * metrics["max_drawdown_pct"]
            + 0.20 * metrics["sharpe"]
            - trade_penalty
        )
        rows.append({**parameters, **metrics, "score": float(score)})
    return pd.DataFrame(rows).sort_values(
        ["score", "profit_factor", "trades"], ascending=[False, False, False]
    )


def choose_locked_config(grid: pd.DataFrame, minimum_trades: int = 6) -> dict:
    eligible = grid.loc[(grid["trades"] >= minimum_trades) & (grid["profit_factor"] > 1.0)]
    chosen = eligible.iloc[0] if not eligible.empty else grid.iloc[0]
    parameter_names = [
        "lookback_hours",
        "minimum_spot_move",
        "entry_z",
        "exit_z",
        "stop_z_extension",
        "maximum_hold_hours",
    ]
    return {
        name: int(chosen[name]) if name in {"lookback_hours", "maximum_hold_hours"} else float(chosen[name])
        for name in parameter_names
    }
