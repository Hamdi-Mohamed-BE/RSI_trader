from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
LOCKED = json.loads((ROOT / "locked-results.json").read_text(encoding="utf-8"))
DEVELOPMENT = json.loads((ROOT / "development-results.json").read_text(encoding="utf-8"))
SELECTION = json.loads((ROOT / "selection.json").read_text(encoding="utf-8"))

LABELS = {"XAUUSD": "Gold", "XAGUSD": "Silver", "US30": "US30", "USTEC": "US100", "BTCUSD": "Bitcoin"}
COLORS = {"XAUUSD": "#f4c95d", "XAGUSD": "#cbd5e1", "US30": "#60a5fa", "USTEC": "#2dd4bf", "BTCUSD": "#f59e0b"}


def fmt_money(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def plot() -> None:
    plt.style.use("dark_background")
    fig = plt.figure(figsize=(15, 10), facecolor="#071310")
    grid = fig.add_gridspec(2, 2, height_ratios=[1.35, 1], hspace=0.27, wspace=0.18)
    ax_curve = fig.add_subplot(grid[0, :])
    ax_return = fig.add_subplot(grid[1, 0])
    ax_stats = fig.add_subplot(grid[1, 1])
    for ax in (ax_curve, ax_return, ax_stats):
        ax.set_facecolor("#0b1b17")
        for spine in ax.spines.values():
            spine.set_color("#21483d")
        ax.grid(True, color="#17372f", alpha=.65, linewidth=.7)

    for item in LOCKED:
        points = item["series"]
        dates = [datetime.fromisoformat(point["date"]) for point in points]
        balances = [point["balance"] for point in points]
        symbol = item["symbol"]
        ax_curve.step(dates, balances, where="post", linewidth=2.1, color=COLORS[symbol],
                      label=f"{LABELS[symbol]}  {item['return_pct']:+.2f}%")
    ax_curve.axhline(10000, color="#6b8f83", linestyle="--", linewidth=1)
    ax_curve.set_title("Untouched last-year MT5 Every Tick equity curves", loc="left", fontsize=18, fontweight="bold")
    ax_curve.set_ylabel("Balance (USD)")
    ax_curve.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax_curve.legend(ncol=5, frameon=False, loc="upper left")

    ordered = sorted(LOCKED, key=lambda item: item["return_pct"], reverse=True)
    labels = [LABELS[item["symbol"]] for item in ordered]
    returns = [item["return_pct"] for item in ordered]
    colors = ["#5ee7b7" if value >= 0 else "#fb7185" for value in returns]
    bars = ax_return.barh(labels, returns, color=colors, alpha=.9)
    ax_return.axvline(0, color="#9fb8b0", linewidth=1)
    ax_return.invert_yaxis()
    ax_return.set_title("Net return", loc="left", fontsize=15, fontweight="bold")
    ax_return.set_xlabel("Percent")
    for bar, value in zip(bars, returns):
        x = value + (.15 if value >= 0 else -.15)
        ax_return.text(x, bar.get_y() + bar.get_height()/2, f"{value:+.2f}%", va="center",
                       ha="left" if value >= 0 else "right", fontweight="bold")

    ax_stats.axis("off")
    columns = ["Market", "PF", "Win", "Max DD", "Trades"]
    rows = [[LABELS[item["symbol"]], f"{item['profit_factor']:.2f}", f"{item['win_rate']:.1f}%",
             f"{item['equity_dd_pct']:.2f}%", str(item["trades"])] for item in ordered]
    table = ax_stats.table(cellText=rows, colLabels=columns, cellLoc="center", colLoc="center",
                           loc="center", colColours=["#123328"] * len(columns))
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 1.8)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#285247")
        cell.set_facecolor("#10251f" if row else "#123328")
        cell.set_text_props(color="#effff9", weight="bold" if row == 0 else "normal")
    ax_stats.set_title("Locked test statistics", loc="left", fontsize=15, fontweight="bold", pad=14)

    fig.suptitle("P Continuation / Failed Auction — Five-Market Validation", x=.04, ha="left",
                 fontsize=23, fontweight="bold", color="#f3fff9")
    fig.text(.04, .94, "Exness MT5 • 2025-08-28 to 2026-08-27 • $10,000 • 1% risk/trade • real spread, commission, swap and random delay",
             color="#9bcbbd", fontsize=11)
    fig.text(.04, .015, "Verdict: REJECT — four of five markets lost money; BTC's PF 1.08 / 13 trades is not a robust edge.",
             color="#fb8b9d", fontsize=12, weight="bold")
    out = ROOT / "P CONTINUATION FIVE MARKET LOCKED AUDIT.png"
    fig.savefig(out, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def markdown() -> None:
    selected = {item["symbol"]: item for item in SELECTION}
    rows = []
    for item in sorted(LOCKED, key=lambda x: ["XAUUSD","XAGUSD","US30","USTEC","BTCUSD"].index(x["symbol"])):
        dev = selected[item["symbol"]]
        rows.append(
            f"| {LABELS[item['symbol']]} | {item['symbol']} | {item['variant']} | "
            f"{dev['development_return_pct']:+.2f}% | {dev['development_pf']:.2f} | "
            f"{item['return_pct']:+.2f}% | {item['profit_factor']:.2f} | {item['win_rate']:.2f}% | "
            f"{item['equity_dd_pct']:.2f}% | {item['wins']} / {item['losses']} | {item['trades']} | "
            f"{fmt_money(item['commission'])} | {fmt_money(item['swap'])} |"
        )
    best_dev = []
    for symbol in ["XAUUSD","XAGUSD","US30","USTEC","BTCUSD"]:
        market = [item for item in DEVELOPMENT if item["symbol"] == symbol]
        winner = max(market, key=lambda x: x["score"])
        best_dev.append(f"- {LABELS[symbol]}: {winner['variant']}, {winner['return_pct']:+.2f}%, PF {winner['profit_factor']:.2f}, DD {winner['equity_dd_pct']:.2f}%, {winner['trades']} trades")
    report = f"""# P Continuation / Failed Auction — full validation

## Verdict

**REJECT. Do not add this EA to the active BAT or website.** The strategy failed on the preselected development history for every market. On the untouched last year, only Bitcoin was marginally positive (+0.71%, PF 1.08) and that came from just 13 trades. This is not sufficient evidence of a repeatable edge.

## Exact test design

- Starting balance: $10,000 per independent test
- Position risk: 1% of current equity per trade
- Broker/data: Exness MT5, broker-native history
- Locked period: 2025-08-28 through 2026-08-27
- Locked modelling: MT5 Every Tick, history quality shown in each native report
- Costs: floating broker spread, commission, swap and random execution delay
- Selection: six simple variants were compared only on 2022-01-01 through 2025-08-27; one variant per market was then frozen
- No locked-year result was used to pick its own settings

## Locked one-year results

| Market | Broker symbol | Frozen variant | Development return | Dev PF | Locked return | PF | Win rate | Max equity DD | Wins / losses | Trades | Commission | Swap |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

## Development winners carried forward

{chr(10).join(best_dev)}

## Rules implemented

1. Detect a directional impulse spanning several completed bars, requiring a minimum ATR move and directional efficiency.
2. Require a compact consolidation to form near the impulse extreme, representing acceptance at the new price level.
3. Build a 24-row volume profile over that consolidation using Exness tick volume and calculate its POC plus 70% value area.
4. Long after price sweeps VAL and closes back inside with a strong upper close; short after the inverse VAH reclaim.
5. The stricter variant also requires reclaim-bar tick volume to be at least 1.25 times its recent average.
6. Put the stop beyond the failed-auction candle with an ATR buffer; use the frozen 1.5R/2R or impulse-size target; move to break-even at 1R.

## Important limitation

Exness CFD history has tick volume, not centralized exchange volume and not a historical order book. Therefore the EA can test a value-area sweep/reclaim and a tick-volume expansion proxy, but it **cannot prove true absorption or a failed auction from bid/ask depth**. A genuine order-flow version needs exchange futures/crypto trade and depth data.

## Files

- Source: `EA/P Continuation Failed Auction EA.mq5`
- Compiled research EA: `EA/P Continuation Failed Auction EA.ex5`
- Frozen sets: `Sets/`
- Native MT5 reports and native equity charts: `Backtest Reports/`
- Machine-readable results: `development-results.json`, `locked-results.json`
- Comparison graph: `P CONTINUATION FIVE MARKET LOCKED AUDIT.png`
"""
    (ROOT / "FULL REPORT.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    plot()
    markdown()
