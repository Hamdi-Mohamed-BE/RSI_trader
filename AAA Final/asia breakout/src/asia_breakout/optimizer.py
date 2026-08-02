from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from itertools import product
from math import isfinite

import pandas as pd

from .config import StrategyConfig
from .engine import backtest_prepared, calculate_metrics, prepare_sessions


ENTRY_MODES = ("mechanical_oco", "confirmed_close", "close_retest")
STOP_MODES = ("midpoint", "opposite")
RR_VALUES = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
EXTENDED_RR_VALUES = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0)
TRAIL_START_VALUES = (0.5, 1.0, 1.5, 2.0)
TRAIL_DISTANCE_VALUES = (0.5, 1.0, 1.5)
BUFFER_FRACTIONS = (0.0, 0.03, 0.05, 0.10)
MAX_RANGE_ADR = (0.25, 0.35, 0.50, 0.70, 1.00)


def parameter_grid(base: StrategyConfig):
    for mode, stop, rr, buffer, max_adr in product(
        ENTRY_MODES,
        STOP_MODES,
        RR_VALUES,
        BUFFER_FRACTIONS,
        MAX_RANGE_ADR,
    ):
        yield base.evolved(
            entry_mode=mode,
            stop_mode=stop,
            rr=rr,
            exit_mode="fixed",
            buffer_range_fraction=buffer,
            max_range_adr_fraction=max_adr,
        )


def _score(row: dict[str, object]) -> float:
    trades = int(row["trades"])
    losses = int(row["losses"])
    if trades < 8 or losses < 1:
        return -1e9
    pf = float(row["profit_factor"])
    pf_component = min(pf, 4.0) if isfinite(pf) else 4.0
    return (
        float(row["net_r"])
        + 0.75 * min(
            float(row["first_half_net_r"]),
            float(row["second_half_net_r"]),
        )
        - 0.20 * float(row["max_drawdown_pct"])
        + 1.5 * pf_component
        + 0.03 * trades
    )


def optimize_symbol(
    frame: pd.DataFrame,
    symbol: str,
    point: float,
    base: StrategyConfig,
    test_start: datetime,
    test_end: datetime,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    best_trades = pd.DataFrame()
    best_score = -1e18
    split_date = (test_start + (test_end - test_start) / 2).date()
    sessions = prepare_sessions(frame, base, test_start, test_end)
    seen: set[tuple[object, ...]] = set()

    def evaluate(config: StrategyConfig) -> None:
        nonlocal best_score, best_trades
        key = (
            config.entry_mode,
            config.stop_mode,
            config.rr,
            config.exit_mode,
            config.trail_start_r,
            config.trail_distance_r,
            config.buffer_range_fraction,
            config.max_range_adr_fraction,
        )
        if key in seen:
            return
        seen.add(key)
        trades = backtest_prepared(sessions, symbol, point, config)
        metrics = calculate_metrics(
            trades, symbol, base.starting_balance, base.risk_pct
        )
        row = metrics.to_dict()
        row.update(
            entry_mode=config.entry_mode,
            stop_mode=config.stop_mode,
            rr=config.rr,
            exit_mode=config.exit_mode,
            trail_start_r=config.trail_start_r,
            trail_distance_r=config.trail_distance_r,
            buffer_range_fraction=config.buffer_range_fraction,
            min_range_adr_fraction=config.min_range_adr_fraction,
            max_range_adr_fraction=config.max_range_adr_fraction,
            retest_bars=config.retest_bars,
        )
        row["first_half_net_r"] = sum(
            item.pnl_r for item in trades if item.session_date < split_date
        )
        row["second_half_net_r"] = sum(
            item.pnl_r for item in trades if item.session_date >= split_date
        )
        row["score"] = _score(row)
        rows.append(row)
        if float(row["score"]) > best_score:
            best_score = float(row["score"])
            best_trades = pd.DataFrame(item.to_dict() for item in trades)

    for config in parameter_grid(base):
        evaluate(config)

    initial = pd.DataFrame(rows).sort_values("score", ascending=False)
    structure_keys = [
        "entry_mode",
        "stop_mode",
        "buffer_range_fraction",
        "max_range_adr_fraction",
    ]
    structures = initial.drop_duplicates(structure_keys).head(4)
    for _, structure in structures.iterrows():
        structural = dict(
            entry_mode=str(structure["entry_mode"]),
            stop_mode=str(structure["stop_mode"]),
            buffer_range_fraction=float(structure["buffer_range_fraction"]),
            max_range_adr_fraction=float(structure["max_range_adr_fraction"]),
        )
        for rr in EXTENDED_RR_VALUES:
            evaluate(
                base.evolved(
                    **structural,
                    rr=rr,
                    exit_mode="fixed",
                )
            )
            for start, distance in product(
                TRAIL_START_VALUES,
                TRAIL_DISTANCE_VALUES,
            ):
                if start >= rr:
                    continue
                evaluate(
                    base.evolved(
                        **structural,
                        rr=rr,
                        exit_mode="trailing",
                        trail_start_r=start,
                        trail_distance_r=distance,
                    )
                )
    results = pd.DataFrame(rows).sort_values(
        ["score", "profit_factor", "net_r"], ascending=False
    )
    return results.reset_index(drop=True), best_trades


def universal_config_summary(results: pd.DataFrame) -> pd.DataFrame:
    """Rank one configuration that behaves robustly across every symbol."""
    total_symbols = int(results["symbol"].nunique())
    keys = [
        "entry_mode",
        "stop_mode",
        "rr",
        "exit_mode",
        "trail_start_r",
        "trail_distance_r",
        "buffer_range_fraction",
        "min_range_adr_fraction",
        "max_range_adr_fraction",
        "retest_bars",
    ]
    grouped = (
        results.groupby(keys, dropna=False)
        .agg(
            symbols=("symbol", "nunique"),
            trades=("trades", "sum"),
            wins=("wins", "sum"),
            losses=("losses", "sum"),
            net_r=("net_r", "sum"),
            gross_profit_r=("gross_profit_r", "sum"),
            gross_loss_r=("gross_loss_r", "sum"),
            worst_symbol_net_r=("net_r", "min"),
            profitable_symbols=("net_r", lambda values: int((values > 0).sum())),
            worst_drawdown_pct=("max_drawdown_pct", "max"),
            first_half_net_r=("first_half_net_r", "sum"),
            second_half_net_r=("second_half_net_r", "sum"),
        )
        .reset_index()
    )
    # Exit refinements are intentionally tested only around each symbol's
    # strongest structures. Do not let a one-symbol refinement masquerade as
    # a universal configuration.
    grouped = grouped[grouped["symbols"] == total_symbols].copy()
    grouped["win_rate_pct"] = grouped["wins"] / grouped["trades"] * 100.0
    grouped["profit_factor"] = (
        grouped["gross_profit_r"] / grouped["gross_loss_r"].replace(0.0, pd.NA)
    ).fillna(float("inf"))
    grouped["score"] = (
        grouped["net_r"]
        + 1.5 * grouped["worst_symbol_net_r"]
        + 0.75
        * grouped[["first_half_net_r", "second_half_net_r"]].min(axis=1)
        + 0.5 * grouped["profitable_symbols"]
        - 0.15 * grouped["worst_drawdown_pct"]
    )
    return grouped.sort_values(
        ["score", "profitable_symbols", "profit_factor"],
        ascending=False,
    ).reset_index(drop=True)
