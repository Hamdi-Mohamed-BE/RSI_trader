from pathlib import Path
import importlib.util,sys
from native import ROOT,save,load,ledger
spec=importlib.util.spec_from_file_location('ivb_proxy_evidence',ROOT.parent.parent/'Calyx Research Pipeline/calyx_pipeline.py')
audit=importlib.util.module_from_spec(spec);sys.modules[spec.name]=audit;spec.loader.exec_module(audit)
out={}
for row in load(ROOT/'SUMMARY.json'):
 name=row['stage'];print('AUDIT '+name,flush=True)
 payload=audit.audit_report(Path(row['report_path']),label='US100 IVB quote-count proxy '+name,paths=10000,block=5,tested_configurations=1,daily_loss_limit_pct=5,total_loss_limit_pct=10,extra_cost_per_trade=None,seed=20261002)
 d=ledger(row);assert payload['metrics']['trades']==len(d) and abs(payload['metrics']['net_profit']-d.net_profit.sum())<.1
 payload['native_equity_drawdown_pct']=row['stats']['equity_dd_pct']
 payload['promotion_block']='Quote-count proxy, NOT NQ order flow. Generated-tick delta is invalid validation evidence; primary real2026 and6m only. No pristine holdout, prospective demo or measured extra cost stress. DSR1 excludes broader prior idea selection. Not an FTMO forecast.'
 save(ROOT/'audit'/(name+'.json'),audit.json_safe(payload));out[name]=dict(verdict=payload['verdict'],gates=payload['gates'],metrics=payload['metrics'],bootstrap=payload['bootstrap'])
 print(name+' '+payload['verdict'],flush=True)
save(ROOT/'AUDIT SUMMARY.json',out)
