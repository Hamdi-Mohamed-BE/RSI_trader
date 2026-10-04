"""Independent checks from persisted native ledgers and admission audits."""
from pathlib import Path
import gzip,json,math,hashlib
from collections import defaultdict
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check_partial():
 bots=load(R/'bots.json');done=[];rows=0;entries=0
 for p in sorted((R/'native').glob('*/result.json')):
  z=load(p);key=z['tag'];folder=p.parent;s=z['stats']
  trades=json.loads(gzip.decompress((folder/'trades.json.gz').read_bytes()));net=np.array([t['net_profit'] for t in trades]);rows+=len(net)
  assert len(net)==s['trades'];assert abs(net.sum()-s['net'])<1e-6
  assert abs(net.sum()/100-s['return_pct'])<1e-6
  gp=sum(float(t['net_profit']) for t in trades if t['net_profit']>0);gl=-sum(float(t['net_profit']) for t in trades if t['net_profit']<0)
  assert (s['pf'] is None and gl==0) or abs(gp/gl-s['pf'])<1e-9
  assert s['win_pct']==(100*sum(t['net_profit']>0 for t in trades)/len(trades) if trades else 0) or abs(s['win_pct']-100*sum(t['net_profit']>0 for t in trades)/len(trades))<1e-9
  for t in trades:
   assert abs(t['gross_profit']+t['commission']+t['swap']-t['net_profit'])<.011
   assert '2025-10-02'<=t['open_time'][:10]<'2026-10-02'
   assert t['close_time']>=t['open_time'] and t['volume']>0
  manifest=load(folder/'manifest.json');b=bots[z['ea']]
  for k,v in b['inputs'].items():assert manifest['inputs'][k]==v
  if not z['original']:
   audit=pd.read_csv(folder/'audit.csv.gz');g=audit[audit.event=='gate'];e=audit[audit.event=='entry'];entries+=len(e)
   assert len(e)==len(trades) and (e.retcode==10009).all()
   enabled=z['variant']!='BASE';level=int(manifest['inputs']['InpStudyADXLevel']);mode=int(manifest['inputs']['InpStudyADXGate']);di=manifest['inputs']['InpStudyDI']=='true'
   expected=[]
   for row in g.itertuples():
    valid=bool(row.valid);admit=not enabled or valid
    if enabled and valid:
     if mode==1 and row.adx<level:admit=False
     if mode==2 and row.adx>level:admit=False
     if di and not ((row.direction>0 and row.plus_di>row.minus_di) or (row.direction<0 and row.minus_di>row.plus_di)):admit=False
    expected.append(int(admit))
    if valid:assert row.epoch>=row.bar_epoch+row.tf_seconds
   assert expected==g.allowed.astype(int).tolist()
   assert len(e)==sum(expected)
   # Chronological entry corresponds to a permitted gate, not a later indicator.
   allowed=g[g.allowed==1].reset_index(drop=True);e=e.reset_index(drop=True)
   assert (e.epoch>=allowed.epoch).all() and (e.direction==allowed.direction).all()
  done.append(key)
 for key,b in bots.items():
  assert sha(Path(b['original']))==b['original_sha'] and sha(Path(b['source']))==b['source_sha'] and sha(Path(b['setting']))==b['set_sha']
 result=dict(checked_cases=len(done),cases=done,ledger_trades_crosschecked=rows,entry_fills_crosschecked=entries,original_assets_unchanged=True,all_original_inputs_retained=True,closed_bar_filter_predicates_verified=True)
 (R/'VERIFICATION.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result
if __name__=='__main__':print(json.dumps(check_partial(),indent=2))
