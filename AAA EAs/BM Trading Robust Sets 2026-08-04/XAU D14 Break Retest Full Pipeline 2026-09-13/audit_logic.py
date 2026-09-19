"""Independent completed-candle and accounting audit for parameterized native runs."""
import argparse
import csv
import importlib.util
import json
import math
from bisect import bisect_left,bisect_right
from datetime import datetime,timedelta
from pathlib import Path
from functools import lru_cache

ROOT=Path(__file__).resolve().parent
RAW=ROOT.parent/'D14 H1 M5 Break Retest Raw 2026-09-13'
spec=importlib.util.spec_from_file_location('raw_verify',RAW/'verify.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)

def pivot(b,i,span,high):
    if i<span or i+span>=len(b):return False
    values=[b[j]['high' if high else 'low'] for j in range(i-span,i+span+1) if j!=i]
    return b[i]['high']>max(values) if high else b[i]['low']<min(values)
def rejection(c,side,lo,hi,mode):
    if mode==0:return base.reject(c,side,lo,hi)
    return lo<=c['low']<=hi and c['close']>hi if side==1 else lo<=c['high']<=hi and c['close']<lo
def rounded(price,step,up):return (math.ceil(price/step-1e-9) if up else math.floor(price/step+1e-9))*step

@lru_cache(maxsize=1)
def bars():
    prefix=RAW/'Audit'/'xauusd-d14-raw-5y-model4'
    d,td=base.loadbars(Path(str(prefix)+'-PERIOD_D1.csv'))
    h,th=base.loadbars(Path(str(prefix)+'-PERIOD_H1.csv'))
    m,tm=base.loadbars(Path(str(prefix)+'-PERIOD_M5.csv'))
    tr=[0.0]+[max(m[i]['high'],m[i-1]['close'])-min(m[i]['low'],m[i-1]['close']) for i in range(1,len(m))]
    return d,td,h,th,m,tm,tr

def audit(tag):
    r=json.loads((ROOT/'Runs'/f'{tag}.json').read_text());c=r['config'];hp=c['InpH1Pivot'];mp=c['InpM5Pivot'];tick=.001
    rows=list(csv.DictReader((ROOT/'Audit'/f'{tag}.csv').open(encoding='utf-8-sig')))
    d,td,h,th,m,tm,tr=bars();seen=set();current=None;checks={'zone':0,'hold':0,'signal':0,'trail':0,'time_exit':0}
    active=None;last_sl=0;time_exits=[]
    for a in rows:
        event=a['event'];now=base.dt(a['server_time']);side=int(a['zone_dir']);lo=float(a['zone_low']);hi=float(a['zone_high'])
        if event in ('zone','held','signal'):
            j=bisect_right(td,now)-1;assert base.direction(d[j-14:j])==int(a['bias']), (tag,event,now,'daily')
        if event=='zone':
            origin=base.dt(a['zone_origin']);created=base.dt(a['zone_created']);i=bisect_left(th,origin)
            assert th[i]==origin and pivot(h,i,hp,side==1)
            assert h[i+hp]['time']+timedelta(hours=1)<=created<=now
            k=bisect_left(th,created)-1;assert h[k]['time']+timedelta(hours=1)==created
            assert any(pivot(h,j,hp,side==-1) and h[j+hp]['time']+timedelta(hours=1)<=created for j in range(i+1,k-hp+1)), (tag,a,'opposite')
            assert (h[k]['close']>h[i]['high'] and h[k-1]['close']<=h[i]['high']) if side==1 else (h[k]['close']<h[i]['low'] and h[k-1]['close']>=h[i]['low'])
            expectedlo=h[i]['low'] if c['InpZoneMode'] or side<0 else max(h[i]['open'],h[i]['close'])
            expectedhi=h[i]['high'] if c['InpZoneMode'] or side>0 else min(h[i]['open'],h[i]['close'])
            if expectedhi-expectedlo<tick:
                if side==1:expectedlo=expectedhi-tick
                else:expectedhi=expectedlo+tick
            assert abs(lo-expectedlo)<1e-6 and abs(hi-expectedhi)<1e-6
            current=(origin,created);checks['zone']+=1
        if event=='invalidate':current=None
        if event=='held':
            held=base.dt(a['held_at']);touch=base.dt(a['touch_time']);k=bisect_left(tm,held);w=m[k-c['InpHoldBars']:k]
            assert len(w)==c['InpHoldBars'] and w[0]['time']>=touch and w[-1]['time']+timedelta(minutes=5)==held<=now
            assert all(y['time']-x['time']==timedelta(minutes=5) for x,y in zip(w,w[1:]))
            assert sum(rejection(x,side,lo,hi,c['InpWickMode']) for x in w)>=2
            extreme=min(x['low'] for x in w) if side==1 else max(x['high'] for x in w)
            assert abs(extreme-float(a['hold_extreme']))<1e-6;checks['hold']+=1
        if event=='signal':
            key=(base.dt(a['zone_origin']),base.dt(a['zone_created']));assert current==key and key not in seen;seen.add(key)
            assert c['InpDirection']==0 or c['InpDirection']==side
            assert c['InpSessionStart']<=now.hour<c['InpSessionEnd']
            assert c['InpMaxZoneHours']==0 or (now-key[1]).total_seconds()<=c['InpMaxZoneHours']*3600
            held=base.dt(a['held_at']);ht=base.dt(a['m5_high_time']);lt=base.dt(a['m5_low_time'])
            ih=bisect_left(tm,ht);il=bisect_left(tm,lt)
            assert pivot(m,ih,mp,True) and pivot(m,il,mp,False)
            assert min(ht,lt)>=held and max(m[ih+mp]['time'],m[il+mp]['time'])+timedelta(minutes=5)<=now
            k=bisect_right(tm,now)-2
            assert m[k]['time']+timedelta(minutes=5)<=now<m[k]['time']+timedelta(minutes=10)
            if side==1:
                assert lt>ht and m[il]['low']>float(a['hold_extreme']) and m[k]['close']>m[ih]['high'] and m[k-1]['close']<=m[ih]['high']
            else:
                assert ht>lt and m[ih]['high']<float(a['hold_extreme']) and m[k]['close']<m[il]['low'] and m[k-1]['close']>=m[il]['low']
            during=m[bisect_left(tm,key[1]):k+1]
            assert all(x['close']>=lo for x in during) if side==1 else all(x['close']<=hi for x in during)
            atr=sum(tr[k-13:k+1])/14
            expected=m[il]['low']-tick-c['InpStopBufferATR']*atr if side==1 else m[ih]['high']+tick+c['InpStopBufferATR']*atr
            stop=float(a['stop']);entry=float(a['entry']);tp=float(a['target'])
            assert abs(stop-rounded(expected,tick,side<0))<tick+.000001,(tag,a,'ATR stop',expected,atr)
            assert abs(abs(tp-entry)-c['InpTargetR']*abs(entry-stop))<tick+.000001
            assert stop<entry<tp if side==1 else tp<entry<stop
            assert float(a['risk_cash'])>=float(a['equity'])*c['InpRiskPercent']/100-1e-5
            assert float(a['entry_spread_cost'])>=0;checks['signal']+=1
        if event=='accepted':
            assert active is None
            active={'time':now,'side':side,'stop':float(a['stop']),'entry':float(a['entry'])};last_sl=active['stop']
        if event=='trail':
            assert active is not None
            new=float(a['stop']);assert new>last_sl if active['side']==1 else new<last_sl
            assert c['InpManagement'] in (1,2,3)
            if c['InpManagement']==1:assert abs(new-active['entry'])<=tick+.000001
            if c['InpManagement']==3:
                k=bisect_right(tm,now)-2;origin=k-mp
                assert pivot(m,origin,mp,active['side']<0)
                expected=m[origin]['low']-tick if active['side']==1 else m[origin]['high']+tick
                assert abs(new-rounded(expected,tick,active['side']<0))<tick+.000001
            last_sl=new;checks['trail']+=1
        if event=='time_exit':
            # The deal callback can precede or follow this audit line, so timing
            # is checked from the closed native trade ledger below.
            assert c['InpMaxHoldHours']>0
            time_exits.append(now);checks['time_exit']+=1
        if event=='exit':active=None
    ts=json.loads((ROOT/'Audit'/f'{tag}-trades.json').read_text());assert len(ts)==r['trades']
    assert abs(sum(t['net_profit'] for t in ts)-r['net_profit'])<.051
    assert abs(sum(t['commission'] for t in ts)-r['commission'])<.051
    assert abs(sum(t['swap'] for t in ts)-r['swap'])<.051
    assert all(x['close_time']<=y['open_time'] for x,y in zip(ts,ts[1:]))
    for when in time_exits:
        matched=[t for t in ts if abs((datetime.fromisoformat(t['close_time'])-when).total_seconds())<=3]
        assert len(matched)==1,(tag,when,'time exit native match')
        t=matched[0]
        assert (datetime.fromisoformat(t['close_time'])-datetime.fromisoformat(t['open_time'])).total_seconds()>=c['InpMaxHoldHours']*3600-3
    assert checks['signal']==r['signals']
    return {'tag':tag,'passed':True,'checks':checks,'accounting_passed':True}

def main():
    cli=argparse.ArgumentParser();cli.add_argument('--tag');cli.add_argument('--all',action='store_true');args=cli.parse_args()
    if args.tag:tags=[args.tag]
    elif args.all:tags=[p.stem for p in sorted((ROOT/'Runs').glob('*.json'))]
    else:
        final=json.loads((ROOT/'final-runs.json').read_text());frozen=json.loads((ROOT/'frozen-selection.json').read_text())['selected']
        tags=[final[k] for k in ('6m','1y','3y','5y','safe-1y','safe-5y')]+[frozen['train'],frozen['validation']]
    results=[]
    for tag in tags:
        # Rebuild derived annotations from the immutable native audit. An
        # accepted-order record includes entry costs in equity; sizing used
        # the preceding signal record's pre-entry equity, not that later value.
        from run_pipeline import annotate_trades
        path=ROOT/'Audit'/f'{tag}-trades.json'
        ts=json.loads(path.read_text())
        rows=list(csv.DictReader((ROOT/'Audit'/f'{tag}.csv').open(encoding='utf-8-sig')))
        path.write_text(json.dumps(annotate_trades(ts,rows),indent=2),encoding='utf-8')
        v=audit(tag);results.append(v);print('AUDIT PASS '+tag,flush=True)
    (ROOT/'logic-verification.json').write_text(json.dumps(results,indent=2))
if __name__=='__main__':main()
