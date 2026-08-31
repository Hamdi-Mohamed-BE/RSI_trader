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

SYMBOLS = {
    "btcusd": ("BTCUSD", "Crypto"),
    "xauusd": ("XAUUSD", "Metal"),
    "us500": ("US500", "Index"),
    "ustec": ("USTEC", "Index"),
    "eurusd": ("EURUSD", "Forex"),
    "gbpusd": ("GBPUSD", "Forex"),
    "usdjpy": ("USDJPY", "Forex"),
    "audusd": ("AUDUSD", "Forex"),
    "usdcad": ("USDCAD", "Forex"),
    "usdchf": ("USDCHF", "Forex"),
    "nzdusd": ("NZDUSD", "Forex"),
}
VARIANTS = ("h1-core", "h1-daily-bias", "h4-core", "h4-daily-bias")


def compact(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def number(value: str | None) -> float:
    match = re.search(r"[-+]?\d+(?:[,.]\d{3})*(?:\.\d+)?", compact(value or "").replace(" ", ""))
    return float(match.group(0).replace(",", "")) if match else 0.0


def percent(value: str | None) -> float:
    match = re.search(r"([-+]?\d+(?:\.\d+)?)%", compact(value or ""))
    return float(match.group(1)) if match else 0.0


def parse_report(path: Path) -> dict:
    soup = BeautifulSoup(path.read_text(encoding="utf-16", errors="replace"), "html.parser")
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
        if len(cells) != 13 or not re.fullmatch(r"\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}", cells[0]) or cells[3].lower() == "balance":
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
    equity_dd = values.get("Equity Drawdown Maximal", "")
    balance_dd = values.get("Balance Drawdown Maximal", "")
    wins = values.get("Profit Trades (% of total)", "")
    losses = values.get("Loss Trades (% of total)", "")
    return {
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


def identify(path: Path, phase: str) -> tuple[str, str]:
    match = re.match(rf"^({'|'.join(SYMBOLS)})--(.+)--{phase}\.htm$", path.name, re.I)
    if not match:
        raise ValueError(path.name)
    return match.group(1).lower(), match.group(2)


def score(row: dict) -> float:
    if row["trades"] < 10 or row["profit_factor"] <= 0:
        return -1000.0 + row["trades"]
    sample_penalty = max(0, 30 - row["trades"]) * 0.15
    return row["return_pct"] + 10.0 * (row["profit_factor"] - 1.0) - 0.45 * row["equity_dd_pct"] - sample_penalty


def load_phase(directory: Path, phase: str) -> dict[tuple[str, str], dict]:
    rows = {}
    for path in directory.glob("*.htm"):
        try:
            symbol, variant = identify(path, phase)
        except ValueError:
            continue
        rows[(symbol, variant)] = parse_report(path)
    return rows


def choose_universal(args: argparse.Namespace) -> None:
    rows = load_phase(args.development, "development")
    variants = {}
    for variant in VARIANTS:
        candidates = [rows[(symbol, variant)] for symbol in SYMBOLS if (symbol, variant) in rows]
        if len(candidates) != len(SYMBOLS):
            raise RuntimeError(f"Incomplete development reports for {variant}: {len(candidates)}")
        returns = [row["return_pct"] for row in candidates]
        factors = [row["profit_factor"] for row in candidates]
        drawdowns = [row["equity_dd_pct"] for row in candidates]
        scores = [score(row) for row in candidates]
        profitable = sum(row["return_pct"] > 0 and row["profit_factor"] > 1 for row in candidates)
        aggregate = statistics.median(scores) + 0.8 * profitable - 0.25 * (len(candidates) - profitable)
        variants[variant] = {
            "aggregate_score": aggregate,
            "median_return_pct": statistics.median(returns),
            "median_pf": statistics.median(factors),
            "median_dd_pct": statistics.median(drawdowns),
            "profitable_markets": profitable,
            "market_count": len(candidates),
        }
    winner = max(variants, key=lambda name: variants[name]["aggregate_score"])
    args.output.write_text(json.dumps({"winner": winner, "variants": variants}, indent=2), encoding="utf-8")


def chart_style(axis) -> None:
    axis.set_facecolor("#0b1714")
    axis.tick_params(colors="#9eb1ac")
    axis.grid(color="#31443f", alpha=0.35, linewidth=0.6)
    for spine in axis.spines.values():
        spine.set_color("#31443f")


def plot_curve(row: dict, path: Path, title: str) -> None:
    balance = row["initial"]
    times, values = [], []
    for deal in row["deals"]:
        balance += deal["cashflow"]
        times.append(deal["time"])
        values.append(balance)
    figure, axis = plt.subplots(figsize=(10.2, 4.2), dpi=165)
    figure.patch.set_facecolor("#07110f")
    chart_style(axis)
    if times:
        axis.plot(times, values, color="#67f5c3", linewidth=1.7)
    else:
        axis.axhline(balance, color="#67f5c3")
    axis.axhline(row["initial"], color="#9eb1ac", linewidth=0.8, linestyle="--")
    axis.set_title(title, color="white", fontsize=13, pad=12)
    axis.set_ylabel("Realized balance (USD)", color="#c9d8d4")
    figure.tight_layout()
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)


def plot_summary(rows: list[dict], path: Path) -> None:
    ordered = sorted(rows, key=lambda item: item["return_pct"])
    colors = ["#ff6b6b" if row["return_pct"] < 0 else "#67f5c3" for row in ordered]
    figure, axis = plt.subplots(figsize=(11, 6.2), dpi=175)
    figure.patch.set_facecolor("#07110f")
    chart_style(axis)
    axis.barh([row["symbol"] for row in ordered], [row["return_pct"] for row in ordered], color=colors, alpha=0.9)
    axis.axvline(0, color="#9eb1ac", linewidth=0.9)
    axis.set_title("CRT universal configuration — locked one-year return", color="white", fontsize=14, pad=12)
    axis.set_xlabel("Return on $10,000 (%)", color="#c9d8d4")
    figure.tight_layout()
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)


def plot_equal_weight(rows: list[dict], path: Path) -> None:
    events = []
    for row in rows:
        for deal in row["deals"]:
            events.append((deal["time"], deal["cashflow"] / row["initial"] * 100.0))
    events.sort(key=lambda item: item[0])
    times, returns = [], []
    total = 0.0
    divisor = max(1, len(rows))
    for when, change in events:
        total += change / divisor
        times.append(when)
        returns.append(total)
    figure, axis = plt.subplots(figsize=(11, 5.0), dpi=175)
    figure.patch.set_facecolor("#07110f")
    chart_style(axis)
    if times:
        axis.plot(times, returns, color="#67f5c3", linewidth=1.8)
    axis.axhline(0, color="#9eb1ac", linewidth=0.9, linestyle="--")
    axis.set_title("CRT equal-weight 11-market locked overlay", color="white", fontsize=14, pad=12)
    axis.set_ylabel("Average return (%)", color="#c9d8d4")
    figure.tight_layout()
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)


def verdict(row: dict) -> str:
    if row["return_pct"] >= 5 and row["profit_factor"] >= 1.20 and row["equity_dd_pct"] <= 15 and row["trades"] >= 25:
        return "KEEP CANDIDATE"
    if row["return_pct"] > 0 and row["profit_factor"] > 1 and row["trades"] >= 15:
        return "WATCH"
    return "REJECT"


def build_report(args: argparse.Namespace) -> None:
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    winner = selection["winner"]
    locked = load_phase(args.locked, "locked")
    charts = args.output / "Charts"
    charts.mkdir(parents=True, exist_ok=True)
    details, rows = [], []
    for slug, (label, group) in SYMBOLS.items():
        row = locked[(slug, winner)]
        row.update({"symbol": label, "slug": slug, "group": group, "variant": winner})
        row["verdict"] = verdict(row)
        plot_curve(row, charts / f"{slug}-locked-equity.png", f"{label} — CRT locked 2025-08-29 to 2026-08-28")
        details.append(row)
        rows.append({key: value for key, value in row.items() if key != "deals"})
    rows.sort(key=lambda item: item["return_pct"], reverse=True)
    plot_summary(details, charts / "all-markets-locked-return.png")
    plot_equal_weight(details, charts / "all-markets-equal-weight-equity.png")
    (args.output / "RESULTS.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    with (args.output / "RESULTS.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    profitable = sum(row["return_pct"] > 0 and row["profit_factor"] > 1 for row in rows)
    average_return = statistics.mean(row["return_pct"] for row in rows)
    lines = [
        "# CRT parent-range — multi-market MT5 audit",
        "",
        f"Development selected one universal configuration for every market: `{winner}`. The locked year was then run without per-symbol parameter changes.",
        "",
        "| Verdict | Market | Group | Return | PF | Win rate | Equity DD | Trades | Final |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['verdict']} | {row['symbol']} | {row['group']} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
            f"{row['win_rate_pct']:.2f}% | {row['equity_dd_pct']:.2f}% | {row['trades']} | ${row['final']:,.2f} |"
        )
    lines += [
        "",
        f"- Profitable locked markets: {profitable}/{len(rows)}.",
        f"- Mean locked return: {average_return:+.2f}%.",
        "- $10,000 initial balance, 1% equity risk, Exness MT5 Every Tick, random execution delay, spread, commission and swap included.",
        "- Development: 2024-08-29 to 2025-08-28; untouched locked test: 2025-08-29 to 2026-08-28.",
        "- The EA uses completed candles only: parent range, one-side raid, close back inside, structural stop and the opposite parent boundary as target.",
        "- No active BAT or website file was changed.",
    ]
    (args.output / "FULL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    select = subparsers.add_parser("select")
    select.add_argument("--development", type=Path, required=True)
    select.add_argument("--output", type=Path, required=True)
    report = subparsers.add_parser("report")
    report.add_argument("--development", type=Path, required=True)
    report.add_argument("--locked", type=Path, required=True)
    report.add_argument("--selection", type=Path, required=True)
    report.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "select":
        choose_universal(args)
    else:
        build_report(args)


if __name__ == "__main__":
    main()
