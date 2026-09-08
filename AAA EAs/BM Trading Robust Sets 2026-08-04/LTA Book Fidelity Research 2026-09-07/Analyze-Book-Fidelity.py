from __future__ import annotations

import argparse
import csv
import json
import math
import re
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent


def read_report(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def number(value: str | None) -> float:
    if not value:
        return 0.0
    cleaned = value.replace("\xa0", " ").replace(" ", "").replace(",", "")
    found = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    return float(found.group(0)) if found else 0.0


def summary_values(soup: BeautifulSoup) -> dict[str, str]:
    values: dict[str, str] = {}
    for row in soup.find_all("tr"):
        cells = [" ".join(cell.get_text(" ").split()) for cell in row.find_all(["td", "th"])]
        for index, cell in enumerate(cells[:-1]):
            if cell.endswith(":"):
                values[cell[:-1]] = cells[index + 1]
    return values


def percent(value: str | None) -> float:
    if not value:
        return 0.0
    found = re.search(r"\(([-\d.]+)%\)", value)
    if not found:
        found = re.search(r"([-\d.]+)%", value)
    return float(found.group(1)) if found else 0.0


def parse_deals(soup: BeautifulSoup, initial: float) -> tuple[list[dict], list[dict]]:
    deals: list[dict] = []
    equity = [{"date": None, "balance": initial}]
    in_deals = False
    previous_balance = initial
    for row in soup.find_all("tr"):
        row_text = " ".join(row.get_text(" ").split())
        if row_text == "Deals":
            in_deals = True
            continue
        if not in_deals:
            continue
        cells = [" ".join(cell.get_text(" ").split()) for cell in row.find_all("td")]
        if len(cells) != 13 or not re.fullmatch(r"\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}", cells[0]):
            continue
        if cells[3].lower() == "balance" or not cells[11].strip():
            continue
        balance = number(cells[11])
        commission = number(cells[8])
        swap = number(cells[9])
        profit = number(cells[10]) + commission + swap
        if balance == previous_balance and abs(profit) < 1e-12:
            continue
        timestamp = datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S")
        denominator = max(abs(previous_balance), 1.0)
        deals.append({
            "date": timestamp.isoformat(sep=" "),
            "pnl": profit,
            "return_fraction": profit / denominator,
            "balance": balance,
        })
        equity.append({"date": timestamp.isoformat(sep=" "), "balance": balance})
        previous_balance = balance
    return deals, equity


def monte_carlo(deals: list[dict], paths: int = 4000) -> dict:
    returns = np.asarray([row["return_fraction"] for row in deals], dtype=float)
    if returns.size < 8:
        return {"paths": 0, "p5_final_return_pct": 0.0, "median_final_return_pct": 0.0, "p95_max_dd_pct": 0.0}
    rng = np.random.default_rng(7262026)
    finals = np.empty(paths)
    drawdowns = np.empty(paths)
    for path in range(paths):
        sample = rng.choice(returns, size=returns.size, replace=True)
        curve = 10000.0 * np.cumprod(1.0 + sample)
        curve = np.maximum(curve, 0.01)
        peaks = np.maximum.accumulate(np.r_[10000.0, curve])
        full_curve = np.r_[10000.0, curve]
        dd = (peaks - full_curve) / peaks * 100.0
        finals[path] = (curve[-1] / 10000.0 - 1.0) * 100.0
        drawdowns[path] = float(dd.max())
    return {
        "paths": paths,
        "p5_final_return_pct": float(np.percentile(finals, 5)),
        "median_final_return_pct": float(np.median(finals)),
        "p95_max_dd_pct": float(np.percentile(drawdowns, 95)),
    }


def parse_report(path: Path, meta: dict) -> dict:
    soup = BeautifulSoup(read_report(path), "html.parser")
    values = summary_values(soup)
    initial = number(values.get("Initial Deposit")) or 10000.0
    net = number(values.get("Total Net Profit"))
    wins_text = values.get("Profit Trades (% of total)", "")
    equity_dd = values.get("Equity Drawdown Maximal", "")
    deals, equity = parse_deals(soup, initial)
    metrics = {
        "case": meta["case"], "phase": meta["phase"], "purpose": meta["purpose"],
        "from": meta["from"], "to": meta["to"], "initial_balance": initial,
        "final_balance": initial + net, "net_profit": net,
        "return_pct": net / initial * 100.0 if initial else 0.0,
        "profit_factor": number(values.get("Profit Factor")),
        "win_rate_pct": percent(wins_text),
        "trades": int(number(values.get("Total Trades"))),
        "max_dd_pct": percent(equity_dd),
        "max_dd_amount": number(equity_dd),
        "sharpe": number(values.get("Sharpe Ratio")),
        "recovery_factor": number(values.get("Recovery Factor")),
        "expected_payoff": number(values.get("Expected Payoff")),
        "history_quality_pct": percent(values.get("History Quality")),
        "gross_profit": number(values.get("Gross Profit")),
        "gross_loss": number(values.get("Gross Loss")),
        "report": str(path), "deals": deals, "equity": equity,
    }
    metrics["monte_carlo"] = monte_carlo(deals)
    return metrics


def robust_score(row: dict, baseline: dict) -> float:
    retention = row["trades"] / max(baseline["trades"], 1)
    sample_weight = math.sqrt(min(retention, 1.0))
    downside = row["monte_carlo"]["p5_final_return_pct"]
    return (
        row["return_pct"] * sample_weight
        + 12.0 * math.log(max(row["profit_factor"], 0.05))
        + 0.35 * downside
        - 1.35 * row["max_dd_pct"]
    )


def analyze(phase: str) -> list[dict]:
    report_root = ROOT / "Backtest Reports" / phase
    manifest_path = report_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if isinstance(manifest, dict):
        manifest = [manifest]
    rows = [parse_report(Path(item["report"]), item) for item in manifest]
    baseline = next(row for row in rows if row["case"] == "baseline-standard")
    for row in rows:
        row["trade_retention_pct"] = row["trades"] / max(baseline["trades"], 1) * 100.0
        row["robust_score"] = robust_score(row, baseline)
        row["passes_research_gate"] = bool(
            row["return_pct"] > 0.0
            and row["profit_factor"] >= max(1.05, baseline["profit_factor"])
            and row["max_dd_pct"] <= baseline["max_dd_pct"]
            and row["trade_retention_pct"] >= 60.0
            and row["monte_carlo"]["p5_final_return_pct"] > 0.0
        )
    rows.sort(key=lambda row: row["robust_score"], reverse=True)

    serializable = [{key: value for key, value in row.items() if key not in {"deals", "equity"}} for row in rows]
    results_root = ROOT / "Results"
    results_root.mkdir(exist_ok=True)
    (results_root / f"{phase}-summary.json").write_text(json.dumps(serializable, indent=2), encoding="utf-8")
    if serializable:
        flat_rows = []
        for row in serializable:
            flat = {key: value for key, value in row.items() if key != "monte_carlo"}
            flat.update({f"mc_{key}": value for key, value in row["monte_carlo"].items()})
            flat_rows.append(flat)
        with (results_root / f"{phase}-summary.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0]))
            writer.writeheader()
            writer.writerows(flat_rows)

    fig, ax = plt.subplots(figsize=(13, 7), dpi=170)
    colors = plt.cm.viridis(np.linspace(0.08, 0.95, len(rows)))
    for color, row in zip(colors, rows):
        points = [point for point in row["equity"] if point["date"]]
        if not points:
            continue
        dates = [datetime.fromisoformat(point["date"]) for point in points]
        balances = [point["balance"] for point in points]
        label = f"{row['case']} | {row['return_pct']:+.1f}% PF {row['profit_factor']:.2f} DD {row['max_dd_pct']:.1f}% n={row['trades']}"
        ax.step(dates, balances, where="post", linewidth=1.2, color=color, label=label)
    ax.axhline(10000.0, color="#94a3b8", linewidth=0.8, linestyle="--")
    ax.set_title(f"LTA book-fidelity isolated comparison - {phase}")
    ax.set_ylabel("Closed balance (USD)")
    ax.grid(alpha=0.2)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=9))
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=7)
    fig.tight_layout()
    fig.savefig(results_root / f"{phase}-equity-comparison.png", bbox_inches="tight")
    plt.close(fig)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("screen", "validation", "locked", "full"))
    args = parser.parse_args()
    rows = analyze(args.phase)
    for row in rows:
        mc = row["monte_carlo"]
        print(
            f"{row['case']:<20} ret={row['return_pct']:+8.2f}% PF={row['profit_factor']:.2f} "
            f"WR={row['win_rate_pct']:.2f}% DD={row['max_dd_pct']:.2f}% n={row['trades']:4d} "
            f"Sharpe={row['sharpe']:.2f} Rec={row['recovery_factor']:.2f} "
            f"MC-P5={mc['p5_final_return_pct']:+.2f}% gate={'PASS' if row['passes_research_gate'] else 'fail'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
