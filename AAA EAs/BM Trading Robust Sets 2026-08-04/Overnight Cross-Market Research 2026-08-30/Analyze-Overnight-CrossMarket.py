from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
from bs4 import BeautifulSoup


MARKETS = {
    "ustec": ("USTEC", "Index control"),
    "us500": ("US500", "Index"),
    "us30": ("US30", "Index"),
    "nvda": ("NVDA", "Stock"),
    "tsla": ("TSLA", "Stock"),
    "aapl": ("AAPL", "Stock"),
    "msft": ("MSFT", "Stock"),
    "amzn": ("AMZN", "Stock"),
    "googl": ("GOOGL", "Stock"),
    "meta": ("META", "Stock"),
    "avgo": ("AVGO", "Stock"),
    "amd": ("AMD", "Stock"),
    "intc": ("INTC", "Stock"),
    "jpm": ("JPM", "Stock"),
    "nflx": ("NFLX", "Stock"),
}


def compact(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def number(value: str | None) -> float:
    match = re.search(r"[-+]?\d+(?:[,.]\d{3})*(?:\.\d+)?", compact(value or "").replace(" ", ""))
    return float(match.group(0).replace(",", "")) if match else 0.0


def percent(value: str | None) -> float:
    match = re.search(r"([-+]?\d+(?:\.\d+)?)%", compact(value or ""))
    return float(match.group(1)) if match else 0.0


def read_report(path: Path) -> BeautifulSoup:
    raw = path.read_bytes()
    for encoding in ("utf-16", "utf-8-sig", "utf-8", "cp1252"):
        try:
            return BeautifulSoup(raw.decode(encoding), "html.parser")
        except (UnicodeDecodeError, UnicodeError):
            continue
    return BeautifulSoup(raw.decode("utf-8", errors="replace"), "html.parser")


def parse_report(path: Path) -> dict:
    soup = read_report(path)
    values: dict[str, str] = {}
    for row in soup.find_all("tr"):
        cells = [compact(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"], recursive=False)]
        for index, cell in enumerate(cells[:-1]):
            if cell.endswith(":"):
                values[cell[:-1]] = cells[index + 1]

    deals = []
    inside_deals = False
    for row in soup.find_all("tr"):
        if compact(row.get_text(" ", strip=True)) == "Deals":
            inside_deals = True
            continue
        if not inside_deals:
            continue
        cells = [compact(cell.get_text(" ", strip=True)) for cell in row.find_all("td", recursive=False)]
        if len(cells) != 13:
            continue
        if not re.fullmatch(r"\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}", cells[0]):
            continue
        if cells[3].lower() == "balance":
            continue
        commission = number(cells[8])
        swap = number(cells[9])
        profit = number(cells[10])
        deals.append(
            {
                "time": datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S"),
                "commission": commission,
                "swap": swap,
                "profit": profit,
                "cashflow": commission + swap + profit,
            }
        )

    initial = number(values.get("Initial Deposit")) or 10000.0
    net = number(values.get("Total Net Profit"))
    wins = values.get("Profit Trades (% of total)", "")
    losses = values.get("Loss Trades (% of total)", "")
    equity_dd = values.get("Equity Drawdown Maximal", "")
    balance_dd = values.get("Balance Drawdown Maximal", "")
    return {
        "report": str(path),
        "initial": initial,
        "final": initial + net,
        "net": net,
        "return_pct": net / initial * 100.0,
        "profit_factor": number(values.get("Profit Factor")),
        "win_rate_pct": percent(wins),
        "wins": int(number(wins)),
        "losses": int(number(losses)),
        "trades": int(number(values.get("Total Trades"))),
        "equity_dd_amount": number(equity_dd),
        "equity_dd_pct": percent(equity_dd),
        "balance_dd_amount": number(balance_dd),
        "balance_dd_pct": percent(balance_dd),
        "gross_profit": number(values.get("Gross Profit")),
        "gross_loss": number(values.get("Gross Loss")),
        "largest_win": number(values.get("Largest profit trade")),
        "largest_loss": number(values.get("Largest loss trade")),
        "average_win": number(values.get("Average profit trade")),
        "average_loss": number(values.get("Average loss trade")),
        "expected_payoff": number(values.get("Expected Payoff")),
        "recovery_factor": number(values.get("Recovery Factor")),
        "sharpe": number(values.get("Sharpe Ratio")),
        "history_quality": values.get("History Quality", ""),
        "commission": sum(item["commission"] for item in deals),
        "swap": sum(item["swap"] for item in deals),
        "deals": deals,
    }


def load_phase(directory: Path, phase: str) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for path in directory.glob(f"*--{phase}.htm"):
        match = re.fullmatch(rf"([a-z0-9]+)--{phase}\.htm", path.name, re.I)
        if match and match.group(1).lower() in MARKETS:
            found[match.group(1).lower()] = parse_report(path)
    missing = [slug for slug in MARKETS if slug not in found]
    if missing:
        raise RuntimeError(f"Missing {phase} MT5 reports: {', '.join(missing)}")
    return found


def verdict(development: dict, locked: dict) -> str:
    if (
        development["return_pct"] > 0
        and development["profit_factor"] >= 1.10
        and development["trades"] >= 30
        and locked["return_pct"] >= 5
        and locked["profit_factor"] >= 1.20
        and locked["equity_dd_pct"] <= 15
        and locked["trades"] >= 30
    ):
        return "KEEP CANDIDATE"
    if (
        development["return_pct"] > 0
        and development["profit_factor"] > 1
        and locked["return_pct"] > 0
        and locked["profit_factor"] > 1
        and locked["trades"] >= 15
    ):
        return "WATCH"
    return "REJECT"


def chart_style(axis) -> None:
    axis.set_facecolor("#0b1714")
    axis.tick_params(colors="#9eb1ac")
    axis.grid(color="#31443f", alpha=0.35, linewidth=0.6)
    for spine in axis.spines.values():
        spine.set_color("#31443f")


def balance_series(row: dict) -> tuple[list[datetime], list[float]]:
    balance = row["initial"]
    times: list[datetime] = []
    values: list[float] = []
    for deal in row["deals"]:
        balance += deal["cashflow"]
        times.append(deal["time"])
        values.append(balance)
    return times, values


def plot_curve(row: dict, path: Path, title: str) -> None:
    times, values = balance_series(row)
    figure, axis = plt.subplots(figsize=(10.4, 4.3), dpi=175)
    figure.patch.set_facecolor("#07110f")
    chart_style(axis)
    if times:
        axis.plot(times, values, color="#67f5c3", linewidth=1.8)
    else:
        axis.axhline(row["initial"], color="#67f5c3")
    axis.axhline(row["initial"], color="#9eb1ac", linewidth=0.8, linestyle="--")
    axis.set_title(title, color="white", fontsize=13, pad=12)
    axis.set_ylabel("Realized balance (USD)", color="#c9d8d4")
    figure.tight_layout()
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)


def plot_locked_returns(rows: list[dict], path: Path) -> None:
    ordered = sorted(rows, key=lambda row: row["locked_return_pct"])
    colors = ["#67f5c3" if row["locked_return_pct"] >= 0 else "#ff6b6b" for row in ordered]
    figure, axis = plt.subplots(figsize=(11.5, 7.2), dpi=175)
    figure.patch.set_facecolor("#07110f")
    chart_style(axis)
    axis.barh([row["market"] for row in ordered], [row["locked_return_pct"] for row in ordered], color=colors)
    axis.axvline(0, color="#9eb1ac", linewidth=0.9)
    axis.set_title("Overnight negative-day rule — locked one-year return", color="white", fontsize=14, pad=12)
    axis.set_xlabel("Return on $10,000 at 1% risk (%)", color="#c9d8d4")
    figure.tight_layout()
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)


def plot_development_vs_locked(rows: list[dict], path: Path) -> None:
    ordered = sorted(rows, key=lambda row: row["locked_return_pct"], reverse=True)
    labels = [row["market"] for row in ordered]
    positions = list(range(len(labels)))
    width = 0.38
    figure, axis = plt.subplots(figsize=(13.2, 6.3), dpi=175)
    figure.patch.set_facecolor("#07110f")
    chart_style(axis)
    axis.bar([x - width / 2 for x in positions], [row["development_return_pct"] for row in ordered], width, label="Development", color="#6bc9ff")
    axis.bar([x + width / 2 for x in positions], [row["locked_return_pct"] for row in ordered], width, label="Locked", color="#67f5c3")
    axis.axhline(0, color="#9eb1ac", linewidth=0.9)
    axis.set_xticks(positions)
    axis.set_xticklabels(labels, rotation=45, ha="right")
    axis.set_ylabel("Return (%)", color="#c9d8d4")
    axis.set_title("Development versus untouched locked year", color="white", fontsize=14, pad=12)
    legend = axis.legend(facecolor="#0b1714", edgecolor="#31443f")
    for text in legend.get_texts():
        text.set_color("white")
    figure.tight_layout()
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)


def plot_equal_weight(details: list[dict], path: Path) -> tuple[float, float]:
    events = []
    for item in details:
        row = item["locked"]
        for deal in row["deals"]:
            events.append((deal["time"], deal["cashflow"] / row["initial"] * 100.0))
    events.sort(key=lambda item: item[0])
    times: list[datetime] = []
    curve: list[float] = []
    value = 0.0
    peak = 0.0
    max_dd = 0.0
    divisor = max(1, len(details))
    for when, change in events:
        value += change / divisor
        peak = max(peak, value)
        max_dd = max(max_dd, peak - value)
        times.append(when)
        curve.append(value)
    figure, axis = plt.subplots(figsize=(11.5, 5.2), dpi=175)
    figure.patch.set_facecolor("#07110f")
    chart_style(axis)
    if times:
        axis.plot(times, curve, color="#67f5c3", linewidth=1.8)
    axis.axhline(0, color="#9eb1ac", linewidth=0.9, linestyle="--")
    axis.set_title("Equal-weight 15-market locked overlay", color="white", fontsize=14, pad=12)
    axis.set_ylabel("Average return (%)", color="#c9d8d4")
    figure.tight_layout()
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)
    return value, max_dd


def clean_metrics(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "deals"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--development", type=Path, required=True)
    parser.add_argument("--locked", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    development = load_phase(args.development, "development")
    locked = load_phase(args.locked, "locked")
    charts = args.output / "Charts"
    charts.mkdir(parents=True, exist_ok=True)

    details = []
    rows = []
    for slug, (market, group) in MARKETS.items():
        dev = development[slug]
        test = locked[slug]
        status = verdict(dev, test)
        plot_curve(test, charts / f"{slug}-locked-equity.png", f"{market} — overnight rule — locked 2025-08-29 to 2026-08-28")
        details.append({"slug": slug, "market": market, "group": group, "development": dev, "locked": test, "verdict": status})
        rows.append(
            {
                "verdict": status,
                "market": market,
                "group": group,
                "development_return_pct": dev["return_pct"],
                "development_pf": dev["profit_factor"],
                "development_win_rate_pct": dev["win_rate_pct"],
                "development_equity_dd_pct": dev["equity_dd_pct"],
                "development_trades": dev["trades"],
                "locked_return_pct": test["return_pct"],
                "locked_pf": test["profit_factor"],
                "locked_win_rate_pct": test["win_rate_pct"],
                "locked_equity_dd_pct": test["equity_dd_pct"],
                "locked_trades": test["trades"],
                "locked_final": test["final"],
                "locked_net": test["net"],
                "locked_gross_profit": test["gross_profit"],
                "locked_gross_loss": test["gross_loss"],
                "locked_commission": test["commission"],
                "locked_swap": test["swap"],
                "locked_largest_win": test["largest_win"],
                "locked_largest_loss": test["largest_loss"],
                "locked_average_win": test["average_win"],
                "locked_average_loss": test["average_loss"],
                "locked_expected_payoff": test["expected_payoff"],
                "locked_recovery_factor": test["recovery_factor"],
                "locked_sharpe": test["sharpe"],
                "history_quality": test["history_quality"],
                "locked_report": test["report"],
            }
        )

    rows.sort(key=lambda row: row["locked_return_pct"], reverse=True)
    plot_locked_returns(rows, charts / "all-markets-locked-return.png")
    plot_development_vs_locked(rows, charts / "development-vs-locked-return.png")
    combined_return, combined_max_dd = plot_equal_weight(details, charts / "all-markets-equal-weight-equity.png")

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "RESULTS.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    with (args.output / "RESULTS.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    profitable_both = sum(
        row["development_return_pct"] > 0
        and row["development_pf"] > 1
        and row["locked_return_pct"] > 0
        and row["locked_pf"] > 1
        for row in rows
    )
    keep_count = sum(row["verdict"] == "KEEP CANDIDATE" for row in rows)
    lines = [
        "# Nasdaq overnight rule — cross-market MT5 audit",
        "",
        "The original Nasdaq Overnight Negative Day logic was transferred without optimization. A broker-session probe was used to avoid market-closed orders: indices enter at 16:00 New York in summer and 15:59 in winter; stocks enter at 15:44 in summer and 14:44 in winter. Only data completed before the entry minute is used.",
        "",
        "## Results",
        "",
        "| Verdict | Market | Type | Dev return | Dev PF | Locked return | Locked PF | Win rate | Equity DD | Trades | Final |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['verdict']} | {row['market']} | {row['group']} | {row['development_return_pct']:+.2f}% | "
            f"{row['development_pf']:.2f} | {row['locked_return_pct']:+.2f}% | {row['locked_pf']:.2f} | "
            f"{row['locked_win_rate_pct']:.2f}% | {row['locked_equity_dd_pct']:.2f}% | {row['locked_trades']} | "
            f"${row['locked_final']:,.2f} |"
        )
    lines += [
        "",
        "## Honest decision",
        "",
        f"- Strict keep candidates: {keep_count}/{len(rows)}.",
        f"- Profitable with PF above 1 in both periods: {profitable_both}/{len(rows)}.",
        f"- Equal-weight locked overlay return: {combined_return:+.2f}%.",
        f"- Equal-weight realized drawdown from the overlay: {combined_max_dd:.2f} percentage points.",
        "- Development: 2024-08-29 to 2025-08-28.",
        "- Untouched locked test: 2025-08-29 to 2026-08-28.",
        "- $10,000 initial balance per market; 1% risk per entry; Exness MT5 Every Tick; random execution delay; broker spread, commission and swap included.",
        "- Index execution: 16:00 New York in DST months and 15:59 in standard-time months, then exit at 09:29 the following session; 2% emergency stop; Friday entries allowed.",
        "- Stock execution: 15:44 New York in DST months and 14:44 in standard-time months, immediately before Exness's 19:45 UTC stock CFD close; the exit remains 09:29 New York.",
        "- These one-minute/session adaptations avoid known market-closed rejections. They are broker compatibility fixes, not performance optimization.",
        "- The 300-M1-bar cash-session completeness check and DST/time handling remain enabled.",
        "- These are separate single-market MT5 tests. The equal-weight curve is a cash-flow overlay, not a simultaneous shared-margin portfolio simulation.",
        "- No active installation BAT or website file was changed.",
    ]
    (args.output / "FULL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
