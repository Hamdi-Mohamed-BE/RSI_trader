from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "claim-982-final-results.json"
OUTPUT = ROOT / "Backtest Reports" / "982 Claim Recheck"


def money(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def graph(row: dict, filename: str, title: str) -> None:
    points = row["series"]
    dates = [datetime.fromisoformat(item["date"]) for item in points]
    balances = [float(item["balance"]) for item in points]
    figure, axis = plt.subplots(figsize=(11.5, 4.8), dpi=180)
    figure.patch.set_facecolor("#07110f")
    axis.set_facecolor("#0b1714")
    axis.plot(dates, balances, color="#67f5c3", linewidth=1.55)
    axis.axhline(row["initial_balance"], color="#81918d", linestyle="--", linewidth=0.8)
    axis.set_title(title, color="white", fontsize=14, pad=12)
    axis.set_ylabel("Realized balance (USD)", color="#cbd8d5")
    axis.tick_params(colors="#9eb1ac")
    axis.grid(color="#31443f", alpha=0.35, linewidth=0.6)
    for spine in axis.spines.values():
        spine.set_color("#31443f")
    figure.tight_layout()
    figure.savefig(OUTPUT / filename, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    rows = json.loads(RESULTS.read_text(encoding="utf-8"))
    by_case = {row["case"]: row for row in rows}
    full = by_case["full-2019-2026"]
    locked = by_case["locked-2025-2026"]
    last_year = by_case["last-year-2025-2026"]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    graph(full, "claim-982-full-history-equity.png", "US100 first-candle EMA/ATR — full-history MT5 equity")
    graph(last_year, "claim-982-last-year-equity.png", "US100 first-candle EMA/ATR — locked last-year MT5 equity")

    lines = [
        "# US100 first-candle momentum — 982% claim recheck",
        "",
        "## Decision",
        "",
        "The strategy is profitable, and the new delayed-trailing version improves the prior full-history return. The advertised +982% return and 57% win rate were not reproduced. The selected configuration is a research candidate, not an automatic BAT replacement.",
        "",
        "| Test | Dates | Return | PF | Win rate | Max equity DD | Trades | Final | Quality |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for label, row in (("Full history", full), ("Locked post-selection", locked), ("Locked last year", last_year)):
        dates = row["period"].split("(", 1)[-1].rstrip(")").replace(".", "-")
        lines.append(
            f"| {label} | {dates} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['win_rate']:.2f}% | "
            f"{row['equity_dd_pct']:.2f}% | {row['trades']:,} | {money(row['final_balance'])} | {row['history_quality_pct']:.0f}% |"
        )
    lines.extend([
        "",
        "## Selected reproducible rules",
        "",
        "- Exness USTEC, five-minute chart.",
        "- At 09:35 New York time, use the completed 09:30–09:35 candle.",
        "- Close above EMA(12): buy. Close below EMA(12): sell.",
        "- One trade maximum per New York trading day; both directions enabled.",
        "- ATR(14) initial stop at 4 ATR.",
        "- Start trailing after +1R; Chandelier-style trailing distance 6 ATR.",
        "- Close any remaining position at 15:55 New York time.",
        "- Risk 1% of current equity to the initial stop; no take-profit and no news filter.",
        "",
        "These parameters were selected using only 2019-07-16 through 2024-12-31. The post-2025 and last-year rows were run afterward without changing the settings.",
        "",
        "## Full-history statistics",
        "",
        f"- Initial / final: {money(full['initial_balance'])} / {money(full['final_balance'])}",
        f"- Net profit: {money(full['net_profit'])}",
        f"- Gross profit / loss: {money(full['gross_profit'])} / {money(full['gross_loss'])}",
        f"- Wins / losses: {full['wins']:,} / {full['losses']:,}",
        f"- Long trades: {full['long_trades']:,}; {full['long_win_rate']:.2f}% won",
        f"- Short trades: {full['short_trades']:,}; {full['short_win_rate']:.2f}% won",
        f"- Largest win / loss: {money(full['largest_win'])} / {money(full['largest_loss'])}",
        f"- Average win / loss: {money(full['average_win'])} / {money(full['average_loss'])}",
        f"- Recovery factor / MT5 Sharpe: {full['recovery_factor']:.2f} / {full['sharpe_ratio']:.2f}",
        f"- Commission / swap: {money(full['commission'])} / {money(full['swap'])}",
        "",
        "![Full-history equity](claim-982-full-history-equity.png)",
        "",
        "## Locked last-year equity",
        "",
        "![Last-year equity](claim-982-last-year-equity.png)",
        "",
        "## Comparison",
        "",
        "| Version | Full-history return | PF | Win rate | Max DD |",
        "| --- | ---: | ---: | ---: | ---: |",
        f"| New delayed-trail candidate | {full['return_pct']:+.2f}% | {full['profit_factor']:.2f} | {full['win_rate']:.2f}% | {full['equity_dd_pct']:.2f}% |",
        "| Existing session-close candidate | +155.35% | 1.12 | 36.07% | 27.10% |",
        "| Existing literal hold candidate | +56.38% | 1.04 | 32.24% | 34.61% |",
        "| Advertised claim | +982% | Not disclosed | 57% | 20% |",
        "",
        "The new candidate improves return but not robustness across every segment: its locked post-selection return is below the prior session-close candidate's +70.18%, and its full-history drawdown is slightly higher. It should be forward-tested before any BAT change.",
        "",
        "## Test integrity",
        "",
        "Native MT5 Every Tick testing used the synchronized Exness USTEC history, $10,000 initial balance, 1:2000 leverage, random execution delay, broker spread, reported commission and swap, and risk-based volume. The source video's proprietary stop formula was not disclosed, so the advertised result is not independently reproducible from the public description.",
    ])
    (OUTPUT / "FULL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
