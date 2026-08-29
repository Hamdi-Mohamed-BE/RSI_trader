from __future__ import annotations

import argparse
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


def parse(path: Path) -> dict:
    soup = BeautifulSoup(path.read_text(encoding="utf-16", errors="replace"), "html.parser")
    values: dict[str, str] = {}
    for row in soup.find_all("tr"):
        cells = [compact(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"], recursive=False)]
        for index, cell in enumerate(cells[:-1]):
            if cell.endswith(":"):
                values[cell[:-1]] = cells[index + 1]
    initial = number(values.get("Initial Deposit")) or 10_000.0
    net = number(values.get("Total Net Profit"))
    pf = number(values.get("Profit Factor"))
    dd = percent(values.get("Equity Drawdown Maximal"))
    trades = int(number(values.get("Total Trades")))
    win = percent(values.get("Profit Trades (% of total)"))
    return {"net": net, "return_pct": net / initial * 100.0, "pf": pf, "dd": dd, "trades": trades, "win_rate": win}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows: list[dict] = []
    pattern = re.compile(r"^(xauusd|ustec|btcusd)--(.+)--development\.htm$", re.I)
    for path in args.reports.glob("*.htm"):
        match = pattern.match(path.name)
        if not match:
            continue
        row = parse(path)
        row.update({"symbol": match.group(1).lower(), "variant": match.group(2), "report": str(path)})
        # Prefer genuine samples. Penalize sparse tests and drawdown; do not select on return alone.
        sample_penalty = max(0, 20 - row["trades"]) * 0.15
        row["score"] = row["return_pct"] + 8.0 * (row["pf"] - 1.0) - 0.6 * row["dd"] - sample_penalty
        if row["trades"] < 5:
            row["score"] = -1e9 + row["trades"]
        rows.append(row)
    selected: dict[str, dict] = {}
    for symbol in ("xauusd", "ustec", "btcusd"):
        candidates = [row for row in rows if row["symbol"] == symbol]
        if not candidates:
            raise RuntimeError(f"No reports for {symbol}")
        selected[symbol] = max(candidates, key=lambda row: row["score"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(selected, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
