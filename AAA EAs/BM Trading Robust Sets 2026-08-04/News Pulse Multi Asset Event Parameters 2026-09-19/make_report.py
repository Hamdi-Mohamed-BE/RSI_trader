"""Build comparison from completed native reports, never screening headline returns."""
import json,re
from collections import defaultdict
from datetime import datetime,timezone
from research import ROOT,ASSETS,save,settings

def number(x,places=2):return 'N/A' if x is None else f'{x:,.{places}f}'
def read(p):return json.loads(p.read_text())
def amount(asset,x):return f'{x/.0001:g} pips' if asset=='EURUSD' else f'${x:g}'
def parameter_row(asset,kind,p,label):
 anchor=['Bid/Ask','Active M1 high/low','Previous closed M1 high/low'][int(p[1])]
 trail='Off' if p[5]==0 else f'{p[5]:g}R trigger / {amount(asset,p[6])} distance'
 tp='None' if p[4]==0 else f'{p[4]:g}R'
 return f'| {asset} | {label} | {kind} | {p[0]:g}s | {anchor} | {amount(asset,p[2])} | {amount(asset,p[3])} | {tp} | {trail} | {p[7]:g}s |'

def audit(asset,variant):
 out=ROOT/'native'/(asset+variant);stats=read(out/'stats.json');trades=read(out/'trades.json')
 families={};months=defaultdict(lambda:dict(trades=0,net_usd=0.,commission=0.,swap=0.));by_event=defaultdict(list)
 for t in trades:
  by_event[t['event_epoch']].append(t)
  m=months[t['close_time'][:7]];m['trades']+=1;m['net_usd']+=t['net_profit'];m['commission']+=t['commission'];m['swap']+=t['swap']
 for k in ('NFP','CPI','FOMC'):
  rows=[t for t in trades if t['event_kind']==k]
  pos=sum(max(0,t['net_profit']) for t in rows);neg=sum(max(0,-t['net_profit']) for t in rows)
  families[k]=dict(trades=len(rows),net_usd=sum(t['net_profit'] for t in rows),win_rate=100*sum(t['net_profit']>0 for t in rows)/len(rows) if rows else 0,pf=pos/neg if neg else None)
 balance=10000.;max_trade_loss=0.;worst_event=0.;events=[]
 for epoch,rows in sorted(by_event.items()):
  pnl=sum(t['net_profit'] for t in rows)
  max_trade_loss=max(max_trade_loss,max(0,-min(t['net_profit'] for t in rows))/balance*100)
  worst_event=max(worst_event,max(0,-pnl)/balance*100)
  events.append(dict(epoch=epoch,kind=rows[0]['event_kind'],event_start_closed_balance=balance,net_usd=pnl,trades=len(rows)))
  balance+=pnl
 assert abs(balance-stats['final_balance'])<.10
 journal=(out/'journal.txt').read_text()
 failures={s:journal.lower().count(s) for s in ('not enough money','invalid price','invalid stops','invalid expiration','market closed')}
 return dict(stats=stats,by_family=families,monthly=dict(months),events=events,max_single_trade_net_loss_pct_event_start_balance=max_trade_loss,worst_event_net_loss_pct_event_start_balance=worst_event,journal_phrase_counts=failures)

def main():
 variants=['Baseline','Fitted','Train','BaselineHoldout','TrainHoldout','BaselineDelay250','FittedDelay250']
 summary={a:{v:audit(a,v) for v in variants} for a in ASSETS}
 recommendations={
  'XAG':'WATCH ONLY: earlier-selected combination merits additional testing, but materially higher equity drawdown and very tight stops prevent recommending automatic replacement.',
  'BTC':'KEEP CURRENT: earlier-selected combination underperformed current settings in the later period and increased risk; the giant full-year fit is not validation.',
  'EURUSD':'WATCH ONLY / INACTIVE: earlier-selected combination merits further testing, but higher drawdown and a small sample do not justify adding it back automatically.',
 }
 lines=['# News Pulse - XAG, BTC and EURUSD event-family optimization','',
 'Research window: **2025-09-19 inclusive to 2026-09-19 exclusive**. Independent USD 10,000 accounts, Exness-MT5Trial16, leverage 1:2000, M1, native MT5 Model 4. Not FTMO. Both pending directions remain enabled. Risk stays 0.75% equity planned per side; it is not a realized loss cap.','',
 '## Decision','',
 'No BAT, active EA, attached chart, website or portfolio settings were changed. EURUSD remains inactive. Do not deploy the maximum fitted return as if it were validated.','']
 for a in ASSETS:lines.append(f'- **{a}:** {recommendations[a]}')
 lines+=['','## One-year native MT5 comparison','',
 'The fitted combination was selected using the full year, including the later validation dates. Its performance is hindsight/in-sample, not an out-of-sample expectation. Earlier-selected uses only releases before 2026-05-19 for parameter selection; its full-year total still includes training data.','',
 '| Asset | Version | Return | Final USD | Trades | Net win rate | Net PF | Max equity DD | Commission | Swap |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for a in ASSETS:
  for v,label in [('Baseline','Current / archived EURUSD'),('Fitted','Full-year fitted'),('Train','Earlier-selected, whole-year replay')]:
   s=summary[a][v]['stats'];lines.append(f"| {a} | {label} | {s['return_pct']:+,.2f}% | ${s['final_balance']:,.2f} | {s['trades']} | {s['win_rate_pct']:.2f}% | {number(s['profit_factor'])} | {s['max_drawdown_pct']:.2f}% | ${s['commission']:,.2f} | ${s['swap']:,.2f} |")
 lines+=['','## Chronological later-period check','',
 '**2026-05-19 inclusive to 2026-09-19 exclusive**, each alternative restarts with $10,000. These runs report **100% real ticks**. Only the earlier-selected combination is compared here; the full-year fit is not eligible for an out-of-sample claim. There are only 11 release dates, so evidence is limited.','',
 '| Asset | Version | Return | Final USD | Trades | Net win rate | Net PF | Max equity DD |','|---|---|---:|---:|---:|---:|---:|---:|']
 for a in ASSETS:
  for v,label in [('BaselineHoldout','Current / archived EURUSD'),('TrainHoldout','Earlier-selected')]:
   s=summary[a][v]['stats'];assert s['history_quality']=='100% real ticks'
   lines.append(f"| {a} | {label} | {s['return_pct']:+,.2f}% | ${s['final_balance']:,.2f} | {s['trades']} | {s['win_rate_pct']:.2f}% | {number(s['profit_factor'])} | {s['max_drawdown_pct']:.2f}% |")
 lines+=['','## Exact selected event settings','',
 'XAG/BTC dollar distances mean symbol price movement, not account cash risk. EURUSD distances are displayed in pips (0.0001). Candle high/low anchors use a current-spread adjustment for the buy side. No-TP and no-trailing are independent settings. Each family uses one reusable rule, not one setting for each historical release.','',
 '| Asset | Selection | Event | Place before | Anchor | Entry offset | SL distance | TP | Trailing | Close after event |','|---|---|---|---:|---|---:|---:|---|---|---:|']
 for a in ASSETS:
  selected=read(ROOT/a/'selected.json')
  for mode,label in [('full','Full-year fitted'),('train','Earlier-selected')]:
   for kind in ('NFP','CPI','FOMC'):lines.append(parameter_row(a,kind,selected[kind][mode]['params_price'],label))
 lines+=['','## Current baseline settings','',
 '| Asset | Place before | Entry offset | SL | TP | Trail trigger | Trail distance | Close after |','|---|---:|---:|---:|---|---:|---:|---:|']
 for a in ASSETS:
  s=settings(a);lines.append(f"| {a} | {s['InpPlacementLeadSeconds']}s | {amount(a,float(s['InpEntryOffsetPrice']))} | {amount(a,float(s['InpStopLossPrice']))} | None | {s['InpTrailStartR']}R | {amount(a,float(s['InpTrailDistancePrice']))} | {s['InpForceCloseSecondsAfterEvent']}s |")
 lines+=['','## Native execution-delay sensitivity','',
 'Fixed 250ms tester execution delay changes placement and subsequent paths; it may increase or decrease returns. This is not a guaranteed live-news latency/slippage model.','',
 '| Asset | Version, 250ms | Return | Trades | Net win rate | PF | Max equity DD |','|---|---|---:|---:|---:|---:|---:|']
 for a in ASSETS:
  for v,label in [('BaselineDelay250','Current'),('FittedDelay250','Full-year fitted')]:
   s=summary[a][v]['stats'];lines.append(f"| {a} | {label} | {s['return_pct']:+,.2f}% | {s['trades']} | {s['win_rate_pct']:.2f}% | {number(s['profit_factor'])} | {s['max_drawdown_pct']:.2f}% |")
 lines+=['','## Screening cost stress - estimates, not native headline results','',
 'Historical bid/ask spread is already in the paths. Extra spread and adverse entry/SL/forced-close slippage are added below; TP fills remain at the target. Screening does not fully model margin, order rejection or liquidity. Consequently it can materially diverge from native results, especially when small stops imply large BTC positions. Approximate screening DD is not MT5 equity DD.','',
 '| Asset | Scenario | Extra spread | Adverse slippage | Placement delay | Current return | Fitted return | Earlier-selected return |','|---|---|---:|---:|---:|---:|---:|---:|']
 for a in ASSETS:
  c=read(ROOT/a/'screening-comparison.json');space=read(ROOT/a/'search-space.json')
  for k in ('stress','severe'):
   x=space[k];lines.append(f"| {a} | {k} | {amount(a,x['extra_spread'])} | {amount(a,x['adverse_slippage'])} | {x['delay_ms']}ms | {c['baseline'][k]['return_pct']:+,.2f}% | {c['full'][k]['return_pct']:+,.2f}% | {c['train'][k]['return_pct']:+,.2f}% |")
 lines+=['','## Later-period cost stress and local parameter stability','',
 'These are supplementary Python sensitivity estimates, not additional native MT5 runs. They did not change the previously frozen selections. The native later-period comparison above remains the execution reference.','',
 '| Asset | Current moderate | Earlier-selected moderate | Current severe | Earlier-selected severe |','|---|---:|---:|---:|---:|']
 for a in ASSETS:
  sensitivity=read(ROOT/a/'sensitivity.json');summary[a]['sensitivity']=sensitivity;c=sensitivity['holdout_cost_stress']
  lines.append(f"| {a} | {c['baseline']['moderate']['return_pct']:+,.2f}% | {c['train']['moderate']['return_pct']:+,.2f}% | {c['baseline']['severe']['return_pct']:+,.2f}% | {c['train']['severe']['return_pct']:+,.2f}% |")
 lines+=['','BTC earlier-selected turns negative with the additional cost assumptions while current BTC remains positive. This reinforces keeping current BTC.','',
 'Local neighbor diagnostics vary one selected timing/distance by -20% or +20%, rounding to broker precision and clipping to the tested timing limits. The saved results are diagnostics, not a new optimization or probability estimate. Earlier-selected EURUSD FOMC has a negative-return neighbor; the strongest headline alone is not a stable-parameter guarantee.','',
 '## Realized risk and coverage audit','',
 'Per-trade and per-event loss percentages below use the event-start closed balance, not exact floating equity at each entry. They demonstrate why the planned 0.75% per side / 1.50% per event does not cap realized loss. Dollar profits also compound; event-family contributions are not independent portfolio returns.','',
 '| Asset | Version | Real ticks | Expected / attempted / placed releases | Worst single net loss / event-start balance | Worst net losing event |','|---|---|---|---|---:|---:|']
 for a in ASSETS:
  for v in ('Baseline','Fitted','Train'):
   x=summary[a][v];s=x['stats'];cal=s['calendar'];lines.append(f"| {a} | {v} | {s['history_quality']} | {cal['expected']} / {cal['attempted']} / {cal['placed']} | {x['max_single_trade_net_loss_pct_event_start_balance']:.2f}% | {x['worst_event_net_loss_pct_event_start_balance']:.2f}% |")
 lines+=['','## Event-family contributions: native combined account','',
 '| Asset | Event | Current trades | Current net USD | Fitted trades | Fitted net USD | Fitted net win rate |','|---|---|---:|---:|---:|---:|---:|']
 for a in ASSETS:
  for k in ('NFP','CPI','FOMC'):
   b=summary[a]['Baseline']['by_family'][k];f=summary[a]['Fitted']['by_family'][k]
   lines.append(f"| {a} | {k} | {b['trades']} | ${b['net_usd']:,.2f} | {f['trades']} | ${f['net_usd']:,.2f} | {f['win_rate']:.2f}% |")
 for a in ASSETS:
  lines+=['',f'## {a} monthly realized cashflow','',
   '| Month | Current trades | Current net USD | Fitted trades | Fitted net USD | Earlier-selected trades | Earlier-selected net USD |','|---|---:|---:|---:|---:|---:|---:|']
  months=sorted(set().union(*(summary[a][v]['monthly'] for v in ('Baseline','Fitted','Train'))))
  for m in months:
   row=[]
   for v in ('Baseline','Fitted','Train'):
    x=summary[a][v]['monthly'].get(m,dict(trades=0,net_usd=0));row.extend([str(x['trades']),f"${x['net_usd']:,.2f}"])
   lines.append('| '+m+' | '+' | '.join(row)+' |')
 lines+=['','## Limitations and next decision','',
 '- Full-year results report 71% real ticks; the remaining ticks were generated by MT5. Do not describe them as a fully real-tick year.',
 '- The huge fitted returns are not forecasts. The search favors very tight stops and has only 7/7/5 earlier-period NFP/CPI/FOMC releases for selection, respectively.',
 '- Baseline replay matches native trade counts and net wins, with final balance differences below $0.10. This does not prove candidate execution or equity-drawdown fidelity.',
 '- The equity path, contract, fees, margin checks and accepted orders in native reports take precedence over Python screening.',
 '- Calendar source/vintage caveats from the XAU study remain. No post-release actual value is used in the trading rule. Fee calibration uses the asset baseline reports and is an empirical cost assumption, not a reconstructed point-in-time commission tariff.',
 '- The chronological split enforces earlier-only parameter selection in code, but these dates have already been researched elsewhere. It is not a pristine prospective blind experiment.',
 '- Nominal 0.75% stop sizing did not cap realized single-trade loss: the fitted XAG and EURUSD tests include losses above 8% of event-start balance. Gaps and original SL geometry are material risks; do not use these as prop-safe settings.',
 '- Keeping both sides means both are eligible, not that a broker must accept or fill both. Rejected orders and unavailable quotes stay in the audit.',
 '- No independent cross-broker validation, live liquidity proof, long-window reoptimization or prop-firm pass simulation was performed.',
 '- These are separate per-asset accounts, not a combined portfolio on shared capital.',
 '- Prefer further forward validation and a separate approved risk study before promoting XAG/EURUSD. Keep current BTC based on the later-period comparison.',
 '', '## Artifacts','',
 'Each native run retains MQ5/EX5, compile log, exact SET, tester configuration, report/images, journal, parsed stats and individual trades. Asset directories retain raw quotes, causal data-quality checks, cost calibration, full candidate arrays, top-100 rankings and selected settings. `SUMMARY.json` contains all native metrics and monthly/event detail.',
 '', 'Production EAs/BATs and the website have intentionally not been updated by this research.']
 summary['_metadata']=dict(created_utc=datetime.now(timezone.utc).isoformat(),manifest=read(ROOT/'manifest.json'),recommendations=recommendations)
 save(ROOT/'SUMMARY.json',summary);(ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print('WROTE',ROOT/'RESULTS.md')
 for a in ASSETS:print(a,{v:summary[a][v]['stats'] for v in ('Baseline','Fitted','TrainHoldout')})

if __name__=='__main__':main()
