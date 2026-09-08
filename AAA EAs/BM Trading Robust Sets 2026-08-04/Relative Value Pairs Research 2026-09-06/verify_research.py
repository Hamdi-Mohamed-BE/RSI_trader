"""Independent invariants, causal-prefix checks, and native ledger reconciliation."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
from research import ROOT,BASE,PAIRS,load_pair,features,run_config,broad_configs,params

def main():
    messages=[]
    assert len(list(broad_configs()))==900
    space=list(broad_configs())
    assert {c['tf'] for c in space}=={5,15,30,60,240}
    assert {c['rr'] for c in space if c['exit']<7}=={.5,1.,1.5,2.,3.,4.,6.}
    assert {c['session'] for c in space}==set(range(6))
    assert params(BASE)[-1]==1.
    for pair in PAIRS:
        d,m,spec=load_pair(pair)
        assert d.index.is_unique and d.index.is_monotonic_increasing
        assert np.all(m[:,5:7]>0)
        for tf in (5,15,30,60,240):
            for model in (0,1):
                c=dict(BASE,tf=tf,model=model)
                f=features(d,tf,64,model)
                # Removing the future must not change any earlier feature, even
                # when the current TF bar becomes incomplete after truncation.
                cut=int(np.searchsorted(m[:,0],pd.Timestamp('2024-07-15 13:35',tz='UTC').timestamp()))
                prefix=features(d.iloc[:cut],tf,64,model)
                np.testing.assert_allclose(f[:cut],prefix,rtol=1e-10,atol=1e-10,equal_nan=True)
                if tf==15:
                    r,t,e=run_config(m,f,spec,c,'train')
                    assert len(t)==r['trades']
                    assert abs(t[:,9].sum()/10000*100-r['return_pct'])<1e-7
                    assert np.all(t[:,1]>=t[:,0])
                    assert np.all(t[1:,0]>t[:-1,1])
                    assert abs(np.prod(1+t[:,10])*10000-(10000+t[:,9].sum()))<1e-5
                    assert np.all(t[:,7]>=spec[0,1]) and np.all(t[:,8]>=spec[1,1])
        messages.append(f'PASS {pair}: 10 timeframe/model causal-prefix comparisons; synchronized unique bars; positive cost floors; basket cash/returns and broker min lots')
    for p in sorted((ROOT/'Native').glob('*/result.json')):
        r=json.loads(p.read_text());b=pd.read_csv(p.parent/'baskets.csv')
        from native import SOURCE,config
        dates={'smoke':('2025.09.01','2025.10.01'),'test':('2025.09.01','2026.09.01'),'full':('2023.09.01','2026.09.01'),'recent':('2026.01.01','2026.09.01')}
        start,end=dates[r['stage']];mode=r['execution_mode']
        fingerprint=hashlib.sha256((SOURCE.read_text()+json.dumps(config(r['pair'],r['config'],p.parent.name),sort_keys=True)+start+end+str(r['model'])+('random-1' if mode==-1 else f'fixed-{mode}')).encode()).hexdigest()
        assert fingerprint==r['fingerprint'],'Source/preset changed after accepted native run'
        assert abs(b.net.sum()-r['net_profit'])<=.06
        assert (b.exit_fills==b.entry_fills).all()
        assert r['execution_mode'] in (-1,250) and r['config']
        assert r['feature_comparisons']>0
        assert max(r['feature_max_absolute_errors'].values())<1e-6
        if r['history_quality_pct']<90:
            assert r['model']==4 and r['status']=='invalid-data'
            messages.append(f'FLAG {p.parent.name}: {r["history_quality_pct"]}% history quality; cash/features reconcile but insufficient full-window recorded-tick coverage; NOT accepted as full validation')
            continue
        messages.append(f'PASS {p.parent.name}: native cash reconciled, both fills accounted for, causal features match Python, execution mode {r["execution_mode"]} verified')
    (ROOT/'VERIFICATION.txt').write_text('\n'.join(messages)+'\n',encoding='utf-8')
    print('\n'.join(messages))

if __name__=='__main__':main()
