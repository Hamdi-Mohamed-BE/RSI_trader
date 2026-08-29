from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
from bs4 import BeautifulSoup


VARIANTS = {
    "h0850-l60-either": dict(hour=8, lookback=60, confirm=2, displacement=0.35, min_rr=1.00, breakeven=True),
    "h0950-l30-either": dict(hour=9, lookback=30, confirm=2, displacement=0.35, min_rr=1.00, breakeven=True),
    "h0950-l60-either": dict(hour=9, lookback=60, confirm=2, displacement=0.35, min_rr=1.00, breakeven=True),
    "h0950-l90-ob": dict(hour=9, lookback=90, confirm=1, displacement=0.50, min_rr=1.25, breakeven=True),
    "h0950-l120-fvg": dict(hour=9, lookback=120, confirm=0, displacement=0.50, min_rr=1.25, breakeven=False),
    "h1050-l60-either": dict(hour=10, lookback=60, confirm=2, displacement=0.35, min_rr=1.00, breakeven=True),
    "h1150-l60-either": dict(hour=11, lookback=60, confirm=2, displacement=0.35, min_rr=1.00, breakeven=True),
}

SYMBOL_LABELS = {"xauusd": "XAUUSD", "ustec": "USTEC", "btcusd": "BTCUSD"}


def compact(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def number(value: str | None) -> float:
    match = re.search(r"[-+]?\d+(?:[,.]\d{3})*(?:\.\d+)?", compact(value or "").replace(" ", ""))
    return float(match.group(0).replace(",", "")) if match else 0.0


def percent(value: str | None) -> float:
    match = re.search(r"([-+]?\d+(?:\.\d+)?)%", compact(value or ""))
    return float(match.group(1)) if match else 0.0


def parse_report(path: Path) -> dict:
    soup = BeautifulSoup(path.read_text(encoding="utf-16", errors="replace"), "html.parser")
    values: dict[str, str] = {}
    for row in soup.find_all("tr"):
        cells = [compact(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"], recursive=False)]
        for index, cell in enumerate(cells[:-1]):
            if cell.endswith(":"):
                values[cell[:-1]] = cells[index + 1]

    deals = []
    in_deals = False
    for row in soup.find_all("tr"):
        row_text = compact(row.get_text(" ", strip=True))
        if row_text == "Deals":
            in_deals = True
            continue
        if not in_deals:
            continue
        cells = [compact(cell.get_text(" ", strip=True)) for cell in row.find_all("td", recursive=False)]
        if len(cells) != 13 or not re.fullmatch(r"\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}", cells[0]):
            continue
        if cells[3].lower() == "balance":
            continue
        deals.append(
            {
                "time": datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S"),
                "commission": number(cells[8]),
                "swap": number(cells[9]),
                "profit": number(cells[10]),
                "cashflow": number(cells[8]) + number(cells[9]) + number(cells[10]),
            }
        )

    initial = number(values.get("Initial Deposit")) or 10_000.0
    net = number(values.get("Total Net Profit"))
    equity_dd = values.get("Equity Drawdown Maximal", "")
    balance_dd = values.get("Balance Drawdown Maximal", "")
    wins = values.get("Profit Trades (% of total)", "")
    losses = values.get("Loss Trades (% of total)", "")
    return {
        "initial": initial,
        "final": initial + net,
        "net": net,
        "return_pct": net / initial * 100.0 if initial else 0.0,
        "profit_factor": number(values.get("Profit Factor")),
        "win_rate_pct": percent(wins),
        "wins": int(number(wins)),
        "losses": int(number(losses)),
        "trades": int(number(values.get("Total Trades"))),
        "equity_dd_amount": number(equity_dd),
        "equity_dd_pct": percent(equity_dd),
        "balance_dd_amount": number(balance_dd),
        "balance_dd_pct": percent(balance_dd),
        "gross_profit": number(values.get("Gross Profit")),
        "gross_loss": number(values.get("Gross Loss")),
        "largest_win": number(values.get("Largest profit trade")),
        "largest_loss": number(values.get("Largest loss trade")),
        "average_win": number(values.get("Average profit trade")),
        "average_loss": number(values.get("Average loss trade")),
        "expected_payoff": number(values.get("Expected Payoff")),
        "recovery_factor": number(values.get("Recovery Factor")),
        "sharpe": number(values.get("Sharpe Ratio")),
        "history_quality": values.get("History Quality", ""),
        "commission": sum(item["commission"] for item in deals),
        "swap": sum(item["swap"] for item in deals),
        "deals": deals,
    }


def identify(path: Path, phase: str) -> tuple[str, str]:
    match = re.match(rf"^(xauusd|ustec|btcusd)--(.+)--{phase}\.htm$", path.name, re.I)
    if not match:
        raise ValueError(path.name)
    return match.group(1).lower(), match.group(2)


def graph(row: dict, path: Path, title: str) -> None:
    balance = row["initial"]
    times = []
    balances = []
    for deal in row["deals"]:
        balance += deal["cashflow"]
        times.append(deal["time"])
        balances.append(balance)
    fig, ax = plt.subplots(figsize=(10.5, 4.4), dpi=160)
    fig.patch.set_facecolor("#07110f")
    ax.set_facecolor("#0b1714")
    if times:
        ax.plot(times, balances, color="#67f5c3", linewidth=1.7)
    else:
        ax.axhline(row["initial"], color="#67f5c3", linewidth=1.7)
    ax.axhline(row["initial"], color="#7a8d88", linewidth=0.8, linestyle="--")
    ax.set_title(title, color="white", fontsize=13, pad=12)
    ax.set_ylabel("Realized balance (USD)", color="#c9d8d4")
    ax.tick_params(colors="#9eb1ac")
    ax.grid(color="#31443f", alpha=0.35, linewidth=0.6)
    for spine in ax.spines.values():
        spine.set_color("#31443f")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def set_text(variant: dict, magic: int) -> str:
    values = {
        "InpMacroHourNY": variant["hour"], "InpMacroStartMinute": 50, "InpMacroEndMinute": 10,
        "InpServerUTCOffsetHours": 0, "InpTradeMonday": "true", "InpTradeTuesday": "true",
        "InpTradeWednesday": "true", "InpTradeThursday": "true", "InpTradeFriday": "true",
        "InpLiquidityLookbackBars": variant["lookback"], "InpATRPeriod": 14,
        "InpMinimumRangeATR": 1.5, "InpMaximumRangeATR": 8.0, "InpMinimumSweepATR": 0.05,
        "InpMaximumSweepATR": 2.5, "InpConfirmationMode": variant["confirm"],
        "InpOrderBlockLookbackBars": 8, "InpMinimumDisplacementATR": variant["displacement"],
        "InpRequireCloseBackInside": "true", "InpAllowLong": "true", "InpAllowShort": "true",
        "InpRiskPercent": 1.0, "InpStopBufferATR": 0.1, "InpMinimumRewardRisk": variant["min_rr"],
        "InpMaximumRewardRisk": 5.0, "InpMaximumSpreadATR": 0.12, "InpMaximumHoldingMinutes": 180,
        "InpMoveToBreakEven": str(variant["breakeven"]).lower(), "InpBreakEvenAtR": 1.0,
        "InpMaximumDeviationPoints": 50, "InpMagic": magic,
    }
    return "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"


def money(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--development", type=Path, required=True)
    parser.add_argument("--locked", type=Path, required=True)
    parser.add_argument("--selected", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selected = json.loads(args.selected.read_text(encoding="utf-8"))
    charts = args.output / "Charts"
    sets = args.output / "Sets"
    charts.mkdir(parents=True, exist_ok=True)
    sets.mkdir(parents=True, exist_ok=True)

    development_rows = []
    for path in sorted(args.development.glob("*.htm")):
        symbol, variant = identify(path, "development")
        row = parse_report(path)
        row.update(symbol=symbol, variant=variant, phase="development", report=str(path))
        development_rows.append(row)

    locked_rows = []
    for index, path in enumerate(sorted(args.locked.glob("*.htm")), start=1):
        symbol, variant = identify(path, "locked")
        row = parse_report(path)
        row.update(symbol=symbol, variant=variant, phase="locked", report=str(path))
        locked_rows.append(row)
        label = SYMBOL_LABELS[symbol]
        graph(row, charts / f"{symbol}-locked-equity.png", f"ICT Macro Liquidity Sweep — {label} M1 — locked year")
        (sets / f"SELECTED - {label} M1 - ICT Macro Liquidity Sweep - 1pct.set").write_text(
            set_text(VARIANTS[variant], 862980 + index), encoding="utf-8"
        )

    all_rows = development_rows + locked_rows
    with (args.output / "RESULTS.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        fields = ["phase", "symbol", "variant", "return_pct", "profit_factor", "win_rate_pct", "equity_dd_pct", "trades", "net", "commission", "swap", "history_quality"]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    lines = [
        "# ICT Macro Liquidity Sweep — native MT5 validation",
        "",
        "## Locked one-year result",
        "",
        "The configuration for each instrument was chosen only from the preceding development year. The table below is the untouched following year, so it is the decision table—not the development ranking.",
        "",
        "| Decision | Symbol / TF | Selected window and trigger | Return | PF | Win rate | Max equity DD | Trades | Net | Costs (commission / swap) |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in locked_rows:
        variant = VARIANTS[row["variant"]]
        decision = "KEEP CANDIDATE" if row["return_pct"] >= 5 and row["profit_factor"] >= 1.15 and row["trades"] >= 20 else "REJECT"
        trigger = f"{variant['hour']:02d}:50–{variant['hour'] + 1:02d}:10 NY; L{variant['lookback']}; confirm {variant['confirm']}"
        lines.append(
            f"| {decision} | {SYMBOL_LABELS[row['symbol']]} M1 | {trigger} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
            f"{row['win_rate_pct']:.2f}% | {row['equity_dd_pct']:.2f}% | {row['trades']} | {money(row['net'])} | "
            f"{money(row['commission'])} / {money(row['swap'])} |"
        )
    lines.extend(["", "## Locked equity graphs", ""])
    for row in locked_rows:
        label = SYMBOL_LABELS[row["symbol"]]
        lines.extend([f"### {label} M1", "", f"![{label} locked equity](Charts/{row['symbol']}-locked-equity.png)", ""])

    lines.extend([
        "## What was implemented",
        "",
        "- New York-local macro windows with U.S. daylight-saving conversion and an explicit broker UTC offset.",
        "- A pre-window liquidity range, range-width/ATR filter, one-side liquidity sweep, close back inside the range, and a later displacement confirmation.",
        "- Confirmation can be an inversion-style three-candle fair-value gap, a close through the nearest opposite candle (order-block proxy), or either/both.",
        "- Stop beyond the sweep, target at opposing range liquidity, minimum/maximum R gate, 1% equity risk, spread gate, optional break-even, and time exit.",
        "- One trade maximum per selected macro window per New York day.",
        "",
        "The transcript's SMT reference was not forced into the cross-asset tests. Genuine SMT needs a synchronized reference future such as ES against NQ; substituting unrelated CFD symbols for XAU or BTC would fabricate the rule. Breaker blocks are also not a separate trigger in this first deterministic version; the test uses FVG and order-block confirmation.",
        "",
        "## Development screen",
        "",
        "| Symbol | Variant | Return | PF | Win rate | Equity DD | Trades |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ])
    for row in sorted(development_rows, key=lambda item: (item["symbol"], -item["return_pct"])):
        marker = " **selected**" if selected[row["symbol"]]["variant"] == row["variant"] else ""
        lines.append(
            f"| {SYMBOL_LABELS[row['symbol']]} | {row['variant']}{marker} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
            f"{row['win_rate_pct']:.2f}% | {row['equity_dd_pct']:.2f}% | {row['trades']} |"
        )
    lines.extend([
        "",
        "## Test integrity",
        "",
        "- Broker: Exness MT5 Trial 16; symbols XAUUSD, USTEC, BTCUSD.",
        "- Native MT5 Every Tick model, random execution delay, $10,000 deposit, 1:2000 leverage, 1% calculated risk per trade.",
        "- Development: 2024-08-28 through 2025-08-27. Locked: 2025-08-28 through 2026-08-27.",
        "- MT5's native report statistics include modeled spread; the cost column is reconstructed from deal commission and swap.",
        "- No BAT or website deployment was made. A positive test remains historical evidence, not a payout or future-profit guarantee.",
    ])
    (args.output / "FULL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
