from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup


SYMBOLS = tuple(item.strip().lower() for item in os.environ.get("TREND_SYMBOLS", "ustec,btcusd,xauusd").split(",") if item.strip())
TIMEFRAMES = ("m15", "h1", "h4")


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
        "equity_dd_pct": percent(values.get("Equity Drawdown Maximal", "")),
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
    sample_penalty = max(0, 35 - row["trades"]) * 0.30
    return row["return_pct"] + 10.0 * (row["profit_factor"] - 1.0) - 0.75 * row["equity_dd_pct"] + 0.5 * row["sharpe"] - sample_penalty


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
        rows.append({"symbol": symbol, "timeframe": timeframe, "variant": variant, "path": str(path), **parse_report(path)})
    return rows


def serializable(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "deals"}


def select_phase(args: argparse.Namespace) -> None:
    rows = load_reports(args.reports, args.phase)
    screen_cases = int(os.environ.get("TREND_SCREEN_CASES_PER_SYMBOL", "15"))
    expected = len(SYMBOLS) * {"screen": screen_cases, "stoprr": 21, "trailing": 7, "session": 5}[args.phase]
    if len(rows) != expected:
        raise RuntimeError(f"Expected {expected} {args.phase} reports, found {len(rows)}")
    winners = {}
    for symbol in SYMBOLS:
        candidates = [row for row in rows if row["symbol"] == symbol]
        eligible = [row for row in candidates if row["trades"] >= args.minimum_trades and row["profit_factor"] > 1.0 and row["return_pct"] > 0]
        winner = max(eligible or candidates, key=lambda row: row["score"])
        winners[symbol] = serializable(winner)
    output = {"selection_policy": "Development-only score; positive PF/return and minimum sample preferred", "winners": winners, "rows": [serializable(row) for row in rows]}
    args.output_json.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    with args.output_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        fields = ["symbol", "timeframe", "variant", "return_pct", "profit_factor", "win_rate_pct", "equity_dd_pct", "trades", "sharpe", "recovery_factor", "score", "history_quality", "commission", "swap", "path"]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted((serializable(row) for row in rows), key=lambda row: (row["symbol"], -row["score"])))
    lines = [f"# Trend Progression {args.phase} selection", "", "Development period: 2023-09-01 to 2025-08-31. This period alone selected the settings.", "", "| Symbol | TF | Variant | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |", "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|"]
    for symbol in SYMBOLS:
        row = winners[symbol]
        lines.append(f"| {symbol.upper()} | {row['timeframe'].upper()} | {row['variant']} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['equity_dd_pct']:.2f}% | {row['trades']} | {row['sharpe']:.2f} | {row['recovery_factor']:.2f} |")
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    plot_candidates(rows, winners, args.phase, args.chart)


def plot_candidates(rows: list[dict], winners: dict, phase: str, output: Path) -> None:
    import matplotlib.pyplot as plt

    fig, axes_grid = plt.subplots(len(SYMBOLS), 1, figsize=(14, 4 * len(SYMBOLS)), constrained_layout=True)
    axes = list(getattr(axes_grid, "flat", [axes_grid]))
    fig.suptitle(f"Trend Progression — {phase} development comparison", fontsize=17, fontweight="bold")
    for axis, symbol in zip(axes, SYMBOLS):
        candidates = sorted((row for row in rows if row["symbol"] == symbol), key=lambda row: row["score"], reverse=True)
        display = candidates[: min(12, len(candidates))]
        labels = [f"{row['timeframe'].upper()} {row['variant']}" for row in display]
        returns = [row["return_pct"] for row in display]
        colors = ["#35e0a1" if row["variant"] == winners[symbol]["variant"] and row["timeframe"] == winners[symbol]["timeframe"] else "#7395c9" for row in display]
        axis.barh(range(len(display)), returns, color=colors)
        axis.set_yticks(range(len(display)), labels)
        axis.invert_yaxis()
        axis.axvline(0, color="#333", linewidth=0.8)
        axis.set_title(symbol.upper())
        axis.set_xlabel("Net return (%)")
        axis.grid(axis="x", alpha=0.2)
        for index, row in enumerate(display):
            axis.text(returns[index], index, f" {returns[index]:+.1f}% | PF {row['profit_factor']:.2f} | DD {row['equity_dd_pct']:.1f}% | n={row['trades']}", va="center", fontsize=8)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=170, facecolor="white")
    plt.close(fig)


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
        return {"samples": samples, "trades": 0, "probability_profitable_pct": 0.0, "ruin_probability_pct": 0.0, "return_p5_pct": 0.0, "return_median_pct": 0.0, "return_p95_pct": 0.0, "max_dd_median_pct": 0.0, "max_dd_p95_pct": 0.0}
    rng = random.Random(9263 + len(outcomes))
    returns, drawdowns = [], []
    profitable = ruin = 0
    for _ in range(samples):
        equity = peak = initial
        maximum_dd = 0.0
        ruined = False
        for _trade in outcomes:
            equity += outcomes[rng.randrange(len(outcomes))]
            peak = max(peak, equity)
            if peak > 0:
                maximum_dd = max(maximum_dd, (peak - equity) / peak * 100.0)
            if equity <= 0:
                ruined = True
        result = (equity - initial) / initial * 100.0
        returns.append(result); drawdowns.append(maximum_dd)
        profitable += int(result > 0.0); ruin += int(ruined)
    return {"samples": samples, "trades": len(outcomes), "probability_profitable_pct": profitable / samples * 100.0, "ruin_probability_pct": ruin / samples * 100.0, "return_p5_pct": quantile(returns, 0.05), "return_median_pct": quantile(returns, 0.50), "return_p95_pct": quantile(returns, 0.95), "max_dd_median_pct": quantile(drawdowns, 0.50), "max_dd_p95_pct": quantile(drawdowns, 0.95)}


def final_audit(args: argparse.Namespace) -> None:
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    locked = load_reports(args.locked_reports, "locked")
    full = load_reports(args.full_reports, "full")
    if len(locked) != len(SYMBOLS) * 2 or len(full) != len(SYMBOLS):
        raise RuntimeError(f"Expected {len(SYMBOLS) * 2} locked and {len(SYMBOLS)} full reports, found {len(locked)} and {len(full)}")
    selections = {name: json.loads(path.read_text(encoding="utf-8"))["winners"] for name, path in (("screen", args.screen), ("stoprr", args.stoprr), ("trailing", args.trailing), ("session", args.session))}
    result = {"test_design": {"development": "2023-09-01 to 2025-08-31", "locked": "2025-09-01 to 2026-09-01", "full": "2023-09-01 to 2026-09-01", "model": "MT5 Every Tick, broker costs and random delay"}, "symbols": {}}
    fig, axes = plt.subplots(len(SYMBOLS), 1, figsize=(14, 4 * len(SYMBOLS)), constrained_layout=True)
    fig.suptitle("Trend Progression — untouched last-year validation", fontsize=17, fontweight="bold")
    mc_rows = (len(SYMBOLS) + 2) // 3
    mc_fig, mc_grid = plt.subplots(mc_rows, 3, figsize=(15, 4.5 * mc_rows), constrained_layout=True)
    mc_axes = list(getattr(mc_grid, "flat", [mc_grid]))
    for unused in mc_axes[len(SYMBOLS):]: unused.set_visible(False)
    mc_fig.suptitle("10,000-path bootstrap Monte Carlo — locked trades", fontsize=16, fontweight="bold")
    for axis, mc_axis, symbol in zip(axes, mc_axes, SYMBOLS):
        variants = {row["variant"]: row for row in locked if row["symbol"] == symbol}
        full_row = next(row for row in full if row["symbol"] == symbol)
        optimized = variants["optimized"]
        mc = monte_carlo(trade_outcomes(optimized["deals"]), optimized["initial"])
        result["symbols"][symbol] = {"selected": {"timeframe": selections["screen"][symbol]["timeframe"], "structure": selections["screen"][symbol]["variant"], "stop_rr": selections["stoprr"][symbol]["variant"], "trailing": selections["trailing"][symbol]["variant"], "session": selections["session"][symbol]["variant"]}, "baseline_locked": serializable(variants["baseline"]), "optimized_locked": serializable(optimized), "optimized_full": serializable(full_row), "monte_carlo": mc}
        for label, row, color in (("Baseline", variants["baseline"], "#9aa3ad"), ("Optimized", optimized, "#16b87a")):
            balance = row["initial"]
            dates = [datetime(2025, 9, 1)]; balances = [balance]
            for deal in row["deals"]:
                balance += deal["cashflow"]
                dates.append(deal["time"]); balances.append(balance)
            axis.step(dates, balances, where="post", label=label, color=color, linewidth=1.6)
        axis.axhline(10_000, color="#444", linestyle="--", linewidth=0.8)
        axis.set_title(f"{symbol.upper()} — optimized {optimized['return_pct']:+.2f}% | PF {optimized['profit_factor']:.2f} | DD {optimized['equity_dd_pct']:.2f}% | n={optimized['trades']}")
        axis.set_ylabel("Balance (USD)"); axis.grid(alpha=0.2); axis.legend(loc="upper left"); axis.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        labels = ["Return P5", "Median", "Return P95", "DD P95"]
        values = [mc["return_p5_pct"], mc["return_median_pct"], mc["return_p95_pct"], mc["max_dd_p95_pct"]]
        mc_axis.bar(labels, values, color=["#ef6c6c", "#35e0a1", "#72a7ff", "#f2b84b"])
        mc_axis.axhline(0, color="#333", linewidth=0.8); mc_axis.set_title(symbol.upper()); mc_axis.set_ylabel("Percent"); mc_axis.tick_params(axis="x", rotation=25); mc_axis.grid(axis="y", alpha=0.2)
        for index, value in enumerate(values): mc_axis.text(index, value, f"{value:.1f}%", ha="center", va="bottom" if value >= 0 else "top", fontsize=9)
    args.charts.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.charts / "locked-baseline-vs-optimized-equity.png", dpi=180, facecolor="white"); plt.close(fig)
    mc_fig.savefig(args.charts / "locked-monte-carlo.png", dpi=180, facecolor="white"); plt.close(mc_fig)
    args.output_json.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    with args.output_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        fields = ["symbol", "period", "return_pct", "profit_factor", "win_rate_pct", "equity_dd_pct", "trades", "sharpe", "recovery_factor", "commission", "swap"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for symbol in SYMBOLS:
            for period in ("baseline_locked", "optimized_locked", "optimized_full"):
                row = result["symbols"][symbol][period]
                writer.writerow({"symbol": symbol.upper(), "period": period, **{key: row[key] for key in fields if key in row}})
    lines = ["# Trend Progression final native-MT5 audit", "", "The two-year development sample selected every parameter. The last year was then run once, untouched.", "", "## Untouched last-year comparison", "", "| Symbol | Config | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |", "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for symbol in SYMBOLS:
        for label, key in (("Baseline", "baseline_locked"), ("Optimized", "optimized_locked")):
            row = result["symbols"][symbol][key]
            lines.append(f"| {symbol.upper()} | {label} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['equity_dd_pct']:.2f}% | {row['trades']} | {row['sharpe']:.2f} | {row['recovery_factor']:.2f} |")
    lines += ["", "## Selected mechanical configuration", "", "| Symbol | TF | Structure | Stop / RR | Exit management | Session |", "|---|---:|---|---|---|---|"]
    for symbol in SYMBOLS:
        selected = result["symbols"][symbol]["selected"]
        lines.append(f"| {symbol.upper()} | {selected['timeframe'].upper()} | {selected['structure']} | {selected['stop_rr']} | {selected['trailing']} | {selected['session']} |")
    lines += ["", "## Three-year and Monte Carlo context", "", "| Symbol | 3Y return | 3Y PF | 3Y DD | 3Y trades | MC profitable | MC return P5 | MC median | MC DD P95 | Ruin |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for symbol in SYMBOLS:
        row = result["symbols"][symbol]["optimized_full"]; mc = result["symbols"][symbol]["monte_carlo"]
        lines.append(f"| {symbol.upper()} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['equity_dd_pct']:.2f}% | {row['trades']} | {mc['probability_profitable_pct']:.1f}% | {mc['return_p5_pct']:+.2f}% | {mc['return_median_pct']:+.2f}% | {mc['max_dd_p95_pct']:.2f}% | {mc['ruin_probability_pct']:.2f}% |")
    lines += ["", "Costs shown by MT5 include broker spread in tick execution, commission, swap and random execution delay. Session hours are broker-server hours."]
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    select = sub.add_parser("select")
    select.add_argument("--phase", choices=("screen", "stoprr", "trailing", "session"), required=True)
    select.add_argument("--reports", type=Path, required=True)
    select.add_argument("--minimum-trades", type=int, default=20)
    select.add_argument("--output-json", type=Path, required=True)
    select.add_argument("--output-csv", type=Path, required=True)
    select.add_argument("--output-md", type=Path, required=True)
    select.add_argument("--chart", type=Path, required=True)
    select.set_defaults(func=select_phase)
    final = sub.add_parser("final")
    final.add_argument("--locked-reports", type=Path, required=True)
    final.add_argument("--full-reports", type=Path, required=True)
    final.add_argument("--screen", type=Path, required=True)
    final.add_argument("--stoprr", type=Path, required=True)
    final.add_argument("--trailing", type=Path, required=True)
    final.add_argument("--session", type=Path, required=True)
    final.add_argument("--charts", type=Path, required=True)
    final.add_argument("--output-json", type=Path, required=True)
    final.add_argument("--output-csv", type=Path, required=True)
    final.add_argument("--output-md", type=Path, required=True)
    final.set_defaults(func=final_audit)
    args = parser.parse_args(); args.func(args)


if __name__ == "__main__":
    main()
