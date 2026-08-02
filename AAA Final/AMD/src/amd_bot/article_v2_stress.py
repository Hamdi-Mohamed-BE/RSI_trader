from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from .article_v2_engine import V2Params, backtest_v2_model
from .article_v2_research import Experiment, _config, _evaluate, _frame
from .config import load_config
from .engine import Trade, metrics


UTC = timezone.utc
DEVELOPMENT_START = datetime(2024, 7, 30, tzinfo=UTC)
DEVELOPMENT_END = datetime(2026, 7, 30, tzinfo=UTC)
OLDER_START = datetime(2020, 7, 30, tzinfo=UTC)
OLDER_END = datetime(2023, 7, 30, tzinfo=UTC)


def _slice(
    trades: list[Trade],
    start: datetime,
    end: datetime,
) -> list[Trade]:
    return [
        trade
        for trade in trades
        if pd.Timestamp(start)
        <= pd.Timestamp(trade.entry_time)
        < pd.Timestamp(end)
    ]


def _compact(name: str, sample: str, result: dict[str, object]) -> dict:
    return {
        "name": name,
        "sample": sample,
        "trades": result["trades"],
        "win_rate": result["win_rate_pct"],
        "pf": result["profit_factor"],
        "net_r": result["net_r"],
        "return": result["return_pct"],
        "dd": result["max_drawdown_pct"],
    }


def _format_pf(value: object) -> str:
    number = float(value)
    return "inf" if number == float("inf") else f"{number:.2f}"


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    report_dir = root / "reports" / "amd_v2"
    frozen = json.loads((report_dir / "frozen_model.json").read_text())
    params = V2Params(**frozen["params"])
    base_config = load_config()
    experiment = Experiment(
        "frozen_london",
        params,
        atr_min=float(frozen["atr_min"]),
        atr_max=float(frozen["atr_max"]),
        asia_min=float(frozen["asia_min"]),
        asia_max=float(frozen["asia_max"]),
    )
    config = _config(base_config, experiment)

    older_path = root / "data" / "XAUUSD___20200620_20230730_M1.csv.gz"
    if not older_path.exists():
        raise FileNotFoundError(
            f"Older broker-history cache is missing: {older_path}"
        )
    older = pd.read_csv(older_path)
    older["time"] = pd.to_datetime(older["time"], utc=True)
    older_trades = backtest_v2_model(
        older,
        "XAUUSD..",
        0.01,
        config,
        params,
        OLDER_START,
        OLDER_END,
    )

    older_rows = [
        _compact(
            experiment.name,
            "2020-07-30_to_2023-07-30",
            metrics("XAUUSD..", older_trades, 1000.0, 3.0),
        )
    ]
    for year in (2020, 2021, 2022):
        start = datetime(year, 7, 30, tzinfo=UTC)
        end = datetime(year + 1, 7, 30, tzinfo=UTC)
        older_rows.append(
            _compact(
                experiment.name,
                f"{year}-07-30_to_{year + 1}-07-30",
                metrics(
                    "XAUUSD..",
                    _slice(older_trades, start, end),
                    1000.0,
                    3.0,
                ),
            )
        )

    development = _frame(root)
    all_history = (
        pd.concat((older, development), ignore_index=True)
        .drop_duplicates("time")
        .sort_values("time")
        .reset_index(drop=True)
    )
    all_history_trades = backtest_v2_model(
        all_history,
        "XAUUSD..",
        0.01,
        config,
        params,
        OLDER_START,
        DEVELOPMENT_END,
    )
    six_year = _compact(
        experiment.name,
        "2020-07-30_to_2026-07-30",
        metrics("XAUUSD..", all_history_trades, 1000.0, 3.0),
    )
    folds = (
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
    variants = (
        ("London only", params),
        (
            "New York only",
            replace(params, trade_london=False, trade_new_york=True),
        ),
        (
            "London + New York, max 1/day",
            replace(params, trade_new_york=True, max_trades_per_day=1),
        ),
        (
            "London + New York, max 2/day",
            replace(params, trade_new_york=True, max_trades_per_day=2),
        ),
    )
    session_rows: list[dict] = []
    for name, variant_params in variants:
        row, _ = _evaluate(
            development,
            base_config,
            replace(experiment, name=name, params=variant_params),
            DEVELOPMENT_START,
            DEVELOPMENT_END,
            folds,
        )
        session_rows.append(
            {
                "name": name,
                "sample": "2024-07-30_to_2026-07-30",
                "trades": row["trades"],
                "win_rate": row["win_rate"],
                "pf": row["pf"],
                "net_r": row["net_r"],
                "return": row["return"],
                "dd": row["dd"],
                "positive_folds": row["positive_folds"],
            }
        )

    pd.DataFrame(older_rows).to_csv(
        report_dir / "older_stress_metrics.csv",
        index=False,
    )
    pd.DataFrame(session_rows).to_csv(
        report_dir / "session_extension_metrics.csv",
        index=False,
    )
    pd.DataFrame((six_year,)).to_csv(
        report_dir / "six_year_metrics.csv",
        index=False,
    )

    older_total = older_rows[0]
    london = session_rows[0]
    both_one = session_rows[2]
    lines = [
        "# AMD v2 Extended Stress Test",
        "",
        "The v2 parameters were frozen before these extra checks.",
        "",
        "## Older broker history",
        "",
        "| Sample | Trades | Win rate | PF | Net R | Return | Max DD |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in older_rows:
        lines.append(
            f"| {row['sample']} | {row['trades']} | "
            f"{float(row['win_rate']):.2f}% | {_format_pf(row['pf'])} | "
            f"{float(row['net_r']):+.2f} | {float(row['return']):+.2f}% | "
            f"{float(row['dd']):.2f}% |"
        )
    lines.extend(
        [
            "",
            "The frozen model is positive over the older three-year aggregate, "
            "but the 2022-2023 regime loses money and exceeds the preferred "
            "15% drawdown ceiling.",
            "",
            "## Session-extension check",
            "",
            "| Variant | Trades | Win rate | PF | Net R | Return | Max DD | "
            "Positive folds |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in session_rows:
        lines.append(
            f"| {row['name']} | {row['trades']} | "
            f"{float(row['win_rate']):.2f}% | {_format_pf(row['pf'])} | "
            f"{float(row['net_r']):+.2f} | {float(row['return']):+.2f}% | "
            f"{float(row['dd']):.2f}% | {row['positive_folds']}/4 |"
        )
    lines.extend(
        [
            "",
            "New York adds frequency but weakens stability. The max-one "
            f"two-session variant raises trades from {london['trades']} to "
            f"{both_one['trades']}, while PF falls from "
            f"{float(london['pf']):.2f} to {float(both_one['pf']):.2f}, "
            f"drawdown rises from {float(london['dd']):.2f}% to "
            f"{float(both_one['dd']):.2f}%, and positive folds fall from "
            f"{london['positive_folds']}/4 to {both_one['positive_folds']}/4.",
            "",
            "## Combined six-year result",
            "",
            "| Trades | Win rate | PF | Net R | Return | Max DD |",
            "|---:|---:|---:|---:|---:|---:|",
            f"| {six_year['trades']} | {float(six_year['win_rate']):.2f}% | "
            f"{_format_pf(six_year['pf'])} | "
            f"{float(six_year['net_r']):+.2f} | "
            f"{float(six_year['return']):+.2f}% | "
            f"{float(six_year['dd']):.2f}% |",
            "",
            "## Decision",
            "",
            "**REJECTED FOR LIVE TRADING.** The v2 reversal is materially "
            "better than the original model, but its sample remains small and "
            f"the older stress sample includes a losing regime "
            f"(aggregate PF {_format_pf(older_total['pf'])}, max DD "
            f"{float(older_total['dd']):.2f}%). Keep it paper-only.",
        ]
    )
    (report_dir / "EXTENDED_STRESS.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
