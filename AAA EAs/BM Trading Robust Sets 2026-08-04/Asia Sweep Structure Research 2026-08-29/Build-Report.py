from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
from bs4 import BeautifulSoup


SYMBOLS = ("eurusd", "usdjpy", "gbpjpy", "audchf", "gbpusd", "usdchf", "usdcad", "audusd", "nzdusd")
LABELS = {symbol: symbol.upper() for symbol in SYMBOLS}
VARIANTS = {
    "literal-20-00-max12-rr15": dict(asia_start=20, asia_end=0, entry_start=0, entry_end=5, min_bars=30, max_bars=12, lookback=12, swing=1, sweep=0.03, mid_r=0.0, rr=1.5, be=False),
    "fast-20-00-max6-rr15": dict(asia_start=20, asia_end=0, entry_start=0, entry_end=5, min_bars=30, max_bars=6, lookback=10, swing=1, sweep=0.03, mid_r=0.0, rr=1.5, be=False),
    "strict-20-00-mid1-rr15": dict(asia_start=20, asia_end=0, entry_start=0, entry_end=5, min_bars=30, max_bars=12, lookback=12, swing=1, sweep=0.05, mid_r=1.0, rr=1.5, be=False),
    "strict-20-00-mid15-rr15": dict(asia_start=20, asia_end=0, entry_start=0, entry_end=5, min_bars=30, max_bars=12, lookback=12, swing=1, sweep=0.05, mid_r=1.5, rr=1.5, be=False),
    "early-19-00-max12-rr15": dict(asia_start=19, asia_end=0, entry_start=0, entry_end=5, min_bars=36, max_bars=12, lookback=12, swing=1, sweep=0.03, mid_r=0.0, rr=1.5, be=False),
    "late-20-01-max12-rr15": dict(asia_start=20, asia_end=1, entry_start=1, entry_end=6, min_bars=30, max_bars=12, lookback=12, swing=1, sweep=0.03, mid_r=0.0, rr=1.5, be=False),
    "literal-20-00-max12-rr20": dict(asia_start=20, asia_end=0, entry_start=0, entry_end=5, min_bars=30, max_bars=12, lookback=12, swing=1, sweep=0.03, mid_r=0.0, rr=2.0, be=False),
    "literal-20-00-be1-rr15": dict(asia_start=20, asia_end=0, entry_start=0, entry_end=5, min_bars=30, max_bars=12, lookback=12, swing=1, sweep=0.03, mid_r=0.0, rr=1.5, be=True),
}


def compact(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def number(value: str | None) -> float:
    match = re.search(r"[-+]?\d+(?:[,.]\d{3})*(?:\.\d+)?", compact(value or "").replace(" ", ""))
    return float(match.group(0).replace(",", "")) if match else 0.0


def percent(value: str | None) -> float:
    match = re.search(r"([-+]?\d+(?:\.\d+)?)%", compact(value or ""))
    return float(match.group(1)) if match else 0.0


def parse(path: Path) -> dict:
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
        deals.append({
            "time": datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S"),
            "commission": number(cells[8]), "swap": number(cells[9]), "profit": number(cells[10]),
            "cashflow": number(cells[8]) + number(cells[9]) + number(cells[10]),
        })
    initial = number(values.get("Initial Deposit")) or 10_000.0
    net = number(values.get("Total Net Profit"))
    wins = values.get("Profit Trades (% of total)", "")
    losses = values.get("Loss Trades (% of total)", "")
    equity_dd = values.get("Equity Drawdown Maximal", "")
    balance_dd = values.get("Balance Drawdown Maximal", "")
    return {
        "initial": initial, "final": initial + net, "net": net,
        "return_pct": net / initial * 100.0 if initial else 0.0,
        "profit_factor": number(values.get("Profit Factor")), "win_rate_pct": percent(wins),
        "wins": int(number(wins)), "losses": int(number(losses)), "trades": int(number(values.get("Total Trades"))),
        "equity_dd_amount": number(equity_dd), "equity_dd_pct": percent(equity_dd),
        "balance_dd_amount": number(balance_dd), "balance_dd_pct": percent(balance_dd),
        "gross_profit": number(values.get("Gross Profit")), "gross_loss": number(values.get("Gross Loss")),
        "largest_win": number(values.get("Largest profit trade")), "largest_loss": number(values.get("Largest loss trade")),
        "average_win": number(values.get("Average profit trade")), "average_loss": number(values.get("Average loss trade")),
        "expected_payoff": number(values.get("Expected Payoff")), "recovery_factor": number(values.get("Recovery Factor")),
        "sharpe": number(values.get("Sharpe Ratio")), "history_quality": values.get("History Quality", ""),
        "commission": sum(item["commission"] for item in deals), "swap": sum(item["swap"] for item in deals), "deals": deals,
    }


def identify(path: Path, phase: str) -> tuple[str, str]:
    symbols = "|".join(SYMBOLS)
    match = re.match(rf"^({symbols})--(.+)--{phase}\.htm$", path.name, re.I)
    if not match:
        raise ValueError(path.name)
    return match.group(1).lower(), match.group(2)


def graph(row: dict, path: Path, title: str) -> None:
    balance = row["initial"]
    times, balances = [], []
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


def combined_graph(rows: list[dict], path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11.5, 5.6), dpi=170)
    fig.patch.set_facecolor("#07110f")
    ax.set_facecolor("#0b1714")
    for row in sorted(rows, key=lambda item: item["return_pct"], reverse=True):
        balance = row["initial"]
        times, returns = [], []
        for deal in row["deals"]:
            balance += deal["cashflow"]
            times.append(deal["time"])
            returns.append((balance / row["initial"] - 1.0) * 100.0)
        if times:
            ax.plot(times, returns, linewidth=1.45, label=row["symbol"])
    ax.axhline(0.0, color="#9eb1ac", linewidth=0.9, linestyle="--")
    ax.set_title("Asia sweep structure shift — locked return by pair", color="white", fontsize=14, pad=12)
    ax.set_ylabel("Return from $10,000 (%)", color="#c9d8d4")
    ax.tick_params(colors="#9eb1ac")
    ax.grid(color="#31443f", alpha=0.35, linewidth=0.6)
    ax.legend(loc="best", ncol=3, facecolor="#0b1714", edgecolor="#31443f", labelcolor="white", fontsize=8)
    for spine in ax.spines.values():
        spine.set_color("#31443f")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def set_text(variant: dict, magic: int) -> str:
    values = {
        "InpSignalTimeframe": 5, "InpATRPeriod": 14,
        "InpAsiaStartHourNY": variant["asia_start"], "InpAsiaEndHourNY": variant["asia_end"],
        "InpEntryStartHourNY": variant["entry_start"], "InpEntryEndHourNY": variant["entry_end"],
        "InpServerUTCOffsetHours": 0, "InpMinimumAsiaBars": variant["min_bars"],
        "InpMinimumAsiaRangeATR": 1.0, "InpMaximumAsiaRangeATR": 8.0,
        "InpMinimumSweepATR": variant["sweep"], "InpMaximumBarsAfterSweep": variant["max_bars"],
        "InpStructureLookbackBars": variant["lookback"], "InpSwingStrength": variant["swing"],
        "InpBOSBufferATR": 0.0, "InpRequireReclaimClose": "true", "InpRequireDirectionalBOSCandle": "true",
        "InpMinimumMidpointR": variant["mid_r"], "InpAllowLong": "true", "InpAllowShort": "true",
        "InpOneTradePerDay": "true", "InpRiskPercent": 1.0, "InpStopBufferATR": 0.05,
        "InpRewardRisk": variant["rr"], "InpMoveToBreakEven": str(variant["be"]).lower(),
        "InpBreakEvenAtR": 1.0, "InpCloseAtNewYorkHour": "true", "InpForcedCloseHourNY": 12,
        "InpMaximumSpreadATR": 0.08, "InpMaximumDeviationPoints": 30, "InpMagic": magic,
    }
    return "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"


def decision(row: dict) -> str:
    if (
        row["return_pct"] >= 5.0
        and row["profit_factor"] >= 1.15
        and row["equity_dd_pct"] <= 15.0
        and row["trades"] >= 20
        and row.get("development_return_pct", 0.0) > 0.0
        and row.get("development_pf", 0.0) >= 1.10
        and row.get("development_trades", 0) >= 15
    ):
        return "KEEP CANDIDATE"
    if row["return_pct"] > 0.0 and row["profit_factor"] > 1.0:
        return "WATCH — NOT ROBUST"
    return "REJECT"


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
    development_rows = {}
    for path in args.development.glob("*.htm"):
        try:
            symbol, variant = identify(path, "development")
        except ValueError:
            continue
        development_rows[(symbol, variant)] = parse(path)
    rows = []
    detail_rows = []
    for path in args.locked.glob("*.htm"):
        try:
            symbol, variant = identify(path, "locked")
        except ValueError:
            continue
        row = parse(path)
        row.update({"symbol": LABELS[symbol], "slug": symbol, "variant": variant})
        dev = development_rows.get((symbol, variant), {})
        row["development_return_pct"] = dev.get("return_pct", 0.0)
        row["development_pf"] = dev.get("profit_factor", 0.0)
        row["development_dd_pct"] = dev.get("equity_dd_pct", 0.0)
        row["development_trades"] = dev.get("trades", 0)
        row["decision"] = decision(row)
        graph(row, charts / f"{symbol}-locked-equity.png", f"{LABELS[symbol]} — locked 2025-08-29 to 2026-08-28")
        (sets / f"SELECTED - {LABELS[symbol]} M5 - Asia Sweep Structure - 1pct.set").write_text(
            set_text(VARIANTS[variant], 86310000 + len(rows)), encoding="utf-8"
        )
        serializable = {key: value for key, value in row.items() if key != "deals"}
        detail_rows.append(row)
        rows.append(serializable)
    combined_graph(detail_rows, charts / "all-pairs-locked-equity.png")
    rows.sort(key=lambda row: row["return_pct"], reverse=True)
    (args.output / "RESULTS.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    fields = [key for key in rows[0].keys()] if rows else []
    with (args.output / "RESULTS.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# Asia Sweep + Structure Shift — MT5 walk-forward validation",
        "",
        "This is an objective implementation of the supplied rules, not the private LuxAlgo indicator. The Asia range is anchored to New York time with automatic US daylight-saving conversion.",
        "",
        "## Locked last-year results",
        "",
        "| Pair | Selected variant | Development return / PF | Locked return / PF | Win rate | Equity DD | Trades | Decision |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['symbol']} | {row['variant']} | {row['development_return_pct']:+.2f}% / {row['development_pf']:.2f} | "
            f"{row['return_pct']:+.2f}% / {row['profit_factor']:.2f} | "
            f"{row['win_rate_pct']:.2f}% | {row['equity_dd_pct']:.2f}% | {row['trades']} | {row['decision']} |"
        )
    lines.extend([
        "", "## Rules tested", "",
        "- Build the Asia range from the selected New York evening window.",
        "- Require a closed M5 candle to sweep an Asia boundary and reclaim it.",
        "- Record the most recent confirmed internal swing, then enter only after a directional close breaks that structure within the allowed bar count.",
        "- Stop beyond the sweep extreme plus 0.05 ATR; target 1.5R or 2R depending on the development variant.",
        "- At most one trade per pair per day; close any remainder at 12:00 New York.",
        "", "## Test integrity", "",
        "- Broker: Exness MT5 Trial 16; native MT5 Every Tick model with random execution delay.",
        "- Initial balance: $10,000; leverage 1:2000; calculated risk: 1% of current equity per trade.",
        "- Development selection: 2024-08-29 through 2025-08-28. Untouched locked test: 2025-08-29 through 2026-08-28.",
        "- MT5 spread, commission and swap are included. Results are historical research, not a profit guarantee.",
        "- No active BAT or website file was changed by this research.",
    ])
    (args.output / "FULL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
