"""Owner 2026-10-27: what would lift the Turbo 20 (+ guard, 0.75% label) to $1k / month on average?
Each lever changed alone from the chosen profile, then sensible combinations. Same kernel and firm model as sim.py.
All-period data (in-sample: the guard was tuned on development; this sweep is NOT a new validation).
python levers_1k.py
"""
import json
from pathlib import Path
import sim

R = Path(__file__).resolve().parent
imp = json.loads((R / 'IMPROVE.json').read_text(encoding='utf-8'))
BASKET = imp['basket']; G = dict(imp['risks']['0.75']['guard']); r = 0.75
mc3 = sim.mc_paths('all', sim.MC_N, 3 * 364, sim.SEED + 1); hist = sim.hist_paths('all', 365)
dev = sim.mc_paths('dev', sim.MC_N, 365, sim.SEED); val = sim.mc_paths('val', sim.MC_N, 365, sim.SEED)

LEVERS = [('Chosen profile (80% share, 14-day rewards)', {}, {}),
          ('95% profit share', {}, dict(share=0.95)),
          ('5-day rewards', {}, dict(cycle=5)),
          ('5-day rewards + 95% share', {}, dict(cycle=5, share=0.95)),
          ('Taper 10% of room', dict(taper=0.10), {}),
          ('Taper 15% of room', dict(taper=0.15), {}),
          ('Taper 20% of room', dict(taper=0.20), {}),
          ('Taper 10% + profit cap 1.0%', dict(taper=0.10, dcap=1.0), {}),
          ('Taper 10% + profit cap 1.0% + 5-day + 95%', dict(taper=0.10, dcap=1.0), dict(cycle=5, share=0.95)),
          ('No daily profit cap', dict(dcap=0.0), {}),
          ('Floor does NOT trail (static $47k; firm-rule sensitivity)', {}, dict(trail=False)),
          ('Static floor + 5-day + 95%', {}, dict(trail=False, cycle=5, share=0.95))]
out = []
for name, gchg, kw in LEVERS:
    g = {**G, **gchg}
    m = sim.summary(sim.simulate(mc3, BASKET, r, g, 3 * 364, **kw), 3 * 364)
    h = sim.summary(sim.simulate(hist, BASKET, r, g, 365, **kw), 365)
    d = sim.summary(sim.simulate(dev, BASKET, r, g, 365, **kw), 365)
    v = sim.summary(sim.simulate(val, BASKET, r, g, 365, **kw), 365)
    row = dict(lever=name, guard=g, kw=kw, mc3_mean=round(m['income_total_mean'] / 36), mc3_median=round(m['income_total_median'] / 36),
               hist_mean=round(h['income_total_mean'] / 12), dev_mean=round(d['income_total_mean'] / 12), val_mean=round(v['income_total_mean'] / 12),
               breach=m['breach'], hist_breach=h['breach_365'], freeze=m['freeze'], worst_day=m['worst_day'], dd_closed_worst=m['dd_closed_worst'],
               trades_month=h['trades_per_month'], trades_day=h['trades_per_day'])
    out.append(row); print(row, flush=True)
(R / 'LEVERS_1K.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
