"""Standard statistics of the selected combination on the plain historical ledger (no prop rules applied).

Columns follow the site's research format: trades, trades/month, trades/day, return %, profit factor, win rate,
consistency, average and maximum win/loss streaks, Sharpe (daily, annualised — same definition as every EA page),
max balance drawdown, worst/best day, monthly returns and the EA correlation matrix.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

import numpy as np

from .engine import Sizing
from .ledger import Features


def _streaks(outcomes: list[float]) -> dict[str, float | int | None]:
    runs: dict[bool, list[int]] = {True: [], False: []}
    current: bool | None = None
    length = 0
    for value in outcomes:
        if value == 0:
            if current is not None:
                runs[current].append(length)
            current, length = None, 0
            continue
        sign = value > 0
        if sign == current:
            length += 1
        else:
            if current is not None:
                runs[current].append(length)
            current, length = sign, 1
    if current is not None:
        runs[current].append(length)
    mean = lambda xs: round(sum(xs) / len(xs), 2) if xs else None  # noqa: E731
    return {"avg_win_streak": mean(runs[True]), "avg_loss_streak": mean(runs[False]),
            "max_win_streak": max(runs[True], default=0), "max_loss_streak": max(runs[False], default=0)}


def combo_stats(features: Features, sizing: Sizing) -> dict[str, Any]:
    pnl = features.pnl
    days = features.days
    trades = sorted(features.accepted, key=lambda row: row["closed"])
    outcomes = [row["pnl"] for row in trades]
    n = len(outcomes)
    wins = [v for v in outcomes if v > 0]
    losses = [v for v in outcomes if v < 0]
    growth = np.cumprod(1 + pnl) if sizing == "pct_balance" else 1 + np.cumsum(pnl)
    peak = np.maximum.accumulate(np.concatenate(([1.0], growth)))[1:]
    drawdown = float(((peak - growth) / peak).max() * 100) if days else 0.0
    daily = pnl if sizing == "pct_initial" else pnl  # daily returns relative to the initial balance
    sd = float(np.std(daily))
    trading_days = pnl[features.opened > 0] if features.opened.any() else np.array([])
    active_days = pnl[pnl != 0]
    months: defaultdict[str, float] = defaultdict(float)
    for offset in range(days):
        months[(features.start + timedelta(days=offset)).strftime("%Y-%m")] += float(pnl[offset])
    per_ea = []
    for slug in sorted(features.per_ea_pnl):
        rows = [r["pnl"] for r in trades if r["ea"] == slug]
        gw, gl = sum(v for v in rows if v > 0), -sum(v for v in rows if v < 0)
        per_ea.append({"slug": slug, "trades": len(rows), "net_pct": round(sum(rows) * 100, 2),
                       "profit_factor": round(gw / gl, 2) if gl else None,
                       "win_rate": round(sum(v > 0 for v in rows) / len(rows) * 100, 1) if rows else None})
    slugs = [row["slug"] for row in per_ea]
    corr: list[list[float | None]] = []
    if len(slugs) > 1:
        matrix = np.vstack([features.per_ea_pnl[s] for s in slugs])
        active = matrix.any(axis=0)
        sub = matrix[:, active]
        with np.errstate(invalid="ignore", divide="ignore"):
            c = np.corrcoef(sub) if sub.shape[1] > 2 else np.full((len(slugs), len(slugs)), np.nan)
        corr = [[None if not math.isfinite(v) else round(float(v), 2) for v in row] for row in c]
    span = max(days, 1)
    return {
        "trades": n,
        "trades_per_month": round(n / span * 30.4375, 2),
        "trades_per_day": round(n / span, 3),
        "return_pct": round(float(growth[-1] - 1) * 100, 2) if days else 0.0,
        "profit_factor": round(sum(wins) / -sum(losses), 2) if losses else None,
        "win_rate_pct": round(len(wins) / n * 100, 2) if n else None,
        "consistency_pct": round(float((trading_days > 0).mean() * 100), 1) if trading_days.size else None,
        **_streaks(outcomes),
        "sharpe_annualized": round(float(np.mean(daily)) / sd * math.sqrt(365), 2) if sd > 0 and n >= 10 else None,
        "max_balance_dd_pct": round(drawdown, 2),
        "max_equity_dd_pct": None,  # intratrade equity is not recorded in the cached ledger
        "worst_day_pct": round(float(pnl.min()) * 100, 2) if days else None,
        "best_day_pct": round(float(pnl.max()) * 100, 2) if days else None,
        "worst_intraday_envelope_pct": round(float(features.low_envelope.min()) * 100, 2) if days else None,
        "active_days": int(active_days.size),
        "monthly_returns_pct": {k: round(v * 100, 2) for k, v in sorted(months.items())},
        "per_ea": per_ea,
        "correlation": {"slugs": slugs, "matrix": corr},
        "skipped": features.skipped,
        "window": {"from": features.start.isoformat(),
                   "to": (features.start + timedelta(days=days - 1)).isoformat(), "days": days},
    }


def common_window(windows: list[tuple[date, date]]) -> tuple[date, date]:
    start = max(w[0] for w in windows)
    end = min(w[1] for w in windows)
    if end <= start:
        raise ValueError("The selected EAs have no overlapping evidence window.")
    return start, end
