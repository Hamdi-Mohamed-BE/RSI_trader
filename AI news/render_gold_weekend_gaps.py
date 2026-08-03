from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "gold-weekend-gaps" / "xauusd-m1-2026-05-01-2026-08-02.json"
OUTPUT_DIR = ROOT / "charts" / "gold-weekend-gaps-2026-05-07"
REPORT_PATH = ROOT / "GOLD_WEEKEND_GAPS_3M.md"
PIP_SIZE = 0.1

BACKGROUND = "#070b14"
PANEL = "#0d1422"
GRID = "#243047"
TEXT = "#e8eef9"
MUTED = "#8ea0ba"
UP = "#23c99a"
DOWN = "#ff5d73"
WEEKEND = "#f8c44f"
PRE_SHADE = "#101a2d"


@dataclass
class WeekendGap:
    close_index: int
    open_index: int
    close_time: datetime
    open_time: datetime
    close_price: float
    open_price: float
    gap: float
    fill_time: datetime | None
    fill_minutes: int | None


def _font(size: int, *, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    path = Path("C:/Windows/Fonts") / name
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def _load() -> tuple[dict, list[dict]]:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    rows = sorted(payload["rows"], key=lambda row: row["time"])
    return payload, rows


def _time(row: dict) -> datetime:
    return datetime.fromtimestamp(int(row["time"]), timezone.utc)


def _find_fill(rows: list[dict], open_index: int, close_price: float, gap: float) -> tuple[datetime | None, int | None]:
    open_time = _time(rows[open_index])
    deadline = open_time + timedelta(days=5)
    for row in rows[open_index:]:
        current = _time(row)
        if current > deadline:
            break
        filled = row["low"] <= close_price if gap > 0 else row["high"] >= close_price
        if filled:
            return current, max(0, int((current - open_time).total_seconds() // 60))
    return None, None


def _gaps(rows: list[dict]) -> list[WeekendGap]:
    result = []
    for index in range(1, len(rows)):
        previous_time = _time(rows[index - 1])
        current_time = _time(rows[index])
        pause = current_time - previous_time
        if pause < timedelta(hours=24):
            continue
        if previous_time.weekday() not in (4, 5) or current_time.weekday() not in (6, 0):
            continue
        close_price = float(rows[index - 1]["close"])
        open_price = float(rows[index]["open"])
        gap = open_price - close_price
        fill_time, fill_minutes = _find_fill(rows, index, close_price, gap)
        result.append(
            WeekendGap(
                close_index=index - 1,
                open_index=index,
                close_time=previous_time,
                open_time=current_time,
                close_price=close_price,
                open_price=open_price,
                gap=gap,
                fill_time=fill_time,
                fill_minutes=fill_minutes,
            )
        )
    return result


def _fill_label(gap: WeekendGap) -> str:
    if gap.fill_minutes is None:
        return "not filled in 5d"
    if gap.fill_minutes == 0:
        return "filled in opening M1"
    if gap.fill_minutes < 60:
        return f"filled in {gap.fill_minutes}m"
    hours = gap.fill_minutes / 60
    return f"filled in {hours:.1f}h" if hours < 24 else f"filled in {hours / 24:.1f}d"


def _summary_chart(gaps: list[WeekendGap]) -> Path:
    width, height = 1900, 920
    image = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.text((45, 28), "XAUUSD Weekend Opening Gaps - May to July 2026", fill=TEXT, font=_font(36, bold=True))
    draw.text((45, 80), "Friday final M1 close to Monday first M1 open / MT5 broker prices", fill=MUTED, font=_font(20))
    left, right, top, bottom = 90, width - 55, 160, height - 135
    maximum = max(abs(gap.gap) for gap in gaps) * 1.2
    baseline = (top + bottom) / 2
    draw.line((left, baseline, right, baseline), fill=TEXT, width=2)
    for fraction in (-1, -0.5, 0.5, 1):
        y = baseline - fraction * (bottom - top) / 2
        draw.line((left, y, right, y), fill=GRID, width=1)
        draw.text((left - 12, y), f"{fraction * maximum:+.0f}", fill=MUTED, font=_font(15), anchor="rm")
    step = (right - left) / len(gaps)
    bar_width = max(18, int(step * 0.55))
    for index, gap in enumerate(gaps):
        x = left + (index + 0.5) * step
        y = baseline - gap.gap / maximum * (bottom - top) / 2
        color = UP if gap.gap > 0 else DOWN
        draw.rectangle((x - bar_width / 2, min(y, baseline), x + bar_width / 2, max(y, baseline)), fill=color)
        anchor = "mb" if gap.gap > 0 else "ma"
        label_y = y - 8 if gap.gap > 0 else y + 8
        draw.text((x, label_y), f"{gap.gap:+.2f}", fill=color, font=_font(16, bold=True), anchor=anchor)
        draw.text((x, bottom + 30), f"{gap.open_time:%b %d}", fill=MUTED, font=_font(15), anchor="ma")
        draw.text((x, bottom + 57), "UP" if gap.gap > 0 else "DOWN", fill=color, font=_font(14, bold=True), anchor="ma")
    average = sum(abs(gap.gap) for gap in gaps) / len(gaps)
    filled = sum(gap.fill_time is not None for gap in gaps)
    largest = max(gaps, key=lambda gap: abs(gap.gap))
    footer = f"Average absolute gap ${average:.2f} ({average / PIP_SIZE:.0f}p)   Filled within 5 days {filled}/{len(gaps)}   Largest {largest.open_time:%b %d}: ${largest.gap:+.2f}"
    draw.text((width / 2, height - 35), footer, fill=TEXT, font=_font(20), anchor="mm")
    path = OUTPUT_DIR / "xauusd-weekend-gap-summary-2026-05-07.png"
    image.save(path, quality=95)
    return path


def _draw_gap_panel(rows: list[dict], gap: WeekendGap, width: int, height: int) -> Image.Image:
    before = rows[max(0, gap.close_index - 14) : gap.close_index + 1]
    after = rows[gap.open_index : gap.open_index + 31]
    bars = before + after
    split = len(before)
    image = Image.new("RGB", (width, height), PANEL)
    draw = ImageDraw.Draw(image)
    left, right, top, bottom = 66, width - 78, 105, height - 58
    prices = [value for row in bars for value in (row["high"], row["low"])]
    low, high = min(prices), max(prices)
    padding = max((high - low) * 0.08, 0.1)
    low -= padding
    high += padding

    def y(value: float) -> float:
        return bottom - (value - low) / (high - low) * (bottom - top)

    for index in range(5):
        gy = top + (bottom - top) * index / 4
        draw.line((left, gy, right, gy), fill=GRID, width=1)
        price = high - (high - low) * index / 4
        draw.text((right + 7, gy), f"{price:,.2f}", fill=MUTED, font=_font(13), anchor="lm")
    step = (right - left) / len(bars)
    candle_width = max(3, int(step * 0.6))
    weekend_x = left + split * step
    draw.rectangle((left, top, weekend_x, bottom), fill=PRE_SHADE)
    for index, row in enumerate(bars):
        x = left + (index + 0.5) * step
        color = UP if row["close"] >= row["open"] else DOWN
        draw.line((x, y(row["high"]), x, y(row["low"])), fill=color, width=2)
        body_top = y(max(row["open"], row["close"]))
        body_bottom = max(body_top + 2, y(min(row["open"], row["close"])))
        draw.rectangle((x - candle_width / 2, body_top, x + candle_width / 2, body_bottom), fill=color)
    draw.line((weekend_x, top, weekend_x, bottom), fill=WEEKEND, width=3)
    draw.line((left, y(gap.close_price), right, y(gap.close_price)), fill=MUTED, width=1)
    color = UP if gap.gap > 0 else DOWN
    draw.text((24, 16), f"Reopen {gap.open_time:%b %d, %Y} / {'gap up' if gap.gap > 0 else 'gap down'}", fill=TEXT, font=_font(22, bold=True))
    draw.text((24, 52), f"Friday close {gap.close_price:,.2f}  ->  open {gap.open_price:,.2f}", fill=MUTED, font=_font(16))
    draw.text((width - 22, 23), f"{gap.gap:+.2f} / {gap.gap / PIP_SIZE:+.0f}p", fill=color, font=_font(20, bold=True), anchor="ra")
    draw.text((width - 22, 58), _fill_label(gap), fill=TEXT, font=_font(15), anchor="ra")
    draw.text((left, bottom + 17), "Friday final 15m", fill=MUTED, font=_font(13), anchor="la")
    draw.text((weekend_x + 7, top + 5), "REOPEN", fill=WEEKEND, font=_font(13))
    draw.text((right, bottom + 17), "First 30m", fill=MUTED, font=_font(13), anchor="ra")
    return image


def _monthly_grid(rows: list[dict], gaps: list[WeekendGap], month: int) -> Path:
    chosen = [gap for gap in gaps if gap.open_time.month == month]
    columns = 2
    panel_width, panel_height, gutter, header = 920, 520, 18, 76
    rows_count = math.ceil(len(chosen) / columns)
    canvas = Image.new("RGB", (panel_width * columns + gutter * 3, panel_height * rows_count + gutter * (rows_count + 1) + header), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw.text((gutter, 18), f"XAUUSD M1 Weekend Gaps - {datetime(2026, month, 1):%B 2026}", fill=TEXT, font=_font(30, bold=True))
    for index, gap in enumerate(chosen):
        panel = _draw_gap_panel(rows, gap, panel_width, panel_height)
        x = gutter + (index % columns) * (panel_width + gutter)
        y = header + gutter + (index // columns) * (panel_height + gutter)
        canvas.paste(panel, (x, y))
    path = OUTPUT_DIR / f"xauusd-weekend-gaps-2026-{month:02d}.png"
    canvas.save(path, quality=95)
    return path


def run() -> list[WeekendGap]:
    payload, rows = _load()
    gaps = _gaps(rows)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = _summary_chart(gaps)
    monthly = [_monthly_grid(rows, gaps, month) for month in (5, 6, 7)]
    lines = [
        "# XAUUSD Weekend Gaps - May through July 2026",
        "",
        f"Source: MT5 `{payload['symbol']}` on `{payload.get('server')}`. Times are UTC. One gold pip is $0.10.",
        "",
        "| Reopen | Friday close | Open | Gap | Gap pips | Direction | Gap fill |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for gap in gaps:
        lines.append(f"| {gap.open_time:%Y-%m-%d %H:%M} | {gap.close_price:.2f} | {gap.open_price:.2f} | {gap.gap:+.2f} | {gap.gap / PIP_SIZE:+.0f} | {'UP' if gap.gap > 0 else 'DOWN'} | {_fill_label(gap)} |")
    lines.extend(["", "## Charts", "", f"- `{summary.relative_to(ROOT)}`"])
    lines.extend(f"- `{path.relative_to(ROOT)}`" for path in monthly)
    lines.extend(["", "The July 31 to August 2 weekend is not included because no reopening candle existed in the downloaded period.", ""])
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return gaps


if __name__ == "__main__":
    result = run()
    print(f"Rendered {len(result)} completed weekend gaps to {OUTPUT_DIR}")
