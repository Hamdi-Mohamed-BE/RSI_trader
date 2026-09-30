"""Generate the user report exclusively from saved evidence."""
from pathlib import Path
import json
from datetime import datetime,timezone
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def fmt(x,n=2):return '—' if x is None else f'{x:,.{n}f}'
NAMES={'orb-long-1r':'ORB30 long 1R','orb-long-2r':'ORB30 long 2R','orb-both-2r':'ORB30 both 2R',
 'orb-control':'10:00 long control','vwap-raw':'VWAP / fixed 1 lot','vwap-atr':'VWAP + M5 ATR stop',
 'twap-atr':'TWAP + M5 ATR control','overnight-raw':'Overnight / fixed 1 lot','overnight-atr':'Overnight + D1 ATR stop',
 'day-raw':'Day long / fixed 1 lot control','day-atr':'Day long + D1 ATR control'}
def name(s):return s.replace('USTEC','US100')
def main():
 raw=read(ROOT/'RAW_RESULTS.json');prop=read(ROOT/'PROP_RESULTS.json');full=read(ROOT/'PROP_YEAR.json');sel=read(ROOT/'SELECTION.json');audit=read(ROOT/'AUDIT.json')
 invalid=[read(p) for p in sorted((ROOT/'native').glob('*/invalid.json'))]
 valid=[r for r in raw if r['window']!='smoke'];year=[r for r in valid if r['model']==4 and r['window']=='1y']
 selected=[s for s in sel if s['screen_pass']]
 passed=[]
 for s in selected:
  cfg=next(v for v in read(ROOT/'run-config.json')['variants'] if v['name']==s['variant'])
  rs=[r for r in valid if r['symbol']==s['symbol'] and r['variant']==s['variant'] and r['model']==4 and r['window'] in ('3y','5y')]
  controls={r['window']:r for r in valid if r['symbol']==s['symbol'] and r['variant']==cfg['control'] and r['model']==4 and r['window'] in ('3y','5y')}
  okay=len(rs)==2 and all(r['stats']['net']>0 and (r['stats']['pf'] or 0)>=1.15 and r['stats']['trades']>=30 and r['stats']['net']>controls[r['window']]['stats']['net'] for r in rs)
  if okay:passed.append(name(s['symbol'])+' '+NAMES[s['variant']])
 lines=['# Conte interview ideas — native tests and prop scenarios',
 '','Built and tested as isolated research. No live EA, installer, website or account was changed.',
 '',
 '## Decision',
 '',
 ('Raw gates passed: '+', '.join(passed)+'. These are research candidates only; no untouched holdout or portfolio-integration validation has been completed.') if passed else 'No candidate has earned promotion through the frozen raw gates. Do not add this basket to the funded system on these results.',
 '',
 'PEAD is **not tested**: individual-stock point-in-time earnings/consensus and historical universe data are missing. The three index strategy families were built and tested; that is not a four-paper replication.',
 '',
 f'{len(invalid)} long-history attempts are data/execution-blocked and excluded from performance statistics. A blocked test is not a pass or a measured strategy loss. See the data-blocked table below.',
 '',
 '## Read this before the numbers',
 '',
 '- Periods end 2026-09-27 (exclusive). Last year starts 2025-09-27; last six months 2026-03-27. Last trading date may be earlier.',
 '- Protected rows: $10,000 native starting balance and fixed $100 intended initial hard-stop risk, no compounding. Actual fill risk/cost can differ. These are NOT the guarded prop-account results.',
 '- Unstopped rows: fixed **1 CFD lot**, NOT 1% risk. One US100 lot is not one NQ futures contract. Never compare their percentage returns as equal-risk strategies.',
 '- The source broker has real ticks only from 2026-01-01. Older data in Model 4 is generated ticks; Model 1 is generated-tick screening. Neither the year nor the five-year test is all real tick data.',
 '- Source execution quotes often show zero spread. Real-tick availability is NOT proof of representative prop-firm costs. Order-log quote diagnostics are recorded below; swap specifications are tester-time metadata, not independently verified historical financing.',
 '- Original 16:00 instructions execute at the earlier of **15:59 New York or one minute before the broker session ends** (15:54 on winter Fridays in this source). VWAP is **tick-volume VWAP**, not consolidated ETF/futures trade-volume VWAP.',
 '- ORB uses completed M5 breakout closes of the 09:30–10:00 range, flat 15:30. VWAP reverses on closed M1 signals; protected stop = 2 x completed M5 ATR14. Overnight long at the broker-aware closing cutoff, exit next NYSE open; protected stop = 1 x completed UTC D1 ATR14.',
 '- Latest year is repeatedly used research history, not a newly untouched holdout. All 22 configurations and controls were declared before results; no full parameter optimization was run.',
 '- PF is calculated from NET complete trades including commission/swap, not separate native report deal components. Trades/day means per weekday including zero-trade weekdays; holidays reduce actual session count.',
 '',
 '## Last-year protected strategies — comparable $100 intended stop risk',
 '',
 '| Asset | Strategy | Return | PF | Win | Eq DD | Trades | /mo | /weekday | W/L max |',
 '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 mainvariants=['orb-long-1r','orb-long-2r','orb-both-2r','vwap-atr','overnight-atr']
 def row(r):
  z=r['stats']
  label=NAMES[r['variant']]+(' †' if z['capital_limited'] or r['flags']['margin_call'] else '')
  return f"| {name(r['symbol'])} | {label} | {z['return_pct']:+.2f}% | {fmt(z['pf'])} | {fmt(z['win_rate'])}% | {fmt(z['equity_dd_pct'])}% | {z['trades']} | {z['per_month']:.1f} | {z['per_weekday']:.2f} | {z['max_win_streak']}/{z['max_loss_streak']} |"
 for r in year:
  if r['variant'] in mainvariants:lines.append(row(r))
 lines+=['','![Native closed-balance paths](balance_curves.png)','','The curves show closed balance at full native research risk, not the prop overlay and not intra-trade equity. See the tables for native equity drawdown.','','## Controls and unstopped benchmarks','','Same columns; raw one-lot rows do not have the same risk budget.','','| Asset | Strategy | Return | PF | Win | Eq DD | Trades | /mo | /weekday | W/L max |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for r in year:
  if r['variant'] not in mainvariants:lines.append(row(r))
 lines+=['','### Execution-cost data checks','','Order-log quote samples can be duplicated and are not all ticks; these diagnose source-feed limitations, not a market spread estimate. No zero spread is assumed for a future prop account.','','| Asset | Protected VWAP real-tick share | Logged quotes with zero spread | Median logged spread (index points) |','|---|---|---:|---:|']
 for r in year:
  if r['variant']=='vwap-atr':
   q=r['stats']['logged_quote_spread'];lines.append(f"| {name(r['symbol'])} | {r['stats']['tick_quality']} | {fmt(q['zero_pct'])}% | {fmt(q['median_points'])} |")
 lines+=['','### Where the money went — last-year protected VWAP and overnight','','Before-fee/swap P&L below still includes the native spread and execution outcomes. It is not frictionless theoretical profit.','','| Asset | Strategy | Before commission/swap | Commission + fees | Swap | Net |','|---|---|---:|---:|---:|---:|']
 for r in year:
  if r['variant'] in ('vwap-atr','overnight-atr'):
   z=r['stats'];lines.append(f"| {name(r['symbol'])} | {NAMES[r['variant']]} | ${fmt(z['net']-z['commission']-z['swap'])} | ${fmt(z['commission'])} | ${fmt(z['swap'])} | ${fmt(z['net'])} |")
 lines+=['','## Six-month native results','','All configured variants, not just the best.','','| Asset | Strategy | Return | PF | Win | Eq DD | Trades | /mo | /weekday | W/L max |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for r in valid:
  if r['window']=='6m' and r['model']==4:lines.append(row(r))
 for model,title in [(1,'Long-history generated-tick screens'),(4,'Long-history Model 4 confirmations')]:
  lines+=['','## '+title,'','These overlapping windows are robustness screens, not independent holdout tests. Failed screens were not optimized.']
  if model==4 and not selected:
   lines+=['','No candidate passed both long-history screening windows, so the frozen pipeline did not advance any candidate to long-history Model 4 confirmation. Annual and six-month Model 4 tests were still completed for all 22 variants and controls.']
  for w in ('3y','5y'):
   records=[r for r in valid if r['model']==model and r['window']==w]
   if not records:continue
   lines+=['','### '+w,'','| Asset | Strategy | Return | PF | Win | Eq DD | Trades | /mo | /weekday | W/L max |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
   lines.extend(row(r) for r in records)
 limited=[r for r in valid if r['stats']['capital_limited'] or r['flags']['margin_call']]
 if limited:
  lines+=['','## Capital-limited native failures (†)','','The strategy was kept at the frozen $100 risk target, not topped up after losses. Closed balance fell to $100 or less and later signals were skipped, or a native margin stop-out occurred (verified against the exit-deal reason). These are failed account paths with censored trade samples, NOT unlimited-capital full-window edge estimates. They remain visible rather than being silently discarded. No capital-censored native year is used as a prop simulation input.','','| Native case | Minimum closed balance | Skipped signals | Last native close |','|---|---:|---:|---|']
  for r in limited:
   z=r['stats'];lines.append(f"| {name(r['tag'])} | ${fmt(z['minimum_closed_balance'])} | {z['native_skipped_signals']} | {z['last_closed_utc']} |")
 lines+=['','## Raw gate decisions','','3y AND 5y: positive net, net-trade PF >=1.15, >=30 trades and better net than the stated control. Control limitations are disclosed in RULES.md.','','| Asset | Candidate | Model 1 screen |','|---|---|---|']
 for s in sel:lines.append(f"| {name(s['symbol'])} | {NAMES[s['variant']]} | {'Advance to Model 4' if s['screen_pass'] else 'Data blocked — not validated' if s.get('evidence_status')=='blocked' else 'Fail — stop'} |")
 if invalid:
  lines+=['','## Data-blocked long-history attempts','','Native Market Closed errors mean the prescribed closing-time rule was not executed. These runs are NOT valid backtests and their returns are intentionally excluded. The first observed USTEC case was 2024-01-23: the archived M1 export has 20:58 UTC, no 20:59 bar, then quotes during the currently declared session break. The next close attempt at 21:00 was rejected. We do not shift the rules again or optimise around this source-history problem. Failed reports, journals and traces are retained as invalid-* artifacts.','','| Case | Market Closed log lines* | Status |','|---|---:|---|']
  for r in invalid:lines.append(f"| {name(r['tag'])} | {r['flags']['market_closed']} | Excluded; needs valid execution data |")
  lines+=['','*Log lines may duplicate terminal/agent messages and are not unique trade counts.']
 lines+=['','## Prop-account results — standalone, conditional scenarios','',
 'These are **500 block-bootstrap paths per scenario**, not measured live pass odds. Whole 28-day entry blocks preserve clustered results, non-trading days and full overnight trades. All variants are tested separately. Complete rules, cost assumptions and limitations are in PROP_PROTOCOL.md.',
 '',
 'FTMO $10K 2-Step Swing: 10%/5% phase targets, four entry days per phase, 5% daily equity loss and 10% static loss. FundedNext $5K Stellar Instant: **funded from day zero**, 6% balance-trailing loss floor, conditional EA addon and payout rules. [FTMO objectives](https://ftmo.com/en/trading-objectives/), [Instant loss rules](https://help.fundednext.com/en/articles/11641163-what-are-the-daily-loss-limit-and-the-maximum-loss-limit-for-the-stellar-instant-accounts).',
 '',
 'FTMO caps: 0.25%/0.50%. Instant caps: 0.15%/0.25%, further limited to 5% of available buffered drawdown room. Both use a 30%-of-balance margin cap and source minimum lots. **Actual risk can be far smaller than the selected percentage.**',
 '',
 'Instant leverage is conditional: its [product page](https://fundednext.com/cfds/stellar-instant) lists index leverage 1:10 but its [dedicated help article](https://help.fundednext.com/en/articles/11641369-what-is-the-leverage-provided-in-the-stellar-instant-accounts) lists 1:5. These scenarios retain the stricter predeclared **1:5**. Confirm the actual account specification before relying on a payout projection.',
 '',
 'Request day is calendar days from simulation start, conditional on reaching eligibility within the horizon. It is not average time for every account. Phase-2 day is cumulative from start. No request within the window does not necessarily mean an account breach. Admin delays are assumptions; payment/KYC/review delays and purchase fees are excluded.',
 '',
 'Instant retains a 3%-of-initial-capital buffer above its trailing floor when requesting a payout. Reference deductions cover only 29 locally available news timestamps; this is not a full compliant news-calendar simulation. Stress adds hypothetical slippage, financing and profit deductions. Quick Strike failures are shown separately from drawdown breaches.']
 profiles=['FTMO 10K 0.50% cap / 30% margin','Instant 5K 0.25% cap / 30% margin']
 for cost in ('reference','stress'):
  lines+=['','### 180-day '+cost+' scenarios','','| Strategy | Account/cap | Phase 1 | Both phases | Request | Request day* | DD breach | Quick flag | No trades | First reward* |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
  for p in prop:
   if p['kind']!='bootstrap' or p['days']!=180 or p['cost']!=cost or p['profile'] not in profiles:continue
   z=p['stats'];ft=p['profile'].startswith('FTMO')
   reward='—' if z['median_first_reward'] is None else '$'+fmt(z['median_first_reward'])
   lines.append(f"| {name(p['variant'])} | {'FTMO .50%' if ft else 'Instant .25%'} | {fmt(z['phase1']['pct'],1)+'%' if ft else 'n/a'} | {fmt(z['phase2']['pct'],1)+'%' if ft else 'n/a'} | {z['first_request']['count']}/500 ({z['first_request']['pct']:.1f}%) | {fmt(z['first_request']['median_days'],1)} | {z['drawdown_breach']['count']}/500 | {z['quick_failure']['count']}/500 | {z['no_trades']}/500 | {reward} |")
 lines+=['','*Conditional medians among qualifying paths. A simulated reward is net of the assumed split, not approved/received cash. A shorter stressed median can mean that only a few fast paths qualified, not that stress improved the strategy.','','## All 2/4/6-month scenarios','','Reference bootstrap; conservative and higher caps both shown. The raw JSON also includes cost-stress scenarios and actual weekly rolling starts.','','| Strategy | Profile | Days | P1 % / day | Both % / day | Funded % / day | P2 duration* | Request % / day | DD breach % | Unresolved % | Mean risk $ |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
 for p in prop:
  if p['kind']!='bootstrap' or p['cost']!='reference':continue
  z=p['stats']
  def pair(f):return f"{z[f]['pct']:.1f}% / {fmt(z[f]['median_days'],1)}"
  ft=p['profile'].startswith('FTMO')
  lines.append(f"| {name(p['variant'])} | {p['profile']} | {p['days']} | {pair('phase1') if ft else 'n/a'} | {pair('phase2') if ft else 'n/a'} | {pair('funded')} | {fmt(z['phase2_duration_median_days'],1)} | {pair('first_request')} | {z['drawdown_breach']['pct']:.1f}% | {z['no_request_no_failure_pct']:.1f}% | {z['median_mean_initial_risk']:.2f} |")
 lines+=['','## Actual chronological last-year account replays','','One historical path per account, not a probability. Reference costs and the higher caps; all four profiles and both costs remain in PROP_YEAR.json. Days are calendar days from 2025-09-27.','',
 '| Strategy | Account | P1 day | P2 day | First request day | Requests | Total modelled reward | Trades taken | Rejected: minimum lot |',
 '|---|---|---:|---:|---:|---:|---:|---:|---:|']
 start=datetime(2025,9,27,tzinfo=timezone.utc).timestamp()
 for p in full:
  if p['cost']!='reference' or p['profile'] not in profiles:continue
  z=p['state'];ft=p['profile'].startswith('FTMO')
  def day(field):return fmt((z[field]-start)/86400,1) if z[field]>=0 else '—'
  lines.append(f"| {name(p['variant'])} | {'FTMO .50%' if ft else 'Instant .25%'} | {day('phase1_time') if ft else 'n/a'} | {day('phase2_time') if ft else 'n/a'} | {day('first_request_time')} | {int(z['payouts'])} | ${fmt(z['total_cash'])} | {int(z['closed_ideas'])} | {p['rejected']['below_minimum_lot']} |")
 lines+=['','## Evidence and limitations','',
 f"- {len(valid)} valid non-smoke native cases, {len(invalid)} explicitly blocked historical attempts, plus 6 final-build smoke cases. Initial failed-build outputs retained separately.",
 f"- {audit['checks']:,} automated evidence checks; passed={audit['passed']}. Unit tests cover 24 accounting/time/risk/execution edge cases.",
 '- Native bid/ask, commission and swap are source-broker costs. Prop symbols, financing, holidays, routing, minimum lots and fills may differ.',
 '- Older overnight tests can skip scheduled entries when the required minute has no quote, even with no order rejection. Zero error flags do not certify complete historical session coverage.',
 '- At the test boundary, native tester liquidation of an overnight trade is included in native results and identified in the deal ledger; it is removed from prop-path inputs.',
 '- No-stop variants are benchmark research only. Their price-based exit does not define a maximum dollar loss.',
 '- Failed candidates do not become deployable because a resampled path happened to earn a payout.',
 '- Offline position sizing rescales recorded fills and uses realised fill-to-stop unit risk; it is not a new native test of each account and cannot reproduce pre-fill sizing or size-dependent execution exactly.',
 '- Entry guards may halt an account near a risk buffer without a formal breach. No breach is not the same as success; unresolved and zero-trade paths are reported.',
 '- Portfolio diversification, existing-EA overlap, target-broker validation, complete news constraints, paper/forward testing and untouched holdout remain before deployment.',
 '',
 '## Files and source checks','',
 '- RULES.md: frozen mechanical definitions and broker-session execution amendments.',
 '- RESEARCH_NOTES.md: findings versus interview claims, primary-source links and access limits.',
 '- RAW_RESULTS.json: all native net-trade statistics; native/ contains compressed reports, deals, floating traces and run manifests.',
 '- PROP_RESULTS.json: every risk/cost/horizon/rolling/bootstrap scenario; PROP_YEAR.json: chronological full-year lifecycle logs.',
 '- PROP_PROTOCOL.md: account rules, guards, costs, bootstrapping and timing assumptions.',
 '- AUDIT.json, BUILD.json and PROP_MANIFEST.json: checks and hashes.',
 '',
 'No profits, pass rates or payouts are guaranteed. This is research evidence, not a recommendation to buy or deploy a prop account.']
 (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 # Full net-trade totals, not native partial-deal charts.
 fig,axes=plt.subplots(2,1,figsize=(12,8),sharex=True)
 colors=['#2563eb','#16a34a','#d97706','#dc2626','#7c3aed']
 for ax,symbol in zip(axes,('USTEC','US500')):
  for variant,color in zip(mainvariants,colors):
   ideas=read(ROOT/'native'/f'{symbol}-{variant}-1y-m4/ideas.json')
   times=[datetime(2025,9,27,tzinfo=timezone.utc)]+[datetime.fromtimestamp(x['close'],timezone.utc) for x in ideas]
   y=np.r_[10000,10000+np.cumsum([x['net'] for x in ideas])]
   ax.step(times,y,where='post',label=NAMES[variant],color=color,lw=1.2)
  ax.axhline(10000,color='#999999',lw=.6);ax.set_title(name(symbol));ax.set_ylabel('Closed balance ($)');ax.grid(alpha=.15);ax.legend(ncol=3,fontsize=8)
 fig.suptitle('Native research: USD 100 stop-risk target / USD 10,000 account — no prop guards',fontsize=12)
 fig.tight_layout();fig.savefig(ROOT/'balance_curves.png',dpi=140);plt.close(fig)
 (ROOT/'DECISION.json').write_text(json.dumps(dict(raw_gate_passed=passed,source_cases=len(valid),deployment_approved=False),indent=2),encoding='utf-8')
 print('REPORT COMPLETE',passed)
if __name__=='__main__':main()
