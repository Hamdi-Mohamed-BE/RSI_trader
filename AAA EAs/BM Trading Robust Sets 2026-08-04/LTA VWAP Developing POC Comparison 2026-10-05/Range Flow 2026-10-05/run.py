"""Isolated native range-only flow comparison; production remains untouched."""
from pathlib import Path
import importlib.util,json,os,sys,msvcrt,shutil
import pandas as pd
R=Path(__file__).resolve().parent;P=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
sp=importlib.util.spec_from_file_location('lta_range_parent',P/'run.py')
n=importlib.util.module_from_spec(sp);sp.loader.exec_module(n)
prior=json.loads((P/'build.json').read_text())
assert n.freeze()==prior['frozen']
assert n.sha(n.SOURCE.with_suffix('.ex5'))==prior['binary']
assert json.loads((P/'PARITY.json').read_text())['passed']
old_inputs=n.inputs;old_metrics=n.metrics
START='2023.10.05';END='2026.10.05'
CASES={
 'RANGE_OFF_1Y':dict(label='New flow: unchanged off-switch parity',mode=1,tf=5,safe=False,range_mode=0,start='2025.10.05',end=END),
 'RANGE_OFF_3Y':dict(label='New flow: ungated',mode=1,tf=5,safe=False,range_mode=0),
 'RANGE_DAILY_3Y':dict(label='New flow: daily Sideways only',mode=1,tf=5,safe=False,range_mode=1),
 'RANGE_COMBO_3Y':dict(label='New flow: daily Sideways + H1 ADX<20',mode=1,tf=5,safe=False,range_mode=2),
}
def inputs(c,tag):
 v=old_inputs(c,tag)
 v.update(InpRangeMode=str(c['range_mode']),InpMarkovReturnWindow='20',InpRangeADXPeriod='14',InpRangeADXMax='20.0')
 return v
def freeze():
 v=dict(window=[START,END],cases=CASES,production=prior['frozen']['production'],parent_frozen=prior['frozen'],
  source={p.name:n.sha(p) for p in sorted((R/'EA').glob('*.mq*'))},protocol=n.sha(R/'PROTOCOL.md'),runner=n.sha(Path(__file__)),
  exact_inputs={tag:inputs(c,tag) for tag,c in CASES.items()})
 for name,digest in v['production'].items():assert n.sha(n.B/name)==digest
 p=R/'frozen.json'
 if p.exists():assert json.loads(p.read_text())==v,'Frozen range research changed'
 else:n.save(p,v)
 return v
def metrics(ts,trace=None):
 m=old_metrics(ts,trace)
 days=(pd.Timestamp('2026-10-05')-pd.Timestamp('2023-10-05')).days
 m['trades_month']=len(ts)/(days/30.4375)
 m['trades_weekday']=len(ts)/len(pd.bdate_range('2023-10-05','2026-10-04'))
 return m
n.R=R;n.START=START;n.END=END;n.CASES=CASES
n.SOURCE=R/'EA/LTA Flow Research.mq5'
n.inputs=inputs;n.freeze=freeze;n.metrics=metrics
def parity():
 a=json.loads((P/'native/FLOW_M5/results.json').read_text())
 b=json.loads((R/'native/RANGE_OFF_1Y/results.json').read_text())
 keep=['position_id','open_epoch','close_epoch','last_deal','side','volume','open_price','close_price','sl','tp','net','gross','commission','swap','fee','partial','breakeven']
 assert [{k:t[k] for k in keep} for t in a['trades']]==[{k:t[k] for k in keep} for t in b['trades']], 'Ungated parity changed'
 assert a['native']==b['native']
 n.save(R/'PARITY.json',dict(passed=True,whole_positions=len(b['trades']),same_all_trade_times_prices_lots_and_costs=True,
  reference_binary=prior['binary'],new_binary=n.sha(n.SOURCE.with_suffix('.ex5'))))
 print('PARITY PASSED: unchanged ungated flow',flush=True)
if __name__=='__main__':
 with (P/'tester.lock').open('a+b') as lease:
  lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
  if sys.argv[1]=='compile':n.compile_ea()
  else:
   for tag in sys.argv[1:]:
    if tag!='RANGE_OFF_1Y':assert json.loads((R/'PARITY.json').read_text())['passed']
    n.run(tag)
    out=R/'native'/tag;began=json.loads((out/'owned-process.json').read_text())['started']
    for kind in ['gate','daily']+(['adx'] if CASES[tag]['range_mode'] else []):
     target=out/(kind+'.csv')
     if not target.exists():
      origin=n.COMMON/(tag+'-'+kind+'.csv')
      assert origin.exists() and origin.stat().st_mtime>=began-2
      shutil.copy2(origin,target)
    if tag=='RANGE_OFF_1Y':parity()
