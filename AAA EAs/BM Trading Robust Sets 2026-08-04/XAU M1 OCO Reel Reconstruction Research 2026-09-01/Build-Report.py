from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


ROOT = Path(__file__).resolve().parent
LOCKED = json.loads((ROOT / "locked-results.json").read_text(encoding="utf-8"))
AUGUST = json.loads((ROOT / "august-results.json").read_text(encoding="utf-8"))
DEVELOPMENT = json.loads((ROOT / "development-results.json").read_text(encoding="utf-8"))

LABELS = {
    "current": "Current-price OCO",
    "previous": "Previous-candle OCO",
}
COLORS = {"current": "#49e6b1", "previous": "#62a8ff"}


def money(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def pct(value: float) -> str:
    return f"{value:+,.2f}%"


def series(item: dict) -> tuple[list[datetime], list[float]]:
    points = item["series"]
    # Keep the plot light without altering the first/last points or curve shape.
    stride = max(1, len(points) // 5000)
    sampled = points[::stride]
    if sampled[-1] is not points[-1]:
        sampled.append(points[-1])
    return [datetime.fromisoformat(p["date"]) for p in sampled], [p["balance"] for p in sampled]


def plot_period(ax, results: list[dict], title: str) -> None:
    for item in results:
        dates, balances = series(item)
        ax.plot(dates, balances, lw=1.6, color=COLORS[item["mode"]], label=LABELS[item["mode"]])
    ax.axhline(10_000, color="#8a98a8", lw=0.8, ls="--", alpha=0.65)
    ax.set_yscale("log")
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", color="#f4f7fb")
    ax.set_ylabel("Realized balance, USD (log scale)")
    locator = mdates.AutoDateLocator(minticks=4, maxticks=7)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.grid(True, color="#263441", alpha=0.55, linewidth=0.7)
    ax.legend(frameon=False, loc="upper left")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"${value:,.0f}"))


plt.rcParams.update({
    "figure.facecolor": "#081014",
    "axes.facecolor": "#0d171d",
    "axes.edgecolor": "#31404b",
    "axes.labelcolor": "#aab7c4",
    "xtick.color": "#91a0ad",
    "ytick.color": "#91a0ad",
    "text.color": "#eaf0f5",
    "font.family": "DejaVu Sans",
})

fig = plt.figure(figsize=(18, 11))
grid = fig.add_gridspec(
    3, 2, height_ratios=[1.2, 1.2, 0.8],
    left=0.055, right=0.985, bottom=0.055, top=0.92, hspace=0.34, wspace=0.20,
)
plot_period(fig.add_subplot(grid[0, 0]), LOCKED, "Locked evaluation · 01 Jul–31 Aug 2026")
plot_period(fig.add_subplot(grid[0, 1]), AUGUST, "Most recent month · 01–31 Aug 2026")

ax_return = fig.add_subplot(grid[1, 0])
names = [LABELS[item["mode"]] for item in LOCKED]
x = range(len(names))
width = 0.35
locked_returns = [item["return_pct"] for item in LOCKED]
aug_returns = [next(row["return_pct"] for row in AUGUST if row["mode"] == item["mode"]) for item in LOCKED]
ax_return.bar([i - width / 2 for i in x], locked_returns, width, color="#49e6b1", label="Jul–Aug")
ax_return.bar([i + width / 2 for i in x], aug_returns, width, color="#62a8ff", label="August")
ax_return.set_xticks(list(x), names)
ax_return.set_title("Compounded return comparison", loc="left", fontsize=12, fontweight="bold")
ax_return.set_ylabel("Return (%)")
ax_return.grid(True, axis="y", color="#263441", alpha=0.55)
ax_return.legend(frameon=False)
for i, (full, month) in enumerate(zip(locked_returns, aug_returns)):
    ax_return.text(i - width / 2, full, f"{full:,.0f}%", ha="center", va="bottom", fontsize=9)
    ax_return.text(i + width / 2, month, f"{month:,.0f}%", ha="center", va="bottom", fontsize=9)

ax_risk = fig.add_subplot(grid[1, 1])
metrics = ["PF", "Win rate", "Max equity DD"]
current = LOCKED[0]
previous = LOCKED[1]
values_current = [current["profit_factor"], current["win_rate"] / 25, current["equity_dd_pct"]]
values_previous = [previous["profit_factor"], previous["win_rate"] / 25, previous["equity_dd_pct"]]
positions = list(range(len(metrics)))
ax_risk.bar([i - width / 2 for i in positions], values_current, width, color=COLORS["current"], label=LABELS["current"])
ax_risk.bar([i + width / 2 for i in positions], values_previous, width, color=COLORS["previous"], label=LABELS["previous"])
ax_risk.set_xticks(positions, ["Profit factor", "Win rate ÷25", "Max DD %"])
ax_risk.set_title("Two-month quality and risk", loc="left", fontsize=12, fontweight="bold")
ax_risk.grid(True, axis="y", color="#263441", alpha=0.55)
ax_risk.legend(frameon=False)
labels_current = [f"{current['profit_factor']:.2f}", f"{current['win_rate']:.2f}%", f"{current['equity_dd_pct']:.2f}%"]
labels_previous = [f"{previous['profit_factor']:.2f}", f"{previous['win_rate']:.2f}%", f"{previous['equity_dd_pct']:.2f}%"]
for i, label in enumerate(labels_current):
    ax_risk.text(i - width / 2, values_current[i], label, ha="center", va="bottom", fontsize=9)
for i, label in enumerate(labels_previous):
    ax_risk.text(i + width / 2, values_previous[i], label, ha="center", va="bottom", fontsize=9)

ax_note = fig.add_subplot(grid[2, :])
ax_note.axis("off")
rows = []
for item in LOCKED:
    rows.append([
        LABELS[item["mode"]], pct(item["return_pct"]), f"{item['profit_factor']:.2f}",
        f"{item['win_rate']:.2f}%", f"{item['equity_dd_pct']:.2f}%", f"{item['trades']:,}",
        money(item["commission"]), money(item["swap"]), money(item["final_balance"]),
    ])
table = ax_note.table(
    cellText=rows,
    colLabels=["Version", "Return", "PF", "Win rate", "Max DD", "Trades", "Commission", "Swap", "Final"],
    colWidths=[0.16, 0.11, 0.07, 0.09, 0.08, 0.09, 0.13, 0.09, 0.13],
    loc="center", cellLoc="center", colLoc="center", bbox=[0, 0.22, 1, 0.70],
)
table.auto_set_font_size(False)
table.set_fontsize(10)
for (row, col), cell in table.get_celld().items():
    cell.set_edgecolor("#31404b")
    cell.set_facecolor("#14222a" if row else "#20323c")
    cell.set_text_props(color="#f0f5f8", weight="bold" if row == 0 else "normal")
ax_note.text(
    0.0, 0.02,
    "Caution: balance-scaled sizing (0.04 lot per $10k, capped at 1.00 lot) and 27,946–43,226 trades in 62 days.\n"
    "MT5 includes Exness spread, random execution delay, commission and swap; it cannot reproduce VPS latency, order-rate limits, or live queue contention.",
    transform=ax_note.transAxes, fontsize=10.5, color="#ffbf69", va="bottom",
)

fig.suptitle("XAUUSD M1 OCO Reel Reconstruction · Two-Version Audit", fontsize=20, fontweight="bold", x=0.02, ha="left")
figure_path = ROOT / "XAU M1 OCO TWO VERSION AUDIT.png"
fig.savefig(figure_path, dpi=170, facecolor=fig.get_facecolor())
plt.close(fig)


def result_table(items: list[dict]) -> str:
    lines = [
        "| Version | Return | Final | PF | Win rate | Max equity DD | Wins / losses | Trades | Gross profit | Gross loss | Commission | Swap | Largest win | Largest loss | Average win | Average loss |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in items:
        lines.append(
            f"| {LABELS[item['mode']]} | {pct(item['return_pct'])} | {money(item['final_balance'])} | "
            f"{item['profit_factor']:.2f} | {item['win_rate']:.2f}% | {item['equity_dd_pct']:.2f}% | "
            f"{item['wins']:,} / {item['losses']:,} | {item['trades']:,} | {money(item['gross_profit'])} | "
            f"{money(item['gross_loss'])} | {money(item['commission'])} | {money(item['swap'])} | "
            f"{money(item['largest_win'])} | {money(item['largest_loss'])} | {money(item['average_win'])} | {money(item['average_loss'])} |"
        )
    return "\n".join(lines)


dev_lines = [
    "| Mode | Candidate | Return | PF | Win rate | Max equity DD | Trades |",
    "|---|---|---:|---:|---:|---:|---:|",
]
for item in DEVELOPMENT:
    dev_lines.append(
        f"| {LABELS[item['mode']]} | {item['variant']} | {pct(item['return_pct'])} | "
        f"{item['profit_factor']:.2f} | {item['win_rate']:.2f}% | {item['equity_dd_pct']:.2f}% | {item['trades']:,} |"
    )

report = f"""# XAUUSD M1 OCO reel reconstruction — two-version audit

## Decision

The **current-price OCO version wins the MT5 comparison** on return, profit factor and drawdown. It is not yet suitable for a real-money BAT deployment: it executed **{LOCKED[0]['trades']:,} trades in 62 calendar days** and charged {money(LOCKED[0]['commission'])} in commission. That frequency makes the result unusually dependent on broker execution, VPS latency and order-rate tolerance.

If you want to trial one, use the current-price version **on demo only**. The previous-candle version is slower and cheaper, but it still executed {LOCKED[1]['trades']:,} trades in two months.

![Two-version audit](./XAU M1 OCO TWO VERSION AUDIT.png)

## Locked 01 July–31 August 2026

{result_table(LOCKED)}

## August 2026 alone

{result_table(AUGUST)}

## Exact winning rules

### Version A — current-price OCO

- On every new M1 bar while flat, place a Buy Stop at ask + **$0.40** and a Sell Stop at bid − **$0.40**.
- When either entry fills, cancel its sibling immediately (one-cancels-other).
- Initial stop: **$0.50** from entry; no fixed take-profit.
- Start trailing after **$0.80** favorable movement; trail **$0.45** behind price.
- Refresh unfilled orders each new M1 bar, reject spread above **$0.50**, and force-close after 180 minutes.

### Version B — previous-candle OCO

- On every new M1 bar while flat, place stops **$0.05** beyond the completed M1 candle high and low, respecting the broker minimum distance.
- Initial stop: **$0.80**; no fixed take-profit.
- Start trailing after **$1.20** favorable movement; trail **$0.60** behind price.
- The same OCO, spread, refresh and maximum-hold rules apply.

### Dynamic lot sizing

`lot = 0.04 × current equity / $10,000`, normalized to the broker step and capped between **0.01 and 1.00 lot**. Thus the default is 0.04 lot on a $10,000 account and it scales up or down with equity.

## Method

- Broker/data: Exness XAUUSD, MT5 **Every Tick**, 100% reported history quality.
- Initial balance: $10,000; leverage 1:2000.
- Costs: broker spread, commission and swap; randomized execution delay enabled.
- Candidate selection: 01 April–30 June 2026 only.
- Untouched evaluation: 01 July–31 August 2026; August also reported separately.
- One open position maximum; no grid and no martingale.
- Custom curves show realized account balance from every deal. MT5 max equity drawdown statistics include floating equity.

## Development screen (not headline performance)

{chr(10).join(dev_lines)}

The spectacular fixed-distance returns should not be read as a promise. They arise from a tiny stop/trail, very high transaction count, and dynamic compounding. MT5 captured historical spread, delay and account charges, but no backtest can reproduce live network latency, rejection bursts, server throttling or simultaneous OCO fills perfectly.

## Engineering references

- MQL5 requires checking the server result when deleting a pending order: [CTrade::OrderDelete](https://www.mql5.com/en/docs/standardlibrary/tradeclasses/ctrade/ctradeorderdelete).
- OCO cleanup is handled through trade-transaction events: [OnTradeTransaction](https://www.mql5.com/en/docs/event_handlers/ontradetransaction).
- Pending-order rules and broker distance constraints: [MQL5 pending orders](https://www.mql5.com/en/book/automation/experts/experts_pending).
- Opening-range evidence supports testing but does not validate this exact reel strategy: [Assessing profitability of intraday opening range breakout strategies](https://www.sciencedirect.com/science/article/pii/S1544612312000438).

## Deployment status

Research only. Neither EA was added to the active portfolio BAT or the website.
"""
(ROOT / "FULL REPORT.md").write_text(report, encoding="utf-8")

print(figure_path)
print(ROOT / "FULL REPORT.md")
