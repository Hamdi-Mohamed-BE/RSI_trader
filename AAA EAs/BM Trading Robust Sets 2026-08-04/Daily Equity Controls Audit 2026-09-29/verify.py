"""Independent accounting and source/price coverage checks on saved results."""
from pathlib import Path
import json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
    checks=[]
    for r in read(ROOT/'RESULTS.json'):
        z=np.load(ROOT/f'{r["id"]}.npz');m=r['metrics'];logs=z['logs'];tr=z['trades']
        assert len(logs)==m['trades']
        assert len(set(logs[:,0]))==len(logs)
        assert np.all(logs[:,5]<=50.+1e-6)
        assert np.all(logs[:,2]>=logs[:,1])
        if m['open_at_end']==0:assert abs(10000+logs[:,4].sum()-m['balance'])<1e-6,r['id']
        if r['config']['cap']:assert m['max_open_risk']<=250.+1e-6,r['id']
        assert not np.isnan(logs).any()
        checks.append(r['id'])
    rate_data={s:np.load(ROOT/f'{s}-M1.npz')['rates'] for s in read(ROOT/'AUDIT.json')['symbols']}
    coverage={}
    for tag in ('','recent-'):
        rr=read(ROOT/f'{tag}ROWS.json');dist=[];examples=[]
        for r in rr:
            a=rate_data[r['symbol']];sgn=1 if r['side']=='Long' else -1
            for kind,t,fill in [('open',r['op'],r['open_price']),('close',r['cl'],r['close_price'])]:
                ix=np.searchsorted(a['time'],t,side='right')-1
                bar=a[ix];ask=(kind=='open' and sgn>0) or (kind=='close' and sgn<0)
                point=.001 if r['symbol'] in ('XAUUSD','XAGUSD','USDJPY') else .00001 if r['symbol']=='EURUSD' else .01
                lo=bar['low']+(bar['spread']*point if ask else 0)
                hi=bar['high']+(bar['spread']*point if ask else 0)
                outside=max(lo-fill,fill-hi,0)/max(abs(r['open_price']-r['stop']),1e-12)
                dist.append(outside)
                if outside>.25:examples.append(dict(ea=r['key'],number=r['number'],kind=kind,outside_r=outside))
        coverage[tag or 'common']=dict(quotes=len(dist),outside_025R=len(examples),outside_r_p95=float(np.quantile(dist,.95)),max_outside_r=float(max(dist)),examples=sorted(examples,key=lambda x:-x['outside_r'])[:15])
    old=read(ROOT.parent/'FTMO vs Stellar Instant Study 2026-09-28/AUDIT.json')
    hashes=[]
    for path,expected in old['source_hashes'].items():
        p=Path(path)
        if p.exists():hashes.append(dict(file=path,unchanged=hashlib.sha256(p.read_bytes()).hexdigest()==expected))
    result=dict(accounting_passed=len(checks),all_saved_cases=checks,quote_coverage=coverage,recent_source_hashes=hashes)
    (ROOT/'CHECKS.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='all_saved_cases'},indent=2))

if __name__=='__main__':main()
