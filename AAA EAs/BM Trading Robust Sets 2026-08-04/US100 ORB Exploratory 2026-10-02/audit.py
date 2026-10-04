"""Existing evidence gates applied after configuration lock; no retuning."""
from pathlib import Path
import importlib.util,json,sys
from native import ROOT,save,load,ledger
path=ROOT.parent.parent/'Calyx Research Pipeline/calyx_pipeline.py'
spec=importlib.util.spec_from_file_location('orb_evidence_pipeline',path);audit=importlib.util.module_from_spec(spec);sys.modules[spec.name]=audit;spec.loader.exec_module(audit)
def main():
 summary=load(ROOT/'SUMMARY.json');trials=summary['trials']['total'];out={}
 for name in ('validation','locked-1y','full-3y','full-5y'):
  row=summary['results'][name]
  print('AUDIT '+name,flush=True)
  payload=audit.audit_report(Path(row['report_path']),label='US100 ORB exploratory '+name,paths=10000,block=5,tested_configurations=trials,daily_loss_limit_pct=5,total_loss_limit_pct=10,extra_cost_per_trade=None,seed=20261002)
  d=ledger(row)
  assert payload['metrics']['trades']==len(d) and abs(payload['metrics']['net_profit']-d.net_profit.sum())<.1
  payload['exploratory_after_raw_failure']=True
  payload['native_equity_drawdown_pct']=row['stats']['equity_dd_pct']
  payload['locked_parameters']=summary['primary']['parameters']
  payload['promotion_block']='No pristine untouched data holdout, no broker-measured incremental-cost stress or prospective forward demo. Internal closed-P&L breach probabilities are not an FTMO forecast.'
  save(ROOT/'audit'/(name+'.json'),audit.json_safe(payload));(ROOT/'audit'/(name+'.md')).write_text(audit.markdown(payload),encoding='utf-8')
  out[name]=dict(verdict=payload['verdict'],gates=payload['gates'],metrics=payload['metrics'],bootstrap=payload['bootstrap'])
  print(name+' '+payload['verdict'],flush=True)
 save(ROOT/'AUDIT SUMMARY.json',out)
if __name__=='__main__':main()
