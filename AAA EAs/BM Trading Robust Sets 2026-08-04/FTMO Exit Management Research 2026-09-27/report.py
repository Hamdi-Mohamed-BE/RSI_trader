"""Render audited research results, with no account or production side effects."""
from pathlib import Path
import json
from collections import defaultdict
ROOT=Path(__file__).resolve().parent
NAMES={'gold':'Gold Overnight Value Area (raw)','overnight':'Nasdaq Overnight','ema':'EMA3 Full Safe','orb':'ORB Volume Profile (saved 0.75R)','xau':'News Pulse XAU','xag':'News Pulse XAG'}
EXITS={'native':'Current/native','rr075':'Fixed 0.75R','rr050':'Fixed 0.50R','atr':'M15 ATR trailing','profile':'Previous-session profile trailing'}
def f(v,n=1):return '—' if v is None else f'{v:,.{n}f}'
def money(v):return ('−' if v<0 else '+')+'$'+f(abs(v),2)
def main():
 data=json.loads((ROOT/'RESULTS.json').read_text());checks=json.loads((ROOT/'CHECKS.json').read_text())
 cfg=json.loads((ROOT/'run-config.json').read_text());keys={e['key']:NAMES[n] for n,e in cfg['eas'].items()}
 cases=sorted(data['cases'],key=lambda r:(r['stress'],r['name']))
 lines=['# FTMO exit-management comparison — 27 September 2026','',
 'Research only. No production EA, launcher, website, or live account settings changed. All six research EAs refuse to run outside the strategy tester.','',
 '## Main findings','',
 '- Current exits retained the strongest six-month modeled payout frequency under stress: 82.7%, versus 0.7% with all 0.75R and 0.0% with all 0.50R.',
 '- Non-news M15 ATR improved the four-month payout frequency from 41.3% to 46.3%, but reduced six-month frequency to 80.2%, reduced win rate and increased modeled drawdown. This is a speed-versus-stability trade-off, not a clear overall upgrade.',
 '- Target-proximity risk halving slowed completion in this test: current + protection reached 75.4% paid by six months versus 82.7% without it. The study does not establish that protection never helps in other conditions.',
 '- Two isolated candidates merit fresh validation: EMA3 at 0.75R and ORB at 0.50R. They have not been combined into a post-hoc optimized portfolio in this report.',
 '- Do not change raw Gold or news exits solely to chase win rate. The raw Gold target is often already below 0.75R, so this change can move its target farther away. News gains depend heavily on a few large winners.',
 '- All modeled breach counts were zero under the admission gates and stop-reserve approximation. This is not a real-world zero-risk finding. All percentages are fitted-history scenario results, not independently validated FTMO forecasts.','',
 '## Scope and what was actually tested','',
 'Basket: raw Gold Overnight Value Area, News Pulse XAU, News Pulse XAG, Nasdaq Overnight, EMA3 Full Safe, and the saved ORB Volume Profile 0.75R configuration. Nasdaq 5M DI and RSI/VWAP are **not** in this six-EA test.','',
 '24 new native MT5 runs: 2 March through 30 August 2026 (end-exclusive 31 August), real ticks, $10,000 initial native balance, 150 ms fixed execution delay. Native quotes are from the isolated Exness research terminal, **not FTMO ticks**. Native leverage is 1:2000 only for generating individual strategy ledgers. Their original sizing is retained; the separate shared-account model imposes FTMO-like leverage and strict dollar risk.','',
 'Then 16,000 paired simulations: eight portfolios × reference/stressed costs × 1,000 paths. All alternatives use the same 26 sampled joint weeks and random seed. The chronological shared-account comparison covers 4 March–30 August (180 days).','',
 'This is exploratory re-use of previously examined history, including fitted news parameters. The simulated percentages are conditional scenario frequencies, **not independently validated real-world success probabilities**.','',
 '| Exit version | Frozen rule |', '|---|---|',
 '| Current | Original targets and management, freshly rerun at the same execution delay |',
 '| Fixed 0.75R / 0.50R | Initial TP at requested entry ± stated multiple of original stop distance; original trailing disabled; original time exits retained |',
 '| M15 ATR | No TP; activate after a completed M15 close reaches +1R; trail best completed close by 2×ATR(14), never widen |',
 '| Profile | No TP; activate after +0.5R; trail behind crossed previous completed UTC-session low/VAL/POC/VAH/high, with 0.2 ATR buffer; completed M15 confirmation |','',
 'The profile uses 64 price bins, M1 typical-price tick-volume, 70% value area and at least 300 bars in the prior eligible UTC day, searching back up to seven days. This is a broker tick-volume proxy, not centralized exchange volume. No forming-bar or future-day levels are used. Neither ATR nor profile parameters were optimized in this batch. Partial profit-taking was not tested.','',
 'Stops are not widened. Both pending sides remain enabled for news. A smaller/farther TP can change holding time, future entry availability and order acceptance, so trade counts need not be identical. Slippage makes achieved R differ from the requested target R.','',
 '## Portfolio definitions','', '| ID | Exit assignments |', '|---|---|',
 '| A | Current exits on all six |','| B | Fixed 0.75R on all six |','| C | Fixed 0.50R on all six |',
 '| D | 0.75R on the four non-news EAs; news unchanged |',
 '| E | Gold/ORB profile trailing; Overnight/EMA M15 ATR; news unchanged |',
 '| F | E plus target-proximity risk reduction |','| G | M15 ATR on all four non-news EAs; news unchanged |',
 '| H | A plus target-proximity risk reduction |','',
 'Target protection halves the next ordinary entry budget only when the phase balance is within two base-risk units ($142.86) of its profit target. It does not close a floating basket early, alter news risk, or change funded-stage risk. E is a preselected strategy-specific hypothesis, not a retrospectively optimized winner.','',
 '## Native per-EA results','',
 'These are independent MT5 runs at each saved source sizing, not additive shared-account dollar returns. Equity DD below is the native **maximum relative equity drawdown**, rather than the percentage attached to maximum cash drawdown. Frequency uses the 26-week source window.','',
 '| EA | Exit | Trades | /week | Net USD | Return | Win rate | PF | Equity DD | Max W/L streak |',
 '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 flat=[]
 for r in data['native']:
  m=r['metrics'];s=r['streaks'];dd=m['relative_equity_drawdown_pct']
  lines.append(f"| {NAMES[r['ea']]} | {EXITS[r['variant']]} | {m['trades']} | {f(m['trades']/26)} | {money(m['net_profit'])} | {f(m['return_pct'],2)}% | {f(m['win_rate_pct'],2)}% | {f(m['profit_factor'],2)} | {f(dd,2)}% | {s[0]}/{s[1]} |")
  flat.append(dict(ea=NAMES[r['ea']],exit=EXITS[r['variant']],trades=m['trades'],trades_per_week=m['trades']/26,net_usd=m['net_profit'],return_pct=m['return_pct'],win_rate_pct=m['win_rate_pct'],profit_factor=m['profit_factor'],native_equity_dd_pct=dd,max_win_streak=s[0],max_loss_streak=s[1]))
 lines+=['','## Shared $10K account — chronological 180-day replay','',
  'All EAs share the same balance, margin and admission limits. This continuous P&L is **not payout income**: it has no evaluation resets or withdrawals. The DD column is a modeled stop-reserve estimate, **not reconstructed native portfolio tick-equity DD**. Actual native equity DD is reported above per EA.','']
 pflat=[]
 for stress in (False,True):
  lines+=['### '+('Stressed costs' if stress else 'Reference costs'),'', '| Portfolio | Trades | /week | Net USD | Return | Win rate | PF | Closed DD | Stop-reserve DD | Worst modeled day | Max W/L |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
  for r in cases:
   if r['stress']!=stress:continue
   h=r['historical'];net=h['balance']-10000
   lines.append(f"| {r['name']} | {h['trades']} | {f(h['trades']/(180/7))} | {money(net)} | {f(net/100,2)}% | {f(h['win_rate'],2)}% | {f(h['pf'],2)} | {f(h['closed_dd_pct'],2)}% | {f(h['model_dd_pct'],2)}% | ${f(h['worst_daily_usd'],2)} | {h['max_win_streak']}/{h['max_loss_streak']} |")
   pflat.append(dict(portfolio=r['name'],stress=stress,trades=h['trades'],net_usd=net,return_pct=net/100,win_rate_pct=h['win_rate'],profit_factor=h['pf'],closed_dd_pct=h['closed_dd_pct'],stop_reserve_dd_pct=h['model_dd_pct'],worst_modeled_day_usd=h['worst_daily_usd'],max_win_streak=h['max_win_streak'],max_loss_streak=h['max_loss_streak']))
 (ROOT/'TABLES.json').write_text(json.dumps({'native':flat,'portfolio':pflat},indent=2),encoding='utf-8')
 lines+=['','## Conditional FTMO outcomes — 1,000 paths per row','',
 'Pass/funding/payment are distinct. Unfinished accounts are not counted as blown. Breaches refer only to the evaluation and funded stage up to the first reward request or day 180, not lifetime funded-account survival. Days are calendar days and conditional on completion within 180 days.','']
 for stress in (False,True):
  lines+=['### '+('Stressed costs' if stress else 'Reference costs'),'', '| Portfolio | Funded 60d | Paid 60d | Funded 120d | Paid 120d | Funded 180d | Paid 180d | Breached by 180d | Median days to funded / paid |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
  for r in cases:
   if r['stress']!=stress:continue
   hh={h['days']:h for h in r['summary']['horizons']};t=r['summary']['timing']
   lines.append(f"| {r['name']} | {f(hh[60]['funded_pct'])}% | {f(hh[60]['payout_pct'])}% | {f(hh[120]['funded_pct'])}% | {f(hh[120]['payout_pct'])}% | {f(hh[180]['funded_pct'])}% | {f(hh[180]['payout_pct'])}% | {f(hh[180]['breach_before_first_reward_pct'])}% | {f(t['funded_days_from_purchase']['median'])} / {f(t['payout_days_from_purchase']['median'])} |")
 lines+=['','## Phase timing and first-reward size — stressed cases','', '| Portfolio | Phase 1 median days | Phase 2 median days from availability | Median first reward if paid | First-payment change vs A (paired, percentage points) |', '|---|---:|---:|---:|---|']
 for r in cases:
  if not r['stress']:continue
  t=r['summary']['timing'];ag=r['aggregate180']
  paired=r['paired_paid180'];ci=paired['paired_mc_only_interval']
  lines.append(f"| {r['name']} | {f(t['phase1_days_among_phase1_passers']['median'])} | {f(t['phase2_days_from_availability_among_phase2_passers']['median'])} | ${f(ag['median_first_reward_if_paid'],2)} | {f(paired['delta_percentage_points'])} pp (MC-only interval {f(ci[0])} to {f(ci[1])}) |")
 lines+=['','## Historical monthly breakdown — stressed costs','', 'Cash is grouped by close month. March and August are partial calendar months. All values are continuous-account trading P&L, not payouts.','', '| Portfolio | Month | Closed trades | Net USD |', '|---|---|---:|---:|']
 for r in cases:
  if not r['stress']:continue
  months=defaultdict(lambda:[0,0.])
  for t in r['historical']['log']:
   m=months[t['close'][:7]];m[0]+=1;m[1]+=t['net_profit']
  for month,(n,net) in sorted(months.items()):lines.append(f"| {r['name']} | {month} | {n} | {money(net)} |")
 lines+=['','## EA contributions — stressed costs','', '| Portfolio | EA | Trades | Win rate | PF | Net USD |', '|---|---|---:|---:|---:|---:|']
 for r in cases:
  if not r['stress']:continue
  for key,v in r['historical']['by_ea'].items():
   lines.append(f"| {r['name']} | {keys[key]} | {v['trades']} | {f(100*v['wins']/v['trades'],2)}% | {f(v['positive']/v['negative'] if v['negative'] else None,2)} | {money(v['net'])} |")
 lines+=['','## Risk and execution assumptions','',
 '- $10,000 FTMO 2-Step Swing model: +$1,000 Phase 1, +$500 Phase 2, four entry days each phase, $500 daily limit, $1,000 static loss floor, Prague midnight reset; no Best Day Rule for 2-Step and no evaluation deadline.',
 '- Ordinary entries: maximum $71.43 initial planned risk, round lots down to 0.01; skip if the minimum lot exceeds budget. News: $10 per pending side, reserve both sides.',
 '- Internal admission: $300 daily loss budget, $225 aggregate planned risk, $150 correlated-metal/per-symbol risk, $9,200 projected equity buffer, max seven fills/day and no new ordinary entries after three closed losses.',
 '- Margin model: 1:15 metals and Nasdaq, at most 80% of modeled available equity. Instrument specifications are modeled assumptions, not a fresh FTMO server verification.',
 '- Reference uses native fills and commission floors ($7 gold, $47.50 silver, $0.70 Nasdaq per lot). Stress reduces positive gross returns by 10%, expands negative gross by 10%, adds adverse price cost (gold ordinary $0.20, gold news $1, silver $0.04, Nasdaq 2 points), doubles negative swaps and includes carry reserve.',
 '- Stop-reserve equity uses ordinary initial risk 1R/1.25R and news 1.25R/2R (reference/stress). It does not track actual combined bid/ask floating equity, tighten this reserve as stops trail, or model unbounded gap losses. Zero modeled breaches does not establish zero actual risk.',
 '- Assumed administration: two business days between phases, five until funded activation, first reward eligibility 14 calendar days after first funded trade while flat and positive by at least $25, four business days for receipt; 80% reward share. These waiting periods are assumptions, not service guarantees.',
 '- Weekly joint resampling preserves within-week cross-EA clustering, but breaks multi-week dependence and has only 26 source weeks. Fitted news settings, parameter selection and broker transfer risk are not cured by more Monte Carlo draws.',
 '- Independent native opportunity ledgers are resized and gated in the shared-account overlay. Skipping a trade can alter later native opportunities; this is not a fully integrated native FTMO portfolio backtest.',
 '- Native baseline may differ from the previous report because it is a fresh six-month run at 150 ms, with current source snapshots and a different warm-up/initial-position context. Compare alternatives to fresh A, not to unrelated prior headline values.','',
 '## Eligibility caveat','',
 'FTMO Swing generally permits news trading, but its general forbidden-practices rules still apply. Pre-news two-sided stop/gap trading requires explicit clarification from FTMO before deployment. This study does not model rejection/disqualification risk or imply the news implementation is approved.','',
 '## Audit','',
 'All production source snapshot hashes remained unchanged. Native trade counts, initial stops, prices, costs, gross/net cash and portfolio ledgers were reconciled. Check details are saved in CHECKS.json. Native tester inputs, reports, journals, source snapshots and binary hashes are retained.','',
 '### Fresh baseline vs earlier cached ledgers','', '| EA | Earlier trades | Fresh trades | Matched entry times | Exact entry/exit price & close-time matches |', '|---|---:|---:|---:|---:|']
 for n,v in data['baseline_parity'].items():lines.append(f"| {NAMES[n]} | {v['old_trades']} | {v['new_trades']} | {v['matched_entry_times']} | {v['exact_price_exit_matches']} |")
 lines+=['','### Native management diagnostics','', '| Case | Manager summary | Journal flags |', '|---|---|---|']
 for r in data['native']:lines.append(f"| {r['ea']}-{r['variant']} | {json.dumps(r['em_summary'])} | {json.dumps(r['flags'])} |")
 lines+=['','### Evidence files','',
 '- RESULTS.json: full simulations, chronological ledgers, phase funnels and paired differences.',
 '- FTMO Exit Comparison.xlsx: native, shared-account and funding comparison tables.',
 '- NATIVE_AUDIT.json, BASELINE_PARITY.json, CHECKS.json: reconciliation and validation.',
 '- run-config.json and PORTFOLIOS_FROZEN.json: frozen test rules.',
 '- native/: compressed native reports/journals, closed trades and metadata for all 24 runs.','',
 '### Official rules checked','',
 '- [FTMO 1-Step / 2-Step comparison](https://ftmo.com/en/comparison-table/)',
 '- [FTMO objectives](https://ftmo.com/en/trading-objectives/)',
 '- [Swing account](https://ftmo.com/en/faq/ftmo-swing-account-type/)',
 '- [Reward withdrawals](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/)',
 '- [Forbidden practices](https://ftmo.com/en/forbidden-trading-practices/)','',
 'No deployment recommendation follows automatically from a highest in-sample return or win rate. Fresh holdout and broker-specific execution validation remain necessary.','']
 (ROOT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
 print('Saved REPORT.md and intermediate table records; checked result cases:',len(cases))
if __name__=='__main__':main()
