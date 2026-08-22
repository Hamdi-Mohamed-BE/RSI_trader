from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent
NEW_YORK = ZoneInfo("America/New_York")
REPORTS = {
    "training": ROOT / "Backtest Reports/selected/Training/training-2020-2023.htm",
    "validation": ROOT / "Backtest Reports/selected/Validation/validation-2024-h1-2025.htm",
    "recent": ROOT / "Backtest Reports/selected/Locked/locked-2025h2-2026.htm",
    "full": ROOT / "Backtest Reports/selected/Full/full-2020-2026.htm",
}


def number(value: str) -> float:
    return float(value.replace(" ", "").replace(",", "")) if value else 0.0


def parse(path: Path) -> list[dict]:
    raw = path.read_bytes()
    text = raw.decode("utf-16")
    soup = BeautifulSoup(text, "html.parser")
    in_deals = False
    open_trade: dict | None = None
    trades: list[dict] = []
    for row in soup.find_all("tr"):
        row_text = " ".join(row.get_text(" ").split())
        if row_text == "Deals":
            in_deals = True
            continue
        if not in_deals:
            continue
        cells = [" ".join(cell.get_text(" ").split()) for cell in row.find_all("td")]
        if len(cells) != 13 or not re.fullmatch(r"\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}", cells[0]):
            continue
        if cells[3].lower() == "balance":
            continue
        timestamp = datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)
        if cells[4].lower() == "in":
            open_trade = {
                "entry_utc": timestamp.isoformat(),
                "entry_ny": timestamp.astimezone(NEW_YORK).isoformat(),
                "direction": cells[3].lower(),
                "volume": number(cells[5]),
                "entry": number(cells[6]),
                "commission": number(cells[8]),
                "swap": number(cells[9]),
                "profit": number(cells[10]),
            }
            continue
        if cells[4].lower() == "out" and open_trade is not None:
            open_trade["exit_utc"] = timestamp.isoformat()
            open_trade["exit_ny"] = timestamp.astimezone(NEW_YORK).isoformat()
            open_trade["exit"] = number(cells[6])
            open_trade["commission"] += number(cells[8])
            open_trade["swap"] += number(cells[9])
            open_trade["profit"] += number(cells[10])
            open_trade["net"] = open_trade["profit"] + open_trade["commission"] + open_trade["swap"]
            ny = timestamp.astimezone(NEW_YORK)
            entry_ny = datetime.fromisoformat(open_trade["entry_ny"])
            open_trade["weekday"] = entry_ny.strftime("%a")
            open_trade["year"] = entry_ny.year
            minute = entry_ny.hour * 60 + entry_ny.minute
            if minute < 10 * 60 + 30:
                open_trade["entry_window"] = "10:00-10:29"
            elif minute < 11 * 60:
                open_trade["entry_window"] = "10:30-10:59"
            else:
                open_trade["entry_window"] = "11:00-11:29"
            trades.append(open_trade)
            open_trade = None
    return trades


def stats(trades: list[dict]) -> dict:
    gains = sum(trade["net"] for trade in trades if trade["net"] > 0)
    losses = -sum(trade["net"] for trade in trades if trade["net"] < 0)
    balance = peak = 10000.0
    max_dd = 0.0
    for trade in trades:
        balance += trade["net"]
        peak = max(peak, balance)
        max_dd = max(max_dd, (peak - balance) / peak * 100.0)
    return {
        "trades": len(trades),
        "net": round(sum(trade["net"] for trade in trades), 2),
        "return_pct": round(sum(trade["net"] for trade in trades) / 100.0, 2),
        "profit_factor": round(gains / losses, 3) if losses else None,
        "win_rate": round(sum(trade["net"] > 0 for trade in trades) / len(trades) * 100.0, 2) if trades else 0.0,
        "realized_dd_pct": round(max_dd, 2),
    }


def grouped(trades: list[dict], key: str) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)
    for trade in trades:
        groups[str(trade[key])].append(trade)
    return {name: stats(items) for name, items in sorted(groups.items())}


output = {}
for segment, report in REPORTS.items():
    trades = parse(report)
    output[segment] = {
        "all": stats(trades),
        "direction": grouped(trades, "direction"),
        "entry_window": grouped(trades, "entry_window"),
        "weekday": grouped(trades, "weekday"),
        "year": grouped(trades, "year"),
        "trades": trades,
    }

(ROOT / "v1-trade-diagnosis.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
for segment, item in output.items():
    print(f"\n{segment.upper()} {item['all']}")
    for dimension in ("direction", "entry_window", "weekday", "year"):
        print(dimension, item[dimension])
