from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent
REPORT_DIR = ROOT / "Reports" / "MT5 Exness XAUUSD 2021-08-15 to 2026-08-14"


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
    commission = 0.0
    swap = 0.0
    for row in soup.find_all("tr"):
        cells = [compact(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"], recursive=False)]
        for index, cell in enumerate(cells[:-1]):
            if cell.endswith(":"):
                values[cell[:-1]] = cells[index + 1]
        # MT5 deal rows contain Time, Deal, Symbol, Type, Direction, Volume,
        # Price, Order, Commission, Swap, Profit, Balance and Comment.
        if len(cells) == 13 and cells[4] in {"in", "out", "in/out", "out by"}:
            commission += number(cells[8])
            swap += number(cells[9])
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
        "commission": round(commission, 2),
        "swap": round(swap, 2),
        "total_charges": round(commission + swap, 2),
        "largest_win": number(values.get("Largest profit trade")),
        "largest_loss": number(values.get("Largest loss trade")),
        "average_win": number(values.get("Average profit trade")),
        "average_loss": number(values.get("Average loss trade")),
        "history_quality": values.get("History Quality", ""),
        "bars": int(number(values.get("Bars"))),
        "ticks": int(number(values.get("Ticks"))),
    }


def main() -> None:
    manifest = json.loads((REPORT_DIR / "manifest.json").read_text(encoding="utf-8-sig"))
    rows = []
    for case in manifest:
        metrics = parse_report(Path(case["report"]))
        rows.append({**case, **metrics})
    (REPORT_DIR / "summary.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    with (REPORT_DIR / "summary.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(
            f"{row['id']:27} ret {row['return_pct']:+8.2f}%  DD {row['equity_dd_pct']:6.2f}%  "
            f"PF {row['profit_factor']:6.2f}  win {row['win_rate_pct']:6.2f}%  trades {row['trades']:4}"
        )


if __name__ == "__main__":
    main()
