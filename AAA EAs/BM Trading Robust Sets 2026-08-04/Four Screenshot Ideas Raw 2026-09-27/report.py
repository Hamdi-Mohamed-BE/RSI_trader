"""Final net-of-cost tables and balance-path comparison from audited native runs."""
from pathlib import Path
from datetime import datetime,timedelta
import json,gzip,hashlib,statistics
import audit
ROOT=Path(__file__).resolve().parent
def num(x,d=2):return 'n/a' if x is None else f'{x:,.{d}f}'
def usd(x):return f'${x:+,.2f}'
def table(lines,heads,rows):
 lines+=['','| '+' | '.join(heads)+' |','|'+'|'.join('---' for _ in heads)+'|']
 lines+=['| '+' | '.join(str(v) for v in row)+' |' for row in rows];lines+=['']
def main():
 cfg=audit.load(ROOT/'run-config.json');build=audit.load(ROOT/'BUILD.json');records=[]
 for c in cfg['cases']:
  folder=ROOT/'native'/c['id'];m=audit.load(folder/'run.json');a=audit.audit(folder);trades=audit.load(folder/'trades.json')
  assert m['build']==build and a['ok']
  s=a['net'];balance=10000.;months={};month=datetime(2025,9,1)
  while month<datetime(2026,10,1):
   k=month.strftime('%Y-%m');v=s['monthly'].get(k,dict(trades=0,net_usd=0,wins=0,win_rate_pct=None))
   months[k]=dict(v,start_balance=balance,return_pct=100*v['net_usd']/balance if balance else None,end_balance=balance+v['net_usd'])
   balance+=v['net_usd'];month=(month.replace(day=28)+timedelta(days=4)).replace(day=1)
  assert abs(balance-m['metrics']['final_balance'])<.11
  enriched=[]
  for t in trades:
   op=audit.stamp(t['open_time']);cl=audit.stamp(t['close_time']);enriched.append(dict(t,holding_hours=(cl-op).total_seconds()/3600))
  records.append(dict(case=c,metrics=m['metrics'],net=s,months=months,audit=a,flags=m['flags'],spec=m['symbol_spec'],summary=m['summary'],real_ticks=m['real_ticks'],trades=enriched,
   best_trade=max((t['net_profit'] for t in trades),default=None),worst_trade=min((t['net_profit'] for t in trades),default=None),
   avg_win=statistics.mean([t['net_profit'] for t in trades if t['net_profit']>0]) if any(t['net_profit']>0 for t in trades) else None,
   avg_loss=statistics.mean([t['net_profit'] for t in trades if t['net_profit']<0]) if any(t['net_profit']<0 for t in trades) else None,
   report_sha=m['report_sha']))
 mainrows=records[:4];controls=records[4:]
 lines=['# Four screenshot strategies — raw last-year results','',
 'Completed September 27, 2026. Research only. No strategy optimization, portfolio changes, FTMO simulation, production EA/BAT/website edits or Git push.', '',
 '## Interpretation and sizing','',
 '- Test period: September 27, 2025 through September 27, 2026 exclusive. Separate $10,000 USD accounts; Exness isolated native MT5 tester, Model 4, 150ms simulated execution delay, original bid/ask prices, commission and swaps.',
 '- USDJPY morning breakout and US100 ORB target 1% CURRENT equity per stop, lots rounded UP using the established raw-study helper. This is not a hard loss cap; costs, gaps and rounding can exceed 1%.',
 '- US30 Turnaround Tuesday and US100 daily long have NO STOP LOSS, as in the screenshots. Both use fixed initial $10,000 notional market exposure, lots rounded down (approximately 1x initial capital). Their returns/DD cannot be compared as if all four have the same risk budget. A much larger position would change their account risk materially.',
 '- All broker-time rules use a synthetic GMT+2/+3 clock, defined as New York +7 hours with US DST, because Exness history is UTC. The source broker and its exact DST convention are unknown. The ORB uses New York time directly.',
 '- Win rate, PF and streaks below use net completed-trade results AFTER commission/swap. Drawdown is native maximum relative floating-equity DD, not the closed-balance curve. Trades/day uses all 260 weekdays, including no-trade days; monthly frequency uses elapsed calendar time.',
 '- Exactly four raw definitions, four predeclared controls and four short smoke runs. No parameters were searched. One year is descriptive and does not establish the 3y/5y pipeline gate, robustness, FTMO compliance or payout probability.', '',
 '**Broker-constrained reproduction, not exact source-broker parity:** market-closed responses delayed 93 daily-long US100 exits, 13 US100 ORB exits and five filtered US30 exits in this run. Some are holidays; winter timing also depends on the native tester session specification. These realized native paths are retained, but the intended-clock versions require source-broker session validation before their edge can be judged reliably.', '',
 '## Primary strategies — side by side']
 table(lines,['Strategy','Trades','/month','/weekday','Net USD','Return','Net win','Net PF','Equity DD','Balance DD','Max W/L'],[
  [r['case']['label'],r['net']['trades'],num(r['net']['trades_per_month'],1),num(r['net']['trades_per_weekday']),usd(r['net']['net_usd']),num(r['net']['return_pct'])+'%',num(r['net']['win_rate_pct'])+'%',num(r['net']['profit_factor']),num(r['metrics']['max_equity_dd_pct'])+'%',num(r['metrics']['max_balance_dd_pct'])+'%',f"{r['net']['max_win_streak']} / {r['net']['max_loss_streak']}"] for r in mainrows])
 lines+=['## Reading the result','',
 f"- USDJPY has a positive annual net result, but {usd(mainrows[0]['months']['2026-09']['net_usd'])} of its {usd(mainrows[0]['net']['net_usd'])} profit came from the final partial September. It lost money in each of January–June. That concentration plus 32.21% equity DD makes the headline return misleading if viewed alone.",
 '- US30 has the strongest raw win-rate/PF figures, but only 16 trades, with 11 consecutive wins. March contributed $866.41 of the $1,117.79 annual net profit. No stop and limited sample size mean this is a research lead, not a validated low-risk strategy.',
 '- US100 daily long has a modest net PF and substantial scheduled-exit uncertainty. Its buy-and-hold control returned more with higher equity DD; that comparison has different overnight exposure.',
 '- The requested US100 ORB lost money and underperformed its predeclared timed-entry control this year. Do not promote or optimize it solely to rescue this sample.', '',
 '## What was actually tested','',
 '1. **USDJPY morning breakout:** 03:00–06:00 broker-time range; at 06:00 pending stops at high/low; SL opposite edge, no TP; first fill cancels the other order; close/cancel 18:00; one trade/day.',
 '2. **US30 Turnaround Tuesday:** Monday 01:05 broker-time buy if current bid is below the mean of 25 completed synthetic broker-day closes; no SL/TP; Tuesday 23:50 exit.',
 '3. **US100 daily long:** every broker weekday 01:05 buy; no SL/TP/filter; 23:50 exit.',
 '4. **US100 NY ORB:** 09:30–09:45 range; completed M5 close outside it, entries 09:50–15:00; stop opposite edge plus 0.25 ATR(14,M5); target TWO RANGE HEIGHTS from the breakout boundary, not 2R from entry; one trade/day; close 15:55.', '',
 'Broker-invalid orders are skipped rather than changing entry/stop/target levels. A scheduled close cannot execute during a closed market; the code retries on the next available minute. Late closures are retained below, not erased or moved earlier.', '',
 '## Streaks, trade sizes and realized trade distribution']
 table(lines,['Strategy','Avg winning streak','Avg losing streak','Avg win USD','Avg loss USD','Best trade','Worst trade','Largest initial SL risk','Notional range (no-stop)'],[
  [r['case']['label'],num(r['net']['avg_win_streak']),num(r['net']['avg_loss_streak']),num(r['avg_win']),num(r['avg_loss']),num(r['best_trade']),num(r['worst_trade']),num(r['audit']['max_initial_risk_pct'],3)+'%' if r['audit']['max_initial_risk_pct'] is not None else 'Undefined: no SL',f"{num(r['audit']['min_notional_usd'])}–{num(r['audit']['max_notional_usd'])}" if r['audit']['min_notional_usd'] is not None else 'Stop-sized'] for r in mainrows])
 lines+=['## Monthly closed-trade USD and counts','',
 'Each cell is net USD / number of trades closed. September 2025 and September 2026 are partial months. This is attribution of full trade P&L to its closing month, not a broker cash statement or monthly equity/payout series. Entry fees on trades spanning months are attributed with their eventual close.']
 table(lines,['Month','USDJPY morning','US30 Tuesday','US100 daily','US100 ORB'],[[m]+[f"{usd(r['months'][m]['net_usd'])} / {r['months'][m]['trades']}" for r in mainrows] for m in mainrows[0]['months']])
 lines+=['## Monthly closed-balance returns','',
 'Return is attributed closed-trade P&L divided by the prior attributed closed balance; no withdrawals. Not a floating-equity monthly return.']
 table(lines,['Month','USDJPY morning','US30 Tuesday','US100 daily','US100 ORB'],[[m]+[num(r['months'][m]['return_pct'])+'%' for r in mainrows] for m in mainrows[0]['months']])
 lines+=['## Predeclared controls','',
 'These are context comparisons, not optimized alternatives or proof of a causal edge. The buy-and-hold control has one trade, full-year overnight exposure and swaps; its win rate/PF are not statistical evidence. Alternating-direction controls can have different valid geometry and participation from breakout entries.']
 table(lines,['Control','Trades','Net USD','Return','Net win','Net PF','Equity DD','Max W/L'],[
  [r['case']['label'],r['net']['trades'],usd(r['net']['net_usd']),num(r['net']['return_pct'])+'%',num(r['net']['win_rate_pct'])+'%',num(r['net']['profit_factor']),num(r['metrics']['max_equity_dd_pct'])+'%',f"{r['net']['max_win_streak']} / {r['net']['max_loss_streak']}"] for r in controls])
 lines+=['## Costs, coverage and execution limitations','',
 'Spread is already in bid/ask entry/exit prices, so it is not subtracted again as a separate fee. Delay-induced slippage is simulated, not an empirical reconstruction of live fills. Broker historical contract/session/commission/swap schedules have NOT been independently reconstructed. In particular, winter scheduled exits can meet market-closed responses under the tester\'s available broker session specification. This is broker/tester-dependent evidence, not exact parity with the source broker.']
 table(lines,['Strategy','Commission USD','Swap USD','Native coverage','Late scheduled exits','Max holding hours'],[
  [r['case']['label'],num(r['net']['commission']),num(r['net']['swap']),r['metrics']['history_quality'],len(r['audit']['late_exits']),num(max((t['holding_hours'] for t in r['trades']),default=0),1)] for r in records])
 lines+=['Real ticks begin January 1, 2026 in these native journals. Earlier missing history is generated/mixed. Requesting Model 4 does not mean 100% real ticks. No out-of-sample claim is made.','',
 'The maximum initial SL risk is fill-to-original-stop before commission and swap, converted to USD. No-stop sizing has unlimited downside up to account/margin constraints; historical DD is not a future bound.','',
 '### Late scheduled exits — primary strategies']
 table(lines,['Strategy','Entry UTC','Exit UTC','Intended exit (strategy local clock)'],[[r['case']['label'],x['open'],x['close'],x['due']] for r in mainrows for x in r['audit']['late_exits']])
 lines+=['## Verification','',
 'Clean compile: zero errors and zero warnings. Each report is checked against frozen inputs, asset, dates, build hashes and execution delay. Native cash totals reconcile to trade ledgers. Every filled entry is checked against original orders and signal logs: local clocks, one-trade/day, completed candles, 25 past SMA closes, stop/target geometry, no-stop notional, costs and exit timing. Independent checks use Python zoneinfo for clock conversion. No live trading API was called.','',
 'Full specification: RULES.md. Frozen runs: run-config.json and BUILD.json. Audits: native/*/AUDIT.json. All raw histories, monthly values and metrics: RESULTS.json. FINAL_CHECKS.json records source/screenshot hashes, independent DST-transition checks and monthly ledger reconciliation.','',
 'Technical references: [MT5 testing and real ticks](https://www.mql5.com/en/docs/runtime/testing), [time-series access](https://www.mql5.com/en/docs/series/copyrates), [account-currency profit calculation](https://www.mql5.com/en/docs/trading/ordercalcprofit).']
 (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 audit.runner.save(ROOT/'RESULTS.json',dict(complete=True,period=[cfg['from'],cfg['to']],build=build,primary_definitions=4,controls=4,smokes=4,optimization=False,records=records))
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 import matplotlib.dates as mdates
 from matplotlib.ticker import FuncFormatter
 fig,axes=plt.subplots(2,2,figsize=(12,8),sharex=True,sharey=True,layout='constrained')
 for ax,r in zip(axes.flat,mainrows):
  ts=[datetime(2025,9,27)];ys=[10000.]
  for t in sorted(r['trades'],key=lambda t:t['close_time']):ts.append(datetime.fromisoformat(t['close_time']));ys.append(ys[-1]+t['net_profit'])
  ts.append(datetime(2026,9,27));ys.append(ys[-1])
  ax.step(ts,ys,where='post',color='#0072B2',linewidth=1.7)
  ax.axhline(10000,color='#777777',linewidth=.8);ax.grid(alpha=.16)
  ax.set_title(r['case']['label'],loc='left',fontsize=11)
  ax.text(.03,.94,f"Net {r['net']['return_pct']:+.2f}% | Equity DD {r['metrics']['max_equity_dd_pct']:.2f}%",transform=ax.transAxes,va='top',fontsize=10)
  ax.text(.03,.85,'1% stop-risk target' if r['case']['mode'] in (1,4) else 'No stop: $10,000 fixed notional',transform=ax.transAxes,va='top',fontsize=9)
  ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3));ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
  ax.yaxis.set_major_formatter(FuncFormatter(lambda y,_:f'${y/1000:.1f}k'))
 for ax in axes[:,0]:ax.set_ylabel('Attributed closed balance (USD)')
 for ax in axes[-1,:]:ax.set_xlabel('UTC close date')
 fig.suptitle('Four raw strategies — separate $10,000 accounts',fontsize=15)
 fig.supxlabel('Native costs + 150ms delay | 73% real ticks | Balance curves understate floating-equity risk',fontsize=10)
 fig.savefig(ROOT/'balance_comparison.png',dpi=150);plt.close(fig)
 print('REPORT, RESULTS and balance comparison saved',flush=True)
if __name__=='__main__':main()
