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
    ("selected-training-2020-2023", "Screen-selected", "Training", "2020-01-01", "2023-12-31", "1-minute OHLC"),
    ("selected-validation-2024-2025h1", "Screen-selected", "Validation", "2024-01-01", "2025-06-30", "1-minute OHLC"),
    ("selected-locked-every-tick", "Screen-selected", "Locked", "2025-07-01", "2026-08-25", "Every Tick"),
    ("selected-one-year-every-tick", "Screen-selected", "Latest year", "2025-08-26", "2026-08-25", "Every Tick"),
    ("selected-full-2020-2026", "Screen-selected", "Full", "2020-01-01", "2026-08-25", "1-minute OHLC"),
    ("literal-training-2020-2023", "Literal transcript", "Training", "2020-01-01", "2023-12-31", "1-minute OHLC"),
    ("literal-validation-2024-2025h1", "Literal transcript", "Validation", "2024-01-01", "2025-06-30", "1-minute OHLC"),
    ("literal-locked-every-tick", "Literal transcript", "Locked", "2025-07-01", "2026-08-25", "Every Tick"),
    ("literal-one-year-every-tick", "Literal transcript", "Latest year", "2025-08-26", "2026-08-25", "Every Tick"),
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
            "period": "M5",
            "chart": "USTEC M5",
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
        3, 1, figsize=(14, 10), gridspec_kw={"height_ratios": [2.3, 2.0, 0.9], "hspace": 0.24}
    )
    figure.patch.set_facecolor("#071311")
    for axis in (full_axis, year_axis, dd_axis):
        axis.set_facecolor("#0b1c19")
        axis.grid(True, color="#28453f", alpha=0.45, linewidth=0.7)

    full_axis.plot(full.date, full.balance, color="#5fffd1", linewidth=1.8)
    full_axis.axhline(10_000, color="#9ab5ad", linestyle="--", linewidth=0.9)
    full_axis.set_title("Screen-selected VWAP bounce — full native MT5 history", loc="left", weight="bold")
    full_axis.set_ylabel("Balance USD")
    full_axis.xaxis.set_major_locator(mdates.YearLocator())
    full_axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    year_axis.plot(selected_year.date, selected_year.balance, color="#5fffd1", linewidth=1.8, label="Selected ORB15 / EMA / 2R")
    year_axis.plot(literal_year.date, literal_year.balance, color="#ffd166", linewidth=1.6, label="Literal ORB30 / extreme target")
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

    figure.suptitle("US100 New York VWAP Bounce — $10,000 initial, 1% equity risk per trade", fontsize=16, weight="bold")
    figure.savefig(ROOT / "US100 NY VWAP Bounce - Native Equity Comparison.png", dpi=180, bbox_inches="tight", facecolor=figure.get_facecolor())
    plt.close(figure)


def main() -> None:
    results = parse_cases()
    public = [{key: value for key, value in row.items() if key != "deals"} for row in results]
    (ROOT / "native-results.json").write_text(json.dumps(public, indent=2), encoding="utf-8")
    with (ROOT / "native-results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        fields = [
            "strategy", "segment", "from_date", "to_date", "model", "initial", "final", "net", "return_pct",
            "profit_factor", "win_rate_pct", "equity_dd_amount", "equity_dd_pct", "balance_dd_pct", "trades",
            "wins", "losses", "gross_profit", "gross_loss", "largest_win", "largest_loss", "average_win",
            "average_loss", "expected_payoff", "recovery_factor", "sharpe", "history_quality", "report_path", "chart_path",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(public)
    save_graph(results)

    selected_year = next(row for row in public if row["slug"] == "selected-one-year-every-tick")
    literal_year = next(row for row in public if row["slug"] == "literal-one-year-every-tick")
    verdict = (
        "PASS FOR FORWARD TEST ONLY" if selected_year["profit_factor"] >= 1.20 and selected_year["return_pct"] > 0
        else "REJECT FOR THE ACTIVE BAT"
    )
    lines = [
        "# US100 New York VWAP Bounce — native MT5 validation",
        "",
        "Research date: 2026-08-26",
        "",
        "## Verdict",
        "",
        f"**{verdict}.** The literal transcript and the training-selected variant are shown separately below. Selection used training and validation only; the latest year was not used to tune the parameters.",
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
            "## Exact versions",
            "",
            "- Literal transcript: 30-minute ORB; price must first extend beyond the ORB, then make its first VWAP pullback; directional rejection candle; rejection-candle stop; target the prior extension extreme.",
            "- Screen-selected: 15-minute ORB; first VWAP pullback; open and close stay on the trend side of VWAP; EMA20/EMA50 trend filter; stop at 0.25 times the median prior 20 New York-session ranges; 2R target.",
            "- Both: New York VWAP anchored at 09:30; 90-minute setup window; one trade per session; flat at 15:55 New York; automatic US DST; 1% equity risk.",
            "",
            "## Test controls",
            "",
            "- Exness USTEC, $10,000 initial balance, 1:2000 leverage.",
            "- Native MT5 commission, swap and spread are included; random execution delay is enabled.",
            "- Same-session signals are evaluated only after a candle closes; entries occur on the following tick.",
            "- The Python screen charged an extra 2.0 US100 points round-trip and resolved ambiguous stop/target bars stop-first.",
            "",
            "## Volume limitation",
            "",
            "Exness USTEC exposes broker tick activity, not centralized Nasdaq futures exchange volume. Its anchored VWAP is therefore a CFD tick-activity proxy. True CME volume validation would require NQ futures data.",
            "",
            "## Deployment decision",
            "",
            "The active BAT, active presets and website were not changed by this research run.",
        ]
    )
    (ROOT / "FULL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    print(json.dumps(public, indent=2))


if __name__ == "__main__":
    main()
