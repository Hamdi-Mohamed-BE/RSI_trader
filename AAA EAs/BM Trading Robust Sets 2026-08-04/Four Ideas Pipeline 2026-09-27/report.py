"""Evidence-backed pipeline handoff. Rejected versions remain research only."""
from pathlib import Path
import json,collections
import pipeline as p
ROOT=p.ROOT;OPT=ROOT/'Optimization'
def read(path):return json.loads(path.read_text())
def f(x,d=2):return 'n/a' if x is None else f'{x:,.{d}f}'
def table(lines,headers,rows):
 lines.extend(['','| '+' | '.join(headers)+' |','|'+'|'.join('---' for _ in headers)+'|'])
 lines.extend('| '+' | '.join(map(str,r))+' |' for r in rows);lines.append('')
def main():
 g=read(ROOT/'GATE.json');checks=read(ROOT/'FINAL_CHECKS.json');assert checks['ok'] and g['all_confirmed']
 selected=read(OPT/'SELECTED.json');hold=read(OPT/'HOLDOUT_GATE.json');v=read(OPT/'VALIDATION.json');trials=read(OPT/'SEARCH_RESULTS.json')
 lines=['# Four screenshot strategies — pipeline outcome','',
 'Completed 2026-09-27. **No version is approved for production or FTMO deployment.**', '',
 'All four raw strategies went through the frozen qualification gate. Only USDJPY morning breakout passed and proceeded to staged parameter optimization. Its validation-selected candidate failed the one-time historical holdout, so that branch stopped too. This is a completed rejection decision, not a claim that every possible variation was optimized or that the chance of funding is zero.', '',
 '## Work completed','',
 '- 36 new native MT5 raw/control evaluations: 16 Model 1 screens, 16 Model 4 long-window confirmations, and four Model 4 six-month runs. The existing eight one-year strategy/control reports were reused without modification.',
 '- Three passive native session/quote-coverage probes; they cannot submit trades.',
 '- Two one-year native parity checks: the original handler and the extended engine at raw settings both match the original completed trades exactly.',
 f"- {checks['search_evaluations']} staged optimizer evaluations covering {checks['distinct_parameter_vectors']} distinct parameter vectors, including the neighbourhood checks. Repeated baselines and inactive-field duplicates are retained and counted conservatively, not claimed as independent discoveries.",
 '- Three separate-period native finalist validations and one historical holdout. No re-tuning after the holdout failed.',
 f"- Independently rechecked {checks['raw_trades_audited']:,} extended raw/control trades: cash totals, orders, clocks, geometry, historical SMA inputs, costs and scheduled-exit delays. Reviewed optimizer manifests, source/binary/report hashes and final native cash ledgers.",
 '- All research builds compiled with zero errors and zero warnings. No live trading API calls, production EA changes, BAT changes, website changes, account changes or Git push.', '',
 '## Raw results — all requested windows','',
 'Periods end 2026-09-27 exclusive; starts are 2026-03-27, 2025-09-27, 2023-09-27 and 2021-09-27. Windows overlap and are not independent experiments. Returns are total-period returns, not annualized.', '',
 'Separate $10,000 native research accounts, Exness-MT5Trial16, 150 ms simulated execution delay and recorded bid/ask/commission/swap. Breakouts use 1% current-equity intended stop risk rounded UP, which is not a guaranteed loss cap. The no-stop US30 and US100 daily-long strategies use $10,000 fixed initial notional rounded DOWN, NOT 1% risk. Do not compare these as equally risky portfolios.', '',
 'Win rate, PF and streaks are based on net completed-trade results; drawdown is native maximum relative floating-equity drawdown. Frequency includes weekdays with no trades.']
 table(lines,['Strategy','Window','Trades','/month','/weekday','Return','Net PF','Net win','Equity DD','Max W/L'],[
  [r['label'],r['period'],r['trades'],f(r['trades_per_month'],1),f(r['trades_per_weekday']),f(r['return_pct'])+'%',f(r['profit_factor']),f(r['win_rate_pct'])+'%',f(r['equity_dd_pct'])+'%',str(r['max_win_streak'])+'/'+str(r['max_loss_streak'])] for r in g['rows']])
 lines+=['## Frozen raw gate and decision','',
 'Both 3y and 5y must have positive net P&L, net PF >=1.15, >=30 trades, and higher return/equity-DD than the predeclared control. This last measure operationalizes the canonical pipeline\'s “better than control” requirement and was frozen before the extended tests. A failing strategy is not optimized solely to rescue its backtest.']
 table(lines,['Strategy','3y return/DD','3y control return/DD','5y return/DD','5y control return/DD','Decision'],[
  [c['label']]+[f(next(r for r in g['rows'] if r['id']==c['id'] and r['period']==period)[key]) for period in ('3y','5y') for key in ('return_dd','control_return_dd')]+[next(d['status'] for d in g['decisions'] if d['id']==c['id'])] for c in p.CASES[:4]])
 lines+=['- **USDJPY morning breakout:** passes raw numeric gate; 32% equity DD at raw risk is already a serious risk issue. Proceeded to optimization, then rejected on holdout.',
 '- **US30 Turnaround Tuesday:** PF looks good, but the 25-day SMA filter does not beat unfiltered Monday longs on the frozen risk-adjusted comparison. No-stop sizing and missing early overnight quotes are additional limitations. Not optimized.',
 '- **US100 daily long:** net PF 1.11 / 1.09 on 3y / 5y, below 1.15. Strong recent performance does not override the long-window failure. Not optimized.',
 '- **US100 NY ORB:** net PF about 1.04 on both long windows and a losing last year/six months. Not optimized.', '',
 '## What USDJPY optimization tested','',
 'Staged search on 2021-09-27–2024-03-27. Top three development candidates were carried through applicable dimensions: M1 through H4 signal timeframes; pending/closed-bar/confirmation/retest entries; range, ATR, fixed, percentage, candle and swing stops; BE, ATR, percent, MA, swing, chandelier and step-lock trailing; 0.5R through 6R, no TP and other exits; shifted intraday ranges; direction; filters; weekdays; reentry/trade counts; max hold; entry buffer and range duration.', '',
 'D1 has no completed same-day signal before the intraday exit. Pyramiding/weekend holds are outside this one-position intraday hypothesis. A separate next-bar market entry duplicates the first available tick after a completed bar. News and volatility-regime overlays were not run without a complete matched point-in-time dataset. This is the frozen applicable staged grid, not an exhaustive Cartesian search of every conceivable strategy.']
 stages=list(dict.fromkeys(r['stage'] for r in trials))
 table(lines,['Stage','Evaluations'],[[s,sum(r['stage']==s for r in trials)] for s in stages])
 lines+=['Neighbourhood audit: each of the three finalists had 27 evaluations but only **nine distinct active neighbouring combinations**. The step-lock variant ignores the trailing-distance field used as the third coordinate, causing equal triplication; the range-time and exit-time coordinates remain active. All nine active neighbours were profitable on development. This does not establish robustness across market regimes; the holdout disproved it.', '',
 '## Native finalist results on separate periods','',
 'Validation: 2024-03-27–2025-09-27. Candidate selected using the predeclared net-PF/return-DD score, not by inspecting holdout outcomes. All three validation runs had unacceptable drawdown for deployment.']
 table(lines,['Candidate','Trades','/month','/weekday','Return','Net PF','Net win','Equity DD','Max W/L'],[
  [str(x['index'])+(' (selected)' if x['index']==selected['index'] else ''),x['net']['trades'],f(x['net']['trades_per_month'],1),f(x['net']['trades_per_weekday']),f(x['net']['return_pct'])+'%',f(x['net']['profit_factor']),f(x['net']['win_rate_pct'])+'%',f(x['metrics']['equity_dd_pct'])+'%',str(x['net']['max_win_streak'])+'/'+str(x['net']['max_loss_streak'])] for x in v])
 z=hold['result'];n=z['net']
 lines+=['Historical holdout: **2020-09-27–2021-09-27**, tested once on the selected candidate. It is an earlier unused regime, not a prospective forward test. The already-inspected most recent year was not called an untouched holdout.']
 table(lines,['Evidence','Trades','/month','/weekday','Return','Net PF','Net win','Equity DD','Max W/L'],[
  ['Selected candidate: held-out year',n['trades'],f(n['trades_per_month'],1),f(n['trades_per_weekday']),f(n['return_pct'])+'%',f(n['profit_factor']),f(n['win_rate_pct'])+'%',f(z['metrics']['equity_dd_pct'])+'%',str(n['max_win_streak'])+'/'+str(n['max_loss_streak'])]])
 lines+=['**Rejected settings — do not deploy:** range 09:00–13:00 on the declared synthetic broker clock (NY+7); pending stops both sides, cancel opposite on fill; initial stop 0.5 × ATR(14,M1); no TP; step-lock trailing starts at 1R, with the tested 0.5R-step/0.2R-lock formula; up to three entries with stop-exit reentry; flat 20:00; no direction or extra filter. These are substantially changed research settings, not the original screenshot rules.', '',
 'The selected candidate ended the validation period at +651.29%, but lost 86.4% from an equity peak along the way. On the held-out year it reduced $10,000 to **$113.93**. A large final return alone would have selected an unsuitable strategy.', '',
 '## FTMO suitability: no candidate to add','',
 'FTMO 2-Step uses 10% / 5% phase targets, a 5% daily loss amount, a static 10% maximum-loss amount, and at least four trading days per evaluation phase. Daily equity includes floating P&L, swaps and commissions and resets at 00:00 CE(S)T. On $10,000, the relevant daily amount is $500 and the static initial equity floor is $9,000. [Official objectives](https://ftmo.com/en/trading-objectives/).', '',
 'The official current symbol API reports USDJPY contract size 100,000 USD and Swing leverage 1:30. [FTMO symbol specifications](https://ftmo.com/en/symbols/) / [official data](https://ftmo.com/wp-json/ftmo/symbols). This was checked on 2026-09-27; account-specific settings must still be verified before any future deployment.']
 for d in checks['diagnostics']:
  first=d['first_trade'];breach=d['first_closed_balance_below_9000']
  lines+=['',f"- **{d['case']}**: first trade {f(first['lot'])} lots; required standalone margin at 1:30 is ${f(first['ftmo_1_to_30_margin_usd'])}, versus $10,000 starting equity. {d['orders_requiring_more_than_entire_equity_at_ftmo_leverage']} of {d['trades']} filled Exness-replay orders require more than the ENTIRE equity-at-placement under the FTMO leverage counterfactual.",
   f"  Median native round-trip commission consumed {f(d['median_roundtrip_cost_pct'],3)}% of equity, on top of intended stop risk. Maximum fill-to-original-stop exposure reached {f(d['max_fill_stop_risk_pct'])}% before fees.",
   f"  The Exness replay closed balance first went below $9,000 at {breach['closed_at']} UTC, after trade {breach['trade_number']}, at ${f(breach['closed_balance'])}."]
 lines+=['',
 'These are **diagnostic counterfactuals, not an executable FTMO backtest or pass probability**. FTMO margin would reject or reduce many orders, producing a different trade path. Maximum relative equity DD is also not the same thing as FTMO\'s static loss rule. The early closed-balance violations above are a separate explicit check, not an inference from the DD percentage.', '',
 'No pass/funding/payout percentages are reported: the candidate failed economic validation and its native sizing is not FTMO-executable. No Monte Carlo, full FTMO lifecycle or portfolio-addition simulation was run after the holdout stop gate. A failed held-out strategy should not be rehabilitated by reshuffling the same trades or selecting a replacement using that now-exposed holdout.', '',
 '## Data, sessions and execution limitations','',
 '- Model 4 real-tick coverage: 6m 100%, 1y 73%, 3y 24%, 5y 14%. The separate validation and historical holdout were **0% real ticks**, generated from the available broker bars. Model 4 is not synonymous with an all-real-tick history. The fast Model 1 reports\' “100%” quality is not a real-tick claim. [MetaTrader tick modelling](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation).',
 '- Passive five-year coverage probes show no US30/USTEC quotes at the required synthetic-broker 01:05 entry minute through May 2023. Entries become available in June 2023. The no-stop strategies\' nominal five-year runs therefore do not represent five years of usable entry-session coverage.',
 '- Current native index trade-session metadata closes 21:00–22:00 UTC on weekdays. The intended winter 23:50 synthetic-broker exit is 21:50 UTC, inside that closure. Historical holiday/quote availability also matters. Delayed closes are retained in the evidence, not silently moved earlier. These are broker-constrained reproductions; source-broker and FTMO session parity is not established.',
 '- This rejection is not proof that every implementation of the screenshot concepts fails universally. It is a conclusion about these explicit rules, controls, available data and frozen search.',
 '- Simulated 150 ms delay is not measured live slippage. No invented measured-cost stress was supplied. Historical broker spec/commission/swap schedules and FTMO fills were not reconstructed.', '',
 '## Integrity and handoff','',
 'Original raw source/rules/build hashes remained unchanged. All extended native reports reconcile to their deals. The independent FX arithmetic check records 63 small conversion-price approximation exceptions (maximum $1.76) rather than assuming that the conversion quote equals the stop execution price; exact report/deal net-cash reconciliation remains enforced.', '',
 'Artifacts: `GATE.json` (all raw net stats); `TIMING_COVERAGE.json` (monthly quote/session evidence); `Optimization/SEARCH_RESULTS.json` (all trials); `Optimization/VALIDATION.json`, `SELECTED.json`, `HOLDOUT_GATE.json`, `STOP.json`; `FINAL_CHECKS.json` (independent checks); compressed native reports/journals in both native folders. See both frozen protocols for interpretation and scope.', '',
 '**Recommendation: leave the current trading system and FTMO configuration unchanged.** The raw USDJPY idea remains a research lead only. Any follow-up would need a newly frozen broker-executable risk/cost specification and fresh validation data, not a silent fallback chosen after this failed holdout.']
 (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 p.save(ROOT/'RESULTS.json',dict(complete=True,decision='NO_PROMOTION',raw=g,optimization=dict(evaluations=len(trials),unique_vectors=checks['distinct_parameter_vectors'],selected=selected,holdout=hold,stop=read(OPT/'STOP.json')),checks=checks,not_run=['Monte Carlo after failed holdout','FTMO lifecycle probabilities','production/website/BAT integration']))
 p.status('COMPLETE — no promotion: three raw failures and one failed optimization holdout',approved_versions=0)
 print('Report and result bundle saved',flush=True)
if __name__=='__main__':main()
