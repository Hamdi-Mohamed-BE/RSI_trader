from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
SESSION_NAMES = {0: "all", 1: "asia", 2: "london", 3: "new-york", 4: "overlap"}


def clean_number(value: str) -> float:
    value = value.replace("\xa0", " ").replace(" ", "").replace(",", "")
    return float(value) if value and value != "-" else 0.0


def match(text: str, pattern: str, default: str = "0") -> str:
    found = re.search(pattern, text)
    return found.group(1).strip() if found else default


def read_report(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def parse_report(path: Path, meta: dict) -> dict:
    soup = BeautifulSoup(read_report(path), "html.parser")
    text = " ".join(soup.get_text(" ").split())
    initial = clean_number(match(text, r"Initial Deposit:\s*([\d .]+?)\s+Leverage:"))
    net = clean_number(match(text, r"Total Net Profit:\s*([-\d .]+?)\s+Balance Drawdown Absolute:"))
    gross_profit = clean_number(match(text, r"Gross Profit:\s*([-\d .]+?)\s+Balance Drawdown Maximal:"))
    gross_loss = clean_number(match(text, r"Gross Loss:\s*([-\d .]+?)\s+Balance Drawdown Relative:"))
    equity_dd_amount = clean_number(match(text, r"Equity Drawdown Maximal:\s*([-\d .]+?)\s*\("))
    equity_dd_pct = float(match(text, r"Equity Drawdown Maximal:\s*[-\d .]+\s*\(([\d.]+)%\)"))
    balance_dd_amount = clean_number(match(text, r"Balance Drawdown Maximal:\s*([-\d .]+?)\s*\("))
    balance_dd_pct = float(match(text, r"Balance Drawdown Maximal:\s*[-\d .]+\s*\(([\d.]+)%\)"))
    profit_factor = float(match(text, r"Profit Factor:\s*([\d.]+)"))
    trades = int(match(text, r"Total Trades:\s*(\d+)"))
    wins = int(match(text, r"Profit Trades \(% of total\):\s*(\d+)"))
    losses = int(match(text, r"Loss Trades \(% of total\):\s*(\d+)"))
    win_rate = float(match(text, r"Profit Trades \(% of total\):\s*\d+\s*\(([\d.]+)%\)"))
    quality = float(match(text, r"History Quality:\s*([\d.]+)%"))
    bars = int(match(text, r"Bars:\s*(\d+)"))
    ticks = int(match(text, r"Ticks:\s*(\d+)"))
    period = match(text, r"Period:\s*(.*?)\s+Inputs:", "unknown")
    dates = re.search(r"\((\d{4}\.\d{2}\.\d{2})\s*-\s*(\d{4}\.\d{2}\.\d{2})\)", period)
    start_date = dates.group(1).replace(".", "-") if dates else meta["From"].replace(".", "-")
    end_date = dates.group(2).replace(".", "-") if dates else meta["To"].replace(".", "-")
    commission = 0.0
    swap = 0.0
    series = [{"date": start_date, "balance": initial}]
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
        if cells[3].lower() == "balance":
            continue
        commission += clean_number(cells[8])
        swap += clean_number(cells[9])
        if cells[11].strip():
            balance = clean_number(cells[11])
            if not series or series[-1]["balance"] != balance:
                when = datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S").isoformat(sep=" ")
                series.append({"date": when, "balance": balance})
    final_balance = initial + net
    if not series or series[-1]["balance"] != final_balance:
        series.append({"date": end_date, "balance": final_balance})
    return_pct = net / initial * 100.0 if initial else 0.0
    score = return_pct - 1.25 * equity_dd_pct + 6.0 * math.log(max(profit_factor, 0.05))
    status = "valid" if quality >= 90 and bars > 0 else "invalid-data"
    return {
        **meta,
        "session": SESSION_NAMES[int(meta["SessionValue"])],
        "period_text": period,
        "history_quality_pct": quality,
        "bars": bars,
        "ticks": ticks,
        "initial_balance": initial,
        "final_balance": final_balance,
        "net_profit": net,
        "return_pct": return_pct,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "equity_dd_amount": equity_dd_amount,
        "equity_dd_pct": equity_dd_pct,
        "balance_dd_amount": balance_dd_amount,
        "balance_dd_pct": balance_dd_pct,
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "commission": commission,
        "swap": swap,
        "score": score,
        "status": status,
        "report": str(path),
        "series": series,
    }


def write_rows(path: Path, rows: list[dict]) -> None:
    serializable = [{key: value for key, value in row.items() if key != "series"} for row in rows]
    path.with_suffix(".json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    fields = list(serializable[0]) if serializable else []
    with path.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(serializable)


def select_sessions(results: list[dict]) -> list[dict]:
    picks = []
    for ea_id in sorted({row["EaId"] for row in results}):
        group = [row for row in results if row["EaId"] == ea_id and row["status"] == "valid"]
        baseline = next((row for row in group if row["session"] == "all"), None)
        if not baseline:
            continue
        minimum = max(5, math.ceil(baseline["trades"] * 0.35))
        eligible = [row for row in group if row["trades"] >= minimum]
        if not eligible:
            eligible = [baseline]
        best = max(eligible, key=lambda row: row["score"])
        picks.append({
            "ea_id": ea_id,
            "label": best["Label"],
            "symbol": best["Symbol"],
            "session": best["session"],
            "session_value": int(best["SessionValue"]),
            "development_return_pct": best["return_pct"],
            "development_pf": best["profit_factor"],
            "development_dd_pct": best["equity_dd_pct"],
            "development_trades": best["trades"],
            "baseline_trades": baseline["trades"],
            "minimum_trades_required": minimum,
            "score": best["score"],
        })
    (ROOT / "selection.json").write_text(json.dumps(picks, indent=2), encoding="utf-8")
    return picks


def role(row: dict) -> str:
    if row["Variant"] == "current":
        return "current"
    if row["Variant"] == "dynamic-only":
        return "dynamic-only"
    return "best-session-dynamic" if row["Dynamic"] else "best-session"


def series_points(row: dict):
    return [datetime.fromisoformat(point["date"]) for point in row["series"]], [point["balance"] for point in row["series"]]


def style_axis(ax):
    ax.grid(True, alpha=0.18)
    ax.spines[["top", "right"]].set_visible(False)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=8))
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))


def plot_per_ea(results: list[dict]) -> None:
    charts = ROOT / "Charts"
    charts.mkdir(exist_ok=True)
    colors = {"current": "#64748b", "dynamic-only": "#f59e0b", "best-session": "#38bdf8", "best-session-dynamic": "#10b981"}
    for ea_id in sorted({row["EaId"] for row in results}):
        group = [row for row in results if row["EaId"] == ea_id]
        fig, ax = plt.subplots(figsize=(11, 5.4), dpi=150)
        for row in group:
            dates, balances = series_points(row)
            r = role(row)
            label = f"{r}: {row['return_pct']:+.2f}% / PF {row['profit_factor']:.2f} / DD {row['equity_dd_pct']:.2f}%"
            ax.plot(dates, balances, label=label, linewidth=1.7, color=colors[r])
        ax.axhline(10000, color="#94a3b8", linewidth=0.8, linestyle="--")
        ax.set_title(f"{group[0]['Label']} — locked one-year realized balance")
        ax.set_ylabel("Balance (USD)")
        style_axis(ax)
        ax.legend(loc="best", fontsize=8)
        fig.tight_layout()
        fig.savefig(charts / f"{ea_id}.png", bbox_inches="tight")
        plt.close(fig)


def combined_curve(rows: list[dict]) -> tuple[list[datetime], list[float]]:
    events = []
    for row in rows:
        previous = row["initial_balance"]
        for point in row["series"][1:]:
            current = point["balance"]
            events.append((datetime.fromisoformat(point["date"]), current - previous))
            previous = current
    events.sort(key=lambda item: item[0])
    balance = 10000.0
    dates = [min((datetime.fromisoformat(row["series"][0]["date"]) for row in rows), default=datetime.now())]
    values = [balance]
    for when, delta in events:
        balance += delta
        dates.append(when)
        values.append(balance)
    return dates, values


def max_drawdown(values: list[float]) -> tuple[float, float]:
    peak = values[0]
    worst_amount = 0.0
    worst_pct = 0.0
    for value in values:
        peak = max(peak, value)
        amount = peak - value
        pct = amount / peak * 100.0 if peak > 0 else 0.0
        if pct > worst_pct:
            worst_pct = pct
            worst_amount = amount
    return worst_amount, worst_pct


def build_combined(results: list[dict]) -> list[dict]:
    roles = ["current", "dynamic-only", "best-session", "best-session-dynamic"]
    rows = []
    charts = ROOT / "Charts"
    colors = {"current": "#64748b", "dynamic-only": "#f59e0b", "best-session": "#38bdf8", "best-session-dynamic": "#10b981"}
    fig, ax = plt.subplots(figsize=(12, 6), dpi=160)
    for target in roles:
        group = [row for row in results if role(row) == target]
        dates, balances = combined_curve(group)
        dd_amount, dd_pct = max_drawdown(balances)
        gross_profit = sum(row["gross_profit"] for row in group)
        gross_loss = sum(row["gross_loss"] for row in group)
        net = sum(row["net_profit"] for row in group)
        trades = sum(row["trades"] for row in group)
        wins = sum(row["wins"] for row in group)
        pf = gross_profit / abs(gross_loss) if gross_loss < 0 else (999.0 if gross_profit > 0 else 0.0)
        rows.append({
            "role": target,
            "initial_balance": 10000.0,
            "final_balance": 10000.0 + net,
            "net_profit": net,
            "return_pct": net / 100.0,
            "profit_factor": pf,
            "win_rate": wins / trades * 100.0 if trades else 0.0,
            "trades": trades,
            "wins": wins,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "realized_dd_amount": dd_amount,
            "realized_dd_pct": dd_pct,
            "commission": sum(row["commission"] for row in group),
            "swap": sum(row["swap"] for row in group),
        })
        ax.plot(dates, balances, linewidth=2.0, label=f"{target}: {net/100:+.2f}%", color=colors[target])
    ax.axhline(10000, color="#94a3b8", linewidth=0.8, linestyle="--")
    ax.set_title("All active BAT EAs — arithmetic realized-balance comparison")
    ax.set_ylabel("Combined balance overlay (USD)")
    style_axis(ax)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(charts / "COMBINED - current vs session vs dynamic.png", bbox_inches="tight")
    plt.close(fig)
    return rows


def fmt_pct(value):
    return f"{value:+.2f}%"


def write_report(results: list[dict], combined: list[dict]) -> None:
    picks = json.loads((ROOT / "selection.json").read_text(encoding="utf-8"))
    selection = {pick["ea_id"]: pick for pick in picks}
    lines = [
        "# Dynamic Trailing SL + Session Filter Audit",
        "",
        "The live BAT and website were not changed. All variants were compiled as isolated per-EA research copies.",
        "",
        "Dynamic rule: after a completed M15 candle reaches 50% of the original entry-to-target distance (or 0.5R when no TP exists), move SL to lock 20% of that distance. Sessions are UTC: Asia 00:00–08:00, London 07:00–12:00, New York 13:00–21:00, overlap 13:00–16:00.",
        "",
        "## Combined arithmetic overlay",
        "",
        "| Variant | Return | PF | Win rate | Realized DD | Trades | Commission | Swap |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in combined:
        lines.append(f"| {row['role']} | {fmt_pct(row['return_pct'])} | {row['profit_factor']:.2f} | {row['win_rate']:.2f}% | {row['realized_dd_pct']:.2f}% | {row['trades']} | ${row['commission']:,.2f} | ${row['swap']:,.2f} |")
    lines += [
        "",
        "> Combined figures are a chronological arithmetic cash-flow overlay of separate EA tests, not a simultaneous shared-margin MT5 portfolio simulation.",
        "",
        "## Per-EA locked results",
        "",
        "| EA | Symbol | Best screened session | Variant | Return | PF | Win rate | Max equity DD | Trades |",
        "|---|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for ea_id in sorted({row["EaId"] for row in results}):
        for row in [r for r in results if r["EaId"] == ea_id]:
            lines.append(f"| {row['Label']} | {row['Symbol']} | {selection[ea_id]['session']} | {role(row)} | {fmt_pct(row['return_pct'])} | {row['profit_factor']:.2f} | {row['win_rate']:.2f}% | {row['equity_dd_pct']:.2f}% | {row['trades']} |")
    lines += [
        "",
        "## Methodology",
        "",
        "- Session choice used 2024-09-01 through 2025-08-31 with M1 OHLC modelling.",
        "- Locked comparison used 2025-09-01 through 2026-08-31 with MT5 Every Tick, random execution delay, broker spread, commission and swap.",
        "- A session needed at least five trades and at least 35% of the all-session trade count to qualify, limiting tiny-sample winners.",
        "- Dynamic trailing only acts on completed M15 candles; short-lived News Pulse positions therefore may be unaffected by design.",
    ]
    (ROOT / "FULL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"Development", "Locked"}:
        raise SystemExit("usage: Analyze-Reports.py Development|Locked")
    stage = sys.argv[1]
    report_dir = ROOT / "Backtest Reports" / stage
    manifest = json.loads((report_dir / "manifest.json").read_text(encoding="utf-8-sig"))
    results = []
    for meta in manifest:
        path = Path(meta["Report"])
        results.append(parse_report(path, meta))
    results.sort(key=lambda row: (row["EaId"], row["Variant"]))
    write_rows(ROOT / f"{stage.lower()}-results", results)
    if stage == "Development":
        picks = select_sessions(results)
        for pick in picks:
            print(f"{pick['label']:<34} {pick['session']:<9} return={pick['development_return_pct']:+7.2f}% PF={pick['development_pf']:.2f} DD={pick['development_dd_pct']:.2f}% trades={pick['development_trades']}")
    else:
        plot_per_ea(results)
        combined = build_combined(results)
        (ROOT / "combined-results.json").write_text(json.dumps(combined, indent=2), encoding="utf-8")
        with (ROOT / "combined-results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(combined[0]))
            writer.writeheader()
            writer.writerows(combined)
        write_report(results, combined)
        for row in combined:
            print(f"{row['role']:<22} return={row['return_pct']:+8.2f}% PF={row['profit_factor']:.2f} WR={row['win_rate']:.2f}% DD={row['realized_dd_pct']:.2f}% trades={row['trades']}")


if __name__ == "__main__":
    main()
