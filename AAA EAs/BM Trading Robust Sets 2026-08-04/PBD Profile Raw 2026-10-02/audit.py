"""Raw diagnostics only. No portfolio pass/payout forecast or parameter selection."""
from pathlib import Path
import importlib.util,sys
from native import ROOT,save,load,ledger
spec=importlib.util.spec_from_file_location('pbd_evidence_pipeline',ROOT.parent.parent/'Calyx Research Pipeline/calyx_pipeline.py')
audit=importlib.util.module_from_spec(spec);sys.modules[spec.name]=audit;spec.loader.exec_module(audit)
out={}
for row in load(ROOT/'SUMMARY.json'):
 if not row['stage'].endswith('1y'):continue
 name=row['stage'];print('AUDIT '+name,flush=True)
 payload=audit.audit_report(Path(row['report_path']),label='PBD CFD proxy raw '+name,paths=10000,block=5,tested_configurations=12,daily_loss_limit_pct=5,total_loss_limit_pct=10,extra_cost_per_trade=None,seed=20261002)
 d=ledger(row);assert payload['metrics']['trades']==len(d) and abs(payload['metrics']['net_profit']-d.net_profit.sum())<.1
 payload['native_equity_drawdown_pct']=row['stats']['equity_dd_pct']
 payload['promotion_block']='No independent volume-at-price, pristine holdout, matched-random control, measured incremental-cost stress or prospective demo. DSR12 adjusts current asset/module candidates only; prior volume-profile studies and broader idea-selection bias remain. Not FTMO predictions.'
 # Illustrative additional friction of 0.05R, NOT calibrated to this broker.
 stressed=d.net_profit-.05*d.requested_risk;gp=float(stressed[stressed>0].sum());gl=float(-stressed[stressed<0].sum())
 payload['illustrative_005R_extra_friction']=dict(net=float(stressed.sum()),return_pct=float(stressed.sum()/100),pf=gp/gl if gl else None,not_broker_measured=True)
 save(ROOT/'audit'/(name+'.json'),audit.json_safe(payload))
 out[name]=dict(verdict=payload['verdict'],gates=payload['gates'],metrics=payload['metrics'],bootstrap=payload['bootstrap'],illustrative_stress=payload['illustrative_005R_extra_friction'])
 print(name+' '+payload['verdict'],flush=True)
save(ROOT/'AUDIT SUMMARY.json',out)
