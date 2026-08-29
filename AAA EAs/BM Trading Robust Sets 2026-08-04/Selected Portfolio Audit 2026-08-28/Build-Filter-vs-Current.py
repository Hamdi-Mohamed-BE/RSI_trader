from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
BOOKMAPER = PACKAGE.parent / "BookMaper" / "artifacts"
INITIAL = 10_000.0

ACTIVE_LABELS = {
    "ATR Candle Breakout",
    "Asia Breakout",
    "BTC Top Down FVG Liquidity",
    "DmC",
    "EMA3",
    "ETH Top Down FVG Liquidity",
    "Go Long",
    "LTA Volume Profile",
    "Nasdaq 5M Open EMA ATR",
    "Nasdaq Overnight",
    "News Pulse",
    "ORB Volume Profile",
    "US100 Fabio ORB 1R",
    "XAU Weakness",
}


def max_drawdown(series: list[dict]) -> tuple[float, float]:
    peak = float(series[0]["balance"])
    worst_amount = 0.0
    worst_pct = 0.0
    for point in series:
        balance = float(point["balance"])
        peak = max(peak, balance)
        amount = peak - balance
        pct = amount / peak * 100.0 if peak else 0.0
        if pct > worst_pct:
            worst_amount, worst_pct = amount, pct
    return worst_amount, worst_pct


def main() -> None:
    current = json.loads((ROOT / "portfolio-results.json").read_text(encoding="utf-8"))
    filter_data = json.loads((BOOKMAPER / "active-ea-regime-filter.json").read_text(encoding="utf-8-sig"))
    standalone = json.loads((BOOKMAPER / "standalone-results.json").read_text(encoding="utf-8-sig"))
    by_ea = {item["ea"]: item for item in filter_data["by_ea"]}

    events = [
        {"time": item["close_time"], "open_time": item["open_time"], "bot": item["bot"], "net": float(item["base_net"])}
        for item in filter_data["decisions"]
        if item["bot"] in ACTIVE_LABELS and item["accepted"]
    ]
    xau = standalone["xau"]["optimized"]
    for trade in xau["trades"]:
        events.append({"time": trade["close_time"], "open_time": trade["open_time"], "bot": "XAU Markov Regime", "net": float(trade["net"])})
    events.sort(key=lambda item: (item["time"], item["open_time"], item["bot"]))

    all_filtered_series = [{"time": "2025-08-11T00:00:00", "balance": INITIAL}]
    balance = INITIAL
    for event in events:
        balance += event["net"]
        all_filtered_series.append({"time": event["time"], "balance": round(balance, 2)})

    filtered_rows = [by_ea[label]["filtered"] for label in ACTIVE_LABELS]
    xau_metrics = xau["metrics"]
    gross_profit = sum(float(row["gross_profit"]) for row in filtered_rows) + float(xau_metrics["gross_profit"])
    gross_loss = sum(float(row["gross_loss"]) for row in filtered_rows) + float(xau_metrics["gross_loss"])
    trades = sum(int(row["trades"]) for row in filtered_rows) + int(xau_metrics["trades"])
    wins = sum(int(row["wins"]) for row in filtered_rows) + int(xau_metrics["wins"])
    dd_amount, dd_pct = max_drawdown(all_filtered_series)
    all_filtered = {
        "label": "Same 15 EAs, filter forced on every eligible EA",
        "initial": INITIAL,
        "final": round(balance, 2),
        "net": round(balance - INITIAL, 2),
        "return_pct": round((balance / INITIAL - 1.0) * 100.0, 4),
        "profit_factor": round(gross_profit / abs(gross_loss), 4) if gross_loss else 0.0,
        "win_rate_pct": round(wins / trades * 100.0, 4) if trades else 0.0,
        "realized_dd_amount": round(dd_amount, 2),
        "realized_dd_pct": round(dd_pct, 4),
        "trades": trades,
        "series": all_filtered_series,
    }
    current_metrics = dict(current["combined"])
    current_metrics["label"] = "Current BAT: filter only where return and PF improved"

    times = sorted({point["time"] for point in current_metrics["series"]} | {point["time"] for point in all_filtered_series})
    current_map = {point["time"]: float(point["balance"]) for point in current_metrics["series"]}
    filtered_map = {point["time"]: float(point["balance"]) for point in all_filtered_series}
    current_value = INITIAL
    filtered_value = INITIAL
    comparison = []
    for time in times:
        current_value = current_map.get(time, current_value)
        filtered_value = filtered_map.get(time, filtered_value)
        comparison.append({"time": time, "current_bat": current_value, "all_filtered": filtered_value})
    with (ROOT / "filter-vs-current-equity.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["time", "current_bat", "all_filtered"])
        writer.writeheader()
        writer.writerows(comparison)

    figure, axis = plt.subplots(figsize=(13, 6), dpi=180)
    figure.patch.set_facecolor("#07110f")
    axis.set_facecolor("#0b1714")
    dates = [datetime.fromisoformat(row["time"]) for row in comparison]
    axis.plot(dates, [row["current_bat"] for row in comparison], color="#67f5c3", linewidth=1.7, label="Current BAT selective mix")
    axis.plot(dates, [row["all_filtered"] for row in comparison], color="#68a7ff", linewidth=1.35, label="Filter forced on all 15")
    axis.axhline(INITIAL, color="#81918d", linestyle="--", linewidth=0.8)
    axis.set_title("Current active BAT vs forcing the regime filter on every EA", color="white", fontsize=14, pad=12)
    axis.set_ylabel("Chronological realized balance (USD)", color="#cbd8d5")
    axis.tick_params(colors="#9eb1ac")
    axis.grid(color="#31443f", alpha=0.35, linewidth=0.6)
    legend = axis.legend(facecolor="#0b1714", edgecolor="#31443f")
    for text in legend.get_texts():
        text.set_color("white")
    for spine in axis.spines.values():
        spine.set_color("#31443f")
    figure.tight_layout()
    figure.savefig(ROOT / "filter-vs-current-equity.png", bbox_inches="tight")
    plt.close(figure)

    fields = ["return_pct", "final", "profit_factor", "win_rate_pct", "realized_dd_pct", "trades"]
    differences = {
        "return_pct": current_metrics["return_pct"] - all_filtered["return_pct"],
        "final": current_metrics["final"] - all_filtered["final"],
        "profit_factor": current_metrics["profit_factor"] - all_filtered["profit_factor"],
        "win_rate_pct": current_metrics["win_rate_pct"] - all_filtered["win_rate_pct"],
        "realized_dd_pct": current_metrics["realized_balance_dd_pct"] - all_filtered["realized_dd_pct"],
        "trades": current_metrics["trades"] - all_filtered["trades"],
    }
    output = {"current": current_metrics, "all_filtered": all_filtered, "current_minus_filtered": differences}
    for group in output.values():
        group.pop("series", None)
    (ROOT / "filter-vs-current-summary.json").write_text(json.dumps(output, indent=2), encoding="utf-8")

    lines = [
        "# Current BAT vs forcing the filter on every active EA",
        "",
        "Both columns use the same 15-EA topology and the same $10,000 chronological closed-cash-flow method. XAU Markov is unchanged because it is already the regime model.",
        "",
        "| Version | Return | Final | PF | Win rate | Realized DD | Trades |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        f"| Current BAT selective mix | {current_metrics['return_pct']:+.2f}% | ${current_metrics['final']:,.2f} | {current_metrics['profit_factor']:.2f} | {current_metrics['win_rate_pct']:.2f}% | {current_metrics['realized_balance_dd_pct']:.2f}% | {current_metrics['trades']:,} |",
        f"| Filter forced on all eligible EAs | {all_filtered['return_pct']:+.2f}% | ${all_filtered['final']:,.2f} | {all_filtered['profit_factor']:.2f} | {all_filtered['win_rate_pct']:.2f}% | {all_filtered['realized_dd_pct']:.2f}% | {all_filtered['trades']:,} |",
        f"| Current minus all-filtered | {differences['return_pct']:+.2f} pp | ${differences['final']:+,.2f} | {differences['profit_factor']:+.2f} | {differences['win_rate_pct']:+.2f} pp | {differences['realized_dd_pct']:+.2f} pp | {differences['trades']:+,} |",
        "",
        "![Current BAT versus all filtered](filter-vs-current-equity.png)",
        "",
        "The filter-everything version is a historical entry-veto overlay, not a simultaneous shared-margin MT5 run. The current selective curve uses native MT5 results for the three rebuilt filtered EAs. Floating-equity interaction and simultaneous margin contention are not represented in either curve.",
    ]
    (ROOT / "FILTER VS CURRENT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
