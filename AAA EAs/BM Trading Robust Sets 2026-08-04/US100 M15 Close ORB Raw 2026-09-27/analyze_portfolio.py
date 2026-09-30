"""Native ORB audits and matched historical/FTMO overlays; never live trading."""
from pathlib import Path
import hashlib,importlib.util,json,random,sys
from collections import defaultdict
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
EXIT=BASE/'FTMO Exit Management Research 2026-09-27';PREV=EXIT/'EMA Trailing ORB Half R Followup'
spec=importlib.util.spec_from_file_location('eight_ea_followup',PREV/'run.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
import audit_native as audit
a=f.a;c=f.c;N=1000;SEED=20260926;HS=c.END-180*c.DAY
J=next(x for x in f.CONFIGS if x['id']=='J')
CONFIGS=[dict(id='J',name='Existing eight EAs',target=None),dict(id='O50',name='Eight + US100 ORB 0.50R',target='half'),dict(id='O33',name='Eight + US100 ORB one-third R',target='third')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,obj):c.save(ROOT/name,obj)
def fmt(x,d=2):return '—' if x is None else f'{x:,.{d}f}'
def usd(x):return ('−' if x<0 else '+')+'$'+fmt(abs(x))

def write_report(out):
 lines=['# US100 M15 close-confirmed ORB — raw six-month test','',
 '27 September 2026. Research only: no production EA, BAT, website, live terminal or account changes.','',
 '## Rules frozen before testing','',
 '- US100 via the isolated Exness tester\'s USTEC symbol. New York time with US DST, broker history clock UTC.',
 '- Opening range is the high/low of 09:30–09:45. Wait for the first LATER completed M15 close strictly above/below it. Earliest signal confirmation is 10:00 NY, not 09:45.',
 '- Market entry on the next available tick after confirmation. Long stop exactly at that breakout candle\'s low; short stop at its high. No additional buffer, EMA/DI/news filter, retest, trailing or breakeven.',
 '- Two alternatives, separately tested: +0.50R profit target and +1/3R. These are small positive targets, not negative profits. Cost-free two-outcome breakeven win rates are 66.67% and 75.00%, respectively.',
 '- Defaults supplied by us: one qualifying signal attempt / at most one filled trade per New York date; remaining positions close requested from 15:55 NY; no fresh entry at/after that time. Invalid stops/session unavailability are skipped, never widened. Exit attempts check session availability and are throttled to once per minute; unavailable markets can delay an exit.',
 '- Native starting capital $10,000, risk target 1% of equity, existing upward broker-lot rounding convention (actual rounded risk may exceed 1%), real-tick Model 4, 150 ms delay, native spread/commission/swap. Isolated tester leverage is 1:2000; these native returns are not FTMO account tests.',
 '- Two strategy configurations only; no parameter search. Smoke check plus two full windows per target. One initial smoke run required a report-parser datetime-format correction; EA logic was unchanged.','',
 '## Latest six calendar months — native MT5','',
 '**27 March–26 September 2026 inclusive** (end-exclusive 27 September). Native maximum relative equity drawdown below includes floating equity. PF is calculated from complete trade net P&L including commission/swap; the native report\'s deal-based PF is retained separately in RESULTS.json.','',
 '| Target | Trades | /30 days | /weekday | Net USD | Return | Win rate | Net PF | Max equity DD | Max win/loss streak |',
 '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
 for target in ('half','third'):
  z=out['native']['latest6m-'+target]['stats'];wl=z['max_win_loss_streak']
  lines.append(f"| {'0.50R' if target=='half' else '1/3R'} | {z['trades']} | {fmt(z['trades_per_30_days'])} | {fmt(z['trades_per_weekday'])} | {usd(z['net_profit'])} | {fmt(z['return_pct'])}% | {fmt(z['win_rate_pct'])}% | {fmt(z['profit_factor'])} | {fmt(z['relative_equity_drawdown_pct'])}% | {wl[0]}/{wl[1]} |")
 lines+=['','### Latest-window monthly native results','',
 '| Month | 0.50R trades | 0.50R win rate | 0.50R net | 1/3R trades | 1/3R win rate | 1/3R net |','|---|---:|---:|---:|---:|---:|---:|']
 months=sorted(set().union(*(out['native']['latest6m-'+t]['stats']['monthly'] for t in ('half','third'))))
 for month in months:
  cells=[]
  for target in ('half','third'):
   z=out['native']['latest6m-'+target]['stats']['monthly'].get(month,dict(trades=0,wins=0,net=0.))
   cells += [str(z['trades']),fmt(100*z['wins']/z['trades'] if z['trades'] else None)+'%',usd(z['net'])]
  lines.append('| '+month+' | '+' | '.join(cells)+' |')
 lines+=['','March and September are partial months. Native profits compound at the stated sizing; monthly cash figures are not payout income.','',
 '### Latest-window cost sensitivity at portfolio sizing','',
 'Each ORB alone, fixed-dollar ceiling $71.43, strict lot rounding down and the existing internal admission guards. This is an offline ledger overlay, not a fresh native run. Stress assumptions are illustrative, not measured FTMO fill calibration.','',
 '| Target | Cost case | Trades | /30 days | /weekday | Net USD | Return | Win rate | PF | Reserve DD proxy | Max win/loss |',
 '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
 for z in out['latest_overlay']:
  h=z['result'];days=out['native']['latest6m-'+z['target']]['stats']['weekdays']
  lines.append(f"| {z['target']} | {'Stress' if z['stress'] else 'Reference'} | {h['trades']} | {fmt(h['trades']/184*30)} | {fmt(h['trades']/days)} | {usd(h['balance']-10000)} | {fmt((h['balance']-10000)/100)}% | {fmt(h['win_rate'])}% | {fmt(h['pf'])} | {fmt(h['model_dd_pct'])}% | {h['max_win_streak']}/{h['max_loss_streak']} |")
 lines+=['','## Effect on the current eight-EA setup','',
 'The control remains Gold Value Area raw, Nasdaq Overnight, EMA3 Safe, ORB Volume Profile 0.75R, News Pulse XAU/XAG, plus the separate EMA M15 ATR and ORB Volume Profile 0.50R copies. Nasdaq 5M DI remains excluded. O50/O33 add ONE new US100 ORB version each; neither replaces the existing gold ORBs, and the two US100 variants are not combined.','',
 '**Matched comparison window: 4 March–30 August 2026**, the prior portfolio study\'s 180 days / 128 weekdays. This differs from the latest six-month standalone window above. The new ORB has fresh aligned native runs from 2 March for the same 26-week Monte Carlo pool; no September-only ORB trades are added to an August-ending portfolio.','',
 'Same fixed-dollar ordinary risk ceiling $71.43, $10/news side, strict 0.01-lot rounding down, $300 daily admission budget, $225 open initial-risk cap, $150 correlated-metal/per-symbol cap, $9,200 projected buffer, maximum seven entries/day, three-loss admission stop and 80% margin ceiling. Both news sides remain possible with full risk/margin reservations. USTEC margin modeled 1:15; actual FTMO platform fills/margin are not verified here. Original strategies retain priority on simultaneous admissions.','']
 for stress in (True,False):
  lines+=['### '+('Stressed costs' if stress else 'Reference costs'),'','| Portfolio | Trades | /30 days | /weekday | Net USD | Return | Win rate | PF | Closed DD | Reserve DD proxy | Max win/loss |',
   '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
  for case in out['cases']:
   if case['stress']!=stress:continue
   h=case['historical'];q=case['frequency']
   lines.append(f"| {case['id']} | {h['trades']} | {fmt(q['trades_per_30_days'])} | {fmt(q['trades_per_weekday'])} | {usd(h['balance']-10000)} | {fmt((h['balance']-10000)/100)}% | {fmt(h['win_rate'])}% | {fmt(h['pf'])} | {fmt(h['closed_dd_pct'])}% | {fmt(h['model_dd_pct'])}% | {h['max_win_streak']}/{h['max_loss_streak']} |")
 lines+=['','Portfolio DD is an initial-stop-reserve approximation, NOT actual combined tick equity. Native standalone equity DD and portfolio reserve DD are different measures.','',
 '## Modeled FTMO challenge outcomes — stressed costs','',
 '1,000 matched 180-day paths per portfolio/cost case; 6,000 total. Joint-week sampling with replacement, 26 source weeks, unchanged seed 20260926. Start-date timing and administration assumptions are the same as the previous study.','',
 '| Portfolio | Funded 30d | Paid 60d | Paid 120d | Funded 180d | Paid 180d | Breached before first reward | Median P1 days* | Median P2 days* | Median funded days* | Median paid days* |',
 '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
 for case in out['cases']:
  if not case['stress']:continue
  hh={v['days']:v for v in case['summary']['horizons']};t=case['summary']['timing']
  lines.append(f"| {case['id']} | {fmt(hh[30]['funded_pct'],1)}% | {fmt(hh[60]['payout_pct'],1)}% | {fmt(hh[120]['payout_pct'],1)}% | {fmt(hh[180]['funded_pct'],1)}% | {fmt(hh[180]['payout_pct'],1)}% | {fmt(hh[180]['breach_before_first_reward_pct'],1)}% | "+' | '.join(fmt(t[k]['median'],1) for k in ('phase1_days_among_phase1_passers','phase2_days_from_availability_among_phase2_passers','funded_days_from_purchase','payout_days_from_purchase'))+' |')
 lines+=['','*Conditional on milestone completion within 180 days. Phase 2 starts at account availability; others from purchase. Zero observed breaches is not zero real risk. Unfinished or risk-blocked accounts are not counted as blown.','',
 '| Portfolio | Payout delta at 180d versus J | Matched MC-only 95% interval | Paths touching internal buffer | P95 reserve DD |','|---|---:|---:|---:|---:|']
 for case in out['cases']:
  if not case['stress']:continue
  p=case['paired_paid180'];iv=p['paired_mc_only_interval']
  lines.append(f"| {case['id']} | {fmt(p['delta_percentage_points'],1)} pp | {fmt(iv[0],1)} to {fmt(iv[1],1)} pp | {case['summary']['paths_touching_internal_total_buffer']}/{N} | {fmt(case['aggregate180']['p95_stop_envelope_dd_pct'])}% |")
 lines+=['','## Marginal US100 trades in the combined account — stress','',
 '| Addition | Admitted trades | /30 days | /weekday | Net USD | Win rate | PF | Max win/loss |','|---|---:|---:|---:|---:|---:|---:|---:|']
 for case in out['cases']:
  if not case['stress'] or not case['target']:continue
  key='us100-m15-close-orb/'+case['target'];h=case['historical'];v=h['by_ea'].get(key)
  if not v:continue
  ws=ls=mw=ml=0
  for t in h['log']:
   if t['ea']!=key:continue
   ws=ws+1 if t['net_profit']>0 else 0;ls=ls+1 if t['net_profit']<0 else 0;mw=max(mw,ws);ml=max(ml,ls)
  lines.append(f"| {case['id']} | {v['trades']} | {fmt(v['trades']/6)} | {fmt(v['trades']/128)} | {usd(v['net'])} | {fmt(100*v['wins']/v['trades'])}% | {fmt(v['positive']/v['negative'] if v['negative'] else None)} | {mw}/{ml} |")
 lines+=['','The total portfolio change can differ from the added ORB\'s own profit because it consumes shared risk/margin and can displace other trades. Full per-EA contributions and rejected-admission counts are in RESULTS.json.','',
 '## Important limits','',
 '- This is a two-preset raw test, not full optimization or pipeline validation. No out-of-sample claim and no production promotion.',
 '- FTMO overlay retains 10%/5% targets, four entry days per phase, 5% daily and 10% static loss, Prague reset; two business days between phases, five to funded activation, reward at least 14 days after first funded entry when flat and $25 profitable, four business days to receipt, 80% share. Administrative timing is assumed.',
 '- Reference retains native fills with commission floors. Stress reduces gross winners 10%, worsens gross losses 10%, adds two Nasdaq points / $0.20 ordinary gold / $1 gold news / $0.04 silver, doubles negative swaps and adds carry reserve. This is an unchanged hypothetical stress scenario, not measured FTMO slippage.',
 '- Saved Exness native ledgers resized/gated together are not a native FTMO multi-EA test. Skipping an entry may change an EA\'s later state, which the overlay does not re-simulate.',
 '- The existing news presets were fitted to this history; 26 weekly blocks are a small selected sample. Monte Carlo repetitions are not independent new market evidence, and do not preserve the actual future macro release calendar.',
 '- Outcomes stop at first reward request or day 180, not lifetime funded-account survival. Reserve DD is not observed floating-equity DD, and gaps can exceed planned stop risk.',
 '- News straddle eligibility still needs FTMO clarification under forbidden gap-trading practices. No regulatory/contract disqualification probability is modeled.','',
 '## Evidence','',
 'run-config.json freezes rules; BUILD.json captures the compiled source/binary hashes. native/* retains compressed reports/journals, native trades, exported M15 bars and independent AUDIT.json files. Every entry is checked against an independent Python reconstruction of the first completed M15 breakout, opening range, stop, target, New York DST and one-trade-per-day rule. PORTFOLIO_FROZEN.json records comparison evidence, RESULTS.json stores all compact paths and detailed historical ledgers; CHECKS.json records exact eight-EA baseline parity and validation.','',
 '- [FTMO objectives and account comparison](https://ftmo.com/en/comparison-table/)',
 '- [FTMO prohibited practices](https://ftmo.com/en/forbidden-trading-practices/)','']
 (ROOT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')

def main():
 c.verify_sources();needed=list(dict.fromkeys((n,v) for n,v,_ in J['members']))
 sources={str(p):sha(p) for p in (ROOT/'ORB15Close.mq5',ROOT/'ORB15Close.ex5',ROOT/'run-config.json',ROOT/'BUILD.json',ROOT/'audit_native.py',ROOT/'analyze_portfolio.py',PREV/'run.py',PREV/'RESULTS.json',EXIT/'analyze.py',c.ROOT/'six_ea.py',c.ROOT/'compare.py',c.SOURCE/'simulate.py',c.SOURCE/'prepare.py')}
 for n,v in needed:
  for filename in ('run.json','trades.json','report.htm.gz','journal.txt.gz'):
   p=EXIT/'native'/(n+'-'+v)/filename;sources[str(p)]=sha(p)
 for period in ('latest6m','aligned'):
  for target in ('half','third'):
   for filename in ('run.json','trades.json','report.htm.gz','journal.txt.gz','bars.csv'):
    p=ROOT/'native'/(period+'-'+target)/filename;sources[str(p)]=sha(p)
 save('PORTFOLIO_FROZEN.json',dict(configs=CONFIGS,seed=SEED,paths=N,risk=500/7,news_risk=10.,source_weeks=26,historical_start=c.iso(HS),end=c.iso(c.END),hashes=sources))
 out=dict(native={},latest_overlay=[],cases=[]);orb={}
 for period in ('latest6m','aligned'):
  for target in ('half','third'):
   rows,info=audit.audit(period,target);orb[period,target]=rows;out['native'][period+'-'+target]=info
   print('AUDITED',period,target,json.dumps(info['stats']),flush=True)
 for target in ('half','third'):
  for stress in (False,True):
   ns=a.six.make_engine('strict_round_down');start=c.datetime(2026,3,27,tzinfo=c.UTC).timestamp();end=c.datetime(2026,9,27,tzinfo=c.UTC).timestamp()
   h=ns['replay']([dict(t) for t in orb['latest6m',target]],[],start,end,stress=stress,challenge=False,detail=True)
   a.six.reconcile(h,True);out['latest_overlay'].append(dict(target=target,stress=stress,result=h))
 native={(n,v):a.load_case(n,v) for n,v in needed};old=c.read(PREV/'RESULTS.json')
 checks=dict(inherited=a.six.checks(c.read(c.SOURCE/'prepared.json')),native_audits=[v['validation'] for v in out['native'].values()],baseline_parity=[])
 for path,info in a.CFG['source_files'].items():assert sha(Path(path))==info['sha256']
 rng=random.Random(SEED);samples=[[rng.randrange(26) for _ in range(26)] for _ in range(N)];controls={}
 for cfg in CONFIGS:
  data,labels=f.body_data(J,native)
  if cfg['target']:
   key='us100-m15-close-orb/'+cfg['target'];data['rows'][key]=orb['aligned',cfg['target']];labels[key]=cfg['name'].split(' + ')[-1]
  keys=list(data['rows']);weeks=c.pool(data,a.ph.POOL_START,26)
  for stress in (False,True):
   ns=a.six.make_engine('strict_round_down');sims=[]
   for sample in samples:
    rr,pp=c.sample_rows(data,keys,a.ph.POOL_START,weeks,sample,c.START,c.START+180*c.DAY)
    sims.append(ns['replay'](rr,pp,c.START,c.START+180*c.DAY,stress=stress,news_risk=10.))
   rr=[dict(t) for rows in data['rows'].values() for t in rows if HS<=t['op']<c.END and t['cl']<c.END];pp=[dict(p) for p in data['placements'] if HS<=p['op']<c.END]
   hist=ns['replay'](rr,pp,HS,c.END,stress=stress,news_risk=10.,challenge=False,detail=True);hc=ns['replay'](rr,pp,HS,c.END,stress=stress,news_risk=10.,detail=True)
   summary=a.ph.summarize(sims,ns);paths=a.a.compact_paths(sims)
   if cfg['id']=='J':
    prev=next(x for x in old['cases'] if x['id']=='J' and x['stress']==stress)
    assert hist==prev['historical'] and summary==prev['summary'] and paths==prev['paths']
    controls[stress]=sims;checks['baseline_parity'].append(dict(stress=stress,historical=True,summary=True,paths=N))
   case=dict(**cfg,stress=stress,labels=labels,historical=hist,historical_challenge=hc,frequency=f.freq(hist),summary=summary,aggregate180=c.summarize(sims,180),paths=paths,
    paired_paid120=a.a.paired(controls[stress],sims,'receipt_at',120),paired_paid180=a.a.paired(controls[stress],sims,'receipt_at',180))
   f.verify_run(case,ns);out['cases'].append(case);save('RESULTS.json',out);write_report(out)
   print('PORTFOLIO',cfg['id'],stress,json.dumps(dict(net=hist['balance']-10000,trades=hist['trades'],wr=hist['win_rate'],pf=hist['pf'],dd=hist['model_dd_pct'],paid180=summary['horizons'][-1]['payout_pct'])),flush=True)
 for p,digest in sources.items():assert sha(Path(p))==digest,p
 for path,info in a.CFG['source_files'].items():assert sha(Path(path))==info['sha256']
 assert len(out['cases'])==6
 checks.update(paths_checked=6000,case_count=6,unchanged_evidence_files=len(sources),unchanged_production_sources=len(a.CFG['source_files']))
 save('CHECKS.json',checks);print('COMPLETE: four full native audits, six portfolio cases, 6000 matched paths, exact baseline parity.',flush=True)
if __name__=='__main__':main()
