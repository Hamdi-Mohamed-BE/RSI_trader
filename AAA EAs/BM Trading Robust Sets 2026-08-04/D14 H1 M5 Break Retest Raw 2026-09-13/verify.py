"""Independent checks of native signal audits against exported completed OHLC bars.

This is correctness verification, not a parameter search or second profit engine.
"""
import argparse
import csv
import json
import re
from bisect import bisect_left, bisect_right
from datetime import datetime, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def dt(v): return datetime.strptime(v,'%Y.%m.%d %H:%M:%S')
def loadbars(path):
    rows=list(csv.DictReader(path.open(encoding='utf-8-sig')))
    for r in rows:
        r['time']=dt(r['time'])
        for k in ('open','high','low','close'):r[k]=float(r[k])
    assert all(a['time']<b['time'] for a,b in zip(rows,rows[1:]))
    return rows,[r['time'] for r in rows]
def direction(b):
    ah=max(x['high'] for x in b[:7]);al=min(x['low'] for x in b[:7])
    bh=max(x['high'] for x in b[7:]);bl=min(x['low'] for x in b[7:])
    return 1 if bh>ah and bl>al else -1 if bh<ah and bl<al else 0
def pivot(b,i,high):
    if i<2 or i+2>=len(b): return False
    key='high' if high else 'low'
    others=[b[j][key] for j in (i-2,i-1,i+1,i+2)]
    return b[i][key]>max(others) if high else b[i][key]<min(others)
def reject(c,side,lo,hi):
    return lo<=c['low']<=hi and min(c['open'],c['close'])>hi if side==1 else lo<=c['high']<=hi and max(c['open'],c['close'])<lo
def verify(tag):
    path=ROOT/'Audit'
    d,td=loadbars(path/f'{tag}-PERIOD_D1.csv');h,th=loadbars(path/f'{tag}-PERIOD_H1.csv');m,tm=loadbars(path/f'{tag}-PERIOD_M5.csv')
    rows=list(csv.DictReader((path/f'{tag}.csv').open(encoding='utf-8-sig')))
    stats=json.loads((ROOT/f'{tag}-stats.json').read_text())
    contract=next(line for line in stats['quality_journal'] if 'RAW CONTRACT' in line)
    tick=float(re.search(r' tick=([0-9.]+)',contract).group(1))
    zones={};seen=set();checks={'bias':0,'zone':0,'held':0,'signal':0,'accepted':0}
    current=None
    for r in rows:
        event=r['event'];now=dt(r['server_time']);side=int(r['zone_dir'])
        if event in ('bias','zone','held','signal'):
            j=bisect_right(td,now)-1
            assert j>=14
            expected=direction(d[j-14:j]);assert expected==int(r['bias']), (tag,now,expected,r['bias'])
            checks['bias']+=1
        if event=='zone':
            origin=dt(r['zone_origin']);created=dt(r['zone_created']);i=bisect_left(th,origin)
            assert th[i]==origin and pivot(h,i,side==1)
            assert h[i+2]['time']+timedelta(hours=1)<=created<=now
            k=bisect_left(th,created)-1
            assert h[k]['time']+timedelta(hours=1)==created
            assert any(pivot(h,j,side==-1) and h[j+2]['time']+timedelta(hours=1)<=created for j in range(i+1,k-1)), (tag,r)
            assert (h[k]['close']>h[i]['high'] and h[k-1]['close']<=h[i]['high']) if side==1 else (h[k]['close']<h[i]['low'] and h[k-1]['close']>=h[i]['low'])
            lo=max(h[i]['open'],h[i]['close']) if side==1 else h[i]['low']
            hi=h[i]['high'] if side==1 else min(h[i]['open'],h[i]['close'])
            if hi-lo<tick:
                if side==1:lo=hi-tick
                else:hi=lo+tick
            assert abs(lo-float(r['zone_low']))<1e-6 and abs(hi-float(r['zone_high']))<1e-6
            zones[(origin,created)]=r;current=(origin,created);checks['zone']+=1
        if event=='invalidate':current=None
        if event=='held':
            held=dt(r['held_at']);touch=dt(r['touch_time']);lo=float(r['zone_low']);hi=float(r['zone_high'])
            k=bisect_left(tm,held);window=m[k-3:k]
            assert len(window)==3 and window[0]['time']>=touch and window[-1]['time']+timedelta(minutes=5)==held<=now
            assert sum(reject(c,side,lo,hi) for c in window)>=2
            extreme=min(c['low'] for c in window) if side==1 else max(c['high'] for c in window)
            assert abs(extreme-float(r['hold_extreme']))<1e-6
            checks['held']+=1
        if event=='signal':
            key=(dt(r['zone_origin']),dt(r['zone_created']))
            assert current==key and key in zones and key not in seen;seen.add(key)
            held=dt(r['held_at']);ht=dt(r['m5_high_time']);lt=dt(r['m5_low_time'])
            ih=bisect_left(tm,ht);il=bisect_left(tm,lt)
            assert tm[ih]==ht and tm[il]==lt and pivot(m,ih,True) and pivot(m,il,False)
            assert min(ht,lt)>=held
            assert max(m[ih+2]['time'],m[il+2]['time'])+timedelta(minutes=5)<=now
            assert abs(m[ih]['high']-float(r['m5_high']))<1e-6 and abs(m[il]['low']-float(r['m5_low']))<1e-6
            k=bisect_right(tm,now)-2
            assert m[k]['time']+timedelta(minutes=5)<=now<m[k]['time']+timedelta(minutes=10)
            if side==1:
                assert lt>ht and m[il]['low']>float(r['hold_extreme'])
                assert m[k]['close']>m[ih]['high'] and m[k-1]['close']<=m[ih]['high']
            else:
                assert ht>lt and m[ih]['high']<float(r['hold_extreme'])
                assert m[k]['close']<m[il]['low'] and m[k-1]['close']>=m[il]['low']
            begin=bisect_left(tm,key[1]);during=m[begin:k+1]
            assert all(c['close']>=float(r['zone_low']) for c in during) if side==1 else all(c['close']<=float(r['zone_high']) for c in during)
            stop=float(r['stop']);entry=float(r['entry']);target=float(r['target'])
            expected=m[il]['low']-tick if side==1 else m[ih]['high']+tick
            assert abs(stop-expected)<tick+1e-6
            assert abs(abs(target-entry)-2*abs(entry-stop))<tick+1e-6
            assert stop<entry<target if side==1 else target<entry<stop
            assert float(r['risk_cash'])>=float(r['equity'])*.01-1e-5
            checks['signal']+=1
        if event=='accepted':checks['accepted']+=1
    assert checks['accepted']==stats['trades'] and checks['signal']==stats['signals']
    trades=json.loads((path/f'{tag}-trades.json').read_text())
    assert abs(sum(t['net_profit'] for t in trades)-stats['net_profit'])<.051
    assert abs(sum(t['commission'] for t in trades)-stats['commission'])<.051
    assert abs(sum(t['swap'] for t in trades)-stats['swap'])<.051
    assert len({t['number'] for t in trades})==len(trades)
    for a,b in zip(trades,trades[1:]): assert a['close_time']<=b['open_time']
    return {'tag':tag,'passed':True,'checks':checks,'candle_counts':{'D1':len(d),'H1':len(h),'M5':len(m)}}
def main():
    cli=argparse.ArgumentParser();cli.add_argument('--tag');args=cli.parse_args()
    tags=[args.tag] if args.tag else [p.name[:-len('-stats.json')] for p in sorted(ROOT.glob('*-stats.json'))]
    results=[verify(t) for t in tags]
    (ROOT/'verification.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results,indent=2))
if __name__=='__main__':main()
