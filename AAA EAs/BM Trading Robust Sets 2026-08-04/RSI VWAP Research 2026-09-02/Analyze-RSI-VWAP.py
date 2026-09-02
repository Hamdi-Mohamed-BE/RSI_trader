from __future__ import annotations

import argparse
import csv
import json
import random
import re
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup


SYMBOLS = ("btcusd", "ethusd", "xauusd", "xagusd", "gbpjpy", "us30", "ustec")
TIMEFRAMES = ("m5", "m15", "m30", "h1", "h4")


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
                "direction": cells[4].lower(),
                "commission": number(cells[8]),
                "swap": number(cells[9]),
                "profit": number(cells[10]),
                "cashflow": number(cells[8]) + number(cells[9]) + number(cells[10]),
            }
        )
    initial = number(values.get("Initial Deposit")) or 10_000.0
    net = number(values.get("Total Net Profit"))
    equity_dd = values.get("Equity Drawdown Maximal", "")
    wins = values.get("Profit Trades (% of total)", "")
    losses = values.get("Loss Trades (% of total)", "")
    result = {
        "initial": initial,
        "final": initial + net,
        "net": net,
        "return_pct": net / initial * 100.0,
        "profit_factor": number(values.get("Profit Factor")),
        "win_rate_pct": percent(wins),
        "wins": int(number(wins)),
        "losses": int(number(losses)),
        "trades": int(number(values.get("Total Trades"))),
        "equity_dd_pct": percent(equity_dd),
        "recovery_factor": number(values.get("Recovery Factor")),
        "sharpe": number(values.get("Sharpe Ratio")),
        "expected_payoff": number(values.get("Expected Payoff")),
        "history_quality": values.get("History Quality", ""),
        "commission": sum(item["commission"] for item in deals),
        "swap": sum(item["swap"] for item in deals),
        "deals": deals,
    }
    result["score"] = score(result)
    return result


def score(row: dict) -> float:
    if row["trades"] < 8 or row["profit_factor"] <= 0:
        return -10_000.0 + row["trades"]
    sample_penalty = max(0, 30 - row["trades"]) * 0.20
    return (
        row["return_pct"]
        + 8.0 * (row["profit_factor"] - 1.0)
        - 0.55 * row["equity_dd_pct"]
        + 0.25 * row["sharpe"]
        - sample_penalty
    )


def identify(path: Path, phase: str) -> tuple[str, str, str]:
    match = re.match(rf"^({'|'.join(SYMBOLS)})--({'|'.join(TIMEFRAMES)})--(.+)--{phase}\.htm$", path.name, re.I)
    if not match:
        raise ValueError(path.name)
    return match.group(1).lower(), match.group(2).lower(), match.group(3).lower()


def load_reports(directory: Path, phase: str) -> list[dict]:
    rows = []
    for path in directory.glob("*.htm"):
        try:
            symbol, timeframe, variant = identify(path, phase)
        except ValueError:
            continue
        metrics = parse_report(path)
        rows.append({"symbol": symbol, "timeframe": timeframe, "variant": variant, "path": str(path), **metrics})
    return rows


def serializable(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "deals"}


def trade_outcomes(deals: list[dict]) -> list[float]:
    pending_cost = 0.0
    outcomes = []
    for deal in deals:
        if deal["direction"] == "in":
            pending_cost += deal["cashflow"]
        elif deal["direction"] == "out":
            outcomes.append(pending_cost + deal["cashflow"])
            pending_cost = 0.0
    return outcomes


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def monte_carlo(outcomes: list[float], initial: float, samples: int = 10_000) -> dict:
    if not outcomes:
        return {"samples": samples, "trades": 0, "probability_profitable_pct": 0.0, "return_p5_pct": 0.0, "return_median_pct": 0.0, "return_p95_pct": 0.0, "max_dd_median_pct": 0.0, "max_dd_p95_pct": 0.0}
    rng = random.Random(9264 + len(outcomes))
    returns = []
    drawdowns = []
    profitable = 0
    for _ in range(samples):
        equity = initial
        peak = initial
        maximum_dd = 0.0
        for _trade in outcomes:
            equity += outcomes[rng.randrange(len(outcomes))]
            peak = max(peak, equity)
            if peak > 0:
                maximum_dd = max(maximum_dd, (peak - equity) / peak * 100.0)
        result = (equity - initial) / initial * 100.0
        returns.append(result)
        drawdowns.append(maximum_dd)
        profitable += int(result > 0.0)
    return {
        "samples": samples,
        "trades": len(outcomes),
        "probability_profitable_pct": profitable / samples * 100.0,
        "return_p5_pct": quantile(returns, 0.05),
        "return_median_pct": quantile(returns, 0.50),
        "return_p95_pct": quantile(returns, 0.95),
        "max_dd_median_pct": quantile(drawdowns, 0.50),
        "max_dd_p95_pct": quantile(drawdowns, 0.95),
    }


def screen(args: argparse.Namespace) -> None:
    rows = load_reports(args.reports, "development")
    expected = len(SYMBOLS) * len(TIMEFRAMES)
    if len(rows) != expected:
        raise RuntimeError(f"Expected {expected} screening reports, found {len(rows)}")
    winners = {}
    for symbol in SYMBOLS:
        candidates = sorted((row for row in rows if row["symbol"] == symbol), key=lambda row: row["score"], reverse=True)
        winners[symbol] = serializable(candidates[0])
    output = {"winners": winners, "rows": [serializable(row) for row in rows]}
    args.output_json.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    fieldnames = ["symbol", "timeframe", "variant", "return_pct", "profit_factor", "win_rate_pct", "equity_dd_pct", "trades", "sharpe", "recovery_factor", "score", "history_quality", "commission", "swap", "path"]
    with args.output_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted((serializable(row) for row in rows), key=lambda row: (row["symbol"], -row["score"])))
    lines = [
        "# RSI+VWAP native MT5 timeframe screen",
        "",
        "| Symbol | Selected TF | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for symbol in SYMBOLS:
        row = winners[symbol]
        lines.append(
            f"| {symbol.upper()} | {row['timeframe'].upper()} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
            f"{row['win_rate_pct']:.2f}% | {row['equity_dd_pct']:.2f}% | {row['trades']} | {row['sharpe']:.2f} | {row['recovery_factor']:.2f} |"
        )
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def select(args: argparse.Namespace) -> None:
    rows = load_reports(args.reports, "development")
    winners = {}
    for symbol in SYMBOLS:
        candidates = [row for row in rows if row["symbol"] == symbol]
        if not candidates:
            raise RuntimeError(f"No development candidates found for {symbol}")
        eligible = [row for row in candidates if row["trades"] >= args.minimum_trades and row["profit_factor"] > 1.0]
        pool = eligible or candidates
        winner = max(pool, key=lambda row: row["score"])
        winners[symbol] = serializable(winner)
    output = {"winners": winners, "rows": [serializable(row) for row in rows]}
    args.output_json.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    lines = [
        f"# {args.title}",
        "",
        "| Symbol | TF | Variant | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for symbol in SYMBOLS:
        row = winners[symbol]
        lines.append(
            f"| {symbol.upper()} | {row['timeframe'].upper()} | {row['variant']} | {row['return_pct']:+.2f}% | "
            f"{row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['equity_dd_pct']:.2f}% | "
            f"{row['trades']} | {row['sharpe']:.2f} | {row['recovery_factor']:.2f} |"
        )
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def final_audit(args: argparse.Namespace) -> None:
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    rows = load_reports(args.reports, "locked")
    if len(rows) != len(SYMBOLS) * 2:
        raise RuntimeError(f"Expected {len(SYMBOLS) * 2} locked reports, found {len(rows)}")
    stop_selection = json.loads(args.stop_selection.read_text(encoding="utf-8"))["winners"]
    trail_selection = json.loads(args.trail_selection.read_text(encoding="utf-8"))["winners"]
    session_selection = json.loads(args.session_selection.read_text(encoding="utf-8"))["winners"]
    by_symbol: dict[str, dict[str, dict]] = {}
    curves = {}
    monte_carlo_results = {}
    for symbol in SYMBOLS:
        variants = {row["variant"]: row for row in rows if row["symbol"] == symbol}
        if set(variants) != {"baseline", "optimized"}:
            raise RuntimeError(f"Missing baseline/optimized locked pair for {symbol}: {sorted(variants)}")
        by_symbol[symbol] = variants
        optimized = variants["optimized"]
        balance = optimized["initial"]
        points = [{"time": "2025-09-01T00:00:00", "balance": balance}]
        for deal in optimized["deals"]:
            balance += deal["cashflow"]
            points.append({"time": deal["time"].isoformat(), "balance": balance})
        curves[symbol] = points
        monte_carlo_results[symbol] = monte_carlo(trade_outcomes(optimized["deals"]), optimized["initial"])

    output = {
        "period": {"from": "2025-09-01", "to": "2026-09-01"},
        "method": "MT5 Every Tick, Exness history, spread, commission, swap and random execution delay",
        "rows": [serializable(row) for row in rows],
        "configs": {
            symbol: {
                "timeframe": stop_selection[symbol]["timeframe"],
                "stop_rr": stop_selection[symbol]["variant"],
                "trailing": trail_selection[symbol]["variant"],
                "session": session_selection[symbol]["variant"],
                "risk_percent": 1.0,
            }
            for symbol in SYMBOLS
        },
        "monte_carlo": monte_carlo_results,
        "curves": curves,
    }
    args.output_json.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")

    fieldnames = ["symbol", "timeframe", "variant", "return_pct", "profit_factor", "win_rate_pct", "equity_dd_pct", "trades", "sharpe", "recovery_factor", "history_quality", "commission", "swap", "path"]
    with args.output_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(serializable(row) for row in sorted(rows, key=lambda item: (item["symbol"], item["variant"])))

    lines = [
        "# RSI+VWAP locked last-year audit",
        "",
        "Period: 2025-09-01 to 2026-09-01. Native MT5 Every Tick with broker spread, commission, swap and random execution delay.",
        "",
        "| Symbol | TF | Baseline return | Optimized return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for symbol in SYMBOLS:
        baseline = by_symbol[symbol]["baseline"]
        optimized = by_symbol[symbol]["optimized"]
        lines.append(
            f"| {symbol.upper()} | {optimized['timeframe'].upper()} | {baseline['return_pct']:+.2f}% | {optimized['return_pct']:+.2f}% | "
            f"{optimized['profit_factor']:.2f} | {optimized['win_rate_pct']:.2f}% | {optimized['equity_dd_pct']:.2f}% | "
            f"{optimized['trades']} | {optimized['sharpe']:.2f} | {optimized['recovery_factor']:.2f} |"
        )
    lines += [
        "",
        "## Selected configuration",
        "",
        "| Symbol | Stop / RR | Trailing | Session | Risk |",
        "|---|---|---|---|---:|",
    ]
    for symbol in SYMBOLS:
        config = output["configs"][symbol]
        lines.append(f"| {symbol.upper()} | {config['stop_rr']} | {config['trailing']} | {config['session']} | 1.00% |")
    lines += [
        "",
        "## 10,000-path trade-bootstrap Monte Carlo",
        "",
        "| Symbol | Trades | Profit probability | Return P5 | Median return | Return P95 | Median max DD | P95 max DD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for symbol in SYMBOLS:
        mc = monte_carlo_results[symbol]
        lines.append(
            f"| {symbol.upper()} | {mc['trades']} | {mc['probability_profitable_pct']:.1f}% | {mc['return_p5_pct']:+.2f}% | "
            f"{mc['return_median_pct']:+.2f}% | {mc['return_p95_pct']:+.2f}% | {mc['max_dd_median_pct']:.2f}% | {mc['max_dd_p95_pct']:.2f}% |"
        )
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    args.charts.mkdir(parents=True, exist_ok=True)
    colors = ["#5ef2c2", "#60a5fa", "#fbbf24", "#f472b6", "#c084fc", "#fb7185", "#34d399"]
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(12, 6.5), dpi=160)
    fig.patch.set_facecolor("#061713")
    ax.set_facecolor("#061713")
    for color, symbol in zip(colors, SYMBOLS):
        points = curves[symbol]
        times = [datetime.fromisoformat(item["time"]) for item in points]
        balances = [item["balance"] for item in points]
        ax.step(times, balances, where="post", label=symbol.upper(), linewidth=1.8, color=color)
    ax.axhline(10_000, color="#94a3b8", linestyle="--", linewidth=0.9, alpha=0.65)
    ax.set_title("RSI+VWAP optimized locked-year realized-balance curves", loc="left", fontsize=15, weight="bold")
    ax.set_ylabel("Balance (USD), $10,000 start")
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.grid(color="#24463d", alpha=0.35, linewidth=0.7)
    ax.legend(ncol=4, frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(args.charts / "optimized-locked-equity.png", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 6), dpi=160)
    fig.patch.set_facecolor("#061713")
    ax.set_facecolor("#061713")
    positions = list(range(len(SYMBOLS)))
    width = 0.36
    baseline_returns = [by_symbol[symbol]["baseline"]["return_pct"] for symbol in SYMBOLS]
    optimized_returns = [by_symbol[symbol]["optimized"]["return_pct"] for symbol in SYMBOLS]
    ax.bar([value - width / 2 for value in positions], baseline_returns, width, label="Baseline", color="#64748b")
    ax.bar([value + width / 2 for value in positions], optimized_returns, width, label="Optimized", color="#5ef2c2")
    ax.axhline(0, color="#cbd5e1", linewidth=0.8)
    ax.set_xticks(positions, [symbol.upper() for symbol in SYMBOLS])
    ax.set_ylabel("Locked-year return (%)")
    ax.set_title("Baseline vs optimized — untouched last year", loc="left", fontsize=15, weight="bold")
    ax.grid(axis="y", color="#24463d", alpha=0.35, linewidth=0.7)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(args.charts / "baseline-vs-optimized-return.png", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("screen")
    command.add_argument("--reports", type=Path, required=True)
    command.add_argument("--output-json", type=Path, required=True)
    command.add_argument("--output-csv", type=Path, required=True)
    command.add_argument("--output-md", type=Path, required=True)
    choose = sub.add_parser("select")
    choose.add_argument("--reports", type=Path, required=True)
    choose.add_argument("--output-json", type=Path, required=True)
    choose.add_argument("--output-md", type=Path, required=True)
    choose.add_argument("--title", default="RSI+VWAP development selection")
    choose.add_argument("--minimum-trades", type=int, default=8)
    audit = sub.add_parser("final")
    audit.add_argument("--reports", type=Path, required=True)
    audit.add_argument("--stop-selection", type=Path, required=True)
    audit.add_argument("--trail-selection", type=Path, required=True)
    audit.add_argument("--session-selection", type=Path, required=True)
    audit.add_argument("--output-json", type=Path, required=True)
    audit.add_argument("--output-csv", type=Path, required=True)
    audit.add_argument("--output-md", type=Path, required=True)
    audit.add_argument("--charts", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "screen":
        screen(args)
    elif args.command == "select":
        select(args)
    else:
        final_audit(args)


if __name__ == "__main__":
    main()
