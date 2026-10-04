"""Vectorised prop-challenge Monte Carlo.

Paths are sequences of *historical days* (whole calendar blocks, so every selected EA moves together and their
correlation is preserved). All paths advance one day at a time through the programme's state machine:

    phases (target, minimum trading / profitable days, time limit, best-day consistency)
    -> handover delay -> funded account (payout cadence, split, fee refund, balance reset after each payout)

Loss rules are checked every day before that day's P/L is booked, using the day's worst intraday point:
    * ``closed``   worst closed-trade balance of the day (optimistic: ignores floating drawdown of open trades)
    * ``envelope`` every open position assumed at its full stop at the worst moment (conservative)
Both are scenario assumptions, not guaranteed bounds on the unrecorded intraday
answer. For no-stop hourly experiments, the reserve is a historical loss reference
only; actual floating losses can exceed it without bound.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

from .ledger import Features
from .rules import Programme

EPS = 1e-9
Sizing = Literal["pct_initial", "pct_balance"]
Method = Literal["bootstrap", "rolling"]


@dataclass(frozen=True)
class SimConfig:
    account_size: float
    fee: float | None
    sizing: Sizing = "pct_initial"
    horizon_days: int = 365
    paths: int = 2000
    method: Method = "bootstrap"
    block_days: int = 28
    seed: int = 20260929


def sample_indices(n_days: int, cfg: SimConfig) -> np.ndarray:
    """(paths, horizon) matrix of historical day indices."""
    horizon = cfg.horizon_days
    if cfg.method == "rolling":
        last = n_days - horizon
        starts = np.arange(0, last + 1, 7) if last >= 0 else np.arange(0, n_days, 7)
        return (starts[:, None] + np.arange(horizon)[None, :]) % n_days
    rng = np.random.default_rng(cfg.seed)
    block = max(1, min(cfg.block_days, n_days))
    n_blocks = -(-horizon // block)
    starts = rng.integers(0, n_days - block + 1, size=(cfg.paths, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(cfg.paths, n_blocks * block)
    return idx[:, :horizon]


@dataclass
class PathOutcomes:
    n_phases: int
    stage: np.ndarray
    alive: np.ndarray
    pass_day: np.ndarray  # (paths, n_phases), -1 = not passed
    funded_day: np.ndarray
    breach_cause: np.ndarray  # 0 none, 1 daily loss, 2 max loss, 3 time limit
    breach_stage: np.ndarray
    payouts: np.ndarray
    payout_usd: np.ndarray
    refunded: np.ndarray
    first_payout_day: np.ndarray


def simulate(programme: Programme, challenge: Features, funded: Features, cfg: SimConfig, idx: np.ndarray,
             equity: Literal["closed", "envelope"]) -> PathOutcomes:
    paths, horizon = idx.shape
    phases = programme.phases
    n_ph = len(phases)
    targets = np.array([p.target_pct / 100 for p in phases] + [np.inf])
    min_days = np.array([p.min_trading_days for p in phases] + [0])
    min_prof = np.array([p.min_profitable_days for p in phases] + [0])
    prof_thr = np.array([p.profitable_day_pct / 100 for p in phases] + [0.0])
    limits = np.array([p.time_limit_days or 0 for p in phases] + [0])
    handover = list(programme.handover_days) + [0] * (n_ph + 1)
    daily = programme.daily_loss_pct / 100 if programme.daily_loss_pct is not None else None
    max_loss = programme.max_loss_pct / 100
    cons = programme.consistency_best_day_pct / 100 if programme.consistency_best_day_pct else None
    cons_challenge = cons is not None and programme.consistency_applies in ("challenge", "both")
    cons_funded = cons is not None and programme.consistency_applies in ("funded", "both")
    payout = programme.payout
    fee = cfg.fee or 0.0

    ch_low = challenge.low_envelope if equity == "envelope" else challenge.low_closed
    fu_low = funded.low_envelope if equity == "envelope" else funded.low_closed
    same = funded is challenge

    stage = np.zeros(paths, dtype=np.int64)
    alive = np.ones(paths, dtype=bool)
    waiting = np.zeros(paths, dtype=np.int64)
    bal = np.ones(paths)
    hwm = np.ones(paths)
    in_phase = np.zeros(paths, dtype=np.int64)
    tdays = np.zeros(paths, dtype=np.int64)
    pdays = np.zeros(paths, dtype=np.int64)
    best = np.zeros(paths)
    pos_sum = np.zeros(paths)
    pass_day = np.full((paths, max(n_ph, 1)), -1, dtype=np.int64)
    funded_day = np.full(paths, -1 if n_ph else 0, dtype=np.int64)
    funded_age = np.zeros(paths, dtype=np.int64)
    next_payout = np.full(paths, payout.first_after_days, dtype=np.int64)
    payouts = np.zeros(paths, dtype=np.int64)
    payout_usd = np.zeros(paths)
    refunded = np.zeros(paths, dtype=bool)
    first_payout = np.full(paths, -1, dtype=np.int64)
    cause = np.zeros(paths, dtype=np.int64)
    breach_stage = np.full(paths, -1, dtype=np.int64)

    for t in range(horizon):
        d = idx[:, t]
        waiting_now = alive & (waiting > 0)
        waiting[waiting_now] -= 1
        act = alive & (waiting == 0)
        if not act.any():
            if not alive.any():
                break
            continue
        is_funded = stage >= n_ph
        if same:
            pnl, low, opened = challenge.pnl[d], ch_low[d], challenge.opened[d]
        else:
            pnl = np.where(is_funded, funded.pnl[d], challenge.pnl[d])
            low = np.where(is_funded, fu_low[d], ch_low[d])
            opened = np.where(is_funded, funded.opened[d], challenge.opened[d])
        if cfg.sizing == "pct_balance":
            pnl, low = pnl * bal, low * bal

        breach_daily = act & (low <= -daily + EPS) if daily is not None else np.zeros(paths, dtype=bool)
        if programme.max_loss_type == "static":
            floor = np.full(paths, 1.0 - max_loss)
        elif programme.max_loss_type == "eod_trailing":
            floor = hwm - max_loss
        else:  # eod_trailing_lock_initial: trails the end-of-day high but never above the initial balance
            floor = np.minimum(hwm - max_loss, 1.0)
        breach_max = act & (bal + low <= floor + EPS)
        breach = breach_daily | breach_max
        if breach.any():
            cause[breach] = np.where(breach_daily[breach], 1, 2)
            breach_stage[breach] = stage[breach]
            alive[breach] = False

        ok = act & ~breach
        bal[ok] += pnl[ok]
        tdays[ok] += (opened[ok] > 0)
        stage_c = np.minimum(stage, n_ph)
        pdays[ok] += (pnl[ok] >= prof_thr[stage_c[ok]] - EPS) & (pnl[ok] > 0)
        best[ok] = np.maximum(best[ok], pnl[ok])
        pos_sum[ok] += np.maximum(pnl[ok], 0.0)
        hwm[ok] = np.maximum(hwm[ok], bal[ok])
        in_phase[ok] += 1

        # ---- challenge phases -------------------------------------------------------------------------------
        if n_ph:
            ch = ok & (stage < n_ph)
            consistent = (best <= cons * pos_sum + EPS) if cons_challenge else np.ones(paths, dtype=bool)
            reached = (ch & (bal - 1.0 >= targets[stage_c] - EPS) & (tdays >= min_days[stage_c])
                       & (pdays >= min_prof[stage_c]) & consistent)
            if reached.any():
                rows = np.nonzero(reached)[0]
                pass_day[rows, stage[rows]] = t
                stage[rows] += 1
                waiting[rows] = [handover[s - 1] for s in stage[rows]]
                bal[rows], hwm[rows] = 1.0, 1.0
                in_phase[rows] = tdays[rows] = pdays[rows] = 0
                best[rows] = pos_sum[rows] = 0.0
                newly_funded = rows[stage[rows] == n_ph]
                # The waiting counter is decremented at the start of each following day; the account trades on
                # the day it reaches zero (or the next day when there is no handover delay).
                funded_day[newly_funded] = t + np.maximum(waiting[newly_funded], 1)
            expired = ch & ~reached & (limits[stage_c] > 0) & (in_phase >= limits[stage_c])
            if expired.any():
                cause[expired], breach_stage[expired] = 3, stage[expired]
                alive[expired] = False

        # ---- funded account ---------------------------------------------------------------------------------
        fa = ok & (stage >= n_ph) & (funded_day <= t)
        if fa.any():
            funded_age[fa] += 1
            due = fa & (funded_age >= next_payout)
            profit_usd = (bal - 1.0) * cfg.account_size
            consistent = (best <= cons * pos_sum + EPS) if cons_funded else np.ones(paths, dtype=bool)
            pay = due & (profit_usd >= payout.min_usd) & consistent
            if pay.any():
                payout_usd[pay] += payout.split_pct / 100 * profit_usd[pay]
                payouts[pay] += 1
                first_payout[pay & (first_payout < 0)] = t
                if payout.fee_refund:
                    refunded[pay] = True
                bal[pay], hwm[pay] = 1.0, 1.0
                best[pay] = pos_sum[pay] = 0.0
                next_payout[pay] = funded_age[pay] + payout.every_days
            retry = due & ~pay
            next_payout[retry] = funded_age[retry] + 1

    del fee  # fee enters the summary, not the path state
    return PathOutcomes(n_ph, stage, alive, pass_day, funded_day, cause, breach_stage, payouts, payout_usd,
                        refunded, first_payout)


def _q(values: np.ndarray) -> dict[str, float] | None:
    if values.size == 0:
        return None
    p25, p50, p75 = np.percentile(values, [25, 50, 75])
    return {"p25": float(p25), "median": float(p50), "p75": float(p75), "mean": float(values.mean())}


def summarise(out: PathOutcomes, cfg: SimConfig, horizon: int) -> dict[str, Any]:
    n = out.stage.size
    n_ph = out.n_phases
    funded = (out.stage >= n_ph) & ((out.funded_day >= 0) & (out.funded_day < horizon))
    res: dict[str, Any] = {"paths": int(n)}
    phase_rates = []
    for k in range(n_ph):
        passed = out.pass_day[:, k] >= 0
        phase_rates.append({"phase": k + 1, "pass_rate": float(passed.mean()),
                            "days_to_pass": _q(out.pass_day[passed, k].astype(float) + 1)})
    res["phases"] = phase_rates
    res["pass_all_rate"] = float(funded.mean()) if n_ph else 1.0
    res["phase2_given_phase1"] = (float(((out.pass_day[:, 1] >= 0).sum()) / max(1, (out.pass_day[:, 0] >= 0).sum()))
                                  if n_ph >= 2 else None)
    res["days_to_funded"] = _q(out.funded_day[funded].astype(float)) if n_ph else None
    breaches = {}
    for code, name in ((1, "daily_loss"), (2, "max_loss"), (3, "time_limit")):
        mask = out.breach_cause == code
        breaches[name] = {"rate": float(mask.mean()),
                          "challenge": float((mask & (out.breach_stage < n_ph)).mean()),
                          "funded": float((mask & (out.breach_stage >= n_ph)).mean())}
    res["breaches"] = breaches
    res["unresolved_rate"] = float((out.alive & (out.stage < n_ph)).mean()) if n_ph else 0.0
    res["funded_alive_at_end"] = float((out.alive & (out.stage >= n_ph)).mean())
    fee = cfg.fee
    refund = out.refunded * (fee or 0.0)
    value = out.payout_usd + refund
    res["payout"] = {
        "probability_any_by": {str(h): float(((out.first_payout_day >= 0) & (out.first_payout_day < h)).mean())
                               for h in (90, 180, 365) if h <= horizon},
        "expected_payouts": float(out.payouts.mean()),
        "expected_payout_usd": float(out.payout_usd.mean()),
        "payout_usd_p5_p50_p95": [float(v) for v in np.percentile(out.payout_usd, [5, 50, 95])],
        "expected_value_usd": (float(value.mean() - fee) if fee is not None else None),
        "fee": fee,
    }
    return res


def fan_chart(pnl: np.ndarray, idx: np.ndarray, sizing: Sizing, points: int = 60) -> dict[str, Any]:
    """Percentiles of the unconstrained cumulative return (no prop rules) across the sampled paths."""
    daily = pnl[idx]
    growth = np.cumprod(1 + daily, axis=1) - 1 if sizing == "pct_balance" else np.cumsum(daily, axis=1)
    cols = np.unique(np.linspace(0, idx.shape[1] - 1, min(points, idx.shape[1])).astype(int))
    pct = np.percentile(growth[:, cols], [5, 25, 50, 75, 95], axis=0) * 100
    return {"day": (cols + 1).tolist(), "p5": pct[0].round(3).tolist(), "p25": pct[1].round(3).tolist(),
            "p50": pct[2].round(3).tolist(), "p75": pct[3].round(3).tolist(), "p95": pct[4].round(3).tolist()}
