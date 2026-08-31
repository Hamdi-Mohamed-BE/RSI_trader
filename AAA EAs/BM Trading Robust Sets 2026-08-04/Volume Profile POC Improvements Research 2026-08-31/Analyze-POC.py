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
    return html.unescape(re.sub(r"<[^>]+>", "", value)).replace("\xa0", " ").strip()


def metric(text: str, label: str) -> str:
    match = re.search(
        rf">\s*{re.escape(label)}:\s*</td>\s*<td[^>]*>\s*<b>(.*?)</b>",
        text,
        flags=re.I | re.S,
    )
    return clean(match.group(1)) if match else ""


def number(value: str) -> float:
    match = re.search(r"[-+]?\d[\d ]*(?:\.\d+)?", value.replace("%", ""))
    return float(match.group(0).replace(" ", "")) if match else 0.0


def pct(value: str) -> float:
    match = re.search(r"\(([\d.]+)%\)", value)
    return float(match.group(1)) if match else 0.0


def parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-16", errors="ignore")
    if "Initial Deposit" not in text:
        text = path.read_text(encoding="utf-8", errors="ignore")
    _, case, phase = path.stem.split("--")
    initial = number(metric(text, "Initial Deposit"))
    net = number(metric(text, "Total Net Profit"))
    return {
        "case": case,
        "phase": phase,
        "return_percent": net / initial * 100.0 if initial else 0.0,
        "profit_factor": number(metric(text, "Profit Factor")),
        "win_rate_percent": pct(metric(text, "Profit Trades (% of total)")),
        "max_equity_drawdown_percent": pct(metric(text, "Equity Drawdown Maximal")),
        "trades": int(number(metric(text, "Total Trades"))),
        "history_quality": metric(text, "History Quality"),
        "report": str(path),
    }


def contact_sheet(rows: list[dict]) -> Path:
    font = ImageFont.load_default()
    cards = []
    for row in rows:
        image_path = Path(row["report"]).with_suffix(".png")
        if not image_path.exists():
            continue
        chart = Image.open(image_path).convert("RGB")
        chart.thumbnail((720, 350))
        card = Image.new("RGB", (760, 420), "white")
        title = (
            f"{row['case']} | {row['phase']} | {row['return_percent']:+.2f}% | "
            f"PF {row['profit_factor']:.2f} | DD {row['max_equity_drawdown_percent']:.2f}%"
        )
        ImageDraw.Draw(card).text((18, 14), title, fill="black", font=font)
        card.paste(chart, ((760 - chart.width) // 2, 48))
        cards.append(card)
    columns = 2
    height = ((len(cards) + 1) // 2) * 420
    sheet = Image.new("RGB", (1520, max(height, 420)), (18, 24, 27))
    for index, card in enumerate(cards):
        sheet.paste(card, ((index % columns) * 760, (index // columns) * 420))
    output = ROOT / "POC IMPROVEMENT EQUITY CURVES.png"
    sheet.save(output, optimize=True)
    return output


def main() -> None:
    rows = [parse(path) for path in sorted(REPORTS.glob("*.htm"))]
    (ROOT / "RESULTS.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    if rows:
        with (ROOT / "RESULTS.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        contact_sheet(rows)
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
