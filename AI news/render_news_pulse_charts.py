from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from PIL import Image, ImageDraw, ImageFont

from news_pending_strategy import CALENDAR_PATH, ROOT, load_day


START = datetime(2026, 6, 1, tzinfo=timezone.utc)
END = datetime(2026, 8, 1, tzinfo=timezone.utc)
BEFORE_MINUTES = 15
AFTER_MINUTES = 30

BACKGROUND = "#070b14"
PANEL = "#0d1422"
GRID = "#243047"
TEXT = "#e8eef9"
MUTED = "#8ea0ba"
UP = "#23c99a"
DOWN = "#ff5d73"
RELEASE = "#f8c44f"
PRE_SHADE = "#101a2d"


@dataclass
class MarketProfile:
    key: str
    symbol: str
    display_name: str
    unit_size: float
    unit_suffix: str
    output_dir: Path
    report_path: Path


PROFILES = {
    "xauusd": MarketProfile(
        key="xauusd",
        symbol="xauusd",
        display_name="XAUUSD",
        unit_size=0.1,
        unit_suffix="p",
        output_dir=ROOT / "charts" / "news-pulses-2026-06-07",
        report_path=ROOT / "NEWS_PULSE_CHARTS_2M.md",
    ),
    "nasdaq": MarketProfile(
        key="nasdaq",
        symbol="usatechidxusd",
        display_name="NASDAQ US100",
        unit_size=1.0,
        unit_suffix=" pts",
        output_dir=ROOT / "charts" / "nasdaq-news-pulses-2026-06-07",
        report_path=ROOT / "NASDAQ_NEWS_PULSE_CHARTS_2M.md",
    ),
}


@dataclass
class EventChart:
    profile: MarketProfile
    event: str
    release: datetime
    title: str
    price_source: str
    bars: list[dict]
    pre_price: float
    first_minute_range: float
    first_minute_close: float
    five_minute_move: float
    fifteen_minute_move: float
    maximum_up: float
    maximum_down: float


def _font(size: int, *, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    path = Path("C:/Windows/Fonts") / name
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def _new_york_time(value: datetime) -> datetime:
    try:
        return value.astimezone(ZoneInfo("America/New_York"))
    except ZoneInfoNotFoundError:
        return value.astimezone(timezone(timedelta(hours=-4)))


def _events() -> list[dict]:
    result = []
    with CALENDAR_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            released = datetime.fromisoformat(row["release_utc"]).astimezone(timezone.utc)
            if START <= released < END:
                result.append({**row, "released": released})
    return sorted(result, key=lambda row: row["released"])


def _mid_bar(bid: dict, ask: dict, stamp: int) -> dict | None:
    if stamp not in bid or stamp not in ask:
        return None
    return {
        "stamp": stamp,
        "open": (bid[stamp]["open"] + ask[stamp]["open"]) / 2,
        "high": (bid[stamp]["high"] + ask[stamp]["high"]) / 2,
        "low": (bid[stamp]["low"] + ask[stamp]["low"]) / 2,
        "close": (bid[stamp]["close"] + ask[stamp]["close"]) / 2,
    }


def _single_side_bar(data: dict, stamp: int) -> dict | None:
    if stamp not in data:
        return None
    return {"stamp": stamp, **{key: data[stamp][key] for key in ("open", "high", "low", "close")}}


def _prepare(event: dict, profile: MarketProfile) -> EventChart | None:
    release = event["released"]
    day = release.date().isoformat()
    bid = load_day(profile.symbol, day, "bid")
    ask = load_day(profile.symbol, day, "ask")
    if not bid and not ask:
        return None
    if bid and ask:
        price_source = "bid/ask midpoint"
        get_bar = lambda stamp: _mid_bar(bid, ask, stamp)
    elif ask:
        price_source = "ask only"
        get_bar = lambda stamp: _single_side_bar(ask, stamp)
    else:
        price_source = "bid only"
        get_bar = lambda stamp: _single_side_bar(bid, stamp)
    release_stamp = int(release.timestamp() * 1000)
    stamps = range(
        release_stamp - BEFORE_MINUTES * 60_000,
        release_stamp + (AFTER_MINUTES + 1) * 60_000,
        60_000,
    )
    bars = [bar for stamp in stamps if (bar := get_bar(stamp))]
    pre = get_bar(release_stamp - 60_000)
    first = get_bar(release_stamp)
    five = get_bar(release_stamp + 4 * 60_000)
    fifteen = get_bar(release_stamp + 14 * 60_000)
    post_15 = [
        bar
        for minute in range(15)
        if (bar := get_bar(release_stamp + minute * 60_000))
    ]
    if not bars or not pre or not first or not five or not fifteen or not post_15:
        return None
    pre_price = pre["close"]
    return EventChart(
        profile=profile,
        event=event["event"],
        release=release,
        title=event["title"],
        price_source=price_source,
        bars=bars,
        pre_price=pre_price,
        first_minute_range=(first["high"] - first["low"]) / profile.unit_size,
        first_minute_close=(first["close"] - pre_price) / profile.unit_size,
        five_minute_move=(five["close"] - pre_price) / profile.unit_size,
        fifteen_minute_move=(fifteen["close"] - pre_price) / profile.unit_size,
        maximum_up=(max(bar["high"] for bar in post_15) - pre_price) / profile.unit_size,
        maximum_down=(min(bar["low"] for bar in post_15) - pre_price) / profile.unit_size,
    )


def _signed(value: float) -> str:
    return f"{value:+,.0f}"


def _draw_panel(chart: EventChart, width: int, height: int) -> Image.Image:
    image = Image.new("RGB", (width, height), PANEL)
    draw = ImageDraw.Draw(image)
    title_font = _font(max(20, width // 40), bold=True)
    body_font = _font(max(15, width // 58))
    small_font = _font(max(13, width // 70))

    left = 72
    right = width - 82
    top = 98
    bottom = height - 62
    plot_width = right - left
    plot_height = bottom - top

    prices = [value for bar in chart.bars for value in (bar["high"], bar["low"])]
    low = min(prices)
    high = max(prices)
    padding = max((high - low) * 0.08, 0.1)
    low -= padding
    high += padding

    def y(value: float) -> float:
        return bottom - (value - low) / (high - low) * plot_height

    count = len(chart.bars)
    step = plot_width / count
    candle_width = max(3, int(step * 0.62))
    release_index = next(
        (index for index, bar in enumerate(chart.bars) if bar["stamp"] == int(chart.release.timestamp() * 1000)),
        BEFORE_MINUTES,
    )
    release_x = left + (release_index + 0.5) * step

    draw.rectangle((left, top, release_x, bottom), fill=PRE_SHADE)
    for index in range(6):
        gy = top + plot_height * index / 5
        draw.line((left, gy, right, gy), fill=GRID, width=1)
        price = high - (high - low) * index / 5
        draw.text((right + 8, gy - 9), f"{price:,.2f}", fill=MUTED, font=small_font)

    for index, bar in enumerate(chart.bars):
        x = left + (index + 0.5) * step
        color = UP if bar["close"] >= bar["open"] else DOWN
        draw.line((x, y(bar["high"]), x, y(bar["low"])), fill=color, width=2)
        body_top = y(max(bar["open"], bar["close"]))
        body_bottom = y(min(bar["open"], bar["close"]))
        if body_bottom - body_top < 2:
            body_bottom = body_top + 2
        draw.rectangle(
            (x - candle_width / 2, body_top, x + candle_width / 2, body_bottom),
            fill=color,
        )

    draw.line((release_x, top, release_x, bottom), fill=RELEASE, width=3)
    draw.text((release_x + 7, top + 5), "RELEASE", fill=RELEASE, font=small_font)
    draw.line((left, y(chart.pre_price), right, y(chart.pre_price)), fill=MUTED, width=1)

    ny = _new_york_time(chart.release)
    heading = f"{chart.release:%b %d, %Y}  {chart.event}"
    timing = f"{chart.release:%H:%M} UTC / {ny:%H:%M} New York / {chart.price_source}"
    draw.text((22, 15), heading, fill=TEXT, font=title_font)
    draw.text((22, 51), timing, fill=MUTED, font=body_font)
    stats = (
        f"M1 range {chart.first_minute_range:,.0f}{chart.profile.unit_suffix}   "
        f"M1 close {_signed(chart.first_minute_close)}{chart.profile.unit_suffix}   "
        f"T+5 {_signed(chart.five_minute_move)}{chart.profile.unit_suffix}   "
        f"T+15 {_signed(chart.fifteen_minute_move)}{chart.profile.unit_suffix}"
    )
    draw.text((width - 25, 58), stats, fill=TEXT, font=small_font, anchor="ra")

    tick_points = ((-15, 0), (0, release_index), (15, release_index + 15), (30, release_index + 30))
    for minute, index in tick_points:
        if 0 <= index < count:
            x = left + (index + 0.5) * step
            draw.text((x, bottom + 15), f"T{minute:+d}" if minute else "T0", fill=MUTED, font=small_font, anchor="ma")
    return image


def _monthly_grid(charts: list[EventChart], month: int, profile: MarketProfile) -> Path:
    chosen = [chart for chart in charts if chart.release.month == month]
    panel_width = 920
    panel_height = 540
    gutter = 18
    header = 76
    canvas = Image.new(
        "RGB",
        (panel_width * 2 + gutter * 3, panel_height * 2 + gutter * 3 + header),
        BACKGROUND,
    )
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (gutter, 18),
        f"{profile.display_name} 1-Minute USD News Pulses - {datetime(2026, month, 1):%B %Y}",
        fill=TEXT,
        font=_font(30, bold=True),
    )
    for index, chart in enumerate(chosen):
        panel = _draw_panel(chart, panel_width, panel_height)
        x = gutter + (index % 2) * (panel_width + gutter)
        y = header + gutter + (index // 2) * (panel_height + gutter)
        canvas.paste(panel, (x, y))
    path = profile.output_dir / f"{profile.key}-news-pulses-2026-{month:02d}.png"
    canvas.save(path, quality=95)
    return path


def run(profile: MarketProfile) -> list[EventChart]:
    profile.output_dir.mkdir(parents=True, exist_ok=True)
    charts = [chart for event in _events() if (chart := _prepare(event, profile))]
    individual_paths = []
    for chart in charts:
        path = profile.output_dir / f"{chart.release:%Y-%m-%d}-{chart.event.lower()}-{profile.key}-m1.png"
        _draw_panel(chart, 1800, 820).save(path, quality=95)
        individual_paths.append(path)
    monthly_paths = [_monthly_grid(charts, month, profile) for month in (6, 7)]

    fallback_sources = sorted({chart.price_source for chart in charts if chart.price_source != "bid/ask midpoint"})
    source_note = (
        "Candles use midpoint OHLC values when both bid and ask are cached. "
        + (
            f"Fallback sources used where one side was unavailable: {', '.join(fallback_sources)}. "
            if fallback_sources
            else ""
        )
        + "The chart window is T-15 through T+30 minutes."
    )

    lines = [
        f"# {profile.display_name} M1 News Pulses - June and July 2026",
        "",
        source_note,
        "",
        "| Date | Event | Source | M1 range | M1 close | T+5 | T+15 | First-15 max up | First-15 max down |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for chart in charts:
        lines.append(
            f"| {chart.release.date()} | {chart.event} | {chart.price_source} | {chart.first_minute_range:.0f}{profile.unit_suffix} | {_signed(chart.first_minute_close)}{profile.unit_suffix} | {_signed(chart.five_minute_move)}{profile.unit_suffix} | {_signed(chart.fifteen_minute_move)}{profile.unit_suffix} | {_signed(chart.maximum_up)}{profile.unit_suffix} | {_signed(chart.maximum_down)}{profile.unit_suffix} |"
        )
    lines.extend(["", "## Monthly grids", ""])
    lines.extend(f"- `{path.relative_to(ROOT)}`" for path in monthly_paths)
    lines.extend(["", "## Individual charts", ""])
    lines.extend(f"- `{path.relative_to(ROOT)}`" for path in individual_paths)
    profile.report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return charts


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=sorted(PROFILES), default="xauusd")
    arguments = parser.parse_args()
    selected_profile = PROFILES[arguments.market]
    rendered = run(selected_profile)
    print(f"Rendered {len(rendered)} event charts to {selected_profile.output_dir}")
