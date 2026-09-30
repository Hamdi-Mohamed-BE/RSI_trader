from pathlib import Path
import json,re
import numpy as np
import study as s
import prop_engine as pe
ROOT=Path(__file__).resolve().parent
def f(x,n=2):return '—' if x is None else f'{x:.{n}f}'
def main():
 raw=json.loads((ROOT/'RAW_RESULTS.json').read_text());props=json.loads((ROOT/'NATIVE_PROP.json').read_text());ver=json.loads((ROOT/'VERIFICATION.json').read_text())
 cfg=json.loads((ROOT/'run-config.json').read_text());selection=json.loads((ROOT/'SELECTION.json').read_text())
 names={'sweep-inversion-control':'Sweep/inversion control','aligned-smt-static':'Aligned SMT — static','aligned-smt-structural-be':'Aligned SMT — structural BE','aligned-smt-1r-be':'Aligned SMT — 1R BE'}
 assert len(raw)==20 and len(props)==16 and not any(x['screen_pass'] for x in selection)
 def get(name,w):return next(x for x in raw if x['variant']==name and x['window']==w)
 text=['# Trader Kane PO3 / SMT — raw research result','',
 '28 September 2026. Decision: **REJECT for deployment. No raw candidate passed the long-window gate.**',
 '',
 'This tests explicitly labelled mechanical approximations of the supplied interview, not Kane’s complete discretionary model, claimed payouts or trading record. His intuition, swing selection and exceptions cannot be recovered from the transcript. USTEC/US500 are Exness CFDs, not NQ/ES futures.',
 '',
 '## What survived scrutiny',
 '',
 '- Daily/H4/H1 location plus SMT improved on the very weak basic control, but the effect was not enough for long-window profitability.',
 '- Structural breakeven reduced drawdowns and five-year losses, while reducing recent profits. That is a risk/return trade-off, not evidence of a profitable edge.',
 '- The static and 1R variants happened to have identical one-year net outcomes despite eight 1R stop modifications; a modification does not necessarily change the eventual exit.',
 '- All aligned variants made zero simulated eligible payout requests across the tested account horizons. Low trade frequency and conservative account constraints matter.',
 '',
 '## Frozen implementation',
 '',
 '10:00–11:30 New York entries, M3 closed-candle inversion, paired previous-hour sweep divergence, prior-day midpoint and custom 06:00–10:00 H4 range context. Stop beyond the current-hour extreme; target combined prior/current-hour midpoint; maximum two entries daily; flat at noon. Both directions, no PM discretionary re-entry or runner.',
 '',
 'The midpoint is an arithmetic level, not a guarantee of fair value or a required market destination. Exact assumptions and deviations from the interview are in [RULES.md](RULES.md). Four variants were frozen before outcomes; no losing rule was optimized afterwards.',
 '',
 '## Native tester performance',
 '',
 'Each case starts with $10,000 and targets fixed $100 initial stop-risk, rounded down to lot step; fills may change actual risk slightly. Native broker spread/costs and 150ms execution delay. Research leverage is not prop-account leverage. PF is computed from complete net position outcomes. Win rate includes tiny net-positive BE exits. DD is MT5 equity peak-relative drawdown.',
 '',
 'Frequency per day uses all weekdays in the window, not only days with a trade, and is not a promise of daily opportunities. Window end: 27 September 2026; start dates are in the table headings.']
 for w,title in [('6m','6 months — 27 March 2026; Model 4'),('1y','1 year — 27 September 2025; Model 4, mixed ticks'),('3y','3 years — 27 September 2023; Model 1 screen'),('5y','5 years — 27 September 2021; Model 1 screen')]:
  text+=['','### '+title,'','| Version | Trades | /month | /weekday | Return | PF | Win % | Equity DD % | Max W/L streak |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
  for name in names:
   a=get(name,w)['stats'];label=names[name]+(' †' if a['capital_exhausted'] else '')
   text.append(f"| {label} | {a['trades']} | {f(a['trades_month'])} | {f(a['trades_weekday'],3)} | {f(a['return_pct'])}% | {f(a['pf'])} | {f(a['win_rate'])} | {f(a['equity_dd_pct'])} | {a['max_win_streak']}/{a['max_loss_streak']} |")
 dead=get('sweep-inversion-control','5y')['stats']
 text+=['',f"† The five-year control exhausted its native research balance; final recorded exit {dead['last_exit_utc']}. Its full-window trade opportunity count and profitability comparison are not valid after exhaustion. The small negative balance is the tester outcome, not an approved prop loss allowance.",
 '',
 'Gate: positive net, PF >=1.15, >=30 trades, and outperform the named viable control on BOTH three and five years. Static and structural BE fail profitability; 1R BE barely breaks even on three years (PF about 1.004) and loses on five years. Even ignoring the exhausted five-year control, all candidates fail their own profitability/PF conditions.',
 '',
 'No long Model4 confirmation, stage-5 parameter optimization, promotion Monte Carlo, portfolio addition or production build was performed after this failure. Model1 screens are not marketed as real-tick proof.',
 '',
 '## Breakeven changes',
 '',
 'Recorded one-way stop modifications (performance is shown in the complete tables above):','']
 for name in ['aligned-smt-static','aligned-smt-structural-be','aligned-smt-1r-be']:
  for w in ['1y','5y']:
   r=get(name,w);a=r['stats']
   text.append(f"- {names[name]}, {w}: {r['signal_audit']['be_moves']} stop modifications across {a['trades']} entries.")
 text+=['','Stops only moved toward reduced risk, with a fee/spread allowance. They cannot guarantee a zero-loss exit. Early exits can free a slot for a second trade, so the five-year comparison includes changed opportunity availability (84 structural-BE entries versus 78 static), not just repricing an identical ledger.',
 '',
 '## Standalone planned-account replay',
 '',
 'Offline replay of the ONE-YEAR native opportunity stream, with smaller lots, target-account leverage, conservative margin/risk limits and withdrawal rules. This is not a test on either firm’s server. [Account rules, sources and assumptions](PROP_RULES.md) are part of these results.',
 '',
 '**Aligned SMT static, structural BE and 1R BE: 0 payouts, 0 FTMO phase-one passes and 0 modeled loss-limit breaches in all tested 30/60/120/180-day base and stress replays.** The result is unresolved, not successfully funded. Instant accounts begin directly funded; that status is not an achievement in this table.',
 '',
 'There are 48 / 44 / 35 / 27 matured weekly starts at 30 / 60 / 120 / 180 days. Starts overlap and are not independent future-probability estimates.',
 '',
 '### 180-day account scenarios',
 '',
 '| Version | Account | Costs | Starts | Phase 1 / 2 passes | Payouts | Loss breaches | Compliance blocks | Mean eligible cash |',
 '|---|---|---|---:|---:|---:|---:|---:|---:|']
 for name in names:
  for r in props:
   if r['tag']!=f'USTEC-{name}-1y-m4':continue
   a=next(x for x in r['rolling'] if x['days']==180)
   phase=f"{a['phase1']}/{a['phase2']}" if r['firm']=='FTMO' else 'n/a'
   text.append(f"| {names[name]} | {r['firm']} | {'Stress' if r['stress'] else 'Base'} | {a['starts']} | {phase} | {a['payout']} | {a['breach_before']+a['breach_after']} | {a['compliance_blocked']} | ${f(a['mean_cash'])} |")
 text+=['','The weak control sometimes makes a small Instant withdrawal in a favourable subperiod. This does not repair its negative full-period expectancy or qualify it for use. Cash excludes purchase, reset, add-on fees, tax and actual approval/processing delay.',
 '',
 '### Entire-year account-risk diagnostic (no withdrawals or evaluation phases)',
 '',
 '| Version | Account | Costs | Accepted trades | /month | /weekday | Net return | PF | Win % | Equity-envelope DD % | Max W/L | Margin rejects |',
 '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
 for r in props:
  name=r['tag'].removeprefix('USTEC-').removesuffix('-1y-m4');h=r['historical'];a=h['snapshot'];capital=10000 if r['firm']=='FTMO' else 5000;ts=np.array(h['trades']);n=len(ts);net=float(ts[:,4].sum()) if n else 0;st=s.stats(ts[:,4] if n else [],365)
  text.append(f"| {names[name]} | {r['firm']} | {'Stress' if r['stress'] else 'Base'} | {n} | {f(n/12)} | {f(n/260,3)} | {f(net/capital*100)}% | {f(st['pf'])} | {f(st['win_rate'])} | {f(a['envelope_dd_pct'])} | {st['max_win_streak']}/{st['max_loss_streak']} | {sum(x[1] for x in h['rejected'])} |")
 text+=['','Account-envelope DD is measured as a percentage of initial capital, unlike the native peak-relative DD. The 10:00 NY entry window makes an incomplete news calendar particularly important for Instant: the replay has only 29 existing event timestamps. Cost stress uses explicit hypothetical haircuts, not measured target-broker execution.',
 '',
 '## Data coverage and verification',
 '',
 f"- {ver['valid_native_cases']} completed native cases: four short smoke tests plus sixteen raw-window tests. Clean compile, {ver['unit_tests']} unit tests passed, cash reconciled to native deals and reports.",
 f"- Independent pre-existing M1 archives reconstructed {ver['independent_history']['decisions']} recorded decisions, with {ver['independent_history']['numeric_comparisons']} comparisons and zero mismatches. This overlapping archive ends {ver['independent_history']['latest_common_bar']}; repeated-window records are not independent observations.",
 '- Six-month vs matching one-year trades reconcile exactly for all four variants, including prices, stops, target, lot size and cash.',
 '- Actual real ticks for both symbols begin 1 January 2026. Six-month report quality is 100% real ticks; one-year and smoke percentages below include warm-up periods. Do not describe the entire one-year trade history as real ticks.',
 '',
 '| Version | Smoke report quality | 6m report quality | 1y report quality |',
 '|---|---|---|---|']
 for name in names:text.append('| '+names[name]+' | '+' | '.join(get(name,w)['stats']['history_quality'] for w in ['smoke','6m','1y'])+' |')
 text+=['','Older reference data are incomplete. The EA safely skipped insufficient reference windows or mismatched paired candles; it did not fabricate confirmation. Each variant rejected 80 reference checks in one year; 130 reference plus 58 synchronization checks in three years; 160 plus 148 in five years. These are repeated M3 checks, not unique missing days. Six-month checks had none. Execution verification passes, but complete-reference-history verification is explicitly FALSE.',
 '',
 f"- {ver['infrastructure_retry_reports']} tester connection/authorization failures were retained as rejected infrastructure attempts; only fresh reports with correct input hashes and cash reconciliation count. A process-level lease was added to the runner to serialize later batches.",
 '- No invalid volume/stops or unexplained order failure occurred in successful runs. The control capital-exhaustion warning is preserved and disqualifying.',
 '- Live MT5 PID 11196 and its creation timestamp are unchanged; no live API was used. Tracked Git diff remains empty; only dated research artifacts and the isolated tester were used.',
 '',
 '## Files',
 '',
 '- [Frozen rules](RULES.md) and [configuration](run-config.json)',
 '- [Raw results](RAW_RESULTS.json), [account replay results](NATIVE_PROP.json), [gate decision](SELECTION.json)',
 '- [Verification](VERIFICATION.json), [independent history audit](HISTORY_AUDIT.json), [test results](TEST_RESULTS.txt)',
 '- Tester-only source/binary plus per-case native report, deals, groups, signal and management logs in this folder. They refuse operation outside Strategy Tester.',
 '',
 'Bottom line: keep the research, not the deployment. Recovering exact discretionary range selection would require additional source material or an explicit new research protocol; it is not legitimate to present these failed proxies as Kane’s full strategy.']
 for r in props:
  if 'sweep-inversion-control' not in r['tag']:
   assert all(a['payout']==0 and a['phase1']==0 and a['breach_total_pct']==0 for a in r['rolling'])
 document='\n'.join(text)+'\n'
 document=re.sub(r'\]\(([A-Za-z_][A-Za-z_0-9.-]+)\)',lambda m:'](<'+(ROOT/m[1]).as_posix()+'>)',document)
 (ROOT/'REPORT.md').write_text(document,encoding='utf-8')
 (ROOT/'README.md').write_text('# Kane research — rejected at raw gate\n\nStart with [REPORT.md](<'+(ROOT/'REPORT.md').as_posix()+'>). No deployment or optimization. Live session unchanged.\n',encoding='utf-8')
 print('REPORT.md generated; 20 native cases, 16 account scenarios, no qualified candidate.')
if __name__=='__main__':main()
