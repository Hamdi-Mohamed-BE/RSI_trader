from __future__ import annotations

import gzip
import html
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "weekend-gap" / "xauusd-m1-1y.json.gz"
RESULT_PATH = ROOT / "weekend_gap_backtest_1y.json"
OUTPUT_DIR = ROOT / "charts" / "weekend-gap-best-1y"
GALLERY_PATH = OUTPUT_DIR / "index.html"
REPORT_PATH = ROOT / "WEEKEND_GAP_TRADE_CHARTS.md"

WIDTH = 1600
HEIGHT = 820
LEFT = 82
RIGHT = 1480
TOP = 112
BOTTOM = 718


def svg_text(x: float, y: float, value: str, *, size: int = 16, fill: str = "#dce7f7", anchor: str = "start", weight: int = 400) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" '
        f'font-family="Segoe UI,Arial,sans-serif" text-anchor="{anchor}" font-weight="{weight}">'
        f"{html.escape(value)}</text>"
    )


def time_of(row: dict) -> datetime:
    return datetime.fromtimestamp(int(row["time"]), timezone.utc)


def chart_svg(rows: list[dict], index_by_time: dict[int, int], trade: dict, number: int, config: dict) -> str:
    reference_index = index_by_time[int(datetime.fromisoformat(trade["reference_time"]).timestamp())]
    entry_index = index_by_time[int(datetime.fromisoformat(trade["entry_time"]).timestamp())]
    exit_index = index_by_time[int(datetime.fromisoformat(trade["exit_time"]).timestamp())]
    start_index = max(0, reference_index - 18)
    end_index = min(len(rows) - 1, exit_index + 16)
    bars = rows[start_index : end_index + 1]
    relative_entry = entry_index - start_index
    relative_exit = exit_index - start_index

    levels = [
        float(trade["pending_price"]),
        float(trade["fill_price"]),
        float(trade["stop_loss"]),
        float(trade["take_profit"]),
        float(trade["exit_price"]),
    ]
    lows = [float(row["low"]) for row in bars] + levels
    highs = [float(row["high"]) for row in bars] + levels
    low, high = min(lows), max(highs)
    padding = max(1.0, (high - low) * 0.06)
    low -= padding
    high += padding
    plot_width = RIGHT - LEFT
    plot_height = BOTTOM - TOP
    step = plot_width / max(1, len(bars))

    def x(index: int) -> float:
        return LEFT + (index + 0.5) * step

    def y(price: float) -> float:
        return BOTTOM - (price - low) / (high - low) * plot_height

    result_r = float(trade["result_r"])
    result_color = "#28d7a1" if result_r > 0 else "#ff647c"
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="Trade {number} chart">',
        '<rect width="1600" height="820" fill="#080d16"/>',
        svg_text(40, 42, f"Trade {number:02d} / {trade['side']} / {trade['source'].upper()} FILL", size=28, weight=600),
        svg_text(40, 76, f"Entry {trade['entry_time'][:16].replace('T', ' ')} UTC  |  Exit {trade['exit_time'][:16].replace('T', ' ')} UTC", size=16, fill="#92a6bf"),
        svg_text(1560, 43, f"{result_r:+.3f}R", size=28, fill=result_color, anchor="end", weight=600),
        svg_text(1560, 76, f"{trade['outcome']}  |  spread ${float(trade['spread_usd_at_entry']):.2f}", size=16, fill="#92a6bf", anchor="end"),
        f'<rect x="{LEFT}" y="{TOP}" width="{plot_width}" height="{plot_height}" fill="#0c1421" stroke="#25344a"/>',
    ]

    for grid in range(6):
        price = high - (high - low) * grid / 5
        gy = TOP + plot_height * grid / 5
        parts.append(f'<line x1="{LEFT}" y1="{gy:.1f}" x2="{RIGHT}" y2="{gy:.1f}" stroke="#233047" stroke-width="1"/>')
        parts.append(svg_text(RIGHT + 12, gy + 5, f"{price:,.2f}", size=13, fill="#8799b0"))

    reopen_relative = None
    for index in range(1, len(bars)):
        if int(bars[index]["time"]) - int(bars[index - 1]["time"]) > 24 * 3600:
            reopen_relative = index
            break
    if reopen_relative is not None:
        rx = x(reopen_relative)
        parts.append(f'<rect x="{rx - step / 2:.1f}" y="{TOP}" width="{max(2.0, step):.1f}" height="{plot_height}" fill="#f0bd4e" fill-opacity="0.18"/>')
        parts.append(svg_text(rx + 7, TOP + 21, "WEEKLY REOPEN", size=13, fill="#f0bd4e"))

    candle_width = max(1.0, min(7.0, step * 0.62))
    for index, row in enumerate(bars):
        cx = x(index)
        open_price = float(row["open"])
        close_price = float(row["close"])
        color = "#25c99a" if close_price >= open_price else "#ff6078"
        parts.append(f'<line x1="{cx:.1f}" y1="{y(float(row["high"])):.1f}" x2="{cx:.1f}" y2="{y(float(row["low"])):.1f}" stroke="{color}" stroke-width="1"/>')
        body_top = min(y(open_price), y(close_price))
        body_height = max(1.2, abs(y(open_price) - y(close_price)))
        parts.append(f'<rect x="{cx - candle_width / 2:.1f}" y="{body_top:.1f}" width="{candle_width:.1f}" height="{body_height:.1f}" fill="{color}"/>')

    level_styles = [
        ("PENDING", float(trade["pending_price"]), "#6da9ff", "4 4"),
        ("FILL", float(trade["fill_price"]), "#42d9e8", ""),
        ("SL", float(trade["stop_loss"]), "#ff6078", ""),
        ("TP", float(trade["take_profit"]), "#25c99a", ""),
        ("EXIT", float(trade["exit_price"]), "#f0bd4e", "6 3"),
    ]
    for label, price, color, dash in level_styles:
        ly = y(price)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        parts.append(f'<line x1="{x(relative_entry):.1f}" y1="{ly:.1f}" x2="{RIGHT}" y2="{ly:.1f}" stroke="{color}" stroke-width="1.5"{dash_attr}/>' )
        parts.append(svg_text(RIGHT - 7, ly - 5, f"{label} {price:,.2f}", size=12, fill=color, anchor="end", weight=600))

    entry_x = x(relative_entry)
    exit_x = x(relative_exit)
    parts.append(f'<line x1="{entry_x:.1f}" y1="{TOP}" x2="{entry_x:.1f}" y2="{BOTTOM}" stroke="#42d9e8" stroke-width="2"/>')
    parts.append(f'<line x1="{exit_x:.1f}" y1="{TOP}" x2="{exit_x:.1f}" y2="{BOTTOM}" stroke="#f0bd4e" stroke-width="2"/>')
    parts.append(svg_text(entry_x + 5, BOTTOM - 12, "ENTRY", size=12, fill="#42d9e8"))
    parts.append(svg_text(exit_x - 5, BOTTOM - 12, "EXIT", size=12, fill="#f0bd4e", anchor="end"))

    for tick_index in range(7):
        bar_index = round((len(bars) - 1) * tick_index / 6)
        label = time_of(bars[bar_index]).strftime("%b %d %H:%M")
        parts.append(svg_text(x(bar_index), BOTTOM + 28, label, size=12, fill="#8799b0", anchor="middle"))

    footer = (
        f"Offset ${config['offset_usd']:g}  |  lead {config['placement_lead_minutes']}m  |  "
        f"SL ${config['stop_usd']:g}  |  RR {config['reward_risk']:g}:1  |  max hold {config['max_hold_market_minutes']} market minutes"
    )
    parts.append(svg_text(LEFT, 790, footer, size=15, fill="#92a6bf"))
    parts.append("</svg>")
    return "\n".join(parts)


def equity_svg(trades: list[dict], metrics: dict) -> str:
    width, height = 1600, 720
    left, right, top, bottom = 80, 1530, 110, 625
    values = [0.0]
    for trade in trades:
        values.append(values[-1] + float(trade["result_r"]))
    low, high = min(values), max(values)
    padding = max(2.0, (high - low) * 0.08)
    low -= padding
    high += padding

    def x(index: int) -> float:
        return left + index / max(1, len(values) - 1) * (right - left)

    def y(value: float) -> float:
        return bottom - (value - low) / (high - low) * (bottom - top)

    points = " ".join(f"{x(index):.1f},{y(value):.1f}" for index, value in enumerate(values))
    area = f"{left},{bottom} {points} {right},{bottom}"
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Weekend strategy equity curve">',
        '<rect width="1600" height="720" fill="#080d16"/>',
        svg_text(40, 42, "XAUUSD WEEKEND STRADDLE / CUMULATIVE R", size=28, weight=600),
        svg_text(40, 77, f"{metrics['trades']} trades  |  win {metrics['win_rate_pct']:.2f}%  |  PF {metrics['profit_factor']:.3f}  |  DD {metrics['max_drawdown_r']:.2f}R", size=17, fill="#92a6bf"),
        svg_text(1560, 47, f"{metrics['net_r']:+.2f}R", size=30, fill="#25c99a", anchor="end", weight=600),
    ]
    for grid in range(6):
        value = high - (high - low) * grid / 5
        gy = top + (bottom - top) * grid / 5
        parts.append(f'<line x1="{left}" y1="{gy:.1f}" x2="{right}" y2="{gy:.1f}" stroke="#233047"/>')
        parts.append(svg_text(left - 12, gy + 5, f"{value:+.0f}R", size=13, fill="#8799b0", anchor="end"))
    parts.append(f'<polygon points="{area}" fill="#25c99a" fill-opacity="0.14"/>')
    parts.append(f'<polyline points="{points}" fill="none" stroke="#25c99a" stroke-width="3"/>')
    for index, trade in enumerate(trades, 1):
        color = "#25c99a" if float(trade["result_r"]) > 0 else "#ff6078"
        parts.append(f'<circle cx="{x(index):.1f}" cy="{y(values[index]):.1f}" r="4" fill="{color}"/>')
    parts.append(svg_text(left, bottom + 34, "Trade 1", size=13, fill="#8799b0"))
    parts.append(svg_text(right, bottom + 34, f"Trade {len(trades)}", size=13, fill="#8799b0", anchor="end"))
    parts.append("</svg>")
    return "\n".join(parts)


def run() -> list[Path]:
    with gzip.open(DATA_PATH, "rt", encoding="utf-8") as handle:
        market = json.load(handle)
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    rows = market["rows"]
    trades = result["trades"]
    config = result["robust_selection"]["config"]
    metrics = result["robust_selection"]["metrics"]
    index_by_time = {int(row["time"]): index for index, row in enumerate(rows)}
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for old_chart in OUTPUT_DIR.glob("trade-*.svg"):
        old_chart.unlink()

    summary_path = OUTPUT_DIR / "equity-summary.svg"
    summary_path.write_text(equity_svg(trades, metrics), encoding="utf-8")
    paths: list[Path] = []
    cards: list[str] = []
    markdown = [
        "# XAUUSD Weekend-Straddle Trade Charts",
        "",
        f"Configuration: offset ${config['offset_usd']}, lead {config['placement_lead_minutes']}m, SL ${config['stop_usd']}, RR {config['reward_risk']}:1, hold {config['max_hold_market_minutes']} market minutes.",
        "",
        f"![Equity summary]({summary_path.relative_to(ROOT).as_posix()})",
        "",
    ]
    for number, trade in enumerate(trades, 1):
        date = trade["weekend_open"][:10]
        slug = f"trade-{number:02d}-{date}-{trade['side'].lower()}-{trade['source']}"
        path = OUTPUT_DIR / f"{slug}.svg"
        path.write_text(chart_svg(rows, index_by_time, trade, number, config), encoding="utf-8")
        paths.append(path)
        result_class = "win" if float(trade["result_r"]) > 0 else "loss"
        cards.append(
            f'<article class="trade-card {result_class}"><a href="{path.name}"><img src="{path.name}" alt="Trade {number} {html.escape(trade["side"])} chart"></a>'
            f'<div><strong>#{number:02d} {date} {html.escape(trade["side"])}</strong><span>{float(trade["result_r"]):+.3f}R / {html.escape(trade["outcome"])}</span></div></article>'
        )
        markdown += [
            f"## Trade {number:02d} - {date} - {trade['side']} - {float(trade['result_r']):+.3f}R",
            "",
            f"![Trade {number:02d}]({path.relative_to(ROOT).as_posix()})",
            "",
        ]

    gallery = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>XAUUSD Weekend-Straddle Trade Charts</title>
<style>
body{{margin:0;background:#f4f6f8;color:#17202b;font-family:Segoe UI,Arial,sans-serif}}main{{max-width:1500px;margin:auto;padding:28px}}h1{{font-size:30px;margin:0 0 8px}}p{{color:#526171;margin:0 0 24px}}.summary{{width:100%;display:block;background:#080d16;border-radius:8px;margin-bottom:24px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:16px}}.trade-card{{background:#fff;border:1px solid #dce2e8;border-radius:8px;overflow:hidden;border-left:4px solid #25a97f}}.trade-card.loss{{border-left-color:#e34f66}}.trade-card img{{display:block;width:100%;height:auto;background:#080d16}}.trade-card div{{display:flex;justify-content:space-between;gap:12px;padding:12px 14px}}.trade-card span{{color:#526171}}@media(max-width:560px){{main{{padding:14px}}.grid{{grid-template-columns:1fr}}.trade-card div{{display:block}}.trade-card span{{display:block;margin-top:4px}}}}
</style></head><body><main><h1>XAUUSD Weekend-Straddle Trades</h1>
<p>{metrics['trades']} trades / {metrics['win_rate_pct']:.2f}% win rate / PF {metrics['profit_factor']:.3f} / {metrics['net_r']:+.2f}R. Click any chart for the full SVG.</p>
<img class="summary" src="{summary_path.name}" alt="Cumulative R equity curve"><section class="grid">{''.join(cards)}</section></main></body></html>"""
    GALLERY_PATH.write_text(gallery, encoding="utf-8")
    REPORT_PATH.write_text("\n".join(markdown), encoding="utf-8")
    return [summary_path, *paths]


if __name__ == "__main__":
    generated = run()
    print(f"Generated {len(generated) - 1} trade charts plus summary.")
    print(GALLERY_PATH)
