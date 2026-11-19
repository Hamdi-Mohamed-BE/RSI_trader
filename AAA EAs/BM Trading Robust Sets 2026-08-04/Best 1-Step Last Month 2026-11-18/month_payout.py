"""Owner 2026-11-19: last month only - fees and payouts. Daily closed R (RESULTS.json daily_r, close day UTC, Nasdaq x0.75) through the frozen
Multi Firm Funded rules (sim.py TYPES, same targets / min days / best-day / split / 14-day first request). Breaches already checked in BREACH.json (none).
Case A: challenge bought 2026-10-18. Case B: already funded on 2026-10-18 (payout every 14 days; FTMO 1-Step on request once best day <= 50%).
In-sample one month; trades still open at 2026-11-17 23:59 counted at their mark; no guard / weekend flat / news closes."""
import importlib.util, json
from datetime import date
from pathlib import Path
H = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('sim', H.parent / 'Multi Firm Funded 2026-11-17/sim.py'); sim = importlib.util.module_from_spec(spec); spec.loader.exec_module(sim)
D = json.loads((H / 'RESULTS.json').read_text())['daily_r']; days = sorted(D); START = date(2026, 10, 18); END = date(2026, 11, 18)
out = {}
for name in ('FTMO_1S', 'FTMO_2S', 'FP_STD', 'T5_HS'):
    T = sim.TYPES[name]
    for risk in (0.0075, 0.005):
        a = dict(fee=round(T['fee']), passed=None, phase_passes=[], funded_from=None, payouts=[])
        ph, b, nd, npd, dp, state = 0, 0.0, 0, 0, [], 'ch'
        for d in days:
            r = D[d] * risk; dd = date.fromisoformat(d)
            if state == 'ch':
                b += r; dp.append(r); nd += 1; npd += 1 if r >= 0.005 else 0
                tgt, mind, minp = T['phases'][ph]; ok = T['best'] is None or (b > 0 and max(dp) <= T['best'] * b)
                if b >= tgt and nd >= mind and npd >= minp and ok:
                    a['phase_passes'].append(d); ph += 1; b, nd, npd, dp = 0.0, 0, 0, []
                    if ph == len(T['phases']): state = 'wait'; a['passed'] = d; ready = date.fromordinal(dd.toordinal() + 4)
            elif state == 'wait' and dd >= ready: state = 'fund'; a['funded_from'] = d; b, dp = r, [r]; first = date.fromordinal(dd.toordinal() + T['first'])
            elif state == 'fund': b += r; dp.append(r)
        a['funded_profit_at_end'] = round(b * 1e5) if state == 'fund' else 0
        a['days_to_pass'] = (date.fromisoformat(a['passed']) - START).days if a['passed'] else None
        # case B
        bb, dp2, nxt, pays = 0.0, [], date.fromordinal(START.toordinal() + T['first']), []
        for d in days:
            dd = date.fromisoformat(d)
            if dd >= nxt and bb > 0 and bb >= T['minpay'] and (T['best'] is None or max(dp2) <= T['best'] * bb):
                pays.append((d, round(T['split'] * bb * 1e5))); bb, dp2 = 0.0, []; nxt = date.fromordinal(dd.toordinal() + T['cycle'])
            bb += D[d] * risk; dp2.append(D[d] * risk)
        if END >= nxt and bb > 0 and (T['best'] is None or max(dp2) <= T['best'] * bb): pays.append(('2026-11-18 request', round(T['split'] * bb * 1e5))); bb = 0
        out[f'{name}@{risk*100:g}'] = dict(new_challenge=a, already_funded=dict(payouts=pays, total=sum(p for _, p in pays), unpaid_profit=round(bb * 1e5)))
        print(name, risk, a, '| funded:', pays, 'unpaid', round(bb * 1e5))
(H / 'MONTH_PAYOUT.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
