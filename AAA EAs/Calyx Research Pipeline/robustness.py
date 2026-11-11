"""Shared robustness checks for Calyx research and live monitoring. No MT5, network, trading or optimization.

Added 2026-10-20 (owner request, from the AI Trading Library review):
- best-day / best-trade / worst-day dependence, used as a raw-gate falsifier;
- day-block bootstrap of drawdown and losing streaks, used for per-EA kill-switch thresholds.
Added 2026-11-04 (owner request, from a pasted clip): `three_monte_carlo`, the stage-6 three-way Monte Carlo:
reshuffle (order luck), resample (trade luck) and randomize (missed trades + worse costs).

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


THREE_MC_RULE = ("Stage 6 three-way Monte Carlo on per-trade results in time order (R or money): RESHUFFLE = same trades, random "
                 "order (total fixed; tests order luck: where the real drawdown ranks among shuffled ones); RESAMPLE = draw trades "
                 "with replacement (tests trade luck: share of runs that end <= 0); RANDOMIZE = drop each trade with probability "
                 "drop_fraction and charge every kept trade an extra cost drawn uniformly from [0, 2 x extra_cost] (tests the "
                 "broker; drop-only and cost-only runs are reported separately so the two causes are not mixed).")


def _dist(arr: list[float]) -> dict:
    arr = sorted(arr)
    return dict(p05=round(_quantile(arr, .05), 4), p50=round(_quantile(arr, .50), 4), p95=round(_quantile(arr, .95), 4),
                p99=round(_quantile(arr, .99), 4))


def _red(totals: list[float]) -> float:
    return round(100.0 * sum(1 for v in totals if v <= 0) / len(totals), 2) if totals else math.nan


def three_monte_carlo(values: list[float], *, runs: int = 1000, seed: int = 20261104, drop_fraction: float = 0.10,
                      extra_cost: float = 0.05, horizon: int | None = None) -> dict:
    """values = per-trade results in time order. horizon=None uses the real sequence length (and, for RANDOMIZE, the real
    order); horizon=k builds k-trade paths by resampling with replacement first (e.g. one year of trades)."""
    vals = [float(v) for v in values]
    n = len(vals)
    if n == 0:
        return dict(trades=0)
    k = horizon or n
    rng = random.Random(seed)
    real = dict(total=round(sum(vals), 4), max_drawdown=round(max_drawdown(vals), 4), losing_streak=longest_losing_streak(vals))

    sh_dd, sh_streak = [], []
    for _ in range(runs):
        path = vals[:]; rng.shuffle(path)
        sh_dd.append(max_drawdown(path)); sh_streak.append(longest_losing_streak(path))
    reshuffle = dict(max_drawdown=_dist(sh_dd), losing_streak=_dist(sh_streak),
                     real_drawdown_worse_than_pct=round(100.0 * sum(1 for d in sh_dd if d < real['max_drawdown']) / runs, 2),
                     real_streak_longer_than_pct=round(100.0 * sum(1 for s in sh_streak if s < real['losing_streak']) / runs, 2))

    def draw() -> list[float]:
        return [vals[rng.randrange(n)] for _ in range(k)] if horizon else vals

    totals, dds = [], []
    for _ in range(runs):
        path = [vals[rng.randrange(n)] for _ in range(k)]
        totals.append(sum(path)); dds.append(max_drawdown(path))
    resample = dict(red_pct=_red(totals), total=_dist(totals), max_drawdown=_dist(dds))

    def randomize(drop: float, cost: float) -> dict:
        tot, dd = [], []
        for _ in range(runs):
            path = [v - (rng.uniform(0, 2 * cost) if cost else 0.0) for v in draw() if not (drop and rng.random() < drop)]
            tot.append(sum(path)); dd.append(max_drawdown(path))
        return dict(red_pct=_red(tot), total=_dist(tot), max_drawdown=_dist(dd))

    return dict(rule=THREE_MC_RULE, trades=n, horizon_trades=k, runs=runs, seed=seed, real=real if not horizon else None,
                reshuffle=reshuffle if not horizon else None, resample=resample,
                randomize=dict(drop_fraction=drop_fraction, extra_cost=extra_cost, both=randomize(drop_fraction, extra_cost),
                               drop_only=randomize(drop_fraction, 0.0), cost_only=randomize(0.0, extra_cost)))


# ---------------------------------------------------------------------------------------------------------------------
# Added 2026-11-11 (owner: "add point 4 to the pipeline", ideas from the QuantLab research library): cost stress at 1x / 2x / 3x
# (stage 4 and 6), a stronger random-entry control (stage 4) and rolling walk-forward with blind runs (stage 5).

COST_STRESS_RULE = ("Recorded per-trade costs (spread + commission + swap, same unit as the results) are multiplied: "
                    "net_k = net - (k - 1) * cost. Gate: the total must stay > 0 at 2x costs; 3x and the break-even multiple are diagnostics.")


def _mean(v: list[float]) -> float:
    return sum(v) / len(v) if v else math.nan


def _tstat(v: list[float]) -> float:
    n = len(v)
    if n < 2:
        return math.nan
    m = _mean(v); var = sum((x - m) ** 2 for x in v) / (n - 1)
    if var <= 0:
        return math.inf if m > 0 else -math.inf if m < 0 else 0.0
    return m / math.sqrt(var / n)


def cost_stress(results: list[float], costs: list[float], multiples: tuple = (1, 2, 3)) -> dict:
    """results = net per-trade results; costs = the (positive) cost each trade already paid, same unit."""
    assert len(results) == len(costs), 'one cost per trade'
    out = {}
    for k in multiples:
        v = [r - (k - 1) * abs(c) for r, c in zip(results, costs)]
        gw = sum(x for x in v if x > 0); gl = -sum(x for x in v if x < 0)
        out[f'{k}x'] = dict(total=round(sum(v), 4), mean=round(_mean(v), 5), pf=round(gw / gl, 3) if gl else None)
    paid = sum(abs(c) for c in costs)
    breakeven = (1 + sum(results) / paid) if paid > 0 else math.inf
    return dict(rule=COST_STRESS_RULE, trades=len(results), costs_paid=round(paid, 4), multiples=out, breakeven_multiple=round(breakeven, 3),
                verdict='PASS' if out.get('2x', {}).get('total', 0) > 0 else 'FAIL')


RANDOM_ENTRY_RULE = ("Each copy keeps every real trade's direction, clock time of day, stop distance, target distance and holding time, "
                     "but enters on a random trading day of the same price history (bars, entry at the bar open). Stop is assumed first "
                     "when stop and target fall in the same bar. p = (copies with mean R >= real mean R + 1) / (copies + 1). "
                     "Raw-gate screen: p <= 0.10 (lenient on purpose: it removes market drift, it does not prove an edge).")


def random_entry_control(trades: list[dict], bars: list[tuple], *, copies: int = 200, seed: int = 20261111, cost_r: float = 0.0) -> dict:
    """trades: dicts with open_epoch, side (+1 / -1), stop (price distance > 0), target (price distance or None), hold_seconds,
    r (real net R). bars: (epoch, open, high, low, close) sorted, one timeframe (M1-M15 recommended). cost_r = cost charged per
    random trade in R (use the real average cost so both sides pay the same)."""
    import bisect
    if not trades or not bars:
        return dict(trades=len(trades), copies=0, verdict='NO_DATA')
    epochs = [b[0] for b in bars]
    days = sorted({e - e % 86400 for e in epochs})
    rng = random.Random(seed)

    def replay(entry_epoch: int, side: int, stop: float, target, hold: int):
        i = bisect.bisect_left(epochs, entry_epoch)
        if i >= len(bars) or bars[i][0] - entry_epoch > 3600:
            return None                                   # no bar near that clock time on that day
        entry = bars[i][1]; end = entry_epoch + max(hold, 60); last = entry
        for j in range(i, len(bars)):
            ep, _o, hi, lo, cl = bars[j]
            if ep > end:
                break
            if (lo <= entry - stop) if side > 0 else (hi >= entry + stop):
                return -1.0 - cost_r
            if target is not None and ((hi >= entry + target) if side > 0 else (lo <= entry - target)):
                return target / stop - cost_r
            last = cl
        return (last - entry) * side / stop - cost_r

    real = [float(t['r']) for t in trades]
    means = []
    for _ in range(copies):
        rs = []
        for t in trades:
            tod = int(t['open_epoch']) % 86400
            for _attempt in range(20):
                r = replay(rng.choice(days) + tod, int(t['side']), float(t['stop']), t.get('target'), int(t['hold_seconds']))
                if r is not None:
                    rs.append(r); break
        means.append(_mean(rs))
    m = _mean(real); s = sorted(means)
    p = (sum(1 for x in means if x >= m) + 1) / (copies + 1)
    return dict(rule=RANDOM_ENTRY_RULE, trades=len(trades), copies=copies, seed=seed, real_mean_r=round(m, 5),
                random_mean_r=dict(p05=round(_quantile(s, .05), 5), p50=round(_quantile(s, .50), 5), p95=round(_quantile(s, .95), 5)),
                p_value=round(p, 4), verdict='PASS' if p <= 0.10 else 'FAIL')


WALK_FORWARD_RULE = ("Rolling walk-forward inside the pre-OOS history (development + validation): train on each fold's training window, "
                     "pick the setting with the best PLATEAU score (mean t-value of the setting and its one-step neighbours, minimum trades), "
                     "trade it on the following test window, step forward, and chain only the test windows. Blind runs repeat the same "
                     "selection on scrambled training scores. Gate: chained test total > 0 and the real chained t-value beats the blind runs "
                     "with p <= 0.10. The fixed last-two-year OOS is still evaluated once afterwards.")


def rolling_folds(start_epoch: int, end_epoch: int, train_days: int = 1095, test_days: int = 365) -> list[tuple]:
    """(train_start, train_end, test_start, test_end) epochs; the first test starts after train_days, steps of test_days."""
    out = []; t0 = start_epoch + train_days * 86400
    while t0 < end_epoch:
        out.append((t0 - train_days * 86400, t0, t0, min(end_epoch, t0 + test_days * 86400))); t0 += test_days * 86400
    return out


def walk_forward(ledgers: dict, neighbours: dict, folds: list[tuple], *, min_trades: int = 30, blind_runs: int = 2000,
                 seed: int = 20261111) -> dict:
    """ledgers: config -> list of (epoch, r) over the pre-OOS history. neighbours: config -> one-step neighbour configs.
    folds: [(train_start, train_end, test_start, test_end)] epochs (see rolling_folds)."""
    configs = list(ledgers)

    def window(cfg, a, b):
        return [r for e, r in ledgers[cfg] if a <= e < b]

    def plateau_scores(a, b):
        t = {}
        for c in configs:
            w = window(c, a, b); t[c] = _tstat(w) if len(w) >= min_trades else -math.inf
        out = {}
        for c in configs:
            if t[c] == -math.inf or math.isnan(t[c]):
                out[c] = -math.inf; continue
            group = [t[c]] + [t[n] for n in neighbours.get(c, []) if n in t and t[n] != -math.inf and not math.isnan(t[n])]
            out[c] = _mean(group)
        return out

    train = [plateau_scores(a, b) for a, b, _c, _d in folds]
    chosen = [max(sc, key=lambda c: sc[c]) if any(v != -math.inf for v in sc.values()) else None for sc in train]
    tests = [window(c, f[2], f[3]) if c else [] for c, f in zip(chosen, folds)]
    chained = [r for t in tests for r in t]
    real_t = _tstat(chained); real_total = sum(chained)
    rng = random.Random(seed); blind_t, blind_total = [], []
    for _ in range(blind_runs):
        path = []
        for sc, f in zip(train, folds):
            eligible = [c for c in configs if sc[c] != -math.inf]
            if not eligible:
                continue
            vals = [sc[c] for c in eligible]; rng.shuffle(vals)                # scrambled training information
            pick = eligible[max(range(len(eligible)), key=lambda i: vals[i])]
            path += window(pick, f[2], f[3])
        blind_t.append(_tstat(path)); blind_total.append(sum(path))
    valid = [x for x in blind_t if not math.isnan(x)]
    p = (sum(1 for x in valid if x >= real_t) + 1) / (len(valid) + 1)
    return dict(rule=WALK_FORWARD_RULE, folds=[dict(choice=c, test_trades=len(t), test_total=round(sum(t), 4)) for c, t in zip(chosen, tests)],
                chained=dict(trades=len(chained), total=round(real_total, 4), mean=round(_mean(chained), 5), t=round(real_t, 3),
                             positive_folds=sum(1 for t in tests if sum(t) > 0), folds=len(folds)),
                blind=dict(runs=blind_runs, real_t_beats_pct=round(100.0 * sum(1 for x in valid if x < real_t) / max(1, len(valid)), 2),
                           real_total_beats_pct=round(100.0 * sum(1 for x in blind_total if x < real_total) / max(1, len(blind_total)), 2), p_value=round(p, 4)),
                verdict='PASS' if real_total > 0 and p <= 0.10 else 'FAIL')
