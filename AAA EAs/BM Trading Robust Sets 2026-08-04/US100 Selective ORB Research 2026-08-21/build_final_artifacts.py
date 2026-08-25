from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--results", default="native-selected-results.json")
parser.add_argument("--output", default="US100 Selective ORB - Full Equity and Drawdown.png")
parser.add_argument("--version", default="US100 Selective ORB")
parser.add_argument("--risk-label", default="1% risk per trade")
args = parser.parse_args()
RESULTS = json.loads((ROOT / args.results).read_text(encoding="utf-8"))
FULL = next(item for item in RESULTS if item["case"] == "full-2020-2026")

frame = pd.DataFrame(FULL["series"])
frame["date"] = pd.to_datetime(frame["date"], format="mixed")
frame = frame.drop_duplicates(subset=["date"], keep="last").sort_values("date")
frame["peak"] = frame["balance"].cummax()
frame["realized_dd_pct"] = (frame["balance"] / frame["peak"] - 1.0) * 100.0

plt.style.use("dark_background")
figure, (axis, drawdown) = plt.subplots(
    2,
    1,
    figsize=(14, 8),
    gridspec_kw={"height_ratios": [3.2, 1.0], "hspace": 0.08},
    sharex=True,
)
figure.patch.set_facecolor("#071311")
for current in (axis, drawdown):
    current.set_facecolor("#0b1c19")
    current.grid(True, color="#28453f", alpha=0.45, linewidth=0.7)

axis.plot(frame["date"], frame["balance"], color="#5fffd1", linewidth=2.1, label="Realized balance")
axis.axhline(10000, color="#9ab5ad", linestyle="--", linewidth=1.0, alpha=0.75, label="$10,000 initial")
axis.axvline(pd.Timestamp("2024-01-01"), color="#ffd166", linestyle="--", linewidth=1.2)
axis.axvline(pd.Timestamp("2025-07-01"), color="#ff8c69", linestyle="--", linewidth=1.2)
axis.text(pd.Timestamp("2021-06-01"), 11620, "TRAINING", color="#9ab5ad", fontsize=10, weight="bold")
axis.text(pd.Timestamp("2024-02-01"), 11620, "VALIDATION", color="#ffd166", fontsize=10, weight="bold")
axis.text(pd.Timestamp("2025-07-20"), 11620, "RECENT CHECK", color="#ff8c69", fontsize=10, weight="bold")
axis.scatter(frame["date"].iloc[-1], frame["balance"].iloc[-1], s=48, color="#ffffff", zorder=4)
axis.annotate(
    f"${frame['balance'].iloc[-1]:,.2f}",
    (frame["date"].iloc[-1], frame["balance"].iloc[-1]),
    xytext=(-8, 12),
    textcoords="offset points",
    ha="right",
    color="#ffffff",
    fontsize=11,
    weight="bold",
)
axis.set_ylabel("Balance (USD)")
axis.set_title(
    f"{args.version} — Exness USTEC M5, {args.risk_label}\n"
    "MT5 Every Tick, recorded spread, random execution delay",
    loc="left",
    fontsize=15,
    weight="bold",
    pad=16,
)
axis.legend(loc="upper left", frameon=False)

drawdown.fill_between(frame["date"], frame["realized_dd_pct"], 0, color="#ff6b6b", alpha=0.65)
drawdown.plot(frame["date"], frame["realized_dd_pct"], color="#ff8a8a", linewidth=1.0)
drawdown.set_ylabel("Realized DD")
drawdown.yaxis.set_major_formatter(lambda value, _: f"{value:.0f}%")
drawdown.xaxis.set_major_locator(mdates.YearLocator())
drawdown.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
drawdown.set_xlabel("Chronological broker history")

output = ROOT / args.output
figure.savefig(output, dpi=180, bbox_inches="tight", facecolor=figure.get_facecolor())
print(output)
