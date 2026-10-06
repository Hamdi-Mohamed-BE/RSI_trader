"""Whole-position independent checks, MC and local-only report."""
from pathlib import Path
import csv,gzip,hashlib,html,importlib.util,json,math,re
import numpy as np
import pandas as pd
import native as n
import plan
R=Path(__file__).resolve().parent;B=R.parent
sp=importlib.util.spec_from_file_location('asia_plot_stats',B/'Trend Progression Optimization 2026-10-05/analyze.py')
a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a)
def read(p):return n.read(R/p)
def save(p,v):n.save(R/p,a.stats.json_safe(v))
def fmt(x,d=2):return '—' if x is None else f'{x:,.{d}f}' if isinstance(x,(int,float)) else str(x)
def esc(x):return html.escape(str(x))
def pf(values):return sum(v for v in values if v>0)/-sum(v for v in values if v<0) if any(v<0 for v in values) else None
def daily(q):
 d=pd.read_csv(R/'native'/q['tag']/'equity.csv');start=pd.Timestamp(q['window'][0].replace('.','-'),tz='UTC');end=pd.Timestamp(q['window'][1].replace('.','-'),tz='UTC')
 s=pd.Series(d.equity.to_numpy(),index=pd.to_datetime(d.epoch,unit='s',utc=True));s=pd.concat([pd.Series([10000.],index=[start]),s]).sort_index()
 s=s.resample('D').last().ffill();return s[(s.index>=start)&(s.index<end)&(s.index.weekday<5)]
def returns(q):
 s=daily(q);r=s.pct_change();r.iloc[0]=s.iloc[0]/10000.-1;return r.dropna()
def verify(q):
 m=q['metrics'];values=[t['net'] for t in q['trades']]
 assert len(values)==m['trades']==q['native']['trades']
 assert abs(sum(values)-m['net_profit'])<.021 and abs(sum(values)-q['native']['net_profit'])<.021
 assert abs(pf(values)-m['pf'])<1e-10 if any(v<0 for v in values) else m['pf'] is None
 assert a.stats.streaks(values)==(m['win_streak'],m['loss_streak'])
 assert q['deal_audit']['all_exported_deals_match_native_report']
 assert n.sha(R/'native'/q['tag']/'report.htm')==q['report_sha256']
 # Parent terminal and tester journals can repeat the same server-time message.
 journal=gzip.decompress((R/'native'/q['tag']/'journal.txt.gz').read_bytes()).decode()
 failures=set(re.findall(r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})\s+(.*(?:stop modification failed|Dynamic trailing SL modification failed)[^\r\n]*)',journal,re.I))
 q['counters']['unique_original_dynamic_modify_failure_events']=len(failures)
 assert len(failures)<=q['counters']['legacy_or_dynamic_modify_failed']
 assert abs(sum(t['net'] for t in q['ledger'])-m['net_profit'])<.021
 for t in q['trades']:
  side=1 if t['side']=='Long' else -1
  assert abs(side*(t['close_price']-t['open_price'])*t['volume']*100-t['gross'])<.031
  assert abs(t['gross']+t['swap']+t['commission']+t['fee']-t['net'])<.001
 x=a.position_returns(q);assert abs((np.prod(1+x)-1)*100-m['return_pct'])<1e-8
 ds=returns(q);m['sharpe_daily_equity']=float(np.sqrt(252)*ds.mean()/ds.std(ddof=1)) if len(ds)>2 and ds.std(ddof=1)>0 else None
 return True
def robust(q,trials):
 x=a.position_returns(q);rng=np.random.default_rng(20261005);paths=10000;size=len(x)
 if size<5:return dict(status='insufficient_data',gate=False)
 blocks=rng.integers(0,size,(paths,math.ceil(size/5)));ix=((blocks[:,:,None]+np.arange(5))%size).reshape(paths,-1)[:,:size]
 boot=a.pathstats(x[ix]);shuffle=a.pathstats(np.array([rng.permutation(x) for _ in range(paths)]));omission={}
 for fraction in [.1,.2]:
  keep=size-round(size*fraction);omission[str(fraction)]=a.pathstats(np.array([x[np.sort(rng.choice(size,keep,replace=False))] for _ in range(paths)]))
 sharp=a.stats.sharpe_statistics(returns(q).tolist(),trials,252)
 stress=[t['net']-t['request_spread']*t['volume']*100 for t in q['trades']]
 lo,hi=a.stats.wilson_interval(q['metrics']['wins'],size)
 return dict(paths=paths,block_length=5,bootstrap=boot,shuffle=shuffle,omission=omission,sharpe_statistics=sharp,
  win_rate_wilson95_pct=[100*lo,100*hi],extra_observed_spread=dict(net_profit=round(sum(stress),2),return_pct=sum(stress)/100,pf=pf(stress),
   median_price_spread=float(np.median([t['request_spread'] for t in q['trades']])),scope='One extra observed entry spread cash penalty, unchanged fills and sizing. No invented spread or slippage distribution.'),
  gate=boot['return_p05_pct']>0 and boot['pf_p05']>1 and boot['positive_paths_pct']>=95 and sharp['deflated_sharpe_pct']>=95 and sum(stress)>0 and not q['operational_failure'],
  limitations='Descriptive closed proportional returns; not floating-equity, margin, lot recalculation, elapsed-day or FTMO probabilities. DSR approximate and optimistic: unknown older trials omitted. These previously inspected dates are not an untouched holdout.')
HEAD=['Version / window','Trades','Net win rate','Net PF','Return','Native equity DD','Daily Sharpe','W / L run','/ month','/ weekday']
def table(rows,head=HEAD):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(v)+'</th>' for v in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def row(q):
 m=q['metrics'];return [q['tag'],m['trades'],fmt(m['win_rate'],1)+'%',fmt(m['pf'],3),fmt(m['return_pct'])+'%',fmt(q['native']['equity_dd_pct'])+'%',
  fmt(m['sharpe_daily_equity']),f"{m['win_streak']} / {m['loss_streak']}",fmt(m['trades_month']),fmt(m['trades_weekday'])]
CSS='''body{margin:0;background:radial-gradient(ellipse at top right,#19392b,#07130f 65%);color:#e9f6ef;font:16px/1.65 system-ui}main{max-width:1380px;margin:auto;padding:40px 24px}h1{font-size:44px;line-height:1.1}h2{margin-top:38px}p{color:#abc8b8}a,summary{color:#77ffd0}.notice{border:1px solid #847348;background:#272719a0;padding:20px;border-radius:14px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:25px 0}.card{border:1px solid #2c5142;border-radius:14px;padding:17px;background:#0c211a}.card b{display:block;font-size:27px;color:#7bffcf}.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:14px;font-variant-numeric:tabular-nums}td,th{padding:12px;text-align:right;border-bottom:1px solid #2b4c3c;white-space:nowrap}td:first-child,th:first-child{text-align:left}th{color:#a5c7b3}svg{width:100%;height:auto}svg text{fill:#a8c7b5;font:12px system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;background:#112a1e;padding:16px}details{margin:22px 0}summary{cursor:pointer}.small{font-size:13px;color:#8dab9b}@media(max-width:650px){main{padding:25px 14px}h1{font-size:32px}.cards{grid-template-columns:repeat(2,1fr)}}'''
def main():
 tags=[v+'-'+w for w in ['1y','6m','3m','3y','5y'] for v in ['raw','candidate']]+['candidate-train','candidate-valid','utc-current-1y','utc-current-3m']
 qs={tag:read('native/'+tag+'/results.json') for tag in tags};assert all(verify(q) for q in qs.values())
 frozen=read('frozen.json');assert all(n.sha(B/p)==v for p,v in frozen['production'].items())
 selected=read('selection-frozen.json');search=read('SEARCH RESULTS.json');trials=search['configurations']+6
 selected_time=(R/'selection-frozen.json').stat().st_mtime
 assert all(read('native/'+tag+'/owned-process.json')['started']>=selected_time for tag in tags if tag.startswith('candidate'))
 assert all(all(n.h._same_setting(str(v).lower() if isinstance(v,bool) else str(v),q['inputs'][k]) for k,v in selected['settings'].items()) for tag,q in qs.items() if tag.startswith('candidate'))
 robustness={tag:robust(qs[tag],trials) for tag in ['raw-1y','candidate-1y','candidate-5y']};save('ROBUSTNESS.json',robustness)
 latest=qs['candidate-1y'];m=latest['metrics'];recent_ok=plan.qualify(latest,30) and qs['candidate-6m']['metrics']['net_profit']>0 and qs['candidate-3m']['metrics']['net_profit']>0
 qualified=selected['qualified'];long_ok=robustness['candidate-5y']['gate']
 verdict=dict(decision='RESEARCH CANDIDATE FOR REVIEW' if qualified and recent_ok and long_ok else 'NO QUALIFIED REPLACEMENT',
  older_gate_pass=qualified,recent_preference_pass=recent_ok,full5y_robustness_pass=long_ok,no_production_change=True,
  selected=selected['selected'],settings=selected['settings'],full_pipeline='NOT RUN',shared_portfolio_ftmo='NOT RUN')
 save('VERDICT.json',verdict);save('COMPARISON.json',list(qs.values()))
 regime_rows=pd.read_csv(R/'native/raw-5y/regimes.csv');last=regime_rows.iloc[-1]
 counts=np.array([float(last[k]) for k in ['b_b','b_s','b_u','s_b','s_s','s_u','u_b','u_s','u_u']]).reshape(3,3)
 matrix=counts/counts.sum(axis=1,keepdims=True);state=int(last.state)
 eigen,vectors=np.linalg.eig(matrix.T);mix=np.real(vectors[:,np.argmin(abs(eigen-1))]);mix=mix/mix.sum()
 snapshot=dict(asset='XAUUSD',asof_candidate=pd.Timestamp(int(last.epoch),unit='s',tz='UTC').isoformat(),completed_d1_start=pd.Timestamp(int(last.d1_epoch),unit='s',tz='UTC').isoformat(),
  params=dict(window=40,threshold=.05,minimum_labels=252),states=['Bear','Sideways','Bull'],current_regime=['Bear','Sideways','Bull'][state],
  transition_matrix=matrix.tolist(),next_state_probabilities=dict(zip(['bear','sideways','bull'],matrix[state].tolist())),signal=float(last.signal),
  persistence_diagonal=dict(zip(['bear','sideways','bull'],np.diag(matrix).tolist())),stationary_distribution=dict(zip(['bear','sideways','bull'],mix.tolist())),
  scope='Last recorded historical entry candidate, not current market forecast. Matrix uses only that candidate’s past completed D1 history. Snapshot stationary mix NOT applied to earlier trades or risk sizing.',
  framework='Roan (@RohOnChain); skill helper script unavailable, exact EA implementation audited directly; historical, not forward-looking.')
 save('REGIME AUDIT.json',snapshot)
 annual=[]
 for tag in ['raw-5y','candidate-5y']:
  for year in range(2021,2027):
   ts=[t for t in qs[tag]['trades'] if pd.Timestamp(t['close_epoch'],unit='s',tz='UTC').year==year]
   if not ts:continue
   vals=[t['net'] for t in ts];w,l=a.stats.streaks(vals)
   annual.append(dict(version=tag,year=year,partial_year=year in [2021,2026],trades=len(ts),net_profit=round(sum(vals),2),initial_base_contribution_pct=sum(vals)/100,pf=pf(vals),win_rate=sum(v>0 for v in vals)/len(vals)*100,win_streak=w,loss_streak=l))
 save('ANNUAL.json',annual)
 parts=[f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Asia Breakout Gold · optimisation review</title><style>{CSS}</style></head><body><main><p class="small">CALYX · ONE EA AT A TIME · 5 OCTOBER 2026</p><h1>Asia Breakout Gold<br>Better exits—or a different session?</h1><div class="notice">Research only. No live EAs, BATs, public website or account settings changed. Gold/Silver news deferred; Trend1.5R future keep preserved. Stop here for review.</div>']
 parts.append(f'<p><a href="{(B/"Active EA Recent Review 2026-10-05/Results.html").as_uri()}">All active-EA keep / pause / review decisions</a></p><h2>{verdict["decision"]}</h2><p>Older native gate: {"PASS" if qualified else "FAIL"}. Latest preference: {"PASS" if recent_ok else "FAIL"}. Five-year robustness: {"PASS" if long_ok else "FAIL"}. This is a bounded exploratory audit, not a full-pipeline certified replacement.</p>')
 clock=qs['utc-current-1y']['metrics']
 parts.append(f'<div class="notice"><b>Important clock warning.</b> The current SET’s tester assumes UTC+2/+3; live code ignores this tester setting. The UTC-aligned current replay returned {fmt(clock["return_pct"])}%, PF {fmt(clock["pf"],3)}, {clock["trades"]} trades in the same latest year—not the +14.14% historical tester headline. Treat both as explicit timing replays, not verified live-chart results. Details below.</div>')
 raw=qs['raw-1y']['metrics'];cand=qs['candidate-1y']['metrics']
 parts.append(f'<div class="cards"><div class="card">Current → candidate wins<b>{fmt(raw["win_rate"],1)} → {fmt(cand["win_rate"],1)}%</b></div><div class="card">Annual net PF<b>{fmt(raw["pf"])} → {fmt(cand["pf"])}</b></div><div class="card">Annual positions<b>{raw["trades"]} → {cand["trades"]}</b></div><div class="card">New configurations<b>{search["configurations"]}</b></div></div>')
 parts.append('<h2>Frozen candidate</h2><pre>'+esc(json.dumps(selected['settings'],indent=2))+'</pre><p>Other inputs remain the shipped SET: Markov on unless shown otherwise, midpoint SL unless shown otherwise, 1% equity sizing, one entry/day and one concurrent own position. No ADX/DI was reinstated. Lower R targets can increase win rate while reducing returns; compare all windows, sample sizes and loss runs.</p>')
 parts.append('<h2>Current versus candidate · fresh native MT5</h2><p>Each period starts $10,000 independently. All end 2026-10-05 exclusive: 1Y from2025-10-05; 6M from2026-04-05; 3M from2026-07-05; 3Y from2023-10-05; 5Y from2021-10-05. XAUUSD Exness, 150ms, Model4, native commission/swap included. Daily Sharpe is sampled floating-equity return annualised √252. Native intraday drawdown is in the table, not the lower-resolution graph. Overlapping returns are not additive.</p>'+table([row(qs[tag]) for tag in tags[:10]]))
 for window in ['1y','3m','5y']:
  curves=[];dds=[]
  for kind in ['raw','candidate']:
   q=qs[kind+'-'+window];d=daily(q);label='Current' if kind=='raw' else 'Candidate';start=pd.Timestamp(q['window'][0].replace('.','-'),tz='UTC').timestamp()
   curves.append((label,[(start,10000.)]+[(t.timestamp(),float(v)) for t,v in d.items()]))
   dds.append((label,[(start,0.)]+[(t.timestamp(),float(v)) for t,v in (100*(d/d.cummax().clip(lower=10000.)-1)).items()]))
  parts.append(a.graph(curves,window.upper()+' · sampled daily floating equity (USD)'));parts.append(a.graph(dds,window.upper()+' · sampled daily-close equity drawdown (%)'))
 parts.append('<h2>What the code audit found</h2><p>The shipped bot uses two stop managers: M15-close lock at50% of TP distance, locking20%; plus tick trailing hardcoded to2R start and0.5R gap. Its legacy “initial R” changes whenever SL moves. The visible InpTrailStartR/InpTrailDistanceR inputs do not affect Asia’s hardcoded manager. New stable management keeps a fixed TP-implied R=(originalTP−filled entry)/configuredRR; it does not recompute R from the moved SL. Small fill differences mean this is not identical to original entry-to-SL risk.</p>')
 parts.append('<div class="notice">Clock mismatch: current historical tests use mode1 (UTC+2/+3 assumption). Exness live automatic offset is UTC0. Thus mode1’s “00–08 UTC” range corresponds to server02–10 winter /03–11 summer, and entries10–15 /11–16. Mode0 below uses actual UTC server timing with unchanged current entry/exit mechanics. Neither replay verifies attached live chart settings; the clock diagnostic is not a matched-trade exit comparison.</div>'+table([row(qs['raw-1y']),row(qs['utc-current-1y']),row(qs['raw-3m']),row(qs['utc-current-3m'])]))
 parts.append('<h2>Older checks · before recent results</h2><p>Development2021-10-05–2024-10-05, validation2024-10-05–2025-10-05. Selection used older training then up to3 native finalists. Validation was reused for selection; no claim of independent holdout. Qualification requires≥90/30 trades, positive, PF≥1.20, WR≥50%, W run>L run, DD≤15%, no execution failures. No gate relaxed.</p>'+table([row(qs['candidate-train']),row(qs['candidate-valid'])]))
 finalrows=[]
 for tag,v in selected['confirmed'].items():
  for window in ['train','valid']:
   q=read(f'native/confirm-{tag}-{window}/results.json');verify(q);finalrows.append(row(q))
 parts.append('<details><summary>All native development / validation finalists</summary>'+table(finalrows)+'</details>')
 parts.append('<h2>Annual attribution · full five-year accounts</h2><p>2021/2026 partial. Net contribution divided by original10k; inherited compounding, not independently reset annual backtests.</p>'+table([[x['version'],str(x['year'])+(' partial' if x['partial_year'] else ''),x['trades'],fmt(x['net_profit']),fmt(x['initial_base_contribution_pct'])+'%',fmt(x['pf'],3),fmt(x['win_rate'],1)+'%',f"{x['win_streak']}/{x['loss_streak']}"] for x in annual],['Version','Year','Trades','Net $','Initial-base contribution','PF','Win rate','W/L']))
 mcrows=[]
 for tag,v in robustness.items():
  z=v['bootstrap'];mcrows.append([tag,z['positive_paths_pct'],fmt(z['return_p05_pct'])+'%',fmt(z['return_p50_pct'])+'%',fmt(z['pf_p05'],3),fmt(z['closed_dd_p95_pct'])+'%',fmt(v['sharpe_statistics']['deflated_sharpe_pct'])+'%',fmt(v['extra_observed_spread']['pf'],3),str(v['gate'])])
 parts.append('<h2>10,000-path Monte Carlo · descriptive, not forecast</h2><p>Block5 bootstrap, shuffle, random10/20% trade omission. Whole-position proportional closed returns with costs, not floating-equity, margin, exact-lot, calendar or FTMO simulation. Extra one observed entry spread stress keeps fills/sizes unchanged. Deflated Sharpe counts new trials plus6 earlier Asia filter variants; unknown wider searches make it optimistic. Previously seen history is not untouched evidence.</p>'+table(mcrows,['Version','Positive paths %','Return P5','Return median','PF P5','Closed DD P95','Approx DSR','Extra spread PF','All MC gates']))
 parts.append('<details><summary>Full uncertainty, shuffled and omission results</summary><pre>'+esc(json.dumps(robustness,indent=2))+'</pre></details>')
 parts.append('<h2>Execution and no-lookahead evidence</h2><p>Default shipped-EX5 parity: '+str(read('parity.json')['deal_rows'])+' native deal rows exactly match entry/exit/volume/costs. All whole positions independently reconcile to the native reports. The regime skill guided a completed-D1, past-only audit; its helper script is unavailable, so the existing engine was directly checked. Every recorded matrix excludes the newest transition and has training cutoff before the latest completed day. Framework Roan (@RohOnChain). No full-sample matrix applied backwards.</p>')
 parts.append('<details><summary>Historical regime diagnostic · not today’s forecast</summary><pre>'+esc(json.dumps(snapshot,indent=2))+'</pre></details>')
 execrows=[]
 for tag in tags:
  q=qs[tag];c=q['counters'];execrows.append([tag,q['native']['history_quality'],c['order_failed'],c['stable_modify_failed'],str(c['unique_original_dynamic_modify_failure_events'])+' ('+str(c['legacy_or_dynamic_modify_failed'])+')',fmt(q['metrics']['max_actual_risk_budget_ratio'],3)+'×',fmt(q['metrics']['commission']),fmt(q['metrics']['swap']),q['operational_failure']])
 parts.append(table(execrows,['Version','History %','Entry fails','Stable trail fails','Original/DTS unique events (log mentions)','Max risk/budget','Commission $','Swap $','Any failure']))
 parts.append('<p class="small">Failure mentions can appear in both parent and agent journals; identical server-time/message events are deduplicated above. Realised metrics with failures are descriptive only, not qualifying replacements.</p>')
 notes=sorted(set(note for q in qs.values() for note in q['tick_notes']));parts.append('<p class="small">Tick coverage: '+esc(' | '.join(notes) or 'Read source journals; report quality alone is not proof of real ticks.')+'</p><p>Upward/minimum-lot rounding means risk may exceed1%. Position exits at test end are administrative forced closes, not a production time exit. Earlier generated ticks, missing broker ticks and retrospective selection limit confidence.</p>')
 parts.append('<h2>All screened settings · retained, not hidden</h2><p>Model1 development screens use generated every tick; not headline native Model4 results. Distinct configurations counted even when low targets make trailing inactive. Bounded search does not exhaust every full-pipeline dimension or random-entry control. Settings changed one factor at a time after the first exit search.</p>')
 srows=[]
 for v in search['rows']:
  m=v['metrics'];srows.append([v['tag'],m['trades'],fmt(m['win_rate'],1)+'%',fmt(m['pf'],3),fmt(m['return_pct'])+'%',fmt(v['equity_dd'])+'%',f"{m['win_streak']}/{m['loss_streak']}",str(v['qualified']),json.dumps(v['settings'],sort_keys=True)])
 parts.append(table(srows,['Setting','Trades','Win rate','Net PF','Return','Native DD','W/L','Gate','Overrides']))
 parts.append('<details><summary>Frozen protocol</summary><pre>'+esc((R/'PROTOCOL.md').read_text())+'</pre></details><p class="small">Historical simulations, not future guarantees. Production preserved. Shared portfolio / prop passing days / payout rate not recalculated. <a href="COMPARISON.json">Full native metrics</a> · <a href="SEARCH RESULTS.json">Every configuration</a> · <a href="ROBUSTNESS.json">Monte Carlo</a> · <a href="ANNUAL.json">Annual cash attribution</a></p></main></body></html>')
 (R/'Results.html').write_text(''.join(parts),encoding='utf-8')
 save('VERIFICATION.json',dict(native_comparisons=len(qs),parity=read('parity.json'),all_cash_costs_deals_reconciled=True,production_hashes_unchanged=True,selected_before_candidate_replays=True,regime_audit='completed D1 / past-only transitions',
  mc_paths=10000,configurations=search['configurations'],no_deployment=True,verdict=verdict))
 print(json.dumps(verdict,indent=2))
if __name__=='__main__':main()
