"""Owner 2026-10-27: the Full EA portfolio on the Turbo $50k reward-account rules, at 0.3/0.5/0.6/0.75/1%.
Same numba kernel / firm model as sim.py (3% daily of the day-start balance; $3,000 trailing below the highest closed
balance, re-based after rewards; 14-day rewards, 3 days >= $250, best day <= 20%; 80% share; breach = all open stops hit).
Portfolios (Full EA = website full-eas stream, 36 ledgers; Gold News V9 has no ledger):
  A  Full EA as the BAT installs it, news OFF (32 EAs incl. US30/US100 hourly; hourly risk = frozen worst-loss reference).
  A+ Same with the four News Pulse bots ON at the BAT's separate 0.10% per order (news ledgers are tester news-spike
     artefacts, about +7R per trade: NOT credible, shown only because the BAT can switch them on).
  B  Full EA stop-defined EAs only (30; hourly have no SL, so a guard cannot admit them) WITH the Turbo guard.
  C  Turbo 20: the portfolio built from the Full EAs for this account (IMPROVE.json basket) WITH the Turbo guard.
No guard = only the per-trade risk (the BAT's native adaptive governor is not modelled; fixed risk).
python full_eas_turbo.py
"""
import json
from pathlib import Path
import numpy as np
import sim

R = Path(__file__).resolve().parent; B = R.parent
L = lambda n: json.loads((R / n).read_text(encoding='utf-8'))  # noqa: E731

raw = json.loads(sim.SRC.read_text(encoding='utf-8'))['full-eas']
rows = [(r['op'], r['cl'], r['key'], r['symbol'], r['unit_risk'], r['unit_gross'] + r['unit_comm'] + r['unit_swap'], r.get('risk_weight', 1.))
        for r in raw if r['unit_risk'] > 0 and r['op'] < r['cl']]
rows.sort(key=lambda r: (r[0], r[1]))
keys = sorted({r[2] for r in rows}); syms = sorted({r[3] for r in rows})
NEWS = [k for k in keys if k.startswith('news-pulse')]; HOURLY = ['us30-hourly-profiles', 'us100-hourly-profiles']
lane = np.array([keys.index(r[2]) for r in rows], np.int64)
base_w = np.array([r[6] for r in rows])
sim.A = dict(op=np.array([r[0] for r in rows]), cl=np.array([r[1] for r in rows]), lane=lane,
             sym=np.array([syms.index(r[3]) for r in rows], np.int64), ur=np.array([r[4] for r in rows]), un=np.array([r[5] for r in rows]), w=base_w.copy())
sim.KEYS, sim.SYMS, sim.NL, sim.NS = keys, syms, len(keys), len(syms)
news_lane = np.isin(lane, [keys.index(k) for k in NEWS])
assert len(keys) == 36 and len(NEWS) == 4, (len(keys), NEWS)

NOGUARD = dict(maxopen=1e6, persym=1e6, dstop=1e6, buffer=-1e6, taper=0.0, dcap=0.0)
imp = L('IMPROVE.json')
FULL = [k for k in keys if k not in NEWS]
STOP = [k for k in FULL if k not in HOURLY]
PORTS = [('A', 'Full EA as installed, news OFF, no guard', FULL, lambda r: NOGUARD),
         ('A+', 'Full EA as installed, news ON (0.10%/order), no guard', keys, lambda r: NOGUARD),
         ('B', 'Full EA stop-defined (30) + Turbo guard', STOP, lambda r: imp['risks'][str(r)]['guard']),
         ('C', 'Turbo 20 (built from Full EAs) + Turbo guard', imp['basket'], lambda r: imp['risks'][str(r)]['guard'])]
assert len(FULL) == 32 and len(STOP) == 30 and len(imp['basket']) == 20


def extra(o, days):
    br = o[:, 0] == 1; dd = o[:, 7]
    return dict(breach_days_mean=round(float(o[br, 1].mean()), 1) if br.any() else None,
                breach_days_median=round(float(np.median(o[br, 1])), 1) if br.any() else None,
                dd_closed_mean=round(float(dd.mean()), 0), worst_day_median=round(float(np.median(o[:, 9])), 0))


def main():
    out = {}
    # events copy the weight column when the paths are built, so paths are rebuilt (same seed) per portfolio and risk
    for code, name, mem, guard in PORTS:
        news = code == 'A+'
        for r in sim.RISKS:
            w = base_w.copy()
            if news: w[news_lane] = 0.10 / r
            sim.A['w'] = w
            mc3 = sim.mc_paths('all', sim.MC_N, 3 * 364, sim.SEED + 1); hist = sim.hist_paths('all', 365)
            g = guard(r)
            m = sim.simulate(mc3, mem, r, g, 3 * 364); h = sim.simulate(hist, mem, r, g, 365)
            out[f'{code}|{r}'] = dict(code=code, portfolio=name, risk=r, members=len(mem), guard=g,
                                     mc3=sim.summary(m, 3 * 364) | extra(m, 3 * 364), hist1=sim.summary(h, 365) | extra(h, 365))
            s = out[f'{code}|{r}']['mc3']
            print(code, r, 'mean/mo', round(s['income_total_mean'] / 36), 'breach', s['breach'], 'days', s['breach_days_mean'], 'worst day', s['worst_day'], flush=True)
    (R / 'FULL_EAS_TURBO.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
