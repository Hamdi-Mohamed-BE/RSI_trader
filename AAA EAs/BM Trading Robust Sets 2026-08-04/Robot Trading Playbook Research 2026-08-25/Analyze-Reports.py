from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime
from html import unescape
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TAG_RE = re.compile(r"<[^>]+>")
ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
CELL_RE = re.compile(r"<td\b[^>]*>(.*?)</td>", re.IGNORECASE | re.DOTALL)


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
    html = read_report(path)
    text = " ".join(unescape(TAG_RE.sub(" ", html)).replace("\xa0", " ").split())
    period = match(text, r"Period:\s*(.*?)\s+Inputs:", "unknown")
    date_match = re.search(r"\((\d{4}\.\d{2}\.\d{2})\s*-\s*(\d{4}\.\d{2}\.\d{2})\)", period)
    start_date = date_match.group(1).replace(".", "-") if date_match else "unknown"
    end_date = date_match.group(2).replace(".", "-") if date_match else "unknown"
    initial = clean_number(match(text, r"Initial Deposit:\s*([\d .]+?)\s+Leverage:"))
    net = clean_number(match(text, r"Total Net Profit:\s*([-\d .]+?)\s+Balance Drawdown Absolute:"))
    gross_profit = clean_number(match(text, r"Gross Profit:\s*([-\d .]+?)\s+Balance Drawdown Maximal:"))
    gross_loss = clean_number(match(text, r"Gross Loss:\s*([-\d .]+?)\s+Balance Drawdown Relative:"))
    result = {
        "report": str(path),
        "period": period,
        "start": start_date,
        "end": end_date,
        "history_quality_pct": float(match(text, r"History Quality:\s*([\d.]+)%")),
        "bars": int(match(text, r"Bars:\s*(\d+)")),
        "ticks": int(match(text, r"Ticks:\s*(\d+)")),
        "initial_balance": initial,
        "final_balance": initial + net,
        "net_profit": net,
        "return_pct": net / initial * 100.0 if initial else 0.0,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": float(match(text, r"Profit Factor:\s*([\d.]+)")),
        "equity_dd_amount": clean_number(match(text, r"Equity Drawdown Maximal:\s*([-\d .]+?)\s*\(")),
        "equity_dd_pct": float(match(text, r"Equity Drawdown Maximal:\s*[-\d .]+\s*\(([\d.]+)%\)")),
        "trades": int(match(text, r"Total Trades:\s*(\d+)")),
        "wins": int(match(text, r"Profit Trades \(% of total\):\s*(\d+)")),
        "losses": int(match(text, r"Loss Trades \(% of total\):\s*(\d+)")),
        "win_rate": float(match(text, r"Profit Trades \(% of total\):\s*\d+\s*\(([\d.]+)%\)")),
        "expected_payoff": clean_number(match(text, r"Expected Payoff:\s*([-\d .]+)")),
        "recovery_factor": float(match(text, r"Recovery Factor:\s*([-\d.]+)")),
        "sharpe_ratio": float(match(text, r"Sharpe Ratio:\s*([-\d.]+)")),
        "largest_win": clean_number(match(text, r"Largest profit trade:\s*([-\d .]+)")),
        "largest_loss": clean_number(match(text, r"Largest loss trade:\s*([-\d .]+)")),
        "average_win": clean_number(match(text, r"Average profit trade:\s*([-\d .]+)")),
        "average_loss": clean_number(match(text, r"Average loss trade:\s*([-\d .]+)")),
    }
    commission = 0.0
    swap = 0.0
    series = [{"date": start_date, "balance": initial}]
    marker = html.lower().find("<b>deals</b>")
    deals_html = html[marker:] if marker >= 0 else ""
    for row in ROW_RE.findall(deals_html):
        cells = [" ".join(unescape(TAG_RE.sub("", cell)).replace("\xa0", " ").split()) for cell in CELL_RE.findall(row)]
        if len(cells) != 13 or not re.fullmatch(r"\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}", cells[0]):
            continue
        if cells[3].lower() == "balance":
            continue
        commission += clean_number(cells[8])
        swap += clean_number(cells[9])
        balance = clean_number(cells[11])
        if balance > 0 and series[-1]["balance"] != balance:
            series.append({"date": datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S").isoformat(sep=" "), "balance": balance})
    result["commission"] = commission
    result["swap"] = swap
    result["series"] = series
    return result


def main() -> None:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "Backtest Reports" / "Training"
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig")) if manifest_path.exists() else []
    if isinstance(manifest, dict):
        manifest = [manifest]
    by_slug = {str(row.get("Slug", "")).lower(): row for row in manifest}
    results = []
    for path in sorted(folder.glob("*.htm")):
        parsed = parse_report(path)
        parsed["slug"] = path.stem
        parsed.update({str(key).lower(): value for key, value in by_slug.get(path.stem.lower(), {}).items() if key not in {"Report"}})
        parsed["score"] = (
            parsed["return_pct"]
            * min(parsed["profit_factor"], 2.5)
            * min(parsed["trades"] / 150.0, 1.0)
            / max(parsed["equity_dd_pct"], 1.0)
        )
        results.append(parsed)
    results.sort(key=lambda row: row["score"], reverse=True)
    (folder / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    fields = [
        "slug", "timeframe", "lookback", "fast", "slow", "rr", "return_pct", "profit_factor",
        "win_rate", "equity_dd_pct", "trades", "net_profit", "commission", "swap", "score", "report",
    ]
    with (folder / "results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    for row in results[:15]:
        print(
            f"{row['slug']:31} return={row['return_pct']:7.2f}% PF={row['profit_factor']:5.2f} "
            f"WR={row['win_rate']:6.2f}% DD={row['equity_dd_pct']:6.2f}% trades={row['trades']:4d} score={row['score']:6.2f}"
        )


if __name__ == "__main__":
    main()
