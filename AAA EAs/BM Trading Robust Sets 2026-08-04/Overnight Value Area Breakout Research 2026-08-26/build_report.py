from __future__ import annotations

import csv
import importlib.util
import json
from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
REPORTS = ROOT / "Backtest Reports"
PARSER_PATH = PACKAGE / "BAT Portfolio Backtest 2026-08-09" / "Build-BAT-Portfolio-Report.py"

spec = importlib.util.spec_from_file_location("mt5_report_parser", PARSER_PATH)
parser_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(parser_module)

CASES = [
    ("selected-training-2020-2023", "Developed", "Training", "2020-01-01", "2023-12-31", "1-minute OHLC"),
    ("selected-validation-2024-2025h1", "Developed", "Validation", "2024-01-01", "2025-06-30", "1-minute OHLC"),
    ("selected-locked-real-ticks", "Developed", "Locked", "2025-07-01", "2026-08-25", "real ticks"),
    ("selected-one-year-real-ticks", "Developed", "One year", "2025-08-26", "2026-08-25", "real ticks"),
    ("selected-one-year-every-tick", "Developed", "One year", "2025-08-26", "2026-08-25", "Every Tick"),
    ("selected-full-2020-2026", "Developed", "Full", "2020-01-01", "2026-08-25", "1-minute OHLC"),
    ("literal-training-2020-2023", "Literal", "Training", "2020-01-01", "2023-12-31", "1-minute OHLC"),
    ("literal-validation-2024-2025h1", "Literal", "Validation", "2024-01-01", "2025-06-30", "1-minute OHLC"),
    ("literal-one-year-real-ticks", "Literal", "One year", "2025-08-26", "2026-08-25", "real ticks"),
    ("literal-one-year-every-tick", "Literal", "One year", "2025-08-26", "2026-08-25", "Every Tick"),
]


def parse_cases() -> list[dict]:
    results = []
    for slug, strategy, segment, start, end, model in CASES:
        path = REPORTS / f"{slug}.htm"
        if not path.is_file():
            raise FileNotFoundError(path)
        case = {
            "id": slug,
            "label": f"{strategy} {segment}",
            "symbol": "USTEC",
            "period": "M15",
            "chart": "USTEC M15",
            "set_source": "",
        }
        result = parser_module.parse_report(path, case)
        result.update(
            {
                "slug": slug,
                "strategy": strategy,
                "segment": segment,
                "from_date": start,
                "to_date": end,
                "model": model,
                "report_path": str(path),
                "chart_path": str(REPORTS / f"{slug}.png"),
            }
        )
        results.append(result)
    return results


def balance_frame(result: dict) -> pd.DataFrame:
    balance = result["initial"]
    rows = [{"date": pd.Timestamp(result["from_date"]), "balance": balance}]
    for deal in sorted(result["deals"], key=lambda item: item["time"]):
        balance += deal["cashflow"]
        rows.append({"date": pd.Timestamp(deal["time"]), "balance": balance})
    rows.append({"date": pd.Timestamp(result["to_date"]), "balance": balance})
    frame = pd.DataFrame(rows).sort_values("date")
    frame["peak"] = frame.balance.cummax()
    frame["drawdown"] = (frame.balance / frame.peak - 1.0) * 100.0
    return frame


def save_graph(results: list[dict]) -> None:
    by_slug = {row["slug"]: row for row in results}
    full = balance_frame(by_slug["selected-full-2020-2026"])
    selected_year = balance_frame(by_slug["selected-one-year-every-tick"])
    literal_year = balance_frame(by_slug["literal-one-year-every-tick"])

    plt.style.use("dark_background")
    figure, (full_axis, year_axis, dd_axis) = plt.subplots(
        3,
        1,
        figsize=(14, 10),
        gridspec_kw={"height_ratios": [2.4, 2.0, 0.9], "hspace": 0.22},
    )
    figure.patch.set_facecolor("#071311")
    for axis in (full_axis, year_axis, dd_axis):
        axis.set_facecolor("#0b1c19")
        axis.grid(True, color="#28453f", alpha=0.45, linewidth=0.7)

    full_axis.plot(full.date, full.balance, color="#5fffd1", linewidth=1.8)
    full_axis.axhline(10_000, color="#9ab5ad", linestyle="--", linewidth=0.9)
    full_axis.set_title(
        "Developed overnight VA retest — full native MT5 history (1-minute OHLC)",
        loc="left",
        weight="bold",
    )
    full_axis.set_ylabel("Balance USD")
    full_axis.xaxis.set_major_locator(mdates.YearLocator())
    full_axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    year_axis.plot(selected_year.date, selected_year.balance, color="#5fffd1", linewidth=1.8, label="Developed retest")
    year_axis.plot(literal_year.date, literal_year.balance, color="#ffd166", linewidth=1.5, label="Literal viral rule")
    year_axis.axhline(10_000, color="#9ab5ad", linestyle="--", linewidth=0.9)
    year_axis.set_title("Latest year — MT5 Every Tick, random execution delay", loc="left", weight="bold")
    year_axis.set_ylabel("Balance USD")
    year_axis.legend(frameon=False, loc="upper left")
    year_axis.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    year_axis.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    dd_axis.fill_between(full.date, full.drawdown, 0, color="#ff6b6b", alpha=0.65)
    dd_axis.plot(full.date, full.drawdown, color="#ff8a8a", linewidth=0.8)
    dd_axis.set_ylabel("Full DD")
    dd_axis.yaxis.set_major_formatter(lambda value, _: f"{value:.0f}%")
    dd_axis.xaxis.set_major_locator(mdates.YearLocator())
    dd_axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    figure.suptitle(
        "US100 Overnight Value Area Breakout — $10,000 initial, 1% risk per trade",
        fontsize=16,
        weight="bold",
    )
    figure.savefig(ROOT / "US100 Overnight VA - Native Equity Comparison.png", dpi=180, bbox_inches="tight", facecolor=figure.get_facecolor())
    plt.close(figure)


def money(value: float) -> str:
    return f"-${abs(value):,.2f}" if value < 0 else f"${value:,.2f}"


def main() -> None:
    results = parse_cases()
    public_results = [{key: value for key, value in row.items() if key != "deals"} for row in results]
    (REPORTS / "manifest.json").write_text(
        json.dumps(
            [
                {
                    "slug": row["slug"],
                    "strategy": row["strategy"],
                    "segment": row["segment"],
                    "from_date": row["from_date"],
                    "to_date": row["to_date"],
                    "model": row["model"],
                    "status": "complete",
                    "report": row["report_path"],
                }
                for row in public_results
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    (ROOT / "native-results.json").write_text(json.dumps(public_results, indent=2), encoding="utf-8")
    with (ROOT / "native-results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        fields = [
            "strategy", "segment", "from_date", "to_date", "model", "initial", "final", "net", "return_pct",
            "profit_factor", "win_rate_pct", "equity_dd_amount", "equity_dd_pct", "balance_dd_pct", "trades",
            "wins", "losses", "gross_profit", "gross_loss", "largest_win", "largest_loss", "average_win",
            "average_loss", "expected_payoff", "recovery_factor", "sharpe", "history_quality", "report_path", "chart_path",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(public_results)
    save_graph(results)

    lines = [
        "# US100 Overnight Value Area Breakout — validation report",
        "",
        "Research date: 2026-08-26",
        "",
        "## Verdict",
        "",
        "The literal viral rule is rejected for deployment. Its high win rate hides negative expectancy in the older training and validation periods. The developed retest version is positive in every native segment, but the edge is too small for the active BAT: latest-year PF is only 1.09 and return is about 2% at 1% risk per trade.",
        "",
        "## Native MT5 results",
        "",
        "| Version | Segment / model | Return | PF | Win rate | Equity DD | Trades | Quality |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in results:
        lines.append(
            f"| {row['strategy']} | {row['segment']} / {row['model']} | {row['return_pct']:+.2f}% | "
            f"{row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['equity_dd_pct']:.2f}% | "
            f"{row['trades']} | {row['history_quality']} |"
        )
    lines.extend(
        [
            "",
            "## Versions",
            "",
            "- Literal: overnight VA from 16:30 to 09:30 New York; the first 09:30 M15 candle must close outside VAH/VAL; direct market entry; signal-candle stop; 0.5R target.",
            "- Developed: wait up to four M15 bars after 09:30 for a directional close outside VAH/VAL; require a directional candle; enter only after a VAH/VAL retest; stop one median prior-RTH range away; 1.5R target; close at 15:55 New York.",
            "- Both use 70% value area, one trade per day, automatic New York DST conversion and 1% equity risk.",
            "",
            "## Data limitation",
            "",
            "The Exness USTEC CFD has broker tick activity, not centralized Nasdaq futures exchange volume or true bid/ask CVD. The recent real-tick reports contain only 56–64% real-tick history quality. The corresponding 100% MT5 Every Tick checks are therefore the primary one-year comparison.",
            "",
            "## Decision",
            "",
            "Do not add either version to the active BAT. Keep the developed EA as research/watch-only until it produces a stronger PF and return in an additional untouched period or is tested against paid CME futures volume.",
            "",
            "The active installer, active SET files and website portfolio were not changed.",
        ]
    )
    (ROOT / "FULL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    print(json.dumps(public_results, indent=2))


if __name__ == "__main__":
    main()
