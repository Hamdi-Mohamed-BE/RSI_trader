from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .backtest import BacktestResult, run_backtest
from .config import AppConfig
from .models import BacktestStats, Trade


@dataclass(frozen=True)
class SplitResult:
    name: str
    start: datetime
    end: datetime
    trades: int
    win_rate: float
    profit_factor: float
    expectancy_r: float
    net_r: float


@dataclass(frozen=True)
class ValidationResult:
    baseline: BacktestResult
    splits: tuple[SplitResult, ...]
    stress: tuple[dict[str, float | int], ...]
    approved_for_forward: bool
    reasons: tuple[str, ...]


def _split_stats(name: str, trades: list[Trade], start: datetime, end: datetime) -> SplitResult:
    values = [trade.result_r for trade in trades]
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    gross_loss = abs(sum(losses))
    profit_factor = sum(wins) / gross_loss if gross_loss else float("inf") if wins else 0.0
    return SplitResult(
        name=name,
        start=start,
        end=end,
        trades=len(trades),
        win_rate=len(wins) / len(values) * 100 if values else 0.0,
        profit_factor=profit_factor,
        expectancy_r=sum(values) / len(values) if values else 0.0,
        net_r=sum(values),
    )


def chronological_splits(result: BacktestResult) -> tuple[SplitResult, ...]:
    if result.h1.empty:
        return ()
    start = result.h1["time"].iloc[0].to_pydatetime()
    end = result.h1["time"].iloc[-1].to_pydatetime()
    duration = end - start
    development_end = start + duration * 0.60
    validation_end = start + duration * 0.80
    definitions = (
        ("development", start, development_end),
        ("validation", development_end, validation_end),
        ("untouched_holdout", validation_end, end),
    )
    splits: list[SplitResult] = []
    for name, split_start, split_end in definitions:
        trades = [
            trade
            for trade in result.trades
            if split_start <= trade.signal_time < split_end
        ]
        splits.append(_split_stats(name, trades, split_start, split_end))
    return tuple(splits)


def run_validation(m1, symbol: str, config: AppConfig) -> ValidationResult:
    baseline = run_backtest(m1, symbol, config)
    splits = chronological_splits(baseline)
    stress_results: list[dict[str, float | int]] = []
    variants = (
        ("spread_1.5x", 1.5, config.profile_rows),
        ("spread_2.0x", 2.0, config.profile_rows),
        ("profile_96", 1.0, 96),
        ("profile_160", 1.0, 160),
    ) if baseline.stats.profit_factor >= 1.0 else ()
    for name, spread, rows in variants:
        result = run_backtest(
            m1,
            symbol,
            config,
            spread_multiplier=spread,
            profile_rows=rows,
        )
        stress_results.append(
            {
                "variant": name,
                "trades": result.stats.trades,
                "profit_factor": result.stats.profit_factor,
                "expectancy_r": result.stats.expectancy_r,
                "max_drawdown_pct": result.stats.max_drawdown_pct,
            }
        )
    reasons: list[str] = []
    holdout = next(
        (split for split in splits if split.name == "untouched_holdout"),
        None,
    )
    if baseline.stats.trades < 100:
        reasons.append("fewer than 100 historical trades")
    if baseline.stats.profit_factor < 1.30:
        reasons.append("baseline profit factor below 1.30")
    if holdout is None or holdout.trades < 40:
        reasons.append("fewer than 40 untouched-holdout trades")
    if holdout is None or holdout.profit_factor < 1.35 or holdout.expectancy_r < 0.15:
        reasons.append("untouched holdout failed PF/expectancy gates")
    if stress_results and any(
        float(item["profit_factor"]) < 1.10 for item in stress_results
    ):
        reasons.append("one or more cost/parameter stress variants failed")
    if not stress_results:
        reasons.append("robustness tests skipped because the baseline already failed")
    return ValidationResult(
        baseline=baseline,
        splits=splits,
        stress=tuple(stress_results),
        approved_for_forward=not reasons,
        reasons=tuple(reasons),
    )
