from __future__ import annotations

import argparse
import csv
import json
import math
import re
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup


def clean_number(value: str) -> float:
    value = value.replace("\xa0", " ").replace(" ", "").replace(",", "")
    return float(value) if value and value != "-" else 0.0


def match(text: str, pattern: str, default: str = "0") -> str:
    found = re.search(pattern, text)
    return found.group(1).strip() if found else default


def read_report(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def parse_report(path: Path) -> dict:
    soup = BeautifulSoup(read_report(path), "html.parser")
    text = " ".join(soup.get_text(" ").split())
    initial = clean_number(match(text, r"Initial Deposit:\s*([\d .]+?)\s+Leverage:"))
    net = clean_number(match(text, r"Total Net Profit:\s*([-\d .]+?)\s+Balance Drawdown Absolute:"))
    gross_profit = clean_number(match(text, r"Gross Profit:\s*([-\d .]+?)\s+Balance Drawdown Maximal:"))
    gross_loss = clean_number(match(text, r"Gross Loss:\s*([-\d .]+?)\s+Balance Drawdown Relative:"))
    equity_dd_amount = clean_number(match(text, r"Equity Drawdown Maximal:\s*([-\d .]+?)\s*\("))
    equity_dd_pct = float(match(text, r"Equity Drawdown Maximal:\s*[-\d .]+\s*\(([\d.]+)%\)"))
    balance_dd_amount = clean_number(match(text, r"Balance Drawdown Maximal:\s*([-\d .]+?)\s*\("))
    balance_dd_pct = float(match(text, r"Balance Drawdown Maximal:\s*[-\d .]+\s*\(([\d.]+)%\)"))
    profit_factor = float(match(text, r"Profit Factor:\s*([\d.]+)"))
    trades = int(match(text, r"Total Trades:\s*(\d+)"))
    wins = int(match(text, r"Profit Trades \(% of total\):\s*(\d+)"))
    losses = int(match(text, r"Loss Trades \(% of total\):\s*(\d+)"))
    win_rate = float(match(text, r"Profit Trades \(% of total\):\s*\d+\s*\(([\d.]+)%\)"))
    quality = float(match(text, r"History Quality:\s*([\d.]+)%"))
    bars = int(match(text, r"Bars:\s*(\d+)"))
    ticks = int(match(text, r"Ticks:\s*(\d+)"))
    period = match(text, r"Period:\s*(.*?)\s+Inputs:", "unknown")
    dates = re.search(r"\((\d{4}\.\d{2}\.\d{2})\s*-\s*(\d{4}\.\d{2}\.\d{2})\)", period)
    start_date = dates.group(1).replace(".", "-") if dates else ""
    end_date = dates.group(2).replace(".", "-") if dates else ""
    commission = 0.0
    swap = 0.0
    series = [{"date": start_date, "balance": initial}] if start_date else []
    in_deals = False
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
        commission += clean_number(cells[8])
        swap += clean_number(cells[9])
        balance = clean_number(cells[11])
        if balance > 0 and (not series or series[-1]["balance"] != balance):
            when = datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S").isoformat(sep=" ")
            series.append({"date": when, "balance": balance})
    final_balance = initial + net
    if end_date and (not series or series[-1]["balance"] != final_balance):
        series.append({"date": end_date, "balance": final_balance})
    parts = path.stem.split("__", 1)
    symbol = parts[0].upper()
    variant = parts[1] if len(parts) > 1 else "unknown"
    return_pct = net / initial * 100.0 if initial else 0.0
    score = return_pct - 1.5 * equity_dd_pct + 4.0 * math.log(max(profit_factor, 0.05))
    if trades < 20:
        score -= (20 - trades) * 2.0
    return {
        "case": path.stem, "symbol": symbol, "variant": variant, "period": period,
        "history_quality_pct": quality, "bars": bars, "ticks": ticks,
        "initial_balance": initial, "final_balance": final_balance, "net_profit": net,
        "return_pct": return_pct, "gross_profit": gross_profit, "gross_loss": gross_loss,
        "profit_factor": profit_factor, "equity_dd_amount": equity_dd_amount,
        "equity_dd_pct": equity_dd_pct, "balance_dd_amount": balance_dd_amount,
        "balance_dd_pct": balance_dd_pct, "trades": trades, "wins": wins, "losses": losses,
        "win_rate": win_rate, "commission": commission, "swap": swap, "score": score,
        "status": "valid" if quality >= 90 and bars > 0 else "invalid-data",
        "report": str(path), "graph": str(path.with_suffix(".png")), "series": series,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_stem", type=Path)
    args = parser.parse_args()
    results = [parse_report(path) for path in sorted(args.input_dir.glob("*.htm"))]
    results.sort(key=lambda item: (item["symbol"], -item["score"]))
    args.output_stem.parent.mkdir(parents=True, exist_ok=True)
    args.output_stem.with_suffix(".json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    fields = [key for key in results[0] if key != "series"] if results else []
    with args.output_stem.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    if args.output_stem.name.startswith("development"):
        picks = []
        for symbol in sorted({item["symbol"] for item in results}):
            group = [item for item in results if item["symbol"] == symbol and item["status"] == "valid"]
            eligible = [item for item in group if item["trades"] >= 20]
            best = max(eligible or group, key=lambda item: item["score"])
            picks.append({"symbol": symbol, "variant": best["variant"], "score": best["score"],
                          "development_return_pct": best["return_pct"],
                          "development_pf": best["profit_factor"],
                          "development_dd_pct": best["equity_dd_pct"],
                          "development_trades": best["trades"]})
        (args.output_stem.parent / "selection.json").write_text(json.dumps(picks, indent=2), encoding="utf-8")
    for item in results:
        print(f"{item['symbol']:6} {item['variant']:22} return={item['return_pct']:8.2f}% "
              f"PF={item['profit_factor']:5.2f} WR={item['win_rate']:6.2f}% "
              f"DD={item['equity_dd_pct']:6.2f}% trades={item['trades']:4d} score={item['score']:8.2f}")


if __name__ == "__main__":
    main()
