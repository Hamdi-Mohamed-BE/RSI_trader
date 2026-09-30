"""Offline suggestion search for the public prop simulator (writes data/prop-sim/suggestions.json).

For every programme and each objective (expected value, pass rate, speed):
  1. candidates = EAs compatible with the programme (5-year cached evidence);
  2. SELECT on the development window (first 80% of the common 5-year window): greedy forward selection of EAs at
     0.5% risk, then a grid over risk per trade and guard presets for the chosen set;
  3. REPORT the frozen choice on the untouched final 20% (holdout) next to the development numbers.
The bootstrap on each window is the Monte Carlo. Selection on the same data it is judged on would overstate pass
rates, which is why the holdout column is published alongside.

Usage:  uv run python tools/precompute_prop_suggestions.py [programme_id ...]
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("EA_STORE_DISABLE_MT5", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from app.prop_sim.engine import SimConfig, sample_indices, simulate, summarise  # noqa: E402
from app.prop_sim.ledger import Features, Guards, Selection, available_eas, build_features, load_ea  # noqa: E402
from app.prop_sim.metrics import combo_stats, common_window  # noqa: E402
from app.prop_sim.rules import Programme, compatibility, programmes  # noqa: E402
from app.prop_sim.service import SUGGESTIONS  # noqa: E402

PERIOD = "5y"
DEV_SHARE = 0.8
SEARCH_PATHS = 250
FINAL_PATHS = 2000
HORIZON = 365
MAX_EAS = 10
MIN_TRADES_PER_MONTH = 5.0
RISK_GRID = (0.25, 0.375, 0.5, 0.75, 1.0)
GUARD_PRESETS = {"none": Guards(), "daily-2": Guards(daily_stop_pct=2.0),
                 "daily-2-open-3": Guards(daily_stop_pct=2.0, max_open_risk_pct=3.0)}
OBJECTIVES = {"expected_value": "Best expected value", "pass_rate": "Highest pass rate", "speed": "Fastest pass"}


def slice_features(f: Features, a: int, b: int) -> Features:
    start = f.start + timedelta(days=a)
    end = f.start + timedelta(days=b - 1)
    keep = [r for r in f.accepted if start.isoformat() <= r["closed"][:10] <= end.isoformat()]
    return Features(start=start, days=b - a, pnl=f.pnl[a:b], low_closed=f.low_closed[a:b],
                    low_envelope=f.low_envelope[a:b], opened=f.opened[a:b],
                    per_ea_pnl={k: v[a:b] for k, v in f.per_ea_pnl.items()}, accepted=keep, skipped=f.skipped)


class Evaluator:
    def __init__(self, programme: Programme, ledgers: dict[str, Any], start, end, size: int, fee: float | None):
        self.p, self.ledgers, self.start, self.end, self.size, self.fee = programme, ledgers, start, end, size, fee
        self.days = (end - start).days + 1
        self.split = int(self.days * DEV_SHARE)
        self.void = programme.hold_time_min_seconds if programme.hold_time_applies in ("funded", "both") else None

    def features(self, picks: list[tuple[str, float]], guards: Guards) -> tuple[Features, Features]:
        sel = [Selection(s, r) for s, r in picks]
        ch = build_features(self.ledgers, sel, self.size, guards, self.start, self.end)
        fu = build_features(self.ledgers, sel, self.size, guards, self.start, self.end, self.void) if self.void else ch
        return ch, fu

    def evaluate(self, picks, guards, window: str, paths: int, seed: int = 1) -> dict[str, Any]:
        ch, fu = self.features(picks, guards)
        a, b = (0, self.split) if window == "dev" else (self.split, self.days)
        ch_w, fu_w = slice_features(ch, a, b), (slice_features(fu, a, b) if fu is not ch else None)
        fu_w = fu_w or ch_w
        cfg = SimConfig(account_size=self.size, fee=self.fee, horizon_days=HORIZON, paths=paths, seed=seed)
        idx = sample_indices(ch_w.days, cfg)
        cons = summarise(simulate(self.p, ch_w, fu_w, cfg, idx, "envelope"), cfg, HORIZON)
        opt = summarise(simulate(self.p, ch_w, fu_w, cfg, idx, "closed"), cfg, HORIZON)
        stats = combo_stats(ch_w, "pct_initial")
        return {"conservative": cons, "optimistic": opt, "stats": stats}


def score(result: dict[str, Any], objective: str) -> float:
    r, stats = result["conservative"], result["stats"]
    if stats["trades_per_month"] < MIN_TRADES_PER_MONTH:
        return -1e18
    if objective == "expected_value":
        ev = r["payout"]["expected_value_usd"]
        return ev if ev is not None else r["payout"]["expected_payout_usd"]
    if objective == "pass_rate":
        return r["pass_all_rate"] - 1e-4 * ((r["days_to_funded"] or {}).get("median") or 999)
    days = (r["days_to_funded"] or {}).get("median")
    return -(days or 1e6) if r["pass_all_rate"] >= 0.5 else -1e6 - (1 - r["pass_all_rate"]) * 1e5


def compact(result: dict[str, Any]) -> dict[str, Any]:
    c, o, s = result["conservative"], result["optimistic"], result["stats"]
    return {
        "pass_all": [c["pass_all_rate"], o["pass_all_rate"]],
        "pass_phase1": [c["phases"][0]["pass_rate"], o["phases"][0]["pass_rate"]] if c["phases"] else None,
        "breach": [c["breaches"]["daily_loss"]["rate"] + c["breaches"]["max_loss"]["rate"],
                   o["breaches"]["daily_loss"]["rate"] + o["breaches"]["max_loss"]["rate"]],
        "median_days_to_funded": (c["days_to_funded"] or {}).get("median"),
        "expected_payout_usd": c["payout"]["expected_payout_usd"],
        "expected_value_usd": c["payout"]["expected_value_usd"],
        "trades_per_month": s["trades_per_month"], "profit_factor": s["profit_factor"],
        "win_rate_pct": s["win_rate_pct"], "sharpe_annualized": s["sharpe_annualized"],
        "max_balance_dd_pct": s["max_balance_dd_pct"], "window": s["window"],
    }


def search(programme: Programme) -> dict[str, Any] | None:
    profiles = [p for p in available_eas(PERIOD) if compatibility(programme, p).selectable]
    if not profiles:
        return None
    ledgers = {p.slug: load_ea(p.slug, PERIOD)[1] for p in profiles}
    start, end = common_window([(p.start, p.end) for p in profiles])
    size = 10000 if 10000 in programme.account_sizes else min(programme.account_sizes, key=lambda s: abs(s - 10000))
    ev = Evaluator(programme, ledgers, start, end, size, programme.fee_for(size))
    out: dict[str, Any] = {"programme": programme.label, "account_size": size, "fee": ev.fee,
                           "fee_currency": programme.fee_currency, "objectives": {}}
    for objective, label in OBJECTIVES.items():
        t0 = time.perf_counter()
        chosen: list[str] = []
        best = -1e18
        remaining = [p.slug for p in profiles]
        while remaining and len(chosen) < MAX_EAS:
            trial = [(s, score(ev.evaluate([(x, 0.5) for x in (*chosen, s)], Guards(), "dev", SEARCH_PATHS), objective))
                     for s in remaining]
            slug, value = max(trial, key=lambda item: item[1])
            if value <= best + 1e-9:
                break
            chosen.append(slug)
            remaining.remove(slug)
            best = value
        if not chosen:
            continue
        grid = []
        for risk in RISK_GRID:
            for gname, guards in GUARD_PRESETS.items():
                picks = [(s, risk) for s in chosen]
                grid.append((score(ev.evaluate(picks, guards, "dev", SEARCH_PATHS), objective), risk, gname))
        _, risk, gname = max(grid)
        picks = [(s, risk) for s in chosen]
        dev = ev.evaluate(picks, GUARD_PRESETS[gname], "dev", FINAL_PATHS, seed=2)
        hold = ev.evaluate(picks, GUARD_PRESETS[gname], "holdout", FINAL_PATHS, seed=3)
        dc, hc = compact(dev), compact(hold)
        g = GUARD_PRESETS[gname]
        out["objectives"][objective] = {
            "objective": objective, "objective_label": label, "account_size": size, "sizing": "pct_initial",
            "eas": [{"slug": s, "risk_pct": risk} for s in chosen],
            "guards": {"daily_stop_pct": g.daily_stop_pct, "profit_lock_pct": g.profit_lock_pct,
                       "max_open_risk_pct": g.max_open_risk_pct, "max_entries_per_day": g.max_entries_per_day},
            "development": dc, "holdout": hc,
            "summary": (f"{len(chosen)} EAs at {risk}% risk, guard '{gname}'. Selected on {dc['window']['from']} to "
                        f"{dc['window']['to']} (pass all {dc['pass_all'][0]:.0%}–{dc['pass_all'][1]:.0%}); combination-"
                        f"selection holdout {hc['window']['from']} to {hc['window']['to']}: pass all "
                        f"{hc['pass_all'][0]:.0%}–{hc['pass_all'][1]:.0%}."),
            "search_seconds": round(time.perf_counter() - t0, 1),
        }
        print(f"  {objective}: {out['objectives'][objective]['summary']} ({time.perf_counter() - t0:.0f}s)", flush=True)
    return out


def main(argv: list[str]) -> None:
    progs = programmes()
    targets = argv or list(progs)
    existing = json.loads(SUGGESTIONS.read_text(encoding="utf-8")) if SUGGESTIONS.is_file() else {"programmes": {}}
    for pid in targets:
        print(f"{pid} …", flush=True)
        result = search(progs[pid])
        if result:
            existing["programmes"][pid] = result
        existing.update({
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "period": PERIOD,
            "method": (f"Greedy forward selection at 0.5% risk, then risk {RISK_GRID} x guards {list(GUARD_PRESETS)} on "
                       f"the first {DEV_SHARE:.0%} of the common {PERIOD} window; {FINAL_PATHS} calendar-block bootstrap "
                       f"paths, {HORIZON}-day horizon; frozen choice re-run on the untouched final "
                       f"{1 - DEV_SHARE:.0%}. Conservative (open risk at stop) – optimistic (closed trades) ranges. The holdout is "
                       "untouched only for choosing the combination: the EAs' own settings were developed on this "
                       "history, so neither window is a true out-of-sample test."),
        })
        SUGGESTIONS.parent.mkdir(parents=True, exist_ok=True)
        tmp = SUGGESTIONS.with_suffix(".tmp")
        tmp.write_text(json.dumps(existing, indent=1, allow_nan=False), encoding="utf-8")
        tmp.replace(SUGGESTIONS)


if __name__ == "__main__":
    np.seterr(all="ignore")
    main(sys.argv[1:])
