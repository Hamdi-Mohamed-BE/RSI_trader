"""Extend the exact tested AND variant only; no production or EA edits."""
from pathlib import Path
import importlib.util,json,os,sys,hashlib
import pandas as pd
R=Path(__file__).resolve().parent;P=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
sp=importlib.util.spec_from_file_location('lta_extension',P/'run.py');n=importlib.util.module_from_spec(sp);sp.loader.exec_module(n)
prior=json.loads((P/'build.json').read_text())
assert n.freeze()==prior['frozen'],'Prior experiment source or settings changed'
assert n.sha(n.SOURCE.with_suffix('.ex5'))==prior['binary']
assert json.loads((P/'PARITY.json').read_text())['passed']
old_metrics=n.metrics
CASE='AND_M5_3Y'
START='2023.10.05';END='2026.10.05'
def freeze():
 v=dict(window=[START,END],source_reference=str(P),source_binary_sha256=n.sha(n.SOURCE.with_suffix('.ex5')),prior_frozen=prior['frozen'],
  protocol=n.sha(R/'PROTOCOL.md'),runner=n.sha(Path(__file__)),inputs=n.inputs(n.CASES[CASE],CASE))
 p=R/'frozen.json'
 if p.exists():assert json.loads(p.read_text())==v
 else:n.save(p,v)
 return v
def metrics(ts,trace=None):
 m=old_metrics(ts,trace)
 days=(pd.Timestamp(END.replace('.','-'))-pd.Timestamp(START.replace('.','-'))).days
 m['trades_month']=len(ts)/(days/30.4375)
 m['trades_weekday']=len(ts)/len(pd.bdate_range(START.replace('.','-'),pd.Timestamp(END.replace('.','-'))-pd.Timedelta(days=1)))
 return m
n.R=R;n.START=START;n.END=END
n.CASES={CASE:dict(label='Existing LTA M5 signal AND new VWAP/developing POC flow',mode=2,tf=5,safe=False)}
n.freeze=freeze;n.metrics=metrics
n.save(R/'build.json',dict(binary=prior['binary'],frozen=freeze(),reuse_prior_verified_compile=True,compiler_tail=prior['compiler_tail']))
if __name__=='__main__':
 result=n.run(CASE,reanalyze='--analyze' in sys.argv)
 n.save(R/'RESULTS.json',result)
 print('COMPLETE exact AND variant over 3 years; production unchanged',flush=True)
