import csv,json,re,hashlib
from bisect import bisect_left
from datetime import datetime,timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def dt(s):return datetime.strptime(s,'%Y.%m.%d %H:%M:%S')
def bars(path):
    rows=list(csv.DictReader(path.open(encoding='utf-8-sig')))
    for r in rows:
        r['time']=dt(r['time'])
        for k in ('open','high','low','close'):r[k]=float(r[k])
    assert all(a['time']<b['time'] for a,b in zip(rows,rows[1:]))
    return rows,[r['time'] for r in rows]
def verify(tag):
    stats=json.loads((ROOT/f'{tag}-stats.json').read_text())
    h,times=bars(ROOT/'Audit'/f'{tag}-PERIOD_H4.csv')
    audit=list(csv.DictReader((ROOT/'Audit'/f'{tag}.csv').open(encoding='utf-8-sig')))
    contract=next(x for x in stats['quality_journal'] if 'H4 FVG RAW SELF TEST PASS' in x)
    tick=float(re.search(r' tick=([0-9.]+)',contract).group(1))
    minlot=float(re.search(r' minlot=([0-9.]+)',contract).group(1))
    zones={};used=set();counts={k:0 for k in ('zone','invalidate','accepted','rejected','error')}
    for r in audit:
        event=r['event'];counts[event]=counts.get(event,0)+1
        if event=='zone':
            first,third,created=dt(r['first_time']),dt(r['third_time']),dt(r['zone_created'])
            i=bisect_left(times,first);j=bisect_left(times,third)
            assert times[i]==first and times[j]==third and j==i+2
            # Weekend/session closures can delay the next executable H4 open.
            assert created>=third+timedelta(hours=4) and created<=dt(r['server_time'])
            side=int(r['direction']);lo=float(r['zone_low']);hi=float(r['zone_high']);stop=float(r['stop'])
            if side==1:
                assert h[j]['low']>h[i]['high']
                assert abs(lo-h[i]['high'])<tick+.000001 and abs(hi-h[j]['low'])<tick+.000001
                assert abs(stop-(h[i]['low']-tick))<tick+.000001
            else:
                assert h[j]['high']<h[i]['low']
                assert abs(lo-h[j]['high'])<tick+.000001 and abs(hi-h[i]['low'])<tick+.000001
                assert abs(stop-(h[i]['high']+tick))<tick+.000001
            assert lo<hi;zones[(created,side)]=r
        if event in ('accepted','rejected','error'):
            key=(dt(r['zone_created']),int(r['direction']));assert key in zones and key not in used;used.add(key)
        if event=='accepted':
            side=int(r['direction']);entry=float(r['entry']);lo=float(r['zone_low']);hi=float(r['zone_high'])
            stop=float(r['stop']);target=float(r['target']);risk=float(r['risk_cash']);equity=float(r['equity']);volume=float(r['volume'])
            assert lo-tick<=entry<=hi+tick
            assert stop<entry<target if side==1 else target<entry<stop
            # TP is submitted from the pre-fill executable quote. The actual fill
            # can differ under tester delay, so reconstruct and validate that quote.
            requested_entry=(target+2*stop)/3
            assert lo-tick<=requested_entry<=hi+tick
            assert risk>0 and equity>0 and volume>=minlot-1e-9 and abs(volume*100-round(volume*100))<1e-6
            assert dt(r['server_time'])>=dt(r['zone_created'])
        if event=='invalidate':
            px=float(r['entry']);side=int(r['direction']);lo=float(r['zone_low']);hi=float(r['zone_high'])
            assert px<lo if side==1 else px>hi
    trades=json.loads((ROOT/'Audit'/f'{tag}-trades.json').read_text())
    accepted=[r for r in audit if r['event']=='accepted']
    assert counts['accepted']==len(trades)==stats['trades']
    for r,t in zip(accepted,trades):
        assert t['side']==('Long' if int(r['direction'])==1 else 'Short')
        assert datetime.fromisoformat(t['open_time'])>=dt(r['server_time'])
        assert abs(t['volume']-float(r['volume']))<1e-8
        assert abs(t['initial_stop']-float(r['stop']))<tick+.000001
        assert abs(t['initial_target']-float(r['target']))<tick+.000001
        assert abs(t['planned_risk_cash']-float(r['risk_cash']))<.011
    assert counts['zone']==stats['zones'] and counts['invalidate']==stats['invalidated']
    assert abs(sum(t['net_profit'] for t in trades)-stats['net_profit'])<.051
    assert abs(sum(t['commission'] for t in trades)-stats['commission'])<.051
    assert abs(sum(t['swap'] for t in trades)-stats['swap'])<.051
    assert len({t['number'] for t in trades})==len(trades)
    for a,b in zip(trades,trades[1:]):assert a['close_time']<=b['open_time']
    return dict(tag=tag,passed=True,counts=counts,h4_bars=len(h))
def main():
    tags=[p.name[:-len('-stats.json')] for p in sorted(ROOT.glob('*-stats.json'))]
    rows=[verify(t) for t in tags];assert len(rows)==8
    (ROOT/'verification.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    print('VERIFICATION PASS',len(rows),'native runs,',sum(x['counts']['accepted'] for x in rows),'trades')
if __name__=='__main__':main()
