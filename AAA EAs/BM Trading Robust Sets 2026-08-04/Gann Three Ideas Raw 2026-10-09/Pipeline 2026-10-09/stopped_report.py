"""Publish completed raw gates and raw-risk diagnostics; do not imply optimisation."""
import html,json,math
import numpy as np
import pandas as pd
import pipeline as p
import runner as r
import search_plan as sp
import finish as f
R=r.R

def native_raw(bot,window):
 q=p.raw_result(bot,window)
 return q|dict(start=q['window'][0].replace('.','-'),end=q['window'][1].replace('.','-'),bot=bot)

def recent_slice(q,start):
 a=pd.Timestamp(start,tz='UTC').timestamp();before=10000+sum(t['net'] for t in q['trades'] if t['close_epoch']<a)
 ts=[t for t in q['trades'] if t['close_epoch']>=a];net=[t['net'] for t in ts];wins=[x for x in net if x>0];loss=[x for x in net if x<0]
 eq=pd.read_csv(R/'native'/q['tag']/'equity.csv');v=np.r_[before,eq[eq.epoch>=a].equity.to_numpy()]
 peak=np.maximum.accumulate(v);dd=float(np.max((peak-v)/peak)*100)
 m=q['metrics'].copy();w,l=f.cp.streaks(net);days=(pd.Timestamp(q['end'])-pd.Timestamp(start)).days
 m.update(trades=len(ts),net_profit=sum(net),return_pct=sum(net)/before*100,pf=sum(wins)/-sum(loss) if loss else None,win_rate=len(wins)/len(ts)*100 if ts else None,
  equity_dd_pct=dd,win_streak=w,loss_streak=l,trades_per_month=len(ts)/(days/30.436875),sharpe_daily_equity=None,
  trades_per_market_day=len(ts)/(days if q['bot']=='btc' else len(pd.bdate_range(start,pd.Timestamp(q['end'])-pd.Timedelta(days=1)))))
 return dict(start=start,end=q['end'],metrics=m,opening_balance=before,basis='Descriptive continuous3Yaccount slice; sampled5min equity DD, not a fresh native window or final locked OOS.')

def main():
 gates=p.gates();parity=r.load(R/'PARITY.json');assert set(parity)==set(sp.RAW) and all(v['exact'] for v in parity.values())
 state=r.load(R/'RAW STATUS.json');assert len(state['complete'])==state['total']==20 and not state['failed']
 mc={};cost={};table=[];pieces=[]
 for bot in sp.RAW:
  mc[bot]={}
  for window in ['3y','5y']:
   q=native_raw(bot,window);sample=f.norm(q)
   mc[bot][window]=f.bootstrap(sample,261509+list(sp.RAW).index(bot)+({'3y':0,'5y':100}[window]))
  q=r.load(R/'native'/('parity-v2-'+bot)/'results.json')[0]
  cost[bot]=f.cost_stress(q)
  mc[bot]['prop_proxy']=f.ftmo(f.norm(q),261609+list(sp.RAW).index(bot))
  _,ret,_=f.daily(f.norm(q)['trades'],q['start'],q['end'])
  mc[bot]['deflated_sharpe']=f.cp.sharpe_statistics(list(ret),42+7,365)
  for window in ['5y','3y','1y','6m']:
   q=native_raw(bot,window);table.append((f.NAMES[bot]+' · '+window,q['start'],q['end'],q['metrics']))
  base=native_raw(bot,'3y');s=recent_slice(base,'2026-07-09');table.append((f.NAMES[bot]+' ·3m slice',s['start'],s['end'],s['metrics']))
  s=recent_slice(base,'2024-10-09');table.append((f.NAMES[bot]+' ·2y raw slice',s['start'],s['end'],s['metrics']))
  ctrl=[]
  for window in ['5y','3y']:
   q=p.raw_result(bot,window,True);ctrl.append(('Signal control '+window,q['window'][0].replace('.','-'),q['window'][1].replace('.','-'),q['metrics']))
   if bot=='us100':
    q=r.load(R/'native'/f'allrr05-gp-ustec-random-cycle-{window}-raw/results.json')
    ctrl.append(('Seeded random clock '+window,q['window'][0].replace('.','-'),q['window'][1].replace('.','-'),q['metrics']))
  failed={window:[k for k,v in gates[bot][window]['checks'].items() if not v] for window in ['3y','5y']}
  pieces+=['<section><h2>'+f.NAMES[bot]+' — STOPPED AT RAW GATE</h2><p>Failed checks:</p><pre>'+html.escape(json.dumps(failed,indent=2))+'</pre><h3>Controls at identical1% risk</h3>'+f.table(ctrl),
   '<h3>Raw native3Y/5Y MonteCarlo,10,000paths</h3><pre>'+html.escape(json.dumps(mc[bot],indent=2))+'</pre>',
   '<h3>Measured extra-cost stress on exact3Y raw reproduction</h3><pre>'+html.escape(json.dumps(cost[bot],indent=2))+'</pre></section>']
  f.export_csv(native_raw(bot,'5y'),bot+'-raw-5y-trades.csv')
 r.save(R/'RAW MONTE CARLO.json',mc);r.save(R/'RAW COST STRESS.json',cost)
 status=dict(rules_and_source=True,raw_native_windows_complete=True,control_gate_complete=True,raw_gate_passed=False,
  stopped_bots=list(sp.RAW),optimisation_performed=False,final_optimised_two_year_validation_performed=False,
  raw_monte_carlo_diagnostics_performed=True,raw_native_parity_complete=True,
  continuation='Awaiting optional user choice for exploratory continuation; saved pipeline says stop failed raw candidates.',
  live_changes=False,push=False)
 r.save(R/'PIPELINE STATUS.json',status)
 rows=[]
 for bot in sp.RAW:
  a=gates[bot]['3y']['raw'];b=gates[bot]['5y']['raw']
  rows.append('<tr><td>'+f.NAMES[bot]+'</td><td>'+f.f(a['pf'])+'</td><td>'+f.f(a['return_pct'])+'%</td><td>'+str(a['trades'])+'</td><td>'+f.f(b['pf'])+'</td><td>'+f.f(b['return_pct'])+'%</td><td>'+str(b['trades'])+'</td><td>FAIL</td></tr>')
 head='<h1>Three Gann-inspired ideas: pipeline gate results</h1><p>Native Exness CFDs · through 8 October 2026 · independent $10,000 accounts · 1% nominal current closed-balance stop risk, floored broker lots · 150 ms delay.</p>'
 head+='<aside>All three fail at least one saved raw-gate requirement. Optimisation is NOT completed or promoted. The saved pipeline stops failed raw candidates; exploratory continuation needs the user choice. Twenty native raw/control runs plus three final trade-parity confirmations are complete. Raw Monte Carlo is additional risk diagnostics, not an optimised-finalist validation.</aside>'
 head+='<h2>Decision summary</h2><div class="scroll"><table><tr><th>Idea</th><th>3Y PF</th><th>3Y return</th><th>3Y trades</th><th>5Y PF</th><th>5Y return</th><th>5Y trades</th><th>Raw gate</th></tr>'+''.join(rows)+'</table></div>'
 head+='<p>Gold misses PF 1.15; BTC misses PF 1.15 and loses over five years; US100 passes profit/PF checks but loses the comparator test to a fixed seeded random clock with equal eligible-bar exposure. One stronger placebo does not prove there is no edge, but it does not support a special 8/16/32 clock advantage. No control is hidden to manufacture a pass.</p>'
 head+='<h2>All requested raw windows and recent diagnostics</h2>'+f.table(table)
 head+='<p>5Y: 2021-10-09 → 2026-10-09; 3Y: 2023-10-09 → 2026-10-09; 1Y: 2025-10-09 → 2026-10-09; 6M: 2026-04-09 → 2026-10-09. The 3M/2Y rows are descriptive slices of continuous three-year runs with inherited balance; their DD is sampled equity, not a separate native tick maximum. They are not optimised or untouched OOS results. A new $10,000 deposit is used for each independent native raw window, so returns do not simply scale the earlier 0.5% study.</p>'
 head+='<p>Native real-tick labels: 5Y 15%, 3Y 25%, 1Y 76%, 6M 100%. Pre-2026 data use generated ticks from broker M1 history. The real-tick model does not make missing history real. Net whole-position costs, trades/month, market-day frequency and win/loss streaks are reported; weekends count for BTC. Sharpe uses 252 weekday equity returns for gold/US100 and 365 calendar-day equity returns for BTC.</p>'
 tail='<h2>Mandatory chronology and next research steps</h2><p>Development: 2021-10-09 → 2023-10-09; older validation: 2023-10-09 → 2024-10-09; final two-year retrospective validation: 2024-10-09 → 2026-10-09. The final two years were already inspected in raw research; never call them untouched. The staged search plan is prepared but has not run. If exploration is approved, choose one stable finalist before that final window; do not choose using the last year, six months or three months.</p>'
 tail+='<details><summary>Prepared staged search scope and exclusions</summary><pre>'+html.escape(json.dumps(sp.freeze(),indent=2))+'</pre></details>'
 tail+='<h2>Verification</h2><pre>'+html.escape(json.dumps(parity,indent=2))+'</pre><p>A one-tick target-rounding mismatch was detected in the first US100 research-copy parity test. The copy was corrected to calculate fixed R after stop rounding. All three now reproduce fresh original-source three-year trades exactly. A gold swap charge changed by $0.09 between broker snapshots; the same drift occurs in the untouched original source. Initial dated reports remain unchanged and preliminary audit records are preserved.</p>'
 tail+='<p>Prop simulations use the existing FTMO 2-Step closed-PnL engine: <a href="https://ftmo.com/en/2-step-challenge/">official objectives</a>, checked 9 October 2026. They do not replay floating equity, exact CE(S)T resets or installed guards and are not forecast pass odds. Native equity DD and closed-cash Monte Carlo DD are different measures. Extra-cost stress uses recorded transaction quotes, fees and entry slippage in the exact three-year reproductions, not invented five-year spreads. No live EAs, BATs, website or Git changes.</p>'
 tail+='<p>Trade downloads: '+', '.join('<a href="'+bot+'-raw-5y-trades.csv">'+f.NAMES[bot]+'</a>' for bot in sp.RAW)+'</p>'
 style='body{background:#071713;color:#eafff3;font:16px system-ui;max-width:1450px;margin:30px auto;padding:0 20px}h1,h2{color:#75f1c9}p{line-height:1.65}aside{border:1px solid #927839;color:#ffdfa0;border-radius:12px;padding:20px}.scroll{overflow-x:auto}table{border-collapse:collapse;min-width:1100px;width:100%;font-size:14px}td,th{padding:12px;text-align:right;border-bottom:1px solid #294338;white-space:nowrap}td:first-child,th:first-child{text-align:left}pre{background:#10281e;white-space:pre-wrap;overflow-wrap:anywhere;padding:18px;border-radius:10px;font-size:13px}section{margin-top:45px}a{color:#75f1c9}details{margin:14px 0}'
 (R/'Results.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Three Gann pipeline raw-gate results</title><style>'+style+'</style><main>'+head+''.join(pieces)+tail+'</main></html>',encoding='utf-8')
 r.save(R/'RESULTS.json',dict(status=status,raw_gates=gates,raw_monte_carlo=mc,raw_cost_stress=cost))
 print('Gate-stopped research report written; no optimisation or live changes',flush=True)
if __name__=='__main__':main()
