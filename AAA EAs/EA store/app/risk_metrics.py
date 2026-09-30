"""One consistent risk-adjusted metric for every EA, portfolio and simulation on the site.

Sharpe (daily, annualised) = mean / standard deviation of **daily closed-trade returns** x sqrt(365).

* A daily return is the day's net closed P/L divided by the balance at the start of that day.
* Every calendar day in the evidence window counts; days without a closed trade are 0 % returns.
  Using calendar days (and sqrt(365)) keeps weekday-only EAs and 24/7 crypto EAs on the same scale.
* No risk-free rate is subtracted (cash yield is not part of the EA's result).

The MT5 report's own "Sharpe Ratio" uses a different, platform-specific method, so it is never mixed with this value.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from .evidence_cache import CACHE_ROOT, validate_period

SHARPE_LABEL = "Sharpe (daily, annualised)"
SHARPE_DEFINITION = (
    "Mean ÷ standard deviation of daily closed-trade returns × √365. Every calendar day in the window counts "
    "(no-trade days are 0%); no risk-free rate. Comparable across all EAs, the portfolio and the prop simulator."
)
MIN_TRADES = 10
MIN_DAYS = 30


def _day(value: Any) -> date | None:
    text = str(value or "")
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def daily_returns(trades: Iterable[Mapping[str, Any]], start: date, end: date,
                  initial_balance: float = 10_000.0) -> list[float]:
    """Daily closed-trade returns for every calendar day in [start, end] (inclusive)."""
    pnl_by_day: defaultdict[date, float] = defaultdict(float)
    for trade in trades:
        closed = _day(trade.get("close_time"))
        if closed is not None and start <= closed <= end:
            pnl_by_day[closed] += float(trade.get("net_profit") or 0.0)
    balance = float(initial_balance)
    returns: list[float] = []
    day = start
    while day <= end:
        pnl = pnl_by_day.get(day, 0.0)
        returns.append(pnl / balance if balance > 0 else 0.0)
        balance += pnl
        day += timedelta(days=1)
    return returns


def annualised_sharpe(trades: Iterable[Mapping[str, Any]], start: date, end: date,
                      initial_balance: float = 10_000.0) -> float | None:
    rows = list(trades)
    if len(rows) < MIN_TRADES or (end - start).days + 1 < MIN_DAYS:
        return None
    returns = daily_returns(rows, start, end, initial_balance)
    deviation = statistics.pstdev(returns)
    if deviation <= 0:
        return None
    return round(statistics.fmean(returns) / deviation * math.sqrt(365), 2)


@lru_cache(maxsize=1024)
def _sharpe_from_file(path: str, mtime_ns: int, start: str, end: str, initial: float) -> float | None:
    trades = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return annualised_sharpe(trades, date.fromisoformat(start), date.fromisoformat(end), initial)


def cached_sharpe(kind: str, slug_or_mode: str, mode_or_period: str, period: str | None,
                  stats: Mapping[str, Any] | None) -> float | None:
    """Sharpe for a cached product (kind="products") or portfolio (kind="portfolio") trade file."""
    if not stats:
        return None
    if kind == "products":
        if period is None:
            return None
        validate_period(period)
        path = CACHE_ROOT / "products" / slug_or_mode / mode_or_period / f"{period}.trades.json"
    else:
        validate_period(mode_or_period)
        path = CACHE_ROOT / "portfolio" / slug_or_mode / f"{mode_or_period}.trades.json"
    start, end = _day(stats.get("from")), _day(stats.get("to"))
    if start is None or end is None or not path.is_file():
        return None
    initial = float(stats.get("initial_balance") or 10_000.0)
    return _sharpe_from_file(str(path), path.stat().st_mtime_ns, start.isoformat(), end.isoformat(), initial)


def product_sharpe(slug: str, mode: str, period: str, stats: Mapping[str, Any] | None) -> float | None:
    return cached_sharpe("products", slug, mode, period, stats)


def portfolio_sharpe(mode: str, period: str, stats: Mapping[str, Any] | None) -> float | None:
    return cached_sharpe("portfolio", mode, period, None, stats)
