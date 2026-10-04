import base64,gzip,html,io
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from native import ROOT,OUT,load,save,ledger
from analyse import reference,ORIGINAL

LABELS={'full-5y':'5 years','full-3y':'3 years','parity-1y':'Last year (parity)','real-2026':'2026 real ticks','delay500-1y':'Last year / 500ms','delay500-6m':'6 months / 500ms'}
def fmt(x,n=2):return '—' if x is None else f'{x:.{n}f}'
def table(headers,rows):return '<div class="table"><table><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</table></div>'
def result(label,r):
 s=r['stats'];return [label,r['start']+' → '+r['end']+' exclusive',f"{s['return_pct']:+.2f}%",fmt(s['pf'],3),fmt(s['win_pct'],1)+'%',fmt(s['equity_dd_pct'])+'%',s['trades'],s['trades_per_month'],s['trades_per_day'],fmt(s['sharpe']),f"{s['max_win_streak']}/{s['max_loss_streak']}",r['native_metrics']['history_quality']]
def curves(row,ax,ddax,colour,label):
 d=ledger(row).sort_values(['close_epoch','position_id']);dates=[pd.Timestamp(row['start'].replace('.','-'))]+list(pd.to_datetime(d.close_epoch,unit='s'))+[pd.Timestamp(row['end'].replace('.','-'))]
 b=np.r_[10000,10000+d.net_profit.cumsum().to_numpy()];b=np.r_[b,b[-1]];pk=np.maximum.accumulate(b)
 ax.step(dates,b,where='post',color=colour,lw=1.2,label=label);ddax.fill_between(dates,-100*(pk-b)/pk,0,step='post',color=colour,alpha=.5)
 ax.axhline(10000,color='#8ca59c',lw=.7,ls='--');ax.set_ylabel('Closed balance USD');ddax.set_ylabel('Closed balance DD %')
def picture(name,title):return '<section><h2>'+title+'</h2><img alt="'+html.escape(title)+'" src="data:image/png;base64,'+base64.b64encode((ROOT/name).read_bytes()).decode()+'"></section>'

def main():
 rows=load(ROOT/'SUMMARY.json');by={r['stage']:r for r in rows};v=load(ROOT/'SUMMARY VERIFICATION.json');a=load(ROOT/'AUDIT SUMMARY.json');mc=load(ROOT/'RISK-UNIT MC.json');cost=load(ROOT/'MEASURED COST STRESS.json');measure=load(ROOT/'COST MEASUREMENT.json');decision=load(ROOT/'DECISION.json')
 plt.rcParams.update({'figure.facecolor':'#091713','axes.facecolor':'#0e211c','axes.edgecolor':'#315047','text.color':'#eef7f2','axes.labelcolor':'#bdcfca','xtick.color':'#bdcfca','ytick.color':'#bdcfca','grid.color':'#315047','font.size':10})
 fig,axes=plt.subplots(2,3,figsize=(17,8),sharex='col',gridspec_kw={'height_ratios':[2,1]})
 for c,(stage,colour) in enumerate([('full-5y','#ffbd74'),('full-3y','#c9a8ff'),('real-2026','#72f6cb')]):
  curves(by[stage],axes[0,c],axes[1,c],colour,LABELS[stage]);axes[0,c].set_title(LABELS[stage]+' | '+by[stage]['native_metrics']['history_quality'])
  for ax in axes[:,c]:ax.grid(alpha=.25)
 fig.suptitle('Frozen PBD Gold COMBINED | $10k | 1% requested balance risk | NOT VALIDATED\nMixed historical execution ticks. Separate fresh accounts, not one portfolio. Through 1 Oct 2026');fig.autofmt_xdate();fig.tight_layout();fig.savefig(ROOT/'gold-validation-curves.png',dpi=140);plt.close(fig)
 r=by['full-5y'];t=pd.read_csv(io.BytesIO(gzip.decompress((OUT/r['stage']/'0-trace.csv.gz').read_bytes())));t['day']=pd.to_datetime(t.epoch,unit='s').dt.normalize();g=t.groupby('day').agg(low=('equity','min'),high=('equity','max'),balance=('balance','last'))
 pk=np.maximum.accumulate(np.r_[10000,t.equity.to_numpy()])[1:];t['dd']=100*(pk-t.equity)/pk;dd=t.groupby('day').dd.max()
 fig,axes=plt.subplots(2,1,figsize=(13,7),sharex=True,gridspec_kw={'height_ratios':[2,1]});axes[0].fill_between(g.index,g.low,g.high,color='#72d8ff',alpha=.4);axes[0].plot(g.index,g.balance,color='#72d8ff',lw=1);axes[1].fill_between(dd.index,-dd,0,color='#ff927b',alpha=.6);axes[0].set_ylabel('USD');axes[1].set_ylabel('Sampled equity DD %');axes[0].set_title('5-year sampled floating equity: daily min/max from minute samples\nExact native equity DD in table; older execution path largely generated')
 for ax in axes:ax.grid(alpha=.25)
 fig.autofmt_xdate();fig.tight_layout();fig.savefig(ROOT/'gold-validation-floating.png',dpi=140);plt.close(fig)
 annual=sorted([r for r in rows if r['stage'].startswith('annual-')],key=lambda r:r['start'])+[by['parity-1y']]
 fig,axes=plt.subplots(1,2,figsize=(13,5));labels=[r['start'][:4]+'–'+r['end'][:4] for r in annual];returns=[r['stats']['return_pct'] for r in annual];pf=[r['stats']['pf'] for r in annual]
 axes[0].bar(labels,returns,color=['#72f6cb' if x>0 else '#ff927b' for x in returns]);axes[0].axhline(0,color='#8ca59c',lw=.8);axes[0].set_ylabel('Return %');axes[0].set_title('Fresh $10k for each Oct2–Oct2 year')
 axes[1].bar(labels,pf,color=['#72f6cb' if x>1.15 else '#ff927b' for x in pf]);axes[1].axhline(1.15,color='#ffbd74',ls='--',label='Raw screen PF1.15');axes[1].set_ylabel('Net PF');axes[1].legend()
 for ax in axes:ax.grid(axis='y',alpha=.25);ax.tick_params(axis='x',rotation=20)
 fig.suptitle('Historical stability without retuning | same frozen Gold PBD rules');fig.tight_layout();fig.savefig(ROOT/'gold-validation-annual.png',dpi=140);plt.close(fig)
 headers=['Window','Dates','Return','Net PF','Win rate','Native equity DD','Trades','Trades/mo','Trades/weekday','Closed Sharpe','Max W/L run','Tick quality']
 results=[result(LABELS[x],by[x]) for x in ['full-5y','full-3y','parity-1y','real-2026','delay500-1y','delay500-6m']]
 old6,_=reference('XAUUSD-4-6m');results.insert(4,result('6 months / original150ms',old6));annualrows=[result('Independent '+r['start'][:4]+'–'+r['end'][:4],r) for r in annual]
 auditrows=[]
 for stage,q in a.items():
  b=q['bootstrap'];m=q['metrics'];auditrows.append([LABELS[stage],q['verdict'],fmt(m['deflated_sharpe_pct'],1)+'%',fmt(b['probability_profit_pct'],1)+'%',fmt(b['return_p05_pct'])+'%',fmt(b['profit_factor_p05'],3),str(m['win_rate_wilson_95_pct']),q['gates']['bootstrap_return_p05_positive'] and q['gates']['bootstrap_pf_p05_above_1']])
 mcrows=[]
 for stage,q in mc.items():
  for name,b in q.items():mcrows.append([LABELS[stage],name,fmt(b['return_p05_pct'])+'%',fmt(b['return_p50_pct'])+'%',fmt(b['closed_dd_p95_pct'])+'%',fmt(b['pf_p05'],3),fmt(b['historical_profit_frequency_pct'],1)+'%'])
 costrows=[]
 for stage,q in cost.items():
  for name,b in q.items():costrows.append([LABELS[stage],name,f"${b['net']:+,.2f}",fmt(b['return_pct'])+'%',fmt(b['pf'],3)])
 failures=['Historical raw gate FAILED on both3y/5y: negative return, PF below1.15. No random controls, parameter search or promotion started.',
  'This verdict applies to the explicitly frozen Exness tick-volume PBD proxy, NOT every discretionary PBD model or genuine exchange order-flow profile.',
  'Exact original source preserved; fresh parity run matched all66 prior one-year positions, numeric trade fields and modules (deal identifiers excluded). No active EAs, terminals/accounts, BATs, website or Git remote changed.',
  f'Independent reconstruction checked {sum(x["positions"] for x in v):,} positions across overlapping new windows and {sum(x["profile_m1_bars"] for x in v):,} exported M1 profile inputs. Zero nonzero exchange-real-volume bars. Both direction and D-extension rules remain unchanged.',
  'Exness real ticks start Jan2026.5y/3y execution is predominantly generated, with historic M1 spread/tick-volume assumptions. Annual older tests have0% real ticks. Profiles spread M1 quote-count volume uniformly over each bar range, not actual trades at prices. No second data source verifies this.',
  'All windows except disjoint annual comparisons overlap. The candidate was chosen after reviewing12 current asset/module combinations and broader prior ideas. This is a frozen historical extension, NOT an untouched prospective holdout.',
  'DD tables use native tick-path floating-equity drawdown. Closing plots and MC omit floating losses. The sampled equity graph is minute resolution. Neither bootstrap breach outputs nor historic profit frequencies are FTMO/live pass or payout forecasts.',
  'Separate fresh $10k per native run;1% requested pre-cost balance risk with floor lots. Fills/fees/gaps may exceed it. Do not sum independent test returns. Closed Sharpe uses realized daily changes, not native report Sharpe.',
  f'Measured last-year adverse ENTRY friction sum${measure["adverse_entry_usd_sum"]:.2f}; observed p95${measure["adverse_usd_per_lot_p95"]:.4f}/lot. Stress adds one extra such cost per traded lot, on top of costs already present. This is an observed broker entry-friction shock, not independently measured future spread/exit slippage.',
  'Native500ms changes simulated market-order/EA-close delay but not necessarily server-side stop/TP latency. It tests execution sensitivity, not a guaranteed future fill.',
  'Risk-unit MC compounds observed net returns at1%risk, ignoring changing lot floor and signal eligibility. Removal does not regenerate trades that might become eligible after a missed fill. Reshuffle changes DD/streaks, not compounded return.',
  'Canonical measured entry-friction shock, chronological consistency and statistical gates failed or remain insufficient. No true volume-at-price, matched-control advantage, pristine holdout or prospective demo. NOT LIVE ELIGIBLE.'
 ]
 css='body{background:#091713;color:#eef7f2;font:16px/1.55 system-ui;max-width:1450px;margin:auto;padding:36px}h1{font-size:42px}h2,a{color:#72f6cb}p,li{color:#bfd2cb}section{background:#0e211c;border:1px solid #315047;border-radius:18px;padding:24px;margin:24px 0}table{border-collapse:collapse;width:100%;font-size:12px}th,td{padding:10px;text-align:right;border-bottom:1px solid #315047}th:first-child,td:first-child{text-align:left}.table{overflow:auto}img{width:100%}.warning{border-color:#a96351}pre{white-space:pre-wrap;color:#bfd2cb}'
 page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calyx | PBD Gold validation</title><style>'+css+'</style><body><h1>Gold PBD — validation failed</h1><p>Frozen COMBINED version · $10k ·1%requested risk · through1October2026</p><section class="warning"><h2>NOT VALIDATED / DO NOT PROMOTE</h2><p>The recent profit did not hold across older data.3y:'+f" {by['full-3y']['stats']['return_pct']:+.2f}% / PF{by['full-3y']['stats']['pf']:.3f}"+';5y:'+f" {by['full-5y']['stats']['return_pct']:+.2f}% / PF{by['full-5y']['stats']['pf']:.3f}"+'. No optimisation or live changes.</p></section><section><h2>Native historical and execution tests</h2>'+table(headers,results)+'</section>'+picture('gold-validation-curves.png','Extended historical closing balance')+picture('gold-validation-floating.png','5-year sampled floating equity')+'<section><h2>Independent annual starts</h2>'+table(headers,annualrows)+'</section>'+picture('gold-validation-annual.png','Year-by-year stability')+'<section><h2>Statistical diagnostics — not forward forecasts</h2>'+table(['Window','Verdict','DSR12','Historical bootstrap positive','Return p05','PF p05','Win95% interval','Bootstrap gates'],auditrows)+'</section><section><h2>Risk-unit bootstrap, shuffle and missed-fill sensitivity</h2>'+table(['Window','Diagnostic','Return p05','Return median','Closed DD p95','PF p05','Historical positive frequency'],mcrows)+'</section><section><h2>Additional costs from observed broker evidence</h2><p>The95th-percentile recorded adverse entry cost is'+f" ${measure['adverse_usd_per_lot_p95']:.4f}/lot."+' Original costs already included. This is an extra observed entry-friction shock, not measured future spread.</p>'+table(['Window','Stress','Net','Return','Net PF'],costrows)+'</section><section><h2>Evidence and limitations</h2><ul>'+''.join('<li>'+html.escape(x)+'</li>' for x in failures)+'</ul><p>Primary execution documentation: <a href="https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation">MetaQuotes real/generated ticks</a> · <a href="https://www.metatrader5.com/en/terminal/help/algotrading/testing">Delay simulation</a></p><p><a href="PROTOCOL.txt">Frozen validation protocol</a> · <a href="SUMMARY.json">Native results</a> · <a href="SUMMARY VERIFICATION.json">Independent checks</a> · <a href="PARITY.json">Parity</a> · <a href="DECISION.json">Decision</a> · <a href="../PBD Profile Raw 2026-10-02/Results.html">Original three-asset study</a></p><details><summary>Full protocol</summary><pre>'+html.escape((ROOT/'PROTOCOL.txt').read_text())+'</pre></details></section></body></html>'
 page=page.replace('through1October2026','through 1 October 2026').replace('·1%requested','· 1% requested')
 (ROOT/'Results.html').write_text(page,encoding='utf-8')
 md='# Gold PBD validation — NOT VALIDATED\n\nFrozen rules, no optimisation.\n\n| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+'\n'.join('| '+' | '.join(map(str,x))+' |' for x in results)+'\n\n## Independent annual starts\n\n| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+'\n'.join('| '+' | '.join(map(str,x))+' |' for x in annualrows)+'\n\n## Conclusion and limitations\n\n'+'\n'.join('- '+x for x in failures)+'\n'
 (ROOT/'REPORT.md').write_text(md,encoding='utf-8');print('Report ready: NOT VALIDATED; 10 native tests, annual/cost/MC diagnostics and 3 graphs.')
if __name__=='__main__':main()
