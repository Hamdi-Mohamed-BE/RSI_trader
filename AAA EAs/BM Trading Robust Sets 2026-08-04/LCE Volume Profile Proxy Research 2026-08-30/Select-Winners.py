from __future__ import annotations
import argparse, json, re
from pathlib import Path
from bs4 import BeautifulSoup

SYMBOLS = ("us500", "ustec", "xauusd", "btcusd")

def compact(value: str) -> str: return " ".join(value.replace("\xa0", " ").split())
def number(value: str | None) -> float:
    match = re.search(r"[-+]?\d+(?:[,.]\d{3})*(?:\.\d+)?", compact(value or "").replace(" ", ""))
    return float(match.group(0).replace(",", "")) if match else 0.0
def percent(value: str | None) -> float:
    match = re.search(r"([-+]?\d+(?:\.\d+)?)%", compact(value or ""))
    return float(match.group(1)) if match else 0.0
def parse(path: Path) -> dict:
    soup = BeautifulSoup(path.read_text(encoding="utf-16", errors="replace"), "html.parser")
    values = {}
    for row in soup.find_all("tr"):
        cells = [compact(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"], recursive=False)]
        for index, cell in enumerate(cells[:-1]):
            if cell.endswith(":"): values[cell[:-1]] = cells[index + 1]
    initial = number(values.get("Initial Deposit")) or 10_000.0
    net = number(values.get("Total Net Profit"))
    return {"return_pct": net / initial * 100.0, "pf": number(values.get("Profit Factor")),
            "dd": percent(values.get("Equity Drawdown Maximal")), "trades": int(number(values.get("Total Trades"))),
            "win_rate": percent(values.get("Profit Trades (% of total)"))}
def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--reports", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    pattern = re.compile(r"^(us500|ustec|xauusd|btcusd)--(.+)--development\.htm$", re.I)
    rows = []
    for path in args.reports.glob("*.htm"):
        match = pattern.match(path.name)
        if not match: continue
        row = parse(path); row.update({"symbol": match.group(1).lower(), "variant": match.group(2), "report": str(path)})
        row["score"] = row["return_pct"] + 9.0 * (row["pf"] - 1.0) - 0.55 * row["dd"] - max(0, 30-row["trades"]) * 0.25
        if row["trades"] < 12 or row["pf"] <= 0.0: row["score"] = -1e9 + row["trades"]
        rows.append(row)
    selected = {}
    for symbol in SYMBOLS:
        candidates = [row for row in rows if row["symbol"] == symbol]
        if not candidates: raise RuntimeError(f"No development reports for {symbol}")
        selected[symbol] = max(candidates, key=lambda row: row["score"])
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(selected, indent=2), encoding="utf-8")
if __name__ == "__main__": main()

