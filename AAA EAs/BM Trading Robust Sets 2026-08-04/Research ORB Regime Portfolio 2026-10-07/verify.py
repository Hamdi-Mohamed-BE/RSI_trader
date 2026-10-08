"""Independent ledger, chronology, sizing and HTML integrity checks."""
from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,importlib.util,json,math,sys
import pandas as pd,numpy as np
import runner as r,report as p,evidence as a
from bs4 import BeautifulSoup
R=r.R;checks=0
def check(value,message):
 global checks
 assert value,message;checks+=1
def ny(epoch):return pd.Timestamp(epoch,unit='s',tz='UTC').tz_convert('America/New_York')
def main():
 print('Independent verification started',flush=True)
 freeze_path=R/'CORRECTED FROZEN.json' if (R/'CORRECTED FROZEN.json').exists() else R/'FROZEN.json'
 frozen=r.load(freeze_path);rows=r.load(R/'EVALUATION.json');audits=r.load(R/'AUDIT.json');windows=r.load(R/'WINDOWS.json')
 if 'parent_freeze_sha256' in frozen:
  check(frozen['parent_freeze_sha256']==r.sha(R/'FROZEN.json'),'Original freeze modified')
  check(frozen['symbols']==r.load(R/'FROZEN.json')['symbols'],'Parameters changed after bug discovery')
 check(frozen['engine_sha256']==r.sha(R/'engine.mq5'),'Source changed after freeze')
 check(frozen['config_sha256']==r.sha(R/'config.json'),'Plan changed after freeze')
 spec=importlib.util.spec_from_file_location('split_policy',R.parent.parent/'Calyx Research Pipeline/data_split.py');split=importlib.util.module_from_spec(spec);spec.loader.exec_module(split)
 planned=split.research_split(r.CONFIG['development'][0],r.CONFIG['end_exclusive'])
 for stage in ['development','validation','oos']:check([planned[stage]['start'],planned[stage]['end_exclusive']]==r.CONFIG[stage],'Central split mismatch')
 evaluated=0;totaltrades=0;decisionchecks=0;lastquotes={};carried=[]
 for out in (R/'native').iterdir():
  if not (out/'results.json').exists() or (freeze_path.name.startswith('CORRECTED') and not out.name.startswith('timing-v2-')):continue
  print('Verifying native batch: '+out.name,flush=True)
  manifest=r.load(out/'manifest.json');records=r.load(out/'results.json');check(len(records)==len(manifest['cases']),'Missing native pass')
  check(r.sha(out/'OrbSearch.ex5')==records[0]['binary_sha256'],'Binary hash mismatch')
  if manifest['start']==r.CONFIG['oos'][0]:check((out/'manifest.json').stat().st_mtime>=freeze_path.stat().st_mtime-1,'Evaluation started before corrected freeze')
  for row in records:
   evaluated+=1;check(row['parameters']==manifest['cases'][row['index']],'Setting mismatch')
   deals=pd.read_csv(out/(str(row['index'])+'-deals.csv.gz'));ledger=row['trades']
   # Independent vectorised reconciliation, not the runner's reconstruction.
   cash=deals[['profit','commission','swap','fee']].sum(axis=1).groupby(deals.position_id).sum()
   ins=deals[deals.entry==0];outs=deals[deals.entry==1]
   check(set(deals.entry).issubset({0,1}),'Unexpected reversal deal type')
   check(not ins.position_id.duplicated().any(),'Multiple entries per position')
   iv=ins.groupby('position_id').volume.sum();ov=outs.groupby('position_id').volume.sum()
   check(set(iv.index)==set(ov.index)==set(cash.index),'Position incomplete')
   check(np.allclose(iv.sort_index().to_numpy(dtype=float),ov.sort_index().to_numpy(dtype=float),atol=1e-7),'Position volume not fully closed')
   native_nets={int(k):float(v) for k,v in cash.items()}
   check(set(native_nets)==set(t['position_id'] for t in ledger),'Saved position missing from native deals')
   check(all(abs(native_nets[t['position_id']]-t['net_profit'])<1e-6 for t in ledger),'Per-position profit mismatch')
   check(len(ledger)==row['metrics']['trades'],'Trade count mismatch')
   check(abs(sum(t['net_profit'] for t in ledger)-row['metrics']['net'])<.03,'Net cash mismatch')
   check(abs(row['native']['balance']-10000-row['metrics']['net'])<.03,'Balance mismatch')
   check(row['native']['open_position']==0,'Final open position')
   check(row['native']['failed_entries']==0,'Native order failure')
   totaltrades+=len(ledger)
   check(all(pd.Timestamp(row['start']).timestamp()<=t['open_epoch']<pd.Timestamp(row['end']).timestamp() for t in ledger),'Date leakage')
   if manifest['verbose']:
    decisions=pd.read_csv(out/(str(row['index'])+'-decisions.csv.gz'));entries=decisions[decisions.reason.isin(['breakout_entry','reversal_entry'])]
    check(len(entries)==len(ledger),'Decision / entry mismatch')
    dates=[str(ny(t['open_epoch']).date()) for t in ledger];check(len(set(dates))==len(dates),'More than one entry per NY day')
    for t in ledger:
     hits=entries[(entries.epoch-t['open_epoch']).abs()<=1];check(len(hits)==1,'No unique entry decision');d=hits.iloc[0]
     check(d.bar_epoch+300<=d.epoch,'Unclosed signal candle / lookahead')
     check(abs(d.p_bear+d.p_sideways+d.p_bull-1)<1e-6,'Invalid Markov probabilities')
     check(d.lots*d.unit_loss<=d.risk_budget+1e-6,'Risk rounded up above budget')
     op=ny(t['open_epoch']);cl=ny(t['close_epoch']);check(op.hour*100+op.minute<row['parameters']['cutoff'],'Entry after cutoff')
     check(op.hour*60+op.minute>=570+row['parameters']['range_minutes'],'Midnight/premarket entry')
     locks=decisions[decisions.reason=='range_ready'];same=locks[(locks.range_high-d.range_high).abs()<1e-6];same=same[(same.range_low-d.range_low).abs()<1e-6]
     check(any(ny(int(v)).date()==op.date() for v in same.epoch),'Entry used a previous-day range')
     if op.date()!=cl.date():
      carried.append(dict(stage=row['stage'],index=row['index'],position_id=t['position_id']))
     if d.reason=='breakout_entry':check(d.close>d.range_high if t['side']=='buy' else d.close<d.range_low,'Not an OR breakout')
     else:check(d.range_low<=d.close<d.range_high if t['side']=='buy' else d.range_low<d.close<=d.range_high,'Reversal entry not back inside range')
     decisionchecks+=1
 for key,row in rows.items():
  check(row['model']==4 and row['clean'],'Final result not native/clean')
  check([row['start'],row['end']]==r.CONFIG['oos'],'Final dates changed')
  df,day,ret=a.equity(row);check(abs(day.iloc[-1].equity-10000-row['metrics']['net'])<.03,'Equity ledger mismatch')
  check(abs(windows[key]['2y']['return_pct']-row['metrics']['return_pct'])<1e-7,'Return window mismatch')
  check(audits[key]['monte_carlo']['paths']==10000,'Bootstrap paths incomplete')
  check(audits[key]['live_promotion'] is False,'Unauthorised promotion')
  count=sum(ny(t['open_epoch']).date()!=ny(t['close_epoch']).date() for t in row['trades'])
  check(audits[key]['execution']['overnight_trades']==count,'Carried positions hidden or miscounted')
  check(audits[key]['gates']['intended_same_day_liquidation']==(count==0),'Scheduled-liquidation gate incorrect')
  check(audits[key]['execution']['rejected_management_requests']==int(row['native']['failed_updates']),'Management rejection counter mismatch')
  if count:check(not audits[key]['all_gates_pass'],'Affected intraday version counted as passed')
  if audits[key]['cost_stress']['status']=='unavailable_zero_spread_quotes':check(not audits[key]['gates']['measured_cost_stress_pf_above_1'],'Missing cost stress counted as pass')
  lastquotes[key]=str(pd.Timestamp(row['native']['last_quote_epoch'],unit='s'))
 source=(R/'engine.mq5').read_text();check('!MQLInfoInteger(MQL_TESTER)' in source,'Missing tester-only guard')
 check('CopyRates(_Symbol,PERIOD_D1,1,1021,d)' in source,'Markov did not use completed daily bars')
 soup=BeautifulSoup((R/'Results.html').read_text(),'html.parser');check(len(soup.find_all('svg'))==2,'Missing equity chart')
 check(len(soup.find_all('table'))>=20,'Incomplete results/rules tables')
 check('nan' not in soup.get_text().lower().replace('financial',''),'Nonfinite rendered value')
 all_flat=not carried
 r.save(R/'VERIFICATION.json',dict(checks=checks,native_passes=evaluated,reconciled_trade_instances=totaltrades,
  independently_checked_final_entries=decisionchecks,last_quotes=lastquotes,ledger_and_entry_checks_passed=True,
  all_intended_same_day_liquidations_passed=all_flat,carried_positions=carried,passed=all_flat,live_changes=False,
  scope='Chronology, cash, risk-floor, frozen settings, native reports, probability/entry invariants, sampled equity and HTML integrity reconciled. Scheduled liquidation exceptions explicitly fail affected operational gates. NOT production readiness approval. No browser file-URL workaround or visual browser claim.'))
 print(json.dumps(dict(checks=checks,native_passes=evaluated,final_entry_checks=decisionchecks,ledger_and_entry_checks_passed=True,all_intended_same_day_liquidations_passed=all_flat)),flush=True)
if __name__=='__main__':
 try:main()
 except Exception as exc:
  import traceback
  detail=traceback.format_exc();print(detail,flush=True)
  r.save(R/'VERIFICATION FAILURE.json',dict(error=str(exc),traceback=detail,checks_completed=checks))
  raise
