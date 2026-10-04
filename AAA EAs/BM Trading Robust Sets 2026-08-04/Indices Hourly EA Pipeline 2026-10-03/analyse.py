"""Native position reconciliation and conditional, fixed-cash robustness."""
from pathlib import Path
import gzip, hashlib, html, json, math, re, sys
import numpy as np
import pandas as pd
from html.parser import HTMLParser
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R.parents[1]/'Calyx Research Pipeline'))
import calyx_pipeline as policy
INITIAL=10000.;SEED=20261003;PATHS=10000;TRIALS=294
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def clean(x):
 if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [clean(v) for v in x]
 if isinstance(x,(np.integer,)):return int(x)
 if isinstance(x,(float,np.floating)):return float(x) if math.isfinite(x) else None
 return x
def save(p,v):p.write_text(json.dumps(clean(v),indent=2,allow_nan=False),encoding='utf-8')
def report_values(folder):
 b=gzip.decompress((folder/'report.htm.gz').read_bytes());s=b.decode('utf-16') if b[:2]==b'\xff\xfe' else b.decode('utf-8-sig')
 cells=[html.unescape(re.sub('<[^>]+>','',x)).strip() for x in re.findall(r'<td[^>]*>(.*?)</td>',s,re.S|re.I)]
 return {cells[i].rstrip(':'):cells[i+1] for i in range(len(cells)-1) if cells[i].endswith(':')}
def number(s):return float(str(s).replace(' ','').replace(',',''))
class DealRows(HTMLParser):
 def __init__(self):super().__init__();self.rows=[];self.row=None;self.cell=None
 def handle_starttag(self,tag,attrs):
  if tag=='tr':self.row=[]
  elif tag=='td' and self.row is not None:self.cell=''
 def handle_data(self,text):
  if self.cell is not None:self.cell+=text
 def handle_endtag(self,tag):
  if tag=='td' and self.cell is not None:self.row.append(' '.join(self.cell.split()));self.cell=None
  elif tag=='tr' and self.row is not None:self.rows.append(self.row);self.row=None
def supplement_forced_exits(d,folder):
 # Server-forced stop-outs carry magic 0, so the owned-magic CSV deliberately
 # omits them. Recover actual missing exits from the same native HTML report.
 # This isolated tester has only one EA and one owned position at a time.
 b=gzip.decompress((folder/'report.htm.gz').read_bytes());s=b.decode('utf-16') if b[:2]==b'\xff\xfe' else b.decode('utf-8-sig');parser=DealRows();parser.feed(s)
 report=[]
 for c in parser.rows:
  if len(c)==13 and re.fullmatch(r'\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}',c[0]) and c[3] in ('buy','sell') and c[4] in ('in','out','out by'):
   report.append(c)
 ids=set(d.ticket.astype(int));extras=[];active=None
 by_ticket={int(r.ticket):r for r in d.itertuples()}
 for c in report:
  ticket=int(c[1]);r=by_ticket.get(ticket)
  if c[4]=='in':
   assert r is not None and active is None,(folder.name,'unexpected native entry')
   active=int(r.position_id)
  else:
   assert active is not None
   if ticket not in ids:
    assert c[12].startswith('so ') or c[12]=='end of test',(folder.name,'unexplained missing exit',c)
    extras.append({'ticket':ticket,'position_id':active,'time_msc':int(pd.Timestamp(c[0],tz='UTC').timestamp()*1000),'magic':0,'entry':1,'type':0 if c[3]=='buy' else 1,'volume':number(c[5]),'price':number(c[6]),'profit':number(c[10]),'commission':number(c[8]),'swap':number(c[9]),'fee':0.,'comment':c[12]})
   active=None
 assert active is None,(folder.name,'report leaves unmatched open trade')
 if extras:d=pd.concat([d,pd.DataFrame(extras)],ignore_index=True).sort_values('time_msc')
 return d,extras
def pairs(folder,receipt):
 d,extras=supplement_forced_exits(pd.read_csv(folder/'deals.csv.gz'),folder);rows=[]
 for pid,g in d.groupby('position_id',sort=False):
  a=g[g.entry==0];z=g[g.entry.isin([1,3])];assert len(a)>0 and len(z)>0,(folder.name,pid)
  assert abs(a.volume.sum()-z.volume.sum())<1e-7,(folder.name,pid,'volume mismatch')
  entry=a.iloc[0];exit=z.iloc[-1];t=pd.Timestamp(int(entry.time_msc),unit='ms',tz='UTC');e=pd.Timestamp(int(exit.time_msc),unit='ms',tz='UTC');ny=t.tz_convert('America/New_York')
  hour=int(str(entry['comment']).split('|')[1]);side='buy' if int(entry.type)==0 else 'sell'
  assert hour==ny.hour and ny.minute==receipt['entry_minute'] and ny.dayofweek<5,(folder.name,ny,entry)
  assert a.magic.eq(103310).all() and g.magic.isin([103310,0]).all() and abs(a.volume.sum()-1)<1e-7
  expected=t.floor('min')+pd.Timedelta(minutes=receipt['hold_minutes'])
  rows.append({'position_id':int(pid),'hour':hour,'side':side,'entry_utc':t.isoformat(),'exit_utc':e.isoformat(),'ny_date':ny.strftime('%Y-%m-%d'),'entry_epoch':int(entry.time_msc)//1000,'exit_epoch':int(exit.time_msc)//1000,'entry_price':float(np.average(a.price,weights=a.volume)),'exit_price':float(np.average(z.price,weights=z.volume)),'lots':float(a.volume.sum()),'profit':float(g.profit.sum()),'commission':float(g.commission.sum()),'swap':float(g.swap.sum()),'fees':float(g.fee.sum()),'net_cash':float(g[['profit','commission','swap','fee']].to_numpy().sum()),'late_exit_seconds':max(0.,(e-expected).total_seconds()-60),'hold_minutes_actual':(e-t).total_seconds()/60})
 df=pd.DataFrame(rows).sort_values(['exit_epoch','position_id']).reset_index(drop=True)
 native=report_values(folder);total=number(native['Total Net Profit'])
 assert abs(df.net_cash.sum()-total)<.11,(folder.name,total,df.net_cash.sum())
 assert len(df)==int(number(native['Total Trades']))
 native['recovered_forced_closes']=extras
 return df,native
def pf(p):
 p=np.asarray(p,float);loss=-p[p<0].sum();return float(p[p>0].sum()/loss) if loss else None
def metrics(df,start,end,initial=INITIAL):
 p=df.net_cash.to_numpy(float);balance=initial+np.r_[0,np.cumsum(p)];peak=np.maximum.accumulate(balance)
 days=pd.date_range(start,end,inclusive='left',freq='B',tz='UTC');daily=pd.Series(0.,index=days)
 for r in df.itertuples():
  day=pd.Timestamp(r.exit_utc).floor('D');
  if day in daily.index:daily.loc[day]+=r.net_cash
  else:daily.loc[day]=daily.get(day,0.)+r.net_cash
 daily=daily.sort_index();returns=(daily/initial).tolist();outcomes=[policy.TradeOutcome(pd.Timestamp(r.exit_utc).to_pydatetime(),r.net_cash,r.commission,r.swap) for r in df.itertuples()]
 wins=int((p>0).sum());w,l=policy.streaks(p.tolist());ci=policy.wilson_interval(wins,len(p))
 return dict(trades=len(p),wins=wins,losses=int((p<0).sum()),win_rate_pct=100*wins/len(p) if len(p) else 0,win_rate_95_pct=[100*ci[0],100*ci[1]],pf=pf(p),net_cash=float(p.sum()),return_pct=float(p.sum()/initial*100),closed_balance_dd_pct=float(np.max((peak-balance)/peak)*100),minimum_closed_balance=float(balance.min()),sharpe_daily=policy.sharpe_statistics(returns,TRIALS,252)['annualized_sharpe'],deflated_sharpe_pct=policy.sharpe_statistics(returns,TRIALS,252)['deflated_sharpe_pct'],max_win_streak=w,max_loss_streak=l,expected_payoff=float(p.mean()) if len(p) else 0,commission=float(df.commission.sum()),swap=float(df.swap.sum()),fees=float(df.fees.sum()),late_positions=int((df.late_exit_seconds>0).sum()),recent_half_pf=pf(p[len(p)//2:]),profitable_thirds=sum(x['net_profit']>0 for x in policy.subperiods(outcomes)),chronological_thirds=policy.subperiods(outcomes),daily_expected_shortfall_95_pct=policy.expected_shortfall(returns)*100,zero_trade_weekdays=int((daily==0).sum()),calendar_days=len(daily))
def bootstrap(df,start,end,block,seed):
 # Date blocks resample whole days; within-day order/exposure remains intact.
 # Fixed lots imply additive dollars, never compounded percent returns.
 dates=pd.date_range(start,end,inclusive='left',freq='B',tz='UTC');groups={d:[] for d in dates}
 for r in df.itertuples():groups.setdefault(pd.Timestamp(r.exit_utc).floor('D'),[]).append(r.net_cash)
 groups=dict(sorted(groups.items()));width=max(1,max(len(v) for v in groups.values()));n=len(groups);a=np.zeros((n,width))
 for i,v in enumerate(groups.values()):a[i,:len(v)]=v
 rng=np.random.default_rng(seed);profits=[];factors=[];drawdowns=[];breaches=[];ruined=[]
 for first in range(0,PATHS,200):
  count=min(200,PATHS-first);starts=rng.integers(0,n,size=(count,math.ceil(n/block)));indices=((starts[:,:,None]+np.arange(block))%n).reshape(count,-1)[:,:n]
  paths=a[indices].reshape(count,-1);bal=INITIAL+np.cumsum(paths,axis=1);pk=np.maximum.accumulate(np.column_stack([np.full(count,INITIAL),bal]),axis=1)[:,1:]
  gp=np.maximum(paths,0).sum(axis=1);gl=-np.minimum(paths,0).sum(axis=1)
  factors.extend(np.divide(gp,gl,out=np.full(count,np.inf),where=gl>0));profits.extend((bal[:,-1]-INITIAL)/100);drawdowns.extend(100*np.max((pk-bal)/pk,axis=1));breaches.extend(np.any(bal<9000,axis=1));ruined.extend(np.any(bal<=0,axis=1))
 def q(x):return [float(v) for v in np.quantile(x,[.05,.5,.95])]
 return dict(paths=PATHS,seed=seed,block_days=block,probability_profit_pct=100*float(np.mean(np.asarray(profits)>0)),return_p05_p50_p95=q(profits),pf_p05_p50_p95=q(factors),closed_dd_p05_p50_p95=q(drawdowns),below_initial_minus_10pct_fraction_pct=100*float(np.mean(breaches)),capital_exhausted_fraction_pct=100*float(np.mean(ruined)),scope='conditional historical day-block bootstrap; fixed dollars; closed P&L only; not forecast or FTMO pass odds')
def shuffle(df,seed):
 p=df.net_cash.to_numpy(float);rng=np.random.default_rng(seed);dd=[];wins=[];losses=[]
 for _ in range(PATHS):
  v=rng.permutation(p);b=INITIAL+np.r_[0,v.cumsum()];pk=np.maximum.accumulate(b);dd.append(100*float(np.max((pk-b)/pk)));w,l=policy.streaks(v.tolist());wins.append(w);losses.append(l)
 return {'paths':PATHS,'seed':seed,'terminal_return_pct_constant':float(p.sum()/100),'closed_dd_p05_p50_p95':np.quantile(dd,[.05,.5,.95]).tolist(),'win_streak_p05_p50_p95':np.quantile(wins,[.05,.5,.95]).tolist(),'loss_streak_p05_p50_p95':np.quantile(losses,[.05,.5,.95]).tolist(),'scope':'trade-order reshuffle; return and PF do not change'}
def missed(df,rate,seed):
 p=df.net_cash.to_numpy(float);rng=np.random.default_rng(seed);returns=[];factors=[]
 for _ in range(PATHS):
  a=p[rng.random(len(p))>=rate];returns.append(float(a.sum()/100));factors.append(pf(a) or 0.)
 return {'miss_rate':rate,'paths':PATHS,'return_p05_p50_p95':np.quantile(returns,[.05,.5,.95]).tolist(),'pf_p05_p50_p95':np.quantile(factors,[.05,.5,.95]).tolist(),'scope':'random missed-trade sensitivity, not full account simulation'}
def friction(folder):
 f=pd.read_csv(folder/'fills.csv.gz');f=f[f.retcode.isin([10009,10010])].copy()
 spread=(f.ask-f.bid).clip(lower=0);adverse=np.where(f.side==1,f.fill_price-f.ask,f.bid-f.fill_price);adverse=np.maximum(adverse,0)
 return {'entry_spread_median_usd_per_lot':float(np.median(spread)),'entry_spread_p95_usd_per_lot':float(np.quantile(spread,.95)),'adverse_entry_fill_p95_usd_per_lot':float(np.quantile(adverse,.95)),'surcharge_per_trade':float(np.quantile(spread,.95)+np.quantile(adverse,.95)),'cpp':1.0,'scope':'one extra observed P95 entry spread plus P95 adverse fill; exit spread not independently measured'}
def main():
 receipts=json.loads((R/'NATIVE.json').read_text());rows=[];ledgers={};manifests=[]
 for receipt in receipts:
  folder=R/'native'/receipt['tag'];df,native=pairs(folder,receipt);ledgers[receipt['tag']]=df
  row=receipt|metrics(df,receipt['from'].replace('.','-'),'2026-10-03',receipt['deposit']);audit=pd.read_csv(folder/'audit.csv.gz').iloc[0].to_dict()
  row.update(native_history_quality=native['History Quality'],native_equity_dd_text=native['Equity Drawdown Maximal'],equity_dd_pct=audit['max_equity_dd_pct'],minimum_equity=audit['minimum_equity'],execution_audit=audit,recovered_forced_closes=native['recovered_forced_closes'],first_entry_utc=df.entry_utc.iloc[0],last_exit_utc=df.exit_utc.iloc[-1],stopped_early=receipt['account_failure'])
  row['hour_breakdown']=[{'hour':int(h),'side':str(s),**metrics(g,receipt['from'].replace('.','-'),'2026-10-03')} for (h,s),g in df.groupby(['hour','side'])]
  dt=pd.to_datetime(df.exit_utc,format='ISO8601',utc=True);row['monthly']=[{'month':str(m),'trades':len(g),'net_cash':float(g.net_cash.sum()),'return_pct':float(g.net_cash.sum()/receipt['deposit']*100),'pf':pf(g.net_cash),'win_rate_pct':100*float((g.net_cash>0).mean())} for m,g in df.groupby(dt.dt.strftime('%Y-%m'))]
  row['annual']=[{'year':str(y),'partial':str(y)=='2026' or (str(y)==receipt['from'][:4] and receipt['from'][5:]!='01.01'),'trades':len(g),'net_cash':float(g.net_cash.sum()),'return_pct':float(g.net_cash.sum()/receipt['deposit']*100),'pf':pf(g.net_cash),'win_rate_pct':100*float((g.net_cash>0).mean())} for y,g in df.groupby(dt.dt.year)]
  (folder/'positions.json.gz').write_bytes(gzip.compress(json.dumps(clean(df.to_dict('records'))).encode(),mtime=0))
  manifests.append({'tag':receipt['tag'],'report_sha256':sha(folder/'report.htm.gz'),'deals_sha256':sha(folder/'deals.csv.gz'),'positions_sha256':sha(folder/'positions.json.gz'),'native_profit_reconciles':True,'native_trade_count_reconciles':True});rows.append(row);print('RECONCILED',receipt['tag'],len(df),flush=True)
 save(R/'SUMMARY.json',rows);save(R/'RECONCILIATION.json',manifests)
 mc={};decisions=[]
 for i,asset in enumerate(['US30','US100','SP500']):
  base={r['window']:r for r in rows if r['asset']==asset and r['variant']=='baseline'};y=base['1y'];q=base['3m'];five=base['5y'];three=base['3y'];fr=friction(R/'native'/y['tag']);studies={}
  for window in ['1y','5y']:
   r=base[window];df=ledgers[r['tag']]
   if r['account_failure']:
    studies[window]={'status':'not_run_on_incomplete_horizon','reason':'Native account stopped out and terminated early. Do not resample the unobserved remainder as zero returns. One-year complete-path Monte Carlo is still supplied.','last_exit_utc':r['last_exit_utc']};continue
   start=r['from'].replace('.','-');boot=[bootstrap(df,start,'2026-10-03',b,SEED+i*100+b+(1000 if window=='5y' else 0)) for b in [1,5,10]]
   studies[window]={'day_blocks':boot,'shuffle':shuffle(df,SEED+200+i),'missed':[missed(df,x,SEED+300+i) for x in [.1,.2]]}
   print('MC DONE',asset,window,flush=True)
  df=ledgers[y['tag']];costs={}
  for name,p in {'double_commission':df.net_cash+df.commission,'double_negative_swap':df.net_cash+np.minimum(df.swap,0),'measured_extra_friction':df.net_cash-fr['surcharge_per_trade'],'all_extra_costs':df.net_cash+df.commission+np.minimum(df.swap,0)-fr['surcharge_per_trade']}.items():costs[name]={'pf':pf(p),'return_pct':float(p.sum()/100),'win_rate_pct':100*float((p>0).mean())}
  variants=[r for r in rows if r['asset']==asset and r['variant']!='baseline'];boot5=studies['1y']['day_blocks'][1]
  gates={'raw_3y_5y_positive_pf115':all(r['return_pct']>0 and r['pf']>=1.15 and r['trades']>=30 for r in [three,five]),'year_pf120_win50':y['pf']>=1.2 and y['win_rate_pct']>=50,'quarter_pf120_win50':q['pf']>=1.2 and q['win_rate_pct']>=50,'bootstrap_profit95':boot5['probability_profit_pct']>=95,'bootstrap_return_p05_positive':boot5['return_p05_p50_p95'][0]>0,'bootstrap_pf_p05_above1':boot5['pf_p05_p50_p95'][0]>1,'deflated_sharpe95':y['deflated_sharpe_pct']>=95,'recent_half_pf_above1':y['recent_half_pf'] is not None and y['recent_half_pf']>1,'two_profitable_thirds':y['profitable_thirds']>=2,'measured_cost_pf_above1':costs['all_extra_costs']['pf']>1,'native_500ms_pf_above1':next(r for r in variants if r['variant']=='delay500')['pf']>1,'all_neighbors_profitable':all(r['return_pct']>0 and r['pf']>1 for r in variants),'no_native_account_failure':not any(r['account_failure'] for r in base.values()),'independent_broker_test':False,'untouched_prospective_holdout':False,'native_equity_path_present':True}
  verdict='WATCH ONLY' if gates['raw_3y_5y_positive_pf115'] else 'RESEARCH ONLY — FAILED LONG-WINDOW GATE'
  decisions.append({'asset':asset,'verdict':verdict,'gates':gates,'friction':fr,'cost_stress':costs,'trial_count':TRIALS,'why_not_promoted':'Hours were chosen on the latest year; no genuinely untouched holdout or independent broker. Bootstrap does not correct this selection bias.'})
  mc[asset]=studies
 save(R/'MONTE-CARLO.json',mc);save(R/'DECISIONS.json',decisions)
 save(R/'ANALYSIS-MANIFEST.json',{'analysis_sha256':sha(Path(__file__)),'selected_hours_sha256':sha(R/'SELECTED-HOURS.json'),'summary_sha256':sha(R/'SUMMARY.json'),'mc_sha256':sha(R/'MONTE-CARLO.json'),'positions_reconciled':True,'paths':PATHS,'seed':SEED,'tested_configuration_lower_bound':TRIALS,'trial_count_explanation':'264 original asset/hour/side/window comparisons plus 30 new native performance/diagnostic runs; approximate DSR screen, not exact selective inference. Functional-only test excluded.'})
 print('ANALYSIS COMPLETE',len(rows),flush=True)
if __name__=='__main__':main()
