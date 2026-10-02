"""Target-only native reruns, one strategy at a time. No live terminal access."""
import native_runner as nr
from native_runner import *
import numpy as np
TARGETS=[.5,.6,.7,1,2,3,6]
WINDOWS={'6m':('2026.04.01','2026.10.02'),'1y':('2025.10.01','2026.10.02'),'3y':('2023.10.01','2026.10.02'),'5y':('2021.10.01','2026.10.02')}
NAMES={'T':'XAU Trend Progression','S':'XAU Slow Trend'}
BASELINES={'T':3,'S':6}
def case(kind,rr):
 c={f:0 for f in FIELDS};c.update(module=1 if kind=='T' else 2,tf=240,rr=rr,maxpos=1);return c
def enrich(name,rows):
 for r in rows:
  d=read_ledger(name,r['index']);p=d.net_profit;wins=p[p>0];losses=p[p<0]
  R=p/d.actual_risk
  r['details']=dict(full_tp_rate_pct=round(100*(d.exit_reason==5).mean(),2) if len(d) else None,
    positive_sl_count=int(((d.exit_reason==4)&(p>0)).sum()),positive_sl_rate_pct=round(100*((d.exit_reason==4)&(p>0)).mean(),2) if len(d) else None,
    avg_winning_R=float(R[p>0].mean()) if len(wins) else None,avg_losing_R=float(R[p<0].mean()) if len(losses) else None,
    realized_cash_payoff=float(wins.mean()/-losses.mean()) if len(wins) and len(losses) else None,
    risk_ratio_mean=float((d.actual_risk/d.requested_risk).mean()) if len(d) else None,risk_ratio_max=float((d.actual_risk/d.requested_risk).max()) if len(d) else None,
    risk_overshoot_count=int((d.actual_risk>d.requested_risk+.01).sum()),boundary=int(d.test_end.sum()),positions=len(d),
    gross_win_rate_pct=round(100*(d.gross_profit>0).mean(),2) if len(d) else None,
    gross_winners_turned_net_losers=int(((d.gross_profit>0)&(p<0)).sum()))
 return rows
def parity(kind,rows):
 original=ROOT/('EA-'+kind);plain=ROOT/('EA-'+kind+'-plain');plain.mkdir(exist_ok=True)
 for p in original.glob('*.mqh'):shutil.copy2(p,plain/p.name)
 ext=read(plain/'Extensions.mqh').split('class AuditTrade:')[0]+'\n#define AuditTrade CTrade\n'
 (plain/'Extensions.mqh').write_text(ext,encoding='utf-8');nr.EA=plain
 rr=BASELINES[kind];name='parity-plain-'+kind
 plainrow=batch(name,[case(kind,rr)],*WINDOWS['6m'],model=4,optimize=False,warmup=365)[0]
 ref=next(r for r in rows if r['parameters']['rr']==rr)
 a=read_ledger(name);b=read_ledger(ref.get('native_batch',kind+'-v2-6m'),ref.get('native_index',ref['index']))
 cols=['open_epoch','close_epoch','side','volume','open_price','close_price','initial_sl','initial_tp','net_profit','exit_reason']
 exact=len(a)==len(b) and np.allclose(a[cols].to_numpy(),b[cols].to_numpy(),rtol=0,atol=1e-8)
 result=dict(exact=bool(exact),plain_net=plainrow['stats']['net'],instrumented_net=ref['stats']['net'],positions=len(a),scope='Same locked source/settings/target/warm-up. Logging subclass removed; all trade times, sides, prices, SL/TP, volumes, net P/L and exit reasons matched.')
 save(ROOT/('PARITY-'+kind+'.json'),result);assert exact,result;nr.EA=original
def window(kind,per):
 if kind=='T' or (per=='6m' and (OUT/(kind+'-v2-'+per)/'results.json').exists()):
  name=kind+'-v2-'+per;rows=enrich(name,batch(name,[case(kind,rr) for rr in TARGETS],*WINDOWS[per],model=4,optimize=True,warmup=365))
  for r in rows:r['native_batch']=name;r['native_index']=r['index']
  return rows
 # At most two local compute passes at once, to keep the PC responsive.
 rows=[]
 for start in range(0,len(TARGETS),2):
  name=f'{kind}-v3-{per}-chunk{start//2}';part=enrich(name,batch(name,[case(kind,rr) for rr in TARGETS[start:start+2]],*WINDOWS[per],model=4,optimize=True,warmup=365))
  for r in part:r['native_batch']=name;r['native_index']=r['index'];r['index']+=start
  rows+=part
 return rows
def main():
 result=load(ROOT/'RESULTS.json') if (ROOT/'RESULTS.json').exists() else {}
 with (TESTER/'gold-targets.lock').open('a+b') as handle:
  handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
  try:
   for kind in ['T','S']:
    nr.EA=ROOT/('EA-'+kind);result.setdefault(kind,{})
    for per in WINDOWS:
     rows=window(kind,per)
     result[kind][per]=rows;save(ROOT/'RESULTS.json',result)
     if per=='6m':parity(kind,rows)
    # Predeclared screen/selection; no post-hoc optimisation.
    candidates=[]
    for i,rr in enumerate(TARGETS):
     a,b=result[kind]['1y'][i],result[kind]['5y'][i]
     passed=all(r['clean'] and r['stats']['net']>0 and r['net']['profit_factor']>=1.2 and (r['stats']['sharpe'] or 0)>0 and r['stats']['trades']>=minimum for r,minimum in [(a,20),(b,30)])
     if passed:candidates.append(i)
    win=max(candidates,key=lambda i:(result[kind]['1y'][i]['net']['win_rate_pct'],result[kind]['5y'][i]['net']['profit_factor'],result[kind]['1y'][i]['stats']['return_pct']/max(result[kind]['1y'][i]['stats']['equity_dd_pct'],.01))) if candidates else None
    balanced=max(candidates,key=lambda i:(min(result[kind][p][i]['stats']['sharpe'] for p in ['1y','5y']),result[kind]['5y'][i]['net']['profit_factor'],-result[kind]['1y'][i]['net']['equity_dd_pct'])) if candidates else None
    picks=load(ROOT/'PICKS.json') if (ROOT/'PICKS.json').exists() else {}
    observed=max(range(len(TARGETS)),key=lambda i:result[kind]['1y'][i]['net']['win_rate_pct'])
    picks[kind]=dict(screened_targets=[TARGETS[i] for i in candidates],highest_win_rate=None if win is None else TARGETS[win],balanced=None if balanced is None else TARGETS[balanced],highest_observed_win_rate=TARGETS[observed],observed_scope='Descriptive highest one-year win rate, regardless of PF/clean/stability screen. Not a passed candidate.',scope='Historical sensitivity screen; not independently validated or approved for live deployment')
    save(ROOT/'PICKS.json',picks)
    # Native scalar charts of original, high-win and balanced variants; do not overlay ledgers.
    targets=list(dict.fromkeys([BASELINES[kind],TARGETS[observed]]+[TARGETS[i] for i in [win,balanced] if i is not None]))
    charts={}
    for rr in targets:
     name=f'chart-{kind}-{rr:g}R-1y';r=batch(name,[case(kind,rr)],*WINDOWS['1y'],model=4,optimize=False,warmup=365)[0]
     ref=result[kind]['1y'][TARGETS.index(rr)];assert abs(r['stats']['net']-ref['stats']['net'])<.01,(name,r['stats'],ref['stats']);charts[str(rr)]=name
    save(ROOT/('CHARTS-'+kind+'.json'),charts)
   trials=sum(len(load(p)['cases']) for p in OUT.glob('*/manifest.json'))
   if (ROOT/'RESOURCE RESUME.json').exists():trials+=load(ROOT/'RESOURCE RESUME.json')['extra_case_attempts']
   save(ROOT/'TRIALS.json',dict(native_attempts=trials,unique_target_settings=14,scope='All runs, failed compile cases, resource-resume repeat and extra baseline/chart checks counted. Overlapping windows are not independent tests.'))
   status('TARGET NATIVE STUDY COMPLETE',trials=trials)
  finally:handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
if __name__=='__main__':main()
