from __future__ import annotations

import csv
import html
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "Backtest Reports"


def clean(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    return html.unescape(value).replace("\xa0", " ").strip()


def metric(text: str, label: str) -> str:
    pattern = rf">\s*{re.escape(label)}:\s*</td>\s*<td[^>]*>\s*<b>(.*?)</b>"
    match = re.search(pattern, text, flags=re.I | re.S)
    return clean(match.group(1)) if match else ""


def number(value: str) -> float:
    match = re.search(r"[-+]?\d[\d ]*(?:\.\d+)?", value.replace("%", ""))
    return float(match.group(0).replace(" ", "")) if match else 0.0


def percent_in_parentheses(value: str) -> float:
    match = re.search(r"\(([\d.]+)%\)", value)
    return float(match.group(1)) if match else 0.0


def parse_report(path: Path) -> dict:
    text = path.read_text(encoding="utf-16", errors="ignore")
    if "Initial Deposit" not in text:
        text = path.read_text(encoding="utf-8", errors="ignore")
    stem = path.stem
    symbol, profile, _ = stem.split("--", 2)
    initial = number(metric(text, "Initial Deposit"))
    net = number(metric(text, "Total Net Profit"))
    winners = metric(text, "Profit Trades (% of total)")
    return {
        "symbol": symbol.upper(),
        "profile": profile,
        "initial_balance": initial,
        "net_profit": net,
        "final_balance": initial + net,
        "return_percent": net / initial * 100.0 if initial else 0.0,
        "profit_factor": number(metric(text, "Profit Factor")),
        "win_rate_percent": percent_in_parentheses(winners),
        "max_equity_drawdown_percent": percent_in_parentheses(metric(text, "Equity Drawdown Maximal")),
        "trades": int(number(metric(text, "Total Trades"))),
        "history_quality": metric(text, "History Quality"),
        "report": str(path),
    }


def make_contact_sheet(rows: list[dict]) -> Path:
    cards = []
    font = ImageFont.load_default()
    for row in rows:
        source = Path(row["report"]).with_suffix(".png")
        if not source.exists():
            continue
        chart = Image.open(source).convert("RGB")
        chart.thumbnail((720, 360))
        card = Image.new("RGB", (760, 430), "white")
        draw = ImageDraw.Draw(card)
        title = (
            f"{row['symbol']} | {row['profile'].upper()} | "
            f"Return {row['return_percent']:+.2f}% | PF {row['profit_factor']:.2f} | "
            f"DD {row['max_equity_drawdown_percent']:.2f}%"
        )
        draw.text((20, 14), title, fill="black", font=font)
        card.paste(chart, ((760 - chart.width) // 2, 48))
        cards.append(card)
    columns = 2
    rows_count = (len(cards) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * 760, rows_count * 430), (18, 24, 27))
    for index, card in enumerate(cards):
        sheet.paste(card, ((index % columns) * 760, (index // columns) * 430))
    output = ROOT / "EQUITY CURVES - NORMAL VS PROP.png"
    sheet.save(output, optimize=True)
    return output


def main() -> None:
    rows = [parse_report(path) for path in sorted(REPORTS.glob("*.htm"))]
    (ROOT / "RESULTS.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    with (ROOT / "RESULTS.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    chart = make_contact_sheet(rows)

    lines = [
        "# Statistical Triple Print EA — one-year MT5 audit",
        "",
        "This is a mechanical reconstruction of the supplied transcript, not the speaker's undisclosed proprietary model.",
        "Tests use Exness MT5 Every Tick modelling, broker spread, random execution delay, commission and swaps where charged.",
        "",
        "| Symbol | Profile | Return | PF | Win rate | Max equity DD | Trades |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['symbol']} | {row['profile']} | {row['return_percent']:+.2f}% | "
            f"{row['profit_factor']:.2f} | {row['win_rate_percent']:.2f}% | "
            f"{row['max_equity_drawdown_percent']:.2f}% | {row['trades']} |"
        )
    lines += [
        "",
        "## Profile rules",
        "",
        "- Normal: 1% equity risk, 2 trades/day, 2R target.",
        "- Prop: 0.35% equity risk, 1 trade/day, 1.5R target, 1% daily equity-loss lock, 5% overall equity guard, flat after the trading window and before the weekend.",
        "- Both: M15 body-close structure breakout, three valid countertrend candles, ATR displacement and wick-gap filters, spread guard, fixed stop and no martingale/grid.",
        "",
        f"Combined chart: `{chart.name}`",
    ]
    (ROOT / "FULL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
