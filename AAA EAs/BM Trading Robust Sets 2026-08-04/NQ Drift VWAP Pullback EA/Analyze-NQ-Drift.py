from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup


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
        "initial": initial,
        "final": initial + net,
        "net": net,
        "return_pct": net / initial * 100.0 if initial else 0.0,
        "equity_dd_amount": number(equity_dd),
        "equity_dd_pct": percent(equity_dd),
        "balance_dd_amount": number(balance_dd),
        "balance_dd_pct": percent(balance_dd),
        "profit_factor": number(values.get("Profit Factor")),
        "trades": int(number(values.get("Total Trades"))),
        "wins": int(number(wins)),
        "losses": int(number(losses)),
        "win_rate_pct": percent(wins),
        "expected_payoff": number(values.get("Expected Payoff")),
        "recovery_factor": number(values.get("Recovery Factor")),
        "sharpe": number(values.get("Sharpe Ratio")),
        "gross_profit": number(values.get("Gross Profit")),
        "gross_loss": number(values.get("Gross Loss")),
        "largest_win": number(values.get("Largest profit trade")),
        "largest_loss": number(values.get("Largest loss trade")),
        "average_win": number(values.get("Average profit trade")),
        "average_loss": number(values.get("Average loss trade")),
        "history_quality": values.get("History Quality", ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    cases = json.loads(args.manifest.read_text(encoding="utf-8"))
    rows = []
    for case in cases:
        row = {**case, **parse_report(Path(case["report"]))}
        row.pop("config", None); row.pop("set", None); row.pop("report", None)
        rows.append(row)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix(".json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    with args.output.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    for row in sorted(rows, key=lambda r: (r["net"] > 0, r["profit_factor"], r["return_pct"]), reverse=True):
        print(f"{row['variant']:12} ret {row['return_pct']:+7.2f}%  DD {row['equity_dd_pct']:6.2f}%  "
              f"PF {row['profit_factor']:5.2f}  win {row['win_rate_pct']:6.2f}%  trades {row['trades']:4}")


if __name__ == "__main__":
    main()
