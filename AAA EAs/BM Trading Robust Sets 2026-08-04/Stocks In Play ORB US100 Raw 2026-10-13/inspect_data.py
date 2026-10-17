import pandas as pd
import run as e
from collections import Counter

f,_=e.load()
for day in ['2020-01-02','2020-03-16','2020-07-02','2020-09-08','2021-03-16','2022-03-16','2022-12-30']:
    start=e.utc(day,'09:30');end=e.utc(day,'16:00')
    bars=f.loc[(f.index>=start)&(f.index<end)]
    missing=pd.date_range(start,end-pd.Timedelta(minutes=1),freq='min').difference(bars.index)
    near=f.loc[(f.index>=end-pd.Timedelta(minutes=6))&(f.index<end+pd.Timedelta(minutes=20))]
    print(day,'cash rows',len(bars),'missing NY',missing.tz_convert(e.NY).strftime('%H:%M').tolist()[:40],
          'quotes near close',near.index.tz_convert(e.NY).strftime('%H:%M').tolist(),flush=True)
cs=e.contexts(f)
rv=[c['rvol'] for c in cs if c['date']>='2020-01-01' and c['rvol'] is not None]
print('Opening RVOL population',len(rv),'min/max',min(rv),max(rv),'over2',sum(x>=2 for x in rv))
print('RVOL eligible dates',[(c['date'],round(c['rvol'],3),c['data_skip']) for c in cs if c['date']>='2020-01-01' and c['rvol'] is not None and c['rvol']>=2])
for y in [2020,2021,2022]:
    cnt=Counter();long_gaps=[]
    for c in cs:
        if not c['date'].startswith(str(y)):continue
        expected=pd.date_range(c['start'],c['end']-pd.Timedelta(minutes=1),freq='min')
        miss=expected.difference(c['bars'].index).tz_convert(e.NY)
        cnt.update(miss.strftime('%H:%M'))
        if len(miss)>3:long_gaps.append((c['date'],len(miss),miss.strftime('%H:%M').tolist()[:25]))
    print(y,'common missing minutes',cnt.most_common(12),'large gaps',long_gaps)
