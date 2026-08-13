from __future__ import annotations

import csv
import importlib.util
import json
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
FINAL = ROOT / "Backtest Reports" / "Final"
PARSER_PATH = PACKAGE / "BAT Portfolio Backtest 2026-08-09" / "Build-BAT-Portfolio-Report.py"
INITIAL = 10_000.0
START = datetime(2025, 8, 11)
FINISH = datetime(2026, 8, 10)

spec = importlib.util.spec_from_file_location("mt5_report_parser", PARSER_PATH)
parser = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(parser)


def money(value: float) -> str:
    return f"-${abs(value):,.2f}" if value < 0 else f"${value:,.2f}"


def signed_pct(value: float) -> str:
    return f"{value:+.2f}%" if value else "0.00%"


def balance_curve(deals: list[dict]) -> list[tuple[datetime, float]]:
    balance = INITIAL
    points = [(START, balance)]
    for deal in sorted(deals, key=lambda item: item["time"]):
        balance += deal["cashflow"]
        points.append((deal["time"], balance))
    points.append((FINISH, balance))
    return points


def main() -> None:
    manifest = json.loads((FINAL / "manifest.json").read_text(encoding="utf-8-sig"))
    results = []
    curves: dict[str, list[tuple[datetime, float]]] = {}
    for case in manifest:
        parsed = parser.parse_report(
            FINAL / f"{case['Id']}.htm",
            {
                "id": case["Id"],
                "label": case["Label"],
                "symbol": case["Symbol"],
                "period": case["Period"],
                "chart": f"{case['Symbol']} {case['Period']}",
                "set_source": str(ROOT / "Sets" / f"BEST - {case['Id']}.set"),
            },
        )
        parsed["status"] = (
            "PASS" if parsed["return_pct"] >= 15 and parsed["profit_factor"] >= 1.1 and parsed["equity_dd_pct"] <= 20
            else "WATCH" if parsed["net"] > 0 and parsed["profit_factor"] > 1
            else "FAIL"
        )
        parsed["native_report"] = str(FINAL / f"{case['Id']}.htm")
        parsed["native_equity_graph"] = str(FINAL / f"{case['Id']}.png")
        curve = balance_curve(parsed["deals"])
        curves[case["Id"]] = curve
        with (FINAL / f"{case['Id']}-realized-balance.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["time", "balance"])
            writer.writerows((when.isoformat(sep=" "), f"{balance:.2f}") for when, balance in curve)
        results.append(parsed)

    fields = [
        "status", "label", "symbol", "timeframe", "initial", "final", "net", "return_pct",
        "equity_dd_amount", "equity_dd_pct", "balance_dd_amount", "balance_dd_pct", "profit_factor",
        "win_rate_pct", "wins", "losses", "trades", "gross_profit", "gross_loss", "largest_win",
        "largest_loss", "average_win", "average_loss", "expected_payoff", "recovery_factor", "sharpe",
        "history_quality", "set_source", "native_report", "native_equity_graph",
    ]
    with (FINAL / "final-summary.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    (FINAL / "final-results.json").write_text(
        json.dumps([{key: value for key, value in row.items() if key != "deals"} for row in results], indent=2),
        encoding="utf-8",
    )

    figure, axis = plt.subplots(figsize=(13, 6), dpi=180)
    for row in results:
        points = curves[row["id"]]
        axis.plot([point[0] for point in points], [point[1] for point in points], linewidth=1.3, label=row["label"])
    axis.axhline(INITIAL, color="gray", linestyle="--", linewidth=0.8)
    axis.set_title("Hybrid CVD — out-of-sample realized-balance comparison")
    axis.set_xlabel("Date")
    axis.set_ylabel("Balance (USD)")
    axis.grid(True, alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(FINAL / "comparison-realized-balance.png")
    plt.close(figure)

    lines = [
        "# Hybrid CVD EA — final research report",
        "",
        "## Honest outcome",
        "",
        "| Status | Market | Final | Net / return | Max equity DD | PF | Win rate | Wins / losses | Trades | Quality |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in results:
        lines.append(
            f"| {row['status']} | {row['symbol']} {row['timeframe']} | {money(row['final'])} | "
            f"{money(row['net'])} / {signed_pct(row['return_pct'])} | {money(row['equity_dd_amount'])} / "
            f"{row['equity_dd_pct']:.2f}% | {row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | "
            f"{row['wins']} / {row['losses']} | {row['trades']} | {row['history_quality']} |"
        )
    lines.extend([
        "",
        "## Test design",
        "",
        "- Broker: Exness `Exness-MT5Trial16`; independent USD 10,000 account simulation per market.",
        "- Training/selection: 2023-08-11 through 2025-08-10. The final choices required positive results in both one-year training halves.",
        "- Untouched final test: 2025-08-11 through 2026-08-10.",
        "- MT5 model: Every Tick generated from synchronized broker M1 history, random execution delay.",
        "- Risk: 1% of current equity per trade; one position at a time per chart and session trade limits.",
        "- XAU and US30 use M5 signals. US100 runs on an M5 chart but uses M15 signal bars internally.",
        "- The main BAT/install pipeline was not modified and this EA was not deployed live.",
        "",
        "## What Hybrid CVD means here",
        "",
        "The EA combines an intrabar tick-volume CVD proxy, session VWAP, relative volume, EMA structure, breakout or divergence context, "
        "ATR stops, R-multiple targets, break-even, and ATR trailing. Exness CFD history does not contain exchange aggressor-tagged "
        "buy/sell volume. Therefore this is not true futures CVD; it estimates pressure from M1 direction and close location weighted "
        "by broker tick volume.",
        "",
        "## Decision",
        "",
        "- US30 met the 15% research return gate, but its 24.59% equity drawdown is too high for the existing portfolio and the PF is only 1.15. Keep research-only.",
        "- US100 was slightly profitable but too weak to qualify.",
        "- XAU failed out of sample and should not be traded.",
        "- None of the three should be added to the main BAT at this stage.",
        "",
        "## Files",
        "",
        "- `Source/Hybrid CVD VWAP EA.mq5` and `.ex5`: source and compiled EA.",
        "- `Sets/BEST - *.set`: selected settings for reproducibility, not live approval.",
        "- `Backtest Reports/Final/*.htm`: native MT5 reports.",
        "- `Backtest Reports/Final/*.png`: native MT5 equity/balance graphs.",
        "- `Backtest Reports/Final/final-summary.csv` and `final-results.json`: extracted statistics.",
        "- `Backtest Reports/Final/comparison-realized-balance.png`: comparison of closed-deal balance curves.",
    ])
    (ROOT / "FINAL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    print(json.dumps([{key: value for key, value in row.items() if key in fields} for row in results], indent=2))


if __name__ == "__main__":
    main()
