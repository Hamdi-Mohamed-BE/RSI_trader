"""Offline, allocation-based weekend robustness; no files, network or MT5 calls.

Returns are decimal NET cash changes per unit of entry notional, not percentages
or stop-defined R. A return of .01 means +1%. The replay allocates 1x current
cash, compounds it, and never describes a no-stop position as 1% account risk.
One shared sampled weekly record sequence drives return, cash-PF, DD and streaks.
Intratrade paths are optional *samples*, never certified tick-level equity.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import math
from statistics import NormalDist
from typing import Sequence
from zoneinfo import ZoneInfo

import numpy as np

NY = ZoneInfo("America/New_York")
DEFAULT_SEED = 2026101701


def wilson_interval(wins: int, total: int, confidence: float = .95) -> dict:
    if total < 0 or not 0 <= wins <= total or not 0 < confidence < 1:
        raise ValueError("Invalid binomial counts/confidence")
    if total == 0:
        return {"lower_pct": None, "upper_pct": None, "confidence": confidence}
    z = NormalDist().inv_cdf((1 + confidence) / 2)
    p = wins / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return {"lower_pct": (centre - half) * 100,
            "upper_pct": (centre + half) * 100, "confidence": confidence,
            "caveat": "Binomial descriptive interval; serial dependence is not corrected."}


def _sharpe(values, annualization=52.0):
    a = np.asarray(values, dtype=float)
    if len(a) < 2 or not np.isfinite(a).all():
        return None
    sd = float(a.std(ddof=1))
    return float(a.mean() / sd * math.sqrt(annualization)) if sd > 0 else None


def deflated_sharpe(weekly_returns, tested_configurations: int,
                    trial_sharpe_std: float | None = None) -> dict:
    """DSR approximation; supplied dispersion is UNANNUALIZED weekly SR across trials."""
    if int(tested_configurations) != tested_configurations or tested_configurations < 1:
        raise ValueError("Use the actual positive unique configuration count")
    x = np.asarray(weekly_returns, dtype=float)
    if len(x) < 3 or not np.isfinite(x).all() or x.std(ddof=1) <= 0:
        return {"status": "insufficient_variation", "tested_configurations": int(tested_configurations),
                "dsr_pct": None, "periods_per_year": 52}
    sr = float(x.mean() / x.std(ddof=1))
    centred = x - x.mean()
    m2 = float(np.mean(centred ** 2))
    skew = float(np.mean(centred ** 3) / m2 ** 1.5)
    kurtosis = float(np.mean(centred ** 4) / m2 ** 2)
    se = math.sqrt(max(1e-12, 1 - skew * sr + (kurtosis - 1) * sr * sr / 4) / (len(x) - 1))
    dispersion = se if trial_sharpe_std is None else float(trial_sharpe_std)
    if not math.isfinite(dispersion) or dispersion < 0:
        raise ValueError("Invalid unannualized trial SR dispersion")
    n = int(tested_configurations)
    normal = NormalDist()
    gamma = .5772156649015329
    expected_max = 0.0 if n == 1 else dispersion * (
        (1 - gamma) * normal.inv_cdf(1 - 1 / n)
        + gamma * normal.inv_cdf(1 - 1 / (n * math.e)))
    return {"status": "complete", "dsr_pct": normal.cdf((sr - expected_max) / se) * 100,
            "annualized_weekly_sharpe": sr * math.sqrt(52), "periods_per_year": 52,
            "tested_configurations": n, "weekly_observations": len(x),
            "trial_unannualized_sr_std": dispersion,
            "dispersion_source": "across-searched-development-trials" if trial_sharpe_std is not None
            else "standard-error approximation; cross-trial dispersion unavailable",
            "benchmark_annualized_weekly_sharpe": expected_max * math.sqrt(52),
            "caveat": "Approximation with nominal independent-trial count; correlated searches and prior undisclosed trials are not fully corrected."}


def _normalize_record(row: dict) -> dict:
    result = row.get("return_per_notional", row.get("gross_return_per_notional", row.get("return")))
    if result is None or not math.isfinite(float(result)) or float(result) < -1:
        raise ValueError("Finite decimal entry-notional return >= -1 is required")
    result = float(result)
    entry, exit_time = int(row["entry_epoch"]), int(row["exit_epoch"])
    if exit_time <= entry:
        raise ValueError("Closed trade must exit after entry")
    week = str(row.get("week_id") or datetime.fromtimestamp(entry, NY).date().isoformat())
    path = row.get("intratrade_path")
    factors = [1.0]
    previous = entry
    if path:
        for point in path:
            epoch, factor = int(point["epoch"]), float(point["equity_factor"])
            if not entry <= epoch <= exit_time or epoch < previous or not math.isfinite(factor) or factor < 0:
                raise ValueError("Invalid chronological intratrade factor path")
            factors.append(factor)
            previous = epoch
    factors.append(1 + result)  # closing fees/costs reconcile through the final net return
    f = np.asarray(factors)
    peaks = np.maximum.accumulate(f)
    dd = np.divide(peaks - f, peaks, out=np.zeros_like(f), where=peaks > 0)
    return {"week_id": week, "entry_epoch": entry, "exit_epoch": exit_time,
            "return": result, "min_factor": float(f.min()), "max_factor": float(f.max()),
            "internal_dd": float(dd.max()), "traded": True,
            "has_path": any(entry < int(p["epoch"]) < exit_time for p in (path or [])),
            "cost_basis": str(row.get("cost_basis", "caller-supplied unit-notional return"))}


def _grid(records: Sequence[dict], scheduled_week_ids: Sequence[str] | None):
    rows = sorted((_normalize_record(r) for r in records), key=lambda r: (r["entry_epoch"], r["exit_epoch"]))
    if any(a["exit_epoch"] > b["entry_epoch"] for a, b in zip(rows, rows[1:])):
        raise ValueError("Overlapping positions are outside this one-position weekend model")
    by_week = {r["week_id"]: r for r in rows}
    if len(by_week) != len(rows):
        raise ValueError("Only one position per scheduled week is supported")
    explicit = scheduled_week_ids is not None
    weeks = list(map(str, scheduled_week_ids)) if explicit else [r["week_id"] for r in rows]
    if len(weeks) != len(set(weeks)) or weeks != sorted(weeks):
        raise ValueError("Scheduled Friday IDs must be unique and chronological")
    if set(by_week) - set(weeks):
        raise ValueError("Trade week is not in the authoritative scheduled-week universe")
    blank = {"return": 0.0, "min_factor": 1.0, "max_factor": 1.0,
             "internal_dd": 0.0, "traded": False, "has_path": False}
    grid = [by_week.get(week, dict(blank, week_id=week)) for week in weeks]
    return rows, weeks, grid, explicit


def _arrays(grid):
    return {key: np.asarray([r[key] for r in grid], dtype=bool if key == "traded" else float)
            for key in ["return", "min_factor", "max_factor", "internal_dd", "traded"]}


def _evaluate(a: dict, indices, initial=10000.0, keep=None):
    """Vectorized exact concatenation of record-path DD summaries, not mixed resamples."""
    if not math.isfinite(initial) or initial <= 0:
        raise ValueError("Positive initial cash is required")
    idx = np.asarray(indices, dtype=int)
    if idx.ndim == 1:
        idx = idx[None, :]
    if idx.shape[1] == 0:
        raise ValueError("Empty sample")
    returns = a["return"][idx]
    low, high, internal = a["min_factor"][idx], a["max_factor"][idx], a["internal_dd"][idx]
    flags = a["traded"][idx]
    if keep is not None:
        keep = np.asarray(keep, dtype=bool)
        returns = np.where(keep, returns, 0)
        low, high = np.where(keep, low, 1), np.where(keep, high, 1)
        internal, flags = np.where(keep, internal, 0), flags & keep
    after = initial * np.cumprod(1 + returns, axis=1)
    before = np.c_[np.full(len(idx), initial), after[:, :-1]]
    executed = flags & (before > 0)
    pnl = before * returns
    record_high = before * high
    peak_before = np.c_[np.full(len(idx), initial),
                        np.maximum.accumulate(np.maximum(record_high, initial), axis=1)[:, :-1]]
    external = np.divide(peak_before - before * low, peak_before,
                         out=np.zeros_like(before), where=peak_before > 0)
    sampled_dd = np.maximum(external, np.where(before > 0, internal, 0)).max(axis=1)
    closed_curve = np.c_[np.full(len(idx), initial), after]
    closed_peaks = np.maximum.accumulate(closed_curve, axis=1)
    closed_dd = (1 - closed_curve / closed_peaks).max(axis=1)
    gains, losses = np.maximum(pnl, 0).sum(axis=1), -np.minimum(pnl, 0).sum(axis=1)
    pf = np.divide(gains, losses, out=np.full(len(idx), np.nan), where=losses > 0)
    pf[(losses == 0) & (gains > 0)] = np.inf
    wins, loses = ((pnl > 1e-12) & executed).sum(axis=1), ((pnl < -1e-12) & executed).sum(axis=1)
    current_win = np.zeros(len(idx), dtype=int)
    current_loss = current_win.copy()
    max_win, max_loss = current_win.copy(), current_win.copy()
    for j in range(idx.shape[1]):
        active = executed[:, j]
        current_win = np.where(active, np.where(pnl[:, j] > 1e-12, current_win + 1, 0), current_win)
        current_loss = np.where(active, np.where(pnl[:, j] < -1e-12, current_loss + 1, 0), current_loss)
        max_win, max_loss = np.maximum(max_win, current_win), np.maximum(max_loss, current_loss)
    return {"return_pct": (after[:, -1] / initial - 1) * 100,
            "ending_balance": after[:, -1], "pnl": pnl, "pf": pf,
            "max_sampled_equity_dd_pct": sampled_dd * 100, "max_closed_dd_pct": closed_dd * 100,
            "wins": wins, "losses": loses, "trades": executed.sum(axis=1),
            "max_win_streak": max_win, "max_loss_streak": max_loss,
            "ruined": after[:, -1] <= 0}


def _finite(value):
    v = float(value)
    return v if math.isfinite(v) else None


def _distribution(values):
    a = np.asarray(values, dtype=float)
    a = a[~np.isnan(a)]
    if len(a) == 0:
        return {"p05": None, "p50": None, "p95": None, "undefined_paths": len(values)}
    # Inverse empirical CDF avoids interpolation between finite PF and infinity.
    a.sort()
    return {f"p{int(q * 100):02d}": _finite(a[max(0, math.ceil(q * len(a)) - 1)])
            for q in [.05, .5, .95]} | {"undefined_paths": int(np.isnan(values).sum()),
                                      "infinite_paths": int(np.isinf(values).sum())}


def _pack_paths(result, paths, seed, method, block_weeks=None):
    distributions = {k: _distribution(result[k]) for k in
                     ["return_pct", "pf", "max_sampled_equity_dd_pct", "max_closed_dd_pct",
                      "max_win_streak", "max_loss_streak", "trades"]}
    return {"status": "complete", "method": method, "paths": paths, "seed": seed,
            "block_calendar_weeks": block_weeks, "distributions": distributions,
            "probability_profit_pct": float(np.mean(result["return_pct"] > 0) * 100),
            "probability_ruin_pct": float(np.mean(result["ruined"]) * 100),
            "bootstrap_return_p05_positive": distributions["return_pct"]["p05"] is not None
            and distributions["return_pct"]["p05"] > 0,
            "bootstrap_pf_p05_above_1": distributions["pf"]["p05"] is not None
            and distributions["pf"]["p05"] > 1,
            "scope": "One joint weekly sequence, 1x current-cash compounding; all costs embedded in caller returns scale with notional. DD uses supplied path samples or closed-only fallback, not certified native equity."}


def summarize_trades(records, scheduled_week_ids=None, initial_balance=10000.0):
    rows, weeks, grid, explicit = _grid(records, scheduled_week_ids)
    if not grid:
        return {"status": "no_scheduled_weeks", "trades": 0}
    a = _arrays(grid)
    x = _evaluate(a, np.arange(len(grid)), initial_balance)
    n = int(x["trades"][0])
    wins = int(x["wins"][0])
    pnl = x["pnl"][0]
    return {"status": "complete", "scheduled_weeks": len(weeks), "trades": n,
            "valid_no_trade_weeks": len(weeks) - len(rows), "authoritative_week_calendar": explicit,
            "trades_with_intratrade_samples": sum(r["has_path"] for r in rows),
            "trades_closed_only": sum(not r["has_path"] for r in rows),
            "return_pct": float(x["return_pct"][0]), "ending_balance_usd": float(x["ending_balance"][0]),
            "net_profit_usd": float(pnl.sum()), "profit_factor": _finite(x["pf"][0]),
            "profit_factor_infinite_no_losses": bool(np.isinf(x["pf"][0])),
            "win_rate_pct": wins / n * 100 if n else None, "wins": wins,
            "losses": int(x["losses"][0]), "breakevens": n - wins - int(x["losses"][0]),
            "win_rate_wilson": wilson_interval(wins, n),
            "max_closed_dd_pct": float(x["max_closed_dd_pct"][0]),
            "max_sampled_equity_dd_pct": float(x["max_sampled_equity_dd_pct"][0]),
            "max_win_streak": int(x["max_win_streak"][0]), "max_loss_streak": int(x["max_loss_streak"][0]),
            "weekly_return_sharpe": _sharpe(a["return"], 52), "weekly_annualization": 52,
            "cost_bases": dict(Counter(r["cost_basis"] for r in rows)),
            "pnl_by_scheduled_week": [{"week_id": w, "pnl_usd": float(v), "traded": bool(t)}
                                      for w, v, t in zip(weeks, pnl, a["traded"])],
            "dd_scope": "Provided intratrade samples plus exact modeled close; unavailable interior paths are closed-only. Not native tick-equity DD."}


def daily_closed_balance_statistics(records, period_start_epoch, period_end_epoch,
                                    initial_balance=10000.0):
    """Full UTC calendar, including zero-exit days; net positions recognized at exit."""
    start, end = int(period_start_epoch), int(period_end_epoch)
    if start % 86400 or end % 86400 or end <= start:
        raise ValueError("Daily comparison requires UTC-midnight start/end-exclusive")
    rows, _, grid, _ = _grid(records, None)
    if any(r["entry_epoch"] < start or not start <= r["exit_epoch"] < end for r in rows):
        raise ValueError("Every supplied completed position must be inside the daily window")
    daily = np.zeros((end - start) // 86400)
    if grid:
        pnl = _evaluate(_arrays(grid), np.arange(len(grid)), initial_balance)["pnl"][0]
        for row, value in zip(rows, pnl):
            daily[(row["exit_epoch"] - start) // 86400] += value
    before = np.r_[initial_balance, initial_balance + np.cumsum(daily)[:-1]]
    returns = np.divide(daily, before, out=np.zeros_like(daily), where=before > 0)
    return {"calendar_days": len(daily), "annualization": 365,
            "daily_closed_balance_sharpe": _sharpe(returns, 365),
            "zero_exit_days": int(np.sum(daily == 0)),
            "net_profit_usd": float(daily.sum()),
            "scope": "Modeled net position P&L recognized on UTC exit date, all calendar days included; not floating equity or native every-deal cash timing."}


def _samples(records, scheduled_week_ids, missing_week_ids, paths, seed, method, block_weeks=5,
             removal_fraction=0.0, initial_balance=10000.0):
    if paths < 1 or int(paths) != paths or not 0 <= removal_fraction <= 1:
        raise ValueError("Invalid path count/removal fraction")
    paths = int(paths)
    rows, weeks, grid, explicit = _grid(records, scheduled_week_ids)
    if not grid or missing_week_ids:
        return {"status": "unavailable_incomplete_history", "paths": 0,
                "missing_week_ids": list(missing_week_ids), "reason": "Missing price weeks are not valid zero-return weeks."}
    if not explicit and method == "block_bootstrap":
        return {"status": "unavailable_calendar", "paths": 0,
                "reason": "Supply authoritative scheduled_week_ids for calendar-week block bootstrap."}
    if block_weeks < 1 or int(block_weeks) != block_weeks:
        raise ValueError("Block length must be a positive integer")
    a = _arrays(grid)
    rng = np.random.default_rng(seed)
    n, chunks = len(grid), []
    for first in range(0, paths, 200):
        size = min(200, paths - first)
        if method == "block_bootstrap":
            starts = rng.integers(n, size=(size, math.ceil(n / block_weeks)))
            idx = ((starts[:, :, None] + np.arange(block_weeks)) % n).reshape(size, -1)[:, :n]
        elif method == "trade_order_reshuffle":
            idx = np.argsort(rng.random((size, n)), axis=1)
        elif method == "trade_removal":
            idx = np.tile(np.arange(n), (size, 1))
        else:
            raise ValueError("Unknown resampling method")
        keep = rng.random((size, n)) >= removal_fraction if method == "trade_removal" else None
        chunks.append(_evaluate(a, idx, initial_balance, keep))
    result = {k: np.concatenate([c[k] for c in chunks]) for k in chunks[0] if k != "pnl"}
    packed = _pack_paths(result, paths, seed, method, block_weeks if method == "block_bootstrap" else None)
    packed["source_trades"] = len(rows)
    packed["scheduled_weeks"] = n
    if method == "trade_removal":
        packed["independent_per_trade_removal_probability"] = removal_fraction
        packed["note"] = "A missed trade removes its entire path and embedded costs; subsequent cash allocation is recomputed."
    return packed


def joint_bootstrap(records, scheduled_week_ids=None, *, missing_week_ids=(), paths=10000,
                    block_weeks=5, seed=DEFAULT_SEED, initial_balance=10000.0):
    return _samples(records, scheduled_week_ids, missing_week_ids, paths, seed, "block_bootstrap",
                    block_weeks=block_weeks, initial_balance=initial_balance)


def trade_order_reshuffle(records, scheduled_week_ids=None, *, paths=10000, seed=DEFAULT_SEED + 20,
                          initial_balance=10000.0):
    return _samples(records, scheduled_week_ids, (), paths, seed, "trade_order_reshuffle",
                    initial_balance=initial_balance)


def trade_removal(records, scheduled_week_ids=None, *, fraction=.1, paths=10000,
                  seed=DEFAULT_SEED + 30, initial_balance=10000.0):
    return _samples(records, scheduled_week_ids, (), paths, seed, "trade_removal",
                    removal_fraction=fraction, initial_balance=initial_balance)


def chronological_checks(records, scheduled_week_ids):
    rows, weeks, _, _ = _grid(records, scheduled_week_ids)
    if not weeks:
        return {"status": "insufficient_data"}
    folds = []
    for ids in np.array_split(np.asarray(weeks, dtype=object), 3):
        allowed = set(ids)
        subset = [r for r in records if str(r.get("week_id") or datetime.fromtimestamp(int(r["entry_epoch"]), NY).date().isoformat()) in allowed]
        folds.append(summarize_trades(subset, ids.tolist()))
    half = weeks[len(weeks) // 2:]
    allowed = set(half)
    recent = [r for r in records if str(r.get("week_id") or datetime.fromtimestamp(int(r["entry_epoch"]), NY).date().isoformat()) in allowed]
    recent_summary = summarize_trades(recent, half)
    return {"status": "complete", "method": "Three chronological scheduled-calendar-week groups; each starts fresh cash; no fitting.",
            "thirds": folds, "profitable_thirds": sum(f.get("net_profit_usd", 0) > 0 for f in folds),
            "recent_half": recent_summary,
            "recent_half_pf_above_1": (recent_summary.get("profit_factor") or 0) > 1}


def family_null(week_return_matrix, configuration_ids, chosen_id, *, paths=10000,
                block_weeks=5, seed=DEFAULT_SEED + 50, cost_matrix=None):
    """Joint centered-week block null. ALL columns share resampled row indices."""
    x = np.asarray(week_return_matrix, dtype=float)
    ids = list(configuration_ids)
    if x.ndim != 2 or x.shape[1] != len(ids) or len(set(ids)) != len(ids) or chosen_id not in ids:
        raise ValueError("Require a week-by-unique-configuration matrix and chosen ID")
    if x.shape[0] < 3 or not np.isfinite(x).all():
        return {"status": "unavailable_incomplete_matrix", "paths": 0,
                "reason": "No zero-imputation of missing configurations/weeks."}
    if paths < 1 or block_weeks < 1 or int(paths) != paths or int(block_weeks) != block_weeks:
        raise ValueError("Invalid null path/block count")
    paths, block_weeks = int(paths), int(block_weeks)
    costs = np.zeros_like(x) if cost_matrix is None else np.asarray(cost_matrix, dtype=float)
    if costs.shape != x.shape or not np.isfinite(costs).all():
        raise ValueError("Cost matrix must match every finite week/configuration")
    gross = x + costs
    centred = gross - gross.mean(axis=0)
    def scores(a):
        mean, sd = a.mean(axis=-2), a.std(axis=-2, ddof=1)
        return np.divide(mean, sd, out=np.zeros_like(mean), where=sd > 0) * math.sqrt(52)
    actual = scores(x)
    selected = ids.index(chosen_id)
    rng = np.random.default_rng(seed)
    maxima, chosen = [], []
    n = len(x)
    # Bound temporary allocation independently of the number of searched rules.
    batch = max(1, min(100, 2_000_000 // max(1, x.size)))
    for first in range(0, paths, batch):
        size = min(batch, paths - first)
        starts = rng.integers(n, size=(size, math.ceil(n / block_weeks)))
        idx = ((starts[:, :, None] + np.arange(block_weeks)) % n).reshape(size, -1)[:, :n]
        simulated = centred[idx] - costs[idx]
        sr = scores(simulated)
        maxima.extend(sr.max(axis=1).tolist())
        chosen.extend(sr[:, selected].tolist())
    maxima, chosen = np.asarray(maxima), np.asarray(chosen)
    return {"status": "complete", "paths": paths, "seed": seed, "block_calendar_weeks": block_weeks,
            "unique_configurations": len(ids), "chosen_id": chosen_id,
            "observed_chosen_weekly_sharpe": float(actual[selected]),
            "observed_best_weekly_sharpe": float(actual.max()),
            "family_max_p_value": float((1 + np.sum(maxima >= actual[selected])) / (paths + 1)),
            "fixed_rule_p_value": float((1 + np.sum(chosen >= actual[selected])) / (paths + 1)),
            "null_maximum_sharpe": _distribution(maxima), "weekly_annualization": 52,
            "method": "Center each gross column, jointly resample circular week blocks across ALL configurations, subtract corresponding unchanged-signed cost rows; plus-one p values.",
            "cost_scope": "Caller-supplied recorded friction remains a cost" if cost_matrix is not None
            else "Centered net-return null; gross/financing decomposition unavailable",
            "caveat": "Conditional empirical null for this registered family, not a guarantee against undisclosed prior searches or a synthetic tradable market."}


def neighborhood_summary(neighbor_metrics, required_profitable_share=.6):
    """Describe the caller's predeclared development neighbours; never selects a rule."""
    metrics = list(neighbor_metrics)
    values = [m.get("return_pct", m.get("net_return")) for m in metrics]
    valid = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    fraction = sum(v > 0 for v in valid) / len(metrics) if metrics else None
    return {"registered_neighbors": len(metrics), "available_neighbors": len(valid),
            "profitable_share": fraction, "required_profitable_share": required_profitable_share,
            "return_p25": float(np.quantile(valid, .25)) if valid else None,
            "plateau_gate": bool(metrics) and len(valid) == len(metrics) and fraction >= required_profitable_share,
            "scope": "Only supplied predeclared development neighbours; unavailable neighbours never count as profitable."}


def analyze_robustness(records, *, tested_configurations, scheduled_week_ids,
                       missing_week_ids=(), paths=10000, seed=DEFAULT_SEED,
                       trial_sharpe_std=None, initial_balance=10000.0,
                       period_start_epoch=None, period_end_epoch=None):
    """High-level final-candidate diagnostics; caller must freeze candidate BEFORE OOS."""
    if missing_week_ids:
        return {"status": "unavailable_incomplete_history", "missing_week_ids": list(missing_week_ids),
                "observed_closed_positions": len(records),
                "reason": "Missing historical prices are not substituted with zero-return weeks or complete-window metrics."}
    _, _, grid, _ = _grid(records, scheduled_week_ids)
    summary = summarize_trades(records, scheduled_week_ids, initial_balance)
    if (period_start_epoch is None) != (period_end_epoch is None):
        raise ValueError("Supply both UTC daily period boundaries or neither")
    if period_start_epoch is not None:
        summary["daily_closed_balance_statistics"] = daily_closed_balance_statistics(
            records, period_start_epoch, period_end_epoch, initial_balance)
    if not grid:
        return {"status": "unavailable_incomplete_history", "summary": summary,
                "missing_week_ids": list(missing_week_ids), "reason": "No bootstrap substitution for missing historical prices."}
    boots = {str(b): joint_bootstrap(records, scheduled_week_ids, paths=paths, block_weeks=b,
                                    seed=seed + b, initial_balance=initial_balance) for b in [1, 5, 10]}
    dsr = deflated_sharpe([r["return"] for r in grid], tested_configurations, trial_sharpe_std)
    chronology = chronological_checks(records, scheduled_week_ids)
    return {"status": "complete_offline_diagnostics", "allocation": "1x CURRENT cash; no stop-defined percent-risk claim",
            "summary": summary, "block_bootstrap": boots,
            "trade_order_reshuffle": trade_order_reshuffle(records, scheduled_week_ids, paths=paths,
                                                            seed=seed + 20, initial_balance=initial_balance),
            "trade_removal": {str(p): trade_removal(records, scheduled_week_ids, fraction=p, paths=paths,
                                                    seed=seed + int(p * 1000), initial_balance=initial_balance)
                              for p in [.1, .2]},
            "deflated_sharpe": dsr, "chronological_checks": chronology,
            "crypto_annualization": {"weekly": 52, "daily_if_separately_reported": 365},
            "cost_stress": {"status": "unavailable_without_measured_extra_costs", "gate": None,
                            "reason": "Unknown historical spread/slippage/financing must not be invented. Native recorded costs and assumed swap sensitivities are different evidence."},
            "prop_simulation": {"status": "unavailable_not_risk_calibrated", "gate": None,
                                "reason": "1x no-stop allocation is not a calibrated FTMO percent-risk policy; closed weekly outcomes cannot establish daily floating-equity phase pass probabilities."},
            "portfolio_overlap": {"status": "unavailable_without_independent_joint_portfolio_simulation", "gate": None},
            "promotion_complete": False,
            "limitations": ["OOS2024-10-17 to2026-10-17 was previously inspected: retrospective OOS, not untouched.",
                            "Empirical resampling is not a future success probability.",
                            "Native Model4 timing, liquidity, costs and true equity-path audit remain separate requirements."]}
