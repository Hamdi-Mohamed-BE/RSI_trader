"""Reconcile native executions; conservative minute envelope for prop counterfactuals."""
from pathlib import Path
import csv,gzip,json,re,math,hashlib
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from verify_signals import audit_case
import numpy as np
import pandas as pd
import study as s
import prop_engine as pe
ROOT=Path(__file__).resolve().parent
DT=np.dtype([('ms','<i8'),('group','<i4'),('bal','<f8'),('eq','<f8'),('low','<f8'),('highbal','<f8')])
def csvread(p):return list(csv.DictReader(gzip.decompress(p.read_bytes()).decode('utf-8-sig').splitlines()))
def process(path):
    signal_audit=audit_case(path)
    run=json.loads((path/'run.json').read_text());groups=csvread(path/'groups.csv.gz');deals=csvread(path/'deals.csv.gz')
    trace=np.frombuffer(gzip.decompress((path/'trace.bin.gz').read_bytes()),dtype=DT)
    pos={};gmap={}
    for d in deals:
        if int(d['type']) not in (0,1):continue
        pos.setdefault(d['position'],[]).append(d)
        if int(d['entry'])==0:gmap[int(re.search(r'G(\d+)',d['comment'])[1])]=d['position']
    cash=[];trs=[];pcs=[];pls=[];offset=0;checks=0;maxrisk=0.;news=np.array(sorted({x['epoch'] for x in json.loads((ROOT.parent/'FTMO Fourteen EA Study 2026-09-27/prepared.json').read_text())['placements']}))
    for g in groups:
        ds=pos[gmap[int(g['group'])]];ins=[d for d in ds if int(d['entry'])==0];outs=[d for d in ds if int(d['entry']) in (1,3)]
        assert len(ins)==len(outs)==1
        en,ex=ins[0],outs[0];vol=float(g['volume']);assert abs(vol-float(ex['volume']))<1e-7
        gross=sum(float(d['profit']) for d in ds);comm=sum(float(d['commission'])+float(d['fee']) for d in ds);swap=sum(float(d['swap']) for d in ds)
        net=gross+comm+swap;assert abs(net-float(g['net']))<1e-5;cash.append(net)
        risk=float(g['risk']);maxrisk=max(maxrisk,risk);assert risk>0 and float(g['sl'])>0
        side=int(g['side']);fill=float(g['fill']);sl=float(g['sl']);tp=float(g['target']);tick=.001 if run['symbol']=='USDJPY' else .01
        # TP is fixed at the pre-delay quote, so allow observed fill slippage in ratio check.
        assert side*(fill-sl)>0 and side*(tp-fill)>0
        op=float(en['time_msc'])/1000;cl=float(ex['time_msc'])/1000
        date=datetime.fromtimestamp(op,ZoneInfo('America/New_York'));assert 600<=date.hour*60+date.minute<690 and date.weekday()<5
        assert cl>=op and float(g['open_time'])>=s.stamp(run['start'].replace('.','-'))
        a=trace[trace['group']==int(g['group'])];assert len(a)>0 and abs(a[-1]['bal']-net)<1e-5
        assert np.all(np.diff(a['ms'])>=0)
        opm=math.ceil(op/60);clm=max(opm+1,math.ceil(cl/60));minutes=np.arange(opm+1,clm+1)
        idx=np.searchsorted(a['ms'],minutes*60000,side='right')-1;idx=np.maximum(idx,0)
        floatprice=(a['eq']-a['bal'])/vol
        # The stored low spans the interval since the preceding trace. Retaining source fee/swap
        # in lows only makes the envelope conservative; it is not an exact target-broker tick path.
        lowprice=a['low']/vol
        cp=floatprice[idx].copy();lo=np.minimum(cp,lowprice[idx]);cp[-1]=gross/vol;lo[-1]=min(lo[-1],gross/vol)
        # No invented post-exit extrema. Native traces can precede recorded deal time by <=150 ms.
        near=bool((np.abs(news-op)<=300).any() or (np.abs(news-cl)<=300).any())
        trs.append([opm,clm,0,1 if run['symbol']=='USTEC' else 2,risk/vol,fill,gross/vol,comm/vol,swap/vol,offset,len(cp),side,near,cl-op<=30,1.])
        pcs.extend(cp);pls.extend(lo);offset+=len(cp);checks+=10+len(a)
    days=(pd.Timestamp(run['end'].replace('.','-'))-pd.Timestamp(run['start'].replace('.','-'))).days
    st=s.stats(np.array(cash)/100,days);st.update(return_pct=sum(cash)/100,equity_dd_pct=run['metrics']['equity_dd_pct'],net_money=sum(cash),
        trades_weekday=len(cash)/max(1,np.busday_count(run['start'].replace('.','-'),run['end'].replace('.','-'))),max_price_risk_money=maxrisk,
        cash_error=abs(sum(cash)-run['metrics']['net_profit']),history_quality=run['metrics']['history_quality'],
        capital_exhausted=bool(run['flags'].get('margin_call',0)>0 or any(float(g['base'])+float(g['net'])<=0 for g in groups)),
        last_exit_utc=datetime.fromtimestamp(float(groups[-1]['close_msc'])/1000,timezone.utc).isoformat() if groups else None)
    assert st['cash_error']<.02
    np.savez_compressed(path/'prop-input.npz',trades=np.array(trs,float).reshape(-1,15),close=np.array(pcs,np.float32),low=np.array(pls,np.float32))
    return dict(tag=path.name,symbol=run['symbol'],variant=run['variant']['name'],window=run['window'],model=run['model'],stats=st,checks=checks,flags=run['flags'],spec=run['spec'],tick_coverage=run['tick_coverage'],signal_audit=signal_audit)

def raw():
    results=[process(p.parent) for p in sorted((ROOT/'native').glob('*/run.json'))]
    s.save('RAW_RESULTS.json',results)
    for r in results:print(r['tag'],{k:r['stats'][k] for k in ['trades','return_pct','pf','equity_dd_pct']},flush=True)
    return results

def prop():
    records=[]
    pe.HORIZONS=np.array([30,60,120,180],np.int64)
    for p in sorted((ROOT/'native').glob('*-1y-m4/prop-input.npz')):
        tag=p.parent.name;z=np.load(p);tr=z['trades'];pc=z['close'];pl=z['low'];begin=pe.epoch(2025,9,27);end=pe.epoch(2026,9,27)
        clock=pe.clocks(begin,end)
        for firm,capital,risk in [('FTMO',10000,.005),('Instant',5000,.0025)]:
            cfg=dict(firm=firm,capital=capital,risk=risk,existing=False,withdraw_all=False)
            for stress in [False,True]:
                paths=[]
                for start in range(pe.epoch(2025,9,29),end-30*1440+1,7*1440):
                    en=min(start+180*1440,end)
                    rr=pe.invoke(tr,pc,pl,start,en,clock[start-begin:en-begin+1],cfg,stress,horizons=pe.HORIZONS)
                    paths.append(dict(start=start,snapshots=rr[0]))
                r=pe.invoke(tr,pc,pl,begin,end,clock,cfg,stress,lifecycle=False,horizons=np.array([365],np.int64))
                records.append(dict(tag=tag,firm=firm,stress=stress,rolling=pe.summarize([x['snapshots'] for x in paths]),
                    historical=dict(snapshot=dict(zip(pe.FIELDS,r[0][0])),trades=r[3],rejected=r[2]),paths=paths))
                s.save('NATIVE_PROP.json',records)
                print('PROP',tag,firm,stress,[(x['days'],x['payout'],x['breach_total_pct'],x['mean_cash']) for x in records[-1]['rolling']],flush=True)
    return records
if __name__=='__main__':
    import sys
    raw()
    if '--prop' in sys.argv:prop()

