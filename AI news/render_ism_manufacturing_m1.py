from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

from train_weekend_direction_model import _load_cache


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "charts" / "ism-manufacturing-xauusd-m1"
REPORT_PATH = ROOT / "ISM_MANUFACTURING_XAUUSD_M1.md"
CSV_PATH = OUTPUT_DIR / "last-five-stats.csv"
BEFORE_MINUTES = 30
AFTER_MINUTES = 60
PIP_SIZE = 0.1

BACKGROUND = "#07101d"
PANEL = "#0c1727"
PRE_SHADE = "#12233a"
GRID = "#273750"
TEXT = "#edf3fc"
MUTED = "#9aabc2"
UP = "#19c99a"
DOWN = "#ff6378"
RELEASE = "#ffcc4d"


@dataclass(frozen=True)
class Event:
    release_utc: datetime
    data_month: str
    actual: float


@dataclass
class Chart:
    event: Event
    bars: list[dict]
    pre_price: float
    m1_range: float
    m1_close: float
    move_5m: float
    move_15m: float
    move_60m: float
    max_up_15m: float
    max_down_15m: float
    full_range: float


EVENTS = (
    Event(datetime(2026, 3, 2, 15, 0, tzinfo=timezone.utc), "February", 52.4),
    Event(datetime(2026, 4, 1, 14, 0, tzinfo=timezone.utc), "March", 52.7),
    Event(datetime(2026, 5, 1, 14, 0, tzinfo=timezone.utc), "April", 52.7),
    Event(datetime(2026, 6, 1, 14, 0, tzinfo=timezone.utc), "May", 54.0),
    Event(datetime(2026, 7, 1, 14, 0, tzinfo=timezone.utc), "June", 53.3),
)


def font(size: int, *, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    path = Path("C:/Windows/Fonts") / name
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def signed(value: float) -> str:
    return f"{value:+,.2f}"


def prepare() -> tuple[str, list[Chart]]:
    markets, _ = _load_cache()
    gold = markets["XAUUSD"]
    output: list[Chart] = []
    for event in EVENTS:
        release = int(event.release_utc.timestamp())
        start = release - BEFORE_MINUTES * 60
        end = release + AFTER_MINUTES * 60
        left = int(gold.time.searchsorted(start, side="left"))
        right = int(gold.time.searchsorted(end, side="right"))
        bars = [
            {
                "stamp": int(gold.time[index]),
                "open": float(gold.open[index]),
                "high": float(gold.high[index]),
                "low": float(gold.low[index]),
                "close": float(gold.close[index]),
            }
            for index in range(left, right)
        ]
        by_stamp = {bar["stamp"]: bar for bar in bars}
        needed = (release - 60, release, release + 4 * 60, release + 14 * 60, release + 59 * 60)
        missing = [stamp for stamp in needed if stamp not in by_stamp]
        if missing:
            raise RuntimeError(f"Missing XAUUSD M1 bars for {event.release_utc.date()}: {missing}")
        pre = by_stamp[release - 60]["close"]
        first = by_stamp[release]
        first_15 = [by_stamp[release + minute * 60] for minute in range(15)]
        output.append(
            Chart(
                event=event,
                bars=bars,
                pre_price=pre,
                m1_range=first["high"] - first["low"],
                m1_close=first["close"] - pre,
                move_5m=by_stamp[release + 4 * 60]["close"] - pre,
                move_15m=by_stamp[release + 14 * 60]["close"] - pre,
                move_60m=by_stamp[release + 59 * 60]["close"] - pre,
                max_up_15m=max(bar["high"] for bar in first_15) - pre,
                max_down_15m=min(bar["low"] for bar in first_15) - pre,
                full_range=max(bar["high"] for bar in bars) - min(bar["low"] for bar in bars),
            )
        )
    return gold.symbol, output


def draw_chart(chart: Chart, broker_symbol: str, width: int, height: int) -> Image.Image:
    image = Image.new("RGB", (width, height), PANEL)
    draw = ImageDraw.Draw(image)
    left, right, top, bottom = 62, width - 78, 102, height - 54
    plot_width, plot_height = right - left, bottom - top
    prices = [price for bar in chart.bars for price in (bar["high"], bar["low"])]
    low, high = min(prices), max(prices)
    padding = max((high - low) * 0.08, 0.08)
    low, high = low - padding, high + padding

    def y(price: float) -> float:
        return bottom - (price - low) / (high - low) * plot_height

    count = len(chart.bars)
    step = plot_width / count
    candle_width = max(2, int(step * 0.64))
    release_stamp = int(chart.event.release_utc.timestamp())
    release_index = next(index for index, bar in enumerate(chart.bars) if bar["stamp"] == release_stamp)
    release_x = left + (release_index + 0.5) * step
    draw.rectangle((left, top, release_x, bottom), fill=PRE_SHADE)

    for index in range(6):
        gy = top + plot_height * index / 5
        draw.line((left, gy, right, gy), fill=GRID, width=1)
        price = high - (high - low) * index / 5
        draw.text((right + 7, gy - 8), f"{price:,.2f}", fill=MUTED, font=font(12))

    for index, bar in enumerate(chart.bars):
        x = left + (index + 0.5) * step
        color = UP if bar["close"] >= bar["open"] else DOWN
        draw.line((x, y(bar["high"]), x, y(bar["low"])), fill=color, width=1)
        body_top = y(max(bar["open"], bar["close"]))
        body_bottom = max(body_top + 2, y(min(bar["open"], bar["close"])))
        draw.rectangle((x - candle_width / 2, body_top, x + candle_width / 2, body_bottom), fill=color)

    draw.line((release_x, top, release_x, bottom), fill=RELEASE, width=3)
    draw.text((release_x + 7, top + 5), "ISM RELEASE", fill=RELEASE, font=font(12, bold=True))
    draw.line((left, y(chart.pre_price), right, y(chart.pre_price)), fill=MUTED, width=1)

    ny = chart.event.release_utc.astimezone(ZoneInfo("America/New_York"))
    heading = f"{chart.event.release_utc:%b %d, %Y} | ISM Manufacturing PMI {chart.event.actual:.1f}"
    subtitle = f"{chart.event.data_month} data | {chart.event.release_utc:%H:%M} UTC / {ny:%H:%M} New York | {broker_symbol} M1"
    draw.text((20, 14), heading, fill=TEXT, font=font(max(17, width // 48), bold=True))
    draw.text((20, 48), subtitle, fill=MUTED, font=font(max(12, width // 72)))
    stats = (
        f"M1 range ${chart.m1_range:.2f} ({chart.m1_range / PIP_SIZE:.0f}p)   "
        f"T+5 {signed(chart.move_5m)}   T+15 {signed(chart.move_15m)}   T+60 {signed(chart.move_60m)}"
    )
    draw.text((20, 75), stats, fill=TEXT, font=font(max(11, width // 84)))

    for minute in (-30, -15, 0, 15, 30, 60):
        stamp = release_stamp + minute * 60
        index = next((i for i, bar in enumerate(chart.bars) if bar["stamp"] == stamp), None)
        if index is None:
            continue
        x = left + (index + 0.5) * step
        label = "T0" if minute == 0 else f"T{minute:+d}"
        draw.text((x, bottom + 13), label, fill=MUTED, font=font(11), anchor="ma")
    return image


def save_report(symbol: str, charts: list[Chart], overview: Path, individuals: list[Path]) -> None:
    fields = [
        "release_utc", "actual", "pre_price", "m1_range_usd", "m1_range_pips",
        "t5_usd", "t15_usd", "t60_usd", "max_up_15m_usd", "max_down_15m_usd", "window_range_usd",
    ]
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for chart in charts:
            writer.writerow(
                {
                    "release_utc": chart.event.release_utc.isoformat(),
                    "actual": chart.event.actual,
                    "pre_price": round(chart.pre_price, 4),
                    "m1_range_usd": round(chart.m1_range, 4),
                    "m1_range_pips": round(chart.m1_range / PIP_SIZE, 1),
                    "t5_usd": round(chart.move_5m, 4),
                    "t15_usd": round(chart.move_15m, 4),
                    "t60_usd": round(chart.move_60m, 4),
                    "max_up_15m_usd": round(chart.max_up_15m, 4),
                    "max_down_15m_usd": round(chart.max_down_15m, 4),
                    "window_range_usd": round(chart.full_range, 4),
                }
            )
    lines = [
        "# XAUUSD M1 Around the Last Five ISM Manufacturing PMI Releases",
        "",
        f"Broker candle source: `{symbol}`. Window: T-30 through T+60. Gold pips use `0.1 = 1 pip`.",
        "",
        f"![Last five overview]({overview.relative_to(ROOT).as_posix()})",
        "",
        "| Release | Actual | Pre-price | M1 range | T+5 | T+15 | T+60 | First-15 max up | First-15 max down |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for chart in charts:
        lines.append(
            f"| {chart.event.release_utc:%Y-%m-%d %H:%M UTC} | {chart.event.actual:.1f} | {chart.pre_price:.2f} | "
            f"${chart.m1_range:.2f} ({chart.m1_range / PIP_SIZE:.0f}p) | {signed(chart.move_5m)} | "
            f"{signed(chart.move_15m)} | {signed(chart.move_60m)} | {signed(chart.max_up_15m)} | {signed(chart.max_down_15m)} |"
        )
    lines.extend(["", "## Full-size charts", ""])
    lines.extend(f"- `{path.relative_to(ROOT).as_posix()}`" for path in individuals)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    symbol, charts = prepare()
    individual_paths: list[Path] = []
    for chart in charts:
        path = OUTPUT_DIR / f"{chart.event.release_utc:%Y-%m-%d}-ism-manufacturing-xauusd-m1.png"
        draw_chart(chart, symbol, 1800, 820).save(path, quality=95)
        individual_paths.append(path)

    panel_width, panel_height, gap = 920, 500, 16
    overview = Image.new("RGB", (panel_width * 2 + gap * 3, panel_height * 3 + gap * 4 + 54), BACKGROUND)
    draw = ImageDraw.Draw(overview)
    draw.text((gap, 14), "XAUUSD M1 | Last Five ISM Manufacturing PMI Releases", fill=TEXT, font=font(28, bold=True))
    for index, chart in enumerate(charts):
        panel = draw_chart(chart, symbol, panel_width, panel_height)
        x = gap + (index % 2) * (panel_width + gap)
        y = 54 + gap + (index // 2) * (panel_height + gap)
        overview.paste(panel, (x, y))
    overview_path = OUTPUT_DIR / "last-five-overview.png"
    overview.save(overview_path, quality=95)
    save_report(symbol, charts, overview_path, individual_paths)
    print(f"Overview: {overview_path}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
