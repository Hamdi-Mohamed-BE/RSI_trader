"""Reconcile actual native deals; exclude non-exact/session-gap holds explicitly."""
from pathlib import Path
import gzip,html,json,re
import numpy as np
import pandas as pd
import research as raw
R=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text())
def pairs(folder):
 deals=pd.read_csv(folder/'deals.csv.gz');out=[]
 for pid,g in deals.groupby('position_id',sort=False):
  a=g[g.entry==0];z=g[g.entry==1]
  assert len(a)==1 and len(z)==1,(pid,g.to_dict('records'))
  a=a.iloc[0];z=z.iloc[0];assert abs(a.volume-1)<1e-9 and abs(z.volume-1)<1e-9
  assert a.magic==z.magic and a.type!=z.type
  slot=int(a.magic)-103000;assert 0<=slot<48
  ts=pd.Timestamp(int(a.time_msc),unit='ms',tz='UTC');te=pd.Timestamp(int(z.time_msc),unit='ms',tz='UTC');ny=ts.tz_convert('America/New_York')
  expected_hour=slot//2;assert ny.hour==expected_hour and ny.minute==0 and ny.dayofweek<5
  sign=1 if slot%2==0 else -1;assert int(a.type)==(0 if sign==1 else 1)
  money=float(g[['profit','commission','swap','fee']].to_numpy().sum())
  out.append(dict(position_id=int(pid),slot=slot,hour=expected_hour,side='buy' if sign==1 else 'sell',date=ny.strftime('%Y-%m-%d'),entry_utc=ts.isoformat(),exit_utc=te.isoformat(),entry_epoch=int(a.time_msc)//1000,exit_epoch=int(z.time_msc)//1000,entry_price=float(a.price),exit_price=float(z.price),net_cash=money,commission=float(g.commission.sum()),swap=float(g.swap.sum()),fees=float(g.fee.sum()),profit=float(g.profit.sum())))
 # Reconcile net cash against native account report, which includes excluded
 # comparison positions too. No partial filled positions silently dropped.
 report=gzip.decompress((folder/'report.htm.gz').read_bytes());report=report.decode('utf-16') if report[:2]==b'\xff\xfe' else report.decode('utf-8-sig')
 def metric(label):
  m=re.search(re.escape(label)+r'.*?</td>\s*<td[^>]*>(.*?)</td>',report,re.S|re.I)
  return html.unescape(re.sub('<[^>]+>','',m.group(1))).strip() if m else None
 v=metric('Total Net Profit:');quality=metric('History Quality:')
 total=float(v.replace(' ','').replace(',','')) if v else None
 assert total is not None and abs(sum(x['net_cash'] for x in out)-total)<.11,(total,sum(x['net_cash'] for x in out))
 return pd.DataFrame(out),quality,total
def main():
 receipts=load(R/'NATIVE.json');assert len(receipts)==8
 import hashlib
 input_hashes={name:hashlib.sha256((R/name).read_bytes()).hexdigest() for name in ['NATIVE.json','hourly-ledgers.json.gz','overnight-ledger.json.gz','AUDIT.json','PROTOCOL.txt','NATIVE-AMENDMENT.txt']}
 complete=pd.DataFrame(json.loads(gzip.decompress((R/'hourly-ledgers.json.gz').read_bytes())))
 overnight_complete=pd.DataFrame(json.loads(gzip.decompress((R/'overnight-ledger.json.gz').read_bytes())))
 meta={x['symbol']:x for x in load(R/'AUDIT.json')['assets']};rows=[];overnight=[];reconcile=[];ledgers={};kept_ledgers=[]
 for receipt in receipts:
  folder=R/'native'/receipt['tag'];d,quality,total=pairs(folder);asset=meta[receipt['symbol']]['asset'];cpp=meta[receipt['symbol']]['cpp'];window=receipt['window'];start,end=raw.WINDOWS[window]
  hold=660 if receipt['overnight'] else 60
  if receipt['overnight']:
   c=overnight_complete;keys=set(c[(c.date>=start)&(c.date<end)].date)
   d['has_bars']=d.date.isin(keys)
  else:
   c=complete[(complete.asset==asset)&(complete.date>=start)&(complete.date<end)];keys=set(zip(c.date,c.hour,c.side));d['has_bars']=[(r.date,r.hour,r.side) in keys for r in d.itertuples()]
  expected=d.entry_epoch//60*60+hold*60
  d['on_time']=(d.exit_epoch>=expected)&(d.exit_epoch<expected+60)
  d['in_window']=(d.date>=start)&(d.date<end)
  kept=d[d.has_bars&d.on_time&d.in_window].copy();excluded=d[~(d.has_bars&d.on_time&d.in_window)].copy()
  kept['net_points']=kept.net_cash/cpp;kept['spread_points']=np.nan
  kept['asset']=asset;kept['window']=window;kept_ledgers.extend(kept.to_dict('records'))
  (folder/'excluded.json.gz').write_bytes(gzip.compress(json.dumps(excluded.to_dict('records')).encode(),mtime=0))
  reconcile.append(dict(tag=receipt['tag'],asset=asset,window=window,overnight=receipt['overnight'],history_quality=quality,all_executed_positions=len(d),kept_positions=len(kept),excluded_positions=len(excluded),excluded_missing_m1=int((~d.has_bars).sum()),excluded_late_exit=int((~d.on_time).sum()),all_positions_net_cash=float(d.net_cash.sum()),native_report_net_cash=total,kept_net_cash=float(kept.net_cash.sum()),excluded_net_cash=float(excluded.net_cash.sum()),commission_all=float(d.commission.sum()),swap_all=float(d.swap.sum()),session_rejected_entries=receipt['session_rejected_entries'],session_rejected_requests=receipt['session_rejected_requests']))
  groups=[(19,'buy')] if receipt['overnight'] else [(h,s) for h in range(24) for s in ['buy','sell']]
  for hour,side in groups:
   k=kept[(kept.hour==hour)&(kept.side==side)].copy();stats=raw.stats(k,start,end,cpp);stats.pop('mean_spread_points',None)
   row=dict(asset=asset,symbol=receipt['symbol'],window=window,start=start,end_exclusive=end,hour=hour,central_hour=(hour-1)%24,side=side,**stats,commission=float(k.commission.sum()),swap=float(k.swap.sum()),fees=float(k.fees.sum()),history_quality=quality,excluded_positions=int(((excluded.hour==hour)&(excluded.side==side)).sum()),equity_dd_pct=None,source='native MT5 deals, complete timely holds only')
   if receipt['overnight']:row.update(entry_ct='18:00',exit_ct='05:00 next day',stop_enabled=False,tp_enabled=False);overnight.append(row)
   else:rows.append(row);ledgers[(asset,hour,side,window)]=k
  print('RECONCILED',receipt['tag'],len(kept),'kept,',len(excluded),'excluded',flush=True)
 # The raw bootstrap helper expects one ledger per asset/hour/side and filters
 # by calendar. Feed the corresponding separately executed window each time.
 for w in raw.WINDOWS:
  lookup={(a,h,s):v for (a,h,s,ww),v in ledgers.items() if ww==w};raw.family_inference(rows,lookup,w)
 raw.save(R/'NATIVE-SUMMARY.json',rows);raw.save(R/'NATIVE-OVERNIGHT.json',overnight);raw.save(R/'RECONCILIATION.json',reconcile)
 raw.save(R/'ANALYSIS-MANIFEST.json',dict(input_hashes=input_hashes,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),summary_sha256=hashlib.sha256((R/'NATIVE-SUMMARY.json').read_bytes()).hexdigest()))
 (R/'native-kept-ledgers.json.gz').write_bytes(gzip.compress(json.dumps(kept_ledgers).encode(),mtime=0))
 eligible=[]
 for a in raw.ASSETS:
  y={(r['hour'],r['side']):r for r in rows if r['asset']==a and r['window']=='1y'}
  recent={(r['hour'],r['side']):r for r in rows if r['asset']==a and r['window']=='3m'}
  for key,r in y.items():
   q=recent[key]
   if r['trades']>=30 and q['trades']>=30 and r['pf'] and q['pf'] and min(r['pf'],q['pf'])>=1.2 and min(r['win_rate_pct'],q['win_rate_pct'])>=52 and min(r['sharpe_daily'],q['sharpe_daily'])>0:
    eligible.append({'asset':a,'hour':key[0],'side':key[1],'1y':r,'3m':q})
 eligible.sort(key=lambda x:min(x['1y']['sharpe_daily'],x['3m']['sharpe_daily']),reverse=True)
 raw.save(R/'CANDIDATES.json',eligible)
 print('BOTH-WINDOW CANDIDATES',json.dumps(eligible),flush=True)
 print('OVERNIGHT',json.dumps(overnight),flush=True)
if __name__=='__main__':main()
