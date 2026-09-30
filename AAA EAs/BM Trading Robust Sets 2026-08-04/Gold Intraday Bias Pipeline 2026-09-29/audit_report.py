"""Offline cash, time, cohort and evidence audit; never connects to a terminal."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import gzip, hashlib, json, re, calendar
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
PREVIOUS=ROOT.parent/'Intraday Bias Discovery 2026-09-29'
UTC=timezone.utc

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x): p.write_text(json.dumps(x,indent=2,allow_nan=False,default=lambda v:v.item() if isinstance(v,np.generic) else str(v)),encoding='utf-8')
def pf(x):
 x=np.asarray(x,float); loss=-x[x<0].sum()
 return float(x[x>0].sum()/loss) if loss else None
def streaks(x):
 w=l=bestw=bestl=0
 for v in x:
  w,l=(w+1,0) if v>0 else (0,l+1) if v<0 else (0,0)
  bestw,bestl=max(w,bestw),max(l,bestl)
 return bestw,bestl
def crosses_roll(o,c):
 a=pd.Timestamp(o,unit='s',tz='UTC').tz_convert('America/New_York')
 b=a.normalize()+pd.Timedelta(hours=17)
 if b<=a: b+=pd.Timedelta(days=1)
 return b.timestamp()<=c
def mql_offset(t,city):
 y=t.year
 if city=='London':
  def lastsun(month):
   d=calendar.monthrange(y,month)[1];date=datetime(y,month,d,1,tzinfo=UTC)
   return date-timedelta(days=(date.weekday()+1)%7)
  return 3600 if lastsun(3)<=t<lastsun(10) else 0
 def sunday(month,second,hour):
  d=datetime(y,month,1,hour,tzinfo=UTC)
  return d+timedelta(days=(6-d.weekday())%7+(7 if second else 0))
 return -14400 if sunday(3,True,7)<=t<sunday(11,False,6) else -18000

def run():
 checks=[];build=json.loads((ROOT/'BUILD.json').read_text())
 assert all(sha(ROOT/p)==s for p,s in build.items());checks.append('All four frozen build/config/protocol hashes unchanged')
 assert json.loads((ROOT/'RAW_GATE.json').read_text())['passed'] is False
 checks.append('Raw gate is a JSON boolean false; cannot be truthy string')
 source=(ROOT/'GoldClock.mq5').read_text()
 assert 'if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED' in source
 checks.append('EA refuses initialization outside Strategy Tester')
 # Independent IANA comparison of the EA calendar algorithm, hourly across all test years.
 hours=pd.date_range('2021-01-01','2027-01-01',freq='h',tz='UTC',inclusive='left')
 for city,z in [('London','Europe/London'),('NY','America/New_York')]:
  for v in hours:
   t=v.to_pydatetime()
   assert mql_offset(t,city)==t.astimezone(ZoneInfo(z)).utcoffset().total_seconds()
 checks.append(f'London/New York clock rules match IANA at {len(hours)*2:,} hourly observations, including DST boundaries')
 prior=pd.read_csv(PREVIOUS/'selected-trades.csv.gz');prior=prior.loc[prior.symbol=='XAUUSD']
 bars=pd.read_csv(PREVIOUS/'data/XAUUSD_M5.csv.gz',usecols=['time'])
 runs=[];manifest={}
 for path in sorted((ROOT/'native').glob('*/run.json')):
  meta=json.loads(path.read_text());out=path.parent
  d=pd.read_csv(out/'trades.csv.gz');p=d.net_profit.to_numpy();m=meta['metrics']
  assert meta['build']==build
  archived_report=out/'report-attempt0.htm.gz'
  assert hashlib.sha256(gzip.decompress(archived_report.read_bytes())).hexdigest()==meta['report_sha']
  assert len(d)==m['trades'] and d.position_id.is_unique
  assert np.allclose(d.volume,d.closed_volume,atol=1e-9)
  assert np.allclose(d.volume,.1,atol=1e-9)
  assert np.allclose(d.gross_profit,(d.close_price-d.open_price)*d.volume*100,atol=.011)
  assert np.allclose(d.net_profit,d[['gross_profit','commission','swap','fee']].sum(axis=1),atol=.011)
  assert abs(p.sum()-m['net_profit'])<.02
  assert abs(10000+p.sum()-m['final_balance'])<.02
  assert abs(pf(p)-m['profit_factor'])<1e-9
  journal=gzip.decompress((out/'journal-attempt0.txt.gz').read_bytes()).decode()
  assert 'testing with execution delay 150 milliseconds' in journal
  start=pd.Timestamp(meta['start'].replace('.','-'),tz='UTC');end=pd.Timestamp(meta['end'].replace('.','-'),tz='UTC')
  assert (d.open_epoch>=start.timestamp()).all() and (d.close_epoch<end.timestamp()).all()
  hold=(d.close_epoch-d.open_epoch)/60
  assert (hold>0).all()
  roll=sum(crosses_roll(o,c) for o,c in zip(d.open_epoch,d.close_epoch))
  forced=len(re.findall('position closed due end of test',journal))
  if meta['variant']=='raw':
   dt=pd.to_datetime(d.open_epoch,unit='s',utc=True).dt.tz_convert('Europe/London')
   assert ((dt.dt.hour==23)&(dt.dt.minute<5)&(dt.dt.dayofweek<5)).all()
   assert not dt.dt.date.duplicated().any()
   assert roll==0 and not any(meta['flags'].values())
   if meta['window']=='smoke':
    assert (hold>=120).sum()==len(d)-1 and forced>0
   else: assert (hold>=120).all() and forced==0
  w,l=streaks(p)
  inbars=bars.loc[(bars.time>=start.timestamp())&(bars.time<end.timestamp()),'time']
  tradingdays=len(np.unique(inbars.to_numpy()//86400))
  priorpart=prior.loc[(prior.time>=start.timestamp())&(prior.time<end.timestamp())]
  native_slots=set((d.open_epoch//300*300).astype(int));old_slots=set(priorpart.time.astype(int))
  cost=dict(gross=float(d.gross_profit.sum()),commission=float(d.commission.sum()),swap=float(d.swap.sum()),fee=float(d.fee.sum()),native_net=float(p.sum()),excluding_swap_net=float((d.net_profit-d.swap).sum()),excluding_swap_pf=pf(d.net_profit-d.swap),swap_charged_trades=int((d.swap!=0).sum()),positions_crossing_published_ny17_roll=roll)
  execution=dict(min_hold_minutes=float(hold.min()),max_hold_minutes=float(hold.max()),holds_over_125_minutes=int((hold>125).sum()),test_boundary_close_log_mentions=forced,close_failure_retcodes=sorted(set(re.findall(r'GC_CLOSE_FAIL (\d+)',journal))),flags=meta['flags'])
  runs.append(dict(tag=meta['tag'],window=meta['window'],variant=meta['variant'],model=meta['model'],start=meta['start'],end=meta['end'],metrics=m|dict(trades_per_month=len(d)/((end-start).days/30.4375),trades_per_available_utc_day=len(d)/tradingdays,available_utc_days=tradingdays,win_streak=w,loss_streak=l),cost=cost,execution=execution,history_quality=m['history_quality'],tick_coverage=meta['tick_coverage'],cohort_comparison_with_previous=dict(previous_trades=len(priorpart),matched_entry_slots=len(native_slots&old_slots),native_only_slots=len(native_slots-old_slots),previous_only_slots=len(old_slots-native_slots)) if meta['variant']=='raw' else None))
  for pth in [path,archived_report,out/'trades.csv.gz',out/'trace.csv.gz',out/'journal-attempt0.txt.gz']:
   manifest[str(pth.relative_to(ROOT))]=sha(pth)
 checks+=['All eight native reports match their archived report hashes and frozen build',
 'All deal volumes close completely; independent price-times-contract cash calculation reconciles',
 'All deal cash components, final balances, trade counts and PFs reconcile to native reports',
 'All raw fills enter within the London 23:00 five-minute slot, once per local weekday',
 'All non-smoke raw positions hold at least 120 minutes, with no order failures or test-end closes',
 'Every raw position avoids 17:00 New York rollover; charged swap retained, not erased',
 'Smoke has one explicitly logged test-end administrative close, not a normal two-hour exit']
 assert len(runs)==8
 results=dict(verdict='NOT PASSED: baseline native gate failed; material financing-model discrepancy unresolved',stage_reached=4,optimization_runs=0,stress_simulations=0,production_changed=False,checks=checks,runs=runs)
 save(ROOT/'RESULTS.json',results);save(ROOT/'VERIFICATION.json',dict(passed=True,checks=checks,evidence_sha256=manifest))
 report(results)
 print(json.dumps(dict(verdict=results['verdict'],checks=len(checks),native_runs=len(runs),raw_costs={r['window']:r['cost'] for r in runs if r['variant']=='raw'}),indent=2))

def table(rows):
 lines=['| Window / model | Trades | /month | /data day | Net USD | Return | PF | Win rate | Equity DD | Longest W/L |',
 '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
 for r in rows:
  m=r['metrics'];model='1m OHLC' if r['model']==1 else 'real-tick mode'
  lines.append(f"| {r['window']} / {model} | {m['trades']} | {m['trades_per_month']:.2f} | {m['trades_per_available_utc_day']:.2f} | {m['net_profit']:+,.2f} | {m['return_pct']:+.2f}% | {m['profit_factor']:.3f} | {m['win_rate_pct']:.2f}% | {m['equity_dd_pct']:.2f}% | {m['win_streak']}/{m['loss_streak']} |")
 return '\n'.join(lines)

def report(x):
 runs=x['runs'];raw=[next(r for r in runs if r['variant']=='raw' and r['window']==w) for w in ['6m','1y','3y','5y']]
 controls=[r for r in runs if r['variant']=='control' and r['window']!='smoke']
 text='''# Gold intraday bias — pipeline result

**Not improved or validated yet. The unchanged strategy failed the native baseline gate. Optimization and Monte Carlo were not run. A material financing-model discrepancy needs resolving before deciding whether to rehabilitate this candidate. No live deployment.**

Tested rule: buy XAUUSD at 23:00 Europe/London (DST-aware), first quote within five minutes; close after 120 elapsed minutes from the fill. Fixed 0.10 lot, $10,000 initial balance, no stop-loss, 150ms simulated execution delay. This is a research baseline, not a 1%-risk strategy or a live recommendation. The tests use the isolated Exness-MT5Trial16 research environment; broker CFD findings do not automatically transfer to other accounts or gold futures.

## Native results, including configured spread, commission and swap

All windows end 27 September 2026 exclusive; starts are 27 March 2026, 27 September 2025, 27 September 2023 and 27 September 2021 respectively. The windows overlap and are not four independent replications.

'''+table(raw)+'''

Trade/day uses the number of UTC dates with available gold bars; it is not trades per active strategy day. Return is fixed-lot cash P&L divided by the $10,000 starting balance, not an unleveraged price return. Drawdown is native marked-to-market relative equity drawdown. No initial stop means risk is not capped at 1%; a higher return from larger size would not establish an improved edge.

The frozen gate requires both three- and five-year native screens to have positive net P&L, PF at least 1.15, at least 30 trades and better mean P&L/trade than a valid control. Three-year PF fails; five-year net and PF fail independently of the control problem below. The recent year passes the PF threshold alone, but cannot override the longer-window failures. The most recent six months are marginal after configured costs.

## Financing is material — diagnostic, not a corrected backtest

The following decomposition preserves the same native fills, spread, commission and size. The last column removes only the recorded swap arithmetically. It does not constitute a second executable backtest, a verified swap-free account or a passed pipeline.

| Window | Fill-based price P&L | Commission | Recorded swap | Native net | PF excluding only swap |
|---|---:|---:|---:|---:|---:|
'''
 for r in raw:
  c=r['cost'];text+=f"| {r['window']} | ${c['gross']:+,.2f} | ${c['commission']:,.2f} | ${c['swap']:,.2f} | ${c['native_net']:+,.2f} | {c['excluding_swap_pf']:.3f} |\n"
 text+='''
Every raw position in these ledgers avoids 17:00 New York, yet receives a swap charge. Positions cross UTC midnight; that pattern is consistent with a tester financing-clock mismatch, but the accrual timestamp itself is not separately logged. Do not read this as proof that the live broker charged incorrectly.

Exness currently documents swap at 21:00 GMT in summer / 22:00 GMT in winter, and states its MetaTrader servers use GMT+0. These raw positions begin at 22:00 or 23:00 UTC, after that published rollover, and close roughly two hours later. The current articles do not establish historical rates, holiday exceptions, or account-specific swap-free eligibility across 2021–2026. Sources: [Exness swap schedule](https://get.exness.help/hc/en-us/articles/360014709151-About-swap), [Exness server timezone](https://get.exness.help/hc/en-us/articles/360014390760-What-is-the-default-timezone-set-for-MetaTrader).

**This supports keeping gold as an unresolved research candidate, not promoting it or declaring the underlying price pattern dead.** Before restarting the gate, establish the intended broker/account's actual rollover time and financing treatment, then implement and freeze a validated cost model. Do not just turn off swap because it improves the result. An accurate accounting repair is not a newly discovered strategy improvement.

## Execution/data qualifications

'''
 for r in raw:
  text+=f"- {r['window']}: native history quality says **{r['history_quality']}**; observed holding times {r['execution']['min_hold_minutes']:.2f}–{r['execution']['max_hold_minutes']:.2f} minutes; no raw entry/close failures.\n"
 text+='''
Real ticks begin 1 January 2026 on this feed. Therefore the one-year real-tick-mode run includes generated history, while the six-month run reports 100% real ticks. The three-/five-year runs are one-minute-OHLC screens, not long-horizon real-tick confirmations. “98% history quality” in those screens is not “98% real ticks.” The [MetaTrader documentation](https://www.metatrader5.com/en/terminal/help/algotrading/testing) describes modeling modes and the simulated execution delay.

The smoke run reconciles, but its final raw position was closed administratively at test end after 119.42 minutes. That exception is retained, not presented as a normal scheduled exit. No such forced end-of-test close occurred in the four principal raw runs.

## Control diagnostics — not valid pass/fail benchmarks

The fixed random-clock controls attempted exits during market-closed periods (retcode 10018), and some positions lasted up to 301 minutes. The unmodified smoke control also had an extended hold without a close rejection because no executable quote arrived at the intended exit. These controls are not clean two-hour comparators. Their cash ledgers are retained for transparency, but **no claim that gold beats/loses to a valid control is made**. Correct session-aware control construction is required before advancing.

'''+table(controls)+'''

Native log counts include overlapping terminal/agent copies, so they must not be interpreted as unique rejected orders. Three-/five-year raw trades themselves had zero close failures; their own PF/net gates fail regardless. Recent control reruns and long-horizon real-tick confirmations were not pursued after rejection.

## Why this differs from the earlier promising gold result

The earlier M5 discovery used fixed-notional, spread-only bar returns; no commission, actual native fills, or native financing. This study uses fixed lots and native execution. Returns are therefore not directly comparable. Also, the old screen discarded windows based on future missing bars. That is a retrospective executability filter; the new EA makes decisions causally and does not discard trades because future data will be incomplete.

| Native window | Previous selected trades | Native trades | Matched five-minute entry slots | Native-only slots | Previous-only slots |
|---|---:|---:|---:|---:|---:|
'''
 for r in raw:
  c=r['cohort_comparison_with_previous'];text+=f"| {r['window']} | {c['previous_trades']} | {r['metrics']['trades']} | {c['matched_entry_slots']} | {c['native_only_slots']} | {c['previous_only_slots']} |\n"
 text+='''
Matching entry slots does not imply identical prices, exit times or costs. The old final-year gold PF of about 1.48 did not pass its original neighboring-time stability and multiple-testing checks. Those failures remain on record. We have already examined that year, so it cannot serve as a fresh holdout for a refined strategy. Reserved older history was not opened for optimization or selection during this run.

## How far the full pipeline got

1. Frozen rules, cost treatment, control, windows, search space and gate: recorded before native results.
2. Tester-only EA: compiled with zero errors/warnings. Cash/time/build audits complete, with the smoke boundary and control-session exceptions documented.
3. Native evidence: two smoke tests, four long-window screens, two recent raw audits — eight runs total.
4. Raw gate: **not passed**; financing validity and control construction also remain unresolved.
5. Optimization, new finalist selection and reserved-period replication: **not started**, per the frozen failure gate. Zero tuning configurations evaluated.
6. Monte Carlo, FTMO simulation and portfolio overlap: **not run**; there is no selected, validated improved candidate to stress-test.
7. Production, deployment, website and account changes: **not authorized and not performed**.

A report-only JSON boolean bug was repaired after the screens: the failed gate is now an actual `false`, and continuation requires `passed is True`. Control execution validity was added to the gate. Neither repair changes the EA, frozen strategy, input file or fills; all four build hashes remain unchanged. The raw gate had already failed on its own economics.

## Evidence and next decision

See [frozen protocol](PROTOCOL.md), [machine-readable results](RESULTS.json), [verification](VERIFICATION.json) and the archived reports, deal ledgers, traces and journals under `native/`. All cash calculations were independently reconciled and timestamps checked against IANA timezone rules. Account/configuration credentials are not reproduced in this report.

Next useful step: verify the target account's real financing/session specifications, repair the cost/control implementation, rerun the unchanged baseline, and only if it passes resume the already-frozen optimization plan. This report does not show that optimization improved gold. It shows precisely what must be resolved before that claim can be tested honestly.
'''
 (ROOT/'REPORT.md').write_text(text,encoding='utf-8')

if __name__=='__main__':run()
