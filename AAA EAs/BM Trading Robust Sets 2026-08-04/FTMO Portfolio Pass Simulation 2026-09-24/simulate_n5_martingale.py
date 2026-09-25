"""FTMO 2-Step simulation: Nasdaq 5M Candle Momentum with loss-doubling (martingale) sizing. Research only, 2026-09-24.

User idea: after every losing trade double the risk; after a win reset to the base risk.
Reuses simulate_n5_adaptive.py (same ledger, FTMO rules, bootstrap, reporting). Sizing:
risk = current balance x base% x 2**(consecutive losses), optionally capped. No adaptive governor.
The streak resets at every new FTMO account (Phase 1, Phase 2, funded).
"""
from __future__ import annotations

import json
import random
import statistics

import simulate as S
import simulate_n5_adaptive as A

SCENARIOS = {
    "M1. Martingale from 1%": dict(risk=1.0, cap=None),
    "M2. Martingale from 0.5%": dict(risk=0.5, cap=None),
    "M3. Martingale from 0.25%": dict(risk=0.25, cap=None),
    "M4. Martingale from 0.5%, capped at 4%": dict(risk=0.5, cap=4.0),
    "Ref. 1% + adaptive governor": None,
    "Ref. flat 1%": None,
}


def mart_governor_factory(sc):
    def gov(bal, peak, streak, day_pl, reference):
        m = 2.0 ** streak
        if sc["cap"] is not None:
            m = min(m, sc["cap"] / sc["risk"])
        return m
    return gov


def main():
    rng = random.Random(20260926)
    out = dict(seed=20260926, paths=A.PATHS, results=[])
    for costs_label, stress in (("reference costs", False), ("stressed costs", True)):
        trades = A.load(stress)
        for pool, (a, b) in A.POOLS.items():
            weeks = S.pool_weeks(trades, a, b)
            for name, sc in SCENARIOS.items():
                if sc is None:
                    ref = {"Ref. 1% + adaptive governor": "A. 1% + adaptive governor", "Ref. flat 1%": "C. Flat 1% (no governor)"}[name]
                    A.governor = ORIGINAL_GOVERNOR
                    r = A.simulate(weeks, A.SCENARIOS[ref], rng, 1.0)
                else:
                    A.governor = mart_governor_factory(sc)
                    r = A.simulate(weeks, dict(risk=sc["risk"], base=1.0, adaptive=True), rng, 1.0)
                out["results"].append(dict(scenario=name, costs=costs_label, pool=pool, equity_model="conservative", **r))
                print(f"{costs_label:<15} {pool:<22} {name:<40} P1 {r['pass_phase1_pct']:>5}%  P2|P1 {r['pass_phase2_given_phase1_pct']}%  both {r['pass_both_pct']:>5}%  "
                      f"breachP1 {r['breach_phase1_pct']}%  days P1 {r['phase1_days_p25_median_p75']} P2 {r['phase2_days_p25_median_p75']} both {r['both_days_p25_median_p75']}  "
                      f"<=30d {r['funded_within_30d_pct']}% <=90d {r['within_90d_pct']}%  surv {r['funded_year_survival_pct']}%  E ${r['expected_payout_per_attempt_usd']:,}  avg mult {r['average_risk_multiplier']}", flush=True)
                (S.ROOT / "RESULTS_N5_MARTINGALE.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


ORIGINAL_GOVERNOR = A.governor
if __name__ == "__main__":
    main()
