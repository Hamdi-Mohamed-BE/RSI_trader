"""Independent executed-entry oracle and deal reconciliation, without MT5 imports."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def oracle(sig,bars,control,seed=290929):
    p=bars[bars.kind=='parent'].sort_values('time').reset_index(drop=True)
    m=bars[bars.kind=='m1'].sort_values('time').reset_index(drop=True)
    assert len(p)==20 and len(m)==64
    a,b,c=p.iloc[-3],p.iloc[-2],p.iloc[-1]
    direction=-int(sig.raw_side);tf=int(sig.parent_seconds)
    assert c.time+tf==sig.ready and c.time-b.time==tf and b.time-a.time==tf
    prior=p.iloc[4:18]
    tr=np.maximum(prior.high-prior.low,np.maximum(abs(prior.high-p.close.shift(1).iloc[4:18]),abs(prior.low-p.close.shift(1).iloc[4:18])))
    atr=float(tr.mean());body=b.close-b.open
    assert abs(body)+1e-9>=atr and abs(body)+1e-9>=.6*(b.high-b.low)
    assert direction*body>0 and abs(atr-sig.atr)<1e-6
    if direction==1:
        assert c.low>a.high and c.close<=b.high
        mid=(c.low+a.high)/2
    else:
        assert c.high<a.low and c.close>=b.low
        mid=(c.high+a.low)/2
    assert abs(mid-sig.midpoint)<1e-7
    assert m.iloc[-1].time==sig.signal_time and sig.signal_time>=sig.ready
    assert 60<=sig.fill_time-sig.ready<=1811
    assert 60<=sig.fill_time-sig.signal_time<=71
    assert m.time.max()+60<=sig.fill_time
    local=pd.Timestamp(int(sig.fill_time),unit='s',tz='UTC').tz_convert('America/New_York')
    assert local.dayofweek<5 and 570<=local.hour*60+local.minute<930
    after=m[m.time>=sig.ready]
    assert len(after)>0
    assert (after.low>mid).all() if direction==1 else (after.high<mid).all()
    z=m.iloc[-1];prev=m.iloc[-2]
    if sig.trigger==0:
        at=m[m.time<sig.ready].tail(20).reset_index(drop=True)
        idx=np.flatnonzero(direction*(at.close-at.open)>0)
        assert len(at)==20 and len(idx)>0
        i=int(idx[-1])
        while i>0 and direction*(at.iloc[i-1].close-at.iloc[i-1].open)>0:i-=1
        level=at.iloc[i].open
        assert direction*(at.iloc[-1].close-level)>=0 and direction*(level-mid)>0
        assert abs(level-sig.reference)<1e-7
        assert direction*(prev.close-level)>=0 and direction*(z.close-level)<0
    else:
        candidates=[]
        for i in range(2,len(m)-1):
            aa,bb,cc=m.iloc[i-2],m.iloc[i-1],m.iloc[i]
            if cc.time<z.time-1200 or cc.time-bb.time!=60 or bb.time-aa.time!=60:continue
            gap=cc.low>aa.high if direction==1 else cc.high<aa.low
            if not gap:continue
            level=aa.high if direction==1 else aa.low
            if direction*(level-mid)<=0:continue
            intact=(direction*(m.iloc[i+1:-1].close-level)>=0).all()
            if intact and direction*(prev.close-level)>=0 and direction*(z.close-level)<0:candidates.append(level)
        assert candidates and abs(candidates[-1]-sig.reference)<1e-7
    if control:
        x=(int(sig.ready)+int(sig.signal_time+60)+seed)&0xffffffff
        x^=x>>16;x=(x*0x7feb352d)&0xffffffff;x^=x>>15;x=(x*0x846ca68b)&0xffffffff;x^=x>>16
        assert int(sig.actual_side)==(1 if x&1 else -1)
    else:assert sig.raw_side==sig.actual_side

def streak(x,positive):
    best=cur=0
    for p in x:
        cur=cur+1 if (p>0 if positive else p<0) else 0;best=max(best,cur)
    return best

def main():
    rows=[];total=0
    for f in sorted((R/'native').glob('*/run.json')):
        run=json.loads(f.read_text());root=f.parent
        assert all(sha(R/name)==value for name,value in run['build'].items())
        cache=root/'entry-audit.json';fingerprint={p.name:sha(p) for p in [f,R/'audit.py',root/'trades.csv.gz',root/'signals.csv.gz',root/'audit.csv.gz']}
        if cache.exists():
            prev=json.loads(cache.read_text())
            if prev['fingerprint']==fingerprint:
                rows.append(prev['row']);total+=prev['row']['metrics']['trades'];print('CACHED',run['tag'],flush=True);continue
        d=pd.read_csv(root/'trades.csv.gz').astype(float);s=pd.read_csv(root/'signals.csv.gz').astype(float);a=pd.read_csv(root/'audit.csv.gz')
        assert len(d)==len(s)==run['metrics']['trades'] and s.position_id.is_unique
        assert abs(d.net_profit.sum()-run['metrics']['net_profit'])<.02
        assert np.allclose(d.net_profit,d.gross_profit+d.commission+d.swap+d.fee)
        assert np.allclose(d.volume,d.closed_volume) and (d.actual_risk>0).all()
        groups={k:v for k,v in a.groupby('position_id')}
        for sig in s.itertuples(index=False):oracle(sig,groups[sig.position_id],run['control'])
        merge=d.merge(s,on='position_id',validate='one_to_one')
        assert (merge.side==merge.actual_side).all()
        # signals.fill_time was written using TimeCurrent() inside OnTick: it is
        # the handled-quote clock, NOT the deal clock. At 150ms execution delay,
        # integer-second deal time can be one second later. Never allow earlier fills.
        clock_delta=merge.open_epoch-merge.fill_time
        assert ((clock_delta>=0)&(clock_delta<=1)).all()
        assert np.allclose(merge.open_price,merge.fill)
        # Quote-based nominal RR is equal before execution delay, tick rounding <=0.02.
        assert ((merge.initial_tp-merge.quote)*merge.side>0).all()
        assert (abs(abs(merge.initial_tp-merge.quote)-abs(merge.initial_sl-merge.quote))<=.021).all()
        if not run['control']:assert (abs(merge.initial_tp-merge.midpoint)<=.011).all()
        days=np.busday_count(run['start'].replace('.','-'),run['end'].replace('.','-'))
        calendar=(pd.Timestamp(run['end'])-pd.Timestamp(run['start'])).days
        m=run['metrics'];m.update(trades_per_month=len(d)/(calendar/30.4375),trades_per_weekday=len(d)/days,
          win_streak=streak(d.net_profit,True),loss_streak=streak(d.net_profit,False),
          commission=float(d.commission.sum()),swap=float(d.swap.sum()),gross_profit=float(d.gross_profit.sum()),
          median_spread=float(s.spread.median()) if len(s) else None,
          median_commission_R=float((-d.commission/d.actual_risk).median()) if len(d) else None,
          max_initial_risk_pct=float((d.actual_risk/d.requested_risk).max()) if len(d) else None,
          max_deal_clock_delta_seconds=float(clock_delta.max()) if len(d) else None,
          max_hold_minutes=float(((d.close_epoch-d.open_epoch)/60).max()) if len(d) else None)
        row=dict(tag=run['tag'],mode=run['bot']['mode'],control=run['control'],window=run['window'],model=run['model'],metrics=m,flags=run['flags'],tick_coverage=run['tick_coverage'])
        rows.append(row);cache.write_text(json.dumps(dict(fingerprint=fingerprint,row=row),indent=2))
        total+=len(s)
        print('PASS',run['tag'],len(s),flush=True)
    (R/'AUDIT.json').write_text(json.dumps(dict(executed_entry_checks=total,all_passed=True,limitations='Executed signals only; not a complete independent candidate-coverage replay.',rows=rows),indent=2))
    print('AUDIT COMPLETE',total,'executed entries')
if __name__=='__main__':main()
