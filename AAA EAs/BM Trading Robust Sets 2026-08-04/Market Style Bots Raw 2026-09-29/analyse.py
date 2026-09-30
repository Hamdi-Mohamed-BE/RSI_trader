"""Offline native cash audit, transparent ranking and visual comparison."""
from pathlib import Path
import gzip,hashlib,json,re,zipfile
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
CFG=json.loads((ROOT/'run-config.json').read_text())
LABEL={'nasdaq-trend':'Nasdaq trend pullback','bitcoin-reversal':'Bitcoin shock reversal','gold-volatility':'Gold volatility regime','eurusd-range':'EURUSD range fade','gbpusd-range':'GBPUSD range fade','usdjpy-range':'USDJPY range fade'}
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False,default=lambda v:v.item() if isinstance(v,np.generic) else str(v)),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def streaks(p):
 curw=curl=bestw=bestl=0
 for x in p:
  curw,curl=(curw+1,0) if x>0 else (0,curl+1) if x<0 else (0,0)
  bestw,bestl=max(bestw,curw),max(bestl,curl)
 return bestw,bestl
def main():
 build=json.loads((ROOT/'BUILD.json').read_text());assert all(sha(ROOT/k)==v for k,v in build.items())
 data={b['symbol']:pd.read_csv(ROOT/'data'/f"{b['symbol']}-H1.csv.gz") for b in CFG['bots']}
 results=[];ledger={};evidence={}
 for f in sorted((ROOT/'native').glob('*/run.json')):
  r=json.loads(f.read_text());assert r['build']==build;out=f.parent;attempt=r['attempt']
  rp=out/f'report-attempt{attempt}.htm.gz';assert hashlib.sha256(gzip.decompress(rp.read_bytes())).hexdigest()==r['report_sha']
  d=pd.read_csv(out/'trades.csv.gz');s=pd.read_csv(out/'signals.csv.gz');m=r['metrics'];p=d.net_profit.to_numpy()
  assert len(d)==m['trades']==len(s) and d.position_id.is_unique and s.position_id.is_unique
  assert np.allclose(d.volume,d.closed_volume,atol=1e-8)
  assert np.allclose(d.net_profit,d[['gross_profit','commission','swap','fee']].sum(axis=1),atol=.011)
  assert abs(p.sum()-m['net_profit'])<.02 and abs(10000+p.sum()-m['final_balance'])<.02
  if len(d):
   assert (d.actual_risk>0).all() and (d.requested_risk>0).all()
   assert (d.side*(d.open_price-d.initial_sl)>0).all() and (d.side*(d.initial_tp-d.open_price)>0).all()
   assert (d.open_epoch%3600<301).all() and not (d.open_epoch//86400).duplicated().any()
   prior_balance=10000+np.r_[0,np.cumsum(p)[:-1]]
   assert np.allclose(d.requested_risk,prior_balance*.01,atol=.011)
  journal=gzip.decompress((out/f'journal-attempt{attempt}.txt.gz').read_bytes()).decode()
  assert 'testing with execution delay 150 milliseconds' in journal and 'demo=1' in journal and 'Exness-MT5Trial16' in journal
  assert not re.search('position closed due end of test',journal),'Unexpected test-boundary liquidation'
  start=pd.Timestamp(r['start'].replace('.','-'),tz='UTC');end=pd.Timestamp(r['end'].replace('.','-'),tz='UTC')
  bars=data[r['bot']['symbol']];t=pd.to_datetime(bars.time,unit='s',utc=True)
  eligible=(t>=start)&(t<end)&(t.dt.hour>=7)&(t.dt.hour<=16)
  if r['bot']['mode']!=1:eligible &= t.dt.dayofweek<5
  days=t[eligible].dt.date.nunique();months=(end-start).days/30.4375
  eq=np.r_[10000,10000+np.cumsum(p)];pk=np.maximum.accumulate(eq);bdd=float(100*np.max((pk-eq)/pk))
  w,l=streaks(p);nr=d.net_profit/d.actual_risk;overshoot=d.actual_risk/d.requested_risk
  m.update(trades_per_month=len(d)/months,trades_per_eligible_day=len(d)/days if days else 0,eligible_days=days,win_streak=w,loss_streak=l,balance_dd_pct=bdd,total_net_R=float(nr.sum()),max_actual_stop_risk_pct=float(overshoot.max()) if len(d) else None,median_actual_stop_risk_pct=float(overshoot.median()) if len(d) else None)
  years=[]
  for year,g in d.groupby(pd.to_datetime(d.close_epoch,unit='s',utc=True).dt.year):
   pn=g.net_profit;loss=-pn[pn<0].sum();years.append(dict(year=int(year),trades=len(g),net_profit=float(pn.sum()),net_R=float((g.net_profit/g.actual_risk).sum()),pf=float(pn[pn>0].sum()/loss) if loss else None))
  r.update(costs={c:float(d[c].sum()) for c in ['gross_profit','commission','swap','fee','net_profit']},calendar_years=years,max_hold_hours=float(((d.close_epoch-d.open_epoch)/3600).max()) if len(d) else 0)
  ledger[r['tag']]=d;results.append(r)
  for pth in [f,rp,out/'trades.csv.gz',out/'signals.csv.gz',out/'trace.csv.gz',out/f'journal-attempt{attempt}.txt.gz']:
   evidence[str(pth.relative_to(ROOT))]=sha(pth)
 pairs=[]
 for r in results:
  if r['control']:continue
  tag=r['tag'].replace('-raw-','-control-');c=next((z for z in results if z['tag']==tag),None)
  if c is None:continue
  a=ledger[r['tag']].copy();b=ledger[tag].copy();a['date']=a.open_epoch//86400;b['date']=b.open_epoch//86400
  joined=a.merge(b,on='date',suffixes=('_raw','_control'),validate='1:1')
  paired=len(joined)==len(a)==len(b)
  timing_max=float(abs(joined.open_epoch_raw-joined.open_epoch_control).max()) if len(joined) else None
  delta=joined.net_profit_raw/joined.actual_risk_raw-joined.net_profit_control/joined.actual_risk_control
  pairs.append(dict(raw_tag=r['tag'],control_tag=tag,all_dates_matched=paired,n=len(joined),max_entry_time_delta_seconds=timing_max,mean_R_difference=float(delta.mean()) if len(joined) else None))
 def get(name,w,control=False,model=None):
  choices=[r for r in results if r['bot']['name']==name and r['window']==w and r['control']==control and (model is None or r['model']==model)]
  return max(choices,key=lambda r:r['model']) if choices else None
 ranks=[]
 for bot in CFG['bots']:
  name=bot['name'];reasons=[];selected=[get(name,w) for w in ['3y','5y']]
  for r in selected:
   if r is None:reasons.append('Missing long-window result');continue
   m=r['metrics'];w=r['window'];c=get(name,w,True,r['model']);pair=next((z for z in pairs if z['raw_tag']==r['tag']),None)
   if m['net_profit']<=0:reasons.append(w+' net loss')
   if (m['profit_factor'] or 0)<1.15:reasons.append(w+' PF below 1.15')
   if m['trades']<30:reasons.append(w+' insufficient trades')
   if any(r['flags'].values()):reasons.append(w+' raw execution/carry flags')
   if c is None or any(c['flags'].values()):reasons.append(w+' control missing or execution/carry flags')
   if c is not None and (m['mean_net_R'] is None or c['metrics']['mean_net_R'] is None or m['mean_net_R']<=c['metrics']['mean_net_R']):reasons.append(w+' does not beat matched control mean R')
   if not pair or not pair['all_dates_matched']:reasons.append(w+' control dates mismatch')
  y=get(name,'1y');recent_good=y is not None and y['metrics']['net_profit']>0 and not any(y['flags'].values())
  rawpass=not reasons
  if y is None:reasons.append('Recent-year result unavailable')
  else:
   if y['metrics']['net_profit']<=0:reasons.append('Recent-year net loss or zero return')
   if any(y['flags'].values()):reasons.append('Recent-year execution/carry flags')
  metric_floor=min((r['metrics']['profit_factor'] or 0) for r in selected if r) if any(selected) else 0
  ranks.append(dict(name=name,label=LABEL[name],raw_gate_pass=rawpass,shortlist=rawpass and recent_good,long_windows_confirmed=all(r and r['model']==4 for r in selected),minimum_long_pf=metric_floor,maximum_long_dd=max(r['metrics']['equity_dd_pct'] for r in selected if r) if any(selected) else None,recent_pf=(y['metrics']['profit_factor'] or 0) if y else 0,reasons=reasons))
 ranks.sort(key=lambda r:(r['shortlist'],r['minimum_long_pf'],-(r['maximum_long_dd'] or 1000),r['recent_pf']),reverse=True)
 for i,r in enumerate(ranks):r['rank']=i+1
 assert len(results)>=60,'Expected twelve smoke tests and forty-eight raw/control tests'
 v=json.loads((ROOT/'SIGNAL_VERIFICATION.json').read_text());assert not v['mismatches'];assert all(x['signals']==x['oracle_checked'] for x in v['runs'])
 save(ROOT/'RESULTS.json',dict(ranking=ranks,runs=results,matched_controls=pairs,claims='Raw historical comparison only; no optimization, unseen holdout, full randomization inference or live readiness'))
 save(ROOT/'VERIFICATION.json',dict(passed=True,checks=['Frozen source/build/rules hashes','Every archived native report hash','Every deal count, cost sum and final balance','All requested risks equal 1% pre-entry equity','Stops/targets have valid direction and position volumes fully close','Independent signal oracle, including gold causal states and random direction','Native broker/demo/symbol/dates/inputs and 150ms delay','No forced end-of-test liquidation; historical carry exceptions retained','All native matched-control entry dates audited'],native_runs=len(results),signal_checks=v['checked'],evidence=evidence))
 tests=json.loads((ROOT/'ORACLE_TESTS.json').read_text());assert tests['passed']
 plot(get);report(get,ranks,results,pairs);presets();bundle();print(json.dumps(ranks,indent=2))
def fmt(x,n=2):return 'n/a' if x is None else f'{x:.{n}f}'
def table(rows,show_window=False):
 s='| Bot | Trades | /month | /day | Return | PF | Win% | Equity DD | W/L streak | Mean net R |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n'
 for r in rows:
  m=r['metrics'];label=LABEL[r['bot']['name']]+(' control' if r['control'] else '')
  if show_window:label+=f" ({r['window']})"
  if any(r['flags'].values()):label+=' †'
  s+=f"| {label} | {m['trades']} | {m['trades_per_month']:.2f} | {m['trades_per_eligible_day']:.3f} | {m['return_pct']:+.2f}% | {fmt(m['profit_factor'])} | {m['win_rate_pct']:.1f} | {m['equity_dd_pct']:.2f}% | {m['win_streak']}/{m['loss_streak']} | {fmt(m['mean_net_R'],3)} |\n"
 return s
def plot(get):
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
 fig,axes=plt.subplots(3,2,figsize=(13,10),layout='constrained')
 for b,ax in zip(CFG['bots'],axes.flat):
  for ctl,color in [(False,'#116b87'),(True,'#b5a086')]:
   r=get(b['name'],'1y',ctl);d=pd.read_csv(ROOT/'native'/r['tag']/'trace.csv.gz');t=pd.to_datetime(d.time,unit='s',utc=True)
   # Daily last balance, explicitly not tick-equity DD.
   z=pd.Series(d.balance.to_numpy(),index=t).resample('D').last().dropna()
   ax.plot(z.index,(z.to_numpy()/10000-1)*100,color=color,lw=1.8,label='Strategy' if not ctl else 'Random-direction control')
  ax.axhline(0,color='#888888',lw=.6);ax.set_title(LABEL[b['name']],loc='left',weight='bold');ax.set_ylabel('Closed-balance return (%)');ax.grid(alpha=.15);ax.tick_params(axis='x',rotation=20)
 handles,labels=axes.flat[0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=2,frameon=False)
 fig.suptitle('Six research bots: recent-year native comparison\n27 Sep 2025–27 Sep 2026 · 1% target risk, rounded up · costs included',fontsize=15,weight='bold')
 fig.savefig(ROOT/'comparison.png',dpi=160);plt.close(fig)
def report(get,ranks,runs,pairs):
 winner=ranks[0];passed=[r for r in ranks if r['shortlist']]
 headline=f"{winner['label']} ranks first among these frozen implementations. "
 headline+='It passes the raw shortlist rules, not the full validation pipeline.' if passed else 'No bot passes all qualification rules; there is no validated winner.'
 text='# Market-style bots — six-bot native comparison\n\n'+headline+'\n\n'
 text+='The user clip supplies hypotheses, not complete strategies. These are our fixed-rule research implementations, not reproductions of the unspecified +180R experiment. Four model families were built across six broker CFDs. No optimization was performed and no live bot was deployed.\n\n'
 text+='## What was built\n\n- Nasdaq / USTEC: trend-aligned EMA pullback, then continuation confirmation; 3R target.\n- BTCUSD: fade a large hourly shock after an opposite candle confirms a reaction; 1.5R target.\n- XAUUSD: trade directional confirmation only in a persistent high-volatility state; 2R target.\n- EURUSD, GBPUSD, USDJPY: fade a band excursion after re-entry in a low-efficiency, flat-trend environment; target the frozen pre-excursion mean.\n\nAll use completed H1 bars, one attempt/day, 1.5 ATR initial stop, 1% equity target risk rounded UP, and bounded intraday holds. No martingale, pyramiding or averaging. [Full frozen rules](RULES.md). An asset characteristic is not itself a profitable directional signal. Gold needs an additional directional rule, explicitly defined rather than assumed. The regime skill informed past-data-only state estimation; its missing packaged runner was replaced by the documented volatility-state transition model, not advertised as GARCH/HMM or the original skill algorithm.\n\n'
 text+='## Main five-year screens\n\n2021-09-27 to 2026-09-27 exclusive. Native one-minute-OHLC screens on Exness-MT5Trial16, $10,000 starting balance, USD, 150ms delay. These are not five years of recorded real ticks.\n\n'
 text+=table([get(r['name'],'5y',False,1) for r in ranks])
 text+='\n† Execution/carry warning: inspect the exceptions below. Returns include configured spread, commission, swap and actual modeled fills, compounded at the target sizing rule. Equity DD is the native report’s relative floating-equity drawdown; closed-balance DD is separately saved in RESULTS.json. /day is trades per eligible UTC date with quotes during the permitted entry hours, not per day with a trade. Lot rounding/slippage mean 1% is a target, not an exact cap.\n\n'
 text+='## Recent year\n\n2025-09-27 to 2026-09-27 exclusive, Model 4 real-tick mode. Real/generated proportions are listed below; this recent year has already been seen in other research and is not an untouched holdout.\n\n'+table([get(r['name'],'1y') for r in ranks])
 text+='\n![Recent-year strategy versus random-direction control](comparison.png)\n\nThe chart shows daily sampled closed balance, not intratrade equity or maximum drawdown. Each bot runs in its own account simulation; adding these returns is not a portfolio backtest.\n\n'
 text+='## Does each bot beat its control?\n\nControls randomize direction with seed 290929 at the same qualifying signals, reflect SL/TP distances, and retain the same risk/session rules. This isolates directional information conditional on the selected times; it does not prove that signal timing beats random times or reproduce the clip’s random-level test. One seed is a noisy comparator, not a distribution of random strategies. Compare mean net R; differently compounded balances can otherwise distort the comparison.\n\n'
 for window in ['5y','3y','1y','6m']:
  text+=f'### {window}: raw and matched control\n\n'+table([get(b['name'],window,c,1 if window in ['3y','5y'] else 4) for b in CFG['bots'] for c in [False,True]])+'\n'
 text+='## Qualification and ranking\n\nThe frozen raw gate requires positive P&L, PF >=1.15 and at least 30 trades in BOTH 3y/5y, better control mean R, matched dates, and valid execution/cost evidence. The current shortlist also requires a positive, execution-clean latest year. Rank eligible passes by the lower 3y/5y PF, then equity drawdown and recent-year PF. A nonpassing leader is a research lead only.\n\n'
 for r in ranks:
  text+=f"- **{r['rank']}. {r['label']}** — {'raw shortlist pass' if r['shortlist'] else 'not qualified'}; minimum long-window PF {r['minimum_long_pf']:.3f}. "+('; '.join(r['reasons']) if r['reasons'] else 'Needs the separately approved optimization/validation/stress pipeline before any promotion.')+'\n'
 confirmations=sorted([r for r in runs if r['model']==4 and r['window'] in ['3y','5y']],key=lambda r:(r['window'],r['control']))
 if confirmations:text+='\nLong-window real-tick-mode confirmations for screen passers (generated ticks before recorded real-tick history begins):\n\n'+table(confirmations,show_window=True)+'\n'
 else:text+='\nNo candidate qualified for long-window Model 4 confirmation.\n'
 text+='\n## Execution, risk and data audit\n\n'
 for b in CFG['bots']:
  name=b['name'];five=get(name,'5y',False,1);year=get(name,'1y');six=get(name,'6m');m=five['metrics'];fl=five['flags']
  text+=f"- **{LABEL[name]}:** five-year raw flags {json.dumps(fl)}. Maximum hold {five['max_hold_hours']:.2f}h. Initial stop risk median/max {fmt(m['median_actual_stop_risk_pct'],3)}% / {fmt(m['max_actual_stop_risk_pct'],3)}% of entry equity. Latest year native history label: {year['metrics']['history_quality']}; latest six months: {six['metrics']['history_quality']}.\n"
 raw_max=max(r['metrics']['max_actual_stop_risk_pct'] for r in runs if not r['control'] and r['metrics']['max_actual_stop_risk_pct'] is not None)
 text+=f'\nAcross all raw runs, actual initial-stop risk reached **{raw_max:.2f}% of equity** despite the 1% target. Volume rounding/minimums and fill changes are material; these tests do not represent a strict 1%-maximum-loss system. Commissions and gap losses can add further loss beyond the measured initial stop risk.\n'
 text+='\nScheduled flat times cannot execute without quotes. Historical missing/early-ending sessions can carry trades into the next session/weekend; those positions are retained with their real modeled costs, not excluded after looking at profits. Such flags block an unqualified intraday/pass claim. Native symbols supply current weekday session schedules, not a complete point-in-time historical holiday calendar. [Session API specification](https://www.mql5.com/en/docs/marketinformation/symbolinfosessiontrade).\n\nReal ticks generally begin 2026-01-01 on this feed. Earlier records are generated. Model 1 is a screen with OHLC path limitations; Model 4 also uses generated ticks where recorded ticks are absent. [MetaTrader real/generated tick documentation](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation). A 150ms simulated delay is not measured live slippage. Commission/swap schedules are tester/account-specific and not audited historical fee series. Do not transfer returns to a different broker or FTMO account.\n\n'
 text+='Native history-quality labels describe the full tester run, including the 90-day warmup; they are not separately measured tick-coverage percentages for just the trading window. Inspect each run’s recorded real-tick start date and archived journal for provenance.\n\n'
 text+='## What these results cannot establish\n\nThe overlapping 5y/3y/1y/6m windows are not independent replications. Six model/asset combinations were compared; selecting the best creates selection bias. There is no fresh holdout, multiple-testing-adjusted proof, full random-control distribution or completed Monte Carlo/FTMO validation here. No claim that Nasdaq always trends, all forex ranges, gold is uniquely clustered, or Bitcoin always reverses is established by this experiment. Nor does a failed implementation disprove an entire strategy family. Gold’s overlapping rolling ATR windows mechanically contribute to state persistence: a high estimated Hot-to-Hot probability is not, by itself, proof of forecast skill.\n\nThe original clip supplies four market families despite saying five; we used three FX pairs for a transparent six-asset comparison. We did not test every style on every asset. The gold bot is a NEW intraday regime strategy, not a repair or retest of the previous 23:00 London clock-bias strategy. Its results cannot settle that strategy’s financing discrepancy.\n\n'
 text+='## Artifacts and verification\n\n[Research bot source](MarketStyles.mq5), compiled MarketStyles.ex5, six named presets in `presets/`, [full results](RESULTS.json), [cash/evidence verification](VERIFICATION.json), [independent signal verification](SIGNAL_VERIFICATION.json), source H1 data and archived native reports/deals/signals/traces. The EA refuses to initialize outside Strategy Tester. Do not attach it to a trading account expecting live execution. No installers, production EAs, SETs, website or live account were modified. No optimization or deployment is implied by a raw pass.\n'
 (ROOT/'REPORT.md').write_text(text,encoding='utf-8')
def presets():
 p=ROOT/'presets';p.mkdir(exist_ok=True)
 for b in CFG['bots']:
  values=dict(InpMode=b['mode'],InpControl='false',InpRiskPercent=1,InpRR=b['rr'],InpSeed=290929,InpTradeFrom='2021.09.27 00:00:00',InpTag=b['name'],InpMagic=9294400)
  (p/(b['name']+'.set')).write_text('\n'.join(f'{k}={v}' for k,v in values.items())+'\n',encoding='utf-8')
def bundle():
 # Explicit public artifact allowlist: never bundle private tester/account INIs.
 files=[ROOT/p for p in ['MarketStyles.mq5','MarketStyles.ex5','RULES.md','REPORT.md','comparison.png','BUILD.json','run-config.json','README.md','RESULTS.json','VERIFICATION.json','SIGNAL_VERIFICATION.json','ORACLE_TESTS.json']]
 files+=sorted((ROOT/'presets').glob('*.set'))
 assert len(files)==18
 with zipfile.ZipFile(ROOT/'Market-style-research-bots.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
  for p in files:z.write(p,str(p.relative_to(ROOT)))
 save(ROOT/'DELIVERY_MANIFEST.json',{str(p.relative_to(ROOT)):sha(p) for p in files})
if __name__=='__main__':main()
