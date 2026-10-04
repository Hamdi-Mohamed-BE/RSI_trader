"""Independent audit and standalone raw research report. No strategy selection."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import base64, csv, gzip, html, io, json, math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
NY=ZoneInfo('America/New_York')
def utc(t):return datetime.fromisoformat(t.replace('.','-')).replace(tzinfo=timezone.utc)
def streaks(p):
 current=0;n=0;runs={1:[], -1:[]}
 for x in p:
  sign=1 if x>0 else -1 if x<0 else 0
  if sign!=current:
   if current:runs[current].append(n)
   current=sign;n=0
  if sign:n+=1
 if current:runs[current].append(n)
 return {'max_win':max(runs[1],default=0),'max_loss':max(runs[-1],default=0),'average_win':float(np.mean(runs[1])) if runs[1] else 0,'average_loss':float(np.mean(runs[-1])) if runs[-1] else 0}
def wilson(w,n):
 if not n:return [0,0]
 z=1.95996398454;p=w/n;d=1+z*z/n
 c=(p+z*z/(2*n))/d;e=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/d
 return [100*(c-e),100*(c+e)]
def metrics(trades,start,end):
 trades=sorted(trades,key=lambda x:(x['close_time'],x['number']))
 pnl=np.array([t['net_profit'] for t in trades],dtype=float)
 balances=np.r_[10000,10000+pnl.cumsum()]
 peaks=np.maximum.accumulate(balances)
 dd=(peaks-balances)/peaks*100
 daily=pd.Series(0.,index=pd.date_range(start,end-timedelta(days=1),freq='D'))
 for t in trades:daily.loc[pd.Timestamp(utc(t['close_time']).date())]+=t['net_profit']
 daily_bal=10000+daily.cumsum();ret=daily/daily_bal.shift(1).fillna(10000)
 sdev=ret.std(ddof=0)
 gp=pnl[pnl>0].sum();gl=-pnl[pnl<0].sum()
 carry=[t for t in trades if utc(t['open_time']).astimezone(NY).date()!=utc(t['close_time']).astimezone(NY).date()]
 late=[t for t in trades if utc(t['close_time']).astimezone(NY).hour*60+utc(t['close_time']).astimezone(NY).minute>=956]
 m={'trades':len(trades),'net':round(float(pnl.sum()),2),'return_pct':round(float(pnl.sum()/100),2),'pf':float(gp/gl) if gl else None,'win_rate_pct':float((pnl>0).mean()*100) if len(pnl) else 0,'win_rate_ci95':wilson(int((pnl>0).sum()),len(pnl)),
    'closed_balance_dd_pct':float(dd.max()),'daily_closed_balance_sharpe':float(ret.mean()/sdev*math.sqrt(365)) if sdev>0 else 0,'streaks':streaks(pnl),'carryover_positions':len(carry),'late_exit_positions':len(late),'costs':round(sum(t['total_costs'] for t in trades),2),'last_trade_close':trades[-1]['close_time'] if trades else None}
 return m,balances,dd,trades

def independent_audit(folder,trades):
 rows=list(csv.DictReader(io.StringIO(gzip.decompress((folder/'signals.csv.gz').read_bytes()).decode())))
 fills=[x for x in rows if x['retcode']=='10009'];assert len(fills)==len(trades)
 seen=set()
 bytime={t['open_time']:t for t in trades}
 verified=0
 for x in fills:
  tm=utc(x['time'].replace(' ','T'));bar=utc(x['signal_bar'].replace(' ','T'));ny=tm.astimezone(NY);bny=bar.astimezone(NY)
  assert ny.weekday()<5 and ny.date()==bny.date()
  assert ny.date() not in seen;seen.add(ny.date())
  assert bny.hour*60+bny.minute>=585 and ny.hour*60+ny.minute<955
  assert (tm-bar).total_seconds()>=300
  side=int(x['side']);stop=float(x['stop']);lo=float(x['range_low']);hi=float(x['range_high']);close=float(x['signal_close'])
  assert (close>hi and abs(stop-lo)<.011) if side>0 else (close<lo and abs(stop-hi)<.011)
  assert float(x['quoted_risk'])<=float(x['risk_budget'])+.02
  # Execution delay can move the fill into the following second.
  candidates=[t for t in trades if abs((utc(t['open_time'])-tm).total_seconds())<=2]
  assert len(candidates)==1,'Missing/ambiguous fill reconciliation'
  t=candidates[0];assert t['side']==('Long' if side>0 else 'Short') and abs(t['volume']-float(x['lots']))<1e-8
  verified+=1
 return {'verified_closed_signal_rows':verified,'ny_dst_checked_with_independent_zoneinfo':True,'one_fill_per_ny_date':True,'completed_signal_checked':True,'stop_boundary_checked':True,'quoted_risk_ceiling_checked':True,'filled_side_volume_checked':True,'range_ohlc_independently_rebuilt':False,'limitation':'Native signal export proves reported inputs/causality constraints, not an independent full OHLC reconstruction.'}

def main():
 data={};checks={};curves={}
 for symbol in ('USTEC','US500'):
  data[symbol]={};checks[symbol]={}
  for window in ('1y','3y','5y'):
   folder=ROOT/'native'/f'{symbol}-{window}'
   run=json.loads((folder/'run.json').read_text());manifest=run['manifest'];assert run['ok']
   trades=json.loads((folder/'trades.json').read_text())
   start=datetime.strptime(manifest['start'],'%Y.%m.%d');end=datetime.strptime(manifest['end'],'%Y.%m.%d')
   m,b,d,trades=metrics(trades,start,end)
   assert abs(m['net']-run['metrics']['net_profit'])<.1 and m['trades']==run['metrics']['trades']
   m['native_equity_dd_pct']=run['metrics']['max_relative_equity_drawdown_pct'];m['native_sharpe']=run['metrics']['sharpe_ratio'];m['history_quality']=run['metrics']['history_quality'];m['flags']=run['flags'];m['tick_coverage_notes']=run['real_tick_notes'];m['execution_summary']=run['summary'];m['symbol_specs']=run['symbol_specs']
   data[symbol][window]=m;checks[symbol][window]=independent_audit(folder,trades);curves[symbol,window]=(b,d,trades)
  failures=[]
  for w in ('3y','5y'):
   m=data[symbol][w]
   if m['net']<=0:failures.append(w+' net return is not positive')
   if m['pf'] is None or m['pf']<=1:failures.append(w+' trade-net PF is not above 1')
   if m['trades']<30:failures.append(w+' fewer than 30 closed trades')
  audit=json.loads((ROOT/'audit'/(symbol+'.json')).read_text())
  assert abs(audit['metrics']['net_profit']-data[symbol]['5y']['net'])<.1
  raw_stat_failures=[k for k,v in audit['gates'].items() if not v and not k.startswith('cost_stress')]
  data[symbol]['raw_gate']={'profitability_only_passed':not failures,'passed':not failures and not raw_stat_failures,'failures':failures+raw_stat_failures,'preferred_pf_1_2_both_windows':all(data[symbol][w]['pf'] and data[symbol][w]['pf']>=1.2 for w in ('3y','5y'))}
  data[symbol]['five_year_audit']={'verdict':audit['verdict'],'deflated_sharpe_probability_pct':audit['metrics']['deflated_sharpe_pct'],'bootstrap_pf_p05':audit['bootstrap']['profit_factor_p05'],'bootstrap_profit_probability_pct':audit['bootstrap']['probability_profit_pct'],'bootstrap_return_p05_pct':audit['bootstrap']['return_p05_pct'],'paths':10000,'block_length':5,'trial_count_for_dsr':2,'extra_cost_stress':'Not supplied; not invented; promotion blocked'}
 (ROOT/'RESULTS.json').write_text(json.dumps({'configuration_count':1,'performance_cases':6,'smoke_cases':1,'symbols':data,'status':'STOPPED FOR USER REVIEW; NO OPTIMISATION'},indent=2),encoding='utf-8')
 (ROOT/'VERIFICATION.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
 plt.rcParams.update({'figure.facecolor':'#091713','axes.facecolor':'#0e211c','axes.edgecolor':'#315047','text.color':'#eef7f2','axes.labelcolor':'#bdcfca','xtick.color':'#bdcfca','ytick.color':'#bdcfca','grid.color':'#315047','font.size':10})
 imgs={}
 for window in ('1y','3y','5y'):
  fig,ax=plt.subplots(2,2,figsize=(13,7),sharex='col',gridspec_kw={'height_ratios':[2,1]})
  for col,symbol in enumerate(('USTEC','US500')):
   b,d,t=curves[symbol,window];start=datetime.strptime(json.loads((ROOT/'native'/f'{symbol}-{window}'/'manifest.json').read_text())['start'],'%Y.%m.%d')
   x=[start]+[utc(z['close_time']).replace(tzinfo=None) for z in t]
   ax[0,col].plot(x,b,color='#72f6cb',lw=1.4);ax[0,col].axhline(10000,color='#8ca59c',ls='--',lw=.8);ax[0,col].set_title(('Nasdaq 100' if symbol=='USTEC' else 'S&P 500')+' — '+window)
   ax[1,col].fill_between(x,-d,0,color='#ff927b',alpha=.65);ax[1,col].set_ylabel('Closed-balance DD %')
   ax[0,col].set_ylabel('Closed balance USD')
   for a in ax[:,col]:a.grid(alpha=.3);a.tick_params(axis='x',rotation=20)
  fig.suptitle('Raw ORB | independent $10,000 accounts | 1% balance-risk target\nClosing curves exclude floating equity; native equity drawdown in table',fontsize=13)
  fig.tight_layout();path=ROOT/(window+'.png');fig.savefig(path,dpi=140);plt.close(fig)
  imgs[window]='data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()
 rows=[];md=['# Raw 15-minute opening-range breakout results','', 'Stopped for review. No optimisation or live EA changes. Last completed data day: 1 October 2026.','', '| Asset | Window | Return | Net PF | Win rate | Native equity DD | Trades | Daily closed Sharpe | Win/loss streak |','|---|---|---:|---:|---:|---:|---:|---:|---:|']
 for symbol in ('USTEC','US500'):
  for w in ('1y','3y','5y'):
   m=data[symbol][w];vals=[symbol,w,f"{m['return_pct']:+.2f}%",f"{m['pf']:.2f}",f"{m['win_rate_pct']:.1f}%",f"{m['native_equity_dd_pct']:.2f}%",str(m['trades']),f"{m['daily_closed_balance_sharpe']:.2f}",f"{m['streaks']['max_win']}/{m['streaks']['max_loss']}"]
   md.append('| '+' | '.join(vals)+' |');rows.append('<tr>'+''.join('<td>'+html.escape(v)+'</td>' for v in vals)+'</tr>')
 caveats=['One strategy configuration, two asset candidates, six overlapping performance runs plus a five-day implementation smoke check. No best-set selection or optimisation. Two asset candidates are conservatively counted for deflated Sharpe.',
 'NY 09:30–09:45 range; first subsequent completed M5 close outside range; stop opposite range boundary; no take-profit; close requested 15:55 NY. $10,000 per independent account, 1% current-balance risk target, rounded down; skip below minimum.',
 'Broker CFD adaptation, not broad stocks-in-play research and not exchange-volume ORB replication. Native model 4, 150ms delay, native costs; historic tick coverage is mixed as recorded below. History quality is a tester field, not proof of real ticks for the whole window.',
 'Daily closed-balance Sharpe annualises calendar-day realised returns at sqrt(365); not native MT5 Sharpe, floating-equity Sharpe or a forecast. Trade-net PF/win rate include entry and exit commission/swap; native floating-equity drawdown is shown separately.',
 'Closed-balance graphs are not floating-equity graphs. The symbols ran separately: no shared portfolio, FTMO limits, position overlap admission or payout simulation.',
 'The signal audit checks timestamps, NY DST, one entry/date, reported range-boundary stops, quoted risk and filled side/volume. It does not independently reconstruct every range from a second OHLC dataset.',
 'Five-year raw audits used 10,000 circular block-bootstrap paths, block length 5, plus deflated Sharpe with 2 asset candidates. These are resampling diagnostics, not forecasts. No separate broker-calibrated extra-cost stress or forward demo was run; missing costs were not invented. Both raw statistical screens failed.',
 'Timed exits can be unavailable around broker market closures. Latest-year carryovers: USTEC 15, US500 14. These trades and their costs are included, not deleted; this realised CFD implementation is not strictly flat every day. A session-aware pre-close version would be a separately frozen test after review.']
 md+=['','## Limitations','']+['- '+c for c in caveats]
 details=[]
 for symbol in ('USTEC','US500'):
  gate=data[symbol]['raw_gate'];line=symbol+': '+('PRELIMINARY RAW PASS (not full pipeline)' if gate['passed'] else 'RAW FAIL')
  md+=['','## '+line,'']+['- '+f for f in gate['failures']]
  a=data[symbol]['five_year_audit'];audit_text=f"5y statistical screen: DSR {a['deflated_sharpe_probability_pct']:.1f}% (gate 95%); bootstrap PF 5th percentile {a['bootstrap_pf_p05']:.3f}; bootstrap return 5th percentile {a['bootstrap_return_p05_pct']:+.2f}%. Neither candidate meets the user's preferred PF >=1.2."
  md+=['',audit_text]
  parts=[]
  for w in ('1y','3y','5y'):
   m=data[symbol][w];text=f"{w}: {m['history_quality']}; costs ${m['costs']:.2f}; carryovers {m['carryover_positions']}; late exits {m['late_exit_positions']}; native Sharpe {m['native_sharpe']}; flags {json.dumps(m['flags'])}."
   md+=['',text]+m['tick_coverage_notes']+m['symbol_specs']
   parts.append('<h4>'+w+'</h4><p>'+html.escape(text)+'</p><pre>'+html.escape('\n'.join(m['tick_coverage_notes']+m['symbol_specs']+m['execution_summary']))+'</pre>')
  details.append('<section><h2>'+html.escape(line)+'</h2><p>'+html.escape('; '.join(gate['failures']) or 'Further validation required.')+'</p><p>'+html.escape(audit_text)+'</p><details><summary>Execution and data coverage</summary>'+''.join(parts)+'</details></section>')
 (ROOT/'REPORT.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
 page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calyx | Raw ORB results</title><style>body{background:#091713;color:#eef7f2;font:16px/1.55 system-ui;margin:auto;max-width:1300px;padding:36px}h1{font-size:clamp(30px,5vw,54px);line-height:1.15}h2{color:#72f6cb}p,li{color:#bfd2cb}section{background:#0e211c;border:1px solid #315047;border-radius:18px;padding:24px;margin:24px 0}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:13px;text-align:right;border-bottom:1px solid #315047}td:first-child,th:first-child{text-align:left}.table{overflow:auto}.tag{color:#72f6cb;text-transform:uppercase;letter-spacing:2px;font-size:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}img{width:100%;height:auto}a{color:#72f6cb}summary{cursor:pointer}.warning{border-color:#987645}</style><body><p class="tag">Calyx research · idea 1 of 5 · unoptimised</p><h1>Opening-range breakout.<br>Raw results, before filters.</h1><p>Through 1 October 2026. Six native tests on independent accounts. No live changes.</p><section class="warning"><h2>Stopped for your review</h2><p>Historical simulation, not a forecast. A video tier ranking does not establish an edge. No parameter search, no deployment and no move to VWAP yet.</p></section><section><h2>One-, three- and five-year performance</h2><div class="table"><table><thead><tr>'''+''.join('<th>'+s+'</th>' for s in ('Asset','Window','Return','Net PF','Win rate','Equity DD','Trades','Daily closed Sharpe','Win/loss streak'))+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div></section>'+''.join(details)+''.join('<section><h2>'+w+' closing-trade curves</h2><img alt="'+w+' independent ORB closing balances and drawdowns" src="'+imgs[w]+'"></section>' for w in ('5y','3y','1y'))+'<section><h2>Frozen rules and evidence limits</h2><ul>'+''.join('<li>'+html.escape(c)+'</li>' for c in caveats)+'</ul><p><a href="RULES.md">Frozen protocol</a> · <a href="RESULTS.json">Results</a> · <a href="VERIFICATION.json">Signal verification</a></p></section></body></html>'
 (ROOT/'Results.html').write_text(page,encoding='utf-8')
 print(json.dumps({s:{w:{k:data[s][w][k] for k in ('return_pct','pf','win_rate_pct','native_equity_dd_pct','trades','daily_closed_balance_sharpe','carryover_positions')} for w in ('1y','3y','5y')} for s in data},indent=2))
 print('Report saved. Stopped for review.',flush=True)
if __name__=='__main__':main()
