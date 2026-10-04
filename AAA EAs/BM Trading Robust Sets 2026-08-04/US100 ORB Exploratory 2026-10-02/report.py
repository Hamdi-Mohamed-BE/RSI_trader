"""Standalone native research comparison; no website/cache changes."""
from pathlib import Path
from datetime import datetime,timezone
import base64,gzip,html,io,json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from native import ROOT,OUT,load,save,ledger

RAW=ROOT.parent/'Tier ORB Raw 2026-10-02'
def raw_series(window):
 t=load(RAW/'native'/('USTEC-'+window)/'trades.json')
 d=pd.DataFrame(t);d['date']=pd.to_datetime(d.close_time);d['balance']=10000+d.net_profit.cumsum()
 return d
def curve(row):
 d=ledger(row).sort_values(['close_epoch','position_id']);d['date']=pd.to_datetime(d.close_epoch,unit='s');d['balance']=10000+d.net_profit.cumsum()
 return d
def img(path):return 'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()
def rowvals(label,s,carry=None):
 return [label,f"{s['return_pct']:+.2f}%",f"{s['pf']:.3f}",f"{s['win_pct']:.1f}%",f"{s['equity_dd_pct']:.2f}%",str(s['trades']),f"{s['sharpe']:.2f}" if s['sharpe'] is not None else 'n/a',f"{s['max_win_streak']}/{s['max_loss_streak']}",str(carry) if carry is not None else 'n/a']
def table(headers,rows):return '<div class="table"><table><thead><tr>'+''.join('<th>'+html.escape(str(v))+'</th>' for v in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def main():
 summary=load(ROOT/'SUMMARY.json');audits=load(ROOT/'AUDIT SUMMARY.json');verification=load(ROOT/'VERIFICATION.json');r=summary['results'];p=summary['primary']['parameters'];dev=summary['primary']['development']
 raw=load(RAW/'RESULTS.json')['symbols']['USTEC']
 primary=[]
 for label,row in [('Development: 2021–24',dev),('Validation: 2024–25',r['validation']),('Locked latest year',r['locked-1y']),('Latest 6 months',r['recent-6m']),('Full 3 years: exploratory',r['full-3y']),('Full 5 years: exploratory',r['full-5y'])]:primary.append(rowvals(label,row['stats'],row['net']['carryovers']))
 original=lambda w:dict(return_pct=raw[w]['return_pct'],pf=raw[w]['pf'],win_pct=raw[w]['win_rate_pct'],equity_dd_pct=raw[w]['native_equity_dd_pct'],trades=raw[w]['trades'],sharpe=raw[w]['daily_closed_balance_sharpe'],max_win_streak=raw[w]['streaks']['max_win'],max_loss_streak=raw[w]['streaks']['max_loss'])
 comparison=[]
 for w,name in [('1y','Latest year'),('5y','Full 5 years')]:
  comparison.append(rowvals(name+' — original raw',original(w),raw[w]['carryover_positions']))
  rr=r['safe-raw-'+w];comparison.append(rowvals(name+' — pre-close raw',rr['stats'],rr['net']['carryovers']))
  rr=r['locked-1y' if w=='1y' else 'full-5y'];comparison.append(rowvals(name+' — selected version',rr['stats'],rr['net']['carryovers']))
 headers=['Period/version','Return','Net PF','Win rate','Native equity DD','Trades','Daily closed Sharpe','Win/loss streak','Carryovers']
 failure=[k for k,v in audits['locked-1y']['gates'].items() if not v]
 decision={'status':'EXPLORATORY ONLY — latest-year profitability failed','live_eligible':False,'latest_year_failed_gates':failure,'chosen_on':'development only; frozen before validation/test','parameters':p,'tested_configurations':summary['trials']['total'],'no_live_changes':True}
 save(ROOT/'DECISION.json',decision)
 plt.rcParams.update({'figure.facecolor':'#091713','axes.facecolor':'#0e211c','axes.edgecolor':'#315047','text.color':'#eef7f2','axes.labelcolor':'#bdcfca','xtick.color':'#bdcfca','ytick.color':'#bdcfca','grid.color':'#315047','font.size':10})
 colors=['#aebdb8','#ffbe7b','#72f6cb'];fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True,gridspec_kw={'height_ratios':[2,1]})
 for d,label,color in [(raw_series('5y'),'Original raw',colors[0]),(curve(r['safe-raw-5y']),'Session-aware raw',colors[1]),(curve(r['full-5y']),'Development-selected version',colors[2])]:
  dates=[pd.Timestamp('2021-10-02')]+list(d.date);balance=np.r_[10000,d.balance.to_numpy()]
  axes[0].plot(dates,balance,label=label,color=color,lw=1.2)
  peak=np.maximum.accumulate(balance);dd=100*(peak-balance)/peak;axes[1].plot(dates,-dd,color=color,lw=1)
 axes[0].axhline(10000,color='#8ca59c',lw=.8,ls='--');axes[0].legend();axes[0].set_ylabel('Closed balance USD');axes[1].set_ylabel('Closed balance DD %')
 axes[0].set_title('US100 ORB | $10,000 starts | 1% balance risk\nFull five-year comparison includes development data, not an OOS return claim')
 for a in axes:a.grid(alpha=.3)
 fig.tight_layout();fig.savefig(ROOT/'five-year-comparison.png',dpi=140);plt.close(fig)
 fig,axes=plt.subplots(2,1,figsize=(12,7),gridspec_kw={'height_ratios':[2,1]})
 for d,label,color in [(raw_series('1y'),'Original raw',colors[0]),(curve(r['safe-raw-1y']),'Session-aware raw',colors[1]),(curve(r['locked-1y']),'Frozen selected version',colors[2])]:
  axes[0].plot([pd.Timestamp('2025-10-02')]+list(d.date),np.r_[10000,d.balance.to_numpy()],label=label,color=color,lw=1.2)
 axes[0].axhline(10000,color='#8ca59c',lw=.8,ls='--');axes[0].legend();axes[0].set_ylabel('Closed balance USD');axes[0].set_title('Configuration-locked latest year | 2 Oct 2025 – 1 Oct 2026\nNo retuning after looking at this result; market history was previously researched')
 d=curve(r['locked-1y']);monthly=d.groupby(d.date.dt.to_period('M')).net_profit.sum();axes[1].bar(range(len(monthly)),monthly.values,color=['#72f6cb' if x>0 else '#ff927b' for x in monthly.values]);axes[1].set_xticks(range(len(monthly)),[str(x) for x in monthly.index],rotation=35);axes[1].set_ylabel('Selected monthly USD');axes[1].axhline(0,color='#8ca59c',lw=.8)
 for a in axes:a.grid(alpha=.3)
 fig.tight_layout();fig.savefig(ROOT/'locked-year-comparison.png',dpi=140);plt.close(fig)
 # One-minute sampled floating equity trace is NOT a tick-perfect equity graph.
 row=r['full-5y'];tp=OUT/row['stage']/f"{row['index']}-trace.csv.gz"
 trace=pd.read_csv(io.BytesIO(gzip.decompress(tp.read_bytes())));trace['day']=pd.to_datetime(trace.epoch,unit='s').dt.normalize()
 daily=trace.groupby('day').agg(equity_min=('equity','min'),equity_max=('equity','max'),balance_last=('balance','last'))
 peak=np.maximum.accumulate(trace.equity.to_numpy());trace['sampled_dd']=100*(peak-trace.equity)/peak;dd=trace.groupby('day').sampled_dd.max()
 fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True,gridspec_kw={'height_ratios':[2,1]})
 axes[0].fill_between(daily.index,daily.equity_min,daily.equity_max,color='#72f6cb',alpha=.28,label='Daily min/max from 1-minute equity samples');axes[0].plot(daily.index,daily.balance_last,color='#72f6cb',lw=1,label='Daily last balance');axes[0].legend();axes[0].set_ylabel('USD');axes[0].set_title('Selected ORB — floating-equity evidence\nMinute-sampled graph; exact native tick-path equity DD shown separately in table')
 axes[1].fill_between(dd.index,-dd,0,color='#ff927b',alpha=.6);axes[1].set_ylabel('Sampled equity DD %')
 for a in axes:a.grid(alpha=.3)
 fig.tight_layout();fig.savefig(ROOT/'selected-floating-equity.png',dpi=140);plt.close(fig)
 target=load(ROOT/'STAGE-target.json')['candidates'];targetrows=[]
 for row in target:
  s=row['stats'];targetrows.append([str(row['parameters']['rr'])+'R' if row['parameters']['rr'] else 'Timed only',f"{s['return_pct']:+.2f}%",f"{s['pf']:.3f}",f"{s['win_pct']:.1f}%",f"{s['equity_dd_pct']:.2f}%",str(s['trades'])])
 searchrows=[]
 for name in ('target','range','cutoff','direction','ema'):
  for row in load(ROOT/('STAGE-'+name+'.json'))['candidates']:
   c=row['parameters'];s=row['stats'];searchrows.append([name,str(c['opening_minutes']),str(c['rr']),str(c['entry_cutoff']),str(c['direction']),str(c['ema']),f"{s['return_pct']:+.2f}%",f"{s['pf']:.3f}",f"{s['win_pct']:.1f}%",str(s['trades'])])
 auditrows=[]
 for name,a in audits.items():
  m=a['metrics'];b=a['bootstrap'];auditrows.append([name,a['verdict'],f"{m['deflated_sharpe_pct']:.1f}%",f"{b['profit_factor_p05']:.3f}",f"{b['return_p05_pct']:+.2f}%",f"{b['probability_profit_pct']:.1f}%"])
 stress=[rowvals('150ms locked year',r['locked-1y']['stats'],r['locked-1y']['net']['carryovers']),rowvals('500ms sensitivity',r['delay-500ms-1y']['stats'],r['delay-500ms-1y']['net']['carryovers'])]
 coverage=[[name,row['native_metrics']['history_quality'],row['start']+' to '+row['end']] for name,row in r.items()]
 settings=f"15-minute range 09:30–09:45 NY; LONG ONLY; previous completed H1 close above EMA100; first later completed M5 close above range high; market entry next tick; SL at range low; target 3R; last entry before 15:30 NY. Exit requested at 15:55 NY or 10 minutes before the current broker weekday session endpoint, whichever is earlier. One qualifying signal attempt per NY day. Risk remains 1% of balance, rounded down, skip below minimum. No trailing, breakeven, grid or martingale."
 caveats=[f"{summary['trials']['total']} unique tested settings counted, including prior raw US500 candidate, controls and delay sensitivity; repeated periods and model confirmations do not create new alpha settings. This is a bounded one-factor staged search, not an exhaustive global optimum.",
 'Opening range, target, entry cutoff, direction and simple H1 EMA filter were selected only on 2021-10-02–2024-10-01 development data. Native M1-OHLC screening followed by model-4 development confirmation of three frozen alternatives. One primary locked before validation/test; no adjustment after the latest-year loss.',
 'Broker CFD history, not NQ futures. Selected five-/three-/one-year native history-quality fields report 14%/23%/60% real ticks respectively, including the 90-day warmup; latest 6-month report is 100% real ticks and validation is 0%. The original raw reports had no warmup and reported 15%/25%/75%. These denominators differ, not the underlying broker feed. Model 4 does not make older generated ticks real. Historical market data had already been researched, so this is not a pristine untouched holdout.',
 'Native market spreads, commission and swaps included. Risk budget excludes fees and gap/slippage. Extra execution delay is an illustrative native sensitivity, not a broker-measured cost calibration; the mandatory calibrated-extra-cost promotion gate remains incomplete.',
 'The current broker weekday session schedule is not a historical holiday or seasonal calendar. Carryovers remain and are included in profits, swaps and drawdowns. Operational improvement is reported separately from entry/target/filter changes.',
 'Five-year and three-year selected totals include development data and overlap the latest year: they are exploratory illustrations, not independent out-of-sample proofs. The latest-year negative return and PF below 1 outweigh an attractive full-history curve.',
 'Reported Sharpe annualises calendar-day closed-balance returns at sqrt(365). Native MT5 Sharpe is stored separately in evidence. Native equity DD includes floating losses; plotted balances exclude them except the explicitly minute-sampled equity figure.',
 '10,000 circular block-bootstrap paths, block length 5, Wilson intervals and DSR corrected for all campaign settings. Resampling is a diagnostic, not a return forecast. Closed-P&L prop breach proxies in audit JSON are not FTMO pass/payout predictions.',
 'No forward demo, prospective data holdout, deployment, active-EA change, website update, Git push or other tier-list strategy started.']
 title='US100 ORB: risk improved, latest-year edge did not survive'
 page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calyx | US100 ORB exploratory optimisation</title><style>body{background:#091713;color:#eef7f2;font:16px/1.55 system-ui;margin:auto;max-width:1300px;padding:36px}h1{font-size:clamp(30px,4.5vw,52px);line-height:1.15}h2{color:#72f6cb}p,li{color:#bfd2cb}section{background:#0e211c;border:1px solid #315047;border-radius:18px;padding:24px;margin:24px 0}table{border-collapse:collapse;width:100%;font-size:13px}td,th{padding:12px;text-align:right;border-bottom:1px solid #315047}td:first-child,th:first-child{text-align:left}.table{overflow:auto}.tag{color:#72f6cb;text-transform:uppercase;letter-spacing:2px;font-size:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}img{width:100%;height:auto}a{color:#72f6cb}summary{cursor:pointer}.warning{border-color:#987645}</style><body><p class="tag">Calyx research · exploratory after raw failure · US100 only</p><h1>'''+title+'</h1><p>Through 1 October 2026. $10,000 starting capital, 1% balance risk. Selected on development, then frozen.</p><section class="warning"><h2>Not ready for live trading</h2><p>Original latest-year loss −9.61%, equity DD 31.70%. Selected loss −1.69%, equity DD 9.82%, PF 0.958. Risk and loss size improved, but the latest year remains unprofitable. No promotion or retuning.</p></section><section><h2>Development-selected settings</h2><p>'+html.escape(settings)+'</p><a href="FROZEN PRIMARY.json">Frozen primary configuration</a></section><section><h2>Chronology and selected performance</h2>'+table(headers,primary)+'</section><section><h2>Separate operational control and strategy improvement</h2>'+table(headers,comparison)+'</section>'+''.join('<section><h2>'+caption+'</h2><img src="'+img(ROOT/name)+'" alt="'+caption+'"></section>' for caption,name in [('Five-year closing-balance comparison','five-year-comparison.png'),('Configuration-locked latest year','locked-year-comparison.png'),('Native sampled floating equity','selected-floating-equity.png')])+'<section><h2>Why not choose a smaller target just for win rate?</h2><p>This first-stage comparison kept the 15-minute range, both directions and no EMA filter. Development screening only (M1 OHLC); not current-year income predictions. 0.5R raised win rate to 63.7% but lost money with PF 0.909. Higher win rate alone did not create an edge.</p>'+table(['Target','Return','Net PF','Win rate','Equity DD','Trades'],targetrows)+'</section><section><h2>Native execution-delay sensitivity</h2><p>Illustrative delay sensitivity; not measured live broker costs.</p>'+table(headers,stress)+'</section><section><h2>Raw statistical gates after optimisation</h2>'+table(['Window','Audit verdict','Deflated Sharpe probability','Bootstrap PF p05','Bootstrap return p05','Bootstrap profit probability'],auditrows)+'</section><section><details><summary>All staged development trials</summary>'+table(['Stage','OR minutes','Target R','Cutoff minute NY','Direction','H1 EMA','Return','PF','Win rate','Trades'],searchrows)+'</details></section><section><h2>Evidence limits</h2><ul>'+''.join('<li>'+html.escape(v)+'</li>' for v in caveats)+'</ul><p>'+str(verification['closed_positions_checked'])+' closed positions and '+str(verification['filled_signals_checked'])+' filled signals independently checked against exports.</p><p><a href="PROTOCOL.txt">Frozen protocol</a> · <a href="SUMMARY.json">All native results</a> · <a href="VERIFICATION.json">Verification</a> · <a href="TRIAL ACCOUNTING.json">Trial accounting</a></p></section></body></html>'
 (ROOT/'Results.html').write_text(page,encoding='utf-8')
 md=['# '+title,'','Exploratory only. No deployment.','',settings,'','| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(v)+' |' for v in primary]+['','## Raw versus selected','']+['| '+' | '.join(v)+' |' for v in comparison]+['','## Limitations','']+['- '+v for v in caveats]
 (ROOT/'REPORT.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
 save(ROOT/'REPORT DATA.json',dict(primary=primary,comparison=comparison,audits=auditrows,delay_stress=stress,decision=decision))
 print(json.dumps({'parameters':p,'performance':primary,'comparison':comparison,'decision':decision},indent=2),flush=True)
if __name__=='__main__':main()
