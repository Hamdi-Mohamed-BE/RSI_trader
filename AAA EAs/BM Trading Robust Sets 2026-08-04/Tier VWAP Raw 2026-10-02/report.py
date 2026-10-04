"""Offline scientific report of frozen raw native tests, not a website promotion."""
import base64,gzip,html,io
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from native import ROOT,OUT,load,save,ledger
def table(headers,rows):
 return '<div class="table"><table><thead><tr>'+''.join('<th>'+html.escape(str(v))+'</th>' for v in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def image(path):return 'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()
def curve(row):
 d=ledger(row).sort_values(['close_epoch','position_id']);return [pd.Timestamp(row['start'].replace('.','-'))]+list(pd.to_datetime(d.close_epoch,unit='s')),np.r_[10000,10000+d.net_profit.cumsum().to_numpy()]
def main():
 rows=load(ROOT/'SUMMARY.json');audits=load(ROOT/'AUDIT SUMMARY.json');verified=load(ROOT/'VERIFICATION.json');by={r['stage']:r for r in rows}
 decisions={}
 for symbol in ['USTEC','US500']:
  gate=all(by[symbol+'-'+w]['stats']['net']>0 and by[symbol+'-'+w]['stats']['pf']>1 and by[symbol+'-'+w]['stats']['trades']>=30 and by[symbol+'-'+w]['clean'] for w in ['3y','5y'])
  decisions[symbol]={'raw_3y_5y_gate_pass':gate,'latest_year_positive':by[symbol+'-1y']['stats']['net']>0,'live_eligible':False}
 save(ROOT/'DECISION.json',dict(assets=decisions,optimisation_started=False,next_idea_started=False,active_eas_changed=False))
 plt.rcParams.update({'figure.facecolor':'#091713','axes.facecolor':'#0e211c','axes.edgecolor':'#315047','text.color':'#eef7f2','axes.labelcolor':'#bdcfca','xtick.color':'#bdcfca','ytick.color':'#bdcfca','grid.color':'#315047','font.size':10})
 plots=[]
 for symbol,label in [('USTEC','Nasdaq / US100'),('US500','S&P 500')]:
  fig,axes=plt.subplots(2,2,figsize=(14,8),gridspec_kw={'height_ratios':[2,1]})
  for col,w in enumerate(['5y','1y']):
   row=by[symbol+'-'+w];dates,balance=curve(row);peak=np.maximum.accumulate(balance);dd=100*(peak-balance)/peak
   axes[0,col].plot(dates,balance,color='#72f6cb',lw=1.2);axes[0,col].axhline(10000,color='#8ca59c',ls='--',lw=.7);axes[0,col].set_title(label+' — '+('five years' if w=='5y' else 'latest year'));axes[0,col].set_ylabel('Closed balance USD')
   axes[1,col].fill_between(dates,-dd,0,color='#ff927b',alpha=.6);axes[1,col].set_ylabel('Closed balance DD %')
   for a in axes[:,col]:a.grid(alpha=.25)
  fig.suptitle('Raw VWAP band reclaim | $10,000 independent account | 1% requested balance risk\nHistorical simulations, not an expected return; adverse fills can exceed risk target');fig.autofmt_xdate();fig.tight_layout();name=symbol+'-curves.png';fig.savefig(ROOT/name,dpi=140);plt.close(fig);plots.append((label+' closing balance',name))
 fig,axes=plt.subplots(2,2,figsize=(14,8),sharex='col',gridspec_kw={'height_ratios':[2,1]})
 for col,symbol in enumerate(['USTEC','US500']):
  row=by[symbol+'-5y'];t=pd.read_csv(io.BytesIO(gzip.decompress((OUT/row['stage']/'0-trace.csv.gz').read_bytes())))
  t['day']=pd.to_datetime(t.epoch,unit='s').dt.normalize();v=t.groupby('day').agg(low=('equity','min'),high=('equity','max'),last=('balance','last'))
  peak=np.maximum.accumulate(np.r_[10000,t.equity.to_numpy()])[1:];t['dd']=100*(peak-t.equity)/peak;dd=t.groupby('day').dd.max()
  axes[0,col].fill_between(v.index,v.low,v.high,color='#72f6cb',alpha=.3);axes[0,col].plot(v.index,v['last'],color='#72f6cb',lw=.9);axes[0,col].set_title(symbol+' sampled floating equity');axes[0,col].set_ylabel('USD')
  axes[1,col].fill_between(dd.index,-dd,0,color='#ff927b',alpha=.6);axes[1,col].set_ylabel('Sampled equity DD %')
  for a in axes[:,col]:a.grid(alpha=.25)
 fig.suptitle('Independent native accounts, NOT a combined portfolio\nDaily min/max band from minute equity samples; exact native tick-path DD in table');fig.autofmt_xdate();fig.tight_layout();fig.savefig(ROOT/'floating-equity.png',dpi=140);plt.close(fig);plots.append(('Floating equity evidence','floating-equity.png'))
 headers=['Asset / window','Net return','Net PF','Win rate','Native equity DD','Trades','Closed Sharpe','Max win/loss run','Carryovers']
 results=[]
 for r in rows:
  s=r['stats'];results.append([r['stage'],f"{s['return_pct']:+.2f}%",f"{s['pf']:.3f}",f"{s['win_pct']:.1f}%",f"{s['equity_dd_pct']:.2f}%",s['trades'],s['sharpe'],f"{s['max_win_streak']}/{s['max_loss_streak']}",r['net']['carryovers']])
 details=[[r['stage'],r['native_metrics']['history_quality'],r['net']['signals'],r['net']['skips'],r['net']['entry_fail'],r['net']['close_fail'],r['net']['boundary']] for r in rows]
 checks=[[name,a['verdict'],f"{a['metrics']['deflated_sharpe_pct']:.1f}%",f"{a['bootstrap']['probability_profit_pct']:.1f}%",f"{a['bootstrap']['profit_factor_p05']:.3f}",f"{a['bootstrap']['return_p05_pct']:+.2f}%"] for name,a in audits.items()]
 limitations=[
 'The video names VWAP mean reversion but supplies no rules. This is one explicitly frozen interpretation, not proof for or against every VWAP strategy. No optimisation was run.',
 'Broker CFD feed; typical-price VWAP weighted by tick counts, not NQ/ES exchange volume. Each signal uses only completed M1 bars from 09:30 NY through the completed M5 signal; market order occurs afterwards.',
 'Native Model 4, 150 ms delay. Actual broker real ticks begin 2026-01-01; earlier history uses generated ticks. Native percentage labels are shown for each report; the six-month window is the cleanest real-tick evidence.',
 'Independent $10,000 tests, 1% current-balance risk before fees and adverse fill changes. Lot size is rounded down and below-minimum trades skipped. Initial filled risk reached almost 1.96% of balance on Nasdaq and 1.31% on S&P500 due to tight distances and fill movement. Fees/gaps can increase losses further. No minimum-lot override.',
 'SL and fixed VWAP TP approximately 1:1 at entry quote after tick rounding. No trailing stop, breakeven, martingale or grid. Native commission/spread/swap included. Broker-measured incremental execution-cost stress missing, so promotion is blocked.',
 'Close requested at 15:30 NY, or 10 minutes before current weekday broker session endpoint. Current schedule is not a historical holiday calendar. Any carryovers/end-of-test exits are disclosed and retained in the results.',
 'Windows overlap and share previously researched market history: these are configuration-frozen raw comparisons, not a pristine out-of-sample validation. A different 3SD-touch VWAP study previously tried 108 variants and failed. DSR with 2 candidates covers only the current asset comparison; broader idea-selection bias remains.',
 'Closed Sharpe uses daily closed-balance returns, calendar days, square-root-of-365 annualisation. Floating equity is sampled once per minute for plots; table equity DD comes from the native tick path, not estimated from closed trades.',
 '10,000 block-bootstrap paths, block length 5. Resampling/DSR are diagnostics, not forecasts. Internal 5%/10% closed-P&L risk proxies are not FTMO pass probabilities or payout expectations.',
 'No active EA, BAT, website, broker account, portfolio, FTMO settings or Git remote changed. Stop for review before optimisation or idea 3.'
 ]
 total=sum(x['positions'] for x in verified);bars=sum(x['m1_bars'] for x in verified);maxrisk=max(x['max_filled_risk_to_budget'] for x in verified)
 conclusion='Both assets fail the raw gate.' if not any(x['raw_3y_5y_gate_pass'] for x in decisions.values()) else 'See separate raw gates; no asset is promoted for live trading.'
 evidence=f'Independent reconstruction checked {total:,} closed positions and {bars:,} exported M1 inputs across overlapping runs. Signal VWAP/SD, M5 extrema, causal timestamps, stops/targets and ledger totals passed. S&P500 rejected one entry on 9 September 2026 with native invalid-stops retcode10016, repeated in each overlapping window; this was not treated as a fill or silently retried. Its clean-execution flag remains false. Maximum filled initial stop risk / selected budget: {maxrisk:.3f}×. Four unit tests passed.'
 settings='Anchor at 09:30 NY; first completed M5 rejection/reclaim of ±2 weighted SD after 10:00 and before 15:00; buy lower-band rejection or sell upper-band rejection. Enter next tick, target signal-close VWAP, 1:1 initial stop. One signal attempt per day, 1% current-balance requested risk; request flat at 15:30 NY or session pre-close.'
 css='body{background:#091713;color:#eef7f2;font:16px/1.55 system-ui;margin:auto;max-width:1300px;padding:36px}h1{font-size:clamp(30px,4vw,50px);line-height:1.2}h2,a{color:#72f6cb}p,li{color:#bfd2cb}section{background:#0e211c;border:1px solid #315047;border-radius:18px;padding:24px;margin:24px 0}table{border-collapse:collapse;width:100%;font-size:13px}td,th{padding:11px;text-align:right;border-bottom:1px solid #315047}td:first-child,th:first-child{text-align:left}.table{overflow:auto}img{width:100%;height:auto}.warning{border-color:#987645}.tag{color:#72f6cb;letter-spacing:2px;font-size:12px}'
 page='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calyx | Raw VWAP mean reversion</title><style>'+css+'</style></head><body><p class="tag">CALYX RESEARCH · IDEA2 · RAW NATIVE BASELINE</p><h1>VWAP mean reversion</h1><p>Through1October2026. Nasdaq and S&P500, independently tested.</p><section class="warning"><h2>'+conclusion+'</h2><p>These results do not establish a tradable edge. Historical simulations, not forecasts. Active EAs unchanged.</p></section><section><h2>Frozen rules</h2><p>'+html.escape(settings)+'</p><a href="PROTOCOL.txt">Complete protocol</a></section><section><h2>Results</h2>'+table(headers,results)+'</section>'+''.join('<section><h2>'+label+'</h2><img src="'+image(ROOT/name)+'" alt="'+label+'"></section>' for label,name in plots)+'<section><h2>Enhanced audit</h2>'+table(['Window','Verdict','DSR probability','Bootstrap profit probability','PF p05','Return p05'],checks)+'</section><section><h2>Native coverage and execution</h2>'+table(['Window','Native history quality','Signals','Skipped','Entry errors','Close errors','Boundary exits'],details)+'</section><section><h2>Verification and limits</h2><p>'+html.escape(evidence)+'</p><ul>'+''.join('<li>'+html.escape(v)+'</li>' for v in limitations)+'</ul><p><a href="SUMMARY.json">Native result manifests</a> · <a href="VERIFICATION.json">Independent verification</a> · <a href="AUDIT SUMMARY.json">Statistical gates</a></p></section></body></html>'
 page=page.replace('Through1October2026','Through 1 October 2026').replace('IDEA2','IDEA 2').replace('retcode10016','retcode 10016')
 (ROOT/'Results.html').write_text(page,encoding='utf-8')
 md=['# VWAP mean reversion — raw baseline','',conclusion,'',settings,'','| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,r))+' |' for r in results]+['',evidence,'','## Limitations','']+['- '+v for v in limitations]
 (ROOT/'REPORT.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
 save(ROOT/'REPORT DATA.json',dict(results=results,audits=checks,coverage=details,decisions=decisions))
 print(conclusion);print(results)
if __name__=='__main__':main()
