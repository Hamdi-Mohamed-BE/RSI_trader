"""Standard Calyx results table from a list of closed trades.

Columns: trades, trades/month, trades/day, return %, profit factor, win rate, consistency score, average win/loss
streak, Sharpe, max balance drawdown and max equity drawdown.

Definitions (kept explicit so reports are comparable):

* **Consistency score** — share of calendar days with trades that ended with positive P/L.
* **Sharpe** — mean / stdev of daily P/L as a fraction of starting balance, annualised with √365 (these venues trade
  every day). ``None`` with fewer than 2 trading days.
* **Max balance DD** — peak-to-trough of the closed-trade balance curve, in % of the peak.
* **Max equity DD** — requires mark-to-market of open positions; ``None`` until a source provides it (missing data is
  reported as missing, not as zero).
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class ClosedTrade:
    closed_at: datetime
    pnl: Decimal


@dataclass(frozen=True, slots=True)
class PerformanceTable:
    trades: int
    trades_per_month: float | None
    trades_per_day: float | None
    return_pct: float
    profit_factor: float | None
    win_rate: float | None
    consistency: float | None
    avg_win_streak: float | None
    avg_loss_streak: float | None
    sharpe: float | None
    max_balance_dd_pct: float
    max_equity_dd_pct: float | None
    net_pnl: Decimal
    first_at: datetime | None
    last_at: datetime | None
    balance_curve: tuple[tuple[datetime, Decimal], ...]


def _streaks(signs: Sequence[bool]) -> tuple[float | None, float | None]:
    wins: list[int] = []
    losses: list[int] = []
    current, run = None, 0
    for s in signs:
        if s == current:
            run += 1
            continue
        if current is not None:
            (wins if current else losses).append(run)
        current, run = s, 1
    if current is not None:
        (wins if current else losses).append(run)
    return _mean(wins), _mean(losses)


def _mean(values: Sequence[int]) -> float | None:
    return sum(values) / len(values) if values else None


def performance_table(
    trades: Sequence[ClosedTrade],
    starting_balance: Decimal,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    equity_dd_pct: float | None = None,
) -> PerformanceTable:
    ordered = sorted(trades, key=lambda t: t.closed_at)
    n = len(ordered)
    start = period_start or (ordered[0].closed_at if ordered else None)
    end = period_end or (ordered[-1].closed_at if ordered else None)
    span_days = max((end - start).total_seconds() / 86400, 1.0) if start and end else None

    balance, peak, max_dd = starting_balance, starting_balance, 0.0
    curve: list[tuple[datetime, Decimal]] = []
    for t in ordered:
        balance += t.pnl
        curve.append((t.closed_at, balance))
        peak = max(peak, balance)
        if peak > 0:
            max_dd = max(max_dd, float((peak - balance) / peak * 100))

    gross_win = sum((t.pnl for t in ordered if t.pnl > 0), ZERO)
    gross_loss = -sum((t.pnl for t in ordered if t.pnl < 0), ZERO)
    decided = [t for t in ordered if t.pnl != 0]
    wins = sum(1 for t in decided if t.pnl > 0)

    daily: defaultdict[date, Decimal] = defaultdict(lambda: ZERO)
    for t in ordered:
        daily[t.closed_at.date()] += t.pnl
    day_returns = [float(v / starting_balance) for v in daily.values()] if starting_balance else []
    sharpe = None
    if len(day_returns) >= 2:
        mean = sum(day_returns) / len(day_returns)
        var = sum((r - mean) ** 2 for r in day_returns) / (len(day_returns) - 1)
        sharpe = mean / math.sqrt(var) * math.sqrt(365) if var > 0 else None

    avg_win_streak, avg_loss_streak = _streaks([t.pnl > 0 for t in decided])
    net = sum((t.pnl for t in ordered), ZERO)
    return PerformanceTable(
        trades=n,
        trades_per_month=n / span_days * 30.4375 if span_days else None,
        trades_per_day=n / span_days if span_days else None,
        return_pct=float(net / starting_balance * 100) if starting_balance else 0.0,
        profit_factor=float(gross_win / gross_loss) if gross_loss else None,
        win_rate=wins / len(decided) if decided else None,
        consistency=sum(1 for v in daily.values() if v > 0) / len(daily) if daily else None,
        avg_win_streak=avg_win_streak,
        avg_loss_streak=avg_loss_streak,
        sharpe=sharpe,
        max_balance_dd_pct=max_dd,
        max_equity_dd_pct=equity_dd_pct,
        net_pnl=net,
        first_at=ordered[0].closed_at if ordered else None,
        last_at=ordered[-1].closed_at if ordered else None,
        balance_curve=tuple(curve),
    )
