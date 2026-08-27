from __future__ import annotations

import csv
import importlib.util
import json
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
    ("selected-training-2020-2023", "Screen-selected ORB15", "Training", "2020-01-01", "2023-12-31", "1-minute OHLC"),
    ("selected-validation-2024-2025h1", "Screen-selected ORB15", "Validation", "2024-01-01", "2025-06-30", "1-minute OHLC"),
    ("selected-locked-every-tick", "Screen-selected ORB15", "Locked", "2025-07-01", "2026-08-25", "Every Tick"),
    ("selected-one-year-every-tick", "Screen-selected ORB15", "Latest year", "2025-08-26", "2026-08-25", "Every Tick"),
    ("selected-full-2020-2026", "Screen-selected ORB15", "Full", "2020-01-01", "2026-08-25", "1-minute OHLC"),
    ("literal-training-2020-2023", "Literal ORB30", "Training", "2020-01-01", "2023-12-31", "1-minute OHLC"),
    ("literal-validation-2024-2025h1", "Literal ORB30", "Validation", "2024-01-01", "2025-06-30", "1-minute OHLC"),
    ("literal-locked-every-tick", "Literal ORB30", "Locked", "2025-07-01", "2026-08-25", "Every Tick"),
    ("literal-one-year-every-tick", "Literal ORB30", "Latest year", "2025-08-26", "2026-08-25", "Every Tick"),
    ("literal-full-2020-2026", "Literal ORB30", "Full", "2020-01-01", "2026-08-25", "1-minute OHLC"),
]


def parse_cases() -> list[dict]:
    results = []
    for slug, strategy, segment, start, end, model in CASES:
        path = REPORTS / f"{slug}.htm"
        case = {"id": slug, "label": f"{strategy} {segment}", "symbol": "USTEC", "period": "M5", "chart": "USTEC M5", "set_source": ""}
        result = parser_module.parse_report(path, case)
        result.update(
            slug=slug,
            strategy=strategy,
            segment=segment,
            from_date=start,
            to_date=end,
            model=model,
            report_path=str(path),
            chart_path=str(REPORTS / f"{slug}.png"),
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
    literal_full = balance_frame(by_slug["literal-full-2020-2026"])
    selected_full = balance_frame(by_slug["selected-full-2020-2026"])
    literal_year = balance_frame(by_slug["literal-one-year-every-tick"])
    selected_year = balance_frame(by_slug["selected-one-year-every-tick"])

    plt.style.use("dark_background")
    figure, (full_axis, year_axis, dd_axis) = plt.subplots(
        3, 1, figsize=(14, 10), gridspec_kw={"height_ratios": [2.3, 2.0, 0.9], "hspace": 0.24}
    )
    figure.patch.set_facecolor("#071311")
    for axis in (full_axis, year_axis, dd_axis):
        axis.set_facecolor("#0b1c19")
        axis.grid(True, color="#28453f", alpha=0.45, linewidth=0.7)

    full_axis.plot(literal_full.date, literal_full.balance, color="#ffd166", linewidth=1.7, label="Literal ORB30 / 1R")
    full_axis.plot(selected_full.date, selected_full.balance, color="#5fffd1", linewidth=1.6, label="Selected ORB15 / 1.5R")
    full_axis.axhline(10_000, color="#9ab5ad", linestyle="--", linewidth=0.9)
    full_axis.set_title("Full native MT5 history — direct long-only ORB", loc="left", weight="bold")
    full_axis.set_ylabel("Balance USD")
    full_axis.legend(frameon=False, loc="upper left")
    full_axis.xaxis.set_major_locator(mdates.YearLocator())
    full_axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    year_axis.plot(literal_year.date, literal_year.balance, color="#ffd166", linewidth=1.8, label="Literal ORB30 / 1R")
    year_axis.plot(selected_year.date, selected_year.balance, color="#5fffd1", linewidth=1.7, label="Selected ORB15 / 1.5R")
    year_axis.axhline(10_000, color="#9ab5ad", linestyle="--", linewidth=0.9)
    year_axis.set_title("Latest year — MT5 Every Tick, random execution delay", loc="left", weight="bold")
    year_axis.set_ylabel("Balance USD")
    year_axis.legend(frameon=False, loc="upper left")
    year_axis.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    year_axis.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    dd_axis.fill_between(literal_full.date, literal_full.drawdown, 0, color="#ff6b6b", alpha=0.65)
    dd_axis.plot(literal_full.date, literal_full.drawdown, color="#ff8a8a", linewidth=0.8)
    dd_axis.set_ylabel("Literal DD")
    dd_axis.yaxis.set_major_formatter(lambda value, _: f"{value:.0f}%")
    dd_axis.xaxis.set_major_locator(mdates.YearLocator())
    dd_axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    figure.suptitle("US100 Fabio ORB — $10,000 initial, 1% volatility-targeted risk", fontsize=16, weight="bold")
    figure.savefig(ROOT / "US100 Fabio ORB - Native Equity Comparison.png", dpi=180, bbox_inches="tight", facecolor=figure.get_facecolor())
    plt.close(figure)


def main() -> None:
    results = parse_cases()
    public = [{key: value for key, value in row.items() if key != "deals"} for row in results]
    (ROOT / "native-results.json").write_text(json.dumps(public, indent=2), encoding="utf-8")
    fields = [
        "strategy", "segment", "from_date", "to_date", "model", "initial", "final", "net", "return_pct",
        "profit_factor", "win_rate_pct", "equity_dd_amount", "equity_dd_pct", "balance_dd_pct", "trades", "wins",
        "losses", "gross_profit", "gross_loss", "largest_win", "largest_loss", "average_win", "average_loss",
        "expected_payoff", "recovery_factor", "sharpe", "history_quality", "report_path", "chart_path",
    ]
    with (ROOT / "native-results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(public)
    save_graph(results)

    literal_locked = next(row for row in public if row["slug"] == "literal-locked-every-tick")
    literal_year = next(row for row in public if row["slug"] == "literal-one-year-every-tick")
    literal_train = next(row for row in public if row["slug"] == "literal-training-2020-2023")
    literal_valid = next(row for row in public if row["slug"] == "literal-validation-2024-2025h1")
    passes = (
        literal_train["profit_factor"] >= 1.05
        and literal_valid["profit_factor"] >= 1.05
        and literal_locked["profit_factor"] >= 1.10
        and literal_year["return_pct"] > 0
        and literal_year["equity_dd_pct"] <= 15.0
    )
    verdict = "PASS FOR CONTROLLED FORWARD TEST" if passes else "RESEARCH-ONLY; DO NOT DEPLOY YET"
    lines = [
        "# US100 Fabio ORB with volatility-targeted sizing — native MT5 validation",
        "",
        "Research date: 2026-08-26",
        "",
        "## Verdict",
        "",
        f"**{verdict}.** The literal transcript version and a training-selected derivative are reported separately. The selected derivative was chosen without looking at locked data.",
        "",
        "## Native MT5 results",
        "",
        "| Version | Segment / model | Return | PF | Win rate | Equity DD | Trades | Quality |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in public:
        lines.append(
            f"| {row['strategy']} | {row['segment']} / {row['model']} | {row['return_pct']:+.2f}% | "
            f"{row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['equity_dd_pct']:.2f}% | "
            f"{row['trades']} | {row['history_quality']} |"
        )
    lines.extend(
        [
            "",
            "## Exact rules",
            "",
            "- Literal: use the 09:30–10:00 New York range; after a completed M5 candle closes above its high, enter long on the next tick; stop at the ORB low; target 1R; close at 15:00 New York; one trade per day.",
            "- Selected derivative: use the first 15 minutes; require a bullish breakout close before 10:30; stop at the ORB low; target 1.5R; close at 15:00 New York.",
            "- Both size the position from the actual entry-to-stop distance so each trade risks 1% of current equity.",
            "- No delta filter is used. Exness USTEC cannot provide CME aggressive buy/sell delta.",
            "",
            "## Test controls",
            "",
            "- Exness USTEC, $10,000 initial balance, 1:2000 leverage.",
            "- Native spread, commissions and swaps are reflected in MT5; random execution delay is enabled.",
            "- Training: 2020–2023. Validation: 2024–June 2025. Locked: July 2025–August 2026. Latest-year and locked runs use 100% MT5 Every Tick modeling.",
            "- Available Exness history begins in 2020, so the video’s claim that the edge weakened before 2019 could not be independently tested here.",
            "",
            "## Deployment",
            "",
            "The active BAT, active presets, installed EAs and website were not changed by this isolated validation.",
        ]
    )
    (ROOT / "FULL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    print(json.dumps(public, indent=2))


if __name__ == "__main__":
    main()
