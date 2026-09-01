from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup


def clean_number(value: str) -> float:
    value = value.replace("\xa0", " ").replace(" ", "").replace(",", "")
    if not value or value == "-":
        return 0.0
    return float(value)


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


def parse_bool(text: str, name: str) -> bool:
    return match(text, rf"{re.escape(name)}=(true|false)", "false") == "true"


def parse_report(path: Path) -> dict:
    soup = BeautifulSoup(read_report(path), "html.parser")
    text = " ".join(soup.get_text(" ").split())
    initial = clean_number(match(text, r"Initial Deposit:\s*([\d .]+?)\s+Leverage:"))
    net = clean_number(match(text, r"Total Net Profit:\s*([-\d .]+?)\s+Balance Drawdown Absolute:"))
    quality = float(match(text, r"History Quality:\s*([\d.]+)%"))
    bars = int(match(text, r"Bars:\s*(\d+)"))
    ticks = int(match(text, r"Ticks:\s*(\d+)"))
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
    long_trades = int(match(text, r"Long Trades \(won %\):\s*(\d+)"))
    long_win_rate = float(match(text, r"Long Trades \(won %\):\s*\d+\s*\(([\d.]+)%\)"))
    short_trades = int(match(text, r"Short Trades \(won %\):\s*(\d+)"))
    short_win_rate = float(match(text, r"Short Trades \(won %\):\s*\d+\s*\(([\d.]+)%\)"))
    largest_win = clean_number(match(text, r"Largest profit trade:\s*([-\d .]+)"))
    largest_loss = clean_number(match(text, r"Largest loss trade:\s*([-\d .]+)"))
    average_win = clean_number(match(text, r"Average profit trade:\s*([-\d .]+)"))
    average_loss = clean_number(match(text, r"Average loss trade:\s*([-\d .]+)"))
    expected_payoff = clean_number(match(text, r"Expected Payoff:\s*([-\d .]+)"))
    recovery_factor = float(match(text, r"Recovery Factor:\s*([-\d.]+)"))
    sharpe_ratio = float(match(text, r"Sharpe Ratio:\s*([-\d.]+)"))
    period = match(text, r"Period:\s*(.*?)\s+Inputs:", "unknown")
    start_end = re.search(r"\((\d{4}\.\d{2}\.\d{2})\s*-\s*(\d{4}\.\d{2}\.\d{2})\)", period)
    start_date = start_end.group(1).replace(".", "-") if start_end else ""
    end_date = start_end.group(2).replace(".", "-") if start_end else ""

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

    result = {
        "case": path.stem,
        "period": period,
        "history_quality_pct": quality,
        "bars": bars,
        "ticks": ticks,
        "initial_stop_atr": float(match(text, r"InpInitialStopATR=([\d.]+)")),
        "trailing_atr": float(match(text, r"InpTrailingATR=([\d.]+)")),
        "trail_start_r": float(match(text, r"InpTrailStartR=([\d.]+)")),
        "close_at_session_end": parse_bool(text, "InpCloseAtSessionEnd"),
        "initial_balance": initial,
        "final_balance": final_balance,
        "net_profit": net,
        "return_pct": net / initial * 100.0 if initial else 0.0,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "equity_dd_amount": equity_dd_amount,
        "equity_dd_pct": equity_dd_pct,
        "balance_dd_amount": balance_dd_amount,
        "balance_dd_pct": balance_dd_pct,
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "long_trades": long_trades,
        "long_win_rate": long_win_rate,
        "short_trades": short_trades,
        "short_win_rate": short_win_rate,
        "largest_win": largest_win,
        "largest_loss": largest_loss,
        "average_win": average_win,
        "average_loss": average_loss,
        "expected_payoff": expected_payoff,
        "recovery_factor": recovery_factor,
        "sharpe_ratio": sharpe_ratio,
        "commission": commission,
        "swap": swap,
        "score": (net / initial * 100.0 if initial else 0.0) - 2.0 * equity_dd_pct,
        "status": "valid" if quality >= 90 and bars > 0 else "invalid-data",
        "report": str(path),
        "graph": str(path.with_suffix(".png")),
        "series": series,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_stem", type=Path)
    args = parser.parse_args()
    results = [parse_report(path) for path in sorted(args.input_dir.glob("*.htm"))]
    results.sort(key=lambda item: item["score"], reverse=True)
    args.output_stem.parent.mkdir(parents=True, exist_ok=True)
    args.output_stem.with_suffix(".json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    fields = [key for key in results[0] if key != "series"] if results else []
    with args.output_stem.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    for result in results:
        print(
            f"{result['case']:12} return={result['return_pct']:8.2f}% PF={result['profit_factor']:5.2f} "
            f"WR={result['win_rate']:6.2f}% DD={result['equity_dd_pct']:6.2f}% "
            f"trades={result['trades']:4d} score={result['score']:8.2f}"
        )


if __name__ == "__main__":
    main()
