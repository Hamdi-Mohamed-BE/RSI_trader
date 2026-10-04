"""Descriptive circular block bootstrap; not a search-corrected validation test."""
from pathlib import Path
import gzip,json
import numpy as np
R=Path(__file__).resolve().parent
def bootstrap(v):
 n=len(v)
 if n<20:return dict(trades=n,eligible=False,reason='Too few trades for a useful block-bootstrap interval; do not interpret small-sample PF as reliable.')
 rng=np.random.default_rng(20261003);block=5;paths=10000
 starts=rng.integers(0,n,size=(paths,(n+block-1)//block));indices=(starts[:,:,None]+np.arange(block))%n
 sample=v[indices.reshape(paths,-1)[:,:n]];gp=np.where(sample>0,sample,0).sum(axis=1);gl=-np.where(sample<0,sample,0).sum(axis=1)
 pf=np.divide(gp,gl,out=np.full(paths,np.nan),where=gl>0);finite=pf[np.isfinite(pf)];net=sample.sum(axis=1)
 return dict(paths=paths,block=block,seed=20261003,pf_p05=float(np.quantile(finite,.05)) if len(finite) else None,pf_p95=float(np.quantile(finite,.95)) if len(finite) else None,net_cash_p05=float(np.quantile(net,.05)),net_cash_p95=float(np.quantile(net,.95)),positive_net_path_fraction=float((net>0).mean()),no_loss_paths=int((gl==0).sum()),caveat='Resampled historical net cash amounts, not fresh dynamic-sizing/equity simulations; not multiple-search adjusted or untouched validation.')
def main():
 decisions=json.loads((R/'DECISION.json').read_text());tags=sorted({d[k] for d in decisions for k in ('baseline','selected','highest_filtered_pf')});out={}
 for tag in tags:
  trades=json.loads(gzip.decompress((R/'native'/tag/'trades.json.gz').read_bytes()));out[tag]=bootstrap(np.array([x['net_profit'] for x in trades]))
 (R/'UNCERTAINTY.json').write_text(json.dumps(out,indent=2,allow_nan=False),encoding='utf-8');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
