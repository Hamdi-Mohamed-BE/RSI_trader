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
SELECTION_PATH = ROOT / "optimization-selection.json"

spec = importlib.util.spec_from_file_location("mt5_report_parser", PARSER_PATH)
parser_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(parser_module)

SYMBOLS = ("XAUUSD", "USTEC", "BTCUSD", "ETHUSD")
CASES = [
    (f"{symbol.lower()}-training", symbol, "Training", "2021-01-01", "2024-12-31", "1-minute OHLC")
    for symbol in SYMBOLS
] + [
    (f"{symbol.lower()}-locked-year", symbol, "Locked year", "2025-08-26", "2026-08-26", "Every Tick")
    for symbol in SYMBOLS
]


def parse_cases() -> list[dict]:
    results: list[dict] = []
    for slug, symbol, segment, start, end, model in CASES:
        path = REPORTS / f"{slug}.htm"
        case = {
            "id": slug,
            "label": f"{symbol} {segment}",
            "symbol": symbol,
            "period": "M15",
            "chart": f"{symbol} M15",
            "set_source": str(ROOT / "Sets" / f"SELECTED - {symbol} M15 - Top Down FVG Liquidity - 1pct.set"),
        }
        result = parser_module.parse_report(path, case)
        result.update(
            slug=slug,
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


def save_graph(results: list[dict]) -> Path:
    locked = {row["symbol"]: balance_frame(row) for row in results if row["segment"] == "Locked year"}
    colors = {"XAUUSD": "#ffd166", "USTEC": "#5fffd1", "BTCUSD": "#5da9ff", "ETHUSD": "#c792ff"}
    plt.style.use("dark_background")
    figure, (equity_axis, dd_axis) = plt.subplots(2, 1, figsize=(14, 8.5), gridspec_kw={"height_ratios": [2.5, 1.0], "hspace": 0.22})
    figure.patch.set_facecolor("#071311")
    for axis in (equity_axis, dd_axis):
        axis.set_facecolor("#0b1c19")
        axis.grid(True, color="#28453f", alpha=0.45, linewidth=0.7)
    for symbol, frame in locked.items():
        equity_axis.plot(frame.date, frame.balance, color=colors[symbol], linewidth=1.7, label=symbol)
        dd_axis.plot(frame.date, frame.drawdown, color=colors[symbol], linewidth=1.2, label=symbol)
    equity_axis.axhline(10_000, color="#9ab5ad", linestyle="--", linewidth=0.9)
    equity_axis.set_title("Locked latest-year MT5 Every Tick balance curves", loc="left", weight="bold")
    equity_axis.set_ylabel("Balance USD")
    equity_axis.legend(frameon=False, ncol=4, loc="upper left")
    dd_axis.axhline(0, color="#9ab5ad", linewidth=0.8)
    dd_axis.set_ylabel("Closed-balance DD")
    dd_axis.yaxis.set_major_formatter(lambda value, _: f"{value:.0f}%")
    dd_axis.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    dd_axis.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    figure.suptitle("Top-Down FVG Liquidity Proxy — $10,000 initial, 1% risk per trade", fontsize=16, weight="bold")
    path = ROOT / "Top Down FVG Liquidity - Locked Year Equity.png"
    figure.savefig(path, dpi=180, bbox_inches="tight", facecolor=figure.get_facecolor())
    plt.close(figure)
    return path


def main() -> None:
    results = parse_cases()
    public = [{key: value for key, value in row.items() if key != "deals"} for row in results]
    selection = {row["symbol"]: row for row in json.loads(SELECTION_PATH.read_text(encoding="utf-8"))}
    graph = save_graph(results)
    (ROOT / "native-results.json").write_text(json.dumps(public, indent=2), encoding="utf-8")
    fields = [
        "symbol", "segment", "from_date", "to_date", "model", "initial", "final", "net", "return_pct",
        "profit_factor", "win_rate_pct", "equity_dd_amount", "equity_dd_pct", "balance_dd_pct", "trades", "wins",
        "losses", "gross_profit", "gross_loss", "largest_win", "largest_loss", "average_win", "average_loss",
        "expected_payoff", "recovery_factor", "sharpe", "history_quality", "report_path", "chart_path",
    ]
    with (ROOT / "native-results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(public)

    lines = [
        "# Top-Down FVG Liquidity — native MT5 validation",
        "",
        "Research date: 2026-08-27",
        "",
        "## Scope warning",
        "",
        "This EA tests only a mechanical technical proxy. The transcript's macro, fundamental and crypto on-chain/order-book filters are not present in MT5 price history, so these results do not validate the speaker's full discretionary method.",
        "",
        "## Results",
        "",
        "| Symbol | Segment / model | Return | PF | Win rate | Equity DD | Trades | Quality |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in public:
        lines.append(
            f"| {row['symbol']} | {row['segment']} / {row['model']} | {row['return_pct']:+.2f}% | "
            f"{row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['equity_dd_pct']:.2f}% | "
            f"{row['trades']} | {row['history_quality']} |"
        )
    lines.extend(["", "## Selected parameters", "", "| Symbol | Bias | Sweep bars | Displacement | Retest bars | RR | Break-even |", "|---|---:|---:|---:|---:|---:|---:|"])
    for symbol in SYMBOLS:
        params = selection[symbol]["parameters"]
        lines.append(f"| {symbol} | {params['InpBiasMode']} | {params['InpSweepLookbackBars']} | {params['InpDisplacementBodyATR']} ATR | {params['InpRetestExpiryBars']} | {params['InpRewardRisk']}R | {params['InpBreakEvenAtR']}R |")
    lines.extend(
        [
            "",
            "## Mechanical rules tested",
            "",
            "1. H4 or H4+D1 EMA alignment is used as an objective proxy for the transcript's manually formed macro/fundamental bias.",
            "2. An M15 candle must sweep a prior rolling extreme and close back through the swept liquidity level.",
            "3. The next M15 candle must displace in the reversal direction by the configured ATR amount.",
            "4. The third candle must leave a true three-candle fair-value gap; entry waits for a midpoint retest.",
            "5. Stop loss is beyond the sweep extreme, the target is the selected fixed R multiple, and each trade risks 1% of current equity.",
            "",
            "## Controls",
            "",
            "- Per-symbol parameters were selected only on 2021-2024 1-minute-OHLC training history.",
            "- The latest year, 2025-08-26 through 2026-08-26, was then run once with MT5 Every Tick and random execution delay.",
            "- Native Exness symbol specifications, spread, commission and swap are included by the tester.",
            "- The active BAT and website were not changed.",
            "",
            f"Equity graph: {graph}",
        ]
    )
    (ROOT / "FULL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    print(json.dumps(public, indent=2))


if __name__ == "__main__":
    main()
