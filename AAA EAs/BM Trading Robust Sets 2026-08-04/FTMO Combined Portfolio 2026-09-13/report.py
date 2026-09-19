from pathlib import Path
import csv
import json
from statistics import mean, median

OUT = Path(__file__).resolve().parent
d = json.loads((OUT/'results.json').read_text())
money = lambda n: f'${n:,.0f}' if n >= 0 else f'-${abs(n):,.0f}'
lines = ['# FTMO Swing: 10-EA shared-account simulation', '',
         'Research only; no live EA, BAT, MT5 account, or website data changed.', '',
         '## Scope and interpretation', '',
         '- $100,000 USD; 5 September 2023 through 31 August 2026 (36 calendar rows; September 2023 is partial).',
         '- One shared balance, simultaneous positions, gross reserved margin, lot-step round-up and common risk controls. BTC News excluded.',
         '- Provisional safer proposal: 0.35% normal risk AND 0.35% news risk. This requires changing the locked news setting only if approved later. Current-news 0.75% is shown as a separate control.',
         '- Normal entries: stop at -$1,000 daily closed P/L; $3,000 total planned open-risk gate; 4%/7% drawdown and 3/5 loss-streak tapers. News bypasses those gates/tapers but not broker margin availability.',
         '- Modelled Swing leverage: FX 1:30, indices 1:15, metals 1:9, from FTMO published asset-class guidance. This is not a verified current contract specification for the connected account. 20% equity margin reserve. No cross-position hedge margin credit.',
         '- FTMO 2-Step: 10% then 5% targets; four entry days each; $5,000 daily loss from midnight CE(S)T balance; static $90,000 floor. No 1-Step consistency/trailing-loss rules applied.',
         '- Payout is a possible gross USD trader claim at 80%, not guaranteed income or cash received. Month-end claim, deferred until flat and at least 14 days after first funded trade/previous claim. Leave $2,000 above initial capital; losses must be recovered first. Evaluation profits are never paid out.',
         '- Each phase starts at $100,000; 2 business days assumed between phases. Withdrawal profit, including firm share, leaves the account. Withdrawals/reset adjustments are not trading losses.', '',
         '## Evidence limits — important', '',
         '- This replays existing cached native MT5 deals, not a new all-EA FTMO Strategy Tester run. Feed differences, signal changes and actual FTMO execution are not reproduced.',
         '- CRITICAL: both News Pulse source backtests report only 13% real ticks. Do not treat their news fills, projected payouts or resulting challenge pass frequencies as verified FTMO evidence.',
         '- No continuous bid/ask equity, original stop history or complete pending-order ledger. A no-breach closed-deal result cannot certify FTMO compliance. Stops and original risk are reconstructed estimates, not guaranteed loss bounds.',
         '- Stop-envelope scenario subtracts all open planned stop losses simultaneously, with stress multipliers. It can overstate risk after trailing stops, and can understate gap/unknown-stop risk. A warning is a hypothetical vulnerability, not evidence the real account breached.',
         '- Source recorded commission/swap are retained; zero recorded swap is not proof the target account is swap-free. Source spreads/fill effects are embedded, not separately measured. No claim of exact historical FTMO costs.',
         '- Stress assumptions: news gross winners x0.65, losers x1.25, extra 0.15R per trade; other winners x0.90, losers x1.10, extra 0.02R. Commission floor $7/lot round-trip on metals/FX; double negative swaps and remove credits. These are sensitivity assumptions, NOT an FTMO fee quote or calibrated slippage model.',
         '- Source timestamps treated as UTC (cached Exness schedules), converted to Prague for resets/months. Same-second round trips close one microsecond after entry to preserve event ordering. Commission split equally between entry and exit; swaps booked at exit.',
         '- Sizing scales from each source trade reconstructed entry balance, not from fixed $10k, avoiding double compounding. 0.01 lot step rounded UP; actual planned risk can exceed the nominal percentage.',
         '- All ten EAs were selected with knowledge of historical results. This is retrospective, not independent out-of-sample proof. The news sample/MT5 modelling quality vary; audit lists source file hashes and quality labels.',
         '- No automatic account restart after failure. Open positions at a model halt are not liquidated at invented prices; ending balance then excludes their unresolved floating P/L.', '',
         '## Included EAs', '', '| EA | Mode | Role | Source 5Y trades | Source PF | Source win rate |',
         '|---|---|---|---:|---:|---:|']
for a in d['source_audit']:
    m = a['metrics']
    role = 'Added' if any(e['slug']==a['slug'] and e['added'] for e in d['eas']) else 'Retained'
    lines.append(f"| {a['name']} | {a['mode']} | {role} | {a['ledger_trades']} | {m.get('profit_factor')} | {m.get('win_rate_pct')}% |")
lines += ['', '## Three-year system scenarios', '', '| Scenario | Trades closed | Net trading P/L | Possible trader payouts | Closed PF | Closed DD | Model status |', '|---|---:|---:|---:|---:|---:|---|']
for key,r in d['runs'].items():
    status = 'Halted: '+r['breach']['reason'] if r['breach'] else 'No closed breach; stop warning' if r['first_envelope_warning'] else 'No closed or stop-envelope breach'
    lines.append(f"| {key} | {r['closed_trades']} | {money(r['net'])} | {money(r['payout'])} | {r['profit_factor']:.2f} | {r['max_closed_drawdown_pct']:.2f}% | {status} |")
lines += ['', '## 1,000 paired resamples per scenario', '',
          'Joint four-week blocks sampled from the common 2021-09-05 to 2026-09-01 source window. Both evaluation phases follow the SAME continuing sampled timeline. Horizon = 730 calendar days TOTAL across phases, not per phase. FTMO itself has no time limit. Seed 20260913. Whole trade durations preserved across block joins; joins may create artificial overlaps. No within-EA independent reshuffle.', '',
          'Pass rates are conditional model frequencies, not verified real-world probabilities. Wilson intervals reflect sampling error only. Funded survival is assessed on the historical path, not by these challenge-only trials.', '',
          '| Scenario | Passed | Breached | Unfinished | Median days to pass, successes only | 95% sampling interval |', '|---|---:|---:|---:|---:|---|']
for k,m in d['monte_carlo'].items():
    lo,hi=m['wilson95_pct']
    lines.append(f"| {k} | {m['passed']} | {m['breach']} | {m['unfinished']} | {m['median_days_if_passed']} | {lo:.1f}–{hi:.1f}% |")
r=d['runs']['funded-lower-news']
c=d['runs']['challenge-lower-news']
lines += ['', '## Proposed 0.35% news: monthly system breakdown', '',
          'Main columns assume funded from the first day. Challenge payout column instead starts in evaluation; its own trades/phase accounting are in the separate scenario CSV/interactive selector. A payout can appear in a negative month after a deferred earlier claim; positive months can pay zero while recovering losses or waiting to be flat.', '',
          '| Month | Closed trades | Net USD | Return on initial $100k | Commission | Swap | Trader claim USD | End balance | Worst closed day loss | Stop-envelope day loss | Breach | Challenge-start claim |',
          '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|']
for m,cm in zip(r['monthly'],c['monthly']):
    status='Closed breach' if m['breach'] else 'Exposure warning' if m['max_envelope_daily_loss']>5000 or m['min_envelope']<90000 else 'None modelled'
    lines.append(f"| {m['month']} | {m['closed']} | {money(m['net'])} | {m['net']/1000:+.2f}% | {money(m['commission'])} | {money(m['swap'])} | {money(m['payout'])} | {money(m['end_balance'])} | {money(m['max_daily_loss'])} | {money(m['max_envelope_daily_loss'])} | {status} | {money(cm['payout'])} |")
lines += ['', f"Total proposed funded-start net: {money(r['net'])}; total trader claims: {money(r['payout'])}; mean per calendar month: {money(r['payout']/36)}; median monthly claim: {money(median(m['payout'] for m in r['monthly']))}; zero-claim months: {sum(m['payout']==0 for m in r['monthly'])}/36.",
          '', f"Challenge-start funded activation estimate: {c['funded_at']}; trader claims over the same overall window: {money(c['payout'])}. Evaluation fee/refund, tax, FX conversion and transfer delays are excluded.",
          '', '## Per-EA contribution to the concurrent safer portfolio', '',
          '| EA | Trades closed | Net contribution | Win rate | PF | Commission | Swap | Extra stress deduction |', '|---|---:|---:|---:|---:|---:|---:|---:|']
ea_totals=[]
for e in d['eas']:
    rows=[t for t in r['trades'] if t['slug']==e['slug']]
    wins=sum(max(0,t['net']) for t in rows); losses=sum(max(0,-t['net']) for t in rows)
    total=dict(slug=e['slug'], name=e['name'], closed=len(rows), net=sum(t['net'] for t in rows),
               win_rate=100*sum(t['net']>0 for t in rows)/max(1,len(rows)), pf=wins/losses if losses else None,
               commission=sum(t['commission'] for t in rows), swap=sum(t['swap'] for t in rows),extra=sum(t['extra_stress'] for t in rows))
    ea_totals.append(total)
    lines.append(f"| {e['name']} | {total['closed']} | {money(total['net'])} | {total['win_rate']:.1f}% | {total['pf']:.2f} | {money(total['commission'])} | {money(total['swap'])} | {money(total['extra'])} |")
lines += ['', 'Payout belongs to the account, not an individual EA: per-EA profit is attribution, not a separately withdrawable reward.', '', '## Sources', '',
          '- [FTMO 2-Step objectives](https://ftmo.com/en/trading-objectives/)',
          '- [FTMO rewards: timing, 80% share and rollover](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/)',
          '- [FTMO Swing leverage by asset class](https://ftmo.com/en/blog/a-few-answers-to-your-questions/)',
          '- [Current symbol specification page](https://ftmo.com/en/symbols/)', '',
          'Eight deterministic tests cover chronology, conservation, deficit recovery, terminal failure, shared margin, minimum entry days, news exemption and Prague DST. Full runs also assert monthly accounting identities, closed-trade ordering and no orphan positions.']
(OUT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(OUT/'per-ea-contributions.json').write_text(json.dumps(ea_totals,indent=2),encoding='utf-8')
visual={'eas':d['eas'], 'runs':{}}
for k,r in d['runs'].items():
    visual['runs'][k]={key:r[key] for key in ['net','payout','closed_trades','profit_factor','win_rate','breach','first_envelope_warning','funded_at']}
    visual['runs'][k]['monthly']=[{key:(round(val,2) if isinstance(val,float) else val) for key,val in m.items() if key!='ea'} | {'ea':{s:{k:round(v,2) if isinstance(v,float) else v for k,v in e.items()} for s,e in m['ea'].items()}} for m in r['monthly']]
(OUT/'visual-data.json').write_text(json.dumps(visual,separators=(',',':')),encoding='utf-8')
print('\n'.join(lines[lines.index('## Proposed 0.35% news: monthly system breakdown'):lines.index('## Sources')]))
