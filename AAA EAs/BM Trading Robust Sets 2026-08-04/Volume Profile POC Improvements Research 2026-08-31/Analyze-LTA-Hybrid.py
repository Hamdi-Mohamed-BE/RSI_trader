from __future__ import annotations

import csv
import html
import json
import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
REPORT_ROOT = ROOT / "Hybrid Backtest Reports"


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
    match = re.search(r"\(([-+]?\d+(?:\.\d+)?)%\)", value)
    return float(match.group(1)) if match else 0.0


def parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-16", errors="ignore")
    if "Initial Deposit" not in text:
        text = path.read_text(encoding="utf-8", errors="ignore")
    _, case, phase = path.stem.split("--")
    initial = number(metric(text, "Initial Deposit"))
    net = number(metric(text, "Total Net Profit"))
    heavy = departure = bars = None
    match = re.match(r"hybrid-h(\d+)-d(\d+)-b(\d+)", case)
    if match:
        heavy = int(match.group(1)) / 100
        departure = int(match.group(2)) / 100
        bars = int(match.group(3))
    return {
        "case": case,
        "phase": phase,
        "heavy": heavy,
        "departure": departure,
        "bars": bars,
        "return_percent": net / initial * 100.0 if initial else 0.0,
        "profit_factor": number(metric(text, "Profit Factor")),
        "win_rate_percent": pct(metric(text, "Profit Trades (% of total)")),
        "max_equity_drawdown_percent": pct(metric(text, "Equity Drawdown Maximal")),
        "trades": int(number(metric(text, "Total Trades"))),
        "sharpe_ratio": number(metric(text, "Sharpe Ratio")),
        "recovery_factor": number(metric(text, "Recovery Factor")),
        "history_quality": metric(text, "History Quality"),
        "report": str(path),
    }


def score(row: dict) -> float:
    if row["case"] == "baseline" or row["trades"] < 20 or row["return_percent"] <= 0 or row["profit_factor"] <= 1:
        return -1e9
    sample = math.sqrt(min(row["trades"], 100) / 100)
    return row["return_percent"] * min(row["profit_factor"], 3) * sample / (1 + row["max_equity_drawdown_percent"])


def make_sheet(rows: list[dict]) -> Path:
    selected_cases = {"baseline"}
    dev = [r for r in rows if r["phase"] == "development" and r["case"] != "baseline"]
    selected_cases.update(r["case"] for r in sorted(dev, key=score, reverse=True)[:5])
    selected = [r for r in rows if r["case"] in selected_cases]
    font = ImageFont.load_default()
    cards = []
    for row in sorted(selected, key=lambda r: (r["phase"], r["case"])):
        chart_path = Path(row["report"]).with_suffix(".png")
        if not chart_path.exists():
            continue
        chart = Image.open(chart_path).convert("RGB")
        chart.thumbnail((720, 330))
        card = Image.new("RGB", (760, 410), "white")
        title = (
            f"{row['case']} | {row['phase']} | {row['return_percent']:+.2f}% | "
            f"PF {row['profit_factor']:.2f} | DD {row['max_equity_drawdown_percent']:.2f}% | {row['trades']} trades"
        )
        ImageDraw.Draw(card).text((18, 14), title, fill="black", font=font)
        card.paste(chart, ((760 - chart.width) // 2, 48))
        cards.append(card)
    columns = 2
    sheet = Image.new("RGB", (1520, max(410, ((len(cards) + 1) // 2) * 410)), (18, 24, 27))
    for index, card in enumerate(cards):
        sheet.paste(card, ((index % columns) * 760, (index // columns) * 410))
    output = ROOT / "LTA HYBRID EQUITY CURVES.png"
    sheet.save(output, optimize=True)
    return output


def main() -> None:
    rows = [parse(path) for path in sorted(REPORT_ROOT.glob("*/*.htm"))]
    (ROOT / "HYBRID RESULTS.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    if rows:
        with (ROOT / "HYBRID RESULTS.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    development = [r for r in rows if r["phase"] == "development" and r["case"] != "baseline"]
    selected = sorted(development, key=score, reverse=True)[:5]
    selection = {"selection_rule": "positive return, PF > 1, at least 20 trades; rank by return, PF, sample size and drawdown", "selected": selected}
    (ROOT / "HYBRID DEVELOPMENT SELECTION.json").write_text(json.dumps(selection, indent=2), encoding="utf-8")
    make_sheet(rows)
    print(json.dumps({"rows": len(rows), "selected": selected}, indent=2))


if __name__ == "__main__":
    main()
