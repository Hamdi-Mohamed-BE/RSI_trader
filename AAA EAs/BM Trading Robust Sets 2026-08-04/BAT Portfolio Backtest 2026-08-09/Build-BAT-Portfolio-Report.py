from __future__ import annotations

import csv
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
BT = PACKAGE / "_Backtests" / "MT5-Isolated-20260805"
SOURCE_REPORTS = BT / "reports" / "bat-portfolio-20260809"
REPORTS = ROOT / "MT5 Reports"
CHARTS = ROOT / "Charts"
STARTING_BALANCE = 10_000.0
START_DATE = datetime(2025, 8, 7)
FINISH_DATE = datetime(2026, 8, 6)


def compact(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def number(value: str | None) -> float:
    match = re.search(r"[-+]?\d+(?:[,.]\d{3})*(?:\.\d+)?", compact(value or "").replace(" ", ""))
    return float(match.group(0).replace(",", "")) if match else 0.0


def percent(value: str | None) -> float:
    match = re.search(r"([-+]?\d+(?:\.\d+)?)%", compact(value or ""))
    return float(match.group(1)) if match else 0.0


def parse_report(path: Path, case: dict) -> dict:
    soup = BeautifulSoup(path.read_text(encoding="utf-16", errors="replace"), "html.parser")
    values: dict[str, str] = {}
    for row in soup.find_all("tr"):
        cells = [compact(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"], recursive=False)]
        for index, cell in enumerate(cells[:-1]):
            if cell.endswith(":"):
                values[cell[:-1]] = cells[index + 1]

    initial = number(values.get("Initial Deposit")) or STARTING_BALANCE
    net = number(values.get("Total Net Profit"))
    wins_text = values.get("Profit Trades (% of total)", "")
    losses_text = values.get("Loss Trades (% of total)", "")
    equity_dd = values.get("Equity Drawdown Maximal", "")
    balance_dd = values.get("Balance Drawdown Maximal", "")

    deals = []
    in_deals = False
    for row in soup.find_all("tr"):
        row_text = compact(row.get_text(" ", strip=True))
        if row_text == "Deals":
            in_deals = True
            continue
        if not in_deals:
            continue
        cells = [compact(cell.get_text(" ", strip=True)) for cell in row.find_all("td", recursive=False)]
        if len(cells) != 13 or not re.fullmatch(r"\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}", cells[0]):
            continue
        if cells[3].lower() == "balance":
            continue
        deals.append({
            "time": datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S"),
            "cashflow": number(cells[8]) + number(cells[9]) + number(cells[10]),
        })

    return {
        "id": case["id"],
        "label": case["label"],
        "symbol": case["symbol"],
        "timeframe": case["period"],
        "chart": case["chart"],
        "set_source": case["set_source"],
        "file": path.name,
        "stem": path.stem,
        "initial": initial,
        "final": initial + net,
        "net": net,
        "return_pct": net / initial * 100.0 if initial else 0.0,
        "equity_dd_amount": number(equity_dd),
        "equity_dd_pct": percent(equity_dd),
        "balance_dd_amount": number(balance_dd),
        "balance_dd_pct": percent(balance_dd),
        "profit_factor": number(values.get("Profit Factor")),
        "trades": int(number(values.get("Total Trades"))),
        "wins": int(number(wins_text)),
        "losses": int(number(losses_text)),
        "win_rate_pct": percent(wins_text),
        "expected_payoff": number(values.get("Expected Payoff")),
        "recovery_factor": number(values.get("Recovery Factor")),
        "sharpe": number(values.get("Sharpe Ratio")),
        "gross_profit": number(values.get("Gross Profit")),
        "gross_loss": number(values.get("Gross Loss")),
        "largest_win": number(values.get("Largest profit trade")),
        "largest_loss": number(values.get("Largest loss trade")),
        "average_win": number(values.get("Average profit trade")),
        "average_loss": number(values.get("Average loss trade")),
        "history_quality": values.get("History Quality", ""),
        "deals": deals,
    }


def max_drawdown(events: list[dict]) -> tuple[float, float]:
    balance = STARTING_BALANCE
    peak = balance
    worst_amount = 0.0
    worst_pct = 0.0
    for event in events:
        balance += event["cashflow"]
        if balance > peak:
            peak = balance
        amount = peak - balance
        pct = amount / peak * 100.0 if peak else 0.0
        if pct > worst_pct:
            worst_amount, worst_pct = amount, pct
    return worst_amount, worst_pct


def status(row: dict) -> str:
    if row["return_pct"] >= 20.0 and row["profit_factor"] >= 1.10 and row["equity_dd_pct"] <= 20.0:
        return "PASS"
    if row["net"] > 0.0 and row["profit_factor"] > 1.0:
        return "WATCH"
    return "FAIL"


def money(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def pct(value: float) -> str:
    return f"{value:+.2f}%" if value != 0 else "0.00%"


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    CHARTS.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    results = []
    for case in manifest:
        source = Path(case["report"])
        if not source.exists():
            raise FileNotFoundError(source)
        row = parse_report(source, case)
        row["status"] = status(row)
        results.append(row)
        for artifact in SOURCE_REPORTS.glob(f"{case['id']}*"):
            if artifact.is_file():
                shutil.copy2(artifact, REPORTS / artifact.name)

    events = []
    for order, row in enumerate(results):
        for deal in row["deals"]:
            events.append({**deal, "order": order, "bot": row["label"]})
    events.sort(key=lambda item: (item["time"], item["order"]))
    combined_balance = STARTING_BALANCE
    combined_series = [(START_DATE, combined_balance)]
    for event in events:
        combined_balance += event["cashflow"]
        combined_series.append((event["time"], combined_balance))
    combined_net = sum(row["net"] for row in results)
    combined_balance = STARTING_BALANCE + combined_net
    combined_series.append((FINISH_DATE, combined_balance))
    combined_dd_amount, combined_dd_pct = max_drawdown(events)
    gross_profit = sum(row["gross_profit"] for row in results)
    gross_loss = sum(row["gross_loss"] for row in results)
    total_trades = sum(row["trades"] for row in results)
    total_wins = sum(row["wins"] for row in results)
    combined_pf = gross_profit / abs(gross_loss) if gross_loss else 0.0
    combined = {
        "initial": STARTING_BALANCE,
        "final": combined_balance,
        "net": combined_net,
        "return_pct": combined_net / STARTING_BALANCE * 100.0,
        "realized_dd_amount": combined_dd_amount,
        "realized_dd_pct": combined_dd_pct,
        "profit_factor": combined_pf,
        "trades": total_trades,
        "wins": total_wins,
        "win_rate_pct": total_wins / total_trades * 100.0 if total_trades else 0.0,
    }

    export_rows = [{key: value for key, value in row.items() if key != "deals"} for row in results]
    (ROOT / "portfolio-data.json").write_text(
        json.dumps({"combined": combined, "bots": export_rows}, indent=2), encoding="utf-8"
    )
    fields = [
        "status", "label", "chart", "initial", "final", "net", "return_pct", "equity_dd_amount",
        "equity_dd_pct", "balance_dd_amount", "balance_dd_pct", "profit_factor", "win_rate_pct", "wins",
        "losses", "trades", "gross_profit", "gross_loss", "largest_win", "largest_loss", "average_win",
        "average_loss", "expected_payoff", "recovery_factor", "sharpe", "history_quality", "set_source",
    ]
    with (ROOT / "portfolio-summary.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(export_rows)
    with (ROOT / "combined-realized-balance.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle); writer.writerow(["time", "balance"])
        writer.writerows((when.isoformat(sep=" "), f"{balance:.2f}") for when, balance in combined_series)

    figure, axis = plt.subplots(figsize=(12, 5.5), dpi=160)
    axis.plot([point[0] for point in combined_series], [point[1] for point in combined_series], linewidth=1.5)
    axis.axhline(STARTING_BALANCE, linestyle="--", linewidth=0.9, color="gray")
    axis.set_title("13-EA BAT portfolio — combined realized cash-flow aggregation")
    axis.set_xlabel("Date"); axis.set_ylabel("Balance (USD)"); axis.grid(True, alpha=0.25)
    figure.tight_layout(); figure.savefig(CHARTS / "combined-realized-balance.png"); plt.close(figure)

    lines = [
        "# Synchronized BAT portfolio — complete one-year Exness backtest",
        "",
        "## Method",
        "",
        "- Source of truth: `_Auto Deploy/Install-BMTradingPortfolio.ps1` (13 currently deployed EAs)",
        "- Broker: Exness `Exness-MT5Trial16`",
        "- Period: 2025-08-07 through 2026-08-06 (latest complete 12-month window available in the synchronized local Exness history)",
        "- Initial balance: USD 10,000 for each independent EA test",
        "- Risk: the exact 1%/USD 100 configuration referenced by the AUTO BAT",
        "- Model: MT5 Every Tick generated from broker history, random execution delay, leverage 1:2000",
        "- Execution evidence: native MT5 reports generated 7 Aug 2026; on 9 Aug every input was compared with the current BAT reference and all 13 matched. A same-day rerun was attempted but Exness weekend synchronization did not authorize the isolated tester.",
        "- PASS gate used for labeling only: return >=20%, PF >=1.10, equity DD <=20%",
        "",
        "## Individual results",
        "",
        "| Status | EA | Symbol / TF | Final | Net / return | Max equity DD | PF | Win rate | Trades |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in results:
        lines.append(
            f"| {row['status']} | {row['label']} | {row['chart']} | {money(row['final'])} | "
            f"{money(row['net'])} / {pct(row['return_pct'])} | {money(row['equity_dd_amount'])} / "
            f"{row['equity_dd_pct']:.2f}% | {row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['trades']:,} |"
        )
    lines.extend([
        "",
        "## Combined realized cash-flow aggregation",
        "",
        f"- Initial balance: {money(combined['initial'])}",
        f"- Final balance: {money(combined['final'])}",
        f"- Net result: {money(combined['net'])} ({pct(combined['return_pct'])})",
        f"- Realized-balance max drawdown: {money(combined['realized_dd_amount'])} ({combined['realized_dd_pct']:.2f}%)",
        f"- Aggregated PF: {combined['profit_factor']:.2f}",
        f"- Trades: {combined['trades']:,}; wins: {combined['wins']:,} ({combined['win_rate_pct']:.2f}%)",
        "",
        "![Combined realized balance](Charts/combined-realized-balance.png)",
        "",
        "## Important portfolio limitation",
        "",
        "The combined curve merges closed-deal cash flows from 13 separate $10,000 MT5 tests. It is not an exact shared-margin simulation: each percentage-risk EA sized from its standalone balance, and overlapping floating P/L is unavailable. Consequently, live shared-account equity drawdown can be materially worse. With 13 EAs each allowed roughly 1% risk, simultaneous exposure can approach 13% before correlations, slippage, or gaps.",
        "",
        "## Native reports and graphs",
        "",
    ])
    for row in results:
        lines.extend([
            f"### {row['label']} — {row['chart']}", "",
            f"- Net: {money(row['net'])} ({pct(row['return_pct'])}); equity DD: {row['equity_dd_pct']:.2f}%; PF: {row['profit_factor']:.2f}",
            f"- Trades: {row['trades']:,}; wins/losses: {row['wins']:,}/{row['losses']:,}; average win/loss: {money(row['average_win'])}/{money(row['average_loss'])}",
            f"- [Native MT5 report](MT5 Reports/{row['file']})", "",
            f"![{row['label']} graph](MT5 Reports/{row['stem']}.png)", "",
        ])
    (ROOT / "FULL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"combined": combined, "bots": export_rows}, indent=2))


if __name__ == "__main__":
    main()
