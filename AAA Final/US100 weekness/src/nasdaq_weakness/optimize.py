from __future__ import annotations

from dataclasses import asdict
from datetime import date
import itertools
import math

import pandas as pd

from .backtest import run_backtest
from .config import Config
from .models import BacktestResult
from .strategy import available_ny_dates


def chronological_splits(
    frame: pd.DataFrame,
) -> tuple[tuple[date, date], tuple[date, date], tuple[date, date]]:
    dates = available_ny_dates(frame)
    if len(dates) < 12:
        raise ValueError(
            f"Only {len(dates)} calendar dates are available; at least 12 "
            "are required for train/validation/holdout separation."
        )
    first_cut = max(1, int(len(dates) * 0.60))
    second_cut = max(first_cut + 1, int(len(dates) * 0.80))
    second_cut = min(second_cut, len(dates) - 1)
    return (
        (dates[0], dates[first_cut - 1]),
        (dates[first_cut], dates[second_cut - 1]),
        (dates[second_cut], dates[-1]),
    )


def parameter_grid(config: Config) -> list[Config]:
    candidates: list[Config] = []
    seen: set[tuple[object, ...]] = set()
    for mode in ("S1", "S2A", "S2B", "ALL"):
        rr_values = (2.0,) if mode == "S1" else (2.0, 3.0)
        pending_values = ("OCO",) if mode == "S1" else ("OCO", "BOTH")
        trail_values = (1, 2) if mode in {"S1", "ALL"} else (1,)
        s2a_models = (
            ("DIRECT", "REFERENCE_PAIR")
            if mode in {"S2A", "ALL"}
            else ("REFERENCE_PAIR",)
        )
        s2b_models = (
            ("CLOSE_PLUS_50", "MID_LOW_PAIR")
            if mode in {"S2B", "ALL"}
            else ("CLOSE_PLUS_50",)
        )
        for conversion, rr, pending, trail, s2a_model, s2b_model in itertools.product(
            (0.1, 1.0),
            rr_values,
            pending_values,
            trail_values,
            s2a_models,
            s2b_models,
        ):
            key = (
                mode,
                conversion,
                rr,
                pending,
                trail,
                s2a_model,
                s2b_model,
            )
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                config.with_parameters(
                    strategy_mode=mode,
                    note_point_to_price=conversion,
                    target_rr=rr,
                    pending_mode=pending,
                    runner_trail_bars=trail,
                    s2a_entry_model=s2a_model,
                    s2b_entry_model=s2b_model,
                )
            )
    return candidates


def _score(result: BacktestResult) -> float:
    stats = result.stats
    if stats.trades < 5 or stats.losses < 2:
        return -1_000 + stats.trades
    pf = min(stats.profit_factor, 5.0)
    return (
        stats.expectancy_r * math.sqrt(stats.trades)
        + pf
        - stats.max_drawdown_pct / 20
        - max(0, 10 - stats.trades) * 0.08
    )


def optimize(
    frame: pd.DataFrame,
    symbol: str,
    config: Config,
    *,
    point: float,
) -> dict[str, object]:
    train, validation, holdout = chronological_splits(frame)
    leaderboard: list[dict[str, object]] = []
    best_config: Config | None = None
    best_result: BacktestResult | None = None
    best_score = -math.inf
    for candidate in parameter_grid(config):
        result = run_backtest(
            frame,
            symbol,
            candidate,
            point=point,
            start_date=train[0],
            end_date=train[1],
        )
        score = _score(result)
        row = {
            **result.parameters,
            **asdict(result.stats),
            "score": score,
        }
        leaderboard.append(row)
        if score > best_score:
            best_score = score
            best_config = candidate
            best_result = result
    assert best_config is not None and best_result is not None
    val_result = run_backtest(
        frame,
        symbol,
        best_config,
        point=point,
        start_date=validation[0],
        end_date=validation[1],
    )
    holdout_result = run_backtest(
        frame,
        symbol,
        best_config,
        point=point,
        start_date=holdout[0],
        end_date=holdout[1],
    )
    full_result = run_backtest(
        frame, symbol, best_config, point=point
    )
    approved = (
        best_result.stats.trades >= 10
        and best_result.stats.profit_factor >= 1.30
        and val_result.stats.trades >= 3
        and val_result.stats.profit_factor >= 1.10
        and val_result.stats.expectancy_r > 0
        and holdout_result.stats.trades >= 3
        and holdout_result.stats.profit_factor >= 1.10
        and holdout_result.stats.expectancy_r > 0
        and full_result.stats.max_drawdown_pct <= 20
    )
    reasons: list[str] = []
    if best_result.stats.trades < 10:
        reasons.append("fewer than 10 training ideas")
    if best_result.stats.profit_factor < 1.30:
        reasons.append("training profit factor below 1.30")
    if val_result.stats.trades < 3:
        reasons.append("fewer than 3 validation ideas")
    if (
        val_result.stats.profit_factor < 1.10
        or val_result.stats.expectancy_r <= 0
    ):
        reasons.append("validation PF/expectancy gate failed")
    if holdout_result.stats.trades < 3:
        reasons.append("fewer than 3 untouched-holdout ideas")
    if (
        holdout_result.stats.profit_factor < 1.10
        or holdout_result.stats.expectancy_r <= 0
    ):
        reasons.append("untouched-holdout PF/expectancy gate failed")
    if full_result.stats.max_drawdown_pct > 20:
        reasons.append("full-sample drawdown exceeded 20%")
    leaderboard.sort(key=lambda item: float(item["score"]), reverse=True)
    return {
        "symbol": symbol,
        "risk_pct": config.risk_pct,
        "split_dates": {
            "training": [train[0].isoformat(), train[1].isoformat()],
            "validation": [
                validation[0].isoformat(),
                validation[1].isoformat(),
            ],
            "untouched_holdout": [
                holdout[0].isoformat(),
                holdout[1].isoformat(),
            ],
        },
        "best_parameters": full_result.parameters,
        "training": asdict(best_result.stats),
        "validation": asdict(val_result.stats),
        "untouched_holdout": asdict(holdout_result.stats),
        "full_sample": asdict(full_result.stats),
        "approved_for_forward": approved,
        "reasons": reasons,
        "leaderboard": leaderboard,
        "full_result": full_result,
    }
