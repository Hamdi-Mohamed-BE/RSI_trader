"""Named firm mixes with per-account risk + expected cost per account / per firm (36-month MC, base and +0.05R cost stress). python mix.py"""
import json
from pathlib import Path

import numpy as np

import sim

H = Path(__file__).resolve().parent
FIRM = dict(FTMO_1S='FTMO', FTMO_2S='FTMO', FP_STD='FundingPips', FP_PRO='FundingPips', T5_HS='The5ers', FN_2S25='FundedNext')
MIXES = {
    'A 0.5% spread (500k)': [('FTMO_1S', 2, '0.5'), ('FP_STD', 2, '0.5'), ('T5_HS', 1, '0.5')],
    'B 0.75% lean (300k)': [('FTMO_2S', 1, '0.75'), ('FP_STD', 1, '0.75'), ('T5_HS', 1, '0.75')],
    'C mixed (500k)': [('FTMO_1S', 2, '0.5'), ('FTMO_2S', 1, '0.75'), ('FP_STD', 1, '0.75'), ('T5_HS', 1, '0.75')],
    'D cost-robust (900k)': [('FTMO_1S', 2, '0.5'), ('FTMO_2S', 2, '0.75'), ('FP_STD', 4, '0.75'), ('T5_HS', 1, '0.75')],
}


def mix(items, tag):
    R = json.loads((H / f'TYPES{tag}.json').read_text()); tot = 0; firms = {}; acc = []
    for n, k, rk in items:
        m = R[f'{n}@{rk}']['mc']; tot = tot + k * np.load(H / f'mc_{n}@{rk}{tag}.npy'); fee = sim.TYPES[n]['fee']
        acc.append(dict(type=n, count=k, risk=rk, fee_per_attempt=round(fee), attempts_36m=m['buys_mean'], fees_36m_per_account=m['fees_mean'],
                        refund=round(sim.TYPES[n]['refund']), funded_breaches=m['breaches_funded_mean'], challenge_fails=m['breaches_challenge_mean'],
                        first_payout_day=m['first_payout_day_median'], net_month_median_per_account=m['monthly_median']))
        f = firms.setdefault(FIRM[n], dict(accounts=0, capital=0, attempts_36m=0.0, fees_36m=0.0, upfront=0.0))
        f['accounts'] += k; f['capital'] += k * sim.TYPES[n]['size']; f['attempts_36m'] = round(f['attempts_36m'] + k * m['buys_mean'], 1)
        f['fees_36m'] = round(f['fees_36m'] + k * m['fees_mean']); f['upfront'] = round(f['upfront'] + k * fee)
    avg = tot.mean(1)
    return dict(monthly_median=round(float(np.median(avg))), monthly_p10=round(float(np.percentile(avg, 10))), monthly_p90=round(float(np.percentile(avg, 90))),
                p_avg_10k=round(float((avg >= 1e4).mean() * 100), 1), first_year_month=round(float(tot[:, :12].mean())), years_2_3_month=round(float(tot[:, 12:].mean())),
                months_ge_10k=round(float((tot >= 1e4).mean() * 100), 1), months_le_0=round(float((tot <= 0).mean() * 100), 1),
                upfront=round(sum(f['upfront'] for f in firms.values())), fees_36m=round(sum(f['fees_36m'] for f in firms.values())), firms=firms, accounts=acc)


out = {name: {t or 'base': mix(items, sim.VAR + t) for t in ('', '_cost0.05')} for name, items in MIXES.items()}
(H / f'MIXES{sim.VAR}.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
for name, v in out.items():
    for t, x in v.items(): print(name, t, {k: x[k] for k in x if k not in ('firms', 'accounts')}); print('    firms', x['firms'])
