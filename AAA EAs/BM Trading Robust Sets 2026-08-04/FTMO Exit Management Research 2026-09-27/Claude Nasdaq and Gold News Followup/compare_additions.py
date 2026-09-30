"""Frozen offline shared-account comparisons; no trading API or deployment."""
from pathlib import Path
import gzip,hashlib,importlib.util,json,random,re,statistics
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parent
EXIT=ROOT.parent
PREV=EXIT/'EMA Trailing ORB Half R Followup'
spec=importlib.util.spec_from_file_location('previous_followup',PREV/'run.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
a=f.a;c=f.c
N=1000;SEED=20260926;HS=c.END-180*c.DAY
DI=a.a.DI
J=next(x for x in f.CONFIGS if x['id']=='J')
CONFIGS=[
 dict(id='J',name='Existing eight EAs',members=J['members'],di=False,news_risk=10.),
 dict(id='M',name='Eight EAs + Claude Nasdaq 5M DI',members=J['members'],di=True,news_risk=10.),
 dict(id='N10',name='Gold News Pulse only, $10 per order',members=[('xau','native',None)],di=False,news_risk=10.),
 dict(id='N30',name='Gold News Pulse only, $30 per order',members=[('xau','native',None)],di=False,news_risk=30.),
 dict(id='N50',name='Gold News Pulse only, $50 per order',members=[('xau','native',None)],di=False,news_risk=50.),
]
def save(name,x):c.save(ROOT/name,x)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load_di():
 p=ROOT/'native-di';meta=c.read(p/'run.json');ts=c.read(p/'trades.json')
 assert meta['ok'] and meta['model']==4 and meta['delay_ms']==150
 assert meta['expert_sha256']=='49c4f03622a8ec7fb8e70db990a2f19b3006b5641aeb915a5d7f2454f26bab35'
 body=a.report_text(p/'report.htm.gz');oo=a.orders(body);rr=[]
 assert len(ts)==meta['metrics']['trades']==90
 assert abs(sum(x['net_profit'] for x in ts)-meta['metrics']['net_profit'])<.1
 for t in ts:
  op,cl=a.epoch(t['open_time']),a.epoch(t['close_time']);matches=oo[op,t['symbol'],t['side']]
  assert len(matches)==1 and cl>op and t['volume']>0
  stop=matches[0]['stop'];sign=1 if t['side']=='Long' else -1
  assert sign*(t['open_price']-stop)>0
  assert abs(sign*(t['close_price']-t['open_price'])*t['volume']-t['gross_profit'])<.03
  assert abs(t['gross_profit']+t['commission']+t['swap']-t['net_profit'])<.03
  rr.append(dict(t,key=DI,news=False,op=op,cl=cl,stop=stop,target=matches[0]['target'],unit_risk=abs(t['open_price']-stop),
                 risk_quality='native_initial_order',unit_gross=t['gross_profit']/t['volume'],unit_comm=t['commission']/t['volume'],unit_swap=t['swap']/t['volume']))
 dd=re.search(r'>\s*Equity Drawdown Relative:\s*</td>\s*<td[^>]*>\s*<b>(.*?)</b>',body,re.I|re.S)
 assert dd;meta['metrics']['relative_equity_drawdown_pct']=float(re.search(r'([\d.]+)%',a.clean(dd.group(1))).group(1))
 journal=gzip.decompress((p/'journal.txt.gz').read_bytes()).decode()
 assert 'testing with execution delay 150 milliseconds' in journal
 meta['operational_caution']='Market-closed close retries on 6 March; the 6 March long actually exited on 8 March. These native outcomes are retained; this is not a clean deployment-readiness test.'
 meta['weekend_hold']=next(t for t in ts if t['open_time'].startswith('2026-03-06'))
 return rr,meta

def validate(case):
 h=case['historical'];budget=case['config']['news_risk']
 a.six.reconcile(h,False)
 assert h['max_open_risk']<=225+1e-7 and h['max_daily_entries']<=7
 assert h['counts'].get('opened',0)==h['trades']
 for t in h['log']:
  assert 0<t['initial_risk']<=(budget if t['ea'] in c.NEWS else 500/7)+1e-7
  assert abs(t['lots']/.01-round(t['lots']/.01))<1e-7
 for hz in case['summary']['horizons']:
  assert sum(hz['counts'].values())==N
  assert hz['first_payout_received']<=hz['funded']<=hz['both_phases_passed']<=hz['phase1_passed']<=N
 assert len(case['paths'])==N

def frequency(hist):
 if hist['trades']:return f.freq(hist)
 blank=dict(hist,counts={**hist['counts'],'opened':0})
 return f.freq(blank)

def gold_margin_audit(rr,pp):
 ns=a.six.make_engine('strict_round_down');out=[]
 for budget in (10.,30.,50.):
  events=[]
  for p in pp:
   if not HS<=p['op']<c.END:continue
   lot=ns['rounded'](budget/(100*p['sl']));margin=2*ns['margin']('XAUUSD',lot,max(p['buy'],p['sell']))
   events.append(dict(event=c.iso(p['epoch']),kind=p['kind'],price=max(p['buy'],p['sell']),lots_per_side=lot,
                      planned_risk_per_side=lot*100*p['sl'],full_two_side_margin=margin,fits_initial_8000_budget=margin<=8000))
  unconstrained=[]
  for stress in (False,True):
   cash=[]
   for t in rr:
    if HS<=t['op']<c.END and t['cl']<c.END:
     gross,comm,swap,extra=ns['costs'](t,stress)
     lot=ns['rounded'](budget/t['unit_risk']);cash.append((gross+comm+swap-extra)*lot)
   unconstrained.append(dict(stress=stress,trades=len(cash),net=sum(cash),win_rate=100*sum(v>0 for v in cash)/len(cash)))
  out.append(dict(risk_per_side=budget,events=events,unconstrained_ledger_cash_NOT_executable_or_FTMO=unconstrained))
 return out

def n(v,p=2):return '—' if v is None else f'{v:,.{p}f}'
def money(v):return ('−' if v<0 else '+')+'$'+n(abs(v))
def report(out):
 lines=['# Claude Nasdaq DI addition and Gold News Pulse risk comparison','',
 'Research only — 27 September 2026. No production EA, launcher, website, trading account or live terminal changed.','',
 '## Exact scope','',
 'J keeps the prior eight instances: raw Gold Overnight Value Area, Nasdaq Overnight, EMA3 Safe, ORB Volume Profile 0.75R, News Pulse XAU, News Pulse XAG, an additional EMA3 M15 ATR-trailing instance, and an additional ORB 0.50R instance. M adds Claude\'s promoted Nasdaq 5M DI-filter EA as the ninth instance. Nasdaq Overnight remains. No RSI/VWAP is added.','',
 'The Nasdaq addition is the verified saved DI binary: DI agreement period 14, EMA12, 09:30 New York M5 signal, fixed 2.5R target, ATR trailing OFF. This is not the wider-stop/ATR experiment. Its exact binary and SET were rerun with real ticks and 150 ms fixed delay in the isolated tester; no source modifications. The other eight ledgers are the previously verified 150 ms native runs.','',
 'Gold-only N30 and N50 mean $30 and $50 per pending order respectively, not per event. Both sides are retained, making $60/$100 planned event risk before gaps/costs. N10 is a $10/order control. No sizing cap is silently introduced to make $30/$50 fit.','',
 '## Method and assumptions','',
 'Historical replay: 4 March–30 August 2026, $10,000 start, 180 calendar days / 128 weekdays. Profits below are continuous-account P&L, not withdrawals or payout income. Portfolio DD is a stop-reserve proxy, NOT tick-measured combined equity. Actual combined equity DD is unavailable.','',
 'Monte Carlo: 1,000 matched paths per configuration and cost case, five configurations × two cost cases = 10,000 paths. Same seed 20260926 and 26 joint source weeks (2 March–30 August), synthetic purchase 28 September 2026. All milestones are conditional on these fitted historical paths, not calibrated future probabilities.','',
 'Same strict 0.01-lot rounding down, ordinary risk ceiling $71.43, daily admission budget $300, aggregate initial risk $225, correlated-metal/per-symbol cap $150, projected $9,200 buffer, maximum seven entries/day and three-loss admission stop. Pending news sides reserve both risk AND full gross margin, with an 80% available-equity margin budget. No credit for hedge-margin offsets is assumed. That is the research controller\'s conservative assumption, not a verified FTMO order-rejection rule.','',
 'Instrument margin assumptions: gold/silver/Nasdaq 1:15. Gold 1:15 matches FTMO\'s February 2026 published update; account-wide Swing up to 1:30 does not mean gold is 1:30. Exact connected-account hedge/pending margin was not queried or tested.','',
 'FTMO model: 2-Step +10% / +5%, four entry days per phase, 5% daily and 10% static loss limits with Prague DST reset. Two business days between phases, five until funded activation, first reward at least 14 calendar days after the first funded trade while flat and at least $25 profitable, then four business days for receipt and an 80% share are retained modeling assumptions. Tests stop at first reward request or day 180; no lifetime funded-account survival estimate.','',
 'Reference uses native fills and commission floors. Stress retains the prior hypothetical adverse-cost scenario: gross wins reduced 10%, losses enlarged 10%, extra adverse price cost ($1 on gold news, $0.20 ordinary gold, $0.04 silver, 2 Nasdaq points), doubled negative swaps/carry. These are sensitivity assumptions, not measured FTMO slippage.','',
 '## Continuous shared-account results','']
 for stress in (True,False):
  lines+=['### '+('Stressed costs' if stress else 'Reference costs'),'','| Case | Trades | /30 days | /weekday | Net USD | Return | Win rate | PF | Closed DD | Reserve DD proxy | Max W/L |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
  for case in out['cases']:
   if case['stress']!=stress:continue
   h=case['historical'];q=case['frequency'];profit=h['balance']-10000
   lines.append(f"| {case['id']} | {h['trades']} | {n(q['trades_per_30_days'])} | {n(q['trades_per_weekday'])} | {money(profit)} | {n(profit/100)}% | {n(h['win_rate']) if h['trades'] else '—'} | {n(h['pf'])} | {n(h['closed_dd_pct'])}% | {n(h['model_dd_pct'])}% | {h['max_win_streak']}/{h['max_loss_streak']} |")
 lines+=['','## FTMO modeled milestones — stressed costs','',
 '| Case | Funded 30d | Paid 60d | Paid 120d | Funded 180d | Paid 180d | Breach before first reward | Median P1 days* | Median P2 days* | Median funded days* | Median paid days* |',
 '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
 for case in out['cases']:
  if not case['stress']:continue
  hz={h['days']:h for h in case['summary']['horizons']};t=case['summary']['timing']
  lines.append(f"| {case['id']} | {n(hz[30]['funded_pct'],1)}% | {n(hz[60]['payout_pct'],1)}% | {n(hz[120]['payout_pct'],1)}% | {n(hz[180]['funded_pct'],1)}% | {n(hz[180]['payout_pct'],1)}% | {n(hz[180]['breach_before_first_reward_pct'],1)}% | "+' | '.join(n(t[k]['median'],1) for k in ('phase1_days_among_phase1_passers','phase2_days_from_availability_among_phase2_passers','funded_days_from_purchase','payout_days_from_purchase'))+' |')
 lines+=['','*Conditional on milestone completion within 180 days. Phase 2 duration starts at availability; other timing is from purchase. Censored/untraded accounts are not blown accounts. Zero modeled breaches is not zero real risk.','',
 '| Case | First reward median if paid* | P95 reserve DD | Paths touching internal total buffer |','|---|---:|---:|---:|']
 for case in out['cases']:
  if case['stress']:lines.append(f"| {case['id']} | ${n(case['aggregate180']['median_first_reward_if_paid'])} | {n(case['aggregate180']['p95_stop_envelope_dd_pct'])}% | {case['summary']['paths_touching_internal_total_buffer']}/{N} |")
 lines+=['','## Nine-EA contributions — stressed costs','',
 '| EA | Trades | /30 days | /weekday | Win rate | PF | Net USD | Max W/L |','|---|---:|---:|---:|---:|---:|---:|---:|']
 for case in out['cases']:
  if case['id']!='M' or not case['stress']:continue
  for key,v in case['historical']['by_ea'].items():
   ws=ls=mw=ml=0
   for trade in case['historical']['log']:
    if trade['ea']!=key:continue
    ws=ws+1 if trade['net_profit']>0 else 0;ls=ls+1 if trade['net_profit']<0 else 0;mw=max(mw,ws);ml=max(ml,ls)
   lines.append(f"| {case['labels'][key]} | {v['trades']} | {n(v['trades']/6)} | {n(v['trades']/128)} | {n(100*v['wins']/v['trades'])}% | {n(v['positive']/v['negative'] if v['negative'] else None)} | {money(v['net'])} | {mw}/{ml} |")
 lines+=['','Contributions reflect trades accepted by the shared controller. Adding a strategy changes which other trades fit; its individual P&L is not the entire causal portfolio effect. Originals retain priority over added versions on simultaneous entries.','',
 '## News margin audit','', '| Per-side risk | Lot/side | Full two-side margin range | Source events fitting initial $8,000 budget |','|---|---:|---:|---:|']
 for item in out['gold_margin_audit']:
  ev=item['events'];m=[p['full_two_side_margin'] for p in ev]
  lines.append(f"| ${item['risk_per_side']:.0f} | {ev[0]['lots_per_side']:.2f} | ${min(m):,.2f}–${max(m):,.2f} | {sum(p['fits_initial_8000_budget'] for p in ev)}/{len(ev)} |")
 lines+=['','N30/N50 follow the same full-two-side margin reserve as all prior portfolio studies. If orders do not fit, they are skipped, not shrunk or assumed filled. Actual platform behavior may reserve differently; verify symbol and hedge/pending-order specifications before interpreting skips as broker rejections.','',
 'For diagnostics only, RESULTS.json also saves cash from resizing every historical gold-news fill at each risk without admission gates. Those numbers ignore margin feasibility and cannot be used as FTMO pass/payout estimates.','',
 '## Monthly net cash — stressed costs','', '| Case | Month | Closed trades | Net USD |','|---|---|---:|---:|']
 for case in out['cases']:
  if not case['stress']:continue
  months={f'2026-{m:02d}':[0,0.] for m in range(3,9)}
  for t in case['historical']['log']:p=months[t['close'][:7]];p[0]+=1;p[1]+=t['net_profit']
  assert abs(sum(p[1] for p in months.values())-(case['historical']['balance']-10000))<1e-7
  for month,(count,profit) in months.items():lines.append(f"| {case['id']} | {month} | {count} | {money(profit)} |")
 lines+=['','## Native Nasdaq operational finding','',
 'The exact unmodified build emitted repeated failed session-close requests (market closed) on 6 March 2026. Its long opened at 14:35 and actually closed on 8 March at 22:00:02, crossing the weekend. The report retains that real simulated outcome and swaps; it does NOT assume the requested Friday close succeeded. The retry behavior and broker-session handling require review before any FTMO deployment; failure messages are duplicated across journal streams, so the aggregate message count is not a unique request count.','',
 '## Limits and deployment blockers','',
 '- Only 26 source weeks. News settings were fitted to overlapping history, and the DI rule was selected on September 2025–April 2026, also overlapping the sample. The results are not independent forward validation.',
 '- Exness native tick ledgers plus a portfolio overlay, not a native FTMO multi-EA test. Shared skips can affect future EA state, and the overlay does not recreate that interaction.',
 '- Weekly resampling does not preserve the actual future calendar of CPI/NFP/FOMC releases. A few large news winners can dominate estimates; repetitions are not new evidence.',
 '- No real combined intratrade equity reconstruction. Planned risk/reserves do not bound stop slippage, gaps, outages or real daily-loss breaches.',
 '- Swing permission to trade news does not override FTMO prohibited gap trading. Written clarification of this pre-event two-sided stop implementation is still required. Disqualification and operational-hyperactivity risk are not priced into the probabilities.',
 '- Nothing deployed. No EA logic, BAT settings, production data or website changed.','',
 '## Evidence','',
 'NATIVE_FROZEN.json: exact Nasdaq inputs and hashes. native-di/: fresh report, trades and journal. FROZEN.json: portfolio choices/assumptions/evidence hashes fixed before replay. RESULTS.json: all historical ledgers, margin diagnostics and compact Monte Carlo paths. CHECKS.json: input/source/cash/funnel validation and exact eight-EA baseline reproduction.','',
 '- [FTMO 2-Step comparison](https://ftmo.com/en/comparison-table/)',
 '- [Gold Swing leverage update](https://ftmo.com/en/blog/trading-updates/trading-update-2-feb-2026/)',
 '- [Account specifications](https://ftmo.com/en/faq/what-are-the-account-specifications/)',
 '- [Forbidden trading practices](https://ftmo.com/en/forbidden-trading-practices/)','']
 (ROOT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')

def main():
 c.verify_sources()
 for path,info in a.CFG['source_files'].items():assert sha(Path(path))==info['sha256']
 needed=list(dict.fromkeys((n,v) for cfg in CONFIGS for n,v,_ in cfg['members']))
 files=[]
 for folder in [EXIT/'native'/(n+'-'+v) for n,v in needed]+[ROOT/'native-di']:
  files.extend(folder/name for name in ('run.json','trades.json','report.htm.gz','journal.txt.gz'))
 files += [PREV/'RESULTS.json',PREV/'run.py',EXIT/'analyze.py',EXIT/'run-config.json',c.ROOT/'compare.py',c.ROOT/'six_ea.py',c.ROOT/'phase_breakdown.py',c.SOURCE/'simulate.py',c.SOURCE/'prepare.py']
 files += [ROOT/'native_di.py',ROOT/'compare_additions.py',ROOT/'NATIVE_FROZEN.json']
 evidence={str(p):sha(p) for p in files}
 frozen=dict(configs=CONFIGS,paths_per_case=N,seed=SEED,historical_start=c.iso(HS),end_exclusive=c.iso(c.END),source_start=c.iso(a.ph.POOL_START),
  risk_per_ordinary_trade=500/7,news_risk_unit='per pending order, both sides retained',margin_policy='full gross margin on both pending sides, 80 percent equity ceiling, no hedge credit',
  symbol_specs=c.SPECS,evidence_hashes=evidence,new_native_runs=1)
 save('FROZEN.json',frozen)
 native={(n,v):a.load_case(n,v) for n,v in needed};di,di_meta=load_di()
 checks=dict(inherited=a.six.checks(c.read(c.SOURCE/'prepared.json')),native_ledgers=9,production_sources_unchanged=len(a.CFG['source_files']),baseline_parity=[])
 rng=random.Random(SEED);samples=[[rng.randrange(26) for _ in range(26)] for _ in range(N)]
 out=dict(frozen=frozen,native_di=di_meta,gold_margin_audit=gold_margin_audit(*native['xau','native'][:2]),cases=[])
 old=c.read(PREV/'RESULTS.json');controls={}
 for cfg in CONFIGS:
  data,labels=f.body_data(cfg,native)
  if cfg['di']:data['rows'][DI]=di;labels[DI]='Claude Nasdaq 5M DI, 2.5R'
  keys=list(data['rows']);weeks=c.pool(data,a.ph.POOL_START,26)
  for stress in (False,True):
   ns=a.six.make_engine('strict_round_down');sims=[]
   for sample in samples:
    rows,pp=c.sample_rows(data,keys,a.ph.POOL_START,weeks,sample,c.START,c.START+180*c.DAY)
    sims.append(ns['replay'](rows,pp,c.START,c.START+180*c.DAY,stress=stress,news_risk=cfg['news_risk']))
   rows=[dict(t) for rr in data['rows'].values() for t in rr if HS<=t['op']<c.END and t['cl']<c.END]
   pp=[dict(p) for p in data['placements'] if HS<=p['op']<c.END]
   hist=ns['replay'](rows,pp,HS,c.END,stress=stress,news_risk=cfg['news_risk'],challenge=False,detail=True)
   hc=ns['replay'](rows,pp,HS,c.END,stress=stress,news_risk=cfg['news_risk'],detail=True)
   summary=a.ph.summarize(sims,ns);paths=a.a.compact_paths(sims)
   if cfg['id']=='J':
    prev=next(x for x in old['cases'] if x['id']=='J' and x['stress']==stress)
    assert hist==prev['historical'] and summary==prev['summary'] and paths==prev['paths'],'Exact baseline reproduction failed'
    controls[stress]=sims;checks['baseline_parity'].append(dict(stress=stress,full_historical=True,full_summary=True,all_paths=N))
   case=dict(id=cfg['id'],config=cfg,stress=stress,labels=labels,historical=hist,historical_challenge=hc,frequency=frequency(hist),summary=summary,
      aggregate180=c.summarize(sims,180),paths=paths,paired_paid120=a.a.paired(controls[stress],sims,'receipt_at',120),paired_paid180=a.a.paired(controls[stress],sims,'receipt_at',180))
   validate(case);out['cases'].append(case);save('RESULTS.json',out);report(out)
   print(cfg['id'],'stress' if stress else 'reference',json.dumps(dict(net=hist['balance']-10000,trades=hist['trades'],weekday=case['frequency']['trades_per_weekday'],wr=hist['win_rate'],pf=hist['pf'],dd=hist['model_dd_pct'],paid180=summary['horizons'][-1]['payout_pct'],counts=hist['counts'])),flush=True)
 for p,digest in evidence.items():assert sha(Path(p))==digest,p
 for p,info in a.CFG['source_files'].items():assert sha(Path(p))==info['sha256']
 assert len(out['cases'])==10
 checks.update(cases_validated=10,paths_checked=10000,evidence_files_unchanged=len(evidence))
 save('CHECKS.json',checks)
 print('COMPLETE: 10,000 paths, exact baseline parity, cash/sizing/funnel checks passed.',flush=True)
if __name__=='__main__':main()
