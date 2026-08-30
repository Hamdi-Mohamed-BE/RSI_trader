from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
from bs4 import BeautifulSoup

SYMBOLS = ("btcusd", "ethusd")
LABELS = {"btcusd": "BTCUSD", "ethusd": "ETHUSD"}


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
        deals.append(
            {
                "time": datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S"),
                "commission": number(cells[8]),
                "swap": number(cells[9]),
                "profit": number(cells[10]),
                "cashflow": number(cells[8]) + number(cells[9]) + number(cells[10]),
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
    match = re.match(rf"^(btcusd|ethusd)--(.+)--{phase}\.htm$", path.name, re.I)
    if not match:
        raise ValueError(path.name)
    return match.group(1).lower(), match.group(2)


def score(row: dict) -> float:
    sample_penalty = max(0, 25 - row["trades"]) * 0.35
    if row["trades"] < 10 or row["profit_factor"] <= 0:
        return -1e9 + row["trades"]
    return (
        row["return_pct"]
        + 12.0 * (row["profit_factor"] - 1.0)
        - 0.65 * row["equity_dd_pct"]
        + 0.035 * (row["win_rate_pct"] - 50.0)
        - sample_penalty
    )


def load_phase(directory: Path, phase: str) -> dict[tuple[str, str], dict]:
    rows = {}
    for path in directory.glob("*.htm"):
        try:
            symbol, variant = identify(path, phase)
        except ValueError:
            continue
        row = parse_report(path)
        row["score"] = score(row)
        rows[(symbol, variant)] = row
    return rows


def select_development(args: argparse.Namespace) -> None:
    rows = load_phase(args.reports, "slowdev")
    selected = {}
    for symbol in SYMBOLS:
        candidates = []
        for (candidate_symbol, variant), row in rows.items():
            if candidate_symbol != symbol:
                continue
            candidates.append({"variant": variant, **{key: value for key, value in row.items() if key != "deals"}})
        if not candidates:
            raise RuntimeError(f"No slow development reports for {symbol}")
        candidates.sort(key=lambda item: item["score"], reverse=True)
        selected[symbol] = {"top_two": candidates[:2]}
    args.output.write_text(json.dumps(selected, indent=2), encoding="utf-8")


def select_validation(args: argparse.Namespace) -> None:
    selected = json.loads(args.selection.read_text(encoding="utf-8"))
    development = load_phase(args.development, "slowdev")
    validation = load_phase(args.validation, "slowval")
    for symbol in SYMBOLS:
        ranked = []
        for candidate in selected[symbol]["top_two"]:
            variant = candidate["variant"]
            dev = development[(symbol, variant)]
            val = validation[(symbol, variant)]
            combined_score = min(dev["score"], val["score"]) + 0.35 * (dev["score"] + val["score"])
            ranked.append(
                {
                    "variant": variant,
                    "combined_score": combined_score,
                    "development": {key: value for key, value in dev.items() if key != "deals"},
                    "validation": {key: value for key, value in val.items() if key != "deals"},
                }
            )
        ranked.sort(key=lambda item: item["combined_score"], reverse=True)
        selected[symbol]["validated_candidates"] = ranked
        selected[symbol]["winner"] = ranked[0]
    args.output.write_text(json.dumps(selected, indent=2), encoding="utf-8")


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
    figure, axis = plt.subplots(figsize=(10.5, 4.4), dpi=170)
    figure.patch.set_facecolor("#07110f")
    chart_style(axis)
    if times:
        axis.plot(times, values, color="#67f5c3", linewidth=1.7)
    else:
        axis.axhline(balance, color="#67f5c3")
    axis.axhline(row["initial"], color="#7a8d88", linewidth=0.8, linestyle="--")
    axis.set_title(title, color="white", fontsize=13, pad=12)
    axis.set_ylabel("Realized balance (USD)", color="#c9d8d4")
    figure.tight_layout()
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)


def plot_combined(rows: list[dict], path: Path) -> None:
    figure, axis = plt.subplots(figsize=(11, 5.2), dpi=175)
    figure.patch.set_facecolor("#07110f")
    chart_style(axis)
    for row in rows:
        balance = row["initial"]
        times, values = [], []
        for deal in row["deals"]:
            balance += deal["cashflow"]
            times.append(deal["time"])
            values.append((balance / row["initial"] - 1.0) * 100.0)
        axis.plot(times, values, linewidth=1.8, label=row["symbol"])
    axis.axhline(0, color="#9eb1ac", linewidth=0.9, linestyle="--")
    axis.set_title("Slower crypto edge — untouched final holdout", color="white", fontsize=14, pad=12)
    axis.set_ylabel("Return from $10,000 (%)", color="#c9d8d4")
    axis.legend(facecolor="#0b1714", edgecolor="#31443f", labelcolor="white")
    figure.tight_layout()
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)


def decision(row: dict) -> str:
    val = row["validation"]
    if (
        row["return_pct"] >= 2.0
        and row["profit_factor"] >= 1.15
        and row["equity_dd_pct"] <= 12.0
        and row["trades"] >= 10
        and val["return_pct"] > 0
        and val["profit_factor"] >= 1.10
        and val["trades"] >= 10
    ):
        return "KEEP CANDIDATE"
    if row["return_pct"] > 0 and row["profit_factor"] > 1.0:
        return "WATCH — NOT ROBUST"
    return "REJECT"


def build_report(args: argparse.Namespace) -> None:
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    holdout = load_phase(args.holdout, "holdout")
    charts = args.output / "Slow Charts"
    charts.mkdir(parents=True, exist_ok=True)
    rows, details = [], []
    for symbol in SYMBOLS:
        winner = selection[symbol]["winner"]
        variant = winner["variant"]
        row = holdout[(symbol, variant)]
        row.update(
            {
                "symbol": LABELS[symbol],
                "slug": symbol,
                "variant": variant,
                "development": winner["development"],
                "validation": winner["validation"],
            }
        )
        row["decision"] = decision(row)
        plot_curve(row, charts / f"{symbol}-final-holdout-equity.png", f"{LABELS[symbol]} — final holdout 2026-03-01 to 2026-08-28")
        details.append(row)
        rows.append({key: value for key, value in row.items() if key != "deals"})
    plot_combined(details, charts / "all-crypto-final-holdout-equity.png")
    rows.sort(key=lambda item: item["return_pct"], reverse=True)
    (args.output / "SLOW RESULTS.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    flat_rows = []
    for row in rows:
        flat_rows.append(
            {
                "symbol": row["symbol"],
                "variant": row["variant"],
                "development_return_pct": row["development"]["return_pct"],
                "development_pf": row["development"]["profit_factor"],
                "validation_return_pct": row["validation"]["return_pct"],
                "validation_pf": row["validation"]["profit_factor"],
                "holdout_return_pct": row["return_pct"],
                "holdout_pf": row["profit_factor"],
                "holdout_win_rate_pct": row["win_rate_pct"],
                "holdout_equity_dd_pct": row["equity_dd_pct"],
                "holdout_trades": row["trades"],
                "decision": row["decision"],
            }
        )
    with (args.output / "SLOW RESULTS.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=flat_rows[0].keys())
        writer.writeheader()
        writer.writerows(flat_rows)
    lines = [
        "# Slower crypto edge — three-stage MT5 validation",
        "",
        "The M15 candidates failed their locked test. A second, explicitly disclosed pass reduced signal frequency to H1/H4 and used development, validation, then a final six-month holdout.",
        "",
        "| Symbol | Selected variant | Development return / PF | Validation return / PF | Final holdout return / PF | Win rate | Equity DD | Trades | Decision |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['symbol']} | {row['variant']} | {row['development']['return_pct']:+.2f}% / {row['development']['profit_factor']:.2f} | "
            f"{row['validation']['return_pct']:+.2f}% / {row['validation']['profit_factor']:.2f} | {row['return_pct']:+.2f}% / {row['profit_factor']:.2f} | "
            f"{row['win_rate_pct']:.2f}% | {row['equity_dd_pct']:.2f}% | {row['trades']} | {row['decision']} |"
        )
    lines += [
        "",
        "- Exness MT5 Trial 16, native Every Tick model, 100% history quality, random execution delay, spread, commission and swap included.",
        "- $10,000 initial balance and 1% equity risk per trade.",
        "- Development: 2024-08-29 to 2025-08-28; validation: 2025-08-29 to 2026-02-28; final holdout: 2026-03-01 to 2026-08-28.",
        "- The second-pass investigation was started after the first M15 locked test failed; that sequence is disclosed to avoid presenting the research as a pristine one-shot discovery.",
        "- No active BAT or website file was changed.",
    ]
    (args.output / "SLOW FULL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    dev = subparsers.add_parser("select-development")
    dev.add_argument("--reports", type=Path, required=True)
    dev.add_argument("--output", type=Path, required=True)
    validation = subparsers.add_parser("select-validation")
    validation.add_argument("--development", type=Path, required=True)
    validation.add_argument("--validation", type=Path, required=True)
    validation.add_argument("--selection", type=Path, required=True)
    validation.add_argument("--output", type=Path, required=True)
    report = subparsers.add_parser("report")
    report.add_argument("--development", type=Path, required=True)
    report.add_argument("--validation", type=Path, required=True)
    report.add_argument("--holdout", type=Path, required=True)
    report.add_argument("--selection", type=Path, required=True)
    report.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "select-development":
        select_development(args)
    elif args.command == "select-validation":
        select_validation(args)
    else:
        build_report(args)


if __name__ == "__main__":
    main()
