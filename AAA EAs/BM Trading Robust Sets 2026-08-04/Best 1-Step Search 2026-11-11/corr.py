"""Correlation of the 11 Best 1-Step EAs (owner 2026-11-11). Daily R by CLOSE date (weekdays 2019-07-16 -> 2026-10-31, days without a trade = 0), monthly R,
loss-day overlap, portfolio vs sum of stand-alone volatility. Same native ledgers as breakdown.py. Run: uv run --with numpy --with pandas python corr.py -> CORR.json / CORR.md"""
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd
H = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('bd', H / 'breakdown.py'); BD = importlib.util.module_from_spec(spec); spec.loader.exec_module(BD)
SHORT = {'nasdaq-5m-candle-momentum': 'NAS5M', 'usdjpy-london-open-momentum': 'USDJPY', '3-way-gold': '3WG', 'sell-nasdaq-15min': 'SELLNAS', 'ema3': 'EMA3',
         'orb-volume-profile-volume-confirmed': 'ORBVC', 'xau-squeeze-momentum-standard': 'SQZ', 'us100-selective-orb-v3': 'SELV3', 'xau-rsi-vwap': 'RSIV',
         'overnight-bias-orb': 'ONB', 'gold-band-wave': 'GBW'}
R = BD.all_years(); days = pd.bdate_range('2019-07-16', '2026-10-31')
D = pd.DataFrame(0.0, index=days, columns=list(SHORT.values()))
for k, rows in R.items():
    for r in rows:
        d = pd.Timestamp(r['c'][:10])
        if d in D.index: D.loc[d, SHORT[k]] += r['r']
        elif d >= days[0] and d <= days[-1]: D.loc[D.index[D.index.get_indexer([d], method='bfill')[0]], SHORT[k]] += r['r']   # weekend close -> next weekday
M = D.resample('ME').sum()
cd, cm = D.corr(), M.corr()
off = lambda c: c.values[np.triu_indices(len(c), 1)]  # noqa: E731
port = D.sum(axis=1)
loss = D < 0; both = {}
for a in D.columns:
    for b in D.columns:
        if a < b: both[f'{a}-{b}'] = round(float((loss[a] & loss[b]).sum() / max(1, (loss[a] | loss[b]).sum())), 3)
worst = port.nsmallest(10)
out = dict(daily=cd.round(2).to_dict(), monthly=cm.round(2).to_dict(), avg_daily=round(float(off(cd).mean()), 3), avg_monthly=round(float(off(cm).mean()), 3),
           max_daily=round(float(off(cd).max()), 3), min_daily=round(float(off(cd).min()), 3),
           sd_sum_daily=round(float(D.std().sum()), 2), sd_port_daily=round(float(port.std()), 2), diversification_ratio=round(float(D.std().sum() / port.std()), 2),
           sd_port_if_corr1=round(float(D.std().sum()), 2), sd_port_if_corr0=round(float(np.sqrt((D.std() ** 2).sum())), 2),
           loss_overlap_top=sorted(both.items(), key=lambda kv: -kv[1])[:8],
           worst_days={str(d.date()): dict(total=round(float(v), 2), eas={c: round(float(D.loc[d, c]), 2) for c in D.columns if D.loc[d, c] != 0}) for d, v in worst.items()},
           losing_eas_on_worst_days=float(np.mean([(D.loc[d] < 0).sum() for d in worst.index])))
(H / 'CORR.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print('DAILY\n', cd.round(2).to_string()); print('\nMONTHLY\n', cm.round(2).to_string())
print({k: out[k] for k in ('avg_daily', 'avg_monthly', 'max_daily', 'min_daily', 'sd_sum_daily', 'sd_port_daily', 'diversification_ratio', 'sd_port_if_corr0', 'losing_eas_on_worst_days')})
print('loss overlap', out['loss_overlap_top']); print(json.dumps(out['worst_days'], indent=0)[:1800])
