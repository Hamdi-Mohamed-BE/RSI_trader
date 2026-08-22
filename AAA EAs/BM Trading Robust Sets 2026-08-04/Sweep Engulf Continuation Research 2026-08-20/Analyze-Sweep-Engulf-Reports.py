from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "Backtest Reports" / "MT5 Exness Live 1Y"
ORDER = [
    "XAUUSD", "XAGUSD", "BTCUSD", "ETHUSD", "US30", "USTEC",
    "EURUSD", "GBPUSD", "USDJPY", "USDCAD", "USDCHF", "AUDUSD",
    "NZDUSD", "GBPJPY",
]


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


def parse_report(path: Path) -> dict:
    soup = BeautifulSoup(read_report(path), "html.parser")
    text = " ".join(soup.get_text(" ").split())
    symbol = match(text, r"Symbol:\s*([^ ]+)")
    period = match(text, r"Period:\s*(.*?)\s+Inputs:", "unknown")
    date_match = re.search(r"\((\d{4}\.\d{2}\.\d{2})\s*-\s*(\d{4}\.\d{2}\.\d{2})\)", period)
    start_date = date_match.group(1).replace(".", "-") if date_match else "2025-08-20"
    end_date = date_match.group(2).replace(".", "-") if date_match else "2026-08-19"
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
    expected_payoff = clean_number(match(text, r"Expected Payoff:\s*([-\d .]+)"))
    recovery_factor = float(match(text, r"Recovery Factor:\s*([-\d.]+)"))
    sharpe_ratio = float(match(text, r"Sharpe Ratio:\s*([-\d.]+)"))
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

    series = [{"date": start_date, "balance": initial}]
    commission = 0.0
    swap = 0.0
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
        deal_type = cells[3].lower()
        if deal_type == "balance":
            continue
        commission += clean_number(cells[8])
        swap += clean_number(cells[9])
        balance = clean_number(cells[11])
        if balance > 0:
            when = datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S").isoformat(sep=" ")
            if not series or series[-1]["balance"] != balance:
                series.append({"date": when, "balance": balance})
    final_balance = initial + net
    if not series or series[-1]["balance"] != final_balance:
        series.append({"date": end_date, "balance": final_balance})

    return {
        "symbol": symbol,
        "timeframe": "H1",
        "period": period,
        "history_quality_pct": quality,
        "bars": bars,
        "ticks": ticks,
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
        "expected_payoff": expected_payoff,
        "recovery_factor": recovery_factor,
        "sharpe_ratio": sharpe_ratio,
        "largest_win": largest_win,
        "largest_loss": largest_loss,
        "average_win": average_win,
        "average_loss": average_loss,
        "commission": commission,
        "swap": swap,
        "status": "valid" if quality >= 90 and bars > 0 else "invalid-data",
        "report": str(path),
        "graph": str(path.with_suffix(".png")),
        "series": series,
    }


def main() -> None:
    results = [parse_report(path) for path in REPORTS.glob("*.htm")]
    order = {symbol: index for index, symbol in enumerate(ORDER)}
    results.sort(key=lambda item: order.get(item["symbol"], len(order)))
    payload = {
        "method": {
            "broker": "Exness Technologies Ltd / Exness-MT5Trial16",
            "terminal": "MetaTrader 5 build 6090",
            "model": "MT5 model 0 / every-tick generation from synchronized broker history",
            "execution": "Random execution delay; broker spread, commission and swap reflected by MT5",
            "period": "2025-08-20 to 2026-08-19",
            "deposit": 10000,
            "risk_per_trade_pct": 0.5,
            "configuration": "H1, any previous candle direction, EMA 50 trend filter, structural signal-extreme stop + 0.10 ATR buffer, 1.5R target",
        },
        "results": results,
    }
    (ROOT / "sweep-engulf-live-results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    fields = [
        "symbol", "timeframe", "status", "history_quality_pct", "initial_balance", "final_balance",
        "net_profit", "return_pct", "profit_factor", "win_rate", "trades", "equity_dd_pct",
        "equity_dd_amount", "gross_profit", "gross_loss", "long_trades", "long_win_rate",
        "short_trades", "short_win_rate", "largest_win", "largest_loss", "average_win",
        "average_loss", "commission", "swap", "report", "graph",
    ]
    with (ROOT / "sweep-engulf-live-results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    for result in results:
        print(
            f"{result['symbol']:7} {result['status']:12} return={result['return_pct']:7.2f}% "
            f"PF={result['profit_factor']:5.2f} WR={result['win_rate']:6.2f}% "
            f"DD={result['equity_dd_pct']:6.2f}% trades={result['trades']:4d}"
        )


if __name__ == "__main__":
    main()
