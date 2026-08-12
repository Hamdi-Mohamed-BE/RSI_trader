from __future__ import annotations

import csv
import importlib.util
import json
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
REPORTS = ROOT / "MT5 Reports"
CHARTS = ROOT / "Charts"
MANIFEST = ROOT / "manifest.json"
PARSER_PATH = PACKAGE / "BAT Portfolio Backtest 2026-08-09" / "Build-BAT-Portfolio-Report.py"
STARTING_BALANCE = 10_000.0
START_DATE = datetime(2025, 8, 11)
FINISH_DATE = datetime(2026, 8, 10)

spec = importlib.util.spec_from_file_location("bat_parser", PARSER_PATH)
bat_parser = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(bat_parser)


def money(value: float) -> str:
    return f"-${abs(value):,.2f}" if value < 0 else f"${value:,.2f}"


def signed_pct(value: float) -> str:
    return f"{value:+.2f}%" if value else "0.00%"


def max_drawdown(series: list[tuple[datetime, float]]) -> tuple[float, float]:
    peak = series[0][1]
    worst_amount = 0.0
    worst_pct = 0.0
    for _, balance in series:
        peak = max(peak, balance)
        amount = peak - balance
        pct = amount / peak * 100.0 if peak else 0.0
        if pct > worst_pct:
            worst_amount, worst_pct = amount, pct
    return worst_amount, worst_pct


def main() -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    results = []
    invalid = []
    for case in manifest:
        report = REPORTS / f"{case['id']}.htm"
        parsed = bat_parser.parse_report(report, {**case, "set_source": case["set_source"]})
        if case["id"] == "09-ninja-turtle-scalper" and parsed["trades"] == 0 and parsed["history_quality"] == "n/a":
            invalid.append({**case, "reason": "OnInit failed: embedded Donchian Channel resource could not be loaded (MT5 error 4802)."})
            continue
        parsed["status"] = "PROFIT" if parsed["net"] > 0 else ("LOSS" if parsed["net"] < 0 else "FLAT")
        parsed["report_path"] = str(report)
        parsed["chart_path"] = str(REPORTS / f"{case['id']}.png")
        results.append(parsed)

    events = []
    for order, result in enumerate(results):
        for deal in result["deals"]:
            events.append({**deal, "order": order, "bot": result["label"]})
    events.sort(key=lambda item: (item["time"], item["order"]))
    combined_balance = STARTING_BALANCE
    combined_series = [(START_DATE, combined_balance)]
    for event in events:
        combined_balance += event["cashflow"]
        combined_series.append((event["time"], combined_balance))
    combined_series.append((FINISH_DATE, combined_balance))
    dd_amount, dd_pct = max_drawdown(combined_series)
    gross_profit = sum(result["gross_profit"] for result in results)
    gross_loss = sum(result["gross_loss"] for result in results)
    trades = sum(result["trades"] for result in results)
    wins = sum(result["wins"] for result in results)
    losses = sum(result["losses"] for result in results)
    combined = {
        "tested_eas": len(results),
        "invalid_eas": len(invalid),
        "initial": STARTING_BALANCE,
        "final": combined_balance,
        "net": combined_balance - STARTING_BALANCE,
        "return_pct": (combined_balance / STARTING_BALANCE - 1.0) * 100.0,
        "realized_balance_dd_amount": dd_amount,
        "realized_balance_dd_pct": dd_pct,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": gross_profit / abs(gross_loss) if gross_loss else 0.0,
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": wins / trades * 100.0 if trades else 0.0,
    }

    with (ROOT / "individual-results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        fields = [
            "status", "label", "chart", "initial", "final", "net", "return_pct", "equity_dd_amount",
            "equity_dd_pct", "balance_dd_amount", "balance_dd_pct", "profit_factor", "win_rate_pct",
            "wins", "losses", "trades", "gross_profit", "gross_loss", "largest_win", "largest_loss",
            "average_win", "average_loss", "expected_payoff", "recovery_factor", "sharpe", "history_quality",
            "set_source", "report_path", "chart_path",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows([{k: v for k, v in result.items() if k != "deals"} for result in results])
    with (ROOT / "combined-realized-balance.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time", "balance"])
        writer.writerows((when.isoformat(sep=" "), f"{balance:.2f}") for when, balance in combined_series)
    (ROOT / "portfolio-results.json").write_text(
        json.dumps({
            "combined": combined,
            "bots": [{k: v for k, v in result.items() if k != "deals"} for result in results],
            "invalid": invalid,
        }, indent=2), encoding="utf-8",
    )

    figure, axis = plt.subplots(figsize=(13, 6), dpi=170)
    axis.plot([point[0] for point in combined_series], [point[1] for point in combined_series], linewidth=1.35)
    axis.axhline(STARTING_BALANCE, linestyle="--", color="gray", linewidth=0.9)
    axis.set_title("Current active BAT — combined realized-balance overlay")
    axis.set_xlabel("Date")
    axis.set_ylabel("Balance (USD)")
    axis.grid(True, alpha=0.25)
    figure.tight_layout()
    figure.savefig(CHARTS / "combined-realized-balance.png")
    plt.close(figure)

    sorted_results = sorted(results, key=lambda item: item["return_pct"], reverse=True)
    lines = [
        "# Current active BAT — complete one-year Exness backtest",
        "",
        "## Combined result",
        "",
        "| Initial | Final | Net / return | Realized balance DD | PF | Win rate | Wins / losses | Trades |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| {money(combined['initial'])} | {money(combined['final'])} | {money(combined['net'])} / {signed_pct(combined['return_pct'])} | "
        f"{money(combined['realized_balance_dd_amount'])} / {combined['realized_balance_dd_pct']:.2f}% | {combined['profit_factor']:.2f} | "
        f"{combined['win_rate_pct']:.2f}% | {combined['wins']} / {combined['losses']} | {combined['trades']} |",
        "",
        "The combined line chronologically merges all realized deal cash flows onto one USD 10,000 balance. It is a useful "
        "capital-normalized overlay, but it is not a native multi-EA MT5 run: MT5 cannot attach these proprietary EX5 files "
        "simultaneously in one Strategy Tester pass. Floating equity DD, shared-equity position resizing, simultaneous margin use, "
        "and cross-EA execution contention are therefore not captured. The reported combined DD is realized-balance DD and can "
        "understate live floating-equity drawdown.",
        "",
        "## One-by-one results",
        "",
        "| Status | EA | Symbol / TF | Final | Net / return | Equity DD | PF | Win rate | Trades | Quality |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in sorted_results:
        lines.append(
            f"| {result['status']} | {result['label']} | {result['chart']} | {money(result['final'])} | "
            f"{money(result['net'])} / {signed_pct(result['return_pct'])} | {money(result['equity_dd_amount'])} / "
            f"{result['equity_dd_pct']:.2f}% | {result['profit_factor']:.2f} | {result['win_rate_pct']:.2f}% | "
            f"{result['trades']} | {result['history_quality']} |"
        )
    lines.extend([
        "",
        "## Invalid active BAT entry",
        "",
    ])
    for item in invalid:
        lines.append(f"- **{item['label']} ({item['symbol']} {item['period']}): START FAILURE.** {item['reason']}")
    lines.extend([
        "",
        "## Test conditions",
        "",
        "- Source of truth: current `_Auto Deploy/Install-BMTradingPortfolio.ps1` invoked by `INSTALL AND RUN ON ACTIVE MT5.bat`.",
        "- Broker: Exness `Exness-MT5Trial16`; account currency USD.",
        "- Period: 2025-08-11 through 2026-08-10, the latest complete one-year window.",
        "- Initial balance: USD 10,000 per independent EA test; leverage 1:2000.",
        "- Model: MT5 Every Tick generated from synchronized broker M1 history; reported quality 99–100% for valid tests.",
        "- Execution: random execution delay.",
        "- Settings: exact current BAT source presets, including the current long-only robust News Pulse set.",
        "- Planned risk: approximately 1% per EA trade. Because every EA has its own allowance, aggregate open risk can exceed 1% "
        "when bots hold positions simultaneously.",
        "",
        "## Files",
        "",
        "- `MT5 Reports`: native report and equity-chart artifacts for every test.",
        "- `individual-results.csv`: all one-by-one statistics.",
        "- `combined-realized-balance.csv`: chronological combined cash-flow curve.",
        "- `portfolio-results.json`: machine-readable full result.",
        "- `Charts/combined-realized-balance.png`: combined graph.",
    ])
    (ROOT / "FULL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    print(json.dumps(combined, indent=2))


if __name__ == "__main__":
    main()
