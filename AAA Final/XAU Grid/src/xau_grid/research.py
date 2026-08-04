from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from pathlib import Path
import json

import pandas as pd

from .config import StrategyConfig
from .engine import BacktestResult, prepare_features, records_frame, run_backtest
from .mt5_data import SymbolSpec


@dataclass(frozen=True)
class Selection:
    config: StrategyConfig
    train: BacktestResult
    validation: BacktestResult
    holdout: BacktestResult
    score: float


def candidate_configs(base: StrategyConfig) -> list[StrategyConfig]:
    candidates: list[StrategyConfig] = []
    for mode in ("trend", "range"):
        thresholds = [(50.0, 50.0)] if mode == "trend" else [(35.0, 65.0), (40.0, 60.0)]
        for levels, first, step, stop, target, be, threshold in product(
            (2, 3), (0.20, 0.35), (0.60, 0.90), (0.90, 1.30), (1.25, 1.75), (0.0, 1.0), thresholds
        ):
            candidates.append(
                base.with_values(
                    mode=mode,
                    grid_levels=levels,
                    first_offset_atr=first,
                    grid_step_atr=step,
                    stop_extra_atr=stop,
                    target_atr=target,
                    be_trigger_r=be,
                    be_lock_r=0.10 if be else 0.0,
                    rsi_long_max=threshold[0],
                    rsi_short_min=threshold[1],
                )
            )
    for levels, first, step, stop, target, be in product(
        (2, 3), (0.10, 0.20), (0.25, 0.45), (1.0, 1.5), (1.0, 1.5, 2.0), (0.0, 1.0)
    ):
        candidates.append(
            base.with_values(
                mode="momentum", grid_levels=levels, first_offset_atr=first,
                grid_step_atr=step, stop_extra_atr=stop, target_atr=target,
                be_trigger_r=be, be_lock_r=0.10 if be else 0.0,
                adx_max=50.0, rsi_long_max=45.0, rsi_short_min=55.0,
            )
        )
    for levels, first, step, stop, target, session in product(
        (2, 3), (0.0, 0.15), (0.40, 0.70), (1.0, 1.5), (1.5, 2.0), ((6, 16), (7, 17))
    ):
        candidates.append(
            base.with_values(
                mode="breakout", grid_levels=levels, first_offset_atr=first,
                grid_step_atr=step, stop_extra_atr=stop, target_atr=target,
                be_trigger_r=0.0, be_lock_r=0.0, adx_max=50.0,
                rsi_long_max=45.0, rsi_short_min=55.0,
                session_start_utc=session[0], session_end_utc=session[1],
            )
        )
    return candidates


def _finite_pf(result: BacktestResult) -> float:
    return min(result.profit_factor, 5.0) if result.profit_factor != float("inf") else 5.0


def _train_score(result: BacktestResult) -> float:
    if result.trades < 12 or result.max_drawdown_pct > 10 or result.profit_factor < 1.05:
        return -10_000.0
    return result.return_pct - 1.8 * result.max_drawdown_pct + 2.0 * _finite_pf(result) + min(result.trades, 40) * 0.03


def _validation_score(train: BacktestResult, validation: BacktestResult) -> float:
    if validation.trades < 4 or validation.max_drawdown_pct > 8 or validation.profit_factor < 1.10:
        return -10_000.0
    stability = abs(_finite_pf(train) - _finite_pf(validation))
    return (
        validation.return_pct
        - 2.5 * validation.max_drawdown_pct
        + 2.5 * _finite_pf(validation)
        + 0.5 * _finite_pf(train)
        - stability
    )


def optimize(
    raw: pd.DataFrame,
    base: StrategyConfig,
    spec: SymbolSpec,
    starting_balance: float = 10_000.0,
    validation_days: int = 90,
    holdout_days: int = 90,
    top_n: int = 32,
) -> tuple[Selection, pd.DataFrame]:
    feature = prepare_features(raw)
    holdout_split = feature.index.max() - pd.Timedelta(days=holdout_days)
    validation_split = holdout_split - pd.Timedelta(days=validation_days)
    train_frame = feature.loc[feature.index < validation_split]
    validation_frame = feature.loc[(feature.index >= validation_split) & (feature.index < holdout_split)]
    holdout_frame = feature.loc[feature.index >= holdout_split]
    rows: list[dict[str, object]] = []
    ranked: list[tuple[float, StrategyConfig, BacktestResult]] = []
    configs = [config for config in candidate_configs(base) if config.mode != "range"]
    for index, config in enumerate(configs, 1):
        result = run_backtest(train_frame, config, spec, starting_balance, prepared=True)
        score = _train_score(result)
        ranked.append((score, config, result))
        rows.append({
            "candidate": index, "stage": "train", "score": score, **config.to_dict(), **result.summary()
        })
    ranked.sort(key=lambda item: item[0], reverse=True)
    finalists: list[Selection] = []
    for score, config, train in ranked[:top_n]:
        validation = run_backtest(validation_frame, config, spec, starting_balance, prepared=True)
        final_score = _validation_score(train, validation)
        finalists.append(Selection(config, train, validation, validation, final_score))
        rows.append({
            "candidate": configs.index(config) + 1,
            "stage": "validation", "score": final_score, **config.to_dict(), **validation.summary()
        })
    finalists.sort(key=lambda item: item.score, reverse=True)
    if not finalists or finalists[0].score <= -10_000:
        # No configuration passed the strict gate. Return the least-bad candidate explicitly;
        # callers must report that validation failed rather than label it safe.
        best_train = ranked[0]
        validation = run_backtest(validation_frame, best_train[1], spec, starting_balance, prepared=True)
        holdout = run_backtest(holdout_frame, best_train[1], spec, starting_balance, prepared=True)
        selection = Selection(best_train[1], best_train[2], validation, holdout, _validation_score(best_train[2], validation))
    else:
        selected = finalists[0]
        holdout = run_backtest(holdout_frame, selected.config, spec, starting_balance, prepared=True)
        selection = Selection(selected.config, selected.train, selected.validation, holdout, selected.score)
    rows.append({
        "candidate": configs.index(selection.config) + 1,
        "stage": "holdout", "score": _validation_score(selection.validation, selection.holdout),
        **selection.config.to_dict(), **selection.holdout.summary(),
    })
    return selection, pd.DataFrame(rows)


def save_result(result: BacktestResult, directory: Path, prefix: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    records_frame(result.records).to_csv(directory / f"{prefix}_trades.csv", index=False)
    result.equity.to_csv(directory / f"{prefix}_equity.csv")
    with (directory / f"{prefix}_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(result.summary(), handle, indent=2, allow_nan=True)


def env_lines(config: StrategyConfig) -> list[str]:
    return [f"{key.upper()}={str(value).lower() if isinstance(value, bool) else value}" for key, value in config.to_dict().items()]
