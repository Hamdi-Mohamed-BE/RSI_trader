"""Independent core-signal numerical checks and native evidence reconciliation."""
import itertools
import json
import math
import gzip
import hashlib
import numpy as np
import pandas as pd
import search as s


def oracle(frame,c):
    h,l,close=[frame[k].to_numpy(float) for k in ['high','low','close']]
    tr=np.maximum(h-l,np.maximum(abs(h-np.r_[close[0],close[:-1]]),abs(l-np.r_[close[0],close[:-1]])))
    ema=lambda n:pd.Series(close).ewm(span=n,adjust=False).mean().to_numpy()
    fast,slow,pull=ema(c['fast']),ema(c['slow']),ema(c['pullback'])
    touchlong=np.any(l[-c['lookback']-1:-1]<=pull[-c['lookback']-1:-1])
    touchshort=np.any(h[-c['lookback']-1:-1]>=pull[-c['lookback']-1:-1])
    side=0
    if fast[-1]>slow[-1] and fast[-1]>fast[-1-c['slope']] and touchlong and close[-1]>h[-2] and close[-1]>pull[-1]:side=1
    if fast[-1]<slow[-1] and fast[-1]<fast[-1-c['slope']] and touchshort and close[-1]<l[-2] and close[-1]<pull[-1]:side=-1
    returns=close[20:]/close[:-20]-1
    states=np.where(returns<-.005,0,np.where(returns>.005,2,1))
    counts=np.zeros((3,3),int)
    for a,b in zip(states[-254:-2],states[-253:-1]):counts[a,b]+=1
    row=counts[states[-1]];prob=(row+1)/(sum(row)+3)
    return dict(side=side,atr=float(tr[-c['atr']:].mean()),markov_allowed=bool(sum(row)>=20 and side*(prob[2]-prob[0])>0),prob=prob.tolist(),counts=counts.tolist())


def scalar(frame,c):
    rates=frame[['high','low','close']].to_numpy(float);sums=[0.];arrays=[]
    for n in [c['fast'],c['slow'],c['pullback']]:
        e=[];a=2/(n+1)
        for h,l,close in rates:e.append(close if not e else a*close+(1-a)*e[-1])
        arrays.append(e)
    for i,(h,l,close) in enumerate(rates):
        prev=rates[max(0,i-1),2];sums.append(sums[-1]+(h-l if i==0 else max(h-l,abs(h-prev),abs(l-prev))))
    f,slow,pull=arrays;z=len(rates)-1;side=0
    lt=any(rates[i,1]<=pull[i] for i in range(z-c['lookback'],z));st=any(rates[i,0]>=pull[i] for i in range(z-c['lookback'],z))
    if f[z]>slow[z] and f[z]>f[z-c['slope']] and lt and rates[z,2]>rates[z-1,0] and rates[z,2]>pull[z]:side=1
    if f[z]<slow[z] and f[z]<f[z-c['slope']] and st and rates[z,2]<rates[z-1,1] and rates[z,2]<pull[z]:side=-1
    def state(j):
        ret=rates[j,2]/rates[j-20,2]-1
        return 0 if ret<-.005 else 2 if ret>.005 else 1
    counts=np.zeros((3,3),int)
    for j in range(len(rates)-253,len(rates)-1):counts[state(j-1),state(j)]+=1
    row=counts[state(z)];prob=(row+1)/(sum(row)+3)
    return dict(side=side,atr=(sums[-1]-sums[-1-c['atr']])/c['atr'],markov_allowed=bool(sum(row)>=20 and side*(row[2]-row[0])>0),prob=prob.tolist(),counts=counts.tolist())


def main():
    bars=pd.read_csv(s.RAW/'data/USTEC-H1.csv.gz').set_index('time');windows=0
    for atr,lookback,slope in itertools.product([7,14,28],[1,2,3],[3,5,10]):
        for end in np.linspace(500,len(bars)-20,12,dtype=int):
            c=s.DEFAULT|dict(atr=atr,lookback=lookback,slope=slope)
            frame=bars.iloc[end-400:end].copy();a=oracle(frame,c);b=scalar(frame,c)
            assert a['side']==b['side'] and np.isclose(a['atr'],b['atr'],rtol=1e-10)
            assert a['counts']==b['counts'] and a['markov_allowed']==b['markov_allowed'] and np.allclose(a['prob'],b['prob'])
            assert sum(map(sum,a['counts']))==252 and np.isclose(sum(a['prob']),1)
            past_future=bars.iloc[:end+10].copy();past_future.iloc[end:]*=100
            assert oracle(past_future.iloc[end-400:end],c)==a
            mirror=frame.copy();centre=3*frame.high.max()
            mirror['close']=centre-frame.close;mirror['high']=centre-frame.low;mirror['low']=centre-frame.high
            m=oracle(mirror,c);assert m['side']==-a['side'] and np.isclose(m['atr'],a['atr'])
            windows+=1
    signals=pd.read_csv(s.OUT/'parity/0-signals.csv.gz');checked=0
    for row in signals.itertuples():
        i=bars.index.get_loc(row.signal_time);v=oracle(bars.iloc[i-399:i+1],s.DEFAULT)
        assert row.raw_side==v['side'] and np.isclose(row.atr,v['atr'],rtol=1e-10)
        assert 3600<=row.fill_time-row.signal_time<3901
        checked+=1
    assert s.effective_key(s.DEFAULT)==s.effective_key(s.DEFAULT|dict(offset=999,start=8,dist=99))
    assert s.effective_key(s.DEFAULT)!=s.effective_key(s.DEFAULT|dict(rr=1))
    plan=json.loads((s.ROOT/'run-config-search.json').read_text())
    assert s.sha(s.ROOT/'PROTOCOL.md')==plan['protocol_sha']
    assert s.sha(s.ROOT/'search.py')==plan['runner_sha']
    assert s.sha(s.EA/'SearchLogic.mqh')==plan['logic_sha']
    assert s.sha(s.EA/'RawCore.mqh')==plan['core_sha']
    audited=[];batches=0
    for p in sorted(s.OUT.glob('*/results.json')):
        manifest=json.loads((p.parent/'manifest.json').read_text());rows=json.loads(p.read_text())
        assert s.sha(p.parent/'SearchLogic.mqh')==manifest['logic']
        assert s.sha(p.parent/'RawCore.mqh')==manifest['core']
        expected='double Cases[]['+str(len(s.FIELDS))+']={\n'+',\n'.join('{'+','.join(str(c[f]) for f in s.FIELDS)+'}' for c in manifest['cases'])+'\n};\n#include "SearchLogic.mqh"\n'
        assert (p.parent/'Nasdaq Trend Search.mq5').read_text()==expected
        assert '0 errors, 0 warnings' in s.read(p.parent/'compile.log')
        reports=list(p.parent.glob('*.htm.gz'))+list(p.parent.glob('*.xml.gz'))
        assert len(reports)==1
        report_sha=hashlib.sha256(gzip.decompress(reports[0].read_bytes())).hexdigest()
        assert len(rows)==len(manifest['cases'])
        batches+=1
        for r in rows:
            assert r['parameters']==manifest['cases'][r['index']]
            assert r['parameters_sha']==s.digest(r['parameters']) and r['report_sha']==report_sha
            trades=s.read_trades(p.parent.name,r['index']);v=r['net']
            gain=sum(max(0,t['net_profit']) for t in trades);loss=-sum(min(0,t['net_profit']) for t in trades)
            assert len(trades)==v['trades'] and abs(sum(t['net_profit'] for t in trades)-v['net_profit'])<1e-6
            assert abs((gain/loss if loss else 99 if gain else 0)-v['profit_factor'])<1e-7
            assert all(abs(t['volume']-t['closed_volume'])<1e-7 and t['close_epoch']>=t['open_epoch'] for t in trades)
            assert all(abs(t['net_profit']-sum(t[k] for k in ['gross_profit','commission','swap','fee']))<.011 for t in trades)
            if r['clean']:assert all(t['actual_risk']>0 and t['requested_risk']>0 for t in trades)
            assert s.sha(p.parent/'Nasdaq Trend Search.ex5')==r['binary_sha']
            audited.append(dict(stage=r['stage'],index=r['index'],trades=len(trades),clean=r['clean']))
    v=dict(passed=True,numerical_causal_windows=windows,baseline_native_signals=checked,native_cases=len(audited),compiled_batches=batches,frozen_plan_unchanged=True,
        positions=sum(x['trades'] for x in audited),execution_rejected=sum(not x['clean'] for x in audited),
        limitation='Core logic and native H1 baseline oracle; not independent tick replay of every optional execution branch.',audited=audited)
    s.save(s.ROOT/'VERIFICATION.json',v)
    print(json.dumps({k:v for k,v in v.items() if k!='audited'},indent=2))


if __name__=='__main__':main()
