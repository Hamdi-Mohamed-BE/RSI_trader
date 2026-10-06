"""Independent arithmetic and research-only results. No deploy or account API."""
import csv,gzip,html,importlib.util,json,math,re
import numpy as np
import pandas as pd
import native as n
import plan
R=n.R;B=n.B
sp=importlib.util.spec_from_file_location('orb_plot_stats',B/'Trend Progression Optimization 2026-10-05/analyze.py')
a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a)
def read(p):return n.read(R/p)
def save(p,v):n.save(R/p,a.stats.json_safe(v))
def esc(x):return html.escape(str(x))
def fmt(x,d=2):return '—' if x is None else f'{x:,.{d}f}' if isinstance(x,(int,float)) else str(x)
def pf(x):return sum(v for v in x if v>0)/-sum(v for v in x if v<0) if any(v<0 for v in x) else None
def daily(q):
 d=pd.read_csv(R/'native'/q['tag']/'equity.csv');start=pd.Timestamp(q['window'][0].replace('.','-'),tz='UTC');end=pd.Timestamp(q['window'][1].replace('.','-'),tz='UTC')
 s=pd.Series(d.equity.to_numpy(),index=pd.to_datetime(d.epoch,unit='s',utc=True));s=pd.concat([pd.Series([10000.],index=[start]),s]).sort_index()
 s=s.resample('D').last().ffill();return s[(s.index>=start)&(s.index<end)&(s.index.weekday<5)]
def returns(q):
 s=daily(q);x=s.pct_change();x.iloc[0]=s.iloc[0]/10000.-1;return x.dropna()
def verify(q):
 m=q['metrics'];x=[t['net'] for t in q['trades']]
 # The reused helper defaults these uninstrumented event counts to zero.
 # Do not present those placeholders as measured BE/partial counts.
 m.pop('breakevens',None);m.pop('partials',None)
 assert len(x)==m['trades']==q['native']['trades']
 assert abs(sum(x)-m['net_profit'])<.021 and abs(sum(x)-q['native']['net_profit'])<.021
 assert abs(pf(x)-m['pf'])<1e-10 if any(v<0 for v in x) else m['pf'] is None
 assert a.stats.streaks(x)==(m['win_streak'],m['loss_streak'])
 assert q['deal_audit']['all_exported_deals_match_native_report']
 assert n.sha(R/'native'/q['tag']/'report.htm')==q['report_sha256']
 assert abs(sum(t['net'] for t in q['ledger'])-m['net_profit'])<.021
 ordered=sorted(q['trades'],key=lambda t:t['open_epoch'])
 assert all(ordered[i]['close_epoch']<=ordered[i+1]['open_epoch'] for i in range(len(ordered)-1))
 for t in q['trades']:
  side=1 if t['side']=='Long' else -1;unit=t['cash_per_point_lot']
  assert abs(side*(t['close_price']-t['open_price'])*t['volume']*unit-t['gross'])<.011
  assert abs(t['gross']+t['swap']+t['commission']+t['fee']-t['net'])<.001
 x=a.position_returns(q);assert abs((np.prod(1+x)-1)*100-m['return_pct'])<1e-8
 ret=returns(q);m['sharpe_daily_equity']=float(np.sqrt(252)*ret.mean()/ret.std(ddof=1)) if len(ret)>2 and ret.std(ddof=1)>0 else None
 return True
def prior_trials():
 folder=B/'ORB H1 Range Research 2026-09-05';seen=set();counts={}
 for p in folder.glob('* RESULTS.json'):
  rows=n.read(p).get('rows',[]);rows=[r for r in rows if r.get('symbol')=='ustec'];counts[p.name]=len(rows)
  for r in rows:
   c={k:v for k,v in r.get('config',{}).items() if k not in ['InpMagic']}
   if c:seen.add(json.dumps(c,sort_keys=True))
 return dict(identifiable_distinct_ustec_settings=len(seen),rows_by_file=counts,note='Deduplicated identifiable USTEC settings only, ignoring magic. Unknown wider trials and other assets are omitted: DSR remains approximate/optimistic.')
def robust(q,trials):
 x=a.position_returns(q);rng=np.random.default_rng(20261006);paths=10000;size=len(x)
 if size<5:return dict(status='insufficient_data',gate=False)
 ix=((rng.integers(0,size,(paths,math.ceil(size/5)))[:,:,None]+np.arange(5))%size).reshape(paths,-1)[:,:size]
 boot=a.pathstats(x[ix]);shuffle=a.pathstats(np.array([rng.permutation(x) for _ in range(paths)]));omission={}
 for f in [.1,.2]:
  keep=size-round(size*f);omission[str(f)]=a.pathstats(np.array([x[np.sort(rng.choice(size,keep,replace=False))] for _ in range(paths)]))
 sharp=a.stats.sharpe_statistics(returns(q).tolist(),trials,252)
 stress=[];spread=[];slip=[]
 for t in q['trades']:
  side=1 if t['side']=='Long' else -1
  adverse=max(side*(t['open_price']-t['request_price']),0);unit=t['cash_per_point_lot'];spread.append(t['request_spread']);slip.append(adverse)
  extra=(adverse+t['request_spread'])*t['volume']*unit+abs(t['commission'])+abs(t['fee'])+max(-t['swap'],0)
  stress.append(t['net']-extra)
 lo,hi=a.stats.wilson_interval(q['metrics']['wins'],size)
 return dict(paths=paths,block_length=5,bootstrap=boot,shuffle=shuffle,omission=omission,sharpe_statistics=sharp,
  win_rate_wilson95_pct=[lo*100,hi*100],trials_used=trials,extra_recorded_cost_stress=dict(return_pct=sum(stress)/100,net_profit=round(sum(stress),2),pf=pf(stress),
   spread_price_median=float(np.median(spread)),spread_price_p95=float(np.quantile(spread,.95)),adverse_fill_p95=float(np.quantile(slip,.95)),
   zero_spread_entries=sum(v<=0 for v in spread),entries=size),
  gate=boot['positive_paths_pct']>=95 and boot['return_p05_pct']>0 and boot['pf_p05']>1 and sharp['deflated_sharpe_pct']>=95 and sum(stress)>0 and not q['operational_failure'],
  limits='Retrospective whole-position proportional closed-return proxy. Not floating equity, margin, exact lot recalculation, elapsed-day/FTMO/payout forecast. Extra paid-cost + measured spread/fill duplicate stress, unchanged fills/sizes. Zero broker quote spreads make this stress weak. DSR approximate, previous wider trials unknown; history already inspected.')
HEAD=['Version / window','Trades','Net wins','Net PF','Return','Equity DD','Daily Sharpe','W / L run','/ month','/ weekday']
def table(rows,head=HEAD):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(v)+'</th>' for v in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def row(q):
 m=q['metrics'];return [q['tag'],m['trades'],fmt(m['win_rate'],1)+'%',fmt(m['pf'],3),fmt(m['return_pct'])+'%',fmt(q['native']['equity_dd_pct'])+'%',fmt(m['sharpe_daily_equity']),f"{m['win_streak']} / {m['loss_streak']}",fmt(m['trades_month']),fmt(m['trades_weekday'])]
CSS='''body{margin:0;background:radial-gradient(ellipse at top right,#19392b,#07130f 65%);color:#e9f6ef;font:16px/1.65 system-ui}main{max-width:1380px;margin:auto;padding:40px 24px}h1{font-size:44px;line-height:1.1}h2{margin-top:38px}p{color:#abc8b8}a,summary{color:#77ffd0}.notice{border:1px solid #847348;background:#272719a0;padding:20px;border-radius:14px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:25px 0}.card{border:1px solid #2c5142;border-radius:14px;padding:17px;background:#0c211a}.card b{display:block;font-size:27px;color:#7bffcf}.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:14px;font-variant-numeric:tabular-nums}td,th{padding:12px;text-align:right;border-bottom:1px solid #2b4c3c;white-space:nowrap}td:first-child,th:first-child{text-align:left}th{color:#a5c7b3}svg{width:100%;height:auto}svg text{fill:#a8c7b5;font:12px system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;background:#112a1e;padding:16px}details{margin:22px 0}summary{cursor:pointer}.small{font-size:13px;color:#8dab9b}@media(max-width:650px){main{padding:25px 14px}h1{font-size:32px}.cards{grid-template-columns:repeat(2,1fr)}}'''
def main():
 selection=read('selection-frozen.json');chosen=selection['selected']['overrides'];selected_time=(R/'selection-frozen.json').stat().st_mtime
 tags=[v+'-'+w for w in ['1y','6m','3m','3y','5y'] for v in ['raw','candidate']]+['candidate-train',selection['validation_tag']]
 qs={t:read('native/'+t+'/results.json') for t in tags}
 assert all(verify(q) for q in qs.values())
 for tag,q in qs.items():
  assert q['model']==4
  if tag.startswith('candidate-'):
   assert read('native/'+tag+'/owned-process.json')['started']>=selected_time
   assert all(n.h._same_setting(str(v).lower() if isinstance(v,bool) else str(v),q['inputs'][k]) for k,v in chosen.items())
 search=read('SEARCH RESULTS.json');unique={json.dumps({k:v for k,v in q['inputs'].items() if k!='InpAuditTag'},sort_keys=True) for q in search};prior=prior_trials();trials=len(unique)+prior['identifiable_distinct_ustec_settings'];save('TRIAL COUNT.json',dict(new_unique=len(unique),prior=prior,total_dsr_trials=trials))
 mc={tag:robust(qs[tag],trials) for tag in ['raw-1y','candidate-1y','candidate-5y']};save('ROBUSTNESS.json',mc)
 older_ok=selection['qualified_older'] and plan.gate(qs['candidate-train'],120)
 year=qs['candidate-1y'];m=year['metrics'];recent=(plan.gate(year,25) and qs['candidate-6m']['metrics']['net_profit']>0 and qs['candidate-3m']['metrics']['net_profit']>0 and (qs['candidate-3m']['metrics']['pf'] or 0)>=1.2 and not any(qs['candidate-'+w]['operational_failure'] for w in ['1y','6m','3m']))
 long=mc['candidate-5y']['gate'];verdict=dict(decision='RESEARCH CANDIDATE FOR REVIEW' if older_ok and recent and long else 'NO QUALIFIED REPLACEMENT',older_gate=older_ok,recent_preferences=recent,robustness_gate=long,settings=chosen,no_production_change=True,full_pipeline='NOT RUN',shared_portfolio_ftmo='NOT RUN')
 save('VERDICT.json',verdict);save('COMPARISON.json',list(qs.values()))
 annual=[];payoffs=[]
 for tag in ['raw-5y','candidate-5y']:
  q=qs[tag]
  for yearnum in range(2021,2027):
   ts=[t for t in q['trades'] if pd.Timestamp(t['close_epoch'],unit='s',tz='UTC').year==yearnum]
   if not ts:continue
   vals=[t['net'] for t in ts];w,l=a.stats.streaks(vals)
   annual.append(dict(version=tag,year=yearnum,partial=yearnum in [2021,2026],trades=len(ts),net=sum(vals),initial_base_pct=sum(vals)/100,pf=pf(vals),win_rate=sum(v>0 for v in vals)/len(vals)*100,win_streak=w,loss_streak=l))
 for tag in ['raw-1y','candidate-1y','raw-3m','candidate-3m']:
  q=qs[tag]
  for side in ['All','Long','Short']:
   ts=[t for t in q['trades'] if side=='All' or t['side']==side];x=[t['net'] for t in ts];w,l=a.stats.streaks(x)
   payoffs.append(dict(version=tag,side=side,trades=len(ts),net=sum(x),pf=pf(x),win_rate=sum(v>0 for v in x)/len(x)*100 if x else None,
    average_win=np.mean([v for v in x if v>0]) if any(v>0 for v in x) else None,average_loss=np.mean([v for v in x if v<0]) if any(v<0 for v in x) else None,
    sl_exits=sum(t['exit_comment'].lower().startswith('sl ') for t in ts),tp_exits=sum(t['exit_comment'].lower().startswith('tp ') for t in ts),
    other_exits=sum(not t['exit_comment'].lower().startswith(('sl ','tp ')) for t in ts),mean_hold_hours=np.mean([t['hold_hours'] for t in ts]) if ts else None))
 save('ANNUAL.json',annual);save('PAYOFFS.json',payoffs)
 frozen=read('frozen.json');assert all(n.sha(B/p)==v for p,v in frozen['production'].items())
 raw=qs['raw-1y']['metrics'];cand=qs['candidate-1y']['metrics']
 parts=[f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>US100 H1 ORB · optimisation review</title><style>{CSS}</style></head><body><main><p class="small">CALYX · ONE EA AT A TIME · 6 OCTOBER 2026</p><h1>US100 H1 ORB 13UTC<br>Target versus time exit</h1><div class="notice">Research only. Asia Breakout left unchanged. No live EA, BAT, public website or account settings changed. News deferred; Trend1.5R future-BAT keep preserved. Stop here for your review.</div>']
 parts.append(f'<p><a href="{(B/"Active EA Recent Review 2026-10-05/Results.html").as_uri()}">All active-EA keep / pause / review decisions</a></p><h2>{verdict["decision"]}</h2><p>Older native gate: {older_ok}. Recent preferences: {recent}. Five-year robustness: {long}. This bounded retrospective search is NOT a full-pipeline or deployment pass.</p>')
 parts.append(f'<div class="cards"><div class="card">Annual win rate<b>{fmt(raw["win_rate"],1)} → {fmt(cand["win_rate"],1)}%</b></div><div class="card">Annual net PF<b>{fmt(raw["pf"])} → {fmt(cand["pf"])}</b></div><div class="card">Annual trades<b>{raw["trades"]} → {cand["trades"]}</b></div><div class="card">New settings tested<b>{len(unique)}</b></div></div>')
 parts.append('<h2>Frozen candidate settings</h2><pre>'+esc(json.dumps(chosen,indent=2))+'</pre><p>Everything else follows the exact shipped SET: 13–14 UTC H1 range; M15 completed-candle direct breakout; entry before15 UTC; opposite-range stop +0.10 H1 ATR; max3 ATR; 1% equity risk with upward/minimum-lot rounding. No stop/risk-size optimisation. No DI/ADX or Markov filter was added.</p>')
 parts.append('<h2>Current versus candidate · fresh native MT5</h2><p>Every period starts $10,000 independently. End-exclusive2026-10-06, through completed October5. Starts:1Y2025-10-06;6M2026-04-06;3M2026-07-06;3Y2023-10-06;5Y2021-10-06. Exness USTEC CFD,150ms delay,Model4 real ticks with generated fallback. Costs are actual native commission/swap/fee. Annualised daily sampled-equity Sharpe uses √252; not the tester’s differently defined Sharpe. Native tick-equity drawdown is separate from the lower-resolution graphs. Returns overlap and cannot be added.</p>'+table([row(qs[t]) for t in tags[:10]]))
 for window in ['1y','3m','5y']:
  curves=[];dds=[]
  for kind in ['raw','candidate']:
   q=qs[kind+'-'+window];s=daily(q);start=pd.Timestamp(q['window'][0].replace('.','-'),tz='UTC').timestamp();label='Current' if kind=='raw' else 'Candidate'
   curves.append((label,[(start,10000.)]+[(t.timestamp(),float(v)) for t,v in s.items()]))
   dd=100*(s/s.cummax().clip(lower=10000.)-1);dds.append((label,[(start,0.)]+[(t.timestamp(),float(v)) for t,v in dd.items()]))
  parts.append(a.graph(curves,window.upper()+' · sampled daily floating equity (USD)'));parts.append(a.graph(dds,window.upper()+' · daily-close sampled equity drawdown (%)'))
 parts.append('<h2>Payoff and direction attribution</h2><p>Stop/target exits are identified by native deal comments; other exits include timed and administrative test-end closes. Native 6R is a nominal target, not realised average reward. Averaged dollars inherit each standalone account’s compounding.</p>'+table([[v['version'],v['side'],v['trades'],fmt(v['net']),fmt(v['pf'],3),fmt(v['win_rate'],1)+'%',fmt(v['average_win']),fmt(v['average_loss']),v['sl_exits'],v['tp_exits'],v['other_exits'],fmt(v['mean_hold_hours'])] for v in payoffs],['Version','Side','Trades','Net $','PF','Wins','Average win $','Average loss $','SL','TP','Other exits','Hours']))
 parts.append('<h2>Older selection checks</h2><p>Development2021-10-06→2024-10-06. Validation2024-10-06→2025-10-06. Selection reused validation across three finalists, so it is not an independent holdout. Historical dates overlap earlier studies. Gates: ≥120/25 trades,PF≥1.20,wins≥50%,return positive,DD≤12%,winning run>losing run,no execution errors. No gate relaxed.</p>'+table([row(qs['candidate-train']),row(qs[selection['validation_tag']])]))
 finalists=[]
 for j,c in enumerate(read('finalists-frozen.json')):
  q=read('native/final-valid-'+str(j)+'/results.json');verify(q);finalists.append(row(q))
 parts.append('<details><summary>All native validation finalists</summary>'+table(finalists)+'</details>')
 parts.append('<h2>Annual attribution · five-year accounts</h2><p>2021/2026 partial. Contribution uses original10k denominator, inherited compounding—not independently reset annual tests.</p>'+table([[v['version'],str(v['year'])+(' partial' if v['partial'] else ''),v['trades'],fmt(v['net']),fmt(v['initial_base_pct'])+'%',fmt(v['pf'],3),fmt(v['win_rate'],1)+'%',f"{v['win_streak']}/{v['loss_streak']}"] for v in annual],['Version','Year','Trades','Net $','Initial-base contribution','PF','Win rate','W/L']))
 mcr=[]
 for tag,v in mc.items():
  z=v['bootstrap'];mcr.append([tag,fmt(z['positive_paths_pct']),fmt(z['return_p05_pct'])+'%',fmt(z['return_p50_pct'])+'%',fmt(z['pf_p05'],3),fmt(z['closed_dd_p95_pct'])+'%',fmt(v['sharpe_statistics']['deflated_sharpe_pct'])+'%',fmt(v['extra_recorded_cost_stress']['pf'],3),str(v['gate'])])
 parts.append('<h2>10,000-path Monte Carlo</h2><p>Block5 whole-position proportional-return bootstrap, reshuffle,10/20% trade omission. Descriptive closed-return proxy, not floating equity/margin/FTMO or passing-day forecast. DSR counts'+str(len(unique))+' new distinct settings plus'+str(prior['identifiable_distinct_ustec_settings'])+' identifiable earlier USTEC settings. Unknown wider trials make it optimistic. Extra-cost stress duplicates observed entry spread/adverse fill and paid costs, not invented costs.</p>'+table(mcr,['Version','Positive %','Return P5','Median return','PF P5','Closed DD P95','Approx DSR','Extra cost PF','All MC gates']))
 parts.append('<details><summary>Full robustness and uncertainty results</summary><pre>'+esc(json.dumps(a.stats.json_safe(mc),indent=2))+'</pre></details>')
 parts.append('<h2>Execution / data audit</h2><p>Exact production-binary parity: '+str(read('parity.json')['deal_rows'])+' native deal rows match timestamps, prices, volumes and costs. All positions grouped including entry commissions; every deal independently matched to native HTML. Broker cash-per-point-per-lot exported via OrderCalcProfit and verified against each realised gross profit and original stop risk. Completed range/candle inputs only; volume comparisons use prior windows. Clock: exact SET assumes testerUTC0; live auto server offset is a separate mechanism, not an inspected live chart configuration.</p>')
 failed_attempts=list((R/'native').glob('*/failed-attempt-*'))
 if failed_attempts:parts.append('<p class="small">'+str(len(failed_attempts))+' infrastructure-failed test attempt(s), before strategy execution, were archived and excluded. The exact unchanged case was rerun; no rejected blank report entered the results or selection.</p>')
 parts.append(table([[t,q['native']['history_quality'],q['counters']['order_failed'],q['counters']['modify_failed'],q['counters']['close_failed'],fmt(q['metrics']['max_actual_risk_budget_ratio'],3)+'×',fmt(q['metrics']['commission']),fmt(q['metrics']['swap']),q['operational_failure']] for t,q in qs.items()],['Version','History %','Entry failures','SL failures','Close failures','Max risk/budget','Commission $','Swap $','Any failure']))
 notes=sorted(set(s for q in qs.values() for s in q['tick_notes']));parts.append('<p class="small">Tick coverage: '+esc(' | '.join(notes))+'</p><p>Model4 real-tick availability starts2026-01-01; earlier ticks are generated. History quality is not a real-tick percentage. Upward/minimum-lot rounding can exceed1% nominal risk. Zero quoted spreads can weaken historical execution realism; no costs were silently fabricated. Only forward evidence can resolve that gap.</p>')
 parts.append('<h2>All screening settings · not hidden</h2><p>Model1 means one-minute OHLC ticks, not real ticks or full every-tick generation. Final comparisons use Model4. Staged bounded target/time/management/confirmation search; no entry-time, stop, Markov, random control or full portfolio pipeline claimed.</p>'+table([[q['tag'],q['metrics']['trades'],fmt(q['metrics']['win_rate'],1)+'%',fmt(q['metrics']['pf'],3),fmt(q['metrics']['return_pct'])+'%',fmt(q['native']['equity_dd_pct'])+'%',f"{q['metrics']['win_streak']}/{q['metrics']['loss_streak']}",q['qualified_training'],json.dumps(plan.overrides(q),sort_keys=True)] for q in search],['Setting','Trades','Wins','PF','Return','DD','W/L','Gate','Overrides']))
 parts.append('<details><summary>Frozen protocol</summary><pre>'+esc((R/'PROTOCOL.md').read_text())+'</pre></details><p class="small">Historical simulations, not forecasts. Shared portfolio/prop pass times/payout rates not recalculated. <a href="COMPARISON.json">Metrics</a> · <a href="ANNUAL.json">Annual attribution</a> · <a href="ROBUSTNESS.json">Monte Carlo</a> · <a href="PAYOFFS.json">Exit/direction details</a></p></main></body></html>')
 (R/'Results.html').write_text(''.join(parts),encoding='utf-8')
 all_native=list((R/'native').glob('*/results.json'))
 for p in all_native:
  q=n.read(p)
  if q['deal_audit'] is not None:verify(q)
 save('VERIFICATION.json',dict(parity=read('parity.json'),comparisons=len(qs),successful_native_runs=len(all_native),infrastructure_failed_attempts_excluded=len(failed_attempts),all_cash_costs_deals_reconciled=True,production_hashes_unchanged=True,selected_before_recent_replays=True,mc_paths=10000,distinct_configs=len(unique),no_deployment=True,verdict=verdict))
 print(json.dumps(verdict,indent=2))
if __name__=='__main__':main()
