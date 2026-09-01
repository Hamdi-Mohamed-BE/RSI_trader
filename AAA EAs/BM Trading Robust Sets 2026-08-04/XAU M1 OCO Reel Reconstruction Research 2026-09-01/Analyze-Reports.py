from __future__ import annotations

import argparse
import csv
import html
import json
import math
import re
from datetime import datetime
from pathlib import Path

def number(value: str) -> float:
    value = value.replace("\xa0", " ").replace(" ", "").replace(",", "")
    return float(value) if value and value != "-" else 0.0


def find(text: str, pattern: str, default: str = "0") -> str:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else default


def plain(markup: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", markup)).split())


def parse(path: Path, include_deals: bool) -> dict:
    # All tester statistics are in the first few hundred HTML lines. Reading
    # only that header avoids constructing a multi-gigabyte DOM for high-churn
    # M1 reports. Locked reports are streamed row-by-row for costs/equity.
    with path.open("r", encoding="utf-16", errors="replace") as handle:
        header_lines = []
        for line in handle:
            header_lines.append(line)
            if "<b>Orders</b>" in line or len(header_lines) >= 2000:
                break
    text = plain("".join(header_lines))
    initial = number(find(text, r"Initial Deposit:\s*([\d .]+?)\s+Leverage:"))
    net = number(find(text, r"Total Net Profit:\s*([-\d .]+?)\s+Balance Drawdown Absolute:"))
    pf = float(find(text, r"Profit Factor:\s*([\d.]+)"))
    eqdd_maximal_pct = float(find(text, r"Equity Drawdown Maximal:\s*[-\d .]+\s*\(([\d.]+)%\)"))
    eqdd_cash = number(find(text, r"Equity Drawdown Maximal:\s*([-\d .]+?)\s*\("))
    eqdd = float(find(text, r"Equity Drawdown Relative:\s*([\d.]+)%"))
    eqdd_relative_cash = number(find(text, r"Equity Drawdown Relative:\s*[\d.]+%\s*\(([-\d .]+)\)"))
    trades = int(find(text, r"Total Trades:\s*(\d+)"))
    wins = int(find(text, r"Profit Trades \(% of total\):\s*(\d+)"))
    losses = int(find(text, r"Loss Trades \(% of total\):\s*(\d+)"))
    win_rate = float(find(text, r"Profit Trades \(% of total\):\s*\d+\s*\(([\d.]+)%\)"))
    quality = float(find(text, r"History Quality:\s*([\d.]+)%"))
    bars = int(find(text, r"Bars:\s*(\d+)"))
    ticks = int(find(text, r"Ticks:\s*(\d+)"))
    gross_profit = number(find(text, r"Gross Profit:\s*([-\d .]+?)\s+Balance Drawdown Maximal:"))
    gross_loss = number(find(text, r"Gross Loss:\s*([-\d .]+?)\s+Balance Drawdown Relative:"))
    largest_win = number(find(text, r"Largest profit trade:\s*([-\d .]+)"))
    largest_loss = number(find(text, r"Largest loss trade:\s*([-\d .]+)"))
    average_win = number(find(text, r"Average profit trade:\s*([-\d .]+)"))
    average_loss = number(find(text, r"Average loss trade:\s*([-\d .]+)"))
    period = find(text, r"Period:\s*(.*?)\s+Inputs:", "unknown")
    dates = re.search(r"\((\d{4}\.\d{2}\.\d{2})\s*-\s*(\d{4}\.\d{2}\.\d{2})\)", period)
    start_date = dates.group(1).replace(".", "-") if dates else ""
    end_date = dates.group(2).replace(".", "-") if dates else ""
    commission = 0.0
    swap = 0.0
    series = [{"date": start_date, "balance": initial}] if start_date else []
    if include_deals:
        in_deals = False
        in_row = False
        row_lines: list[str] = []
        with path.open("r", encoding="utf-16", errors="replace") as handle:
            for line in handle:
                if not in_deals:
                    if "<b>Deals</b>" in line:
                        in_deals = True
                    continue
                if "<tr" in line:
                    in_row = True
                    row_lines = [line]
                    if "</tr>" not in line:
                        continue
                elif not in_row:
                    continue
                else:
                    row_lines.append(line)
                    if "</tr>" not in line:
                        continue
                markup = "".join(row_lines)
                in_row = False
                cells = [plain(cell) for cell in re.findall(r"<td\b[^>]*>(.*?)</td>", markup, re.I | re.S)]
                if len(cells) != 13 or not re.fullmatch(r"\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}", cells[0]):
                    continue
                if cells[3].lower() == "balance":
                    continue
                commission += number(cells[8])
                swap += number(cells[9])
                balance = number(cells[11])
                if balance > 0 and (not series or balance != series[-1]["balance"]):
                    when = datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S").isoformat(sep=" ")
                    series.append({"date": when, "balance": balance})
    final = initial + net
    if end_date and (not series or series[-1]["balance"] != final):
        series.append({"date": end_date, "balance": final})
    mode, variant = path.stem.split("__", 1)
    ret = net / initial * 100 if initial else 0.0
    score = ret - 1.5 * eqdd + 10.0 * math.log(max(pf, 0.05))
    if trades < 100:
        score -= (100 - trades) * 0.10
    return {
        "case": path.stem, "mode": mode, "variant": variant, "period": period,
        "history_quality_pct": quality, "bars": bars, "ticks": ticks,
        "initial_balance": initial, "final_balance": final, "net_profit": net,
        "return_pct": ret, "gross_profit": gross_profit, "gross_loss": gross_loss,
        "profit_factor": pf, "equity_dd_amount": eqdd_cash,
        "equity_dd_maximal_pct": eqdd_maximal_pct,
        "equity_dd_relative_amount": eqdd_relative_cash, "equity_dd_pct": eqdd,
        "trades": trades, "wins": wins, "losses": losses, "win_rate": win_rate,
        "largest_win": largest_win, "largest_loss": largest_loss,
        "average_win": average_win, "average_loss": average_loss,
        "commission": commission, "swap": swap, "score": score,
        "status": "valid" if quality >= 90 and bars > 0 else "invalid-data",
        "report": str(path), "graph": str(path.with_suffix(".png")), "series": series,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_stem", type=Path)
    args = parser.parse_args()
    include_deals = not args.output_stem.name.startswith("development")
    results = [parse(path, include_deals) for path in sorted(args.input_dir.glob("*.htm"))]
    results.sort(key=lambda item: (item["mode"], -item["score"]))
    args.output_stem.with_suffix(".json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    fields = [key for key in results[0] if key != "series"] if results else []
    with args.output_stem.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    if args.output_stem.name.startswith("development"):
        picks = []
        for mode in ("current", "previous"):
            group = [item for item in results if item["mode"] == mode and item["status"] == "valid"]
            eligible = [item for item in group if item["trades"] >= 100]
            best = max(eligible or group, key=lambda item: item["score"])
            picks.append({"mode": mode, "variant": best["variant"], "score": best["score"],
                          "development_return_pct": best["return_pct"], "development_pf": best["profit_factor"],
                          "development_dd_pct": best["equity_dd_pct"], "development_trades": best["trades"]})
        (args.output_stem.parent / "selection.json").write_text(json.dumps(picks, indent=2), encoding="utf-8")
    for item in results:
        print(f"{item['mode']:8} {item['variant']:20} return={item['return_pct']:8.2f}% "
              f"PF={item['profit_factor']:5.2f} WR={item['win_rate']:6.2f}% "
              f"DD={item['equity_dd_pct']:6.2f}% trades={item['trades']:5d} score={item['score']:8.2f}")


if __name__ == "__main__":
    main()
