from __future__ import annotations

import csv
import json
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "MT5 Reports"
CHARTS = ROOT / "Charts"
STARTING_BALANCE = 10_000.0

REPORT_MAP = [
    ("active-01-atr-candle-breakout.htm", "ATR Candle Breakout", "XAUUSD H1"),
    ("active-02-go-long.htm", "Go Long", "US30 D1"),
    ("active-03-aaa-final-ema3.htm", "AAA Final EMA3", "XAUUSD H4"),
    ("active-04-aaa-final-asia-breakout.htm", "AAA Final Asia Breakout", "XAUUSD H1"),
    ("active-05-aaa-final-weekend-direction.htm", "AAA Final Weekend Direction", "XAUUSD M15"),
    ("active-06-aaa-final-xau-weakness.htm", "AAA Final XAU Weakness", "XAUUSD M15"),
    ("active-07-lta-volume-profile.htm", "LTA Volume Profile", "XAUUSD M15"),
]


def clean_number(value: str) -> float:
    value = value.replace("\xa0", " ").replace(" ", "").replace(",", "")
    if not value or value == "-":
        return 0.0
    return float(value)


def match(text: str, pattern: str, default: str = "0") -> str:
    found = re.search(pattern, text)
    return found.group(1).strip() if found else default


def parse_report(path: Path, label: str, chart: str) -> dict:
    raw = path.read_text(encoding="utf-16", errors="replace")
    soup = BeautifulSoup(raw, "html.parser")
    text = " ".join(soup.get_text(" ").split())

    period = match(text, r"Period:\s*(.*?)\s+Inputs:", "unknown")
    quality = match(text, r"History Quality:\s*([^ ]+)")
    net = clean_number(match(text, r"Total Net Profit:\s*([-\d .]+?)\s+Balance Drawdown Absolute:"))
    gross_profit = clean_number(match(text, r"Gross Profit:\s*([-\d .]+?)\s+Balance Drawdown Maximal:"))
    gross_loss = clean_number(match(text, r"Gross Loss:\s*([-\d .]+?)\s+Balance Drawdown Relative:"))
    balance_dd_pct = float(match(text, r"Balance Drawdown Relative:\s*([\d.]+)%"))
    balance_dd_amt = clean_number(match(text, r"Balance Drawdown Relative:\s*[\d.]+%\s*\(([-\d .]+)\)"))
    equity_dd_pct = float(match(text, r"Equity Drawdown Relative:\s*([\d.]+)%"))
    equity_dd_amt = clean_number(match(text, r"Equity Drawdown Relative:\s*[\d.]+%\s*\(([-\d .]+)\)"))
    pf = float(match(text, r"Profit Factor:\s*([\d.]+)"))
    expected = clean_number(match(text, r"Expected Payoff:\s*([-\d .]+)"))
    recovery = float(match(text, r"Recovery Factor:\s*([-\d.]+)"))
    sharpe = float(match(text, r"Sharpe Ratio:\s*([-\d.]+)"))
    trades = int(match(text, r"Total Trades:\s*(\d+)"))
    wins = int(match(text, r"Profit Trades \(% of total\):\s*(\d+)"))
    win_rate = float(match(text, r"Profit Trades \(% of total\):\s*\d+\s*\(([\d.]+)%\)"))
    losses = int(match(text, r"Loss Trades \(% of total\):\s*(\d+)"))
    largest_win = clean_number(match(text, r"Largest profit trade:\s*([-\d .]+)"))
    largest_loss = clean_number(match(text, r"Largest loss trade:\s*([-\d .]+)"))
    average_win = clean_number(match(text, r"Average profit trade:\s*([-\d .]+)"))
    average_loss = clean_number(match(text, r"Average loss trade:\s*([-\d .]+)"))
    max_loss_streak = int(match(text, r"Maximum consecutive losses \(\$\):\s*(\d+)"))
    max_loss_streak_amount = clean_number(match(text, r"Maximum consecutive losses \(\$\):\s*\d+\s*\(([-\d .]+)\)"))
    bars = int(match(text, r"Bars:\s*(\d+)"))
    ticks = int(match(text, r"Ticks:\s*(\d+)"))

    deals = []
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
        when = datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S")
        deal_type = cells[3].lower()
        commission = clean_number(cells[8])
        swap = clean_number(cells[9])
        profit = clean_number(cells[10])
        balance = clean_number(cells[11])
        if deal_type == "balance":
            continue
        deals.append(
            {
                "time": when,
                "commission": commission,
                "swap": swap,
                "profit": profit,
                "cashflow": commission + swap + profit,
                "balance": balance,
            }
        )

    daily = {datetime(2025, 8, 5).date(): STARTING_BALANCE}
    for deal in deals:
        daily[deal["time"].date()] = deal["balance"]
    daily[datetime(2026, 8, 4).date()] = STARTING_BALANCE + net

    return {
        "file": path.name,
        "stem": path.stem,
        "label": label,
        "chart": chart,
        "period": period,
        "quality": quality,
        "bars": bars,
        "ticks": ticks,
        "initial_balance": STARTING_BALANCE,
        "final_balance": STARTING_BALANCE + net,
        "net_profit": net,
        "return_pct": net / STARTING_BALANCE * 100.0,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "balance_dd_pct": balance_dd_pct,
        "balance_dd_amt": balance_dd_amt,
        "equity_dd_pct": equity_dd_pct,
        "equity_dd_amt": equity_dd_amt,
        "profit_factor": pf,
        "expected_payoff": expected,
        "recovery_factor": recovery,
        "sharpe_ratio": sharpe,
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "largest_win": largest_win,
        "largest_loss": largest_loss,
        "average_win": average_win,
        "average_loss": average_loss,
        "max_loss_streak": max_loss_streak,
        "max_loss_streak_amount": max_loss_streak_amount,
        "deals": deals,
        "daily": daily,
    }


def max_drawdown(events: list[dict]) -> tuple[float, float]:
    balance = STARTING_BALANCE
    peak = balance
    worst_amount = 0.0
    worst_pct = 0.0
    for event in events:
        balance += event["cashflow"]
        peak = max(peak, balance)
        amount = peak - balance
        pct = amount / peak * 100.0 if peak else 0.0
        if pct > worst_pct:
            worst_pct = pct
            worst_amount = amount
    return worst_amount, worst_pct


def chart_series(daily: dict) -> list[dict]:
    return [{"date": day.isoformat(), "balance": round(value, 2)} for day, value in sorted(daily.items())]


def money(value: float) -> str:
    return f"${value:,.2f}"


def percent(value: float) -> str:
    return f"{value:.2f}%"


def main() -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    results = [parse_report(REPORTS / filename, label, chart) for filename, label, chart in REPORT_MAP]

    events = []
    for index, result in enumerate(results):
        for deal in result["deals"]:
            events.append({**deal, "bot": result["label"], "order": index})
    events.sort(key=lambda item: (item["time"], item["order"]))

    combined_daily = {datetime(2025, 8, 5).date(): STARTING_BALANCE}
    combined_balance = STARTING_BALANCE
    for event in events:
        combined_balance += event["cashflow"]
        combined_daily[event["time"].date()] = combined_balance
    combined_net = sum(result["net_profit"] for result in results)
    combined_balance = STARTING_BALANCE + combined_net
    combined_daily[datetime(2026, 8, 4).date()] = combined_balance
    combined_dd_amt, combined_dd_pct = max_drawdown(events)
    gross_profit = sum(result["gross_profit"] for result in results)
    gross_loss = sum(result["gross_loss"] for result in results)
    total_trades = sum(result["trades"] for result in results)
    total_wins = sum(result["wins"] for result in results)
    total_losses = sum(result["losses"] for result in results)
    combined_pf = gross_profit / abs(gross_loss) if gross_loss else 0.0

    combined = {
        "label": "Combined realized balance",
        "chart": "7 active EAs",
        "initial_balance": STARTING_BALANCE,
        "final_balance": combined_balance,
        "net_profit": combined_net,
        "return_pct": combined_net / STARTING_BALANCE * 100.0,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "balance_dd_amt": combined_dd_amt,
        "balance_dd_pct": combined_dd_pct,
        "profit_factor": combined_pf,
        "expected_payoff": combined_net / total_trades if total_trades else 0.0,
        "recovery_factor": combined_net / combined_dd_amt if combined_dd_amt else 0.0,
        "trades": total_trades,
        "wins": total_wins,
        "losses": total_losses,
        "win_rate": total_wins / total_trades * 100.0 if total_trades else 0.0,
        "daily": combined_daily,
    }

    export = {
        "method": {
            "broker": "Exness Technologies Ltd / Exness-MT5Trial16",
            "period": "2025-08-05 to 2026-08-04",
            "deposit": STARTING_BALANCE,
            "leverage": "1:2000",
            "model": "Every tick generated from broker M1 data",
            "execution": "Random execution delay",
            "risk": "1% per EA trade; Go Long uses the installer-equivalent fixed lot and hard stop",
        },
        "combined": {**{key: value for key, value in combined.items() if key != "daily"}, "series": chart_series(combined["daily"])},
        "bots": [
            {
                **{key: value for key, value in result.items() if key not in {"deals", "daily"}},
                "series": chart_series(result["daily"]),
            }
            for result in results
        ],
    }
    (ROOT / "portfolio-data.json").write_text(json.dumps(export, indent=2), encoding="utf-8")

    with (ROOT / "portfolio-summary.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        fields = [
            "label", "chart", "initial_balance", "final_balance", "net_profit", "return_pct",
            "equity_dd_pct", "equity_dd_amt", "balance_dd_pct", "balance_dd_amt", "profit_factor",
            "recovery_factor", "sharpe_ratio", "trades", "wins", "losses", "win_rate",
            "average_win", "average_loss", "largest_win", "largest_loss",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    with (ROOT / "combined-balance.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "balance"])
        for point in chart_series(combined_daily):
            writer.writerow([point["date"], f"{point['balance']:.2f}"])

    dates = [point["date"] for point in chart_series(combined_daily)]
    balances = [point["balance"] for point in chart_series(combined_daily)]
    fig, axis = plt.subplots(figsize=(12, 5.5), dpi=160)
    axis.plot([datetime.fromisoformat(item) for item in dates], balances, linewidth=1.8)
    axis.axhline(STARTING_BALANCE, linewidth=0.9, linestyle="--")
    axis.set_title("Active 1% portfolio — combined realized balance")
    axis.set_xlabel("Date")
    axis.set_ylabel("Balance (USD)")
    axis.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(CHARTS / "combined-realized-balance.png")
    plt.close(fig)

    lines = [
        "# Active 1% portfolio — one-year Exness report",
        "",
        "## Test method",
        "",
        "- Broker: Exness Technologies Ltd, `Exness-MT5Trial16`",
        "- Period: 2025-08-05 through 2026-08-04",
        "- Initial balance: $10,000 USD per individual test",
        "- Leverage: 1:2000",
        "- Model: Every tick generated from Exness M1 data",
        "- Execution: random execution delay",
        "- Risk: synchronized installer settings at 1% per EA trade; Go Long uses the installer-equivalent fixed lot and hard stop",
        "",
        "## Results",
        "",
        "| EA | Chart | Net profit | Return | Max equity DD | PF | Win rate | Trades |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        lines.append(
            f"| {result['label']} | {result['chart']} | {money(result['net_profit'])} | "
            f"{percent(result['return_pct'])} | {percent(result['equity_dd_pct'])} | "
            f"{result['profit_factor']:.2f} | {percent(result['win_rate'])} | {result['trades']} |"
        )
    lines.extend(
        [
            "",
            "## Combined realized-balance aggregation",
            "",
            f"- Final balance: {money(combined['final_balance'])}",
            f"- Net profit: {money(combined['net_profit'])} ({percent(combined['return_pct'])})",
            f"- Realized balance drawdown: {money(combined['balance_dd_amt'])} ({percent(combined['balance_dd_pct'])})",
            f"- Aggregated profit factor: {combined['profit_factor']:.2f}",
            f"- Trades: {combined['trades']:,}; winning trades: {combined['wins']:,} ({percent(combined['win_rate'])})",
            "",
            "![Combined realized balance](Charts/combined-realized-balance.png)",
            "",
            "## Individual native MT5 reports and graphs",
            "",
        ]
    )
    for result in results:
        lines.extend(
            [
                f"### {result['label']} — {result['chart']}",
                "",
                f"- Final balance: {money(result['final_balance'])}",
                f"- Net profit: {money(result['net_profit'])} ({percent(result['return_pct'])})",
                f"- Max equity drawdown: {money(result['equity_dd_amt'])} ({percent(result['equity_dd_pct'])})",
                f"- Profit factor: {result['profit_factor']:.2f}; recovery factor: {result['recovery_factor']:.2f}; Sharpe: {result['sharpe_ratio']:.2f}",
                f"- Trades: {result['trades']}; wins: {result['wins']} ({percent(result['win_rate'])}); losses: {result['losses']}",
                f"- Average win/loss: {money(result['average_win'])} / {money(result['average_loss'])}",
                f"- Largest win/loss: {money(result['largest_win'])} / {money(result['largest_loss'])}",
                f"- [Native MT5 report](MT5 Reports/{result['file']})",
                "",
                f"![{result['label']} balance graph](MT5 Reports/{result['stem']}.png)",
                "",
            ]
        )
    lines.extend(
        [
            "## Critical combined-result limitation",
            "",
            "The combined curve merges the realized cash flows from seven separate $10,000 MT5 tests. It shows what their closed-deal results would look like on one timeline, including commissions and swaps. It is not an exact multi-EA MT5 portfolio simulation: percentage-risk EAs sized trades from their own standalone balances, not a shared changing balance, and the combined curve does not reconstruct overlapping floating P/L. Therefore the combined realized drawdown can understate live equity drawdown. Simultaneous 1% trades can stack account exposure well above 1%.",
            "",
            "Weekend Direction generated zero trades on this Exness data/window despite being enabled. That is reported as-is, not filled using results from a different broker.",
        ]
    )
    (ROOT / "FULL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"combined": export["combined"], "bots": [{k: v for k, v in bot.items() if k != "series"} for bot in export["bots"]]}, indent=2))


if __name__ == "__main__":
    main()
