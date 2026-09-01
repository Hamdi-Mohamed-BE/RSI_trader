from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re

from bs4 import BeautifulSoup


def compact(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def number(value: str | None) -> float:
    match = re.search(r"[-+]?\d+(?:[,.]\d{3})*(?:\.\d+)?", compact(value or "").replace(" ", ""))
    return float(match.group(0).replace(",", "")) if match else 0.0


def percent(value: str | None) -> float:
    match = re.search(r"([-+]?\d+(?:\.\d+)?)%", compact(value or ""))
    return float(match.group(1)) if match else 0.0


def metrics(path: Path) -> dict:
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
    return {
        "initial_balance": initial,
        "net_profit": net,
        "return_pct": net / initial * 100.0 if initial else 0.0,
        "equity_dd_pct": percent(values.get("Equity Drawdown Maximal")),
        "profit_factor": number(values.get("Profit Factor")),
        "recovery_factor": number(values.get("Recovery Factor")),
        "sharpe_ratio": number(values.get("Sharpe Ratio")),
        "trades": int(number(values.get("Total Trades"))),
        "wins": int(number(wins)),
        "win_rate_pct": percent(wins),
        "history_quality": values.get("History Quality", ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("report_dir", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    rows = []
    for case in json.loads(args.manifest.read_text(encoding="utf-8")):
        result = metrics(args.report_dir / f"{case['case']}.htm")
        train = case["train"]
        result.update({
            "case": case["case"],
            "set": case["set"],
            "train_profit": train.get("Profit", 0),
            "train_pf": train.get("Profit Factor", 0),
            "train_dd_pct": train.get("Equity DD %", 0),
            "train_trades": train.get("Trades", 0),
        })
        stable = result["net_profit"] > 0 and result["profit_factor"] >= 1.05 and result["trades"] >= 8
        result["passes_selection"] = stable
        result["selection_score"] = round(
            (result["net_profit"] / max(result["equity_dd_pct"], 1.0))
            * min(result["profit_factor"], 2.5)
            * min(1.25, (max(result["trades"], 1) / 25.0) ** 0.5)
            if stable else -1_000_000 + result["trades"], 6
        )
        rows.append(result)
    rows.sort(key=lambda row: row["selection_score"], reverse=True)
    output = args.out or args.manifest.with_name(args.manifest.stem.replace("manifest", "results") + ".json")
    output.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    with output.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
