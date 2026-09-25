"""Greedy EA-combination selection for FTMO 2-Step, chosen on pre-2024-09 data only (research, 2026-09-24).

Candidates: every non-news EA/mode with an audited native 5y ledger in ../FTMO Combination Study 2026-09-19/prepared.json
(at most one mode per EA). News EAs are excluded (FTMO pre-news straddle clarification pending; fitted presets).
Objective (frozen before running): FTMO pass-both-phases frequency at 0.5% risk per trade, stressed costs,
conservative equity model, weekly bootstrap of the pre-2024-09-19 pool (1,500 paths per evaluation, common seed).
Forward selection: add the EA that raises the objective most; stop when the best addition improves it by < 1 point.
Then the chosen set is evaluated (5,000 paths) on the full, pre and post pools at several risks, and per-EA plus
combined native-ledger statistics are reported. Uses simulate.py for all FTMO accounting.
"""
from __future__ import annotations

import json
import random
import statistics
from collections import defaultdict
from datetime import datetime, timezone

import simulate as S

SELECT_PATHS = 1500
FINAL_PATHS = 5000
SELECT_RISK = 0.5
SEED = 20260927


def all_rows(stress):
    data = json.loads((S.STUDY / "prepared.json").read_text(encoding="utf-8-sig"))
    rows = {}
    for k, rr in data["rows"].items():
        if k.startswith("news-pulse-"):
            continue
        out = []
        for r in rr:
            g, c, s, x = S.costs(r, stress)
            out.append(dict(key=k, op=r["op"], cl=max(r["cl"], r["op"] + 1), R=(g + c + s - x) / r["unit_risk"]))
        rows[k] = out
    return rows


def objective(rows, keys, pool, paths, risk, seed):
    trades = [t for k in keys for t in rows[k]]
    weeks = S.pool_weeks(trades, *pool)
    S.PATHS = paths
    return S.simulate(weeks, risk, random.Random(seed), envelope=1.0)


def stats(trades, start, end, risk_pct=0.5):
    """Native-ledger overlay at fixed risk of initial $100k (not compounded): closed-balance figures."""
    sel = sorted((t for t in trades if (start is None or t["op"] >= start) and t["op"] < end), key=lambda t: t["cl"])
    if not sel:
        return None
    unit = S.CAPITAL * risk_pct / 100
    bal = peak = S.CAPITAL
    dd = 0.0
    gp = gl = 0.0
    w = l = bw = bl = wins = 0
    years = defaultdict(float)
    for t in sel:
        pnl = t["R"] * unit
        bal += pnl
        peak = max(peak, bal)
        dd = max(dd, 100 * (peak - bal) / peak)
        years[datetime.fromtimestamp(t["cl"], timezone.utc).year] += pnl
        if pnl > 0:
            gp += pnl; wins += 1; w += 1; l = 0
        else:
            gl -= pnl; l += 1; w = 0
        bw, bl = max(bw, w), max(bl, l)
    n = len(sel)
    span_years = (sel[-1]["cl"] - sel[0]["op"]) / (365.25 * 86400)
    return dict(trades=n, trades_per_month=round(n / max(span_years, 1e-9) / 12, 1), win_pct=round(100 * wins / n, 1),
                pf=round(gp / gl, 2) if gl else None, avg_R=round(statistics.fmean(t["R"] for t in sel), 3),
                return_pct=round(100 * (bal / S.CAPITAL - 1), 1), closed_dd_pct=round(dd, 1),
                best_win_streak=bw, worst_loss_streak=bl,
                yearly_pct={y: round(100 * v / S.CAPITAL, 1) for y, v in sorted(years.items())})


def main():
    rows = all_rows(stress=True)
    pre = (None, S.SPLIT)
    candidates = sorted(rows)
    chosen, history = [], []
    best_score = 0.0
    while True:
        trials = []
        used_slugs = {k.split("/")[0] for k in chosen}
        for k in candidates:
            if k in chosen or k.split("/")[0] in used_slugs:
                continue
            r = objective(rows, chosen + [k], pre, SELECT_PATHS, SELECT_RISK, SEED)
            trials.append((r["pass_both_pct"], -r["breach_phase1_pct"], k, r))
        if not trials:
            break
        trials.sort(reverse=True)
        score, _, k, r = trials[0]
        history.append(dict(step=len(chosen) + 1, added=k, pass_both_pct=score, top5=[(t[2], t[0]) for t in trials[:5]]))
        print(f"step {len(chosen) + 1}: best add {k} -> pass both {score}% (prev {best_score}%)  runners-up {[(t[2], t[0]) for t in trials[1:4]]}", flush=True)
        if score < best_score + 1.0:
            history[-1]["stopped"] = "improvement < 1 point; not added"
            break
        chosen.append(k)
        best_score = score
    print("CHOSEN:", chosen, flush=True)

    out = dict(seed=SEED, objective=dict(metric="pass_both_pct", risk_pct=SELECT_RISK, costs="stressed", equity="conservative",
                                         pool="pre-2024-09-19", paths=SELECT_PATHS), selection_history=history, chosen=chosen,
               per_ea={}, combined={}, ftmo=[])
    ref_rows = all_rows(stress=False)
    for label, rs in (("stressed", rows), ("reference", ref_rows)):
        for k in chosen:
            out["per_ea"].setdefault(k, {})[label] = {p: stats(rs[k], *rng) for p, rng in S.POOLS.items()}
        comb = [t for k in chosen for t in rs[k]]
        out["combined"][label] = {p: stats(comb, *rng) for p, rng in S.POOLS.items()}
    for label, rs in (("stressed", rows), ("reference", ref_rows)):
        for pool_name, pool in S.POOLS.items():
            for risk in (0.25, 0.5, 0.75, 1.0):
                r = objective(rs, chosen, pool, FINAL_PATHS, risk, SEED + 1)
                out["ftmo"].append(dict(costs=label, pool=pool_name, risk_pct=risk, **r))
                print(f"FTMO {label:<9} {pool_name:<31} {risk:>4}%  P1 {r['pass_phase1_pct']}%  both {r['pass_both_pct']}%  "
                      f"med days {r['median_days_both']}  <=90d {r['within_90d_pct']}%  <=180d {r['within_180d_pct']}%  "
                      f"surv {r['funded_year_survival_pct_of_funded']}%  E ${r['expected_payout_per_attempt_usd']:,}", flush=True)
    (S.ROOT / "SELECTION_RESULTS.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
