from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
PIPELINE = ROOT / "Run-ORB-H1-Pipeline.py"
spec = importlib.util.spec_from_file_location("h1_orb", PIPELINE)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load H1 ORB pipeline")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

audit = json.loads((ROOT / "FINAL AUDIT.json").read_text(encoding="utf-8"))
rr6 = json.loads((ROOT / "US100 RR6 VALIDATION.json").read_text(encoding="utf-8"))
rr_curve = json.loads((ROOT / "RR EXTENSION RESULTS.json").read_text(encoding="utf-8"))["rows"]

rr4_item = audit["symbols"]["ustec"]["anchors"]["overlap-1300"]
rr4_locked = rr4_item["locked"]
rr6_locked = rr6["locked"]
rr6_full = rr6["full"]
rr6_mc = rr6["monte_carlo"]

rr6_report = module.ORB.ANALYZER.parse_report(Path(rr6_locked["path"]))
rr4_report = module.ORB.ANALYZER.parse_report(Path(rr4_locked["path"]))
rr6_dates, rr6_balance = module.ORB.ANALYZER.equity_points(rr6_report, module.datetime(2025, 9, 1))
rr4_dates, rr4_balance = module.ORB.ANALYZER.equity_points(rr4_report, module.datetime(2025, 9, 1))
outcomes = module.ORB.ANALYZER.trade_outcomes(rr6_report["deals"])
wins = [value for value in outcomes if value > 0]
losses = [value for value in outcomes if value < 0]
average_win = sum(wins) / len(wins)
average_loss = sum(losses) / len(losses)
average_payoff = average_win / abs(average_loss)
expectancy = sum(outcomes) / len(outcomes)

audit["us100_rr6_extension"] = {
    "decision": "PASS / demo candidate",
    "locked": rr6_locked,
    "full": rr6_full,
    "monte_carlo": rr6_mc,
    "realized_payoff": {
        "average_win_usd": average_win,
        "average_loss_usd": average_loss,
        "average_win_loss_ratio": average_payoff,
        "expectancy_usd_per_trade": expectancy,
    },
}
(ROOT / "FINAL AUDIT.json").write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")

plt.style.use("dark_background")
fig, axes = plt.subplots(2, 2, figsize=(15, 9), dpi=180)
fig.patch.set_facecolor("#07110f")
for axis in axes.flat:
    axis.set_facecolor("#0b1714")
    axis.grid(color="#94a3b8", alpha=0.15)
    axis.spines[["top", "right"]].set_visible(False)

ax = axes[0, 0]
ax.step(rr4_dates, rr4_balance, where="post", color="#94a3b8", linewidth=1.2, label="4R finalist")
ax.step(rr6_dates, rr6_balance, where="post", color="#6ee7b7", linewidth=1.8, label="6R selected")
ax.axhline(10000, color="#64748b", linestyle="--", linewidth=0.8)
ax.set_title("US100 locked-year equity", loc="left", fontweight="bold")
ax.set_ylabel("USD")
ax.legend(frameon=False)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

ax = axes[0, 1]
labels = ["XAU\n13:00", "XAU\n09:30", "XAG\n18:00", "XAG\n00:00", "US100\n08:20", "US100\n13:00 6R"]
locked_rows = [
    audit["symbols"]["xauusd"]["anchors"]["overlap-1300"]["locked"],
    audit["symbols"]["xauusd"]["anchors"]["ny-cash-0930"]["locked"],
    audit["symbols"]["xagusd"]["anchors"]["futures-1800"]["locked"],
    audit["symbols"]["xagusd"]["anchors"]["asia-0000"]["locked"],
    audit["symbols"]["ustec"]["anchors"]["ny-metals-0820"]["locked"],
    rr6_locked,
]
x = np.arange(len(labels))
width = 0.36
colors = ["#ef4444" if row["return_pct"] <= 0 else "#38bdf8" for row in locked_rows[:-1]] + ["#6ee7b7"]
ax.bar(x - width / 2, [row["return_pct"] for row in locked_rows], width, color=colors, label="Return")
ax.bar(x + width / 2, [row["max_drawdown_pct"] for row in locked_rows], width, color="#f87171", alpha=0.75, label="Max DD")
ax.axhline(0, color="#64748b", linewidth=0.8)
ax.set_xticks(x, labels)
ax.set_ylabel("Percent")
ax.set_title("Untouched-year decision", loc="left", fontweight="bold")
ax.legend(frameon=False)
for index, row in enumerate(locked_rows):
    ax.text(index, max(row["return_pct"], 0), f"PF {row['profit_factor']:.2f}\nn={row['trades']}", ha="center", va="bottom", fontsize=7)

ax = axes[1, 0]
rr_values = [float(row["config"]["InpRewardRisk"]) for row in rr_curve]
returns = [float(row["return_pct"]) for row in rr_curve]
pfs = [float(row["profit_factor"]) for row in rr_curve]
ax.plot(rr_values, returns, marker="o", color="#6ee7b7", linewidth=2, label="Return %")
ax.set_xlabel("Nominal target (R)")
ax.set_ylabel("Return %", color="#6ee7b7")
ax.set_title("US100 development RR extension", loc="left", fontweight="bold")
ax2 = ax.twinx()
ax2.plot(rr_values, pfs, marker="s", color="#38bdf8", linewidth=1.6, label="PF")
ax2.set_ylabel("Profit factor", color="#38bdf8")
ax.axvline(6, color="#fbbf24", linestyle="--", linewidth=1, label="Selected 6R")
lines1, names1 = ax.get_legend_handles_labels()
lines2, names2 = ax2.get_legend_handles_labels()
ax.legend(lines1 + lines2, names1 + names2, frameon=False, loc="lower right")

ax = axes[1, 1]
fan = rr6_mc["fan"]
trades = [point["trade"] for point in fan]
ax.fill_between(trades, [point["p5"] for point in fan], [point["p95"] for point in fan], color="#6ee7b7", alpha=0.14, label="5–95%")
ax.fill_between(trades, [point["p25"] for point in fan], [point["p75"] for point in fan], color="#6ee7b7", alpha=0.30, label="25–75%")
ax.plot(trades, [point["p50"] for point in fan], color="#6ee7b7", linewidth=2, label="Median")
ax.set_title("US100 RR6 — 10,000-path Monte Carlo", loc="left", fontweight="bold")
ax.set_xlabel("Trade number")
ax.set_ylabel("USD")
ax.legend(frameon=False)
ax.text(0.03, 0.05,
        f"P(profit) {rr6_mc['probability_profitable_pct']:.1f}%\n"
        f"Return P5 {rr6_mc['return_p5_pct']:+.2f}%\n"
        f"P95 DD {rr6_mc['max_dd_p95_pct']:.2f}%\nRuin {rr6_mc['ruin_probability_pct']:.2f}%",
        transform=ax.transAxes, fontsize=9, color="#d1fae5")

fig.suptitle("One-hour ORB — final validation", fontsize=19, fontweight="bold", y=0.99)
fig.text(0.5, 0.957, "XAUUSD · XAGUSD · USTEC · MT5 Every Tick · fixed 1% risk · costs + random delay",
         ha="center", color="#94a3b8", fontsize=9)
fig.tight_layout(rect=(0, 0, 1, 0.93))
chart = module.ORB.CHARTS / "H1 ORB FINAL DECISION AND MONTE CARLO.png"
fig.savefig(chart, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close(fig)

report = f"""# One-Hour Opening Range Breakout — Final Audit

## Decision

**US100 passes for demo-forward testing. XAU and XAG do not pass the untouched-year validation.** Do not add any H1 ORB to live BATs or the website yet.

## Final market comparison

| Market/configuration | Locked return | PF | Win | DD | Trades | Sharpe | Recovery | MC P5 | MC P95 DD | 3Y return | 3Y PF |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| XAU 13:00 UTC, 1.5R | -0.26% | 0.99 | 48.28% | 10.01% | 145 | -0.10 | -0.02 | -14.03% | 17.96% | +41.56% | 1.36 |
| XAU 09:30 NY, 0.5R | +0.58% | 1.09 | 64.71% | 2.04% | 34 | 2.03 | 0.28 | -2.00% | 3.20% | +12.07% | 2.10 |
| XAG 18:00 NY, 0.5R | -2.13% | 0.92 | 60.00% | 7.78% | 95 | -2.77 | -0.27 | -10.34% | 12.24% | +1.52% | 1.06 |
| XAG 00:00 UTC, 2R | -11.54% | 0.71 | 41.18% | 15.27% | 102 | -5.00 | -0.75 | -22.89% | 24.29% | -8.02% | 0.84 |
| US100 08:20 NY, 2R | +1.04% | 1.02 | 58.05% | 10.06% | 174 | 0.37 | 0.09 | -18.15% | 23.58% | +47.74% | 1.24 |
| **US100 13:00 UTC, 6R** | **+23.00%** | **1.72** | **50.70%** | **6.81%** | **71** | **9.22** | **3.25** | **+0.12%** | **11.25%** | **+107.21%** | **1.96** |

## US100 demo configuration

- Instrument: Exness USTEC CFD.
- Opening range: 13:00–14:00 UTC, exactly 60 minutes.
- Entry window: 14:00–15:00 UTC only.
- Signal: M15 direct breakout; candle body at least 55%; 0.03 H1-ATR breakout buffer.
- Confirmation: permissive relative tick volume, opening >= 0.50 and breakout >= 0.70; no EMA, VWAP or profile filter.
- Stop: opposite side of the range plus 0.10 H1 ATR, capped at 3 H1 ATR.
- Nominal target: 6R; flat at 20:00 UTC; no break-even, trailing, Dynamic 50/20 or Safe filter.
- Risk: fixed 1% of current equity.

The locked-year realized average win/loss ratio was **{average_payoff:.2f}:1**, not 6:1, because many positions were closed by the 20:00 UTC session flat before reaching the distant nominal target. Average win was ${average_win:.2f}, average loss ${average_loss:.2f}, and historical expectancy was ${expectancy:.2f} per trade on the $10,000 test account.

## Robustness

- RR was tested from 0.5R through 10R. Development peaked at 6R and declined at 8R/10R.
- Locked year: +23.00%, PF 1.72, 50.70% win rate, 6.81% DD, 71 trades.
- Three-year Every Tick: +107.21%, PF 1.96, 54.19% win rate, 6.81% DD, 179 trades.
- Monte Carlo: 95.2% profitable paths, +0.12% return P5, +21.85% median, 11.25% P95 DD, 8.79% probability of >=10% DD, 0.06% probability of >=20% DD, and 0% simulated ruin.

## XAU and XAG verdict

XAU and XAG are rejected for this exact one-hour ORB concept. Gold's attractive development result failed in the locked year, and silver was negative in the locked year. Their positive full-period figures must not override the untouched validation failure.

## Integrity

- All parameter selection occurred on 2023-09-01 through 2025-08-31 before reading the locked 2025-09-01 through 2026-09-01 results.
- Safe mode used the existing completed-D1, no-lookahead Markov gate and was rejected independently for these candidates.
- Exness symbols are CFDs; volume is broker tick activity, not centralized exchange volume.
- No BAT, installed EA, selected portfolio set or website record was changed.
- The recommendation is demo-forward testing only; historical backtests and Monte Carlo are not guarantees.

## Artifacts

- Final graph: `Charts/H1 ORB FINAL DECISION AND MONTE CARLO.png`
- Final data: `FINAL AUDIT.json`, `FINAL AUDIT.csv`, `US100 RR6 VALIDATION.json`
- RR extension: `RR EXTENSION RESULTS.json`
- Demo set: `Sets/USTEC - overlap-1300 - H1 opening range - RR6 - 1pct.set`
"""
(ROOT / "FINAL REPORT.md").write_text(report, encoding="utf-8")
print(json.dumps({
    "chart": str(chart),
    "report": str(ROOT / "FINAL REPORT.md"),
    "average_payoff": average_payoff,
    "expectancy": expectancy,
}, indent=2))
