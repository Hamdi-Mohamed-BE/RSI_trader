from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent
ASSET_ORDER = ("xauusd", "xagusd", "ustec", "eurusd", "btcusd")


def read_report(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def match(text: str, pattern: str, default: str = "0") -> str:
    found = re.search(pattern, text)
    return found.group(1).strip() if found else default


def number(value: str) -> float:
    cleaned = value.replace("\xa0", "").replace(" ", "").replace(",", "")
    return float(cleaned) if cleaned and cleaned != "-" else 0.0


def parse_report(path: Path, meta: dict) -> dict:
    soup = BeautifulSoup(read_report(path), "html.parser")
    text = " ".join(soup.get_text(" ").split())
    initial = number(match(text, r"Initial Deposit:\s*([\d .]+?)\s+Leverage:"))
    net = number(match(text, r"Total Net Profit:\s*([-\d .]+?)\s+Balance Drawdown Absolute:"))
    gross_profit = number(match(text, r"Gross Profit:\s*([-\d .]+?)\s+Balance Drawdown Maximal:"))
    gross_loss = number(match(text, r"Gross Loss:\s*([-\d .]+?)\s+Balance Drawdown Relative:"))
    dd_amount = number(match(text, r"Equity Drawdown Maximal:\s*([-\d .]+?)\s*\("))
    dd_pct = float(match(text, r"Equity Drawdown Maximal:\s*[-\d .]+\s*\(([\d.]+)%\)"))
    pf = float(match(text, r"Profit Factor:\s*([\d.]+)"))
    trades = int(match(text, r"Total Trades:\s*(\d+)"))
    wins = int(match(text, r"Profit Trades \(% of total\):\s*(\d+)"))
    losses = int(match(text, r"Loss Trades \(% of total\):\s*(\d+)"))
    win_rate = float(match(text, r"Profit Trades \(% of total\):\s*\d+\s*\(([\d.]+)%\)"))
    sharpe = float(match(text, r"Sharpe Ratio:\s*([-\d.]+)"))
    recovery = float(match(text, r"Recovery Factor:\s*([-\d.]+)"))
    quality = float(match(text, r"History Quality:\s*([\d.]+)%"))
    bars = int(match(text, r"Bars:\s*(\d+)"))

    series = [{"date": meta["from"].replace(".", "-"), "balance": initial}]
    entries: dict[str, list[dict]] = {}
    trade_returns: list[float] = []
    in_deals = False
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
        deal_type = cells[3].lower()
        if deal_type == "balance":
            continue
        symbol = cells[2]
        direction = cells[4].lower()
        volume = number(cells[5])
        commission = number(cells[8])
        swap = number(cells[9])
        profit = number(cells[10])
        if symbol and deal_type in {"buy", "sell"}:
            if direction in {"in", "in/out"}:
                entries.setdefault(symbol, []).append({"volume": volume, "remaining": volume, "costs": commission + swap + profit})
            if direction in {"out", "out by", "in/out"}:
                remaining_exit = volume
                queue = entries.get(symbol, [])
                while remaining_exit > 1e-9 and queue:
                    entry = queue[0]
                    matched = min(remaining_exit, float(entry["remaining"]))
                    exit_share = matched / volume if volume > 0 else 1.0
                    entry_share = matched / float(entry["volume"]) if float(entry["volume"]) > 0 else 1.0
                    trade_returns.append((commission + swap + profit) * exit_share + float(entry["costs"]) * entry_share)
                    entry["remaining"] = float(entry["remaining"]) - matched
                    remaining_exit -= matched
                    if float(entry["remaining"]) <= 1e-9:
                        queue.pop(0)
        if cells[11].strip():
            balance = number(cells[11])
            if not series or abs(series[-1]["balance"] - balance) > 0.005:
                when = datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S").isoformat(sep=" ")
                series.append({"date": when, "balance": balance})
    final = initial + net
    if not series or abs(series[-1]["balance"] - final) > 0.005:
        series.append({"date": meta["to"].replace(".", "-"), "balance": final})
    return_pct = net / initial * 100 if initial else 0.0
    bounded_pf = min(max(pf, 0.05), 3.0)
    sample_penalty = 20.0 / math.sqrt(max(trades, 1))
    score = return_pct + 8.0 * (bounded_pf - 1.0) - 0.8 * dd_pct - sample_penalty
    if trades < 5 or quality < 90 or bars <= 0:
        score = -1e9
    return {
        **meta,
        "initial_balance": initial,
        "final_balance": final,
        "net_profit": net,
        "return_pct": return_pct,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": pf,
        "win_rate_pct": win_rate,
        "wins": wins,
        "losses": losses,
        "trades": trades,
        "max_drawdown_amount": dd_amount,
        "max_drawdown_pct": dd_pct,
        "sharpe_ratio": sharpe,
        "recovery_factor": recovery,
        "history_quality_pct": quality,
        "bars": bars,
        "selection_score": score,
        "series": series,
        "trade_returns": trade_returns,
    }


def save_rows(stage: str, rows: list[dict]) -> None:
    (ROOT / f"{stage.upper()} RESULTS.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    flat = [{key: value for key, value in row.items() if key not in {"series", "trade_returns"}} for row in rows]
    with (ROOT / f"{stage.upper()} RESULTS.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)


def plot_stage(stage: str, rows: list[dict]) -> None:
    chart_root = ROOT / "Charts"
    chart_root.mkdir(exist_ok=True)
    colors = {"buy-only": "#10b981", "sell-only": "#f97316", "two-sided": "#38bdf8"}
    for asset in ASSET_ORDER:
        group = [row for row in rows if row["asset"] == asset]
        if not group:
            continue
        fig, ax = plt.subplots(figsize=(11, 5.4), dpi=150)
        for row in group:
            dates = [datetime.fromisoformat(point["date"]) for point in row["series"]]
            balances = [point["balance"] for point in row["series"]]
            label = f"{row['direction']} {row['geometry']} {row['management']}: {row['return_pct']:+.1f}% / PF {row['profit_factor']:.2f} / DD {row['max_drawdown_pct']:.1f}% / n={row['trades']}"
            ax.plot(dates, balances, color=colors[row["direction"]], linewidth=1.6, alpha=0.78, label=label)
        ax.axhline(10000, color="#94a3b8", linewidth=0.8, linestyle="--")
        ax.grid(True, alpha=0.18)
        ax.spines[["top", "right"]].set_visible(False)
        locator = mdates.AutoDateLocator(minticks=4, maxticks=8)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        ax.set_title(f"News Pulse {asset.upper()} — {stage}")
        ax.set_ylabel("Balance (USD)")
        ax.legend(fontsize=7, ncol=2)
        fig.tight_layout()
        fig.savefig(chart_root / f"{stage}-{asset}.png", bbox_inches="tight")
        plt.close(fig)


def select_calibration(rows: list[dict]) -> None:
    picks = []
    for asset in ASSET_ORDER:
        best = max((row for row in rows if row["asset"] == asset), key=lambda row: row["selection_score"])
        picks.append({"asset": asset, "direction": best["direction"], "geometry": best["geometry"], "entry_offset": best["entry_offset"], "stop_distance": best["stop_distance"], "trail_distance": best["trail_distance"], "calibration_return_pct": best["return_pct"], "calibration_profit_factor": best["profit_factor"], "calibration_drawdown_pct": best["max_drawdown_pct"], "calibration_trades": best["trades"], "selection_score": best["selection_score"]})
    (ROOT / "CALIBRATION SELECTION.json").write_text(json.dumps(picks, indent=2), encoding="utf-8")


def select_management(rows: list[dict]) -> None:
    picks = []
    for asset in ASSET_ORDER:
        best = max((row for row in rows if row["asset"] == asset), key=lambda row: row["selection_score"])
        picks.append({"asset": asset, "symbol": best["symbol"], "direction": best["direction"], "geometry": best["geometry"], "entry_offset": best["entry_offset"], "stop_distance": best["stop_distance"], "trail_distance": best["trail_distance"], "management": best["management"], "dynamic": best["dynamic"], "close_seconds": best["close_seconds"], "development_return_pct": best["return_pct"], "development_profit_factor": best["profit_factor"], "development_drawdown_pct": best["max_drawdown_pct"], "development_trades": best["trades"], "selection_score": best["selection_score"]})
    (ROOT / "DEVELOPMENT SELECTION.json").write_text(json.dumps(picks, indent=2), encoding="utf-8")


def quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def monte_carlo(row: dict, samples: int = 10000) -> dict:
    outcomes = [value for value in row["trade_returns"] if abs(value) > 0.01]
    if not outcomes:
        return {"paths": samples, "probability_profitable_pct": 0.0, "return_p5_pct": 0.0, "return_median_pct": 0.0, "return_p95_pct": 0.0, "max_dd_p95_pct": 0.0}
    rng = random.Random(20260905 + len(outcomes))
    returns, drawdowns = [], []
    for _ in range(samples):
        balance = peak = 10000.0
        worst = 0.0
        for _ in outcomes:
            balance += rng.choice(outcomes)
            peak = max(peak, balance)
            worst = max(worst, (peak - balance) / peak * 100 if peak > 0 else 100.0)
        returns.append((balance / 10000 - 1) * 100)
        drawdowns.append(worst)
    return {"paths": samples, "probability_profitable_pct": sum(value > 0 for value in returns) / samples * 100, "return_p5_pct": quantile(returns, 0.05), "return_median_pct": quantile(returns, 0.50), "return_p95_pct": quantile(returns, 0.95), "max_dd_p95_pct": quantile(drawdowns, 0.95)}


def plot_final_comparison(rows: list[dict]) -> None:
    labels = [row["symbol"] for row in rows]
    colors = ["#38bdf8", "#a78bfa", "#10b981", "#f59e0b", "#f43f5e"]
    metrics = (
        ("return_pct", "Return (%)"),
        ("profit_factor", "Profit factor"),
        ("win_rate_pct", "Win rate (%)"),
        ("max_drawdown_pct", "Max drawdown (%)"),
    )
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), dpi=160)
    for ax, (key, title) in zip(axes.flat, metrics):
        values = [row[key] for row in rows]
        bars = ax.barh(labels, values, color=colors, alpha=0.88)
        ax.set_title(title)
        ax.grid(axis="x", alpha=0.18)
        ax.spines[["top", "right"]].set_visible(False)
        for bar, value in zip(bars, values):
            ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2, f" {value:.2f}", va="center", fontsize=8)
    fig.suptitle("News Pulse — selected one-year configurations (1% risk per enabled side)", fontsize=14)
    fig.tight_layout()
    fig.savefig(ROOT / "Charts" / "FINAL COMPARISON.png", bbox_inches="tight")
    plt.close(fig)


def finalize() -> None:
    stage_names = ("calibration", "management", "locked", "full", "stress")
    paths = {stage: ROOT / f"{stage.upper()} RESULTS.json" for stage in stage_names}
    if not all(path.is_file() for path in paths.values()):
        return
    stages = {stage: json.loads(path.read_text(encoding="utf-8")) for stage, path in paths.items()}
    if any("trade_returns" not in row for rows in stages.values() for row in rows):
        return
    selection = json.loads((ROOT / "DEVELOPMENT SELECTION.json").read_text(encoding="utf-8"))
    mc = {row["asset"]: monte_carlo(row) for row in stages["full"]}
    plot_final_comparison(stages["full"])
    payload = {"test_design": {"calibration_and_management": "2025-09-01 to 2026-05-31", "locked": "2026-06-01 to 2026-09-01", "full": "2025-09-01 to 2026-09-01", "risk_per_enabled_side_pct": 1.0, "model": "MT5 Every Tick with Exness broker costs", "note": "Two-sided mode can risk up to approximately 2% per event."}, "selection": selection, "stages": stages, "monte_carlo": mc}
    (ROOT / "FINAL AUDIT.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = ["# Step 8 — News Pulse multi-market audit", "", "The EA already contained independent buy/sell switches and real BuyStop/SellStop execution. This audit calibrates absolute price distances separately for each market and keeps risk fixed at 1% per enabled side.", "", "## Selected configurations", "", "| Market | Direction | Entry / stop | Management | Development return / PF / trades | Locked return / PF / trades | Full return | PF | Win rate | Max DD | Trades | Sharpe | Recovery | Random-delay return / PF |", "|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for asset in ASSET_ORDER:
        full = next(row for row in stages["full"] if row["asset"] == asset)
        dev = next(row for row in stages["management"] if row["asset"] == asset and row["management"] == full["management"])
        locked = next(row for row in stages["locked"] if row["asset"] == asset)
        stress = next(row for row in stages["stress"] if row["asset"] == asset)
        lines.append(f"| {full['symbol']} | {full['direction']} | {full['entry_offset']:g} / {full['stop_distance']:g} | {full['management']} | {dev['return_pct']:+.2f}% / {dev['profit_factor']:.2f} / {dev['trades']} | {locked['return_pct']:+.2f}% / {locked['profit_factor']:.2f} / {locked['trades']} | {full['return_pct']:+.2f}% | {full['profit_factor']:.2f} | {full['win_rate_pct']:.2f}% | {full['max_drawdown_pct']:.2f}% | {full['trades']} | {full['sharpe_ratio']:.2f} | {full['recovery_factor']:.2f} | {stress['return_pct']:+.2f}% / {stress['profit_factor']:.2f} |")
    lines.extend(["", "## Monte Carlo — 10,000 closed-trade resamples", "", "| Market | Probability profitable | Return P5 | Median return | Return P95 | P95 max DD |", "|---|---:|---:|---:|---:|---:|"])
    for asset in ASSET_ORDER:
        result = mc[asset]
        lines.append(f"| {asset.upper()} | {result['probability_profitable_pct']:.1f}% | {result['return_p5_pct']:+.2f}% | {result['return_median_pct']:+.2f}% | {result['return_p95_pct']:+.2f}% | {result['max_dd_p95_pct']:.2f}% |")
    lines.extend([
        "", "## Deployment decision", "",
        "| Market | Decision | Reason |", "|---|---|---|",
        "| XAUUSD | Keep the existing long-only preset as the production default; demo-test this two-sided preset | The candidate lifts return to +79.02%, but PF falls to 9.02, DD rises to 2.39%, and simultaneous two-sided exposure can approach 2%. The current long-only system is +62.39%, PF 40.78, DD 1.46%, 19 trades. |",
        "| XAGUSD | Demo forward only | Excellent historical and random-delay results, but +366.10% from 37 one-minute news trades is too execution-sensitive to treat as a live expectation. |",
        "| USTEC | Demo forward | Buy-only is the cleanest selection and remains profitable under random delay; the sample is still only 22 trades. |",
        "| EURUSD | Demo forward | Two-sided result is strong in development, locked data, and random delay, but live news spread and rejection risk remain material. |",
        "| BTCUSD | Reject / do not promote | PF 1.56, DD 8.44%, recovery 0.70, and Monte Carlo P5 is -5.42%. |",
        "", "No BAT or website preset is promoted by this research step. Promotion should follow a review and demo-forward check, especially for XAGUSD and EURUSD.",
        "", "## Evidence limits", "",
        "- The Strategy Tester cannot query MT5's live economic calendar. The current EA contains an explicit NFP/CPI/FOMC tester schedule for this audited year only; pretending this is a three-year test would be misleading.",
        "- The locked period is only three months and event counts are small. Large PF values are not stable expectations.",
        "- MT5's reported Sharpe ratios are mechanically inflated for sparse trades that last about one minute, so they are displayed for completeness but were not used as the promotion criterion.",
        "- News execution is gap-, spread- and latency-sensitive. Random-delay testing still cannot reproduce every live rejection or spread shock.",
        "- Two-sided mode keeps 1% risk per triggered side and can therefore expose roughly 2% around one release before slippage."
    ])
    (ROOT / "FINAL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=("Calibration", "Management", "Locked", "Full", "Stress"))
    args = parser.parse_args()
    stage = args.stage.lower()
    manifest_path = ROOT / "Backtest Reports" / args.stage / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if isinstance(manifest, dict):
        manifest = [manifest]
    rows = [parse_report(Path(item["report"]), item) for item in manifest]
    save_rows(stage, rows)
    plot_stage(stage, rows)
    if args.stage == "Calibration":
        select_calibration(rows)
    elif args.stage == "Management":
        select_management(rows)
    finalize()
    for row in rows:
        print(f"{row['symbol']:7} {row['direction']:10} {row['geometry']:5} {row['management']:9} ret={row['return_pct']:+7.2f}% PF={row['profit_factor']:6.2f} win={row['win_rate_pct']:6.2f}% DD={row['max_drawdown_pct']:5.2f}% n={row['trades']:2}")


if __name__ == "__main__":
    main()
