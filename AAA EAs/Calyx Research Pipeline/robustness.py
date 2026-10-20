"""Shared robustness checks for Calyx research and live monitoring. No MT5, network, trading or optimization.

Added 2026-10-20 (owner request, from the AI Trading Library review):
- best-day / best-trade / worst-day dependence, used as a raw-gate falsifier;
- day-block bootstrap of drawdown and losing streaks, used for per-EA kill-switch thresholds.

Trades are dicts with a close timestamp and a P&L value; both field names are configurable so the same code reads
native ledgers (net_profit, close_time), evidence-cache rows (estimated_r) and live reconstructed trades.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict
from datetime import datetime
from typing import Any, Iterable

DEPENDENCE_RULE = ("For a positive total, the result FAILS if removing the single best day or the single best trade "
                   "leaves a total <= 0. Worst-day removal is reported as a diagnostic (mean-reversion shape), not a gate.")


def _day(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    return str(value).replace('.', '-')[:10]


def daily_totals(trades: Iterable[dict], value: str = 'net_profit', time: str = 'close_time') -> dict[str, float]:
    days: dict[str, float] = defaultdict(float)
    for t in trades:
        days[_day(t[time])] += float(t[value])
    return dict(days)


def dependence(trades: list[dict], value: str = 'net_profit', time: str = 'close_time') -> dict:
    """Best-day / best-trade / worst-day dependence of a closed-trade ledger."""
    pnl = [float(t[value]) for t in trades]
    total = sum(pnl)
    days = daily_totals(trades, value, time)
    out: dict[str, Any] = dict(trades=len(pnl), days=len(days), total=round(total, 4), rule=DEPENDENCE_RULE)
    if not pnl:
        out.update(applicable=False, verdict='NO_TRADES')
        return out
    best_day = max(days.items(), key=lambda kv: kv[1])
    worst_day = min(days.items(), key=lambda kv: kv[1])
    best_trade, worst_trade = max(pnl), min(pnl)
    ranked = sorted(days.values(), reverse=True)
    out.update(
        best_day=dict(date=best_day[0], value=round(best_day[1], 4)),
        worst_day=dict(date=worst_day[0], value=round(worst_day[1], 4)),
        best_trade=round(best_trade, 4), worst_trade=round(worst_trade, 4),
        without_best_day=round(total - best_day[1], 4),
        without_best_trade=round(total - best_trade, 4),
        without_worst_day=round(total - worst_day[1], 4),
        without_top5_days=round(total - sum(ranked[:5]), 4),
        best_day_share_of_total=round(best_day[1] / total, 4) if total > 0 else None,
    )
    if total <= 0:
        out.update(applicable=False, verdict='NOT_APPLICABLE_NON_POSITIVE_TOTAL',
                   best_day_sign_flip=None, best_trade_sign_flip=None)
    else:
        flip_day = total - best_day[1] <= 0
        flip_trade = total - best_trade <= 0
        out.update(applicable=True, best_day_sign_flip=flip_day, best_trade_sign_flip=flip_trade,
                   top5_days_sign_flip=total - sum(ranked[:5]) <= 0,
                   verdict='FAIL' if (flip_day or flip_trade) else 'PASS')
    return out


def dependence_lines(dep: dict, unit: str = '$') -> list[str]:
    """Markdown bullet lines for a study report."""
    if dep.get('verdict') == 'NO_TRADES':
        return ['- Best-day dependence: no trades.']
    f = (lambda v: f'{v:+,.2f} R') if unit == 'R' else (lambda v: f'{v:+,.0f} $')
    return [f"- Total {f(dep['total'])} over {dep['trades']} trades / {dep['days']} days.",
            f"- Best day {dep['best_day']['date']} {f(dep['best_day']['value'])}; without it {f(dep['without_best_day'])}.",
            f"- Best trade {f(dep['best_trade'])}; without it {f(dep['without_best_trade'])}.",
            f"- Without the 5 best days {f(dep['without_top5_days'])}; without the worst day {f(dep['without_worst_day'])} (diagnostic).",
            f"- Verdict: **{dep['verdict']}**."]


def longest_losing_streak(values: Iterable[float]) -> int:
    best = cur = 0
    for v in values:
        if v < 0:
            cur += 1; best = max(best, cur)
        elif v > 0:
            cur = 0
    return best


def max_drawdown(values: Iterable[float]) -> float:
    """Maximum peak-to-trough fall of the cumulative sum (same unit as values), starting from 0."""
    peak = cum = dd = 0.0
    for v in values:
        cum += v; peak = max(peak, cum); dd = max(dd, peak - cum)
    return dd


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return math.nan
    i = min(len(sorted_values) - 1, max(0, math.ceil(q * len(sorted_values)) - 1))
    return sorted_values[i]


def day_block_bootstrap(trades: list[dict], horizon_days: int, *, value: str = 'estimated_r', time: str = 'close_time',
                        paths: int = 10000, block_days: int = 5, seed: int = 20261020,
                        calendar_days: list[str] | None = None) -> dict:
    """Resample trading days (with their trades, in order) in blocks to build horizon-length paths.

    When calendar_days is given, days without trades are kept as empty days so the trade frequency is preserved.
    Returns p50/p95/p99 of max drawdown (in `value` units), longest losing streak (trades) and worst single day.
    """
    by_day: dict[str, list[float]] = defaultdict(list)
    for t in sorted(trades, key=lambda r: str(r[time])):
        by_day[_day(t[time])].append(float(t[value]))
    days = sorted(set(calendar_days) | set(by_day)) if calendar_days else sorted(by_day)
    if not days:
        return dict(paths=0)
    seq = [by_day.get(d, []) for d in days]
    rng = random.Random(seed)
    dds, streaks, worst_days, totals = [], [], [], []
    n = len(seq)
    for _ in range(paths):
        path: list[list[float]] = []
        while len(path) < horizon_days:
            start = rng.randrange(n)
            for k in range(block_days):
                path.append(seq[(start + k) % n])
                if len(path) >= horizon_days:
                    break
        flat = [v for day in path for v in day]
        dds.append(max_drawdown(flat)); streaks.append(longest_losing_streak(flat))
        worst_days.append(min((sum(day) for day in path), default=0.0)); totals.append(sum(flat))
    dds.sort(); streaks.sort(); worst_days.sort(); totals.sort()
    q = lambda arr, p: round(_quantile(arr, p), 4)  # noqa: E731
    return dict(paths=paths, horizon_days=horizon_days, block_days=block_days, seed=seed, source_days=n,
                source_trades=sum(len(d) for d in seq),
                max_drawdown=dict(p50=q(dds, .50), p95=q(dds, .95), p99=q(dds, .99)),
                losing_streak=dict(p50=q(streaks, .50), p95=q(streaks, .95), p99=q(streaks, .99)),
                worst_day=dict(p50=q(worst_days, .50), p05=q(worst_days, .05), p01=q(worst_days, .01)),
                total=dict(p05=q(totals, .05), p50=q(totals, .50), p95=q(totals, .95)))
