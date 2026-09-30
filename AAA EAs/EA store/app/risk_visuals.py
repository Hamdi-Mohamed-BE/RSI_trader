"""Risk-adjusted visuals for every EA: rolling Sharpe trend and win/loss streak distributions.

* Rolling Sharpe uses exactly the headline definition (``app/risk_metrics.py``): daily closed-trade returns, every
  calendar day counted, annualised with √365 — computed over a trailing 90-calendar-day window, sampled weekly.
* Streaks are consecutive winning or losing trades by close time; break-even trades end a streak and count as
  neither (same rule as ``trade_metrics.outcome_streaks``).
Small inline SVGs are generated server-side for catalogue cards (no extra requests, no JavaScript).
"""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Any

from .evidence_cache import CACHE_ROOT, validate_period
from .risk_metrics import SHARPE_DEFINITION, daily_returns

ROLLING_WINDOW_DAYS = 90
SAMPLE_EVERY_DAYS = 7
MIN_TRADES_IN_WINDOW = 5


def _day(value: Any) -> date | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def rolling_sharpe(trades: Sequence[Mapping[str, Any]], start: date, end: date,
                   initial_balance: float = 10_000.0, window: int = ROLLING_WINDOW_DAYS) -> list[dict[str, Any]]:
    returns = daily_returns(trades, start, end, initial_balance)
    closes = [0] * len(returns)
    for trade in trades:
        closed = _day(trade.get("close_time"))
        if closed is not None and start <= closed <= end:
            closes[(closed - start).days] += 1
    points: list[dict[str, Any]] = []
    for last in range(window - 1, len(returns), SAMPLE_EVERY_DAYS):
        chunk = returns[last - window + 1: last + 1]
        n_trades = sum(closes[last - window + 1: last + 1])
        mean = sum(chunk) / window
        var = sum((r - mean) ** 2 for r in chunk) / window
        value = round(mean / math.sqrt(var) * math.sqrt(365), 2) if var > 0 and n_trades >= MIN_TRADES_IN_WINDOW else None
        points.append({"date": (start + timedelta(days=last)).isoformat(), "sharpe": value, "trades": n_trades})
    return points


def streak_distribution(trades: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ordered = sorted(trades, key=lambda t: (str(t.get("close_time")), int(t.get("number") or 0)))
    wins: Counter[int] = Counter()
    losses: Counter[int] = Counter()
    run_sign: bool | None = None
    run_len = 0
    timeline: list[int] = []  # signed streak length after each trade (+ wins, - losses, 0 break-even)

    def flush() -> None:
        if run_sign is not None and run_len:
            (wins if run_sign else losses)[run_len] += 1

    for trade in ordered:
        pnl = float(trade.get("net_profit") or 0.0)
        if pnl == 0:
            flush()
            run_sign, run_len = None, 0
            timeline.append(0)
            continue
        sign = pnl > 0
        if sign == run_sign:
            run_len += 1
        else:
            flush()
            run_sign, run_len = sign, 1
        timeline.append(run_len if sign else -run_len)
    flush()
    mean = lambda c: round(sum(k * v for k, v in c.items()) / sum(c.values()), 2) if c else None  # noqa: E731
    return {"wins": {str(k): v for k, v in sorted(wins.items())}, "losses": {str(k): v for k, v in sorted(losses.items())},
            "max_win_streak": max(wins, default=0), "max_loss_streak": max(losses, default=0),
            "avg_win_streak": mean(wins), "avg_loss_streak": mean(losses), "timeline": timeline}


@lru_cache(maxsize=512)
def _cached(path: str, mtime_ns: int, start: str, end: str, initial: float) -> str:
    trades = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    return json.dumps({"rolling_sharpe": rolling_sharpe(trades, s, e, initial), "streaks": streak_distribution(trades)})


def risk_series(slug: str, mode: str, period: str, stats: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Rolling Sharpe + streak data for a cached product evidence file, or None when unavailable."""
    validate_period(period)
    if not stats:
        return None
    path = CACHE_ROOT / "products" / slug / mode / f"{period}.trades.json"
    start, end = _day(stats.get("from")), _day(stats.get("to"))
    if start is None or end is None or not path.is_file():
        return None
    data = json.loads(_cached(str(path), path.stat().st_mtime_ns, start.isoformat(), end.isoformat(),
                              float(stats.get("initial_balance") or 10_000.0)))
    data.update({"window_days": ROLLING_WINDOW_DAYS, "sample_every_days": SAMPLE_EVERY_DAYS,
                 "definition": SHARPE_DEFINITION, "from": start.isoformat(), "to": end.isoformat()})
    return data


# ---- tiny inline SVGs for catalogue cards ---------------------------------------------------------------------
def sharpe_sparkline_svg(points: Sequence[Mapping[str, Any]], width: int = 132, height: int = 30) -> str:
    values = [p["sharpe"] for p in points if p.get("sharpe") is not None]
    if len(values) < 2:
        return ""
    lo, hi = min(min(values), 0.0), max(max(values), 0.0)
    span = (hi - lo) or 1.0
    xs = [i / (len(values) - 1) * (width - 2) + 1 for i in range(len(values))]
    y = lambda v: height - 2 - (v - lo) / span * (height - 4)  # noqa: E731
    path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y(v):.1f}" for i, (x, v) in enumerate(zip(xs, values)))
    zero = y(0.0)
    last = values[-1]
    colour = "#7ef7c7" if last >= 0 else "#fca5a5"
    title = escape(f"Rolling {ROLLING_WINDOW_DAYS}-day Sharpe (ann.), latest {last:.2f}")
    return (f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" preserveAspectRatio="none" '
            f'class="block" role="img" aria-label="{title}"><title>{title}</title>'
            f'<line x1="0" x2="{width}" y1="{zero:.1f}" y2="{zero:.1f}" stroke="rgba(255,255,255,.18)" '
            f'stroke-dasharray="2 2" vector-effect="non-scaling-stroke"/>'
            f'<path d="{path}" fill="none" stroke="{colour}" stroke-width="1.5" stroke-linejoin="round" '
            f'vector-effect="non-scaling-stroke"/></svg>')


def streak_bars_svg(streaks: Mapping[str, Any], width: int = 132, height: int = 30, max_len: int = 8) -> str:
    wins, losses = streaks.get("wins") or {}, streaks.get("losses") or {}
    if not wins and not losses:
        return ""
    counts_w = [wins.get(str(k), 0) + (sum(v for kk, v in wins.items() if int(kk) > max_len) if k == max_len else 0)
                for k in range(1, max_len + 1)]
    counts_l = [losses.get(str(k), 0) + (sum(v for kk, v in losses.items() if int(kk) > max_len) if k == max_len else 0)
                for k in range(1, max_len + 1)]
    # square-root scale so the rarer long streaks stay visible next to the many 1-trade streaks
    peak = math.sqrt(max(counts_w + counts_l) or 1)
    mid = height / 2
    bar_w = width / max_len
    bars = []
    for i, (cw, cl) in enumerate(zip(counts_w, counts_l)):
        x = i * bar_w + 1
        hw, hl = math.sqrt(cw) / peak * (mid - 1), math.sqrt(cl) / peak * (mid - 1)
        bars.append(f'<rect x="{x:.1f}" y="{mid - hw:.1f}" width="{bar_w - 2:.1f}" height="{hw:.1f}" rx="1" fill="#0ea371"/>')
        bars.append(f'<rect x="{x:.1f}" y="{mid:.1f}" width="{bar_w - 2:.1f}" height="{hl:.1f}" rx="1" fill="#f0443c"/>')
    bars.append(f'<line x1="0" x2="{width}" y1="{mid:.1f}" y2="{mid:.1f}" stroke="rgba(255,255,255,.18)" '
                f'vector-effect="non-scaling-stroke"/>')
    title = escape(f"Streak lengths 1–{max_len}+ (wins up, losses down, square-root scale). Max "
                   f"{streaks.get('max_win_streak')} wins / {streaks.get('max_loss_streak')} losses")
    return (f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" preserveAspectRatio="none" '
            f'class="block" role="img" aria-label="{title}"><title>{title}</title>{"".join(bars)}</svg>')
