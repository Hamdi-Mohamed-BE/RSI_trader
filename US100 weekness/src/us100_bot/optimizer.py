from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import pandas as pd

from .analytics import metrics, trades_frame
from .config import Config
from .models import Skip, Trade
from .normalization import PriceNormalizer
from .strategies import Backtest, evolve


@dataclass(frozen=True, slots=True)
class Variant:
    name: str
    changes: dict[str, Any]


CANDIDATES: dict[str, tuple[Variant, ...]] = {
    "A_FIXED": (
        Variant("baseline_50_100", {}),
        Variant("tight_40_80", {"a_stop_pips": 40.0, "a_target_pips": 80.0}),
        Variant("wide_60_120", {"a_stop_pips": 60.0, "a_target_pips": 120.0}),
        Variant("rr3_50_150", {"a_stop_pips": 50.0, "a_target_pips": 150.0}),
    ),
    "A_RUNNER": (
        Variant("baseline_prev_m15", {}),
        Variant("prev_m15_be1", {"a_break_even_r": 1.0}),
        Variant("previous_two_m15", {"a_runner_method": "previous_two_m15"}),
        Variant("atr_be1", {"a_runner_method": "atr", "a_break_even_r": 1.0}),
        Variant("prev_m15_buffer5", {"a_trail_buffer_pips": 5.0}),
    ),
    "B1": (
        Variant("baseline_london_2R", {}),
        Variant("second_high_2R", {"b1_stop_reference": "second_candle_high"}),
        Variant("reference_high_2R", {"b1_stop_reference": "reference_candle_high"}),
        Variant("london_1.5R", {"b1_rr": 1.5}),
        Variant("london_2.5R", {"b1_rr": 2.5}),
        Variant("london_3R", {"b1_rr": 3.0}),
        Variant("body5_london_2R", {"doji_body_pips": 5.0}),
    ),
    "B2": (
        Variant("baseline_close_plus50", {}),
        Variant("close_plus35", {"b2_entry_pips": 35.0}),
        Variant("close_plus75", {"b2_entry_pips": 75.0}),
        Variant("candle_midpoint", {"b2_pullback_mode": "candle_midpoint"}),
        Variant("candle_50pct", {"b2_pullback_mode": "candle_50pct"}),
        Variant("reference_midpoint", {"b2_pullback_mode": "reference_midpoint"}),
        Variant("baseline_1.5R", {"b2_rr": 1.5}),
        Variant("baseline_2.5R", {"b2_rr": 2.5}),
        Variant("baseline_3R", {"b2_rr": 3.0}),
    ),
}


def _score(metric: dict[str, Any]) -> float:
    count = int(metric.get("trades", 0))
    if count < 8:
        return -10_000 + count
    pf_raw = metric.get("profit_factor", 0)
    pf = 10.0 if pf_raw == "inf" else float(pf_raw)
    dd = max(float(metric.get("max_dd_pct", 0)), 0.25)
    expectancy = float(metric.get("expected_payoff", 0))
    net = float(metric.get("net_profit", 0))
    # Stability-oriented objective; trade-count term penalizes tiny samples.
    return min(pf, 5.0) * 2.0 + net / dd / 100.0 + expectancy / 20.0 + min(count, 40) / 20


def walk_forward(
    raw: pd.DataFrame,
    cfg: Config,
    norm: PriceNormalizer,
    train_days: int = 180,
    test_days: int = 90,
) -> tuple[list[Trade], list[Skip], pd.DataFrame]:
    data = raw.copy()
    data["time"] = pd.to_datetime(data["time"], utc=True)
    first = data["time"].min().floor("D")
    last = data["time"].max().ceil("D")
    rows: list[dict[str, Any]] = []
    oos_trades: list[Trade] = []
    oos_skips: list[Skip] = []
    test_start = first + pd.Timedelta(days=train_days)
    fold = 1
    while test_start < last:
        train_start = test_start - pd.Timedelta(days=train_days)
        test_end = min(test_start + pd.Timedelta(days=test_days), last)
        if test_end - test_start < pd.Timedelta(days=60):
            break
        train = data[(data["time"] >= train_start) & (data["time"] < test_start)]
        test = data[(data["time"] >= test_start) & (data["time"] < test_end)]
        if train.empty or test.empty:
            break
        for strategy, variants in CANDIDATES.items():
            ranked: list[tuple[float, Variant, dict[str, Any]]] = []
            for variant in variants:
                candidate = evolve(cfg, **variant.changes)
                tr, _ = Backtest(candidate, norm).run(train, (strategy,))
                met = metrics(trades_frame(tr), cfg.starting_balance)
                ranked.append((_score(met), variant, met))
            ranked.sort(key=lambda x: x[0], reverse=True)
            _, selected, train_metrics = ranked[0]
            selected_cfg = evolve(cfg, **selected.changes)
            test_trades, test_skips = Backtest(selected_cfg, norm).run(test, (strategy,))
            test_metrics = metrics(trades_frame(test_trades), cfg.starting_balance)
            for trade in test_trades:
                trade.metadata["walk_forward_fold"] = fold
                trade.metadata["selected_variant"] = selected.name
            oos_trades.extend(test_trades)
            oos_skips.extend(test_skips)
            rows.append(
                {
                    "fold": fold,
                    "strategy": strategy,
                    "train_start": str(train_start.date()),
                    "train_end": str((test_start - pd.Timedelta(days=1)).date()),
                    "test_start": str(test_start.date()),
                    "test_end": str((test_end - pd.Timedelta(days=1)).date()),
                    "selected": selected.name,
                    "changes": repr(selected.changes),
                    "train_trades": train_metrics.get("trades", 0),
                    "train_pf": train_metrics.get("profit_factor", 0),
                    "train_dd_pct": train_metrics.get("max_dd_pct", 0),
                    "oos_trades": test_metrics.get("trades", 0),
                    "oos_pf": test_metrics.get("profit_factor", 0),
                    "oos_net": test_metrics.get("net_profit", 0),
                    "oos_dd_pct": test_metrics.get("max_dd_pct", 0),
                }
            )
        test_start += pd.Timedelta(days=test_days)
        fold += 1
    return sorted(oos_trades, key=lambda t: t.entry_time), oos_skips, pd.DataFrame(rows)


def robustness(
    raw: pd.DataFrame,
    cfg: Config,
    norm: PriceNormalizer,
    strategies: tuple[str, ...] = ("A_FIXED", "A_RUNNER", "B1", "B2"),
) -> pd.DataFrame:
    scenarios: list[tuple[str, pd.DataFrame, Config]] = [("baseline", raw, cfg)]
    for factor in (1.25, 1.50, 2.0):
        stressed = raw.copy()
        stressed["spread"] = (stressed["spread"].astype(float) * factor).round()
        scenarios.append((f"spread_x{factor:.2f}", stressed, cfg))
    for extra in (1.0, 2.0, 5.0):
        scenarios.append(
            (f"extra_slippage_{extra:g}pip", raw, evolve(cfg, slippage_pips=cfg.slippage_pips + extra))
        )
    scenarios.extend(
        [
            ("A_stop_minus10", raw, evolve(cfg, a_stop_pips=max(10, cfg.a_stop_pips - 10))),
            ("A_stop_plus10", raw, evolve(cfg, a_stop_pips=cfg.a_stop_pips + 10)),
            ("targets_minus10pct", raw, evolve(cfg, a_target_pips=cfg.a_target_pips * 0.9, b1_rr=cfg.b1_rr * 0.9, b2_rr=cfg.b2_rr * 0.9)),
            ("targets_plus10pct", raw, evolve(cfg, a_target_pips=cfg.a_target_pips * 1.1, b1_rr=cfg.b1_rr * 1.1, b2_rr=cfg.b2_rr * 1.1)),
        ]
    )
    rows = []
    for name, bars, scenario_cfg in scenarios:
        tr, _ = Backtest(scenario_cfg, norm).run(bars, strategies)
        frame = trades_frame(tr)
        met = metrics(frame, cfg.starting_balance)
        rows.append({"scenario": name, **met})
    return pd.DataFrame(rows)
