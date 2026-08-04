from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import pandas as pd

from .config import StrategyConfig
from .engine import Result, prepare, run_backtest
from .mt5_data import SymbolSpec


@dataclass(frozen=True)
class Selection:
    config: StrategyConfig
    train: Result
    validation: Result
    holdout: Result
    gate_passed: bool


def _score(result: Result, minimum_trades: int) -> float:
    if result.trades < minimum_trades or result.profit_factor < 1.0 or result.return_pct <= 0:
        return -10_000.0 + result.trades
    return result.net_r + 2.0 * min(result.profit_factor, 4.0) - 1.5 * result.max_drawdown_pct + 0.05 * result.trades


def optimize(raw: pd.DataFrame, base: StrategyConfig, spec: SymbolSpec, balance: float = 10_000.0) -> tuple[Selection, pd.DataFrame]:
    frame = prepare(raw)
    start, finish = frame.index.min(), frame.index.max()
    total = finish - start
    train_end = start + total * 0.67
    validation_end = start + total * 0.84
    rows: list[dict[str, object]] = []
    candidates: list[tuple[float, StrategyConfig, Result]] = []
    grid = product(
        (12, 16), (2.0, 2.5), (0.10, 0.20), (3, 4),
        (0.05, 0.10), (2.0, 3.0), (1.0, 2.0), (8,), (0, 2),
    )
    for impulse_bars, impulse_atr, tolerance, gap, entry_buffer, max_range, rr, expiry, activation_delay in grid:
        config = base.with_values(
            impulse_bars=impulse_bars, impulse_atr=impulse_atr, test_tolerance_atr=tolerance,
            min_test_gap=gap, entry_buffer_atr=entry_buffer, max_range_atr=max_range,
            target_rr=rr, pending_expiry_bars=expiry, activation_delay_bars=activation_delay,
        )
        result = run_backtest(frame, config, spec, balance, start, train_end)
        score = _score(result, 10)
        candidates.append((score, config, result))
    candidates.sort(key=lambda value: value[0], reverse=True)
    finalists = candidates[:40]
    selected = None
    best_validation_score = -100_000.0
    for train_score, config, train in finalists:
        validation = run_backtest(frame, config, spec, balance, train_end, validation_end)
        validation_score = _score(validation, 3)
        rows.append({
            **config.to_dict(), "train_score": train_score, "train_trades": train.trades,
            "train_pf": train.profit_factor, "train_return_pct": train.return_pct,
            "train_dd_pct": train.max_drawdown_pct, "validation_score": validation_score,
            "validation_trades": validation.trades, "validation_pf": validation.profit_factor,
            "validation_return_pct": validation.return_pct, "validation_dd_pct": validation.max_drawdown_pct,
        })
        if validation_score > best_validation_score:
            best_validation_score = validation_score
            selected = (config, train, validation)
    assert selected is not None
    config, train, validation = selected
    holdout = run_backtest(frame, config, spec, balance, validation_end, finish)
    gate = (
        train.trades >= 10 and validation.trades >= 3 and holdout.trades >= 3
        and train.profit_factor >= 1.05 and validation.profit_factor >= 1.05
        and holdout.profit_factor >= 1.05 and holdout.return_pct > 0
        and holdout.max_drawdown_pct <= 8.0
    )
    return Selection(config, train, validation, holdout, gate), pd.DataFrame(rows).sort_values("validation_score", ascending=False)
