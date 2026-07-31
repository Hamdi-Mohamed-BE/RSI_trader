from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
import math
from pathlib import Path

import pandas as pd

from .article_v2_engine import V2Params, backtest_v2_model
from .config import Config, load_config
from .engine import Trade, metrics


UTC = timezone.utc
DEVELOPMENT_START = datetime(2024, 7, 30, tzinfo=UTC)
HOLDOUT_START = datetime(2023, 7, 30, tzinfo=UTC)
HOLDOUT_END = DEVELOPMENT_START
END = datetime(2026, 7, 30, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class Experiment:
    name: str
    params: V2Params
    atr_min: float = 0.50
    atr_max: float = 1.60
    asia_min: float = 0.40
    asia_max: float = 1.20


def _frame(root: Path) -> pd.DataFrame:
    paths = (
        root / "data" / "XAUUSD___20230620_20240730_M1.csv.gz",
        root / "data" / "XAUUSD___20240620_20250730_M1.csv.gz",
        root / "data" / "XAUUSD___20250620_20260730_M1.csv.gz",
    )
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing research data: " + ", ".join(missing))
    frames = [pd.read_csv(path) for path in paths]
    result = pd.concat(frames, ignore_index=True)
    result["time"] = pd.to_datetime(result["time"], utc=True)
    return (
        result.drop_duplicates("time")
        .sort_values("time")
        .reset_index(drop=True)
    )


def _development_folds() -> tuple[tuple[str, datetime, datetime], ...]:
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


def _all_folds() -> tuple[tuple[str, datetime, datetime], ...]:
    return (
        (
            "2023_H2",
            datetime(2023, 7, 30, tzinfo=UTC),
            datetime(2024, 1, 30, tzinfo=UTC),
        ),
        (
            "2024_H1",
            datetime(2024, 1, 30, tzinfo=UTC),
            datetime(2024, 7, 30, tzinfo=UTC),
        ),
        *_development_folds(),
    )


def _config(base: Config, experiment: Experiment) -> Config:
    return replace(
        base,
        risk_pct=3.0,
        regime_filter_enabled=True,
        regime_use_relative_atr=True,
        regime_atr_days=5,
        regime_atr_median_days=30,
        regime_atr_ratio_min=experiment.atr_min,
        regime_atr_ratio_max=experiment.atr_max,
        regime_asia_median_days=20,
        regime_asia_ratio_min=experiment.asia_min,
        regime_asia_ratio_max=experiment.asia_max,
    )


def _structural_experiments() -> list[Experiment]:
    base = V2Params(
        enable_reversal=True,
        enable_continuation=False,
        trade_london=True,
        trade_new_york=False,
        max_trades_per_day=1,
        reversal_rr=2.0,
        sweep_min_fraction=0.02,
        sweep_max_fraction=0.60,
        displacement_body_fraction=0.50,
        displacement_close_location=0.65,
        fvg_entry_fraction=0.50,
        stop_buffer_fraction=0.03,
        max_risk_fraction=0.90,
        management_mode="none",
        use_regime_filter=True,
        london_window_minutes=240,
    )
    result: list[Experiment] = []
    for lookback in (2, 3, 5):
        for displacement in (1.0, 1.20):
            for gap in (0.0, 0.005):
                for retest in (6, 12):
                    params = replace(
                        base,
                        mss_lookback_bars=lookback,
                        displacement_range_factor=displacement,
                        fvg_min_fraction=gap,
                        fvg_retest_bars=retest,
                    )
                    result.append(
                        Experiment(
                            (
                                f"rev_mss{lookback}_disp{displacement}_"
                                f"gap{gap}_retest{retest}"
                            ),
                            params,
                        )
                    )
    continuation = replace(
        base,
        enable_reversal=False,
        enable_continuation=True,
        continuation_rr=2.0,
    )
    for displacement in (1.0, 1.20):
        for require_fvg in (False, True):
            for hold in (0.0, 0.02):
                params = replace(
                    continuation,
                    displacement_range_factor=displacement,
                    continuation_require_fvg=require_fvg,
                    breakout_hold_fraction=hold,
                )
                result.append(
                    Experiment(
                        (
                            f"cont_disp{displacement}_fvg"
                            f"{int(require_fvg)}_hold{hold}"
                        ),
                        params,
                    )
                )
    return result


def _slice(
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
    number = float(value)
    return min(number, 5.0) if math.isfinite(number) else 5.0


def _evaluate(
    frame: pd.DataFrame,
    base_config: Config,
    experiment: Experiment,
    start: datetime,
    end: datetime,
    folds: tuple[tuple[str, datetime, datetime], ...],
) -> tuple[dict[str, object], list[Trade]]:
    config = _config(base_config, experiment)
    trades = backtest_v2_model(
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
        "atr_min": experiment.atr_min,
        "atr_max": experiment.atr_max,
        "asia_min": experiment.asia_min,
        "asia_max": experiment.asia_max,
        "trades": full["trades"],
        "win_rate": full["win_rate_pct"],
        "pf": full["profit_factor"],
        "net_r": full["net_r"],
        "return": full["return_pct"],
        "dd": full["max_drawdown_pct"],
    }
    positive = 0
    fold_pfs: list[float] = []
    fold_counts: list[int] = []
    for name, fold_start, fold_end in folds:
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
        positive += float(fold["net_r"]) > 0
        fold_pfs.append(_finite_pf(fold["profit_factor"]))
        fold_counts.append(int(fold["trades"]))
    row["positive_folds"] = positive
    trade_count = int(full["trades"])
    expectancy = float(full["net_r"]) / trade_count if trade_count else -10.0
    score = (
        positive * 10.0
        + min(fold_pfs, default=0.0) * 3.0
        + float(pd.Series(fold_pfs).median()) * 2.0
        + expectancy * 5.0
        - float(full["max_drawdown_pct"]) / 8.0
    )
    if trade_count < 30 or min(fold_counts, default=0) < 3:
        score -= 100.0
    row["score"] = score
    return row, trades


def _management_experiments(
    structural: pd.DataFrame,
) -> list[Experiment]:
    result: list[Experiment] = []
    top = structural.head(3)
    regimes = (
        ("broad", 0.50, 1.60, 0.40, 1.20),
        ("normal", 0.65, 1.20, 0.50, 1.10),
        ("calm", 0.65, 1.00, 0.60, 1.00),
    )
    management = (
        ("none_2r", "none", 2.0, 0.0, 99.0, 0.0, 99.0, 1.0),
        ("none_3r", "none", 3.0, 0.0, 99.0, 0.0, 99.0, 1.0),
        ("be1_2r", "be_confirmed", 2.0, 0.0, 1.0, 0.0, 99.0, 1.0),
        ("partial25_3r", "partial_be", 3.0, 0.25, 1.0, 0.0, 99.0, 1.0),
        ("trail2_3r", "trail", 3.0, 0.0, 1.0, 0.0, 2.0, 1.0),
    )
    for _, row in top.iterrows():
        base_params = V2Params(**json.loads(str(row["params"])))
        for regime, atr_min, atr_max, asia_min, asia_max in regimes:
            for (
                label,
                mode,
                rr,
                partial,
                trigger,
                profit,
                trail_start,
                trail_distance,
            ) in management:
                params = replace(
                    base_params,
                    reversal_rr=rr,
                    continuation_rr=rr,
                    management_mode=mode,
                    partial_fraction=partial,
                    protect_trigger_r=trigger,
                    protect_profit_r=profit,
                    trail_start_r=trail_start,
                    trail_distance_r=trail_distance,
                )
                result.append(
                    Experiment(
                        f"{row['name']}__{regime}_{label}",
                        params,
                        atr_min,
                        atr_max,
                        asia_min,
                        asia_max,
                    )
                )
    return result


def _monthly(trades: list[Trade]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    buckets: dict[str, list[Trade]] = {}
    for trade in trades:
        month = pd.Timestamp(trade.entry_time).strftime("%Y-%m")
        buckets.setdefault(month, []).append(trade)
    for month, values in sorted(buckets.items()):
        result = metrics("XAUUSD..", values, 1000.0, 3.0)
        rows.append(
            {
                "month": month,
                "trades": result["trades"],
                "win_rate": result["win_rate_pct"],
                "pf": result["profit_factor"],
                "net_r": result["net_r"],
                "dd": result["max_drawdown_pct"],
            }
        )
    return pd.DataFrame(rows)


def _fmt(value: object) -> str:
    number = float(value)
    return "inf" if not math.isfinite(number) else f"{number:.2f}"


def run() -> None:
    base_config = load_config()
    frame = _frame(base_config.root)
    report_dir = base_config.root / "reports" / "amd_v2"
    report_dir.mkdir(parents=True, exist_ok=True)

    structural_rows: list[dict[str, object]] = []
    structural_experiments = _structural_experiments()
    print(
        f"Stage 1: {len(structural_experiments)} structural candidates",
        flush=True,
    )
    for index, experiment in enumerate(structural_experiments, 1):
        row, _ = _evaluate(
            frame,
            base_config,
            experiment,
            DEVELOPMENT_START,
            END,
            _development_folds(),
        )
        structural_rows.append(row)
        print(
            f"[{index:02d}/{len(structural_experiments):02d}] "
            f"{experiment.name}: {row['trades']} trades | "
            f"PF {_fmt(row['pf'])} | {float(row['net_r']):+.2f}R | "
            f"DD {float(row['dd']):.1f}% | "
            f"folds {row['positive_folds']}/4",
            flush=True,
        )
    structural = pd.DataFrame(structural_rows).sort_values(
        ["score", "pf"],
        ascending=False,
    )
    structural.to_csv(report_dir / "structural_search.csv", index=False)

    management_rows: list[dict[str, object]] = []
    management_experiments = _management_experiments(structural)
    print(
        f"\nStage 2: {len(management_experiments)} management/regime candidates",
        flush=True,
    )
    for index, experiment in enumerate(management_experiments, 1):
        row, _ = _evaluate(
            frame,
            base_config,
            experiment,
            DEVELOPMENT_START,
            END,
            _development_folds(),
        )
        management_rows.append(row)
        print(
            f"[{index:02d}/{len(management_experiments):02d}] "
            f"{experiment.name}: {row['trades']} trades | "
            f"PF {_fmt(row['pf'])} | {float(row['net_r']):+.2f}R | "
            f"DD {float(row['dd']):.1f}% | "
            f"folds {row['positive_folds']}/4",
            flush=True,
        )
    management_result = pd.DataFrame(management_rows).sort_values(
        ["score", "pf"],
        ascending=False,
    )
    management_result.to_csv(
        report_dir / "development_search.csv",
        index=False,
    )

    frozen_row = management_result.iloc[0]
    frozen = Experiment(
        str(frozen_row["name"]),
        V2Params(**json.loads(str(frozen_row["params"]))),
        float(frozen_row["atr_min"]),
        float(frozen_row["atr_max"]),
        float(frozen_row["asia_min"]),
        float(frozen_row["asia_max"]),
    )
    (report_dir / "frozen_model.json").write_text(
        json.dumps(
            {
                "name": frozen.name,
                "params": asdict(frozen.params),
                "atr_min": frozen.atr_min,
                "atr_max": frozen.atr_max,
                "asia_min": frozen.asia_min,
                "asia_max": frozen.asia_max,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    holdout_row, holdout_trades = _evaluate(
        frame,
        base_config,
        frozen,
        HOLDOUT_START,
        HOLDOUT_END,
        _all_folds()[:2],
    )
    full_row, full_trades = _evaluate(
        frame,
        base_config,
        frozen,
        HOLDOUT_START,
        END,
        _all_folds(),
    )
    pd.DataFrame([holdout_row]).to_csv(
        report_dir / "holdout_metrics.csv",
        index=False,
    )
    pd.DataFrame([full_row]).to_csv(
        report_dir / "full_metrics.csv",
        index=False,
    )
    pd.DataFrame([trade.to_dict() for trade in holdout_trades]).to_csv(
        report_dir / "holdout_trades.csv",
        index=False,
    )
    pd.DataFrame([trade.to_dict() for trade in full_trades]).to_csv(
        report_dir / "full_trades.csv",
        index=False,
    )
    _monthly(full_trades).to_csv(
        report_dir / "monthly.csv",
        index=False,
    )

    accepted = bool(
        int(frozen_row["trades"]) >= 40
        and int(frozen_row["positive_folds"]) == 4
        and float(frozen_row["pf"]) >= 1.25
        and float(frozen_row["dd"]) <= 20.0
        and int(holdout_row["trades"]) >= 15
        and float(holdout_row["pf"]) >= 1.10
        and float(holdout_row["net_r"]) > 0
        and float(holdout_row["dd"]) <= 20.0
        and int(full_row["positive_folds"]) >= 5
    )
    decision = {
        "accepted": accepted,
        "development": frozen_row.to_dict(),
        "holdout": holdout_row,
        "full": full_row,
    }
    (report_dir / "decision.json").write_text(
        json.dumps(decision, indent=2, default=str),
        encoding="utf-8",
    )
    report = [
        "# AMD v2 Robustness Report",
        "",
        f"Decision: **{'ACCEPTED' if accepted else 'REJECTED'}**",
        "",
        "The model was selected using only 2024-07-30 through 2026-07-30. "
        "Its parameters were frozen before the 2023-07-30 through "
        "2024-07-30 holdout was evaluated.",
        "",
        "| Sample | Trades | Win rate | PF | Net R | Return | Max DD |",
        "|---|---:|---:|---:|---:|---:|---:|",
        (
            f"| Development | {int(frozen_row['trades'])} | "
            f"{float(frozen_row['win_rate']):.2f}% | "
            f"{_fmt(frozen_row['pf'])} | "
            f"{float(frozen_row['net_r']):+.2f} | "
            f"{float(frozen_row['return']):+.2f}% | "
            f"{float(frozen_row['dd']):.2f}% |"
        ),
        (
            f"| Holdout | {int(holdout_row['trades'])} | "
            f"{float(holdout_row['win_rate']):.2f}% | "
            f"{_fmt(holdout_row['pf'])} | "
            f"{float(holdout_row['net_r']):+.2f} | "
            f"{float(holdout_row['return']):+.2f}% | "
            f"{float(holdout_row['dd']):.2f}% |"
        ),
        (
            f"| Full three years | {int(full_row['trades'])} | "
            f"{float(full_row['win_rate']):.2f}% | "
            f"{_fmt(full_row['pf'])} | "
            f"{float(full_row['net_r']):+.2f} | "
            f"{float(full_row['return']):+.2f}% | "
            f"{float(full_row['dd']):.2f}% |"
        ),
        "",
        "## Frozen model",
        "",
        "```json",
        json.dumps(
            {
                "name": frozen.name,
                "params": asdict(frozen.params),
                "atr_min": frozen.atr_min,
                "atr_max": frozen.atr_max,
                "asia_min": frozen.asia_min,
                "asia_max": frozen.asia_max,
            },
            indent=2,
        ),
        "```",
    ]
    (report_dir / "REPORT.md").write_text(
        "\n".join(report) + "\n",
        encoding="utf-8",
    )
    print("\nFROZEN MODEL")
    print(frozen.name)
    print(
        f"Development: {frozen_row['trades']} trades | "
        f"WR {float(frozen_row['win_rate']):.2f}% | "
        f"PF {_fmt(frozen_row['pf'])} | "
        f"{float(frozen_row['net_r']):+.2f}R | "
        f"DD {float(frozen_row['dd']):.2f}%"
    )
    print(
        f"Holdout: {holdout_row['trades']} trades | "
        f"WR {float(holdout_row['win_rate']):.2f}% | "
        f"PF {_fmt(holdout_row['pf'])} | "
        f"{float(holdout_row['net_r']):+.2f}R | "
        f"DD {float(holdout_row['dd']):.2f}%"
    )
    print(
        f"Full: {full_row['trades']} trades | "
        f"WR {float(full_row['win_rate']):.2f}% | "
        f"PF {_fmt(full_row['pf'])} | "
        f"{float(full_row['net_r']):+.2f}R | "
        f"DD {float(full_row['dd']):.2f}%"
    )
    print(f"Decision: {'ACCEPTED' if accepted else 'REJECTED'}")


if __name__ == "__main__":
    run()
