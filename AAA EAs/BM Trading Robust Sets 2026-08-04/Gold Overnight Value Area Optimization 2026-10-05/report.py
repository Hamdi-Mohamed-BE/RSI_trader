"""Independent arithmetic, closed-return robustness, offline research report."""
from pathlib import Path
import csv,hashlib,html,importlib.util,json,math,sys
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent;B=R.parent
sp=importlib.util.spec_from_file_location('gold_va_plot_helpers',B/'Trend Progression Optimization 2026-10-05/analyze.py')
a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a)
def read(p):return json.loads((R/p).read_text(encoding='utf-8'))
def save(p,v):(R/p).write_text(json.dumps(a.stats.json_safe(v),indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fmt(x,n=2):return '—' if x is None else f'{x:,.{n}f}' if isinstance(x,(int,float)) else html.escape(str(x))
def pf(x):return sum(v for v in x if v>0)/-sum(v for v in x if v<0) if any(v<0 for v in x) else None
def daily(q):
 d=pd.read_csv(R/'native'/q['tag']/'equity.csv');s=pd.Series(d.equity.to_numpy(),index=pd.to_datetime(d.epoch,unit='s',utc=True))
 start,end=pd.to_datetime(q['window'][0].replace('.','-'),utc=True),pd.to_datetime(q['window'][1].replace('.','-'),utc=True)
 # Explicit initial USD10k and final flat close for comparable independent starts.
 s=pd.concat([pd.Series([10000.],index=[start]),s]).sort_index()
 s=s.resample('D').last().ffill();s=s[(s.index>=start)&(s.index<end)&(s.index.weekday<5)]
 return s
def daily_returns(q):
 s=daily(q)
 # Include the first weekday's change from the independent USD10k deposit.
 r=s.pct_change();r.iloc[0]=s.iloc[0]/10000.-1
 return r.dropna()
def independent(q):
 ts=q['trades'];p=[t['net'] for t in ts];m=q['metrics']
 assert len(ts)==m['trades'] and abs(sum(p)-m['net_profit'])<.021 and abs(m['net_profit']-q['native']['net_profit'])<.021
 assert a.stats.streaks(p)==(m['win_streak'],m['loss_streak'])
 assert abs(pf(p)-m['pf'])<1e-10 if any(v<0 for v in p) else m['pf'] is None
 assert q['deal_audit']['all_exported_deals_match_native_report'] and sha(R/'native'/q['tag']/'report.htm')==q['report_sha256']
 assert abs(sum(x['net'] for x in q['ledger'])-m['net_profit'])<.021
 for t in ts:
  side=1 if t['side']=='Long' else -1
  assert abs(side*(t['close_price']-t['open_price'])*t['volume']*100-t['gross'])<.031
  assert abs(sum(t[k] for k in ['gross','commission','swap','fee'])-t['net'])<.001
 # Closed proportional returns reproduce the observed compounded final balance.
 returns=a.position_returns(q)
 assert abs((np.prod(1+returns)-1)*100-m['return_pct'])<1e-8
 return True
def robust(q,trials):
 x=a.position_returns(q);rng=np.random.default_rng(20261005);paths=10000;n=len(x)
 if n<5:return dict(status='insufficient_data')
 blocks=rng.integers(0,n,(paths,math.ceil(n/5)));ix=((blocks[:,:,None]+np.arange(5))%n).reshape(paths,-1)[:,:n]
 boot=a.pathstats(x[ix]);shuffle=a.pathstats(np.array([rng.permutation(x) for _ in range(paths)]));omit={}
 for fraction in [.1,.2]:
  keep=n-round(n*fraction);omit[str(fraction)]=a.pathstats(np.array([x[np.sort(rng.choice(n,keep,replace=False))] for _ in range(paths)]))
 d=daily(q);sharpe=a.stats.sharpe_statistics(daily_returns(q).tolist(),trials,252)
 stress=[t['net']-t['request_spread']*t['volume']*100 for t in q['trades']]
 low,high=a.stats.wilson_interval(q['metrics']['wins'],n)
 return dict(paths=paths,block_length=5,bootstrap=boot,shuffle=shuffle,omission=omit,sharpe_statistics=sharpe,
  win_rate_wilson95_pct=[100*low,100*high],additional_observed_spread=dict(net_profit=round(sum(stress),2),return_pct=sum(stress)/100,pf=pf(stress),
   median_observed_spread=float(np.median([t['request_spread'] for t in q['trades']])),
   scope='One extra observed entry bid/ask spread applied to unchanged realised trade cash flows; no invented spread, no refills or recompounding.'),
  gate=boot['return_p05_pct']>0 and boot['pf_p05']>1 and boot['positive_paths_pct']>=95 and sharpe['deflated_sharpe_pct']>=95 and sum(stress)>0 and not q['operational_failure'],
  limitations='Descriptive whole-position proportional closed-return resampling, not floating-equity/margin/lot/elapsed-day/FTMO or future-return probability. Blocks5 may miss longer regimes; DSR approximation uses new plus195 earlier known configurations, broader historical trials unknown. Execution-rejected records cannot pass even if resampling looks attractive.')
def eligibility(q,minimum):
 m=q['metrics'];return m['trades']>=minimum and m['net_profit']>0 and (m['pf'] or 0)>=1.2 and (m['win_rate'] or 0)>=60 and m['win_streak']>m['loss_streak'] and q['native']['equity_dd_pct']<=15 and not q['operational_failure']
HEADER=['Version / period','Trades','Wins','Net PF','Return','Equity DD','Daily Sharpe','W / L run','/ month','/ weekday','History']
def row(q):
 m=q['metrics'];v=q['tag'].replace('candidate','Candidate').replace('raw','Current');vals=[v,m['trades'],fmt(m['win_rate'],1)+'%',fmt(m['pf'],3),fmt(m['return_pct'])+'%',
  fmt(q['native']['equity_dd_pct'])+'%',fmt(m['sharpe_daily_equity']),f"{m['win_streak']} / {m['loss_streak']}",fmt(m['trades_month']),fmt(m['trades_weekday']),q['native']['history_quality']]
 return '<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in vals)+'</tr>'
def table(rows,header=HEADER):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+html.escape(x)+'</th>' for x in header)+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'
def main():
 tags=[f'{v}-{w}' for w in ['1y','6m','3m','3y','5y'] for v in ['raw','candidate']]+['candidate-train','candidate-valid']
 qs={tag:read('native/'+tag+'/results.json') for tag in tags};assert all(independent(q) for q in qs.values())
 for q in qs.values():
  returns=daily_returns(q)
  q['metrics']['sharpe_daily_equity']=float(np.sqrt(252)*returns.mean()/returns.std(ddof=1)) if len(returns)>2 and returns.std(ddof=1)>0 else None
 hashes=read('frozen.json');assert all(sha(B/p)==v for p,v in hashes['production'].items())
 selected=read('selection-frozen.json');search=read('SEARCH RESULTS.json');trials=search['configurations']+195
 chosen=selected['selected']['config'];qualified=eligibility(qs['candidate-train'],150) and eligibility(qs['candidate-valid'],40)
 for inp,key in dict(InpTargetR='target_r',InpMinimumR='min_r',InpStopMode='stop',InpEntryEndMinute='entry_end',InpExitMinute='exit',InpBreakEvenR='be',InpTrailDistanceR='trail').items():
  assert all(float(qs[tag]['inputs'][inp])==chosen[key] for tag in qs if tag.startswith('candidate'))
 robustness={tag:robust(qs[tag],trials) for tag in ['raw-1y','candidate-1y','candidate-5y']};save('ROBUSTNESS.json',robustness)
 annual=[]
 for tag in ['raw-5y','candidate-5y']:
  for year in range(2021,2027):
   ts=[t for t in qs[tag]['trades'] if pd.Timestamp(t['close_epoch'],unit='s',tz='UTC').year==year]
   if not ts:continue
   p=[t['net'] for t in ts];w,l=a.stats.streaks(p)
   annual.append(dict(version=tag,year=year,partial_year=year in [2021,2026],trades=len(ts),net_profit=round(sum(p),2),net_return_initial_pct=sum(p)/100,
    pf=pf(p),win_rate=sum(v>0 for v in p)/len(p)*100,win_streak=w,loss_streak=l))
 save('ANNUAL.json',annual);save('COMPARISON.json',[qs[tag] for tag in tags])
 verdict=dict(qualified_native_development_validation=qualified,decision='NO REPLACEMENT RECOMMENDATION' if not qualified else 'RESEARCH ONLY',
  no_production_change=True,candidate=chosen,recent_year_better_pf=qs['candidate-1y']['metrics']['pf']>qs['raw-1y']['metrics']['pf'],
  recent_year_better_win_rate=qs['candidate-1y']['metrics']['win_rate']>qs['raw-1y']['metrics']['win_rate'],
  full_robustness_pass=robustness['candidate-5y']['gate'],broader_stage5_search='NOT RUN',portfolio_prop_pass_replay='NOT RUN')
 save('VERDICT.json',verdict)
 parts=['''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Gold Overnight Value Area · payoff research</title><style>
body{margin:0;background:radial-gradient(ellipse at top right,#173b2c,#071511 65%);color:#eaf6ef;font:16px/1.65 system-ui}main{max-width:1320px;margin:auto;padding:40px 25px}h1{font-size:44px;line-height:1.15}h2{margin-top:40px}p{color:#afc7bb}a,summary{color:#74fac5}.notice{border:1px solid #847346;border-radius:14px;padding:19px;background:#1c261bd0}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:25px 0}.card{background:#0d231b;border:1px solid #2b5140;border-radius:14px;padding:18px}.card b{display:block;font-size:27px;color:#74fac5}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}th,td{white-space:nowrap;padding:13px;text-align:right;border-bottom:1px solid #294c3c}th:first-child,td:first-child{text-align:left}th{color:#9fbfae}svg{width:100%;height:auto}svg text{fill:#afc7bb;font:12px system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#10261b;padding:15px;font-size:12px}details{padding:18px 0;border-bottom:1px solid #294c3c}summary{cursor:pointer}.small{font-size:13px;color:#8dad9c}@media(max-width:650px){main{padding:25px 14px}h1{font-size:32px}.cards{grid-template-columns:repeat(2,1fr)}}</style></head><body><main>
<p class="small">CALYX · ONE EA AT A TIME · 5 OCTOBER 2026</p><h1>Gold Overnight Value Area<br>Can better payoff preserve the wins?</h1><div class="notice">Research only. Gold and Silver news are saved and deferred. No live account, EA, BAT, public website or Git deployment was changed. Stop here for your review.</div>''']
 parts.append(f'<p><a href="{(B/"Active EA Recent Review 2026-10-05/Results.html").as_uri()}">All active-EA keep / pause / review decisions and deferred news</a></p>')
 parts.append(f'<h2>{verdict["decision"]}</h2><div class="notice">Native older development/validation gate: {"PASS" if qualified else "FAIL"}. Five-year candidate robustness gate: {"PASS" if robustness["candidate-5y"]["gate"] else "FAIL"}. Do not switch the production bot to this candidate from recent headline numbers.</div>')
 raw=qs['raw-1y']['metrics'];cand=qs['candidate-1y']['metrics']
 parts.append(f'<div class="cards"><div class="card">Current annual wins<b>{fmt(raw["win_rate"],1)}%</b></div><div class="card">Candidate annual wins<b>{fmt(cand["win_rate"],1)}%</b></div><div class="card">Current → candidate PF<b>{fmt(raw["pf"],2)} → {fmt(cand["pf"],2)}</b></div><div class="card">Distinct new settings<b>{search["configurations"]}</b></div></div>')
 parts.append('<h2>Exact frozen diagnostic</h2><p>M5 first breakout of the same 64-bin, 70% overnight value area; both directions; opposite VA stop; fixed 0.5R target; minimum computed reward/risk 0.5; entries before 14:00 NY, exit 16:00 NY; no breakeven/trailing/ADX/DI. One first signal consumed/day, even if geometry or payoff fails. Minimum-R exactly equal to target-R is sensitive to tick rounding: neighbouring 0.4 and 0.6 thresholds change which days trade substantially. That is a warning, not a stable filter.</p>')
 parts.append('<p>Fixed-R also permits first signals whose original overnight-extreme target was already behind entry. Combined with the payoff and entry-time gates, the candidate changes which days trade; this is not a matched-trade exit-only comparison. The profile uses broker M1 tick-volume at typical price, not centralised Gold exchange volume.</p>')
 parts.append(f'<p>{search["configurations"]} cached-bar settings, plus 195 earlier known configurations considered in the approximate Sharpe adjustment. Bounded payoff/management/time search, NOT the complete full pipeline. Training: 2021-10-05–2024-10-05; validation: 2024-10-05–2025-10-05. Settings frozen before opening recent native tests. Previously inspected years are NOT an untouched holdout. The original raw five-year PF 1.04 failed the pipeline gate before this exploratory search.</p>')
 parts.append('<h2>Native current versus candidate</h2><p>All periods end 2026-10-05 exclusive. 1Y starts 2025-10-05; 6M: 2026-04-05; 3M: 2026-07-05; 3Y: 2023-10-05; 5Y: 2021-10-05. Each restarts USD 10,000 with 1% intended equity risk, leverage 1:2000, XAUUSD Exness, 150ms. Overlapping returns are not additive. Equity DD is native MT5; daily Sharpe is reconstructed from sampled equity and annualised √252. Old native report Sharpe is not substituted. Real-tick history begins January 2026; earlier ticks are generated where unavailable.</p>')
 parts.append(table([row(qs[tag]) for tag in tags if not tag.endswith(('train','valid'))]))
 for window in ['1y','3m','5y']:
  curves=[];drawdowns=[]
  for kind in ['raw','candidate']:
   q=qs[kind+'-'+window];d=daily(q);label='Current' if kind=='raw' else 'Candidate'
   initial=pd.Timestamp(q['window'][0].replace('.','-'),tz='UTC').timestamp()
   curves.append((label,[(initial,10000.)]+[(t.timestamp(),float(v)) for t,v in d.items()]))
   drawdowns.append((label,[(initial,0.)]+[(t.timestamp(),float(v)) for t,v in (100*(d/d.cummax().clip(lower=10000.)-1)).items()]))
  parts.append(a.graph(curves,window.upper()+' · daily sampled floating equity (USD)'))
  parts.append(a.graph(drawdowns,window.upper()+' · sampled daily-close equity drawdown (%)'))
 parts.append('<p class="small">Daily-close graphs can miss intraday peaks/troughs; the table uses the higher-resolution native equity drawdown. These are two independent accounts, not one combined portfolio.</p>')
 parts.append('<h2>Why a high win rate can disappoint</h2>')
 payoff=[]
 for tag in ['raw-1y','candidate-1y','raw-3m','candidate-3m']:
  q=qs[tag];m=q['metrics'];vals=[tag,fmt(m['avg_win']),fmt(m['avg_loss']),fmt(m['mean_initial_rr'],3),fmt(m['max_actual_risk_budget_ratio'],3)+'×',m['late_exits_over_60s'],m['overnight_positions']]
  payoff.append('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in vals)+'</tr>')
 parts.append(table(payoff,['Version','Mean net win $','Mean net loss $','Mean initial R/R','Max risk/budget','Late exit >60s','Overnight positions']))
 parts.append('<p>Upward/minimum-lot rounding was retained for exact-current parity: 1% is not a hard cap. Late session/holiday exits and rejected orders are operational evidence, not fabricated fills. A moved-to-entry stop is not a net breakeven after costs.</p>')
 parts.append('<h2>Frozen older native checks</h2>'+table([row(qs['candidate-train']),row(qs['candidate-valid'])]))
 parts.append('<p>Qualification: ≥150 development and ≥40 validation positions; both positive, PF ≥1.20, win rate ≥60%, winning run longer than losing, native equity DD ≤15%, no operational rejects. No gate was relaxed after results. Only one diagnostic finalist was native-tested: the cached top 3 were near-duplicate inactive-management settings, and none passed the screening gate.</p>')
 parts.append('<h2>Annual cash-flow attribution · full 5Y ledgers</h2><p>2021 and 2026 are partial years. These are contributions to the full compounded five-year account, divided by its initial $10,000—not independent annual backtests. Returns and costs reconcile to each 5Y total.</p>')
 yrrows=[]
 for y in annual:
  vals=[y['version'],str(y['year'])+(' (partial)' if y['partial_year'] else ''),y['trades'],fmt(y['net_profit']),fmt(y['net_return_initial_pct'])+'%',fmt(y['pf'],3),fmt(y['win_rate'],1)+'%',f"{y['win_streak']}/{y['loss_streak']}"]
  yrrows.append('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in vals)+'</tr>')
 parts.append(table(yrrows,['Version','Calendar year','Trades','Net $','Initial-base contribution','PF','Win rate','W/L']))
 parts.append('<h2>10,000-path descriptive robustness</h2><p>Circular block bootstrap length 5, order shuffle, and random 10/20% trade omission. Proportional closed returns with native costs. No floating equity, minimum-lot recalculation, elapsed-day calendar, joint portfolio or FTMO model. Conditional resampling is not a future probability forecast. Executions with failures cannot qualify.</p>')
 mcrows=[]
 for tag,v in robustness.items():
  b=v['bootstrap'];s=v['sharpe_statistics'];vals=[tag,fmt(b['return_p05_pct'])+'%',fmt(b['return_p50_pct'])+'%',fmt(b['pf_p05'],3),fmt(b['closed_dd_p95_pct'])+'%',fmt(b['positive_paths_pct'],1)+'%',fmt(s['deflated_sharpe_pct'],1)+'%',v['gate']]
  mcrows.append('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in vals)+'</tr>')
 parts.append(table(mcrows,['Ledger','Return P5','Return median','PF P5','Closed DD P95','Profitable paths','Approx DSR','Gate']))
 for tag,v in robustness.items():parts.append('<details><summary>'+tag+' · shuffle, omission, measured spread and confidence limits</summary><pre>'+html.escape(json.dumps(v,indent=2))+'</pre></details>')
 parts.append('<h2>All cached-bar searches and neighbouring settings</h2><p>Not native MT5. M1 stop-first ambiguous-bar handling, historical spread and observed $5.50/lot commission assumption; no complete native margin/session history. Approximate drawdown is not native equity DD. No missing bars were fabricated; the June 20, 2025 history gap remains.</p>')
 for stage in dict.fromkeys(r['stage'] for r in search['rows']):
  rows=[]
  for r in search['rows']:
   if r['stage']!=stage:continue
   c=r['config'];m=r['training'];name=f"R{c['target_r']} min{c['min_r']} stop{c['stop']} BE{c['be']} trail{c['trail']} entry{c['entry_end']} exit{c['exit']}"
   vals=[name,m['trades'],fmt(m['pf'],3),fmt(m['win_rate'],1)+'%',fmt(m['return_pct'])+'%',fmt(m['dd'])+'%',f"{m['win_streak']}/{m['loss_streak']}"]
   rows.append('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in vals)+'</tr>')
  parts.append('<details><summary>'+stage+f' · {len(rows)} settings</summary>'+table(rows,['Config','Trades','PF','Wins','Return','Approx DD','W/L'])+'</details>')
 parts.append('<h2>Execution and evidence warnings</h2>')
 for tag,q in qs.items():
  if q['operational_failure']:parts.append('<p>'+html.escape(tag)+': '+html.escape(json.dumps({k:v for k,v in q['counters'].items() if k in ['rejected','modify_failed','close_failed','missing','invalid_geometry']}))+'; genuine realised figures retained, no promotion.</p>')
 parts.append('<p>Shipped-binary/default-copy parity passed all 106 native deal rows over the quarter. Every audited completed position and its native HTML cash flows reconcile. One cash-risk analytical check was corrected for cent rounding; the failed analysis attempt was archived and replayed, with frozen strategy/settings unchanged. No runtime rule was tuned after recent results.</p><p>Source, EX5, SET, reports, journals, deal exports and equity traces retained. Cross-broker, truly untouched data, full timeframe/entry/regime search and shared-portfolio/prop simulation NOT RUN. No guaranteed returns, no live replacement.</p>')
 parts.append('<p><a href="COMPARISON.json">Complete native comparisons</a> · <a href="SEARCH%20RESULTS.json">Every screen</a> · <a href="ROBUSTNESS.json">Monte Carlo</a> · <a href="VERIFICATION.json">Verification</a> · <a href="PROTOCOL.md">Frozen protocol</a></p><h2>Awaiting your review</h2><p>Current production version preserved. Next non-news candidate in the review queue: Asia Breakout Gold. No further EA starts automatically.</p></main></body></html>')
 (R/'Results.html').write_text(''.join(parts),encoding='utf-8')
 check=dict(audited_native_results=len(qs)+1,distinct_new_settings=search['configurations'],earlier_known_trials=195,parity=read('parity.json'),
  native_deals_cash_costs_streaks_checked=True,all_requested_periods_present=True,production_hashes_unchanged=True,qualified_native_development_validation=qualified,
  no_live_api_used=True,no_deployment=True,failed_analysis_attempts_archived=1)
 save('VERIFICATION.json',check);print(json.dumps(check,indent=2),flush=True)
if __name__=='__main__':main()
