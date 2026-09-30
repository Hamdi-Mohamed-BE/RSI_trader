"""Independent evidence/rejection review. No new trades or parameter selection."""
from pathlib import Path
import hashlib,gzip,json,re,sys,statistics
from datetime import datetime
from zoneinfo import ZoneInfo
import pipeline as p
import extended_audit as a
ROOT=p.ROOT;OPT=ROOT/'Optimization'
def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 frozen=p.freeze();raw_checks=[];conversion=[]
 for path in sorted((ROOT/'native').glob('*/run.json')):
  meta=read(path);assert meta['frozen']==frozen
  checked=a.audit(path.parent)
  raw_checks.append(dict(case=path.parent.name,trades=checked['trades_checked'],cash_reconciled=True))
  conversion.extend(dict(case=path.parent.name,**x) for x in checked['conversion_approximation_exceptions'])
 assert len(raw_checks)==36
 rows=read(OPT/'SEARCH_RESULTS.json');assert len(rows)==384
 parity=read(OPT/'PARITY.json');assert all(parity.values())
 native=[]
 for path in sorted((OPT/'native').glob('*/results.json')):
  folder=path.parent;manifest=read(folder/'manifest.json');results=read(path)
  assert manifest['logic_sha']==sha(OPT/'SearchLogic.mqh') and manifest['protocol_sha']==sha(OPT/'PROTOCOL.md')
  assert manifest['raw_source_sha']==sha(p.RAW/'FourIdeas.mq5')
  meta=read(folder/'run_metadata.json')
  report=gzip.decompress((folder/('report.xml.gz' if manifest['optimization'] else 'report.htm.gz')).read_bytes())
  assert hashlib.sha256(report).hexdigest()==meta['report_sha']
  assert sha(folder/'Search.ex5')==meta['binary_sha']
  if manifest['optimization']:
   assert len(results)==len(manifest['cases'])
   assert sorted(r['index'] for r in results)==list(range(len(results)))
  else:
   trades=read(folder/'trades.json');m=results[0]['metrics']
   assert len(trades)==m['trades'] and abs(sum(t['net_profit'] for t in trades)-m['net_profit'])<.11
   assert abs(a.old.shared.stats(trades,manifest['start'],manifest['end'])['profit_factor']-results[0]['net']['profit_factor'])<1e-10
   assert all(t['open_time']<=t['close_time'] for t in trades)
   assert all(trades[i]['close_time']<=trades[i+1]['open_time'] for i in range(len(trades)-1))
  native.append(dict(case=folder.name,evaluations=len(results),optimization=manifest['optimization']))
 hold=read(OPT/'HOLDOUT_GATE.json');assert hold['passed'] is False
 assert read(OPT/'STOP.json')['reason']=='Historical holdout failed; no retuning'
 assert not (OPT/'native/retrospective-1y').exists(),'Unexpected testing after the stop gate'
 selected=read(OPT/'SELECTED.json')
 validations=read(OPT/'VALIDATION.json')
 import importlib.util
 spec=importlib.util.spec_from_file_location('research_selection',OPT/'search.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
 assert selected['index']==max(validations,key=s.score)['index']
 assert hold['result']['parameters']==selected['parameters']
 selected_folder=OPT/'native'/('validation-'+str(selected['index']))
 diagnostics=[]
 for folder in [selected_folder,OPT/'native/holdout']:
  report=gzip.decompress((folder/'report.htm.gz').read_bytes()).decode('utf-16')
  orders=a.old.filled_orders(report);trades=read(folder/'trades.json')
  journal=gzip.decompress((folder/'journal.txt.gz').read_bytes()).decode()
  pat=r'IDEA_ORDER t=([\d.]+ [\d:]+) mode=(\d+) control=(\d+) side=(-?\d+) pending=(\d+) entry=([\d.]+) sl=([\d.]+) tp=([\d.]+) lot=([\d.]+) risk=([\d.]+) eq=([\d.]+) high=([\d.]+) low=([\d.]+) due=([\d.]+ [\d:]+) order=(\d+)'
  logs={int(v[-1]):v for v in re.findall(pat,journal)}
  measured=[];balance=10000.;breach=None;daily={}
  for t in trades:
   opened=a.old.stamp(t['open_time']);match=[o for o in orders if o['filled']==opened and o['side']==t['side']]
   assert len(match)==1,(folder.name,t)
   o=match[0];v=logs[o['ticket']];eq=float(v[10]);risk=float(v[9]);sl=o['stop']
   fillrisk=abs(t['open_price']-sl)*t['volume']*100000/sl
   margin=t['volume']*100000/30
   measured.append(dict(number=t['number'],lot=t['volume'],intended_risk_pct=100*risk/eq,fill_stop_risk_pct=100*fillrisk/eq,roundtrip_cost_pct=100*abs(t['commission'])/eq,ftmo_1_to_30_margin_usd=margin,equity_at_placement=eq))
   balance+=t['net_profit']
   if breach is None and balance<9000:breach=dict(closed_at=t['close_time'],closed_balance=round(balance,2),trade_number=t['number'])
   day=a.old.stamp(t['close_time']).astimezone(ZoneInfo('Europe/Prague')).date().isoformat()
   daily[day]=daily.get(day,0)+t['net_profit']
  diagnostics.append(dict(case=folder.name,first_trade=measured[0],max_fill_stop_risk_pct=max(x['fill_stop_risk_pct'] for x in measured),median_fill_stop_risk_pct=statistics.median(x['fill_stop_risk_pct'] for x in measured),median_roundtrip_cost_pct=statistics.median(x['roundtrip_cost_pct'] for x in measured),orders_requiring_more_than_entire_equity_at_ftmo_leverage=sum(x['ftmo_1_to_30_margin_usd']>x['equity_at_placement'] for x in measured),trades=len(measured),first_closed_balance_below_9000=breach,worst_closed_day=min(daily.items(),key=lambda x:x[1])))
 # Third neighborhood coordinate was inactive for step-lock (no target).
 # The other two coordinates were active. Equal triplication leaves the pass
 # fraction unchanged, but must NOT be described as 27 independent neighbors.
 neighborhoods=[]
 for folder in sorted((OPT/'native').glob('neighborhood-*')):
  r=read(folder/'results.json');active={}
  for x in r:
   c=dict(x['parameters'])
   if c['trail']==7 and c['exit']==0:c.pop('trail_distance');c.pop('rr')
   active.setdefault(json.dumps(c,sort_keys=True),[]).append(x)
  for group in active.values():
   assert len({(x['native']['Profit'],x['native']['Profit Factor'],x['native']['Trades']) for x in group})==1
  neighborhoods.append(dict(case=folder.name,evaluations=len(r),distinct_active_neighbors=len(active),profitable_fraction=sum(g[0]['native']['Profit']>0 for g in active.values())/len(active)))
 result=dict(ok=True,raw_cases=len(raw_checks),raw_trades_audited=sum(x['trades'] for x in raw_checks),search_evaluations=len(rows),distinct_parameter_vectors=len({json.dumps(x['parameters'],sort_keys=True) for x in rows}),search_native_runs=native,parity=parity,diagnostics=diagnostics,neighborhoods=neighborhoods,fx_conversion_approximation_exceptions=len(conversion),max_fx_conversion_approximation_difference_usd=max((x['difference_usd'] for x in conversion),default=0),holdout_rejected=True,production_changed=False,live_api_called=False)
 p.save(ROOT/'FINAL_CHECKS.json',result)
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
