"""Follow-up (owner 2026-10-26): which EAs to keep, and can the Turbo $50k account average $1k / month?
A. Leave-one-out contribution of each of the 25 members at 0.75% and 0.3% (chosen guards): dev / val / all-period 12-month MC.
   An EA is a DRAG only if removing it raises mean 12-month income in BOTH dev and val (then shown on OOS / all-period).
B. Extended guard grid on DEVELOPMENT (adds a daily profit cap and smaller buffers / tapers), basket = 25 minus drags.
   Chosen per risk = highest dev mean 12-month income with breach <= 10%. Then validation, OOS (previously viewed) and all-period.
python improve.py contrib | grid | table
"""
import json, sys, time
from pathlib import Path
import sim

R = Path(__file__).resolve().parent
L = lambda n: json.loads((R / n).read_text(encoding='utf-8'))  # noqa: E731
GRID2 = [dict(maxopen=o, persym=p, dstop=d, buffer=b, taper=t, dcap=c) for o in (1.0, 1.5, 2.0, 2.5) for p in (1.0, 2.0) for d in (1.0, 1.5, 2.0, 2.5)
         for b in (0.25, 0.5, 1.0) for t in (0.05, 0.10, 0.20) for c in (0.0, 0.75, 1.0, 1.5, 2.0)]


def contrib():
    mem = L('SELECT.json')['members']; fin = L('FINAL.json'); t = time.time()
    paths = {seg: sim.mc_paths(seg, sim.MC_N, 365, sim.SEED + 7) for seg in ('dev', 'val', 'oos', 'all')}
    out = {}
    for r in ('0.75', '0.3'):
        g = fin[r]['guard']; base = {seg: sim.summary(sim.simulate(p, mem, float(r), g, 365), 365) for seg, p in paths.items()}
        rows = []
        for k in mem:
            s = {seg: sim.summary(sim.simulate(p, [m for m in mem if m != k], float(r), g, 365), 365) for seg, p in paths.items()}
            d = {seg: round(s[seg]['income_total_mean'] - base[seg]['income_total_mean'], 0) for seg in paths}
            rows.append(dict(ea=k, delta_if_removed=d, freeze_if_removed={seg: s[seg]['freeze'] for seg in paths},
                             drag=d['dev'] > 0 and d['val'] > 0))
        rows.sort(key=lambda x: x['delta_if_removed']['dev'] + x['delta_if_removed']['val'])
        out[r] = dict(base={seg: dict(mean=base[seg]['income_total_mean'], median=base[seg]['income_total_median'], freeze=base[seg]['freeze']) for seg in paths}, rows=rows)
        print(r, 'drags:', [x['ea'] for x in rows if x['drag']], f'{time.time() - t:.0f}s', flush=True)
    (R / 'CONTRIB.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


def grid():
    mem = L('SELECT.json')['members']; c = L('CONTRIB.json'); t = time.time()
    drags = sorted({x['ea'] for r in c for x in c[r]['rows'] if x['drag']}); basket = [m for m in mem if m not in drags]
    dev = sim.mc_paths('dev', sim.MC_N, 365, sim.SEED); val = sim.mc_paths('val', sim.MC_N, 365, sim.SEED); oos = sim.mc_paths('oos', sim.MC_N, 365, sim.SEED)
    allp = sim.mc_paths('all', sim.MC_N, 365, sim.SEED + 2); hist = sim.hist_paths('all', 365); out = dict(drags=drags, basket=basket, risks={})
    for r in sim.RISKS:
        rows = []
        for g in GRID2:
            if g['maxopen'] < r: continue
            s = sim.summary(sim.simulate(dev, basket, r, g, 365), 365); rows.append(dict(guard=g, dev=s))
        ok = [x for x in rows if x['dev']['breach_365'] <= 0.10]
        ch = max(ok, key=lambda x: (x['dev']['income_total_mean'], -(x['dev']['breach'] + x['dev']['freeze'])))
        g = ch['guard']
        res = dict(guard=g, dev=ch['dev'], val=sim.summary(sim.simulate(val, basket, r, g, 365), 365), oos=sim.summary(sim.simulate(oos, basket, r, g, 365), 365),
                   all=sim.summary(sim.simulate(allp, basket, r, g, 365), 365), hist=sim.summary(sim.simulate(hist, basket, r, g, 365), 365),
                   all_3y=sim.summary(sim.simulate(sim.mc_paths('all', sim.MC_N, 3 * 364, sim.SEED + 1), basket, r, g, 3 * 364), 3 * 364))
        out['risks'][str(r)] = res
        print(r, g, 'dev mean', ch['dev']['income_total_mean'], 'val', res['val']['income_total_mean'], 'oos', res['oos']['income_total_mean'],
              'all', res['all']['income_total_mean'], 'hist', res['hist']['income_total_mean'], f'{time.time() - t:.0f}s', flush=True)
    (R / 'IMPROVE.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


if __name__ == '__main__':
    dict(contrib=contrib, grid=grid)[sys.argv[1]]()
