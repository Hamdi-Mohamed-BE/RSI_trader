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
    equity_dd = values.get("Equity Drawdown Maximal", "")
    return {
        "initial": initial,
        "net": net,
        "return_pct": net / initial * 100.0 if initial else 0.0,
        "equity_dd_pct": percent(equity_dd),
        "profit_factor": number(values.get("Profit Factor")),
        "trades": int(number(values.get("Total Trades"))),
        "win_rate_pct": percent(wins),
        "recovery_factor": number(values.get("Recovery Factor")),
        "sharpe": number(values.get("Sharpe Ratio")),
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
        report = Path(case["report"])
        row = {**case, **parse_report(report)}
        row.pop("config", None)
        row.pop("set", None)
        row.pop("report", None)
        rows.append(row)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix(".json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    with args.output.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for market in sorted({row["market"] for row in rows}):
        print(f"\n{market.upper()}")
        subset = sorted((row for row in rows if row["market"] == market),
                        key=lambda row: (row["net"] > 0, row["profit_factor"], row["return_pct"]), reverse=True)
        for row in subset:
            print(f"{row['variant']:12} ret {row['return_pct']:+7.2f}%  DD {row['equity_dd_pct']:6.2f}%  "
                  f"PF {row['profit_factor']:5.2f}  trades {row['trades']:4}")


if __name__ == "__main__":
    main()
