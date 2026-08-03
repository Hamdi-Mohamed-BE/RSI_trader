from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import MetaTrader5 as mt5
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "charts" / "nzd-labour-usdnzd-m1"
NZ = ZoneInfo("Pacific/Auckland")
PIP = 0.0001


@dataclass(frozen=True)
class Release:
    quarter: str
    local_time: datetime
    employment: str
    unemployment: str

    @property
    def utc_time(self) -> datetime:
        return self.local_time.astimezone(UTC)


RELEASES = [
    Release("Mar 2026", datetime(2026, 5, 6, 10, 45, tzinfo=NZ), "+0.2%", "5.3%"),
    Release("Dec 2025", datetime(2026, 2, 4, 10, 45, tzinfo=NZ), "n/a", "5.4%"),
    Release("Sep 2025", datetime(2025, 11, 5, 10, 45, tzinfo=NZ), "n/a", "5.3%"),
    Release("Jun 2025", datetime(2025, 8, 6, 10, 45, tzinfo=NZ), "n/a", "5.2%"),
    Release("Mar 2025", datetime(2025, 5, 7, 10, 45, tzinfo=NZ), "n/a", "5.1%"),
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def discover_source_symbol() -> tuple[str, bool]:
    symbols = mt5.symbols_get() or []
    names = [item.name for item in symbols]
    native = next((name for name in names if "USDNZD" in name.upper()), None)
    if native:
        return native, False
    inverse = next((name for name in names if "NZDUSD" in name.upper()), None)
    if inverse:
        return inverse, True
    raise RuntimeError("The connected MT5 account exposes neither USDNZD nor NZDUSD.")


def load_window(symbol: str, release: Release, invert: bool) -> list[dict[str, float | datetime]]:
    start = release.utc_time - timedelta(minutes=31)
    end = release.utc_time + timedelta(minutes=61)
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, end)
    if rates is None or len(rates) < 60:
        raise RuntimeError(
            f"Incomplete M1 history for {symbol} at {release.utc_time.isoformat()}: "
            f"{0 if rates is None else len(rates)} bars; MT5={mt5.last_error()}"
        )

    rows: list[dict[str, float | datetime]] = []
    for rate in rates:
        stamp = datetime.fromtimestamp(int(rate["time"]), UTC)
        if stamp < release.utc_time - timedelta(minutes=30) or stamp > release.utc_time + timedelta(minutes=60):
            continue
        if invert:
            open_, high, low, close = (
                1.0 / float(rate["open"]),
                1.0 / float(rate["low"]),
                1.0 / float(rate["high"]),
                1.0 / float(rate["close"]),
            )
        else:
            open_, high, low, close = map(float, (rate["open"], rate["high"], rate["low"], rate["close"]))
        rows.append({"time": stamp, "open": open_, "high": high, "low": low, "close": close})
    return rows


def nearest(rows: list[dict[str, float | datetime]], stamp: datetime) -> dict[str, float | datetime]:
    return min(rows, key=lambda row: abs((row["time"] - stamp).total_seconds()))  # type: ignore[operator]


def stats(rows: list[dict[str, float | datetime]], release: Release) -> dict[str, float | str]:
    event_bar = nearest(rows, release.utc_time)
    base = float(event_bar["open"])
    result: dict[str, float | str] = {
        "quarter": release.quarter,
        "release_nz": release.local_time.strftime("%Y-%m-%d %H:%M %Z"),
        "release_utc": release.utc_time.strftime("%Y-%m-%d %H:%M UTC"),
        "employment_change": release.employment,
        "unemployment_rate": release.unemployment,
        "m1_range_pips": (float(event_bar["high"]) - float(event_bar["low"])) / PIP,
    }
    for minutes in (1, 5, 15, 60):
        row = nearest(rows, release.utc_time + timedelta(minutes=minutes - 1))
        result[f"t_plus_{minutes}_pips"] = (float(row["close"]) - base) / PIP
    return result


def draw_chart(
    rows: list[dict[str, float | datetime]],
    release: Release,
    width: int,
    height: int,
    subtitle: str,
) -> Image.Image:
    bg, panel, grid = "#071019", "#0b1622", "#203344"
    green, red, ink, muted, accent = "#21d4a2", "#ff6074", "#eff7ff", "#91a4b7", "#ffc857"
    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)
    left, top, right, bottom = 70, 88, width - 88, height - 62
    draw.rounded_rectangle((18, 18, width - 18, height - 18), radius=8, fill=panel, outline="#294055", width=2)
    draw.text((36, 31), f"USDNZD M1 | NZ Labour Market | {release.quarter}", font=font(23, True), fill=ink)
    draw.text((36, 59), subtitle, font=font(14), fill=muted)

    lows = [float(row["low"]) for row in rows]
    highs = [float(row["high"]) for row in rows]
    pad = max((max(highs) - min(lows)) * 0.10, 0.00003)
    lo, hi = min(lows) - pad, max(highs) + pad
    plot_w, plot_h = right - left, bottom - top

    def y(price: float) -> float:
        return bottom - ((price - lo) / (hi - lo)) * plot_h

    for i in range(6):
        yy = top + i * plot_h / 5
        price = hi - i * (hi - lo) / 5
        draw.line((left, yy, right, yy), fill=grid, width=1)
        draw.text((right + 8, yy - 8), f"{price:.5f}", font=font(12), fill=muted)
    for minute in (-30, -15, 0, 15, 30, 45, 60):
        x = left + ((minute + 30) / 90) * plot_w
        draw.line((x, top, x, bottom), fill=accent if minute == 0 else grid, width=2 if minute == 0 else 1)
        label = "Release" if minute == 0 else f"T{minute:+d}"
        draw.text((x - 18, bottom + 13), label, font=font(11, minute == 0), fill=accent if minute == 0 else muted)

    candle_w = max(2, int(plot_w / max(len(rows), 1) * 0.62))
    first_time = rows[0]["time"]
    last_time = rows[-1]["time"]
    span = max((last_time - first_time).total_seconds(), 60)  # type: ignore[operator]
    for row in rows:
        x = left + ((row["time"] - first_time).total_seconds() / span) * plot_w  # type: ignore[operator]
        open_, high_, low_, close = (float(row[key]) for key in ("open", "high", "low", "close"))
        color = green if close >= open_ else red
        draw.line((x, y(high_), x, y(low_)), fill=color, width=1)
        y1, y2 = y(open_), y(close)
        draw.rectangle((x - candle_w / 2, min(y1, y2), x + candle_w / 2, max(y1, y2) + 1), fill=color)
    return image


def build_overview(charts: list[Image.Image], rows: list[dict[str, float | str]], source_note: str) -> Image.Image:
    width, height = 1920, 1710
    canvas = Image.new("RGB", (width, height), "#050c13")
    draw = ImageDraw.Draw(canvas)
    draw.text((52, 34), "Last five NZ employment releases | USDNZD one-minute reaction", font=font(32, True), fill="#eff7ff")
    draw.text((52, 75), source_note, font=font(16), fill="#91a4b7")
    tile_w, tile_h = 900, 500
    positions = [(42, 120), (978, 120), (42, 640), (978, 640), (42, 1160)]
    for chart, pos in zip(charts, positions):
        canvas.paste(chart.resize((tile_w, tile_h), Image.Resampling.LANCZOS), pos)

    x, y = 1000, 1170
    draw.rounded_rectangle((x, y, 1878, 1660), radius=8, fill="#0b1622", outline="#294055", width=2)
    draw.text((x + 28, y + 26), "Impulse summary (USDNZD pips)", font=font(22, True), fill="#eff7ff")
    headers = ["Release", "M1 range", "T+5", "T+15", "T+60"]
    cols = [x + 28, x + 270, x + 420, x + 545, x + 675]
    for xx, header in zip(cols, headers):
        draw.text((xx, y + 75), header, font=font(14, True), fill="#91a4b7")
    for i, row in enumerate(rows):
        yy = y + 114 + i * 57
        draw.line((x + 24, yy - 12, 1848, yy - 12), fill="#203344", width=1)
        values = [
            str(row["quarter"]),
            f"{float(row['m1_range_pips']):.1f}",
            f"{float(row['t_plus_5_pips']):+.1f}",
            f"{float(row['t_plus_15_pips']):+.1f}",
            f"{float(row['t_plus_60_pips']):+.1f}",
        ]
        for xx, value in zip(cols, values):
            color = "#21d4a2" if value.startswith("+") else "#ff6074" if value.startswith("-") else "#eff7ff"
            draw.text((xx, yy), value, font=font(15, i == 0), fill=color)
    draw.text((x + 28, y + 445), "Positive = USD up / NZD down. Negative = USD down / NZD up.", font=font(13), fill="#91a4b7")
    return canvas


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        symbol, invert = discover_source_symbol()
        mt5.symbol_select(symbol, True)
        all_rows = [(release, load_window(symbol, release, invert)) for release in RELEASES]
    finally:
        mt5.shutdown()

    summary: list[dict[str, float | str]] = []
    charts: list[Image.Image] = []
    source_note = f"Broker source: {symbol}; " + ("synthetic inverse USDNZD = 1/NZDUSD" if invert else "native USDNZD")
    for release, rows in all_rows:
        row_stats = stats(rows, release)
        summary.append(row_stats)
        subtitle = f"Released {release.local_time:%d %b %Y %H:%M} NZ | {release.utc_time:%d %b %Y %H:%M} UTC | {source_note}"
        chart = draw_chart(rows, release, 1200, 680, subtitle)
        charts.append(chart)
        chart.save(OUTPUT / f"{release.local_time:%Y-%m-%d}-usdnzd-m1.png")

    with (OUTPUT / "last-five-stats.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)

    overview = build_overview(charts, summary, source_note)
    overview.save(OUTPUT / "last-five-overview.png")
    print(f"source={symbol} invert={invert}")
    for row in summary:
        print(row)
    print(OUTPUT / "last-five-overview.png")


if __name__ == "__main__":
    main()
