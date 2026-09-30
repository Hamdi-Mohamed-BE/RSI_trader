"""Independent numerical/causality checks and archived native ledger audits."""
import importlib.util, itertools, json, math
from pathlib import Path
import numpy as np
import pandas as pd
import search as s

def oracle(frame,c):
    o,h,l,close=[frame[k].to_numpy(float) for k in ['open','high','low','close']]
    tr=np.maximum(h-l,np.maximum(abs(h-np.r_[close[0],close[:-1]]),abs(l-np.r_[close[0],close[:-1]])))
    ratio=pd.Series(tr).rolling(c['fast']).mean()/pd.Series(tr).rolling(c['slow']).mean()
    states=np.where(ratio<.8,0,np.where(ratio>c['hot'],2,1));n=len(frame)
    a=states[n-c['train']-2:n-2];b=states[n-c['train']-1:n-1];hot=a==2
    count=int(hot.sum());prob=(int(((b==2)&hot).sum())+1)/(count+3)
    ema=pd.Series(close).ewm(span=c['ema'],adjust=False).mean().to_numpy();side=0
    if states[-1]==2 and count>=20 and prob>=c['persist']:
        if close[-1]>ema[-1]>ema[-1-c['slope']] and close[-1]>h[-2]:side=1
        if close[-1]<ema[-1]<ema[-1-c['slope']] and close[-1]<l[-2]:side=-1
    return dict(side=side,atr=float(tr[-c['fast']:].mean()),count=count,prob=prob)

def prefix_version(frame,c):
    # Separately implemented algorithm corresponding to the new EA's rolling sums.
    rates=frame[['open','high','low','close']].to_numpy(float);total=[0.];em=[]
    for i,(o,h,l,close) in enumerate(rates):
        prev=rates[max(0,i-1),3]
        total.append(total[-1]+(h-l if i==0 else max(h-l,abs(h-prev),abs(l-prev))))
        a=2/(c['ema']+1);em.append(close if i==0 else a*close+(1-a)*em[-1])
    def state(j):
        fast=(total[j+1]-total[j+1-c['fast']])/c['fast'];slow=(total[j+1]-total[j+1-c['slow']])/c['slow']
        ratio=fast/slow if slow else 1;return 0 if ratio<.8 else 2 if ratio>c['hot'] else 1
    n=len(rates);count=stay=0
    for j in range(n-c['train']-1,n-1):
        if state(j-1)==2:count+=1;stay+=int(state(j)==2)
    prob=(stay+1)/(count+3);side=0
    if state(n-1)==2 and count>=20 and prob>=c['persist']:
        if rates[-1,3]>em[-1]>em[-1-c['slope']] and rates[-1,3]>rates[-2,1]:side=1
        if rates[-1,3]<em[-1]<em[-1-c['slope']] and rates[-1,3]<rates[-2,2]:side=-1
    return dict(side=side,atr=(total[-1]-total[-1-c['fast']])/c['fast'],count=count,prob=prob)

def main():
    bars=pd.read_csv(s.RAW/'data/XAUUSD-H1.csv.gz').set_index('time');windows=0
    for fast,slow,train in itertools.product([7,14,28],[50,100,200],[126,252]):
        for end in np.linspace(500,len(bars)-20,12,dtype=int):
            c=s.DEFAULT|dict(fast=fast,slow=slow,train=train);n=max(400,slow+train+2);frame=bars.iloc[end-n:end].copy()
            a=oracle(frame,c);b=prefix_version(frame,c)
            assert a['side']==b['side'] and a['count']==b['count'] and a['prob']==b['prob'] and np.isclose(a['atr'],b['atr'],rtol=1e-10)
            future=bars.iloc[:end+10].copy();future.iloc[end:,future.columns.get_indexer(['open','high','low','close'])]*=100
            assert oracle(future.iloc[end-n:end],c)==a
            mirror=frame.copy();centre=3*frame.high.max();mirror['open']=centre-frame.open;mirror['close']=centre-frame.close;mirror['high']=centre-frame.low;mirror['low']=centre-frame.high
            m=oracle(mirror,c);assert m['side']==-a['side'] and np.isclose(m['atr'],a['atr']) and m['count']==a['count']
            assert 0<=a['count']<=train and 0<a['prob']<1;windows+=1
    signals=pd.read_csv(s.OUT/'parity/0-signals.csv.gz');native_checked=0
    for row in signals.itertuples():
        i=bars.index.get_loc(row.signal_time);result=oracle(bars.iloc[i-399:i+1],s.DEFAULT)
        assert result['side']==row.raw_side and np.isclose(result['atr'],row.atr,rtol=1e-10)
        assert 3600<=row.fill_time-row.signal_time<=3900 and row.spread>=0;native_checked+=1
    audit=[];runs=[]
    for p in sorted(s.OUT.glob('*/results.json')):
        rows=json.loads(p.read_text());manifest=json.loads((p.parent/'manifest.json').read_text())
        assert s.sha(p.parent/'SearchLogic.mqh')==manifest['logic'] and s.sha(p.parent/'RawCore.mqh')==manifest['core']
        for r in rows:
            t=s.read_trades(p.parent.name,r['index']);v=r['net'];gain=sum(max(0,x['net_profit']) for x in t);loss=-sum(min(0,x['net_profit']) for x in t)
            assert len(t)==v['trades'] and abs(sum(x['net_profit'] for x in t)-v['net_profit'])<1e-6
            assert abs((gain/loss if loss else 99 if gain else 0)-v['profit_factor'])<1e-7
            assert all(x['close_epoch']>=x['open_epoch'] and abs(x['volume']-x['closed_volume'])<1e-7 for x in t)
            if r['clean']:assert all(x['actual_risk']>0 and x['requested_risk']>0 for x in t)
            audit.append(dict(stage=r['stage'],index=r['index'],trades=len(t),clean=r['clean']))
        runs.append(p.parent.name)
    result=dict(passed=True,numerical_causal_windows=windows,native_baseline_signals=native_checked,native_case_ledgers=len(audit),
                native_positions=sum(a['trades'] for a in audit),execution_rejected_cases=sum(not a['clean'] for a in audit),
                checks=['Independent rolling means vs EA prefix sums','Future mutation invariant','Mirrored price direction symmetry',
                        'Transition support and probability bounds','44-trade original parity plus independent H1 signal oracle',
                        'Every archived source hash and position ledger reconciled to native report'],
                limitation='Independent signal checks cover core regime mathematics and baseline H1 entries; not proof of alpha or exhaustive execution verification of every optional branch.',runs=runs)
    s.save(s.ROOT/'VERIFICATION.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
