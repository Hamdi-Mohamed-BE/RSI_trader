"""Frozen-history diagnostics; no forward probabilities, tuning or deployment."""
from pathlib import Path
import gzip,io,importlib.util,sys
import numpy as np
import pandas as pd
from native import ROOT,OUT,load,save,ledger,sha
ORIGINAL=ROOT.parent/'PBD Profile Raw 2026-10-02'
spec=importlib.util.spec_from_file_location('gold_validation_pipeline',ROOT.parent.parent/'Calyx Research Pipeline/calyx_pipeline.py')
pipe=importlib.util.module_from_spec(spec);sys.modules[spec.name]=pipe;spec.loader.exec_module(pipe)

def reference(name):
 row=next(x for x in load(ORIGINAL/'SUMMARY.json') if x['stage']==name)
 d=pd.read_csv(io.BytesIO(gzip.decompress((ORIGINAL/'native'/name/'0-trades.csv.gz').read_bytes())))
 return row,d
def entries(row,base=OUT):
 s=pd.read_csv(io.BytesIO(gzip.decompress((base/row['stage']/'0-signals.csv.gz').read_bytes())))
 return s[s.retcode==10009].sort_values('epoch').reset_index(drop=True)
def measure(row,d,base=OUT):
 d=d.sort_values('open_epoch').reset_index(drop=True);s=entries(row,base)
 assert len(d)==len(s) and (d.open_epoch.to_numpy()>=s.epoch.to_numpy()).all()
 assert (d.open_epoch.to_numpy()-s.epoch.to_numpy()<60).all()
 assert np.allclose(d.initial_sl,s.initial_sl) and np.allclose(d.volume,s.lots)
 adverse=np.maximum(0,d.actual_risk.to_numpy()-s.quoted_risk.to_numpy())
 return dict(n=len(d),adverse_entry_usd_sum=float(adverse.sum()),adverse_usd_per_lot_p50=float(np.quantile(adverse/d.volume,.5)),adverse_usd_per_lot_p95=float(np.quantile(adverse/d.volume,.95)),maximum_actual_risk_budget=float((d.actual_risk/d.requested_risk).max()))
def simple(pnl,initial=10000):
 pnl=np.asarray(pnl,dtype=float);gp=pnl[pnl>0].sum();gl=-pnl[pnl<0].sum()
 b=np.r_[initial,initial+np.cumsum(pnl)];pk=np.maximum.accumulate(b)
 return dict(trades=len(pnl),net=float(pnl.sum()),return_pct=float(pnl.sum()/initial*100),pf=float(gp/gl) if gl>0 else None,win_pct=float(np.mean(pnl>0)*100) if len(pnl) else None,closed_dd_pct=float(np.max((pk-b)/pk)*100),max_loss_streak=pipe.streaks(list(pnl))[1])
def path_stats(R):
 # Repricing/capacity/lot-floor effects are NOT simulated in this risk-unit replay.
 b=10000*np.cumprod(1+.01*R);prior=np.r_[10000,b[:-1]];pnl=prior*.01*R
 gp=pnl[pnl>0].sum();gl=-pnl[pnl<0].sum();pk=np.maximum.accumulate(np.r_[10000,b])[1:]
 return (float((b[-1]/10000-1)*100) if len(b) else 0,float(np.max((pk-b)/pk)*100) if len(b) else 0,float(gp/gl) if gl else np.inf)
def aggregate(values):
 a=np.asarray(values);pf=a[:,2];finite=pf[np.isfinite(pf)]
 return dict(paths=len(a),historical_profit_frequency_pct=float(np.mean(a[:,0]>0)*100),return_p05_pct=float(np.quantile(a[:,0],.05)),return_p50_pct=float(np.quantile(a[:,0],.5)),return_p95_pct=float(np.quantile(a[:,0],.95)),closed_dd_p50_pct=float(np.quantile(a[:,1],.5)),closed_dd_p95_pct=float(np.quantile(a[:,1],.95)),pf_p05=float(np.quantile(finite,.05)) if len(finite) else None,no_loss_paths=int(np.sum(~np.isfinite(pf))),not_a_forecast=True)
def risk_mc(d,seed=20261002,paths=10000):
 R=(d.net_profit/d.requested_risk).to_numpy();base=path_stats(R)
 assert abs(base[0]-d.net_profit.sum()/100)<1e-5,'Risk-unit reconstruction fails'
 out={};n=len(R)
 for block in [1,5,10]:
  rng=np.random.default_rng(seed+block);v=[]
  for _ in range(paths):
   starts=rng.integers(n,size=(n+block-1)//block);idx=((starts[:,None]+np.arange(block))%n).ravel()[:n]
   v.append(path_stats(R[idx]))
  out['block'+str(block)]=aggregate(v)
 rng=np.random.default_rng(seed+200);v=[];loss=[]
 for _ in range(paths):
  sample=rng.permutation(R);v.append(path_stats(sample));loss.append(pipe.streaks(list(sample))[1])
 out['order_reshuffle']=aggregate(v)|dict(longest_loss_run_p50=float(np.quantile(loss,.5)),longest_loss_run_p95=float(np.quantile(loss,.95)),return_should_be_order_invariant=True)
 for fraction in [.1,.2]:
  rng=np.random.default_rng(seed+int(fraction*100));v=[]
  for _ in range(paths):
   kept=np.sort(rng.choice(n,size=n-int(np.ceil(n*fraction)),replace=False));v.append(path_stats(R[kept]))
  out['remove'+str(int(fraction*100))+'pct']=aggregate(v)
 return out

def main():
 rows=load(ROOT/'SUMMARY.json');by={r['stage']:r for r in rows};parity=ledger(by['parity-1y']).sort_values(['open_epoch','close_epoch']).reset_index(drop=True)
 original,old=reference('XAUUSD-4-1y');old=old.sort_values(['open_epoch','close_epoch']).reset_index(drop=True)
 assert len(parity)==len(old)
 for c in old.columns:
  if c=='position_id':continue
  if pd.api.types.is_numeric_dtype(old[c]):assert np.allclose(parity[c],old[c],rtol=0,atol=1e-7),'Parity difference '+c
  else:assert list(parity[c])==list(old[c]),'Parity difference '+c
 assert sha(ROOT/'EA/Main.mqh')==sha(ORIGINAL/'EA/Main.mqh')
 save(ROOT/'PARITY.json',dict(positions=len(old),all_trade_fields_except_ids_identical=True,source_main_sha=sha(ROOT/'EA/Main.mqh')))
 measurement=measure(original,old,ORIGINAL/'native');shock=measurement['adverse_usd_per_lot_p95'];save(ROOT/'COST MEASUREMENT.json',measurement|dict(source='original last-year native150ms fills',extra_cost='one extra observed p95 adverse-entry-slippage USD per lot',not_future_spread_measurement=True))
 audits={};stress={}
 for stage in ['parity-1y','full-3y','full-5y','real-2026']:
  r=by[stage];d=ledger(r);print('AUDIT '+stage,flush=True)
  payload=pipe.audit_report(Path(r['report_path']),label='Frozen PBD Gold '+stage,paths=10000,block=5,tested_configurations=12,daily_loss_limit_pct=5,total_loss_limit_pct=10,extra_cost_per_trade=None,seed=20261002)
  assert payload['metrics']['trades']==len(d) and abs(payload['metrics']['net_profit']-d.net_profit.sum())<.1
  payload['native_equity_dd_pct']=r['stats']['equity_dd_pct'];payload['promotion_block']='Selection-biased history, proxy volume, no pristine holdout or prospective demo; closed-path MC not FTMO probability.'
  save(ROOT/'audit'/(stage+'.json'),pipe.json_safe(payload));audits[stage]=dict(verdict=payload['verdict'],metrics=payload['metrics'],gates=payload['gates'],bootstrap=payload['bootstrap'])
  stress[stage]=dict(additional_measured_p95_entry_friction=simple(d.net_profit-shock*d.volume),double_recorded_commission=simple(d.net_profit+d.commission),measured_entry_friction_plus_double_commission=simple(d.net_profit-shock*d.volume+d.commission))
 save(ROOT/'AUDIT SUMMARY.json',audits);save(ROOT/'MEASURED COST STRESS.json',stress)
 mc={}
 for stage in ['full-5y','parity-1y','real-2026']:
  print('RISK-UNIT MC '+stage,flush=True);mc[stage]=risk_mc(ledger(by[stage]))
 save(ROOT/'RISK-UNIT MC.json',mc)
 raw={stage:bool(r['stats']['net']>0 and r['stats']['pf']>=1.15 and r['stats']['trades']>=30) for stage,r in by.items() if stage in ['full-3y','full-5y']}
 stat_gates=['minimum_30_closed_trades','positive_locked_return','profit_factor_above_1','bootstrap_return_p05_positive','bootstrap_pf_p05_above_1','deflated_sharpe_95pct','recent_half_pf_above_1','two_of_three_subperiods_profitable']
 strong={stage:all(a['gates'][g] for g in stat_gates) for stage,a in audits.items()}
 execution=all(by[stage]['stats']['net']>0 and by[stage]['stats']['pf']>1 for stage in ['delay500-1y','delay500-6m'])
 costs=all(v['additional_measured_p95_entry_friction']['net']>0 and v['additional_measured_p95_entry_friction']['pf'] is not None and v['additional_measured_p95_entry_friction']['pf']>1 for stage,v in stress.items())
 decision=dict(status='NOT VALIDATED',historical_raw_gates=raw,statistical_gates=strong,native500ms_gate=execution,measured_additional_entry_friction_gate=costs,controls_required_before_any_promotion=True,controls_started=False,controls_stop_reason='Raw3y/5y failure' if not all(raw.values()) else 'Control advantage not yet established; no promotion',live_eligible=False,optimisation_started=False,active_eas_changed=False,prospective_holdout_available=False,true_exchange_volume_available=False)
 save(ROOT/'DECISION.json',decision);print(decision,flush=True)
if __name__=='__main__':main()
