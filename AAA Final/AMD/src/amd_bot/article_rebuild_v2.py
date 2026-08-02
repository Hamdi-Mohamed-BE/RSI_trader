from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
import math

import pandas as pd

from .article_engine import ArticleParams, backtest_article_model
from .article_walk_forward import Experiment, _base_params, _config
from .config import load_config
from .engine import Trade, metrics


UTC = timezone.utc


def _frame() -> pd.DataFrame:
    root = load_config().root
    paths = (
        root / "data" / "XAUUSD___20230620_20240730_M1.csv.gz",
        root / "data" / "XAUUSD___20240620_20250730_M1.csv.gz",
        root / "data" / "XAUUSD___20250620_20260730_M1.csv.gz",
    )
    frames = [pd.read_csv(path) for path in paths]
    result = pd.concat(frames, ignore_index=True)
    result["time"] = pd.to_datetime(result["time"], utc=True)
    return (
        result.drop_duplicates("time")
        .sort_values("time")
        .reset_index(drop=True)
    )


def _folds() -> tuple[tuple[str, datetime, datetime], ...]:
    return (
        ("2023_H2", datetime(2023, 7, 30, tzinfo=UTC), datetime(2024, 1, 30, tzinfo=UTC)),
        ("2024_H1", datetime(2024, 1, 30, tzinfo=UTC), datetime(2024, 7, 30, tzinfo=UTC)),
        ("2024_H2", datetime(2024, 7, 30, tzinfo=UTC), datetime(2025, 1, 30, tzinfo=UTC)),
        ("2025_H1", datetime(2025, 1, 30, tzinfo=UTC), datetime(2025, 7, 30, tzinfo=UTC)),
        ("2025_H2", datetime(2025, 7, 30, tzinfo=UTC), datetime(2026, 1, 30, tzinfo=UTC)),
        ("2026_H1", datetime(2026, 1, 30, tzinfo=UTC), datetime(2026, 7, 30, tzinfo=UTC)),
    )


def _experiments() -> list[Experiment]:
    base = _base_params()
    result = [
        Experiment("reference_broad", base, True, 0.65, 1.60, 0.40, 1.20, 0.30),
        Experiment(
            "reference_calm_fade",
            replace(base, enable_distribution=False),
            True,
            0.65,
            1.00,
            0.60,
            1.00,
            0.30,
        ),
    ]
    for fast, slow in ((4, 12), (8, 24), (12, 36), (20, 50)):
        for phase in ("both", "fade"):
            result.append(
                Experiment(
                    f"h1ema_{fast}_{slow}_{phase}",
                    replace(
                        base,
                        enable_distribution=phase == "both",
                        trend_filter_mode="h1_ema",
                        trend_fast=fast,
                        trend_slow=slow,
                        trend_price_alignment=True,
                    ),
                    True,
                    0.50,
                    1.60,
                    0.40,
                    1.20,
                    0.30,
                )
            )
    for lookahead in (3, 6, 12):
        mss = replace(
            base,
            enable_distribution=False,
            fade_confirmation_mode="mss",
            fade_mss_lookahead_bars=lookahead,
        )
        for regime, atr_min, atr_max, asia_min, asia_max in (
            ("broad", 0.50, 1.60, 0.40, 1.20),
            ("normal", 0.65, 1.20, 0.50, 1.10),
            ("calm", 0.65, 1.00, 0.60, 1.00),
        ):
            result.append(
                Experiment(
                    f"mss{lookahead}_{regime}",
                    mss,
                    True,
                    atr_min,
                    atr_max,
                    asia_min,
                    asia_max,
                    0.30,
                )
            )
    for rr in (1.0, 1.5, 2.0, 3.0):
        result.append(
            Experiment(
                f"mss6_normal_rr{rr}",
                replace(
                    base,
                    enable_distribution=False,
                    fade_confirmation_mode="mss",
                    fade_mss_lookahead_bars=6,
                    fade_rr=rr,
                ),
                True,
                0.65,
                1.20,
                0.50,
                1.10,
                0.30,
            )
        )
    for trigger in (0.50, 1.00, 99.0):
        result.append(
            Experiment(
                f"mss6_normal_lock{trigger}",
                replace(
                    base,
                    enable_distribution=False,
                    fade_confirmation_mode="mss",
                    fade_mss_lookahead_bars=6,
                ),
                True,
                0.65,
                1.20,
                0.50,
                1.10,
                trigger,
            )
        )
    return result


def _slice(trades: list[Trade], start: datetime, end: datetime) -> list[Trade]:
    lower = pd.Timestamp(start)
    upper = pd.Timestamp(end)
    return [
        trade
        for trade in trades
        if lower <= pd.Timestamp(trade.entry_time) < upper
    ]


def _pf(value: object) -> float:
    number = float(value)
    return number if math.isfinite(number) else 10.0


def _score(row: dict[str, object]) -> float:
    net = [float(row[f"{name}_net_r"]) for name, _, _ in _folds()]
    pfs = [_pf(row[f"{name}_pf"]) for name, _, _ in _folds()]
    counts = [int(row[f"{name}_trades"]) for name, _, _ in _folds()]
    positive = sum(value > 0 for value in net)
    if int(row["full_trades"]) < 40 or min(counts) < 3 or positive < 5:
        return -1000.0 + positive * 10.0 + int(row["full_trades"]) / 100.0
    return (
        min(pfs) * 4.0
        + float(pd.Series(pfs).median()) * 2.0
        + positive
        + float(row["full_net_r"]) / int(row["full_trades"]) * 4.0
        - float(row["full_dd"]) / 10.0
    )


def run() -> None:
    base_config = load_config()
    frame = _frame()
    start = datetime(2023, 7, 30, tzinfo=UTC)
    end = datetime(2026, 7, 30, tzinfo=UTC)
    rows: list[dict[str, object]] = []
    experiments = _experiments()
    for index, experiment in enumerate(experiments, 1):
        config = _config(base_config, experiment)
        trades = backtest_article_model(
            frame,
            "XAUUSD..",
            0.01,
            config,
            experiment.params,
            start,
            end,
        )
        full = metrics("XAUUSD..", trades, 1000.0, 3.0)
        row: dict[str, object] = {
            "name": experiment.name,
            "params": json.dumps(asdict(experiment.params), sort_keys=True),
            "relative_atr": experiment.relative_atr,
            "atr_min": experiment.atr_min,
            "atr_max": experiment.atr_max,
            "asia_min": experiment.asia_min,
            "asia_max": experiment.asia_max,
            "lock_trigger": experiment.lock_trigger,
            "lock_profit": experiment.lock_profit,
            "full_trades": full["trades"],
            "full_wr": full["win_rate_pct"],
            "full_pf": full["profit_factor"],
            "full_net_r": full["net_r"],
            "full_return": full["return_pct"],
            "full_dd": full["max_drawdown_pct"],
        }
        for name, fold_start, fold_end in _folds():
            fold = metrics(
                "XAUUSD..",
                _slice(trades, fold_start, fold_end),
                1000.0,
                3.0,
            )
            row[f"{name}_trades"] = fold["trades"]
            row[f"{name}_pf"] = fold["profit_factor"]
            row[f"{name}_net_r"] = fold["net_r"]
            row[f"{name}_dd"] = fold["max_drawdown_pct"]
        row["positive_folds"] = sum(
            float(row[f"{name}_net_r"]) > 0 for name, _, _ in _folds()
        )
        row["score"] = _score(row)
        rows.append(row)
        print(
            f"[{index:02d}/{len(experiments):02d}] {experiment.name}: "
            f"{int(full['trades'])} trades | WR "
            f"{float(full['win_rate_pct']):.1f}% | PF "
            f"{float(full['profit_factor']):.2f} | "
            f"{float(full['net_r']):+.2f}R | DD "
            f"{float(full['max_drawdown_pct']):.1f}%",
            flush=True,
        )
    result = pd.DataFrame(rows).sort_values(
        ["score", "full_pf"],
        ascending=False,
    )
    report_dir = base_config.root / "reports" / "robust_rebuild"
    report_dir.mkdir(parents=True, exist_ok=True)
    result.to_csv(report_dir / "three_year_rebuild.csv", index=False)
    (report_dir / "three_year_winner.json").write_text(
        json.dumps(result.iloc[0].to_dict(), indent=2, default=str),
        encoding="utf-8",
    )
    columns = [
        "name", "full_trades", "full_wr", "full_pf", "full_net_r",
        "full_return", "full_dd", "positive_folds",
    ]
    for name, _, _ in _folds():
        columns.extend([f"{name}_pf", f"{name}_net_r"])
    columns.append("score")
    print("\nTOP THREE-YEAR MODELS")
    print(result[columns].head(12).to_string(index=False))


if __name__ == "__main__":
    run()
