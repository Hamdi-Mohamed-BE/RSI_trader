"""Negative RR Study part B: Best Prop 9 challenge / first payout / funded $100k income per RR level.

Engines are imported unchanged from `FTMO First Payout Study 2026-10-20` (run.py, lowrisk.py) and the Best Prop retest.
Level `base` must reproduce the stored results of those studies exactly.

python prop.py e2e <level> | income <level> <risk 0.01|0.005> <cost>
"""
import bisect, importlib.util, json, random, sys, time
from datetime import date, timedelta
from pathlib import Path

R = Path(__file__).resolve().parent; B = R.parent; FP = B / 'FTMO First Payout Study 2026-10-20'
def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))


L = load('lowrisk', FP / 'lowrisk.py'); I, P, T, D, E = L.I, L.P, L.T, L.D, L.E
OUT = R / 'prop'


def setup(level):
    data = read(OUT / f'INPUTS-{level}.json'); plan = T.splan_for(data['window']); events = E.master_events(plan, data)
    return data, plan, events, [x[0] for x in events]


def windows():
    split = load('data_split', P.SPLIT_PY).research_split(P.DATA_START, P.DATA_END)
    w = {k: (date.fromisoformat(split[k]['start']), date.fromisoformat(split[k]['end_exclusive'])) for k in ('development', 'validation', 'oos')}
    w['all'] = (P.DATA_START, P.DATA_END); return w


def pool_index(data, plan):
    priority = {ea: i for i, ea in enumerate(plan['candidate_priority'])}
    pool = sorted((c for c in data['candidates'] if not c['end_censored']), key=lambda c: c['op']); ops = [c['op'] for c in pool]
    mondays, m = [], date(2021, 10, 11)
    while m + timedelta(days=T.BLOCK_DAYS) <= P.DATA_END: mondays.append(m); m += timedelta(days=7)
    index = {m: (bisect.bisect_left(ops, P.midnight(m)), bisect.bisect_left(ops, P.midnight(m + timedelta(days=T.BLOCK_DAYS)))) for m in mondays}
    return priority, pool, mondays, index


def e2e(level):
    began = time.time(); data, plan, events, epochs = setup(level); wins = windows(); out = dict(level=level, challenge_oos={}, challenge_all={}, e2e={}, e2e_mc={})
    for sc in plan['scenarios']:  # challenge only, retest method
        rows = [T.per_trial(D.replay(plan, s, sc['cost'], sc['handover'], P.window(events, epochs, s['epoch'], s['horizon_epoch']), [(-1e9, T.CAP)])) for s in T.oos_starts()]
        out['challenge_oos'][f"{sc['cost']}|{sc['handover']}"] = T.summarize(rows)
        starts, d = [], P.DATA_START
        while d + timedelta(days=180) <= P.DATA_END:
            if d.weekday() < 5: starts.append(P.start_dict(d, 180))
            d += timedelta(days=1)
        rows = [T.per_trial(D.replay(plan, s, sc['cost'], sc['handover'], P.window(events, epochs, s['epoch'], s['horizon_epoch']), [(-1e9, T.CAP)])) for s in starts]
        out['challenge_all'][f"{sc['cost']}|{sc['handover']}"] = T.summarize(rows)
    print(level, 'challenge', json.dumps(out['challenge_oos']['recorded_exness|next_prague_midnight']), f'{time.time() - began:.0f}s', flush=True)
    for sc, (cost, handover) in P.SCEN.items():
        rows, d = [], P.DATA_START
        while d <= P.E2E_LAST_START:
            if d.weekday() < 5:
                ch = P.window(events, epochs, P.midnight(d), P.midnight(d + timedelta(days=P.HORIZON)))
                rows.append(P.e2e_one(plan, ch, lambda fd: P.window(events, epochs, P.midnight(fd), P.midnight(fd + timedelta(days=P.HORIZON))), d, cost, handover))
            d += timedelta(days=1)
        for w, (a, b) in wins.items():
            sel = [r for r in rows if a <= date.fromisoformat(r['start']) < b]
            if sel: out['e2e'][f'{sc}|{w}_starts'] = P.summarize_e2e(sel)
    priority, pool, mondays, index = pool_index(data, plan); sd = date(2030, 1, 7); rng = random.Random(P.E2E_SEED); er = {sc: [] for sc in P.SCEN}
    for i in range(P.PATHS):
        ev = P.path_events(pool, mondays, index, rng, sd, priority, P.E2E_BLOCKS); ee = [x[0] for x in ev]
        ch = P.window(ev, ee, P.midnight(sd), P.midnight(sd + timedelta(days=P.HORIZON)))
        for sc, (cost, handover) in P.SCEN.items():
            er[sc].append(P.e2e_one(plan, ch, lambda fd: P.window(ev, ee, P.midnight(fd), P.midnight(fd + timedelta(days=P.HORIZON))), sd, cost, handover))
    for sc, v in er.items(): out['e2e_mc'][sc] = P.summarize_e2e(v)
    if level == 'base':
        rt = read(B / 'Best Prop Portfolio Retest 2026-10-20' / 'RESULTS.json'); fp = read(FP / 'RESULTS.json')
        for k, v in out['challenge_oos'].items(): assert v == rt['oos'][f'DI_OFF|{k}'], ('challenge parity', k)
        for k, v in out['e2e'].items(): assert v == fp['e2e'][f'DI_OFF|{k}'], ('e2e parity', k)
        for k, v in out['e2e_mc'].items(): assert v == fp['e2e_mc'][f'DI_OFF|{k}'], ('e2e MC parity', k)
        out['parity'] = 'exact vs retest OOS challenge and first-payout e2e / e2e MC'; print('base parity exact', flush=True)
    out['seconds'] = round(time.time() - began)
    (OUT / f'E2E-{level}.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); print('done e2e', level, out['seconds'], 's', flush=True)


def income(level, risk, cost):
    began = time.time(); data, plan, events, epochs = setup(level); wins = windows(); k = I.SIZE / 10000
    rows, d = [], P.DATA_START
    while d <= I.HIST_LAST_START:
        if d.weekday() < 5: rows.append(L.live2(plan, P.window(events, epochs, P.midnight(d), P.midnight(d + timedelta(days=I.HIST_DAYS))), d, I.HIST_DAYS, cost, k, 'set', risk))
        d += timedelta(days=1)
    out = dict(level=level, risk=risk, cost=cost, hist={'all_starts': L.summarize(rows, I.HIST_DAYS)})
    for w, (a, b) in wins.items():
        if w == 'all': continue
        sel = [x for x in rows if a <= date.fromisoformat(x['start']) < b]
        if sel: out['hist'][f'{w}_starts'] = L.summarize(sel, I.HIST_DAYS)
    priority, pool, mondays, index = pool_index(data, plan); sd = date(2030, 1, 7); days = T.BLOCK_DAYS * I.MC_BLOCKS; rng = random.Random(I.MC_SEED); mc = []
    for i in range(P.PATHS):
        mc.append(L.live2(plan, P.path_events(pool, mondays, index, rng, sd, priority, I.MC_BLOCKS), sd, days, cost, k, 'set', risk))
        if i % 500 == 0: print('mc', level, risk, cost, i, f'{time.time() - began:.0f}s', flush=True)
    out['mc'] = L.summarize(mc, days)
    if level == 'base':
        ref = read(FP / f"LOWRISK-SET_{'1.00' if risk == 0.01 else '0.50'}-{cost}.json")
        assert out['mc'] == ref['mc'], 'income MC parity'
        for key, v in out['hist'].items(): assert v == ref['hist'][key], ('income hist parity', key)
        out['parity'] = 'exact vs FTMO First Payout Study LOWRISK'; print('base income parity exact', risk, cost, flush=True)
    out['seconds'] = round(time.time() - began)
    (OUT / f'INCOME-{level}-{risk:g}-{cost}.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); print('done income', level, risk, cost, out['seconds'], 's', flush=True)


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'e2e': e2e(sys.argv[2])
    elif c == 'income': income(sys.argv[2], float(sys.argv[3]), sys.argv[4])
