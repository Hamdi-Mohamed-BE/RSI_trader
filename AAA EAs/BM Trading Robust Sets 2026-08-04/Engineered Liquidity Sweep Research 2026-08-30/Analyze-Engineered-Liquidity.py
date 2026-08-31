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
    "xauusd": ("XAUUSD", "Metal"),
    "btcusd": ("BTCUSD", "Crypto"),
    "ethusd": ("ETHUSD", "Crypto"),
    "ustec": ("USTEC", "Index"),
    "eurusd": ("EURUSD", "Forex"),
    "gbpusd": ("GBPUSD", "Forex"),
    "usdjpy": ("USDJPY", "Forex"),
    "audusd": ("AUDUSD", "Forex"),
    "usdcad": ("USDCAD", "Forex"),
    "usdchf": ("USDCHF", "Forex"),
    "nzdusd": ("NZDUSD", "Forex"),
}

VARIANTS = (
    "m15-h1-reclaim",
    "m15-h4-reclaim",
    "m15-h4-displacement",
    "m30-h4-reclaim",
    "m30-h4-displacement",
    "h1-d1-reclaim",
)


def compact(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def number(value: str | None) -> float:
    match = re.search(r"[-+]?\d+(?:[,.]\d{3})*(?:\.\d+)?", compact(value or "").replace(" ", ""))
    return float(match.group(0).replace(",", "")) if match else 0.0


def percent(value: str | None) -> float:
    match = re.search(r"([-+]?\d+(?:\.\d+)?)%", compact(value or ""))
    return float(match.group(1)) if match else 0.0


def soup_for(path: Path) -> BeautifulSoup:
    raw = path.read_bytes()
    for encoding in ("utf-16", "utf-8-sig", "utf-8", "cp1252"):
        try:
            return BeautifulSoup(raw.decode(encoding), "html.parser")
        except UnicodeError:
            continue
    return BeautifulSoup(raw.decode("utf-8", errors="replace"), "html.parser")


def parse_report(path: Path) -> dict:
    soup = soup_for(path)
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
        if len(cells) != 13 or not re.fullmatch(r"\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}", cells[0]):
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


def identify(path: Path, phase: str) -> tuple[str, str]:
    match = re.fullmatch(rf"([a-z0-9]+)--(.+)--{phase}\.htm", path.name, re.I)
    if not match:
        raise ValueError(path.name)
    slug = match.group(1).lower()
    variant = match.group(2).lower()
    if slug not in MARKETS or variant not in VARIANTS:
        raise ValueError(path.name)
    return slug, variant


def load_phase(directory: Path, phase: str) -> dict[tuple[str, str], dict]:
    rows = {}
    for path in directory.glob(f"*--{phase}.htm"):
        try:
            slug, variant = identify(path, phase)
        except ValueError:
            continue
        rows[(slug, variant)] = parse_report(path)
    return rows


def development_score(row: dict) -> float:
    trades = row["trades"]
    if trades < 10 or row["profit_factor"] <= 0:
        return -1000.0 + trades
    bounded_pf = min(row["profit_factor"], 3.0)
    sample_penalty = max(0, 35 - trades) * 0.30
    return row["return_pct"] + 12.0 * (bounded_pf - 1.0) - 0.55 * row["equity_dd_pct"] - sample_penalty


def select_variants(args: argparse.Namespace) -> None:
    rows = load_phase(args.development, "development")
    selection = {"method": "development-only score", "markets": {}}
    for slug, (market, group) in MARKETS.items():
        candidates = []
        for variant in VARIANTS:
            row = rows.get((slug, variant))
            if row is None:
                raise RuntimeError(f"Missing development report: {slug} {variant}")
            candidates.append((development_score(row), variant, row))
        score, variant, row = max(candidates, key=lambda item: item[0])
        selection["markets"][slug] = {
            "market": market,
            "group": group,
            "variant": variant,
            "score": score,
            "development": {key: value for key, value in row.items() if key != "deals"},
        }
    args.output.write_text(json.dumps(selection, indent=2), encoding="utf-8")


def chart_style(axis) -> None:
    axis.set_facecolor("#0b1714")
    axis.tick_params(colors="#9eb1ac")
    axis.grid(color="#31443f", alpha=0.35, linewidth=0.6)
    for spine in axis.spines.values():
        spine.set_color("#31443f")


def plot_curve(row: dict, path: Path, title: str) -> None:
    balance = row["initial"]
    times: list[datetime] = []
    values: list[float] = []
    for deal in row["deals"]:
        balance += deal["cashflow"]
        times.append(deal["time"])
        values.append(balance)
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


def plot_returns(rows: list[dict], path: Path) -> None:
    ordered = sorted(rows, key=lambda row: row["locked_return_pct"])
    colors = ["#67f5c3" if row["locked_return_pct"] >= 0 else "#ff6b6b" for row in ordered]
    figure, axis = plt.subplots(figsize=(11.2, 6.3), dpi=175)
    figure.patch.set_facecolor("#07110f")
    chart_style(axis)
    axis.barh([row["market"] for row in ordered], [row["locked_return_pct"] for row in ordered], color=colors)
    axis.axvline(0, color="#9eb1ac", linewidth=0.9)
    axis.set_title("Engineered-liquidity sweep — untouched locked-year return", color="white", fontsize=14, pad=12)
    axis.set_xlabel("Return on $10,000 at 1% risk (%)", color="#c9d8d4")
    figure.tight_layout()
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)


def plot_development_vs_locked(rows: list[dict], path: Path) -> None:
    ordered = sorted(rows, key=lambda row: row["locked_return_pct"], reverse=True)
    positions = list(range(len(ordered)))
    width = 0.38
    figure, axis = plt.subplots(figsize=(12.8, 6.2), dpi=175)
    figure.patch.set_facecolor("#07110f")
    chart_style(axis)
    axis.bar([x - width / 2 for x in positions], [row["development_return_pct"] for row in ordered], width, label="Development", color="#6bc9ff")
    axis.bar([x + width / 2 for x in positions], [row["locked_return_pct"] for row in ordered], width, label="Locked", color="#67f5c3")
    axis.axhline(0, color="#9eb1ac", linewidth=0.9)
    axis.set_xticks(positions)
    axis.set_xticklabels([row["market"] for row in ordered], rotation=45, ha="right")
    axis.set_ylabel("Return (%)", color="#c9d8d4")
    axis.set_title("Selected on development only — validation comparison", color="white", fontsize=14, pad=12)
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
    figure, axis = plt.subplots(figsize=(11.2, 5.0), dpi=175)
    figure.patch.set_facecolor("#07110f")
    chart_style(axis)
    if times:
        axis.plot(times, curve, color="#67f5c3", linewidth=1.8)
    axis.axhline(0, color="#9eb1ac", linewidth=0.9, linestyle="--")
    axis.set_title("Equal-weight 11-market locked overlay", color="white", fontsize=14, pad=12)
    axis.set_ylabel("Average return (%)", color="#c9d8d4")
    figure.tight_layout()
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)
    return value, max_dd


def verdict(dev: dict, locked: dict) -> str:
    if (
        dev["return_pct"] > 0
        and dev["profit_factor"] >= 1.15
        and dev["trades"] >= 30
        and locked["return_pct"] >= 5
        and locked["profit_factor"] >= 1.20
        and locked["equity_dd_pct"] <= 15
        and locked["trades"] >= 30
    ):
        return "KEEP CANDIDATE"
    if (
        dev["return_pct"] > 0
        and dev["profit_factor"] > 1
        and locked["return_pct"] > 0
        and locked["profit_factor"] > 1
        and locked["trades"] >= 20
    ):
        return "WATCH"
    return "REJECT"


def build_report(args: argparse.Namespace) -> None:
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    development = load_phase(args.development, "development")
    locked = load_phase(args.locked, "locked")
    charts = args.output / "Charts"
    charts.mkdir(parents=True, exist_ok=True)
    details = []
    rows = []
    for slug, (market, group) in MARKETS.items():
        variant = selection["markets"][slug]["variant"]
        dev = development[(slug, variant)]
        test = locked.get((slug, variant))
        if test is None:
            raise RuntimeError(f"Missing locked report: {slug} {variant}")
        status = verdict(dev, test)
        plot_curve(test, charts / f"{slug}-locked-equity.png", f"{market} — {variant} — locked 2025-08-29 to 2026-08-28")
        details.append({"market": market, "locked": test})
        rows.append(
            {
                "verdict": status,
                "market": market,
                "group": group,
                "variant": variant,
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
    plot_returns(rows, charts / "all-markets-locked-return.png")
    plot_development_vs_locked(rows, charts / "development-vs-locked-return.png")
    combined_return, combined_dd = plot_equal_weight(details, charts / "all-markets-equal-weight-equity.png")
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "RESULTS.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    with (args.output / "RESULTS.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    keep_count = sum(row["verdict"] == "KEEP CANDIDATE" for row in rows)
    profitable_both = sum(
        row["development_return_pct"] > 0
        and row["development_pf"] > 1
        and row["locked_return_pct"] > 0
        and row["locked_pf"] > 1
        for row in rows
    )
    lines = [
        "# Engineered-liquidity sweep — multi-market MT5 audit",
        "",
        "This is an objective reconstruction of the supplied transcript, not the speaker's proprietary code. Each market's configuration was chosen using only the development year, then frozen for the untouched locked year.",
        "",
        "| Verdict | Market | Selected configuration | Dev return | Dev PF | Locked return | Locked PF | Win rate | Equity DD | Trades |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['verdict']} | {row['market']} | {row['variant']} | {row['development_return_pct']:+.2f}% | "
            f"{row['development_pf']:.2f} | {row['locked_return_pct']:+.2f}% | {row['locked_pf']:.2f} | "
            f"{row['locked_win_rate_pct']:.2f}% | {row['locked_equity_dd_pct']:.2f}% | {row['locked_trades']} |"
        )
    lines += [
        "",
        f"- Strict keep candidates: {keep_count}/{len(rows)}.",
        f"- Profitable with PF above 1 in both periods: {profitable_both}/{len(rows)}.",
        f"- Equal-weight locked overlay return: {combined_return:+.2f}%.",
        f"- Equal-weight realized drawdown: {combined_dd:.2f} percentage points.",
        "- Development: 2024-08-29 to 2025-08-28; untouched locked validation: 2025-08-29 to 2026-08-28.",
        "- $10,000 initial balance, 1% equity risk, Exness MT5 Every Tick, random execution delay, spread, commission and swap included.",
        "- Core rule: dominant EMA trend, confirmed internal swing sweep against the trend, reclaim close, structural stop beyond the sweep and prior opposing liquidity as target.",
        "- All signals use completed bars. No locked-period result influenced configuration selection.",
        "- No active installation BAT or website file was changed.",
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
        select_variants(args)
    else:
        build_report(args)


if __name__ == "__main__":
    main()
