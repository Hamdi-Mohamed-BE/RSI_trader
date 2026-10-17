"""Post-freeze statistics; no tuning or live publication."""
from pathlib import Path
from datetime import datetime,timezone
import ast,csv,gzip,html,importlib.util,json,math,sys
import numpy as np
import pandas as pd
import runner as r
import search_plan as sp
R=r.R;B=r.B;CFG=r.CFG
cp_path=B.parent/'Calyx Research Pipeline/calyx_pipeline.py'
spec=importlib.util.spec_from_file_location('calyx_audit',cp_path);cp=importlib.util.module_from_spec(spec);sys.modules[spec.name]=cp;spec.loader.exec_module(cp)
# Reuse the established vectorised MC and prop engine adapters, not their old study.
MC_SOURCE=B/'Matteo Golden Trio Raw 2026-10-06/Pipeline 2026-10-07 R3/finish.py'
tree=ast.parse(MC_SOURCE.read_text())
nodes=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in ['daily','samples','summary_paths','bootstrap','ftmo']]
assert len(nodes)==5
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(MC_SOURCE)+'::reused-statistics','exec'),globals())
NAMES={'gold':'Gold eighth-range rejection','us100':'US100 time-cycle gate','btc':'BTC weekly quartile rejection'}

def norm(q):
 trades=[dict(t,net_profit=t['net'],open_time=datetime.fromtimestamp(t['open_epoch'],timezone.utc).replace(tzinfo=None).isoformat(),close_time=datetime.fromtimestamp(t['close_epoch'],timezone.utc).replace(tzinfo=None).isoformat()) for t in q['trades']]
 return dict(trades=trades,start=q['start'],end=q['end'])

def cost_stress(q):
 folder=R/'native'/q['stage'];index=str(q['index'])
 quotes=pd.read_csv(folder/(index+'-quotes.csv'));deals=pd.read_csv(folder/(index+'-deals.csv'))
 assert quotes.deal.is_unique and set(deals.deal)<=set(quotes.deal),'No complete transaction quote evidence'
 mult=100 if q['bot']=='gold' else 1
 spreads=((quotes.ask-quotes.bid)*quotes.volume*mult).groupby(quotes.position_id).sum().to_dict()
 ts=sorted(q['trades'],key=lambda t:t['open_epoch']);signals=q['signals'];cost=[];adverse=[];commission=[]
 for t,s in zip(ts,signals):
  side=1 if t['side']=='Long' else -1
  expected=side*(t['close_price']-t['open_price'])*t['volume']*mult
  assert abs(expected-t['gross'])<.04*t['exit_legs'],'Contract cash conversion failed'
  slip=max(0,side*(t['open_price']-float(s['requested_entry'])))*t['volume']*mult
  fees=-min(0,t['commission']+t['fee']);cost.append(spreads[t['position_id']]+fees+slip);adverse.append(slip);commission.append(fees)
 pnl=np.array([t['net'] for t in ts]);cost=np.asarray(cost);rows=[]
 for multiple in [1,2]:
  p=pnl-multiple*cost
  rows.append(dict(extra_cost_multiple=multiple,mean_extra_cash=float(np.mean(multiple*cost)),net_profit=float(p.sum()),return_pct=float(p.sum()/100),pf=cp.profit_factor(p),win_rate=float(np.mean(p>0)*100)))
 return r.safe(dict(status='measured',mean_roundtrip_spread_cash=float(np.mean(list(spreads.values()))),mean_adverse_entry_slippage_cash=float(np.mean(adverse)),mean_commission_cash=float(np.mean(commission)),scenarios=rows,
  scope='Algebraic extra1x/2x recorded transaction-event quote spread + commissions + adverse requested-versus-filled entry slippage, above native costs. Quotes observed at transaction callbacks, not a claim of exchange orderbook fills. No invented spreads. Different exits/gap paths not replayed.'))

def chronological_thirds(q):
 a=pd.Timestamp(q['start']);b=pd.Timestamp(q['end']);rows=[]
 for i in range(3):
  start=a+(b-a)*i/3;end=a+(b-a)*(i+1)/3
  values=[t['net'] for t in q['trades'] if start.timestamp()<=t['close_epoch']<end.timestamp()]
  rows.append(dict(start=start.isoformat(),end_exclusive=end.isoformat(),trades=len(values),net_profit=sum(values),pf=cp.profit_factor(values)))
 return r.safe(rows)

def robustness(bot,q,full):
 f=r.load(R/(bot+' FROZEN.json'));sample=norm(q);_,returns,_=daily(sample['trades'],sample['start'],sample['end'])
 sr=cp.sharpe_statistics(list(returns),f['counted_trials'],365)
 mc=bootstrap(sample,261009+list(sp.RAW).index(bot));stress=cost_stress(q);thirds=chronological_thirds(q)
 profits=[t['net'] for t in q['trades']];recent=cp.profit_factor(profits[len(profits)//2:])
 checks=dict(raw_gate_passed=f['raw_gate_passed'],older_validation_eligible=f['validation_eligible'],oos_clean=q['clean'],minimum30=len(profits)>=30,
  positive=sum(profits)>0,pf_above1=(q['metrics']['pf'] or 0)>1,bootstrap_probability95=(mc.get('probability_profit_pct') or 0)>=95,
  bootstrap_p05_return_positive=(mc.get('return_p05_pct') or -1)>0,bootstrap_pf_p05_above1=(mc.get('profit_factor_p05') or 0)>1,
  deflated_sharpe95=sr['deflated_sharpe_pct']>=95,two_profitable_calendar_thirds=sum(x['net_profit']>0 for x in thirds)>=2,
  recent_half_pf_above1=recent>1,total_breach_below5=(mc.get('closed_pnl_total_breach_pct') or 0)<5,
  measured_cost_stress_positive=all((s['pf'] or 0)>1 and s['net_profit']>0 for s in stress['scenarios']))
 verdict='FORWARD-TEST RESEARCH CANDIDATE' if all(checks.values()) else ('WATCH / NOT VALIDATED' if checks['positive'] and checks['pf_above1'] else 'REJECT FROZEN CANDIDATE')
 return r.safe(dict(verdict=verdict,gates=checks,sharpe=sr,monte_carlo=mc,cost_stress=stress,calendar_thirds=thirds,
  recent_half_pf=recent,ftmo=ftmo(sample,261109+list(sp.RAW).index(bot)),
  five_year_context_mc=bootstrap(norm(full),261209+list(sp.RAW).index(bot)),
  reuse=dict(source=str(MC_SOURCE),sha256=r.sha(MC_SOURCE),functions=['daily','samples','summary_paths','bootstrap','ftmo']),
  caution='Previously inspected retrospective validation and model-family selection risk; analytic DSR approximation counts correlated and prior raw trials. Prop simulation closed-PnL proxy, no native floating equity or precise CE(S)T resets. No promotion.'))

def graph(a,b):
 curves=[]
 for q in [a,b]:
  z=norm(q);days,ret,p=daily(z['trades'],z['start'],z['end']);curves.append(np.r_[10000,10000+np.cumsum(p)])
 low=min(x.min() for x in curves);high=max(x.max() for x in curves);span=max(1,high-low);parts=[]
 for value in np.linspace(low,high,5):
  y=250-(value-low)/span*220;parts.append(f'<line x1="80" x2="980" y1="{y}" y2="{y}" stroke="#294338"/><text x="70" y="{y+5}" text-anchor="end" fill="#bfd0c8">${value:,.0f}</text>')
 for values,color in zip(curves,['#fdc77c','#75f1c9']):
  points=' '.join(f'{80+i/(len(values)-1)*900:.1f},{250-(v-low)/span*220:.1f}' for i,v in enumerate(values))
  parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{points}"/>')
 return '<svg viewBox="0 0 1040 300" role="img" aria-label="Original versus frozen candidate closing balance"><title>Retrospective two-year validation, original amber, candidate green</title>'+''.join(parts)+'<text x="80" y="285" fill="#bfd0c8">2024-10-09</text><text x="840" y="285" fill="#bfd0c8">2026-10-08</text></svg>'

def f(x,n=2):return '—' if x is None or not math.isfinite(x) else f'{x:,.{n}f}'
def table(rows):
 heads=['Version / window','Dates (end exclusive)','Trades','/month','/market day','Return','PF','Win rate','Equity DD','Sharpe','W/L streak']
 body=[]
 for label,start,end,m in rows:
  days=(pd.Timestamp(end)-pd.Timestamp(start)).days
  values=[label,start+' → '+end,str(m['trades']),f(m.get('trades_per_month',m['trades']/(days/30.436875))),f(m.get('trades_per_market_day')),
   f(m['return_pct'])+'%',f(m['pf']),f(m['win_rate'],1)+'%',f(m['equity_dd_pct'])+'%',f(m.get('sharpe_daily_equity')),str(m['win_streak'])+'/'+str(m['loss_streak'])]
  body.append('<tr>'+''.join('<td>'+html.escape(x)+'</td>' for x in values)+'</tr>')
 return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+x+'</th>' for x in heads)+'</tr></thead><tbody>'+''.join(body)+'</tbody></table></div>'

def portfolio(evaluations):
 from app.portfolio_analytics import allocation_replay,performance
 days=pd.date_range(*CFG['oos'],inclusive='left');ret={}
 for bot,e in evaluations.items():
  z=norm(e['OOS']);_,values,_=daily(z['trades'],z['start'],z['end']);ret[bot]=values
 pair={a+' vs '+b:float(np.corrcoef(ret[a],ret[b])[0,1]) for i,a in enumerate(ret) for b in list(ret)[i+1:]}
 source=B.parent/'EA store/data/portfolio-risk-ledgers.json';catalog=B.parent/'EA store/data/portfolios.json'
 saved=r.load(source)['current14-orb05']['long'];start=CFG['oos'][0];end='2026-10-06';extra={}
 for bot,e in evaluations.items():
  mult=100 if bot=='gold' else 1;extra[bot]=[]
  for t in e['OOS']['trades']:
   unit=abs(t['open_price']-t['sl'])*mult
   if unit>0:extra[bot].append(dict(key='research-'+bot,op=t['open_epoch'],cl=t['close_epoch'],unit_risk=unit,unit_gross=t['gross']/t['volume'],unit_comm=t['commission']/t['volume'],unit_swap=t['swap']/t['volume'],risk_weight=1,news=False))
 baseline,meta=allocation_replay(saved,start,end,'percent',.5,10000)
 base_stats=performance(baseline,start,end)[0];rows={}
 for bot,addition in list(extra.items())+[('all-three',[t for xs in extra.values() for t in xs])]:
  # Reference0.5% portfolio budget and1% new ideas, using explicit per-entry weights.
  q,m=allocation_replay(saved+[t|dict(risk_weight=2) for t in addition],start,end,'percent',.5,10000)
  rows[bot]=dict(metrics=performance(q,start,end)[0],allocation=m)
 return r.safe(dict(candidate_daily_correlations=pair,contextual_current14_orb05=dict(start=start,end_exclusive=end,baseline=base_stats,additions=rows,
  source_hashes={str(source):r.sha(source),str(catalog):r.sha(catalog)},
  scope='Contextual retrospective fractional-lot entry/exit allocation replay: saved15-EA current14+ORB05 roster at0.5%, new ideas1%. It endsOct6 because saved coverage ends there; the required strategy validation still endsOct9. No broker lot floors, shared native fills, margin, intraday equity or installed guards. Historical-risk hourly calibration is not new unseen evidence.'),
  current_portfolio_validation='NOT a native shared-account validation or deployment recommendation.'))

def export_csv(q,filename):
 z=norm(q)
 with (R/filename).open('w',newline='',encoding='utf-8-sig') as file:
  fields=['position_id','open_time','close_time','side','volume','open_price','close_price','sl','tp','gross','commission','swap','net','exit_legs']
  writer=csv.DictWriter(file,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(z['trades'])

def main():
 evaluations={b:r.load(R/(b+' EVALUATION.json')) for b in sp.RAW};audits={};body=[]
 for bot,e in evaluations.items():
  r.status('Robustness calculations '+bot);audits[bot]=robustness(bot,e['OOS'],e['5y']);r.save(R/(bot+' ROBUSTNESS.json'),audits[bot])
 joint=portfolio(evaluations);r.save(R/'PORTFOLIO CONTEXT.json',joint)
 body+=['<h1>Three Gann-inspired ideas · full research pipelines</h1><p>Frozen end9October2026 · Gold / US100 / Bitcoin · separate$10,000accounts ·1% planned current-balance risk, floored broker lots.</p>',
 '<aside>Research only. No live bots, BATs, website settings or Git push. Final two-year validation2024-10-09 →2026-10-09 is retrospective: it was already inspected in raw research. Failed raw/older-validation/statistical gates remain failed. Native Model4/150ms includes broker costs, but pre2026 history uses generated ticks; fresh2026 is checked separately.</aside>',
 '<h2>Two-year validation: original versus frozen finalist</h2>']
 rows=[]
 for b,e in evaluations.items():
  for key,label in [('Raw OOS','Original'),('OOS','Frozen finalist')]:
   q=e[key];rows.append((NAMES[b]+' · '+label,q['start'],q['end'],q['metrics']))
 body.append(table(rows))
 for bot,e in evaluations.items():
  fz=r.load(R/(bot+' FROZEN.json'));a=audits[bot];body.append('<section id="'+bot+'"><h2>'+NAMES[bot]+' — '+a['verdict']+'</h2>'+graph(e['Raw OOS'],e['OOS']))
  body.append('<h3>All periods, matched risk and costs</h3>');rows=[]
  for window in ['5y','3y','OOS','1y','6m','3m','2026']:
   for key,label in [('Raw OOS' if window=='OOS' else 'Raw '+window,'Original'),(window,'Finalist')]:
    q=e[key];start=q.get('start',q.get('window',[None,None])[0]);end=q.get('end',q.get('window',[None,None])[1])
    if isinstance(start,str):start=start.replace('.','-');end=end.replace('.','-')
    rows.append((label+' '+window,start,end,q['metrics']))
  body.append(table(rows));body.append('<h3>Older native development and selection validation</h3>'+table([(k,e[k]['start'],e[k]['end'],e[k]['metrics']) for k in ['DEV','VALIDATION']]))
  body.append('<p>Raw gate passed: '+str(fz['raw_gate_passed'])+'; older validation eligible: '+str(fz['validation_eligible'])+'. '+html.escape(fz['status'])+'</p>')
  body.append('<h3>Frozen settings</h3><pre>'+html.escape(json.dumps(fz['parameters'],indent=2))+'</pre><p>'+str(fz['unique_development_configurations'])+' unique development configurations, '+str(fz['total_screening_passes'])+' screening passes; '+str(fz['counted_trials'])+' conservative counted trials. Profitable-neighbour shares: '+', '.join(f'{p["profitable_neighbour_share"]*100:.0f}%' for p in fz['plateaus'])+'.</p>')
  body.append('<h3>10,000-path Monte Carlo and measured costs</h3><pre>'+html.escape(json.dumps(a,indent=2))+'</pre>')
  body.append('<h3>Post-freeze risk/delay checks</h3>'+table([(k,e[k]['start'],e[k]['end'],e[k]['metrics']) for k in ['Risk 0.5%','Delay 300ms']]))
  body.append('<p>History quality:5Y '+html.escape(e['5y']['native']['history_quality'])+',3Y '+html.escape(e['3y']['native']['history_quality'])+',2Y '+html.escape(e['OOS']['native']['history_quality'])+',fresh2026 '+html.escape(e['2026']['native']['history_quality'])+'.</p>')
  filename=bot+'-final-5y-trades.csv';export_csv(e['5y'],filename);body.append('<p><a href="'+filename+'">Download all five-year finalist trades</a></p>')
  tests=r.load(R/(bot+' DEVELOPMENT TABLE.json'))
  for stage in dict.fromkeys(x['stage'] for x in tests):
   rs=[x for x in tests if x['stage']==stage];body.append('<details><summary>'+html.escape(stage)+f' · {len(rs)} screening cases</summary>'+table([(json.dumps(q['parameters'],separators=(',',':')),q['start'],q['end'],q['metrics']) for q in rs])+'</details>')
  body.append('</section>')
 body.append('<h2>Raw gates and controls</h2><pre>'+html.escape(json.dumps(r.load(R/'RAW GATES.json'),indent=2))+'</pre>')
 body.append('<h2>Portfolio overlap: contextual allocation replay only</h2><pre>'+html.escape(json.dumps(joint,indent=2))+'</pre>')
 body.append('<h2>Settings legend and omitted dimensions</h2><pre>'+html.escape(json.dumps({k:v for k,v in sp.freeze().items() if k in ['code_labels','omitted']},indent=2))+'</pre>')
 body.append('<h2>Evidence limits</h2><p>Gold and BTC are mechanical prior-range hypotheses, not a verified original Gann strategy. US100 is an H1 EMA crossover with a confirmed-pivot clock, not the live Nasdaq5m opening model. Win rates count net whole positions, including fees and partials. Native tick-equity DD differs from MonteCarlo closed-balance DD; charts use closing cash. Sharpe is daily mark-to-market equity,252weekdays forGold/US100 and365days forBTC; DSR/MC use calendar-day closed cash with no-trade days. Windows are start inclusive/end exclusive; no end liquidation is allowed for selection.</p><p>Prop metrics are a closed-PnL proxy using the existing simulator, not actual FTMO pass odds. Source: <a href="https://ftmo.com/en/2-step-challenge/">FTMO2-Step official objectives</a>, checked9October2026. Floating losses, exact reset clocks, changing regimes, lot/margin constraints and future transaction costs can worsen results. A failed candidate cannot be swapped for a recent winner; a new search needs a new documented experiment.</p>')
 style='body{background:#071713;color:#eafff3;font:16px system-ui;max-width:1450px;margin:30px auto;padding:0 20px}h1,h2{color:#75f1c9}p{line-height:1.6}aside{border:1px solid #927839;color:#ffdfa0;border-radius:12px;padding:20px}.scroll{overflow-x:auto}table{border-collapse:collapse;min-width:1150px;width:100%;font-size:14px}td,th{padding:12px;text-align:right;border-bottom:1px solid #294338;white-space:nowrap}td:first-child,th:first-child{text-align:left}pre{background:#10281e;white-space:pre-wrap;overflow-wrap:anywhere;padding:18px;border-radius:10px;font-size:13px}svg{width:100%;margin:20px 0}section{margin-top:45px}a{color:#75f1c9}details{margin:14px 0}'
 (R/'Results.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Gann-inspired three pipeline results</title><style>'+style+'</style><main>'+''.join(body)+'</main></html>',encoding='utf-8')
 r.save(R/'RESULTS.json',dict(audits=audits,portfolio=joint,live_changes=False,push=False))
 r.status('All research pipelines analysed and report generated; verification pending')
if __name__=='__main__':main()
