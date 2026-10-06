"""Read-only independent consistency audit of frozen experiment artifacts."""
from pathlib import Path
import importlib.util,json,hashlib
import pandas as pd
import numpy as np
R=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
sp=importlib.util.spec_from_file_location('model_checks',R/'model.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
manifest=json.loads((R/'model-frozen.json').read_text());mdata=json.loads((R/'MODEL.json').read_text())
assert sha(R/'PROTOCOL.md')==manifest['protocol_sha256']
assert sha(R/'model.py')==manifest['model_source_sha256']
assert sha(R/'forecasts.csv')==mdata['forecast_sha256']
assert sha(R/'EA/Forecasts.mqh')==mdata['embedded_sha256']
raw=pd.read_csv(R/'data/USTEC-M5.csv.gz');all_sessions=m.sessions(raw);forecasts=m.make_forecasts(all_sessions)
# Historical prefix-only construction must equal full-history construction on every earlier feature.
prefix_cut=int(pd.Timestamp('2024-01-01',tz='UTC').timestamp())
prefix=m.make_forecasts(m.sessions(raw[raw.time<prefix_cut]))
past=forecasts.date<'2024-01-01'
np.testing.assert_array_equal(prefix.loc[prefix.date<'2024-01-01',m.FEATURES].to_numpy(),forecasts.loc[past,m.FEATURES].to_numpy())
assert np.all(forecasts.feature_date<forecasts.date)
assert len(m.FEATURES)==15 and len(set(m.FEATURES))==15
# ER definition sanity: monotonic path=1, returning zig-zag=0; both under NY DST.
synthetic=[]
for day,monotonic in [('2020-01-06',True),('2020-07-06',False)]:
 times=pd.date_range(day+' 09:30',periods=78,freq='5min',tz='America/New_York')
 prices=100+np.arange(1,79) if monotonic else np.tile([101.,100.],39)
 prev=100.
 for t,c in zip(times,prices):
  synthetic.append(dict(time=int(t.timestamp()),open=prev,high=max(prev,c),low=min(prev,c),close=c));prev=c
syn=m.sessions(pd.DataFrame(synthetic))
assert syn.er.iloc[0]==1 and syn.er.iloc[1]==0
training=forecasts[(forecasts.date<'2024-01-01')&forecasts.target_er.notna()]
assert abs(training.target_er.median()-manifest['training_target_er_median'])<1e-12
w=json.loads((R/'weights.json').read_text());forecast=pd.read_csv(R/'forecasts.csv')
X=(forecast[m.FEATURES].to_numpy()-np.asarray(w['scaler_mean']))/np.asarray(w['scaler_scale'])
p=1/(1+np.exp(-(X@np.asarray(w['coef'])+w['intercept'])))
assert np.max(np.abs(p-forecast.probability))<1e-12
assert np.array_equal(p>=.5,forecast.ml_allow)
assert json.loads((R/'PARITY.json').read_text())['exact']
frozen=json.loads((R/'native-frozen.json').read_text())
for rel,digest in frozen['production'].items():assert sha(R.parent/rel)==digest,'Production file changed'
for name,digest in frozen['research'].items():assert sha(R/'EA'/name)==digest
checks=[]
paths=sorted((R/'native').glob('*/results.json'))
assert len(paths)==10,'Incomplete comparison'
for path in paths:
 x=json.loads(path.read_text());n=x['native'];ts=x['trades']
 assert len(ts)==n['trades']
 assert abs(sum(t['net_profit'] for t in ts)-n['net_profit'])<.021
 assert all(pd.Timestamp(t['open_time'])<pd.Timestamp(t['close_time']) for t in ts)
 if not x['original']:
  assert x['counters']['deal_rows_audited']==2*len(ts),'Not one full entry + exit per position'
  assert x['counters']['blocked']>=0
  gates=pd.read_csv(path.parent/'gates.csv')
  assert np.all(gates.available<gates.epoch)
  if x['mode']==1:assert all(t['ml_allow'] for t in ts)
  if x['mode']==2:assert all(t['lag_er_allow'] for t in ts)
 assert all(t['probability']>=0 and t['probability']<=1 for t in ts)
 checks.append(dict(case=x['tag'],positions=len(ts),deal_audit=x['counters']['deal_rows_audited'],equity_dd=n['equity_dd_pct'],quality=n['history_quality']))
v=dict(ok=True,checks=dict(fifteen_features=True,ER_monotonic_and_zigzag_sanity=True,NY_DST_sessions_correct=True,prefix_history_identical=True,future_mutation_identical=mdata['checks']['future_price_mutation_prior_features_unchanged'],scaling_and_coefficients_replay=True,training_median_only=True,all_forecasts_past_only=True,
 exact_production_parity=True,native_deal_reconciliation=True,production_and_BAT_hashes_unchanged=True,all_gate_logic_reconciled=True),runs=checks)
(R/'verification.json').write_text(json.dumps(v,indent=2));print(json.dumps(v,indent=2))
