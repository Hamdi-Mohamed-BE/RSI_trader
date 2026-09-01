from __future__ import annotations

import csv
import json
import math
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent


def number(value: str) -> float:
    value = value.replace("\xa0", " ").replace(" ", "").replace(",", "")
    return float(value) if value and value != "-" else 0.0


def found(text: str, pattern: str, default="0") -> str:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else default


def report_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def parse(meta: dict) -> dict:
    path = Path(meta["report"])
    soup = BeautifulSoup(report_text(path), "html.parser")
    text = " ".join(soup.get_text(" ").split())
    initial = number(found(text, r"Initial Deposit:\s*([\d .]+?)\s+Leverage:"))
    net = number(found(text, r"Total Net Profit:\s*([-\d .]+?)\s+Balance Drawdown Absolute:"))
    pf = float(found(text, r"Profit Factor:\s*([\d.]+)"))
    dd_amount = number(found(text, r"Equity Drawdown Maximal:\s*([-\d .]+?)\s*\("))
    dd_pct = float(found(text, r"Equity Drawdown Maximal:\s*[-\d .]+\s*\(([\d.]+)%\)"))
    trades = int(found(text, r"Total Trades:\s*(\d+)"))
    wins = int(found(text, r"Profit Trades \(% of total\):\s*(\d+)"))
    win_rate = float(found(text, r"Profit Trades \(% of total\):\s*\d+\s*\(([\d.]+)%\)"))
    quality = float(found(text, r"History Quality:\s*([\d.]+)%"))
    commission = swap = 0.0
    series = [(datetime.strptime(meta["from"], "%Y.%m.%d"), initial)]
    daily = {}
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
        when = datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S")
        commission += number(cells[8])
        swap += number(cells[9])
        pnl = number(cells[8]) + number(cells[9]) + number(cells[10])
        daily[when.date().isoformat()] = daily.get(when.date().isoformat(), 0.0) + pnl
        if cells[11].strip():
            balance = number(cells[11])
            if series[-1][1] != balance:
                series.append((when, balance))
    final = initial + net
    if series[-1][1] != final:
        series.append((datetime.strptime(meta["to"], "%Y.%m.%d"), final))
    min_balance = min(value for _, value in series)
    return {
        **meta, "initial": initial, "final": final, "net": net,
        "return_pct": net / initial * 100 if initial else 0,
        "pf": pf, "win_rate": win_rate, "dd_amount": dd_amount,
        "dd_pct": dd_pct, "trades": trades, "wins": wins,
        "commission": commission, "swap": swap, "quality": quality,
        "min_balance": min_balance,
        "survived": min_balance > 0 and final > 0 and quality >= 90,
        "series": [(d.isoformat(sep=" "), v) for d, v in series],
        "daily": daily,
    }


def serial(row):
    return {k: v for k, v in row.items() if k not in ("series", "daily")}


def save_rows(stage: str, rows: list[dict]):
    (ROOT / f"{stage.lower()}-results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    flat = [serial(row) for row in rows]
    with (ROOT / f"{stage.lower()}-results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat[0]))
        writer.writeheader(); writer.writerows(flat)


def development(rows: list[dict]):
    eligible = [r for r in rows if r["survived"] and r["net"] > 0 and r["pf"] > 1 and r["trades"] >= 250]
    for r in eligible:
        initial_dip = max(0.0, r["initial"] - r["min_balance"])
        r["selection_score"] = r["net"] - 3.0 * r["dd_amount"] - 10.0 * initial_dip + 25.0 * math.log(max(r["pf"], .01))
    picks = sorted(eligible, key=lambda r: r["selection_score"], reverse=True)[:8]
    selection = [{"id": r["id"], "development_score": r["selection_score"]} for r in picks]
    (ROOT / "development-selection.json").write_text(json.dumps(selection, indent=2), encoding="utf-8")
    for r in picks:
        print(f"{r['id']:<28} net=${r['net']:>9.2f} PF={r['pf']:.2f} WR={r['win_rate']:.2f}% DD={r['dd_pct']:.2f}% min=${r['min_balance']:.2f} trades={r['trades']}")


def locked(rows: list[dict]):
    dev = {r["id"]: r for r in json.loads((ROOT / "development-results.json").read_text(encoding="utf-8"))}
    robust = []
    for row in rows:
        prior = dev[row["id"]]
        if row["survived"] and row["net"] > 0 and row["pf"] > 1 and prior["net"] > 0 and prior["pf"] > 1:
            row["robust_score"] = min(prior["net"], row["net"]) - 2.5 * max(prior["dd_amount"], row["dd_amount"]) + 20 * math.log(min(prior["pf"], row["pf"]))
            robust.append(row)
    winner = max(robust, key=lambda r: r["robust_score"]) if robust else max(rows, key=lambda r: r["net"])
    (ROOT / "winner.json").write_text(json.dumps({"id": winner["id"]}, indent=2), encoding="utf-8")
    for r in sorted(rows, key=lambda x: x["net"], reverse=True):
        print(f"{r['id']:<28} net=${r['net']:>9.2f} PF={r['pf']:.2f} WR={r['win_rate']:.2f}% DD={r['dd_pct']:.2f}% min=${r['min_balance']:.2f} trades={r['trades']}")
    print("WINNER", winner["id"])


def bootstrap(daily: dict, start_text: str, end_text: str, trials=20000):
    start = datetime.strptime(start_text, "%Y.%m.%d").date()
    end = datetime.strptime(end_text, "%Y.%m.%d").date()
    values_list = []
    current = start
    while current <= end:
        values_list.append(daily.get(current.isoformat(), 0.0))
        current += timedelta(days=1)
    values = np.array(values_list, dtype=float)
    if len(values) == 0:
        return {"median": 0, "p10": 0, "p90": 0, "loss_probability": 1}
    rng = np.random.default_rng(864050)
    draws = rng.choice(values, size=(trials, 30), replace=True).sum(axis=1)
    return {"median": float(np.median(draws)), "mean": float(np.mean(draws)), "p10": float(np.percentile(draws, 10)), "p90": float(np.percentile(draws, 90)), "loss_probability": float(np.mean(draws < 0) * 100)}


def final_report(row: dict):
    dev = next(r for r in json.loads((ROOT / "development-results.json").read_text(encoding="utf-8")) if r["id"] == row["id"])
    locked = next(r for r in json.loads((ROOT / "locked-results.json").read_text(encoding="utf-8")) if r["id"] == row["id"])
    projection = bootstrap(locked["daily"], locked["from"], locked["to"])
    (ROOT / "next-month-estimate.json").write_text(json.dumps(projection, indent=2), encoding="utf-8")
    fig, ax = plt.subplots(figsize=(11, 5.5), dpi=150)
    dates = [datetime.fromisoformat(d) for d, _ in row["series"]]
    values = [v for _, v in row["series"]]
    ax.plot(dates, values, color="#10b981", lw=1.5)
    ax.axhline(50, color="#64748b", ls="--", lw=.9, label="$50 initial balance")
    ax.set_title(f"OCO $50 study — {row['id']} — 01 Jul to 31 Aug 2026")
    ax.set_ylabel("Realized balance (USD)")
    ax.grid(alpha=.2); ax.spines[["top", "right"]].set_visible(False)
    locator = mdates.AutoDateLocator(minticks=4, maxticks=9)
    ax.xaxis.set_major_locator(locator); ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.legend(); fig.tight_layout(); fig.savefig(ROOT / "OCO 50 USD equity.png", bbox_inches="tight"); plt.close(fig)
    lines = [
        "# OCO small-balance audit — $50",
        "", "## Decision", "",
        f"Selected configuration: **{row['id']}**. It survived both months in this MT5 test, but live OCO execution can be materially worse.",
        "", "## Results", "",
        "| Period | Net | Final | PF | Win rate | Max equity DD | Minimum balance | Trades | Commission |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, r in (("July development", dev), ("August locked", locked), ("Two months", row)):
        lines.append(f"| {label} | ${r['net']:,.2f} | ${r['final']:,.2f} | {r['pf']:.2f} | {r['win_rate']:.2f}% | {r['dd_pct']:.2f}% | ${r['min_balance']:,.2f} | {r['trades']:,} | ${r['commission']:,.2f} |")
    lines += [
        "", "## Exact setting", "",
        f"- Entry offset: ${row['offset']:.2f}", f"- Initial stop: ${row['stop']:.2f}",
        f"- Trail starts: ${row['trail_start']:.2f}", f"- Trail distance: ${row['trail_distance']:.2f}",
        f"- Session: {'all hours' if not row['use_session'] else f'{row['session_start']:02d}:00-{row['session_end']:02d}:00 UTC'}",
        f"- Direction: {'both' if row['long'] and row['short'] else 'long only' if row['long'] else 'short only'}",
        "- Fixed lot: 0.01; no equity scaling; one open position maximum; no martingale.",
        "", "## Next 30-day statistical estimate", "",
        f"Bootstrap median: **${projection['median']:,.2f}** net; 10th-90th percentile: **${projection['p10']:,.2f} to ${projection['p90']:,.2f}**; sampled probability of a losing month: **{projection['loss_probability']:.2f}%**.",
        "This is a resampling of August daily P&L, not a forecast or guarantee. Live latency, rejected/cancelled orders, simultaneous fills and broker throttling are not reproduced perfectly.",
    ]
    (ROOT / "FULL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("FINAL", row["id"], projection)


def main():
    stage = sys.argv[1]
    manifest = json.loads((ROOT / "Reports" / stage / "manifest.json").read_text(encoding="utf-8-sig"))
    if isinstance(manifest, dict): manifest = [manifest]
    rows = [parse(meta) for meta in manifest]
    save_rows(stage, rows)
    if stage == "Development": development(rows)
    elif stage == "Locked": locked(rows)
    else: final_report(rows[0])


if __name__ == "__main__":
    main()
