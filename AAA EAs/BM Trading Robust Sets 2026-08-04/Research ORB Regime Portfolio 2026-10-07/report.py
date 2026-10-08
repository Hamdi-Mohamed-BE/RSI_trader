"""No selection: audit locked executions and create the user-facing report."""
from pathlib import Path
from datetime import datetime
import html,json,math
import sys
import pandas as pd,numpy as np
import runner as r,evidence as a
R=r.R;C=r.CONFIG
LABELS={'raw':'Plain M15 ORB control','breakout':'Developed breakout','reversal':'Developed reversal','hybrid':'Regime-routed two-module system'}
SOURCES=[
 ('University of St Gallen / SFI ORB working paper','https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content','Opening relative volume and ATR are research hypotheses; stock-universe results do not establish CFD profitability. This is a working paper, not a claimed peer-reviewed guarantee.'),
 ('Lundstrom, Day trading returns across volatility states','https://umu.diva-portal.org/smash/get/diva2%3A732318/FULLTEXT02.pdf','Volatility-dependent ORB hypothesis; not an exact replication of the paper.'),
 ('CME CVOL overview','https://www.cmegroup.com/market-data/cme-group-benchmark-administration/cme-group-volatility-indexes.html','Actual surface features include skew, convexity and ATM volatility. Historical licensed data are not present; these features were NOT fabricated or used.')]
SOURCES.append(('Exness server clock documentation','https://get.exness.help/hc/en-us/articles/360014390760-What-is-the-default-timezone-set-for-MetaTrader','Exness documents GMT+0 server time. The EA converts UTC to New York wall clock using US DST rules. Gold uses the 09:30 NY session anchor; this is not a claim that gold itself opens at the stock-market bell.'))
def window(row,start):
 df,day,ret=a.equity(row);begin=pd.Timestamp(start);prev=day[day.index<begin]
 initial=float(prev.iloc[-1].equity) if len(prev) else 10000
 d=day[day.index>=begin];rs=d.equity.pct_change();rs.iloc[0]=d.iloc[0].equity/initial-1
 ts=[t for t in row['trades'] if t['open_epoch']>=begin.timestamp()]
 p=[t['net_profit'] for t in ts];wm,lm=a.a.streaks(p)
 sampled=df[df.epoch>=begin.timestamp()].equity.to_numpy();peaks=np.maximum.accumulate(np.r_[initial,sampled])[1:]
 dd=float(max(1-sampled/peaks)*100) if len(sampled) else 0
 full=start==row['start'];wr=sum(v>0 for v in p)/len(p)*100 if p else 0
 m=dict(trades=len(p),return_pct=(float(d.iloc[-1].equity)/initial-1)*100,pf=a.a.profit_factor(p),win_rate_pct=wr,
  sharpe=a.a.sharpe_statistics(rs.tolist(),1,365)['annualized_sharpe'],equity_dd=row['metrics']['equity_dd'] if full else dd,
  dd_kind='Native every-tick' if full else 'Minute-sampled subwindow (may understate intraminute DD)',
  max_win_streak=wm,max_loss_streak=lm,average_trade=float(sum(p)/len(p)) if p else 0,
  start=start,actual_end=str(d.index[-1].date()),rebase_equity=initial,closed_pnl=sum(p),
  note='Subwindow of the same 1% equity-risk native account, rebased at period start; not a fresh independently reoptimised run.')
 return m
def module_stats(row):
 d=pd.read_csv(a.path_for(row,'decisions'));entries=d[d.reason.isin(['breakout_entry','reversal_entry'])]
 result={}
 for kind,name in [(0,'breakout'),(1,'reversal')]:
  selected=entries[entries.module==kind];p=[]
  for t in row['trades']:
   hits=selected[(selected.epoch-t['open_epoch']).abs()<=1]
   if len(hits):p.append(t['net_profit'])
  result[name]=dict(trades=len(p),net=sum(p),pf=a.a.profit_factor(p),win_rate_pct=sum(v>0 for v in p)/len(p)*100 if p else 0)
 assert sum(x['trades'] for x in result.values())==len(row['trades'])
 return result
def rules(p):
 end_minute=570+int(p['range_minutes']);end_clock=f'{end_minute//60:02d}:{end_minute%60:02d}'
 stop=f"{100*p['stop_atr']:.0f}% of previous completed D1 ATR(14)" if p['stop_atr'] else 'Breakout: opposite OR boundary. Reversal: failed-break extreme + 0.1 M5 ATR(14).'
 return [('Opening range',f"09:30–{end_clock} New York, DST-aware; completed M5 bars"),
  ('Entries','Breakout: first completed M5 close outside the OR. Reversal: close outside then the following close back inside; trade toward opposite range boundary.'),
  ('Module',LABELS[{0:'breakout',1:'reversal',2:'hybrid'}[int(p['module'])]]),
  ('Relative volume','OFF' if not p['rvol_min'] else f"Opening tick-volume / mean of prior 20 opening windows ≥ {p['rvol_min']}; minimum 14 historical sessions"),
  ('ATR-normalised range','OFF' if not p['range_min'] and not p['range_max'] else f"OR width / previous D1 ATR(14) between {p['range_min']} and {p['range_max']}"),
  ('Markov',f"Directional/sideways gate {'ON' if p['markov'] else 'OFF'}; hybrid routing always uses prior completed D1 state: Sideways with P(next Sideways)≥50% → reversal; otherwise breakout."),
  ('Markov definition','20-day completed-close return: Bull > +2%, Bear < −2%, otherwise Sideways. Up to 1000 historical transitions, Laplace smoothing; no full-sample HMM.'),
  ('Stop',stop),('Targets',f"Breakout {p['target_r']}R; reversal opposite OR edge (variable RR, not a fixed-R target)."),
  ('Trail','OFF' if not p['trail_atr'] else f"M5 ATR(14) × {p['trail_atr']}, activates after +1R"),
  ('Risk and schedule',f"1% current equity target per trade, floor to broker lot step; skip below broker minimum. Maximum one trade/day, stop entries at {int(p['cutoff'])//100:02d}:{int(p['cutoff'])%100:02d} NY; attempt flatten from 15:55 NY. Broker session/holiday closures or absent ticks may cause carry until reopening: see execution audit. Gaps, execution slippage and fees can exceed the planned risk.")]
def table(headers,rows):return a.table(headers,rows)
def metrics_line(name,m):return [html.escape(name),m['trades'],a.pct(m['return_pct']),a.f(m['pf']),a.f(m['win_rate_pct'])+'%',a.f(m['equity_dd'])+'%',a.f(m['sharpe']),str(m['max_win_streak'])+' / '+str(m['max_loss_streak'])]
def chart(symbol,rows):
 colors=['#f9bf64','#58d6aa','#ab9aff','#66b6ff'];parts=['<svg viewBox="0 0 1050 345" role="img" aria-label="Native daily equity curves">']
 curves=[]
 for label in LABELS:
  _,d,_=a.equity(rows[symbol+' '+label]);curves.append((label,d.equity.to_numpy()))
 allv=np.concatenate([v for _,v in curves]);low=min(10000,allv.min());high=max(10000,allv.max());span=max(1,high-low)
 for j in range(5):
  y=280-58*j;val=low+span*j/4;parts.append(f'<path d="M80 {y} H1020" stroke="#2d443f"/><text x="2" y="{y+5}" fill="#a6bcb4">${val:,.0f}</text>')
 for j,(label,vals) in enumerate(curves):
  ids=np.unique(np.linspace(0,len(vals)-1,min(len(vals),1000)).astype(int));pts=' '.join(f'{80+940*i/max(1,len(vals)-1):.1f},{280-232*(vals[i]-low)/span:.1f}' for i in ids)
  parts.append(f'<polyline points="{pts}" fill="none" stroke="{colors[j]}" stroke-width="2"/><text x="{80+(j%2)*475}" y="{310+(j//2)*24}" fill="{colors[j]}">{html.escape(LABELS[label])}</text>')
 return ''.join(parts)+'</svg>'
def main():
 frozen=r.load(R/'CORRECTED FROZEN.json' if (R/'CORRECTED FROZEN.json').exists() else R/'FROZEN.json');rows=r.load(R/'EVALUATION.json');trials=frozen['unique_tested_configurations'];audits={};windows={};mods={}
 diagnostics=r.load(R/'CORRECTED DIAGNOSTICS.json') if (R/'CORRECTED DIAGNOSTICS.json').exists() else {}
 if '--render-only' in sys.argv:
  audits=r.load(R/'AUDIT.json');windows=r.load(R/'WINDOWS.json');mods=r.load(R/'MODULES.json')
 for i,(key,row) in ([] if '--render-only' in sys.argv else enumerate(rows.items())):
  audits[key]=a.audit(row,trials,26100700+i);audits[key]['data_quality']=a.quality(row)
  symbol=key.split()[0];pre=next(z for z in (diagnostics.get(symbol,{}).get('validation') or frozen['symbols'][symbol]['validation']) if z['parameters']==row['parameters'])
  audits[key]['pre_oos_validation']=pre['metrics']
  audits[key]['gates']['supported_positive_pre_oos_validation']=pre['metrics']['trades']>=60 and pre['metrics']['net']>0 and (pre['metrics']['pf'] or 0)>1
  audits[key]['all_gates_pass']=all(audits[key]['gates'].values())
  if not audits[key]['all_gates_pass']:audits[key]['verdict']='WATCH_ONLY' if row['metrics']['net']>0 and (row['metrics']['pf'] or 0)>1 else 'REJECT'
  windows[key]={'2y':window(row,C['oos'][0])}|{period:window(row,start) for period,start in C['recent'].items()}
  mods[key]=module_stats(row)
 seen={}
 for key,row in rows.items():
  identity=(row['stage'],row['index'])
  if identity in seen:audits[key]=audits[seen[identity]]
  else:seen[identity]=key
 if any('execution' not in z for z in audits.values()):
  # Execution QA is deterministic, not a parameter-selection step.
  r.save(R/'AUDIT.json',audits)
  import execution_audit
  execution_audit.main();audits=r.load(R/'AUDIT.json')
 r.save(R/'AUDIT.json',audits);r.save(R/'WINDOWS.json',windows);r.save(R/'MODULES.json',mods)
 sections=['<h1>Research ORB regime portfolio</h1><p>Breakouts + failed-break reversals · US100 and gold CFDs · 1% equity-risk target · research only</p>',
 '<div class="warning">Live EAs, BATs, presets, website and active MT5 account remain unchanged. No options surface or exchange order-flow data was fabricated. This is a new adaptation, not a claim to reproduce someone’s undisclosed strategy.</div>',
 '<h2>Decision</h2><p><strong>No tested version passes every promotion check.</strong> Gold’s RVOL-filtered failed-break reversal is the strongest two-year risk-adjusted research candidate: +16.32%, PF 1.59, 55.3% wins, 76 trades, native floating DD 6.55% and daily-equity Sharpe 1.15. Its last year returned +9.24%, but the last three months lost 0.88% on only seven trades. Earlier validation returned −9.37% (PF 0.59). The 10,000-path historical bootstrap has 92.06% profitable paths, below the 95% gate, with a negative fifth-percentile return. Keep it research-only.</p>',
 '<p>The two-module controller uses past-only daily Markov routing; adding breakout days did not improve gold’s result (hybrid +4.96%, PF 1.12) or US100’s result (hybrid −15.48%, PF 0.79). No ATR/range-normalisation/directional-filter breakout finalist earned promotion, so the unchanged plain breakout remains the comparison control. These findings do not establish a profitable institutional volatility-surface ORB.</p>',
 '<h2>Chronological split</h2>'+table(['Stage','Start inclusive','End exclusive','Use'],[[k,*C[k],v] for k,v in [('development','Parameter experiments'),('validation','Pre-OOS finalist selection'),('oos','Locked retrospective evaluation')]]),
 f'<p>{trials} implementation/asset/settings combinations counted: 100 original search configurations plus six corrected frozen finalists. Corrected source/settings frozen at {html.escape(frozen["created_utc"])} before the corrected runs. These asset histories were previously inspected: this is retrospective, not genuinely unseen forward data.</p>',
 '<div class="warning">Timing QA correction: a midnight cutoff-reopening bug was found by independent audit. ALL preliminary V1 figures were withdrawn and preserved under Withdrawn Timing Audit V1. The entry window is now strictly bounded between the opening-range end and 12:00 NY. The original finalist input values were retained, without re-optimising after seeing results; development, validation and final accounts were rerun on the corrected implementation.</div>',
 '<div class="warning">Execution QA: the intended 15:55 NY exit was not always executable. Native broker-session and holiday closures caused overnight carry in some comparisons. A logging-only reproduction confirmed MT5 retcode 10018 (market closed) for a US100 Friday exit, while gold had no later tradable holiday tick. These positions and all rejected-close outcomes remain in the results. Affected versions are NOT clean strict-intraday backtests and fail their scheduled-liquidation gate. Gold reversal and gold hybrid had no overnight positions in this evaluation.</div>',
 '<div class="warning">Finalists are research comparisons, NOT passed candidates. Selection required 60 trades per development/validation window. Where no finalist qualifies, the first declared unsupported finalist is retained only to expose the failure; a five-trade lucky profit was not selected as an edge. Prior validation failures remain a promotion blocker.</div>',
 '<p>All final comparisons use native MT5 Model 4 with available real ticks, 150 ms execution delay, a $10,000 USD start per asset/version and broker commission/swap/fee ledger reconciliation. Frozen-case optimisation enumerates independent accounts concurrently; it is NOT OOS parameter optimisation. Identical raw/developed breakout parameters reuse a verified account. Earlier missing real-tick history is disclosed below.</p>',
 '<h2>Locked two-year results</h2>'+table(['Asset / system','Trades','Return','Net PF','Win rate','Native float DD','Daily equity Sharpe','Win / loss streak'],[metrics_line(key,windows[key]['2y']) for key in rows])]
 for symbol in C['symbols']:
  sections.append('<h2>'+symbol+' — equity comparison</h2>'+chart(symbol,rows))
  lines=[]
  for period in ['1y','6m','3m']:
   for label in LABELS:lines.append(metrics_line(period+' · '+LABELS[label],windows[symbol+' '+label][period]))
  sections.append(table(['Recent period / system','Trades','Rebased return','PF','Win rate','Sampled DD¹','Sharpe','Win / loss streak'],lines))
  sections.append('<p>¹Recent returns are rebased subwindows of the SAME native account. Recent DD uses one-minute snapshots, which may miss intraminute lows. Final two-year DD uses native every-tick extrema. Sharpe is calculated on calendar-day end-of-day equity returns, annualised by √365.</p>')
  selected=frozen['symbols'][symbol]['selected'];sections.append('<h3>Hybrid contributions: same account, mutually exclusive routing</h3>'+table(['Module','Trades','Net USD','PF','Win rate'],[[k,z['trades'],a.f(z['net']),a.f(z['pf']),a.f(z['win_rate_pct'])+'%'] for k,z in mods[symbol+' hybrid'].items()]))
  sections.append('<p>Hybrid trades are not an arithmetic sum of independently compounded strategies. Both modules run inside one EA and share its equity and one-trade-per-day guard. US100 and gold above are separate asset accounts; they are not advertised as a combined cross-asset portfolio.</p>')
  for label,mod in [('breakout','0'),('reversal','1'),('hybrid','2')]:sections.append('<details><summary>'+LABELS[label]+' — frozen rules</summary>'+table(['Setting','Value'],[[html.escape(k),html.escape(v)] for k,v in rules(selected[mod])])+'</details>')
  v=diagnostics.get(symbol,{}).get('validation') or frozen['symbols'][symbol]['validation'];sections.append('<details><summary>Corrected pre-OOS validation — unchanged finalists</summary>'+table(['Module / inputs','Trades','Return','PF','Win rate','DD','Use'],[[html.escape(json.dumps(x['parameters'])),x['metrics']['trades'],a.pct(x['metrics']['return_pct']),a.f(x['metrics']['pf']),a.f(x['metrics']['win_rate_pct']),a.f(x['metrics']['equity_dd']),'Diagnostic; no re-selection'] for x in v])+'</details>')
 sections.append('<h2>Robustness: 10,000 five-observation block-bootstrap paths</h2>')
 lines=[]
 for key,z in audits.items():
  mc=z['monte_carlo'];lines.append([html.escape(key),z['verdict'],a.f(mc['probability_profit_pct'])+'%', ' / '.join(a.f(v)+'%' for v in mc['return_p05_p50_p95']), ' / '.join(a.f(v) for v in mc['pf_p05_p50_p95']), a.f(z['sharpe']['deflated_sharpe_pct'])+'%',a.f(mc['initial_balance_10pct_breach_proxy_pct'])+'%'])
 sections.append(table(['System','Verdict','P(profit)','Return P05 / median / P95','PF P05 / median / P95','Deflated Sharpe probability','10% initial-loss proxy'],lines))
 sections.append('<p>Bootstrap resamples clustered historical closed-balance daily returns and trade outcomes separately; it does not generate new market paths or recreate fills. Loss-limit statistics exclude intraday floating drawdown and are NOT prop-challenge pass probabilities. No live promotion is authorised by this report.</p>')
 sections.append('<h2>Execution and data-quality limitations</h2>')
 sections.append(table(['System','Overnight positions retained','Rejected management requests','Same-day liquidation observed'],[[html.escape(k),z['execution']['overnight_trades'],z['execution']['rejected_management_requests'],'Yes' if z['execution']['same_day_liquidation_observed'] else 'NO — promotion gate failed'] for k,z in audits.items()]))
 sections.append('<p>The frozen native market_closed_updates column is an uninstrumented zero placeholder, not proof of zero close failures. Diagnostic evidence and full carried-position inventory are saved in SESSION DIAGNOSTIC.json and EXECUTION AUDIT.json. No positions were deleted to improve metrics.</p>')
 for key,z in audits.items():
  row=rows[key];q=z['data_quality'];cost=z['cost_stress'];sections.append('<details><summary>'+html.escape(key)+' — '+html.escape(q['history_quality'])+' history quality; '+cost['status']+'</summary>'+table(['Check','Evidence'],[['Last quote',str(pd.Timestamp(row['native']['last_quote_epoch'],unit='s'))+' UTC'],['Tick notes',html.escape(json.dumps(q['real_tick_notes']))],['Extra cost stress',html.escape(json.dumps(cost))],['Failed gates',html.escape(', '.join(k for k,v in z['gates'].items() if not v))],['Win-rate 95% interval',' / '.join(a.f(v)+'%' for v in z['wilson95_pct'])],['Native entry failures',row['native']['failed_entries']],['Minimum-lot skips',row['native'].get('minimum_lot_skips',0)],['Stop-update failures',row['native']['failed_updates']]])+'</details>')
 sections.append('<h2>Research basis and what is missing</h2><p>Realised ATR and CFD tick-volume proxies are available. No licensed historical option chain/surface, skew, convexity, term structure, bid/ask aggressor delta or futures exchange volume is present. The added Markov gate is not an institutional order-flow model.</p>')
 sections.extend('<p><a href="'+url+'">'+html.escape(title)+'</a> — '+html.escape(note)+'</p>' for title,url,note in SOURCES)
 sections.append('<h2>Reproducibility</h2><p>Original input freeze: FROZEN.json. Corrected source/settings freeze: CORRECTED FROZEN.json. Timing correction: TIMING CORRECTION.json. Corrected diagnostics: CORRECTED DIAGNOSTICS.json. Every original trial: DEVELOPMENT.json and native manifests. Trade ledger, quotes, decisions, daily equity, native reports and journals: native/. Statistical audit: AUDIT.json. Execution limitations: EXECUTION AUDIT.json. Live changes: none.</p>')
 text='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Research ORB Regime Portfolio</title><style>body{margin:0;background:#091510;color:#e9f2ed;font:15px/1.55 system-ui}main{max-width:1260px;margin:auto;padding:36px}h1{font-size:34px}h2{margin-top:34px;color:#85e9bf}h3{color:#c9e1d5}p{color:#afc5b9}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:10px 12px;text-align:left;border-bottom:1px solid #284037}th{color:#93dcc0;background:#10241b}tr:nth-child(even){background:#0d1e16}td:first-child{max-width:420px;overflow-wrap:anywhere}.warning{border:1px solid #bf9638;border-radius:12px;padding:18px;background:#282412}details{margin:14px 0;padding:14px;border:1px solid #2c483c;border-radius:10px}summary{cursor:pointer;color:#8ee6c0}svg{width:100%;max-height:460px;border:1px solid #254235;border-radius:12px;background:#102019}a{color:#92ddff}small{display:block}</style></head><body><main>'+''.join(sections)+'</main></body></html>'
 (R/'Results.html').write_text(text,encoding='utf-8');r.status('Report and statistical audit ready',report=str(R/'Results.html'))
 print(json.dumps({k:{'two_year':v['2y'],'one_year':v['1y'],'three_month':v['3m']} for k,v in windows.items()},indent=2),flush=True)
if __name__=='__main__':main()
