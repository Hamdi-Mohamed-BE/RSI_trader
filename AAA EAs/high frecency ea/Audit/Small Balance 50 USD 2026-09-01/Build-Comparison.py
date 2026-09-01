from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent


def one(path: str):
    data = json.loads((ROOT / path).read_text(encoding="utf-8"))
    return data[0] if isinstance(data, list) else data


def calendar_bootstrap(row: dict, trials=30000):
    start = datetime.strptime(row["from"], "%Y.%m.%d").date()
    end = datetime.strptime(row["to"], "%Y.%m.%d").date()
    daily = row["daily"]
    values = []
    current = start
    while current <= end:
        values.append(daily.get(current.isoformat(), 0.0))
        current += timedelta(days=1)
    rng = np.random.default_rng(864050)
    draws = rng.choice(np.array(values), size=(trials, 30), replace=True).sum(axis=1)
    return {
        "median": float(np.median(draws)),
        "p10": float(np.percentile(draws, 10)),
        "p90": float(np.percentile(draws, 90)),
        "loss_probability_pct": float(np.mean(draws < 0) * 100),
    }


max_profit = one("max-profit-results.json")
safe = one("safe-results.json")
locked = {row["id"]: row for row in json.loads((ROOT / "locked-results.json").read_text(encoding="utf-8"))}
estimates = {
    "max_profit": calendar_bootstrap(locked[max_profit["id"]]),
    "safe": calendar_bootstrap(locked[safe["id"]]),
}
(ROOT / "next-month-comparison.json").write_text(json.dumps(estimates, indent=2), encoding="utf-8")

colors = {"Max profit": "#f59e0b", "Safer": "#10b981"}
fig, axes = plt.subplots(2, 1, figsize=(11.5, 8.2), dpi=160, sharex=True)
for label, row in (("Max profit", max_profit), ("Safer", safe)):
    dates = [datetime.fromisoformat(item[0]) for item in row["series"]]
    balances = [item[1] for item in row["series"]]
    for ax in axes:
        ax.plot(dates, balances, lw=1.35, color=colors[label], label=f"{label}: ${row['final']:,.2f}, PF {row['pf']:.2f}")
for ax in axes:
    ax.axhline(50, color="#64748b", ls="--", lw=.9)
    ax.grid(alpha=.18)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left")
axes[0].set_title("OCO $50 audit — continuous MT5 Every Tick balance curves")
axes[0].set_ylabel("Balance (USD), linear")
axes[1].set_yscale("log")
axes[1].set_ylabel("Balance (USD), log scale")
locator = mdates.AutoDateLocator(minticks=5, maxticks=9)
axes[1].xaxis.set_major_locator(locator)
axes[1].xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
fig.tight_layout()
fig.savefig(ROOT / "OCO 50 USD comparison.png", bbox_inches="tight")
plt.close(fig)

ranking = sorted(locked.values(), key=lambda row: row["net"], reverse=True)
lines = [
    "# OCO $50 final comparison",
    "",
    "## Recommendation",
    "",
    "Use **literal NY-full** for a demo/cent-account trial. It gives up headline profit in exchange for materially fewer trades, higher PF and win rate, and lower peak-relative drawdown. Do not treat either backtest as a reliable live-income forecast: the edge depends on sub-dollar XAUUSD moves and extremely frequent pending-order changes.",
    "",
    "## Continuous two-month results — 01 July to 31 August 2026",
    "",
    "| Option | Final | Net | PF | Win rate | Max equity DD | Minimum realized balance | Trades | Commission |",
    "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
]
for label, row in (("Max profit — all hours", max_profit), ("Recommended safer — 13:00-21:00 UTC", safe)):
    lines.append(f"| {label} | ${row['final']:,.2f} | ${row['net']:,.2f} | {row['pf']:.2f} | {row['win_rate']:.2f}% | {row['dd_pct']:.2f}% (${row['dd_amount']:,.2f}) | ${row['min_balance']:,.2f} | {row['trades']:,} | ${row['commission']:,.2f} |")
lines += [
    "",
    "## Recommended exact settings",
    "",
    "- XAUUSD M1; current-price OCO; both long and short.",
    "- Fixed lot 0.01; equity scaling off; one position maximum; no martingale.",
    "- Entry offset $0.40; initial SL $0.50.",
    "- Start trailing after $0.80 favorable movement; trail $0.45 behind price.",
    "- Session filter on: 13:00-21:00 UTC.",
    "- Maximum spread $0.50; replace unfilled OCO orders on each new M1 candle; maximum hold 180 minutes.",
    "",
    "## August validation finalists",
    "",
    "| Candidate | Net | PF | Win rate | Max DD | Minimum balance | Trades |",
    "|---|---:|---:|---:|---:|---:|---:|",
]
for row in ranking:
    lines.append(f"| {row['id']} | ${row['net']:,.2f} | {row['pf']:.2f} | {row['win_rate']:.2f}% | {row['dd_pct']:.2f}% | ${row['min_balance']:,.2f} | {row['trades']:,} |")
lines += [
    "",
    "## Next 30-calendar-day model-only estimate",
    "",
    f"- Recommended safer setup: median **${estimates['safe']['median']:,.2f}** net; 10th-90th percentile **${estimates['safe']['p10']:,.2f} to ${estimates['safe']['p90']:,.2f}**.",
    f"- Maximum-profit setup: median **${estimates['max_profit']['median']:,.2f}** net; 10th-90th percentile **${estimates['max_profit']['p10']:,.2f} to ${estimates['max_profit']['p90']:,.2f}**.",
    "",
    "These are bootstrap resamples of August daily tester P&L with weekend/no-trade days included. They are not credible cash forecasts until forward execution confirms cancellation latency, slippage, rejected modifications, simultaneous fills and broker order-rate tolerance. A defensible live expectation is therefore **unknown**, not the bootstrap median.",
    "",
    "## Method",
    "",
    "- July screened 31 parameter combinations; August tested only the eight July survivors.",
    "- Continuous two-month reruns used $50 initial balance, 0.01 fixed lot, Exness XAUUSD, MT5 Every Tick, 100% reported history quality, broker spread, random execution delay, commission and swap.",
    "- Active BAT and website were not changed.",
]
(ROOT / "FINAL COMPARISON.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps(estimates, indent=2))
