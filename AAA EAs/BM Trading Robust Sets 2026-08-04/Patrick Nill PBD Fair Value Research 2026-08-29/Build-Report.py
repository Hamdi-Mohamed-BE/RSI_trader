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
    "reclaim-r12-rr3": dict(mode=0, range_bars=12, impulse_bars=4, min_impulse=1.25, max_range=2.50, retest=True, follow=False, h4=False, session=False, rr=3.0, measured=False),
    "reclaim-r20-rr3": dict(mode=0, range_bars=20, impulse_bars=6, min_impulse=1.50, max_range=3.00, retest=True, follow=False, h4=False, session=False, rr=3.0, measured=False),
    "break-r12-direct-rr3": dict(mode=1, range_bars=12, impulse_bars=4, min_impulse=1.25, max_range=2.50, retest=False, follow=True, h4=False, session=False, rr=3.0, measured=False),
    "break-r20-retest-rr3": dict(mode=1, range_bars=20, impulse_bars=6, min_impulse=1.50, max_range=3.00, retest=True, follow=True, h4=False, session=False, rr=3.0, measured=False),
    "both-r20-rr3": dict(mode=2, range_bars=20, impulse_bars=6, min_impulse=1.50, max_range=3.00, retest=True, follow=False, h4=False, session=False, rr=3.0, measured=False),
    "both-r20-h4-rr3": dict(mode=2, range_bars=20, impulse_bars=6, min_impulse=1.50, max_range=3.00, retest=True, follow=False, h4=True, session=False, rr=3.0, measured=False),
    "both-r20-rr4": dict(mode=2, range_bars=20, impulse_bars=6, min_impulse=1.50, max_range=3.00, retest=True, follow=False, h4=False, session=False, rr=4.0, measured=True),
    "both-r32-day-rr3": dict(mode=2, range_bars=32, impulse_bars=8, min_impulse=1.50, max_range=3.50, retest=True, follow=False, h4=False, session=True, rr=3.0, measured=False),
}

SYMBOL_LABELS = {"xauusd": "XAUUSD", "btcusd": "BTCUSD", "ustec": "USTEC", "eurusd": "EURUSD"}


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
    wins = values.get("Profit Trades (% of total)", "")
    losses = values.get("Loss Trades (% of total)", "")
    equity_dd = values.get("Equity Drawdown Maximal", "")
    balance_dd = values.get("Balance Drawdown Maximal", "")
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
    match = re.match(rf"^(xauusd|btcusd|ustec|eurusd)--(.+)--{phase}\.htm$", path.name, re.I)
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
        "InpSignalTimeframe": 15,
        "InpATRPeriod": 14,
        "InpRangeBars": variant["range_bars"],
        "InpImpulseBars": variant["impulse_bars"],
        "InpMinimumImpulseATR": variant["min_impulse"],
        "InpMinimumRangeATR": 0.75,
        "InpMaximumRangeATR": variant["max_range"],
        "InpMinimumAlternatingTouches": 3,
        "InpTouchToleranceFraction": 0.15,
        "InpAllowDProfile": "false",
        "InpZoneMaximumBars": 192,
        "InpSetupMode": variant["mode"],
        "InpMinimumSweepATR": 0.05,
        "InpBreakoutBufferATR": 0.05,
        "InpRetestToleranceATR": 0.20,
        "InpMaximumRetestDepthFraction": 0.35,
        "InpConfirmationBars": 3,
        "InpRequireBreakoutRetest": str(variant["retest"]).lower(),
        "InpFollowImpulseOnly": str(variant["follow"]).lower(),
        "InpAllowLong": "true",
        "InpAllowShort": "true",
        "InpUseH4TrendFilter": str(variant["h4"]).lower(),
        "InpH4EMAPeriod": 50,
        "InpUseNewYorkSession": str(variant["session"]).lower(),
        "InpNewYorkStartHour": 2,
        "InpNewYorkEndHour": 16,
        "InpServerUTCOffsetHours": 0,
        "InpRiskPercent": 1.0,
        "InpStopBufferATR": 0.10,
        "InpRewardRisk": variant["rr"],
        "InpUseMeasuredImpulseTarget": str(variant["measured"]).lower(),
        "InpMaximumTargetR": 6.0,
        "InpMoveToBreakEven": "true",
        "InpBreakEvenAtR": 1.0,
        "InpUseStructureTrail": "true",
        "InpTrailStartR": 2.0,
        "InpTrailBufferATR": 0.10,
        "InpMaximumHoldingHours": 72,
        "InpMaximumSpreadATR": 0.12,
        "InpMaximumDeviationPoints": 50,
        "InpMagic": magic,
    }
    return "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"


def money(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def serializable(row: dict) -> dict:
    output = {key: value for key, value in row.items() if key != "deals"}
    balance = row["initial"]
    series = [{"time": "2025-08-28T00:00:00", "balance": balance}]
    for deal in row["deals"]:
        balance += deal["cashflow"]
        series.append({"time": deal["time"].isoformat(), "balance": round(balance, 2)})
    output["series"] = series
    return output


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
        graph(row, charts / f"{symbol}-locked-equity.png", f"PBD Fair Value Range Proxy — {label} M15 — locked year")
        (sets / f"SELECTED - {label} M15 - PBD Fair Value Proxy - 1pct.set").write_text(
            set_text(VARIANTS[variant], 86292980 + index), encoding="utf-8"
        )

    all_rows = development_rows + locked_rows
    with (args.output / "RESULTS.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        fields = ["phase", "symbol", "variant", "return_pct", "profit_factor", "win_rate_pct", "equity_dd_pct", "trades", "net", "commission", "swap", "history_quality"]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)
    (args.output / "RESULTS.json").write_text(
        json.dumps([serializable(row) for row in all_rows], indent=2), encoding="utf-8"
    )

    lines = [
        "# PBD Fair Value Range Proxy — native MT5 validation",
        "",
        "## Locked one-year decision table",
        "",
        "Each instrument's configuration was selected only from the preceding development year. These are the untouched following-year results.",
        "",
        "| Decision | Symbol / TF | Selected configuration | Return | PF | Win rate | Max equity DD | Trades | Net | Costs (commission / swap) |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in locked_rows:
        decision = "KEEP CANDIDATE" if row["return_pct"] >= 5 and row["profit_factor"] >= 1.15 and row["trades"] >= 20 else "REJECT"
        lines.append(
            f"| {decision} | {SYMBOL_LABELS[row['symbol']]} M15 | {row['variant']} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
            f"{row['win_rate_pct']:.2f}% | {row['equity_dd_pct']:.2f}% | {row['trades']} | {money(row['net'])} | "
            f"{money(row['commission'])} / {money(row['swap'])} |"
        )
    lines.extend(["", "## Locked equity graphs", ""])
    for row in locked_rows:
        label = SYMBOL_LABELS[row["symbol"]]
        lines.extend([f"### {label} M15", "", f"![{label} locked equity](Charts/{row['symbol']}-locked-equity.png)", ""])

    lines.extend([
        "## Deterministic rules tested",
        "",
        "- The M15 chart searches for an impulse followed by a compact fair-value range. The range must receive at least three alternating interactions with its upper and lower boundaries.",
        "- False-break reclaim: price sweeps outside a validated range, closes back inside, and a later directional candle closes beyond the reclaim candle.",
        "- Breakout confirmation: price closes outside a validated range and either confirms directly or retests the broken boundary before a further directional close, depending on the selected variant.",
        "- Stops sit beyond the sweep/retest structure with an ATR buffer. Targets are at least 3R; one candidate also tests a capped measured-impulse target.",
        "- Risk is 1% of current equity, with broker-aware volume, modeled spread, a spread/ATR gate, break-even at 1R, structure trailing from 2R and a 72-hour time exit.",
        "- Optional H4 EMA direction and New York daytime filters were candidates, not assumed to be universally beneficial.",
        "",
        "## What cannot be claimed",
        "",
        "Patrick explicitly says the precise zone-drawing, resizing, volume-profile and footprint rules remain secret and that his execution is discretionary. This EA is therefore a transparent systematic proxy for the public framework, not Patrick Nill's exact strategy and not an endorsement by him.",
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
        "- Broker: Exness MT5 Trial 16; XAUUSD, BTCUSD, USTEC and EURUSD.",
        "- Native MT5 Every Tick model, random execution delay, $10,000 initial balance, 1:2000 leverage and 1% calculated risk per trade.",
        "- Development: 2024-08-28 through 2025-08-27. Locked test: 2025-08-28 through 2026-08-27.",
        "- MT5 statistics include modeled broker spread. Commission and swap are reconstructed from the native deal ledger.",
        "- No active BAT or website file was changed.",
    ])
    (args.output / "FULL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
