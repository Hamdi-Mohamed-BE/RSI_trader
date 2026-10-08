"""Post-freeze evidence audit and offline report; no parameter selection here."""
from pathlib import Path
from datetime import datetime
import gzip,html,importlib.util,math,re
import numpy as np,pandas as pd
import runner as r,build_engine as e
R=r.R;C=r.CONFIG
spec=importlib.util.spec_from_file_location('calyx_evidence_audit',R.parent.parent/'Calyx Research Pipeline/calyx_pipeline.py')
# dataclasses require the imported module to be registered.
import sys
a=importlib.util.module_from_spec(spec);sys.modules[spec.name]=a;spec.loader.exec_module(a)

def path_for(row,suffix):return R/'native'/row['stage']/(str(row['index'])+'-'+suffix+'.csv.gz')

def equity(row):
 df=pd.read_csv(path_for(row,'equity'))
 assert not df.empty and df.epoch.is_monotonic_increasing
 assert abs(float(df.iloc[-1].balance)-10000-row['metrics']['net'])<.03
 df['day']=pd.to_datetime(df.epoch,unit='s').dt.normalize()
 observed_end=min(pd.Timestamp(row['end'])-pd.Timedelta(days=1),pd.Timestamp(row['native']['last_quote_epoch'],unit='s').normalize())
 dates=pd.date_range(row['start'],observed_end)
 end=df.groupby('day')[['balance','equity']].last().reindex(dates).ffill().fillna(10000)
 # Every final position is liquidated by MT5 before OnTester. Native DD
 # covers every tick; this one-minute path is not a replacement for it.
 ret=end.equity.pct_change().fillna(end.equity.iloc[0]/10000-1)
 return df,end,ret

def monte_carlo(pnl,returns,seed):
 """Circular five-observation blocks, 10k paths, bounded memory."""
 rng=np.random.default_rng(seed);paths=C['bootstrap_paths'];block=C['bootstrap_block']
 def indices(length):
  starts=rng.integers(0,length,size=(paths,math.ceil(length/block)))
  return ((starts[:,:,None]+np.arange(block))%length).reshape(paths,-1)[:,:length]
 p=np.asarray(pnl,float);rs=np.asarray(returns,float)
 sampled=p[indices(len(p))];gp=np.maximum(sampled,0).sum(axis=1);gl=-np.minimum(sampled,0).sum(axis=1)
 pfs=np.divide(gp,gl,out=np.full(paths,np.nan),where=gl>0)
 x=rs[indices(len(rs))];curves=np.cumprod(np.maximum(0,1+x),axis=1)
 peaks=np.maximum.accumulate(np.concatenate([np.ones((paths,1)),curves],axis=1),axis=1)[:,1:]
 dd=np.max((peaks-curves)/peaks,axis=1)*100;final=(curves[:,-1]-1)*100
 def qs(z):return np.nanquantile(z,[.05,.5,.95]).tolist()
 return dict(paths=paths,block=block,seed=seed,return_p05_p50_p95=qs(final),pf_p05_p50_p95=qs(pfs),
  max_dd_p05_p50_p95=qs(dd),probability_profit_pct=float(np.mean(final>0)*100),
  daily_5pct_breach_proxy_pct=float(np.mean(np.any(x<=-.05,axis=1))*100),
  initial_balance_10pct_breach_proxy_pct=float(np.mean(np.any(curves<=.9,axis=1))*100),
  scope='Closed-balance daily returns / trade cash separately resampled in circular five-observation blocks. Monte Carlo omits floating/intraday extrema and does not resize/reexecute synthetic trades. Breaches are closed-P&L proxies, not FTMO challenge probabilities.')

def quote_cost(row):
 q=pd.read_csv(path_for(row,'quotes'));q=q[(q.entry==0)&(q.volume>0)&(q.spread_cash>=0)&(q.epoch>=pd.Timestamp('2026-01-02').timestamp())]
 if q.empty:return dict(status='unavailable',observations=0)
 cost=float((q.spread_cash/q.volume).median())
 if cost<=0:
  return dict(status='unavailable_zero_spread_quotes',observations=len(q),median_extra_usd_per_lot=0,
   scope='All sampled 2026 entry quotes have identical bid/ask. Charging another zero spread is not a meaningful stress test. No positive broker cost was invented; the mandatory extra-cost gate fails. Results may be optimistic if this feed does not represent executable spreads.')
 p=[t['net_profit']-cost*t['volume'] for t in row['trades']]
 return dict(status='measured_extra_spread_sensitivity',observations=len(q),median_extra_usd_per_lot=cost,
  mean_extra_usd_per_trade=float(np.mean([cost*t['volume'] for t in row['trades']])),net=sum(p),return_pct=sum(p)/100,pf=a.profit_factor(p),
  win_rate_pct=sum(v>0 for v in p)/len(p)*100,
  scope='One additional full quoted bid/ask spread per round trip, using the median entry spread cash per lot measured on available 2026 native real-tick quotes. Existing spread, commissions and swaps already remain in baseline P&L. Indicative widening sensitivity, not an exact rerun with widened quotes or a guaranteed future spread.')

def audit(row,trials,seed):
 df,daily,ret=equity(row);p=[t['net_profit'] for t in row['trades']];n=len(p)
 assert n>0
 wl=a.wilson_interval(sum(v>0 for v in p),n)
 # Follow the central policy's closed-P&L proxy; native floating DD and
 # daily-equity Sharpe are separately retained, never substituted by MC.
 cash=pd.Series(0.,index=daily.index)
 for t in row['trades']:cash.loc[pd.Timestamp(t['close_time']).normalize()]+=t['net_profit']
 balance=10000+cash.cumsum();closed_ret=cash/balance.shift(1).fillna(10000)
 mc=monte_carlo(p,closed_ret,seed);cost=quote_cost(row)
 outcomes=[a.TradeOutcome(datetime.fromisoformat(t['close_time']),t['net_profit']) for t in row['trades']]
 thirds=a.subperiods(outcomes);sharpe=a.sharpe_statistics(ret.tolist(),trials,365)
 half=a.profit_factor(p[len(p)//2:])
 sample_dd=float(np.max(1-df.equity/np.maximum.accumulate(np.maximum(10000,df.equity)))*100)
 gates=dict(minimum_30_trades=n>=30,positive_return=row['metrics']['net']>0,pf_above_1=(row['metrics']['pf'] or 0)>1,
  bootstrap_return_p05_positive=mc['return_p05_p50_p95'][0]>0,bootstrap_pf_p05_above_1=mc['pf_p05_p50_p95'][0]>1,
  deflated_sharpe_95pct=sharpe['deflated_sharpe_pct']>=95,recent_half_pf_above_1=half>1,
  two_of_three_chronological_parts_positive=sum(x['net_profit']>0 for x in thirds)>=2,
  total_breach_proxy_below_5pct=mc['initial_balance_10pct_breach_proxy_pct']<5,
  measured_cost_stress_pf_above_1=cost.get('pf',0)>1,native_floating_path_present=True)
 return dict(metrics=row['metrics'],wilson95_pct=[100*x for x in wl],monte_carlo=mc,sharpe=sharpe,recent_half_pf=half,
  thirds=thirds,cost_stress=cost,native_dd_pct=row['metrics']['equity_dd'],sampled_minute_dd_pct=sample_dd,
  daily_equity_expected_shortfall_95_pct=a.expected_shortfall(ret.tolist())*100,
  daily_closed_balance_expected_shortfall_95_pct=a.expected_shortfall(closed_ret.tolist())*100,
  gates=gates,all_gates_pass=all(gates.values()),
  verdict='PASS_FOR_FORWARD_RESEARCH' if all(gates.values()) else 'WATCH_ONLY' if row['metrics']['net']>0 and (row['metrics']['pf'] or 0)>1 else 'REJECT',
  live_promotion=False,deflated_sharpe_note='Uses central pipeline independent-trial approximation with every unique searched configuration; not a correction for all researcher choices or a promise of future Sharpe.')

def f(v,d=2):return '—' if v is None or not math.isfinite(float(v)) else f'{float(v):.{d}f}'
def pct(v):return f'{v:+.2f}%'
def esc(v):return html.escape(str(v))
def table(headers,rows):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'

def quality(row):
 raw=gzip.decompress((R/'native'/row['stage']/'report.htm.gz').read_bytes())
 text=raw.decode('utf-16') if raw[:2] in [b'\xff\xfe',b'\xfe\xff'] else raw.decode('utf-8',errors='replace')
 match=re.search(r'>\s*History Quality:\s*</td>\s*<td[^>]*>\s*<b>(.*?)</b>',text,re.I|re.S)
 history=html.unescape(re.sub('<[^>]+>','',match.group(1))).strip() if match else 'not reported'
 journal=gzip.decompress((R/'native'/row['stage']/'journal.txt.gz').read_bytes()).decode('utf-8',errors='replace')
 notes=sorted(set(x.strip() for x in re.findall(r'[^\r\n]*real ticks[^\r\n]*',journal,re.I)))
 return dict(history_quality=history,real_tick_notes=notes,dynamic_helper_rejection_log_lines=len(re.findall('Dynamic trailing SL modification failed',journal)))

def rules(p):
 anchors={0:'09:30 New York',1:'08:00 Berlin',2:'09:00 Berlin',3:'09:30 Berlin',4:'10:00 Berlin',5:'10:00 New York',6:'08:30 Berlin',7:'15:30 Berlin'}
 stop=({'0':f"ATR14 × {f(p['InpInitialStopATR'])}",'1':f"Signal-candle extreme + {f(p['InpSignalStopBufferATR'])} ATR buffer",'2':f"{f(p['InpInitialStopPercent'])}% of entry price"})[str(int(p['InpStopMode']))]
 target=f"{f(p['InpRewardRisk'])}R" if p['InpUseFixedTarget'] else 'No fixed target'
 if p['InpUseAdaptiveRR']:target+=f"; strong body ≥{f(p['InpAdaptiveStrongBodyATR'])} ATR → {f(p['InpAdaptiveStrongRR'])}R"
 trail=f"ATR14 × {f(p['InpTrailingATR'])}, arms at {f(p['InpTrailStartR'])}R" if p['InpUseATRTrailing'] else f"MA{int(p['InpTrailMAPeriod'])}, arms at {f(p['InpTrailMAStartR'])}R" if p['InpUseMATrailing'] else 'Off'
 extras=[]
 if p['InpUseBreakEven']:extras.append(f"BE arms at {f(p['InpBreakEvenTriggerR'])}R; locks {f(p['InpBreakEvenLockR'])}R")
 if p['InpUseDynamicTrailingSL']:
  extras.append(f"Completed M15 close reaches {f(100*p['InpDynamicTriggerFraction'])}% of initial TP distance → lock {f(100*p['InpDynamicLockFraction'])}% of TP distance; this is a one-level lock, alongside any ATR/MA trail")
 holding=f"{int(p['InpMaximumHoldingMinutes'])} minutes" if p['InpMaximumHoldingMinutes'] else 'No maximum hold'
 if p['InpCloseAtSessionEnd']:holding+='; session close '+('17:25 Berlin' if p['ResearchBerlinClose'] else '15:55 New York')
 filters=[]
 for k in ['ResearchADXMinimum','ResearchADXMaximum','InpMinimumBodyATR','InpMinimumBodyFraction','InpMinimumEMADistanceATR','InpMaximumEMADistanceATR','InpMinimumRelativeVolume']:
  if p[k]:filters.append(k+' = '+f(p[k]))
 if p['InpRequireEMASlope']:filters.append('EMA slope agrees')
 if p['ResearchRequireBodyDirection']:filters.append('Candle-body direction agrees')
 if p['ResearchSkipWeekday']:filters.append({1:'Skip Monday',2:'Skip Friday',3:'Skip Monday and Friday'}[int(p['ResearchSkipWeekday'])])
 return [('Symbol','Exness DE30 (Germany DAX CFD)'),('Signal',f"First completed M{int(p['InpSignalTimeframe'])} candle starting at {anchors[int(p['ResearchAnchor'])]}; EMA{int(p['InpEMAPeriod'])} close comparison"),
 ('Direction','Both' if p['InpAllowLong'] and p['InpAllowShort'] else 'Long only' if p['InpAllowLong'] else 'Short only'),
 ('DI',f"{'ON' if p['InpRequireDIAgreement'] else 'OFF'}, period {int(p['InpDIPeriod'])}"),('Additional filters','; '.join(filters) or 'None'),
 ('Initial stop',stop),('Profit target',target),('Trailing stop',trail),('Break-even / dynamic','; '.join(extras) or 'Off'),('Time exit',holding),
 ('Sizing','1% current equity target; original upward lot-step / broker-minimum rounding retained. Not a guaranteed loss cap.'),
 ('Scope','Tester-only research binary; cannot attach to a live chart. No live source, preset, BAT or website change.')]

def svg_curves(rows):
 curves=[]
 for label,row in rows:
  _,day,_=equity(row);curves.append((label,day.equity.to_numpy()))
 values=np.concatenate([z for _,z in curves]);low=min(10000,values.min());high=max(10000,values.max());span=max(1,high-low)
 colors=['#62e2bb','#f3b55e'];parts=['<svg viewBox="0 0 1000 310" role="img" aria-label="Daily equity comparison">']
 for i in range(5):
  y=260-i*55;v=low+span*i/4;parts.append(f'<path d="M85 {y} H960" stroke="#29433c"/><text x="5" y="{y+5}" fill="#aac4bb">${v:,.0f}</text>')
 for i,(label,vals) in enumerate(curves):
  ids=np.unique(np.linspace(0,len(vals)-1,min(1200,len(vals))).astype(int))
  pts=' '.join(f'{85+875*j/max(1,len(vals)-1):.1f},{260-220*(vals[j]-low)/span:.1f}' for j in ids)
  parts.append(f'<polyline points="{pts}" fill="none" stroke="{colors[i]}" stroke-width="1.8"/><text x="{100+i*410}" y="295" fill="{colors[i]}">{esc(label)}</text>')
 return ''.join(parts)+'</svg>'

def overview(records,audits):
 headers=['Period / requested dates','Version','Trades','Return','Net PF','Win rate','Equity DD','Daily equity Sharpe','Win / loss streak']
 lines=[]
 for period in ['2020–2023','OOS','2024','2025','2026 YTD','1 year','6 months','3 months']:
  for variant in ['baseline','candidate']:
   key=period+' '+variant;row=records[key];m=row['metrics'];au=audits[key]
   end=(pd.Timestamp(row['end'])-pd.Timedelta(days=1)).date()
   lines.append([esc(period)+f'<small>{row["start"]} → {end}</small>',variant,m['trades'],pct(m['return_pct']),f(m['pf']),f(m['win_rate_pct'])+'%',f(m['equity_dd'])+'%',f(au['sharpe']['annualized_sharpe']),f'{m["max_win_streak"]} / {m["max_loss_streak"]}'])
 return table(headers,lines)

def main():
 frozen=r.load(R/'FROZEN.json');records=r.load(R/'EVALUATION.json');diagnostics=r.load(R/'DIAGNOSTICS.json')
 baseline=r.load(R/'native/parity-2020-2023/results.json')[0]
 chosen=r.load(R/'native/selected-2020-2023/results.json')[0]
 records={'2020–2023 baseline':baseline,'2020–2023 candidate':chosen}|records
 trials=frozen['unique_tested_configurations'];audits={}
 # Full robustness audit on the temporal holdout only; other tables get
 # native daily Sharpe/CI/cost data without spending 10k paths per row.
 for i,(key,row) in enumerate(records.items()):
  if key.startswith('OOS '):au=audit(row,trials,C['seed']+i)
  else:
   _,_,ret=equity(row);wl=a.wilson_interval(sum(t['net_profit']>0 for t in row['trades']),len(row['trades']))
   au=dict(sharpe=a.sharpe_statistics(ret.tolist(),trials,365),wilson95_pct=[100*x for x in wl],cost_stress=quote_cost(row))
  au['data_quality']=quality(row);audits[key]=au
 original=r.load(R/'PRODUCTION FINGERPRINTS.json');sourceaudit=r.load(R/'SOURCE AUDIT.json')
 unchanged=all(r.sha(Path(path))==digest for path,digest in original.items()) and e.fingerprints()==sourceaudit['source_fingerprints']
 assert unchanged,'Production changed during isolated study'
 chronology={name:Path(R/'native'/name/'manifest.json').stat().st_mtime>=Path(R/'FROZEN.json').stat().st_mtime for name in [row['stage'] for key,row in records.items() if not key.startswith('2020')]}
 assert all(chronology.values()),'Holdout evaluated before freeze'
 audits['proof']=dict(production_unchanged=unchanged,original_707_trade_parity=r.load(R/'PARITY.json')['exact'],holdout_manifests_after_freeze=chronology)
 r.save(R/'AUDITS.json',audits)
 candidate=audits['OOS candidate'];m=records['OOS candidate']['metrics'];mb=records['OOS baseline']['metrics']
 last_quote=str(pd.Timestamp(records['OOS candidate']['native']['last_quote_epoch'],unit='s'))
 summary=dict(study=C,last_available_oos_broker_quote_utc=last_quote,chosen_parameters=frozen['parameters'],unique_configurations=trials,native_search_passes=frozen['native_search_passes'],
  internal_validation_pass=frozen['passed_internal_validation'],candidate_oos=m,baseline_oos=mb,candidate_audit=candidate,production_unchanged=unchanged,
  failed_gates=[key for key,value in candidate['gates'].items() if not value],
  decision='Research only. '+('Eligible for a forward research test, not live deployment.' if candidate['all_gates_pass'] and frozen['passed_internal_validation'] else 'Fails one or more validation gates; do not call it a validated improvement.'))
 r.save(R/'SUMMARY.json',summary)
 development=r.load(R/'DEVELOPMENT TABLE.json');validation=r.load(R/'VALIDATION TABLE.json');progress=r.load(R/'SEARCH PROGRESS.json')
 intro=f'''<h1>DAX momentum · full research pipeline</h1><p>2020–2023 development / 2024 onward retrospective out-of-sample</p>
 <div class="notice">{esc(summary['decision'])} Live EAs, BATs, presets and website remain unchanged.</div>
 <p>{trials} unique settings; {frozen['native_search_passes']} screening / neighbourhood passes. 2020–2022 searches, 2023 finalist check, frozen settings before all 2024+ evaluation. Raw PF 1.11 misses the usual raw gate: optimisation is exploratory.</p>
 <p>All native runs start with $10,000, use a 1% equity-risk target, and include broker commissions, spread, swaps and 150 ms execution delay. Calendar-period runs restart separately; yearly returns must not be added. Requested endpoint is today; latest available OOS broker quote: {esc(last_quote)} UTC. Today is provisional and may be missing or incomplete. Final tester liquidations are included.</p>
 <p>History limitations: no real ticks in development. Older OOS history is generated; real ticks begin in 2026. “Every tick based on real ticks” mode falls back where broker real ticks are missing. These are DAX CFD results, not futures/NQ results.</p>
 <div class="notice">Cost warning: sampled 2026 entry quotes have identical bid and ask. A zero extra spread is not a stress test. Native commission/swap remain included, but the mandatory broker-extra-cost gate is unavailable / failed. The recent results may be optimistic if this quote feed does not reflect executable spreads.</div>
 <p>The baseline’s later history was viewed in prior work, so this is a retrospective temporal holdout—not a completely untouched experiment. No parameter re-selection occurred after 2024+ evaluation.</p>'''
 blocks=[intro,'<h2>Frozen settings</h2>',table(['Rule','Selected candidate'],[(esc(k),esc(v)) for k,v in rules(frozen['parameters'])]),
  '<h2>Original versus frozen candidate</h2><p>PF / wins are calculated from net position P&amp;L including all deal costs. DD is native maximum relative floating-equity DD, not closed-balance DD. Sharpe uses daily equity returns including zero-return calendar days (365 annualisation), not chart-sensitive MT5 Sharpe.</p>',overview(records,audits),
  '<h2>Out-of-sample daily equity</h2>',svg_curves([('Frozen candidate',records['OOS candidate']),('Unchanged baseline',records['OOS baseline'])]),
  '<h2>2023 internal finalist check</h2>',table(['Finalist','Trades','Return','PF','Win rate','Equity DD'],[[i,x['metrics']['trades'],pct(x['metrics']['return_pct']),f(x['metrics']['pf']),f(x['metrics']['win_rate_pct'])+'%',f(x['metrics']['equity_dd'])+'%'] for i,x in enumerate(validation)]),
  '<p>At most three development finalists, including raw. Selection was based on this pre-2024 check and development parameter-neighbour stability; not the best later return.</p>',
  '<h2>Development stages · screening only</h2>',table(['Stage','Top screening trades','Return','PF','Win rate','DD'],[[s,x[0]['metrics']['trades'],pct(x[0]['metrics']['return_pct']),f(x[0]['metrics']['pf']),f(x[0]['metrics']['win_rate_pct'])+'%',f(x[0]['metrics']['equity_dd'])+'%'] for s,x in progress['stages'].items()]),
  '<p>M1 OHLC screening is an approximation. Finalists, full 2020–2023 and every OOS table use native tick-level tests. A two-candidate staged beam search is not an exhaustive global optimum.</p>',
  '<h2>Parameter-neighbour robustness · 2020–2022 only</h2>',table(['Selected?','Profitable neighbours','Median neighbour PF','Neighbour count'],[['Yes' if x['center']==frozen['parameters'] else 'No',f(x['positive_neighbour_share']*100)+'%',f(x['median_pf']),x['neighbours']] for x in frozen['plateaus']])]
 for version in ['candidate','baseline']:
  au=audits['OOS '+version];mc=au['monte_carlo'];ss=au['sharpe'];cost=au['cost_stress'];ci=au['wilson95_pct']
  blocks += [f'<h2>{esc(version.title())} · locked OOS robustness</h2>',table(['Metric','Value'],[
   ['Win rate 95% Wilson interval',f'{f(ci[0])}%–{f(ci[1])}%'],['Daily equity Sharpe',f(ss['annualized_sharpe'])],
   ['Deflated Sharpe probability, all searched settings',f(ss['deflated_sharpe_pct'])+'%'],['Recent half-trades net PF',f(au['recent_half_pf'])],
   ['95% daily equity / closed-balance expected shortfall',f(au['daily_equity_expected_shortfall_95_pct'])+'% / '+f(au['daily_closed_balance_expected_shortfall_95_pct'])+'%'],
   ['Monte Carlo paths / block','10,000 / 5 observations'],['Probability profitable',f(mc['probability_profit_pct'])+'%'],
   ['Return P5 / median / P95',' / '.join(pct(x) for x in mc['return_p05_p50_p95'])],['PF P5 / median / P95',' / '.join(f(x) for x in mc['pf_p05_p50_p95'])],
   ['Closed-balance max DD P5 / median / P95',' / '.join(f(x)+'%' for x in mc['max_dd_p05_p50_p95'])],
   ['5% daily / initial-equity 10% total breach proxies',f(mc['daily_5pct_breach_proxy_pct'])+'% / '+f(mc['initial_balance_10pct_breach_proxy_pct'])+'%'],
   ['Measured extra-cost PF',f(cost.get('pf'))],['Measured median extra USD / lot',f(cost.get('median_extra_usd_per_lot'))],
   ['Real-tick quote observations',cost['observations']],['Native / sampled-minute floating DD',f(au['native_dd_pct'])+'% / '+f(au['sampled_minute_dd_pct'])+'%']]),
   '<p>'+esc(mc['scope'])+'</p><p>'+esc(cost.get('scope','Cost stress unavailable'))+'</p>',
   table(['Chronological trade-count third','Dates','Trades','Net USD','PF'],[[x['part'],x['start'][:10]+' → '+x['end'][:10],x['trades'],f(x['net_profit']),f(x['profit_factor'])] for x in au['thirds']]),
   table(['Promotion gate','Result'],[[esc(k.replace('_',' ')),'PASS' if v else '<span class="bad">FAIL</span>'] for k,v in au['gates'].items()]),
   '<p>Evidence verdict: '+esc(au['verdict'])+'. This does not override the exploratory raw-gate failure or authorise live installation.</p>']
 blocks += ['<h2>Execution / size sensitivity · frozen candidate only</h2>',table(['Diagnostic','Dates','Trades','Return','PF','Win rate','Native equity DD'],[[esc(label),row['start']+' → '+str((pd.Timestamp(row['end'])-pd.Timedelta(days=1)).date()),row['metrics']['trades'],pct(row['metrics']['return_pct']),f(row['metrics']['pf']),f(row['metrics']['win_rate_pct'])+'%',f(row['metrics']['equity_dd'])+'%'] for label,row in diagnostics.items()]),
  '<p>500 / 1,000 ms native-delay reruns are sensitivity checks; not parameter reselection. Half-risk native rerun retains broker lot rounding and may not halve losses exactly.</p>',
  '<h2>Data and execution audit</h2>',table(['Run','History quality / real-tick share','Failed entries','Core stop-update rejections','Last broker quote (UTC)'],[[esc(key),esc(audits[key]['data_quality']['history_quality']),int(row['native']['failed_entries']),int(row['native']['failed_updates']),str(pd.Timestamp(row['native']['last_quote_epoch'],unit='s'))] for key,row in records.items()]),
  '<p>Original stop-update retry behaviour is retained. Core market-closed or invalid-stop modification rejections are counted separately from entry rejections. Dynamic-helper rejections, if any, remain separately recorded in AUDITS.json and the archived journals. No failed entry is silently dropped from an eligible candidate.</p>',
  '<details><summary>All tested settings and metrics</summary>',table(['Stage','Case','Trades','Return','PF','Win rate','Equity DD','W / L streak','Full parameters'],[[esc(x['stage']),x['index'],x['metrics']['trades'],pct(x['metrics']['return_pct']),f(x['metrics']['pf']),f(x['metrics']['win_rate_pct'])+'%',f(x['metrics']['equity_dd'])+'%',str(x['metrics']['max_win_streak'])+' / '+str(x['metrics']['max_loss_streak']),'<code>'+esc(str(x['parameters']))+'</code>'] for x in development]),'</details>',
  '<details><summary>Full frozen OOS trade ledger</summary>',table(['Entry UTC','Exit UTC','Side','Lots','Entry','Exit','Initial SL','Initial TP','Commission','Swap','Fee','Net USD'],[[t['open_time'],t['close_time'],t['side'],f(t['volume']),f(t['open_price']),f(t['close_price']),f(t['initial_sl']),f(t['initial_tp']),f(t['commission']),f(t['swap']),f(t['fee']),f(t['net_profit'])] for t in records['OOS candidate']['trades']]),'</details>',
  '<h2>Files and method</h2><p><a href="SUMMARY.json">Summary JSON</a> · <a href="AUDITS.json">Complete robustness audit</a> · <a href="FROZEN.json">Frozen parameters / selection</a> · <a href="PARITY.json">Original 707-trade parity</a> · <a href="Frozen%20Research%20EA/">Tester-only source, binary and configuration</a></p>',
  '<p>Native-method references: <a href="https://www.mql5.com/en/docs/runtime/testing">MQL5 tester modes and limitations</a>; <a href="https://www.mql5.com/en/docs/constants/environment_state/statistics">MT5 statistic definitions</a>. No future-return choice, live-account trading or push was performed.</p>']
 style='''body{background:#081511;color:#dcefe7;font:16px/1.55 system-ui;margin:0}main{max-width:1320px;margin:auto;padding:30px}h1{font-size:36px}h2{color:#6de6c0;margin-top:40px}p{color:#adc9bd}a{color:#7ce7c5}small{display:block;font-size:12px;color:#99b8ab}.notice{border:1px solid #b08a42;background:#312817;padding:20px;border-radius:12px}.scroll{overflow:auto;margin:15px 0}table{border-collapse:collapse;min-width:650px;width:100%;font-variant-numeric:tabular-nums}th,td{text-align:left;padding:11px;border-bottom:1px solid #244235;vertical-align:top}th{background:#163428;color:#7ce7c5;white-space:nowrap}td:nth-child(n+3){white-space:nowrap}.bad{color:#ff9d9d}details{border:1px solid #365144;border-radius:10px;padding:15px;margin:22px 0}summary{cursor:pointer;color:#75e6c1}code{display:block;white-space:normal;max-width:750px;font-size:12px}svg{width:100%;background:#10251c;border-radius:14px}'''
 page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DAX Momentum Full Pipeline</title><style>'+style+'</style><main>'+''.join(blocks)+'</main></html>'
 # Generated report artifact, not source editing.
 (R/'Results.html').write_text(page,encoding='utf-8')
 r.status('FULL PIPELINE COMPLETE',report=str(R/'Results.html'),candidate_verdict=candidate['verdict'],candidate_oos_return=m['return_pct'],candidate_oos_pf=m['pf'])
 print(r.safe(summary),flush=True)

if __name__=='__main__':main()
