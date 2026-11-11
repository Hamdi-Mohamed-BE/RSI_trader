"""COPY of Merge 1Step 60d Search 2026-11-10/search.py (2026-11-11, see PLAN.md): only FORCED changed (4 must-have EAs); dev caches copied (same engine, same keys).
Original docstring follows.
Owner 2026-11-10: merge Core 9 with P4 (+ today's new EAs), and find the best profile for FTMO 1-Step passed within 2 months (60 days).
Frozen engines (Prop Portfolio Selection 2026-11-03: prop_select / nobuffer / f1_profile, $100k, 2021-10-07 -> 2026-10-06 streams), no new tester runs.

Pool (13 EAs, one Nasdaq 5M): Core 9 members from Merged E10 FTMO17 2026-11-05/INPUTS-C9.json without its Nasdaq (old skip-the-day stream) +
Portfolio P7 2026-11-10/INPUTS-P7.json (Nasdaq 5M REPLACE DI OFF = deployed, Vault Break, Overnight Bias ORB, Gold Band Wave, ORB VP, EMA3, RSI VWAP).

Models: GUARD = the built ftmo 1_step guard (f1_profile.Profile); NOGUARD = FTMO 1-Step firm rules only (p7.py f1u).
Rule (declared before any search result, PLAN in this docstring):
  objective = share of weekday starts that PASS WITHIN 60 DAYS, on DEVELOPMENT starts only (2021-10-07 -> 2023-10-06);
  feasibility = breach <= 5% in development (GUARD and NOGUARD alike);
  greedy forward selection from the empty set over the 13 EAs at each risk 0.5 / 0.75 / 1.0 / 1.25 %, adding the EA that raises dev pass_60 most, stop when
  nothing improves it by >= 1 point; then backward: drop any member whose removal does not lower dev pass_60.
  ADDENDUM 1 (2026-11-10, before any non-zero result was seen): forward selection from the empty set is degenerate (every single EA scored 0 at 0.5%, so the first
  pick was a tie broken by order and the walk would stop at one EA). Replaced by BACKWARD elimination from all 13: drop the EA whose removal raises dev pass_60 most
  (ties: higher dev pass_90), stop when no removal raises pass_60 by >= 0.5 point; then one add-back pass over the removed EAs (keep an add that raises pass_60 by
  >= 0.5 point). Breach <= 5% as before. The voided forward logs are in void-addendum1/.
  Final pick = the best VALIDATION pass_60 (2023-10-06 -> 2024-10-06) among the per-risk dev winners with val breach <= 5%. OOS (2024-10 -> 2026-10, previously viewed by
  the portfolios, so retrospective) and MC 2,000 paths are reported once, for the pick and the reference portfolios (Core 9, P4, Core 9 + P4 merge, all 13).
Run from AAA EAs/EA store: uv run --with pandas --with numpy python "<this>" search GUARD | search NOGUARD | final"""
import importlib.util, json, random, sys, time
from concurrent.futures import ProcessPoolExecutor
from datetime import date, timedelta
from pathlib import Path

H = Path(__file__).resolve().parent; B = H.parent
SEL = B / 'Prop Portfolio Selection 2026-11-03'
spec = importlib.util.spec_from_file_location('f1_profile', SEL / 'f1_profile.py'); F1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(F1)
S, C, O, N = F1.S, F1.C, F1.O, F1.N
NAS = 'nasdaq-5m-candle-momentum'
RISKS = (0.005, 0.0075, 0.01, 0.0125)
REFS = {'Core9': ['usdjpy-london-open-momentum', '3-way-gold#930930101', 'sell-nasdaq-15min', 'xau-rsi-vwap', 'ema3', 'xau-squeeze-momentum-standard', 'orb-volume-profile-volume-confirmed', 'us100-selective-orb-v3', NAS],
        'P4': ['overnight-bias-orb', NAS, 'ema3', 'gold-band-wave']}
REFS['Core9+P4'] = sorted(set(REFS['Core9']) | set(REFS['P4']))


def pool():
    f = H / 'INPUTS-POOL.json'
    if f.exists(): return json.loads(f.read_text(encoding='utf-8'))
    c9 = json.loads((B / 'Merged E10 FTMO17 2026-11-05/INPUTS-C9.json').read_text(encoding='utf-8')); p7 = json.loads((B / 'Portfolio P7 2026-11-10/INPUTS-P7.json').read_text(encoding='utf-8'))
    assert c9['window'] == p7['window'] and c9['year_begin_epoch'] == p7['year_begin_epoch']
    p7e = {c['ea'] for c in p7['candidates']}
    cands = p7['candidates'] + [c for c in c9['candidates'] if c['ea'] not in p7e]
    for ea in ('ema3', 'xau-rsi-vwap'):                                  # same EA in both pools: must be the same trades
        a = sorted((c['op'], c['cl'], round(c['unit_gross'], 6)) for c in c9['candidates'] if c['ea'] == ea); b = sorted((c['op'], c['cl'], round(c['unit_gross'], 6)) for c in p7['candidates'] if c['ea'] == ea)
        assert a == b, ea
    assert len({c['id'] for c in cands}) == len(cands)
    d = dict({k: v for k, v in p7.items() if k != 'candidates'}, candidates=cands); f.write_text(json.dumps(d, separators=(',', ':')), encoding='utf-8'); return d


ALL = None


def setup(name, members):
    data = dict(ALL, candidates=[c for c in ALL['candidates'] if c['ea'] in members]); plan = S.T.splan_for(data['window']); eas = sorted(members)
    plan['baskets'][name] = eas; plan['candidate_priority'] = plan['candidate_priority'] + [s for s in eas if s not in plan['candidate_priority']]
    events = S.E.master_events(plan, data); return data, plan, events, [x[0] for x in events]


def noguard_cls():
    class NoGuard(N.make_ftmo1(True)):
        def reject_reason(self, row, t, risk_, margin):
            if self.failed: return 'permanent_hard_failure'
            if self.finished: return 'passed'
            if self.balance >= self.target() - 1e-8 and self.best_day_ok(): return 'target_entry_gate_await_flat'
            return C.unguarded_reject(self, row, t, margin)
    return NoGuard


def run_one(model, plan, name, r, d, ev):
    if model == 'GUARD': return F1.one(plan, name, True, r, d, ev)
    return O.one(noguard_cls(), plan, name, False, r, d, ev)


def summarize(rows):
    n = len(rows)
    if not n: return None
    p = [x for x in rows if x['passed']]; days = sorted(x['days'] for x in p if x['days'] is not None)
    return dict(n=n, pass_30=round(sum(1 for x in p if x['days'] is not None and x['days'] <= 30) / n, 4), pass_60=round(sum(1 for x in p if x['days'] is not None and x['days'] <= 60) / n, 4),
                pass_90=round(sum(1 for x in p if x['days'] is not None and x['days'] <= 90) / n, 4), pass_180=round(len(p) / n, 4), breach=round(sum(x['breach'] for x in rows) / n, 4),
                median_days=days[len(days) // 2] if days else None, median_trades=sorted(x['trades'] for x in rows)[n // 2])


def evaluate(args):
    """members, risk, model, segments -> {segment: summary}. Weekday starts, 180-day horizon (pass_60 = passed by day 60)."""
    members, r, model, segs = args
    global ALL
    if ALL is None: ALL = pool()
    S.E.verify_freeze(); name = 'X' + ('U' if model == 'NOGUARD' else ''); data, plan, events, epochs = setup(name, members); out = {}
    for seg in segs:
        a, b = S.SEG[seg]; rows = []; d = max(a, S.P.DATA_START)
        while d < b and d + timedelta(days=S.P.HORIZON) <= S.P.DATA_END:
            if d.weekday() < 5: rows.append(run_one(model, plan, name, r, d, S.P.window(events, epochs, S.P.midnight(d), S.P.midnight(d + timedelta(days=S.P.HORIZON)))))
            d += timedelta(days=1)
        out[seg] = summarize(rows)
    return out


def mc(args):
    members, r, model = args
    global ALL
    if ALL is None: ALL = pool()
    name = 'X' + ('U' if model == 'NOGUARD' else ''); data, plan, events, epochs = setup(name, members); pl, mondays, index, priority = C.mc_pool(data, plan)
    rng = random.Random(S.T.SEED); sd = date(2030, 1, 7)
    return summarize([run_one(model, plan, name, r, sd, S.T.bootstrap_events(pl, mondays, index, rng, sd, priority)) for _ in range(S.T.PATHS)])


FORCED = [NAS, 'gold-band-wave', 'overnight-bias-orb', 'ema3']   # owner 2026-11-11: Nasdaq 5M, Overnight Bias ORB, Gold Band Wave, EMA3 are must-haves -> never dropped


def search(model, workers=7, forced=False):
    eas = sorted({c['ea'] for c in pool()['candidates']}); assert len(eas) == 13, eas
    log = H / f'SEARCH-{model}.jsonl'; done = {}; tag = model + ('-FORCED' if forced else '')
    if log.exists():
        for line in log.read_text(encoding='utf-8').splitlines():
            x = json.loads(line); done[(tuple(sorted(x['members'])), x['risk'])] = x['dev']
    keep = FORCED if forced else []
    # ADDENDUM 2 (2026-11-10): with every one-EA removal still infeasible the walk stopped at the infeasible 13 (NOGUARD 0.75%). Infeasible sets now score
    # -breach, so a removal that lowers breach counts as progress until breach <= 5%; feasible sets always rank above infeasible ones.
    def score(x): return (-1, -1) if x is None else ((-x['breach'], -x['breach']) if x['breach'] > 0.05 else (x['pass_60'], x['pass_90']))
    with ProcessPoolExecutor(workers) as ex:
        def batch(sets, r):
            todo = [s for s in sets if (tuple(sorted(s)), r) not in done]
            for s, res in zip(todo, ex.map(evaluate, [(s, r, model, ('dev',)) for s in todo])):
                done[(tuple(sorted(s)), r)] = res['dev']
                with open(log, 'a', encoding='utf-8') as f: f.write(json.dumps(dict(members=sorted(s), risk=r, dev=res['dev'])) + '\n')
            return {tuple(sorted(s)): done[(tuple(sorted(s)), r)] for s in sets}
        winners = {}
        for r in RISKS:
            cur = list(eas); best = score(batch([cur], r)[tuple(sorted(cur))]); print(tag, r, 'start all13', best, flush=True)
            while len(cur) > len(keep) + 1:
                res = batch([[m for m in cur if m != x] for x in cur if x not in keep], r)
                k, v = max(res.items(), key=lambda kv: score(kv[1]))
                if score(v)[0] < best[0] + 0.005: break
                gone = [m for m in cur if m not in k]; cur, best = list(k), score(v); print(tag, r, 'drop', gone, '->', len(cur), best, flush=True)
            for x in [e for e in eas if e not in cur]:
                v = batch([cur + [x]], r)[tuple(sorted(cur + [x]))]
                if score(v)[0] >= best[0] + 0.005: cur, best = sorted(cur + [x]), score(v); print(tag, r, 'add back', x, best, flush=True)
            assert all(f in cur for f in keep)
            winners[str(r)] = dict(members=sorted(cur), dev=done[(tuple(sorted(cur)), r)])
    (H / f'WINNERS-{tag}.json').write_text(json.dumps(winners, indent=1), encoding='utf-8'); print('SEARCH DONE', tag, flush=True)


def final(workers=7):
    """Validation pick, then OOS + MC reported once for the pick and the references."""
    out = dict(picks={}, refs={})
    jobs = []
    for model in ('GUARD', 'NOGUARD'):
        for kind, tag in (('win', model), ('win-forced', model + '-FORCED')):
            W = json.loads((H / f'WINNERS-{tag}.json').read_text(encoding='utf-8'))
            for r, w in W.items(): jobs.append((kind, model, float(r), w['members']))
        for ref, mem in dict(REFS, ALL13=sorted({c['ea'] for c in pool()['candidates']})).items():
            for r in RISKS: jobs.append(('ref:' + ref, model, r, mem))
    with ProcessPoolExecutor(workers) as ex:
        hist = list(ex.map(evaluate, [(m, r, model, ('dev', 'val', 'oos')) for _k, model, r, m in jobs]))
        rows = [dict(kind=k, model=model, risk=r, members=m, **h) for (k, model, r, m), h in zip(jobs, hist)]
        for model in ('GUARD', 'NOGUARD'):
            for kind in ('win', 'win-forced'):
                ok = [x for x in rows if x['kind'] == kind and x['model'] == model and x['val']['breach'] <= 0.05 and x['dev']['breach'] <= 0.05]   # ADDENDUM A (2026-11-11): dev-infeasible winners excluded
                out['picks'][model + ('-FORCED' if kind == 'win-forced' else '')] = max(ok, key=lambda x: x['val']['pass_60']) if ok else None
        picked = [id(x) for x in out['picks'].values() if x]
        mcjobs = [x for x in rows if (x['kind'].startswith('ref:') and x['risk'] in (0.005, 0.0075, 0.01)) or id(x) in picked]
        for x, res in zip(mcjobs, ex.map(mc, [(x['members'], x['risk'], x['model']) for x in mcjobs])): x['mc'] = res
    out['rows'] = rows
    (H / 'FINAL.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print('FINAL DONE', flush=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'time':
        t = time.time(); ALL = pool(); print(evaluate((REFS['P4'], 0.005, 'GUARD', ('dev',))), round(time.time() - t, 1), 's')
    elif a[0] == 'search': search(a[1], int(a[2]) if len(a) > 2 else 7, forced=len(a) > 3 and a[3] == 'forced')
    else: final(int(a[1]) if len(a) > 1 else 7)
