"""Self-contained HTML handoff, no external scripts or fabricated metrics."""
from pathlib import Path
import hashlib,html,json,math,shutil
from types import SimpleNamespace
R=Path(__file__).resolve().parent
def load(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')
r=SimpleNamespace(R=R,CONFIG=load(R/'config.json'),load=load,sha=sha,save=save)
def esc(x):return html.escape(str(x))
def f(v,n=2):return '—' if v is None or not math.isfinite(float(v)) else f'{v:.{n}f}'
def pct(v):return ('+' if v>=0 else '')+f(v)+'%'
def table(head,rows):
 return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(v)+'</th>' for v in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def chart(rows):
 w=1050;h=300;points=[v['equity'] for _,row in rows for v in row['daily_curve']]
 lo=min(10000,min(points));hi=max(10000,max(points));pad=max((hi-lo)*.08,20);lo-=pad;hi+=pad
 lines=[]
 for label,row in rows:
  data=row['daily_curve'];n=len(data)
  coords=' '.join(f'{50+i/max(1,n-1)*(w-70):.2f},{20+(hi-v["equity"])/(hi-lo)*(h-55):.2f}' for i,v in enumerate(data))
  color='#85ffcd' if label=='Candidate' else '#a6b6c7'
  lines.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2"/>')
 y0=20+(hi-10000)/(hi-lo)*(h-55)
 return f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Daily equity comparison"><line x1="50" y1="{y0}" x2="{w-20}" y2="{y0}" stroke="#64777c" stroke-dasharray="4 4"/><text x="3" y="25" fill="#a4bfbc">{hi:.0f}</text><text x="3" y="{h-35}" fill="#a4bfbc">{lo:.0f}</text>'+''.join(lines)+f'<text x="50" y="{h-4}" fill="#a4bfbc">{esc(rows[0][1]["start"])}</text><text x="{w-200}" y="{h-4}" fill="#a4bfbc">{esc(rows[0][1]["metrics"]["actual_last_quote_utc"][:10])}</text></svg><p class="muted">Grey: baseline · Green: frozen candidate. Daily end equity; full-tick native drawdown is reported separately.</p>'

def metrics_table(s):
 rows=[]
 for label,bkey,ckey in [
  ('In-sample 2020–2024','raw-5y-0','in-sample-selected-0'),
  ('Retrospective holdout 2025 onward','holdout-0','holdout-1'),
  ('Last year','recent-1y-0','recent-1y-1'),
  ('Last 6 months','recent-6m-0','recent-6m-1'),
  ('Last 3 months','recent-3m-0','recent-3m-1')]:
  for version,key in [('Baseline',bkey),('Candidate',ckey)]:
   m=s[key]['metrics']
   rows.append([esc(label),esc(s[key]['start'])+' → '+esc(s[key]['end_exclusive']),version,str(m['trades']),f(m['win_rate_pct'])+'%',f(m['pf']),pct(m['return_pct']),f(m['equity_dd'])+'%',f(m['daily_equity_sharpe']),f"{m['max_win_streak']} / {m['max_loss_streak']}"])
 return table(['Period','Dates (end exclusive)','Version','Trades','Win rate','PF','Return','Floating DD','Daily Sharpe','Win / loss streak'],rows)

def main():
 s=r.load(R/'SUMMARY.json');freeze=r.load(R/'FROZEN.json');sel=r.load(R/'SELECTION.json');v=r.load(R/'VERIFICATION.json');g=r.load(R/'RAW-GATES.json')
 chosen=s['holdout-1'];m=chosen['metrics'];raw=s['holdout-0'];mc=chosen['monte_carlo']
 out=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>US100 news reversion — exploratory pipeline</title><style>body{margin:0;background:#081512;color:#e5f5ef;font:16px system-ui;line-height:1.55}main{max-width:1200px;margin:auto;padding:32px 24px}h1{font-size:36px;line-height:1.2}h2{margin-top:38px}a{color:#8affd2}section,.box{background:#0d211c;border:1px solid #31574b;border-radius:14px;padding:20px;margin:18px 0}.warn{border-color:#b39248;color:#ffe3a0}.muted{color:#9dbbb1}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:10px;border-bottom:1px solid #28483e;white-space:nowrap}th{color:#94dbbf}.scroll{overflow:auto}details{margin:12px 0}summary{cursor:pointer;color:#83ffd0}pre{overflow:auto;font-size:13px}svg{width:100%;height:auto}.pill{display:inline-block;border:1px solid #917d46;border-radius:16px;padding:4px 12px;color:#ffe5a5}footer{margin-top:40px;color:#9dbbb1}</style><main>',
  '<span class="pill">Research only · No live changes</span><h1>US100 CPI / NFP / FOMC reversion</h1>',
  '<p>1% of current equity targeted at the initial stop, $10,000 starting balance. US100 is the Exness USTEC CFD, not NQ futures. Stops can lose more than the intended budget due to slippage or gaps.</p>',
  '<section class="warn"><h2 style="margin-top:0">Exploratory optimisation — not approved for live trading</h2><p>'+esc(r.CONFIG['holdout_label'])+'</p><p>Development uses 2020–2023; 2024 validates the finalists. Settings were frozen before running 2025 onward. The global two-year OOS policy is unchanged; this study uses your explicit date split.</p><p>Requested end: 8 October 2026 exclusive. Actual price archive ends '+esc(m['actual_last_quote_utc'])+'. No missing-date trades or prices were fabricated.</p><p>Generated tick fallback before 2026 and frequent zero-spread 2026 news quotes prevent a reliable execution-quality pass. This is a price-pattern reversion model, not a verified market-consensus “priced-in” signal.</p></section>',
  '<h2>Baseline versus frozen candidate</h2>',metrics_table(s),'<p class="muted">Each period is a separate native backtest restarting at $10,000. Daily Sharpe uses observed UTC calendar-day end equity, √365 and zero risk-free rate. MT5 trade-level Sharpe is not substituted.</p>',
  '<h2>Equity: 2025 onward</h2>',chart([('Baseline',raw),('Candidate',chosen)]),
  '<h2>Raw gates before optimisation</h2><p>Independent cached-M1 checks matched all 158 available development fair prices and ATR readings. Of 159 scheduled 2020–2024 releases, the 10 April 2020 CPI fell on Good Friday and had no tradable USTEC event window; it remains accounted for as a no-trade, not fabricated data.</p>',
  table(['Window','Trades','PF','Return','Raw PF≥1.15 / ≥30 trades / positive net'],[['2022–2024 (3y)' if x['stage']=='raw-3y' else '2020–2024 (5y)',x['metrics']['trades'],f(x['metrics']['pf']),pct(x['metrics']['return_pct']),'PASS' if x['passed'] else 'FAIL — exploratory continuation authorised'] for x in g['rows']]),
  '<h2>Frozen settings and rules</h2><p>Pre-news fair price = the last completed M1 close before the scheduled release. Pre-news volatility = ATR(14) on completed M5 candles. Measure the first post-release M1 close against that fair price. Enter in the reversal direction after a completed M1 displacement candle and/or a causally confirmed three-bar structure break. One trade per release, no trailing or partial exits.</p>',
  table(['Setting','Raw baseline','Frozen candidate'],[[esc(k),esc(freeze['locked']['baseline'][k]),esc(value)] for k,value in freeze['locked']['parameters'].items()]),
  '<p class="muted">signal_mode: 0 = either displacement or structure; 1 = displacement only; 2 = structure only. Target fraction 1 reaches the original fair price; lower values exit partway back. Hold deadline is minutes after fill, additionally capped at 90 minutes after the release. Lots floor to broker step; undersized minimum lots skip rather than exceed planned risk.</p>',
  '<h2>Annual contributions</h2>']
 annual=[]
 for block,br,cr in [('2020–2024 in-sample',s['raw-5y-0'],s['in-sample-selected-0']),('2025+ retrospective holdout',raw,chosen)]:
  years=sorted(set(br['annual_contributions'])|set(cr['annual_contributions']))
  for year in years:
   for label,row in [('Baseline',br),('Candidate',cr)]:
    z=row['annual_contributions'][year]
    annual.append([esc(block),year,label,z['trades'],f(z['win_rate_pct'])+'%',f(z['pf']),f(z['net']),pct(z['return_contribution_pct'])])
 out.append(table(['Test','Year','Version','Trades','Win rate','PF','Net USD','Contribution'],annual))
 out.append('<p class="muted">Annual rows are contributions within their continuously compounded in-sample or holdout backtest, divided by its original $10,000; not standalone yearly percentage returns.</p><h2>Event-type breakdown — diagnostics only</h2>')
 out.append(table(['Event','Version','Trades','Win rate','PF','Net USD'],[[kind,label,z['trades'],f(z['win_rate_pct'])+'%',f(z['pf']),f(z['net'])] for kind in ['CPI','NFP','FOMC'] for label,row in [('Baseline',raw),('Candidate',chosen)] for z in [row['events'][kind]]]))
 out.append('<p class="muted">All three release types remained enabled during selection. This table was not used to choose an OOS event filter.</p><h2>Monte Carlo and uncertainty — frozen holdout</h2>')
 out.append(table(['Metric','5th percentile','Median','95th percentile'],[[label]+[f(x) for x in mc[key]] for label,key in [('Return %','return_p05_p50_p95'),('Profit factor','pf_p05_p50_p95'),('Closed-balance DD %','closed_dd_p05_p50_p95')]]))
 out.append('<p>10,000 paths, circular blocks of five. Positive-return probability '+f(mc['probability_profit_pct'])+'%; initial-balance 10% loss-breach proxy '+f(mc['total_10pct_breach_proxy_pct'])+'%. Win-rate 95% interval '+f(m['win_rate_wilson95_pct'][0])+'–'+f(m['win_rate_wilson95_pct'][1])+'%. Deflated Sharpe '+f(chosen['sharpe']['deflated_sharpe_pct'])+'%, accounting approximately for '+str(v['dsr_tested_configurations'])+' tested configurations.</p><p class="muted">'+esc(mc['scope'])+' Resampling the small historical sample is not new market evidence. DSR does not correct every earlier asset/model/researcher choice.</p><h2>Execution sensitivity</h2>')
 out.append(table(['Delay','Trades','Win rate','PF','Return','Floating DD'],[[label,z['trades'],f(z['win_rate_pct'])+'%',f(z['pf']),pct(z['return_pct']),f(z['equity_dd'])+'%'] for label,key in [('150 ms','holdout-1'),('500 ms','delay-500-0'),('1,000 ms','delay-1000-0')] for z in [s[key]['metrics']]]))
 cost=chosen['cost_stress']
 out.append('<p>2026 entry quotes: '+str(cost['entry_quotes_2026'])+'; zero-spread quotes: '+str(cost['zero_spread_observations'])+'; strictly positive quotes: '+str(cost['positive_observations'])+'. '+esc(cost['stress_scope'])+'</p>')
 out.append('<h3>Tick-model diagnostic</h3>'+table(['Model','Version','Trades','Win rate','PF','Return'],[[model,label,z['trades'],f(z['win_rate_pct'])+'%',f(z['pf']),pct(z['return_pct'])] for model,base in [('Available real ticks + fallback','holdout'),('Generated every tick','generated-tick-diagnostic')] for label,i in [('Baseline',0),('Candidate',1)] for z in [s[base+'-'+str(i)]['metrics']]]))
 out.append('<p class="muted">Settings were not changed after seeing this diagnostic. News exits are sensitive to intraminute tick paths; generated ticks cannot resolve that uncertainty.</p>')
 if 'extra_spread_pf' in cost:
  out.append('<p>Extra positive-quote median spread '+f(cost['positive_quote_median_usd_per_lot'])+' USD/lot → indicative return '+pct(cost['extra_spread_return_pct'])+', PF '+f(cost['extra_spread_pf'])+', win rate '+f(cost['extra_spread_win_rate_pct'])+'%.</p>')
 out.append('<h2>Validation gates — candidate</h2>'+table(['Gate','Result'],[[esc(k),'PASS' if value else 'FAIL'] for k,value in chosen['gates'].items()]))
 out.append('<p class="warn">Verdict: '+esc(chosen['verdict'])+'. Nothing was installed, promoted, added to BATs, published or pushed.</p><h2>Development search and 2024 finalists</h2><p>'+str(v['unique_searched_configurations'])+' distinct settings tested. One-factor stages with beam width two; local stop/impulse/hold neighbours; median plateau score and 2024 finalist score. No promise this is a global optimum.</p>')
 out.append(table(['Finalist','2024 trades','2024 PF','2024 return','Selection score'],[[esc(x['parameters']),x['validation_metrics']['trades'],f(x['validation_metrics']['pf']),pct(x['validation_metrics']['return_pct']),f(x['selection_score'])] for x in sel['validation_ranked']]))
 out.append('<details><summary>All development trials</summary>'+table(['Stage','Settings','Trades','PF','Win rate','Return','Floating DD'],[[esc(x['stage']),esc(x['parameters']),x['metrics']['trades'],f(x['metrics']['pf']),f(x['metrics']['win_rate_pct'])+'%',pct(x['metrics']['return_pct']),f(x['metrics']['equity_dd'])+'%'] for x in r.load(R/'trials.json')])+'</details>')
 for label,key in [('Candidate holdout trades','holdout-1'),('Baseline holdout trades','holdout-0')]:
  out.append('<details><summary>'+label+'</summary>'+table(['Release NY','Side','Entry NY','Exit NY','Lots','Entry','Exit','SL','TP','Exit reason','Net USD','R','Minutes'],[[esc(t['event_time_ny'])+' '+esc(t['event']),esc(t['side']),esc(t['open_time_ny']),esc(t['close_time_ny']),f(t['volume']),f(t['open_price']),f(t['close_price']),f(t['initial_sl']),f(t['initial_tp']),esc(t['exit_label']),f(t['net_profit']),f(t['realised_r']),f(t['hold_minutes'])] for t in s[key]['trades']])+'</details>')
 out.append('<details><summary>Every scheduled holdout release, including no-trades</summary>'+table(['Release NY','Type','Disposition','Trades','Net USD'],[[esc(x['release_ny']),esc(x['kind']),esc(x['disposition']),x['trades'],f(x['net'])] for x in chosen['event_dispositions']])+'</details>')
 out.append('<h2>Evidence and downloads</h2><p><a href="SUMMARY.json">Full results</a> · <a href="FROZEN.json">Selection freeze</a> · <a href="VERIFICATION.json">Verification</a> · <a href="calendar.json">214 official releases</a> · <a href="SELECTION.json">Selection evidence</a> · <a href="Frozen Research EA/Research News Reversion.mq5">Tester-only EA source</a> · <a href="Frozen Research EA/Research News Reversion.set">1% research set</a></p><p>Calendar sources: <a href="https://www.bls.gov/schedule/2020/home.htm">BLS 2020</a>, <a href="https://www.bls.gov/schedule/2025/home.htm">BLS 2025</a>, and linked official Fed statements in the calendar receipts. Unscheduled 2020 emergency interventions are excluded rather than pretending they were scheduled ahead of time.</p><footer>'+str(v['checks'])+' ledger, timing, sizing, signal and calendar checks passed. Native source, binary and report hashes retained per batch. Verification workflow: tokenmaxxer skill. Browser rendering was not verified; local file access is restricted in this session.</footer></main></html>')
 path=R/'Results.html';path.write_text(''.join(out),encoding='utf-8')
 export=R/'Frozen Research EA';export.mkdir(exist_ok=True)
 for source,name in [('OrbSearch.mq5','Research News Reversion.mq5'),('OrbSearch.ex5','Research News Reversion.ex5')]:
  shutil.copy2(R/'native/in-sample-selected'/source,export/name)
 (export/'Research News Reversion.set').write_text('InpCase=0\nInpTag=frozen-news-research\nInpVerbose=false\nInpRiskPct=1\n',encoding='utf-8')
 r.save(export/'manifest.json',dict(source_sha256=r.sha(export/'Research News Reversion.mq5'),binary_sha256=r.sha(export/'Research News Reversion.ex5'),
  set_sha256=r.sha(export/'Research News Reversion.set'),parameters=freeze['locked']['parameters'],tester_only=True,live_supported=False))
 print(str(path),flush=True)

if __name__=='__main__':main()
