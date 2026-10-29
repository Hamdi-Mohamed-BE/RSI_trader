"""Sensitivity for full_eas_turbo.py portfolio A: closed-balance (optimistic) breach instead of all open stops hit."""
import json, numpy as np
import full_eas_turbo as f, sim
out = {}
for r in sim.RISKS:
    sim.A['w'] = f.base_w.copy()
    mc3 = sim.mc_paths('all', sim.MC_N, 3 * 364, sim.SEED + 1); hist = sim.hist_paths('all', 365)
    m = sim.simulate(mc3, f.FULL, r, f.NOGUARD, 3 * 364, pess=False); h = sim.simulate(hist, f.FULL, r, f.NOGUARD, 365, pess=False)
    out[str(r)] = dict(mc3=sim.summary(m, 3 * 364) | f.extra(m, 3 * 364), hist1=sim.summary(h, 365) | f.extra(h, 365))
    a, b = out[str(r)]['mc3'], out[str(r)]['hist1']
    print(r, 'MC breach', a['breach'], 'avg days', a['breach_days_mean'], 'income/mo', round(a['income_total_mean'] / 36), '| hist breach<=1y', b['breach_365'], 'avg days', b['breach_days_mean'], 'income/mo', round(b['income_total_mean'] / 12), 'worst day', b['worst_day'], 'closed DD worst', b['dd_closed_worst'])
(f.R / 'FULL_EAS_TURBO_OPTIMISTIC_A.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
