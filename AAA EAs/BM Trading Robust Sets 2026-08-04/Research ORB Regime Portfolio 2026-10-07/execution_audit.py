"""Preserve and flag failed scheduled liquidations; never remove losing trades."""
import json
import pandas as pd
import runner as r,evidence as a

def ny(epoch):return pd.Timestamp(epoch,unit='s',tz='UTC').tz_convert('America/New_York')
def main():
 rows=r.load(r.R/'EVALUATION.json');audits=r.load(r.R/'AUDIT.json');inventory={}
 for key,row in rows.items():
  overnight=[]
  for t in row['trades']:
   op,cl=ny(t['open_epoch']),ny(t['close_epoch'])
   if op.date()!=cl.date():overnight.append(dict(position_id=t['position_id'],open_ny=op.isoformat(),close_ny=cl.isoformat(),net_profit=t['net_profit']))
  execution=dict(overnight_trades=len(overnight),overnight_positions=overnight,
   rejected_management_requests=int(row['native']['failed_updates']),
   flatten_schedule='Attempt close from 15:55 New York; cannot fill while market closed or if no executable tick. Some broker sessions/holiday closures do not permit this schedule.',
   same_day_liquidation_observed=not overnight,
   native_market_closed_counter='Not instrumented in frozen source; its exported zero is a placeholder, NOT evidence of zero market-closed rejections.',
   preserved_in_results=True,
   scope='All positions, including overnight carry and rejected-close outcomes, remain in native P&L, DD and bootstrap. Same-day liquidation failures block promotion; this is not a clean strict-intraday backtest for affected versions.')
  inventory[key]=execution;audits[key]['execution']=execution;audits[key]['data_quality']=a.quality(row)
  audits[key]['gates']['intended_same_day_liquidation']=not overnight
  audits[key]['gates']['no_rejected_management_requests']=row['native']['failed_updates']==0
  audits[key]['all_gates_pass']=all(audits[key]['gates'].values())
  if not audits[key]['all_gates_pass']:audits[key]['verdict']='WATCH_ONLY' if row['metrics']['net']>0 and (row['metrics']['pf'] or 0)>1 else 'REJECT'
 r.save(r.R/'EXECUTION AUDIT.json',inventory);r.save(r.R/'AUDIT.json',audits)
 print(json.dumps({k:{'overnight_trades':v['overnight_trades'],'rejected_management_requests':v['rejected_management_requests']} for k,v in inventory.items()},indent=2),flush=True)
if __name__=='__main__':main()
