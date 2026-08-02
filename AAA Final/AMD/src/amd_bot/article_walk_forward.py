from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
import math
from pathlib import Path

import pandas as pd

from .article_engine import ArticleParams, backtest_article_model
from .config import Config, load_config
from .engine import Trade, metrics


UTC = timezone.utc


@dataclass(frozen=True, slots=True)
class Experiment:
    name: str
    params: ArticleParams
    relative_atr: bool
    atr_min: float
    atr_max: float
    asia_min: float
    asia_max: float
    lock_trigger: float
    lock_profit: float = 0.15


def _read_cached_frame(root: Path) -> pd.DataFrame:
    paths = (
        root / "data" / "XAUUSD___20240620_20250730_M1.csv.gz",
        root / "data" / "XAUUSD___20250620_20260730_M1.csv.gz",
    )
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Required development caches are missing: " + ", ".join(missing)
        )
    frames = [pd.read_csv(path) for path in paths]
    frame = pd.concat(frames, ignore_index=True)
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    return (
        frame.drop_duplicates("time")
        .sort_values("time")
        .reset_index(drop=True)
    )


def _base_params() -> ArticleParams:
    return ArticleParams(
        enable_fade=True,
        enable_distribution=True,
        trade_london=True,
        trade_new_york=False,
        max_trades_per_day=1,
        fade_rr=2.0,
        distribution_rr=2.0,
        sweep_min_fraction=0.02,
        sweep_max_fraction=0.60,
        breakout_fraction=0.00,
        retest_tolerance_fraction=0.04,
        stop_buffer_fraction=0.03,
        volume_factor=0.0,
        use_regime_filter=True,
        london_window_minutes=180,
        ny_window_minutes=180,
    )


def _experiments() -> list[Experiment]:
    base = _base_params()
    experiments: list[Experiment] = [
        Experiment(
            "old_fixed_baseline",
            base,
            False,
            1.5,
            2.8,
            0.40,
            1.20,
            0.30,
        ),
        Experiment(
            "relative_baseline",
            base,
            True,
            0.65,
            1.60,
            0.40,
            1.20,
            0.30,
        ),
        Experiment(
            "relative_tight",
            base,
            True,
            0.75,
            1.40,
            0.50,
            1.10,
            0.30,
        ),
        Experiment(
            "relative_plain_fade_only",
            replace(base, enable_distribution=False),
            True,
            0.65,
            1.60,
            0.40,
            1.20,
            0.30,
        ),
        Experiment(
            "relative_plain_distribution_only",
            replace(base, enable_fade=False),
            True,
            0.65,
            1.60,
            0.40,
            1.20,
            0.30,
        ),
    ]

    quality_variants: tuple[tuple[str, dict[str, object]], ...] = (
        (
            "directional",
            {"require_directional_confirmation": True},
        ),
        (
            "quality20",
            {
                "require_directional_confirmation": True,
                "min_body_fraction": 0.20,
                "min_close_location": 0.60,
            },
        ),
        (
            "quality30",
            {
                "require_directional_confirmation": True,
                "min_body_fraction": 0.30,
                "min_close_location": 0.65,
            },
        ),
        (
            "quality20_risk60",
            {
                "require_directional_confirmation": True,
                "min_body_fraction": 0.20,
                "min_close_location": 0.60,
                "max_risk_fraction": 0.60,
            },
        ),
        (
            "quality20_reclaim03",
            {
                "require_directional_confirmation": True,
                "min_body_fraction": 0.20,
                "min_close_location": 0.60,
                "fade_reclaim_fraction": 0.03,
                "distribution_hold_fraction": 0.02,
            },
        ),
        (
            "quality30_reclaim05",
            {
                "require_directional_confirmation": True,
                "min_body_fraction": 0.30,
                "min_close_location": 0.65,
                "fade_reclaim_fraction": 0.05,
                "distribution_hold_fraction": 0.03,
                "max_risk_fraction": 0.75,
            },
        ),
    )
    for label, updates in quality_variants:
        params = replace(base, **updates)
        experiments.append(
            Experiment(
                f"relative_{label}",
                params,
                True,
                0.65,
                1.60,
                0.40,
                1.20,
                0.30,
            )
        )
        experiments.append(
            Experiment(
                f"relative_tight_{label}",
                params,
                True,
                0.75,
                1.40,
                0.50,
                1.10,
                0.30,
            )
        )

    robust = replace(
        base,
        require_directional_confirmation=True,
        min_body_fraction=0.20,
        min_close_location=0.60,
        fade_reclaim_fraction=0.03,
        distribution_hold_fraction=0.02,
        max_risk_fraction=0.75,
    )
    for phase, updates in (
        ("fade_only", {"enable_distribution": False}),
        ("distribution_only", {"enable_fade": False}),
    ):
        experiments.append(
            Experiment(
                f"relative_{phase}",
                replace(robust, **updates),
                True,
                0.65,
                1.60,
                0.40,
                1.20,
                0.30,
            )
        )
    for rr in (1.0, 1.5, 2.5, 3.0):
        experiments.append(
            Experiment(
                f"relative_plain_fade_rr{rr}",
                replace(
                    base,
                    enable_distribution=False,
                    fade_rr=rr,
                ),
                True,
                0.65,
                1.60,
                0.40,
                1.20,
                0.30,
            )
        )
    for trigger in (0.15, 0.50, 0.75, 1.00):
        experiments.append(
            Experiment(
                f"relative_plain_fade_lock{trigger}",
                replace(base, enable_distribution=False),
                True,
                0.65,
                1.60,
                0.40,
                1.20,
                trigger,
            )
        )
    for minimum, maximum in (
        (0.50, 1.00),
        (0.65, 0.90),
        (0.65, 1.00),
        (0.65, 1.10),
        (0.75, 1.00),
    ):
        experiments.append(
            Experiment(
                f"calm_fade_atr{minimum}_{maximum}",
                replace(base, enable_distribution=False),
                True,
                minimum,
                maximum,
                0.40,
                1.20,
                0.30,
            )
        )
    for asia_minimum, asia_maximum in (
        (0.50, 1.00),
        (0.60, 1.00),
        (0.50, 1.10),
        (0.60, 1.20),
    ):
        experiments.append(
            Experiment(
                f"calm_fade_asia{asia_minimum}_{asia_maximum}",
                replace(base, enable_distribution=False),
                True,
                0.65,
                1.00,
                asia_minimum,
                asia_maximum,
                0.30,
            )
        )
    for rr in (1.5, 2.5, 3.0):
        experiments.append(
            Experiment(
                f"calm_fade_rr{rr}",
                replace(
                    base,
                    enable_distribution=False,
                    fade_rr=rr,
                ),
                True,
                0.65,
                1.00,
                0.40,
                1.20,
                0.30,
            )
        )
    for trigger in (0.50, 0.75):
        experiments.append(
            Experiment(
                f"calm_fade_lock{trigger}",
                replace(base, enable_distribution=False),
                True,
                0.65,
                1.00,
                0.40,
                1.20,
                trigger,
            )
        )
    for rr in (1.5, 2.5):
        experiments.append(
            Experiment(
                f"relative_robust_rr{rr}",
                replace(robust, fade_rr=rr, distribution_rr=rr),
                True,
                0.65,
                1.60,
                0.40,
                1.20,
                0.30,
            )
        )
    for trigger in (0.50, 0.75):
        experiments.append(
            Experiment(
                f"relative_robust_lock{trigger}",
                robust,
                True,
                0.65,
                1.60,
                0.40,
                1.20,
                trigger,
            )
        )
    for minutes in (120, 240):
        experiments.append(
            Experiment(
                f"relative_robust_window{minutes}",
                replace(robust, london_window_minutes=minutes),
                True,
                0.65,
                1.60,
                0.40,
                1.20,
                0.30,
            )
        )
    for factor in (0.8, 1.0, 1.2):
        experiments.append(
            Experiment(
                f"relative_robust_volume{factor}",
                replace(robust, volume_factor=factor),
                True,
                0.65,
                1.60,
                0.40,
                1.20,
                0.30,
            )
        )
    experiments.append(
        Experiment(
            "relative_long_only_benchmark",
            replace(base, trend_filter_mode="long_only"),
            True,
            0.65,
            1.60,
            0.40,
            1.20,
            0.30,
        )
    )
    experiments.append(
        Experiment(
            "relative_short_only_benchmark",
            replace(base, trend_filter_mode="short_only"),
            True,
            0.65,
            1.60,
            0.40,
            1.20,
            0.30,
        )
    )
    for fast, slow in ((4, 12), (8, 24), (12, 36), (20, 50)):
        for aligned in (False, True):
            experiments.append(
                Experiment(
                    f"relative_h1ema_{fast}_{slow}_align{int(aligned)}",
                    replace(
                        base,
                        trend_filter_mode="h1_ema",
                        trend_fast=fast,
                        trend_slow=slow,
                        trend_price_alignment=aligned,
                    ),
                    True,
                    0.65,
                    1.60,
                    0.40,
                    1.20,
                    0.30,
                )
            )
    for phase, updates in (
        ("fade", {"enable_distribution": False}),
        ("distribution", {"enable_fade": False}),
    ):
        experiments.append(
            Experiment(
                f"relative_h1ema_8_24_{phase}",
                replace(
                    base,
                    trend_filter_mode="h1_ema",
                    trend_fast=8,
                    trend_slow=24,
                    trend_price_alignment=False,
                    **updates,
                ),
                True,
                0.65,
                1.60,
                0.40,
                1.20,
                0.30,
            )
        )
    return experiments


def _config(base: Config, experiment: Experiment) -> Config:
    return replace(
        base,
        risk_pct=3.0,
        lock_trigger_r=experiment.lock_trigger,
        lock_profit_r=experiment.lock_profit,
        regime_filter_enabled=True,
        regime_use_relative_atr=experiment.relative_atr,
        regime_atr_median_days=30,
        regime_atr_ratio_min=experiment.atr_min,
        regime_atr_ratio_max=experiment.atr_max,
        regime_atr_pct_min=experiment.atr_min,
        regime_atr_pct_max=experiment.atr_max,
        regime_asia_ratio_min=experiment.asia_min,
        regime_asia_ratio_max=experiment.asia_max,
    )


def _folds() -> tuple[tuple[str, datetime, datetime], ...]:
    return (
        (
            "2024_H2",
            datetime(2024, 7, 30, tzinfo=UTC),
            datetime(2025, 1, 30, tzinfo=UTC),
        ),
        (
            "2025_H1",
            datetime(2025, 1, 30, tzinfo=UTC),
            datetime(2025, 7, 30, tzinfo=UTC),
        ),
        (
            "2025_H2",
            datetime(2025, 7, 30, tzinfo=UTC),
            datetime(2026, 1, 30, tzinfo=UTC),
        ),
        (
            "2026_H1",
            datetime(2026, 1, 30, tzinfo=UTC),
            datetime(2026, 7, 30, tzinfo=UTC),
        ),
    )


def _trade_slice(
    trades: list[Trade],
    start: datetime,
    end: datetime,
) -> list[Trade]:
    lower = pd.Timestamp(start)
    upper = pd.Timestamp(end)
    return [
        trade
        for trade in trades
        if lower <= pd.Timestamp(trade.entry_time) < upper
    ]


def _finite_pf(value: object) -> float:
    result = float(value)
    return result if math.isfinite(result) else 10.0


def _score(row: dict[str, object]) -> float:
    fold_pfs = [_finite_pf(row[f"{name}_pf"]) for name, _, _ in _folds()]
    fold_nets = [float(row[f"{name}_net_r"]) for name, _, _ in _folds()]
    fold_trades = [int(row[f"{name}_trades"]) for name, _, _ in _folds()]
    positive_folds = sum(value > 0 for value in fold_nets)
    if min(fold_trades) < 5 or positive_folds < 3:
        return -1000.0 + positive_folds * 10.0 + sum(fold_trades) / 100.0
    stable_pf = min(fold_pfs)
    median_pf = float(pd.Series(fold_pfs).median())
    average_r = float(row["full_net_r"]) / max(int(row["full_trades"]), 1)
    return (
        stable_pf * 4.0
        + min(median_pf, 4.0) * 2.0
        + average_r * 4.0
        + positive_folds
        - float(row["full_dd"]) / 10.0
    )


def run() -> None:
    base = load_config()
    frame = _read_cached_frame(base.root)
    start = datetime(2024, 7, 30, tzinfo=UTC)
    end = datetime(2026, 7, 30, tzinfo=UTC)
    report_dir = base.root / "reports" / "robust_rebuild"
    report_dir.mkdir(parents=True, exist_ok=True)
    search_path = report_dir / "development_search.csv"
    rows: list[dict[str, object]] = []
    completed: set[str] = set()
    if search_path.exists():
        previous = pd.read_csv(search_path)
        rows = previous.to_dict(orient="records")
        completed = set(previous["name"].astype(str))
    experiments = _experiments()
    for index, experiment in enumerate(experiments, 1):
        if experiment.name in completed:
            continue
        config = _config(base, experiment)
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
            fold_metrics = metrics(
                "XAUUSD..",
                _trade_slice(trades, fold_start, fold_end),
                1000.0,
                3.0,
            )
            row[f"{name}_trades"] = fold_metrics["trades"]
            row[f"{name}_pf"] = fold_metrics["profit_factor"]
            row[f"{name}_net_r"] = fold_metrics["net_r"]
            row[f"{name}_dd"] = fold_metrics["max_drawdown_pct"]
        row["positive_folds"] = sum(
            float(row[f"{name}_net_r"]) > 0 for name, _, _ in _folds()
        )
        row["score"] = _score(row)
        rows.append(row)
        print(
            f"[{index:02d}/{len(experiments):02d}] "
            f"{experiment.name}: {int(full['trades'])} trades, "
            f"PF {float(full['profit_factor']):.2f}, "
            f"{float(full['net_r']):+.2f}R, "
            f"DD {float(full['max_drawdown_pct']):.2f}%",
            flush=True,
        )
    result = pd.DataFrame(rows).sort_values(
        ["score", "full_pf"],
        ascending=False,
    )
    result.to_csv(search_path, index=False)
    winner = result.iloc[0].to_dict()
    (report_dir / "development_winner.json").write_text(
        json.dumps(winner, indent=2, default=str),
        encoding="utf-8",
    )
    columns = [
        "name",
        "full_trades",
        "full_wr",
        "full_pf",
        "full_net_r",
        "full_return",
        "full_dd",
        "positive_folds",
        "2024_H2_pf",
        "2024_H2_net_r",
        "2025_H1_pf",
        "2025_H1_net_r",
        "2025_H2_pf",
        "2025_H2_net_r",
        "2026_H1_pf",
        "2026_H1_net_r",
        "score",
    ]
    print("\nTOP DEVELOPMENT MODELS")
    print(result[columns].head(10).to_string(index=False))


if __name__ == "__main__":
    run()
