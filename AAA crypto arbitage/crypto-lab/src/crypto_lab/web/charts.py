"""Tiny server-side SVG charts in the Calyx palette (no JavaScript, CSP-friendly)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from html import escape

WIDTH, HEIGHT, PAD_X, PAD_Y = 900, 280, 56, 28


def line_chart_svg(
    points: Sequence[tuple[datetime, float]], *, start_value: float, label: str = "Balance (USDC)"
) -> str:
    """Balance curve as an inline SVG. Returns an empty-state SVG when there are no points."""
    if not points:
        return (
            f'<svg viewBox="0 0 {WIDTH} {HEIGHT}" class="evidence-chart" role="img" aria-label="No data yet">'
            f'<text x="{WIDTH / 2}" y="{HEIGHT / 2}" text-anchor="middle" class="chart-empty">'
            "No settled paper trades yet</text></svg>"
        )
    t0 = points[0][0].timestamp()
    series = [(t0 - 1, start_value), *[(at.timestamp(), v) for at, v in points]]
    xs, ys = [p[0] for p in series], [p[1] for p in series]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    if y_max == y_min:
        y_min, y_max = y_min - 1, y_max + 1
    x_span, y_span = (x_max - x_min) or 1, y_max - y_min

    def sx(x: float) -> float:
        return PAD_X + (x - x_min) / x_span * (WIDTH - 2 * PAD_X)

    def sy(y: float) -> float:
        return HEIGHT - PAD_Y - (y - y_min) / y_span * (HEIGHT - 2 * PAD_Y)

    path = " ".join(f"{'M' if i == 0 else 'L'}{sx(x):.1f},{sy(y):.1f}" for i, (x, y) in enumerate(series))
    area = f"{path} L{sx(x_max):.1f},{HEIGHT - PAD_Y} L{sx(x_min):.1f},{HEIGHT - PAD_Y} Z"
    grid = "".join(
        f'<line x1="{PAD_X}" x2="{WIDTH - PAD_X}" y1="{sy(v):.1f}" y2="{sy(v):.1f}" class="chart-grid"/>'
        f'<text x="{PAD_X - 8}" y="{sy(v) + 4:.1f}" text-anchor="end" class="chart-axis">{v:,.2f}</text>'
        for v in (y_min, (y_min + y_max) / 2, y_max)
    )
    first, last = points[0][0].strftime("%Y-%m-%d"), points[-1][0].strftime("%Y-%m-%d")
    return (
        f'<svg viewBox="0 0 {WIDTH} {HEIGHT}" class="evidence-chart" role="img" aria-label="{escape(label)}">'
        '<defs><linearGradient id="bal" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0%" stop-color="#7ef7c7" stop-opacity=".28"/>'
        '<stop offset="100%" stop-color="#7ef7c7" stop-opacity="0"/></linearGradient></defs>'
        f"{grid}"
        f'<path d="{area}" fill="url(#bal)"/>'
        f'<path d="{path}" fill="none" stroke="#7ef7c7" stroke-width="2.2" stroke-linejoin="round"/>'
        f'<text x="{PAD_X}" y="{HEIGHT - 6}" class="chart-axis">{first}</text>'
        f'<text x="{WIDTH - PAD_X}" y="{HEIGHT - 6}" text-anchor="end" class="chart-axis">{last}</text>'
        "</svg>"
    )
