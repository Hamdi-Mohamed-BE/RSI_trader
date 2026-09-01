from __future__ import annotations

import csv
import json
from pathlib import Path
import re
import shutil

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
BT = PACKAGE / "_Backtests" / "MT5-Isolated-20260805"
REPORT_SOURCE = BT / "reports" / "orb-volume-data"
SET_SOURCE = BT / "MQL5" / "Profiles" / "Tester"
REPORTS = ROOT / "Reports"
SETTINGS = ROOT / "Best Settings"

CASES = [
    {"key": "xau", "market": "Gold", "symbol": "XAUUSD", "set": "ORB XAU Candidate 07.set", "saved": "VALIDATED - XAUUSD M5 - 1pct.set"},
    {"key": "btc", "market": "Bitcoin", "symbol": "BTCUSD", "set": "ORB BTC Candidate 02.set", "saved": "REJECTED FINAL - BTCUSD M5 - 1pct.set"},
    {"key": "us30", "market": "Dow", "symbol": "US30", "set": "ORB US30LEN Candidate 04.set", "saved": "VALIDATED MODEST - US30 M5 - 1pct.set"},
    {"key": "ustec", "market": "Nasdaq", "symbol": "USTEC", "set": "ORB USTEC Candidate 03.set", "saved": "REJECTED FINAL - USTEC M5 - 1pct.set"},
    {"key": "us500", "market": "S&P 500", "symbol": "US500", "set": "ORB US500 Candidate 05.set", "saved": "REJECTED FINAL - US500 M5 - 1pct.set"},
]


def compact(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def number(value: str | None) -> float:
    match = re.search(r"[-+]?\d+(?:[,.]\d{3})*(?:\.\d+)?", compact(value or "").replace(" ", ""))
    return float(match.group(0).replace(",", "")) if match else 0.0


def percent(value: str | None) -> float:
    match = re.search(r"([-+]?\d+(?:\.\d+)?)%", compact(value or ""))
    return float(match.group(1)) if match else 0.0


def parse_report(path: Path) -> dict:
    soup = BeautifulSoup(path.read_text(encoding="utf-16"), "html.parser")
    values: dict[str, str] = {}
    for row in soup.find_all("tr"):
        cells = [compact(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"], recursive=False)]
        for index, cell in enumerate(cells[:-1]):
            if cell.endswith(":"):
                values[cell[:-1]] = cells[index + 1]
    initial = number(values.get("Initial Deposit")) or 10000.0
    net = number(values.get("Total Net Profit"))
    wins = values.get("Profit Trades (% of total)", "")
    losses = values.get("Loss Trades (% of total)", "")
    equity_dd = values.get("Equity Drawdown Maximal", "")
    balance_dd = values.get("Balance Drawdown Maximal", "")
    return {
        "initial_balance": initial,
        "final_balance": initial + net,
        "net_profit": net,
        "return_pct": net / initial * 100.0 if initial else 0.0,
        "equity_dd_amount": number(equity_dd),
        "equity_dd_pct": percent(equity_dd),
        "balance_dd_amount": number(balance_dd),
        "balance_dd_pct": percent(balance_dd),
        "profit_factor": number(values.get("Profit Factor")),
        "expected_payoff": number(values.get("Expected Payoff")),
        "recovery_factor": number(values.get("Recovery Factor")),
        "sharpe_ratio": number(values.get("Sharpe Ratio")),
        "trades": int(number(values.get("Total Trades"))),
        "wins": int(number(wins)),
        "losses": int(number(losses)),
        "win_rate_pct": percent(wins),
        "gross_profit": number(values.get("Gross Profit")),
        "gross_loss": number(values.get("Gross Loss")),
        "largest_win": number(values.get("Largest profit trade")),
        "largest_loss": number(values.get("Largest loss trade")),
        "average_win": number(values.get("Average profit trade")),
        "average_loss": number(values.get("Average loss trade")),
        "history_quality": values.get("History Quality", ""),
    }


def inputs(path: Path) -> dict[str, str]:
    result = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        result[name] = value.split("||", 1)[0]
    return result


def money(value: float) -> str:
    return f"${value:,.2f}"


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    SETTINGS.mkdir(exist_ok=True)
    rows = []
    for case in CASES:
        report = REPORT_SOURCE / f"final-{case['key']}.htm"
        row = {**case, **parse_report(report)}
        row["pass"] = (
            row["net_profit"] > 0
            and row["profit_factor"] >= 1.15
            and row["equity_dd_pct"] <= 12.0
            and row["trades"] >= 20
        )
        row["status"] = "PASS" if row["pass"] else "REJECT"
        row["report"] = f"Reports/final-{case['key']}.htm"
        row["graph"] = f"Reports/final-{case['key']}.png"
        row["settings"] = f"Best Settings/{case['saved']}"
        row["inputs"] = inputs(SET_SOURCE / case["set"])
        rows.append(row)
        shutil.copy2(report, REPORTS / report.name)
        graph = report.with_suffix(".png")
        if graph.exists():
            shutil.copy2(graph, REPORTS / graph.name)
        shutil.copy2(SET_SOURCE / case["set"], SETTINGS / case["saved"])

    (ROOT / "final-results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    flat_rows = [{key: value for key, value in row.items() if key != "inputs"} for row in rows]
    with (ROOT / "final-results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0]))
        writer.writeheader()
        writer.writerows(flat_rows)

    lines = [
        "# ORB Volume + Data EA — final honest report",
        "",
        "## Verdict",
        "",
        "There is no perfect universal ORB preset in this test. XAUUSD passed cleanly and US30 passed with a small edge. BTCUSD, USTEC, and US500 failed the untouched final year and are not approved for live deployment.",
        "",
        "## Untouched final-year results",
        "",
        "- Window: 2025-08-07 through 2026-08-06",
        "- Broker/history: Exness `Exness-MT5Trial16` CFDs",
        "- Initial balance: USD 10,000 per independent test",
        "- Risk: 1.00% of current equity per trade",
        "- Engine: MT5 Every Tick from broker M1 history with random execution delay",
        "- Chart: M5; maximum one position per market per session; forced intraday flat",
        "- Pass gate: positive net profit, PF at least 1.15, equity DD no more than 12%, and at least 20 trades",
        "",
        "| Status | Market | Symbol | Final | Net | Return | Equity DD | PF | Win rate | Wins / losses | Trades | History |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['status']} | {row['market']} | {row['symbol']} M5 | {money(row['final_balance'])} | "
            f"{money(row['net_profit'])} | {row['return_pct']:+.2f}% | {row['equity_dd_pct']:.2f}% | "
            f"{row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['wins']} / {row['losses']} | "
            f"{row['trades']} | {row['history_quality']} |"
        )

    lines += [
        "",
        "## Detailed trade statistics",
        "",
        "| Symbol | Gross profit | Gross loss | Largest win | Largest loss | Average win | Average loss | Balance DD | Recovery | Sharpe |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['symbol']} | {money(row['gross_profit'])} | {money(row['gross_loss'])} | "
            f"{money(row['largest_win'])} | {money(row['largest_loss'])} | {money(row['average_win'])} | "
            f"{money(row['average_loss'])} | {money(row['balance_dd_amount'])} ({row['balance_dd_pct']:.2f}%) | "
            f"{row['recovery_factor']:.2f} | {row['sharpe_ratio']:.2f} |"
        )

    lines += [
        "",
        "## Locked presets",
        "",
        "| Symbol | NY anchor | OR | Opening relative tick volume | Breakout relative tick volume | Range / ATR | Entry | Body minimum | Stop | Target | Result |",
        "|---|---:|---:|---:|---:|---:|---|---:|---|---:|---|",
    ]
    for row in rows:
        cfg = row["inputs"]
        stop = "opposite OR" if cfg["InpStopMode"] == "1" else "signal candle"
        lines.append(
            f"| {row['symbol']} | {cfg['InpSessionHour']}:{int(cfg['InpSessionMinute']):02d} | "
            f"{cfg['InpOpeningRangeMinutes']} min | ≥ {cfg['InpMinOpeningRelativeVolume']}× | "
            f"≥ {cfg['InpMinBreakoutRelativeVolume']}× | {cfg['InpMinRangeATR']}–{cfg['InpMaxRangeATR']} | "
            f"direct breakout | {float(cfg['InpBreakoutBodyMinimum'])*100:.0f}% | {stop} | {cfg['InpRewardRisk']}R | {row['status']} |"
        )

    lines += [
        "",
        "## Validation design",
        "",
        "1. Development/optimization: 2022-01-03 through 2024-12-31.",
        "2. Candidate selection without optimization: 2025-01-01 through 2025-08-06.",
        "3. Locked final test: 2025-08-07 through 2026-08-06. Final results were not used to choose another preset.",
        "",
        "This avoids the dishonest practice of selecting the best settings on the same year being advertised. It does not remove market-regime risk or prove future profitability.",
        "",
        "## Volume-data limitation",
        "",
        "Exness CFD history exposes tick volume, not consolidated exchange volume. The EA therefore compares each opening window and breakout bar with its own recent tick-volume baseline. That is a useful activity proxy, but it is not CME, COMEX, NYSE, Nasdaq, or consolidated crypto volume.",
        "",
        "## Research basis",
        "",
        "- [NYSE auction schedule](https://www.nyse.com/trade/auctions): the core opening auction begins at 09:30 New York time.",
        "- [Zarattini, Barbon, and Aziz — US equity ORB](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284): large-sample evidence emphasizes unusually active stocks and compares several opening-range lengths.",
        "- [Wang and Gangwar — ORB robustness study](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5198458): volume thresholds and 5/15/30-minute variants are tested, but statistical significance remains inconclusive—an important warning against overclaiming.",
        "- [Graczyk and Queirós — intraday volume nonstationarity](https://arxiv.org/abs/1810.12099): opening volume/volatility patterns exist but change across regimes.",
        "- [Bitcoin intraday price discovery](https://doi.org/10.1016/j.ribaf.2022.101625): London–New York overlap dominates price discovery in the sample, although the 08:00 New York variant failed our later broker-data selection test.",
        "",
        "Native MT5 HTML reports and equity graphs are under `Reports`. Settings are under `Best Settings`; rejected presets are labeled explicitly and should not be deployed.",
    ]
    (ROOT / "FULL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    readme = [
        "# ORB Volume Data EA",
        "",
        "A single native MT5 EA with market-specific SET files. It builds a New York opening range, requires relative tick-volume and ATR-regime confirmation, enters only a completed-candle breakout, sizes by planned stop risk, moves to break-even at 1R, and exits intraday.",
        "",
        "Use only presets marked `VALIDATED`. Read `FULL REPORT.md` before deployment. Historical performance is not a guarantee.",
    ]
    (ROOT / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    print(json.dumps([{key: row[key] for key in ("market", "symbol", "status", "return_pct", "equity_dd_pct", "profit_factor", "win_rate_pct", "trades")} for row in rows], indent=2))


if __name__ == "__main__":
    main()
