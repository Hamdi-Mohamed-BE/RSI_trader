import base64,gzip,html,io
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from native import ROOT,OUT,load,save,ledger
def table(headers,rows):return '<div class="table"><table><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</table></div>'
def main():
 rows=load(ROOT/'SUMMARY.json');verified=load(ROOT/'VERIFICATION.json');audits=load(ROOT/'AUDIT SUMMARY.json');by={r['stage']:r for r in rows}
 plt.rcParams.update({'figure.facecolor':'#091713','axes.facecolor':'#0e211c','axes.edgecolor':'#315047','text.color':'#eef7f2','axes.labelcolor':'#bdcfca','xtick.color':'#bdcfca','ytick.color':'#bdcfca','grid.color':'#315047','font.size':10})
 fig,axes=plt.subplots(2,2,figsize=(14,8),sharex='col',gridspec_kw={'height_ratios':[2,1]})
 for col,w in enumerate(['real-2026','5y']):
  r=by[w];d=ledger(r).sort_values(['close_epoch','position_id']);dates=[pd.Timestamp(r['start'].replace('.','-'))]+list(pd.to_datetime(d.close_epoch,unit='s'));b=np.r_[10000,10000+d.net_profit.cumsum().to_numpy()];peak=np.maximum.accumulate(b)
  dates.append(pd.Timestamp('2026-10-02'));b=np.r_[b,b[-1]];peak=np.maximum.accumulate(b)
  axes[0,col].step(dates,b,where='post',color='#72f6cb',lw=1.2);axes[0,col].axhline(10000,color='#8ca59c',lw=.7,ls='--');axes[0,col].set_ylabel('Closed balance USD');axes[0,col].set_title('2026 real-tick evidence' if w=='real-2026' else '5y synthetic-tick diagnostic — NOT delta validation')
  axes[1,col].fill_between(dates,-100*(peak-b)/peak,0,step='post',color='#ff927b',alpha=.6);axes[1,col].set_ylabel('Closed balance DD %')
  for a in axes[:,col]:a.grid(alpha=.25)
 fig.suptitle('IVB-style US100 quote-count proxy | Exness USTEC | $10k | 1% requested risk\nNOT Fabio NQ futures replication. Native spreads/costs and 150ms delay.');fig.autofmt_xdate();fig.tight_layout();fig.savefig(ROOT/'ivb-curves.png',dpi=140);plt.close(fig)
 r=by['real-2026'];t=pd.read_csv(io.BytesIO(gzip.decompress((OUT/r['stage']/'0-trace.csv.gz').read_bytes())));t['day']=pd.to_datetime(t.epoch,unit='s').dt.normalize();g=t.groupby('day').agg(low=('equity','min'),high=('equity','max'),balance=('balance','last'));pk=np.maximum.accumulate(np.r_[10000,t.equity.to_numpy()])[1:];t['dd']=100*(pk-t.equity)/pk;dd=t.groupby('day').dd.max()
 fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True,gridspec_kw={'height_ratios':[2,1]});axes[0].fill_between(g.index,g.low,g.high,color='#72f6cb',alpha=.3);axes[0].plot(g.index,g.balance,color='#72f6cb',lw=1);axes[0].set_ylabel('USD');axes[0].set_title('2026 sampled floating equity — daily min/max from minute samples\nExact native tick-path drawdown shown separately in table');axes[1].fill_between(dd.index,-dd,0,color='#ff927b',alpha=.6);axes[1].set_ylabel('Sampled equity DD %')
 for a in axes:a.grid(alpha=.25)
 fig.autofmt_xdate();fig.tight_layout();fig.savefig(ROOT/'ivb-floating.png',dpi=140);plt.close(fig)
 headers=['Window','Return','Net PF','Win rate','Native equity DD','Trades','Closed Sharpe','Max win/loss run','Tick evidence']
 results=[]
 for r in rows:
  s=r['stats'];results.append([r['stage'],f"{s['return_pct']:+.2f}%",f"{s['pf']:.3f}",f"{s['win_pct']:.1f}%",f"{s['equity_dd_pct']:.2f}%",s['trades'],s['sharpe'],f"{s['max_win_streak']}/{s['max_loss_streak']}",r['native_metrics']['history_quality']])
 auditrows=[[k,a['verdict'],f"{a['metrics']['deflated_sharpe_pct']:.1f}%",f"{a['bootstrap']['probability_profit_pct']:.1f}%",f"{a['bootstrap']['profit_factor_p05']:.3f}",f"{a['bootstrap']['return_p05_pct']:+.2f}%"] for k,a in audits.items()]
 total=sum(v['positions'] for v in verified);ticks=sum(v['quote_ticks_recounted'] for v in verified);risk=max(v['max_filled_risk_to_budget'] for v in verified if v['max_filled_risk_to_budget'] is not None)
 caveats=[
 'User explicitly requested Exness US100 rather than paid NQ history. This is a bid-quote uptick-count minus downtick-count proxy. It is NOT aggressor-side contract volume, footprint delta, or independent proof of Fabio Valentini’s model.',
 'NY08:30–09:00 range, first later completed M5 close above high and quote-count delta>=200; long only. Cumulative delta filter OFF. One qualifying attempt/day. Next-tick entry, SL range low, fixed1:1 target from entry quote. No trailing, BE, optimisation or extra filters.',
 'Corrected the published code’s entry-at-EOD sequencing hazard by requiring entry strictly before14:00 NY and closing at14:00/session pre-close. Source this-bar-close fill replaced by causal next-tick market order. $10k/1% balance sizing is not a fixed1NQ-contract reproduction.',
 'Older history uses GENERATED TICKS. Their price paths manufacture up/down counts, so1/3/5year results are diagnostics only, not validation of this filter. Primary evidence is2026 real ticks and latest6months, each100% real ticks. These are small, overlapping samples, not independent holdouts.',
 'Native Model4,150ms delay, CFD spreads/commission/swap included. Broker-measured incremental-cost stress missing. The broker may emit same-bid/ask-only events: those contribute zero; seed is last completed M1 bid close before signal.',
 'Signal-bar quote counts independently recomputed from exported ticks; timestamps, range snapshots, stops/targets, risk-budget sizing and net-ledger sums verified. Opening-range snapshots and preceding-bid seed were exported by the EA, not independently recovered from a separate historical data source.',
 f'{total:,} closed positions across overlapping windows checked; {ticks:,} quote ticks recounted. Maximum filled stop-risk/budget ratio: {risk:.3f}×. The 1% setting is requested pre-cost risk, not an absolute loss guarantee; adverse fills/fees/gaps can exceed it.',
 'Native equity DD includes floating losses. Closed-balance plots exclude them; floating plot is sampled once/minute and is not the exact tick-path DD.10,000 block-bootstrap paths/block5 are diagnostics, not profit or FTMO pass/payout forecasts.',
 'No prospective forward test, calibration or live promotion. Prior IVB/FRVP source is a different model and remains unchanged. Active MT5 account, EAs, BATs, website and Git remote untouched; no paid data downloaded.'
 ]
 primary=by['real-2026']['stats'];decision={'status':'RAW REAL-TICK BASELINE REJECTED' if primary['net']<=0 or primary['pf']<=1 else 'RAW ONLY; INSUFFICIENT VALIDATION','live_eligible':False,'genuine_NQ_replication':False,'optimisation_started':False,'active_eas_changed':False,'paid_data_downloaded':False};save(ROOT/'DECISION.json',decision)
 css='body{background:#091713;color:#eef7f2;font:16px/1.55 system-ui;max-width:1350px;margin:auto;padding:36px}h1{font-size:40px}h2,a{color:#72f6cb}p,li{color:#bfd2cb}section{background:#0e211c;border:1px solid #315047;border-radius:18px;padding:24px;margin:24px 0}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:10px;text-align:right;border-bottom:1px solid #315047}th:first-child,td:first-child{text-align:left}.table{overflow:auto}img{width:100%}.warning{border-color:#987645}'
 page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calyx | IVB US100 quote-count proxy</title><style>'+css+'</style><body><h1>IVB-style US100 — raw quote-count proxy</h1><p>Exness USTEC · $10,000 · 1% requested risk · through1October2026</p><section class="warning"><h2>'+decision['status']+'</h2><p>Real-tick2026 return'+f" {primary['return_pct']:+.2f}%"+', PF'+f" {primary['pf']:.3f}"+'. Older generated-tick runs cannot validate a delta filter. This is NOT the original NQ model.</p></section><section><h2>Native results</h2>'+table(headers,results)+'</section>'+''.join('<section><h2>'+title+'</h2><img src="data:image/png;base64,'+base64.b64encode((ROOT/name).read_bytes()).decode()+'" alt="'+title+'"></section>' for title,name in [('Closed balance','ivb-curves.png'),('Sampled floating equity','ivb-floating.png')])+'<section><h2>Raw statistical diagnostics</h2>'+table(['Window','Verdict','DSR probability','Bootstrap profit probability','PF p05','Return p05'],auditrows)+'</section><section><h2>Rules, verification and limits</h2><ul>'+''.join('<li>'+html.escape(v)+'</li>' for v in caveats)+'</ul><p><a href="PROTOCOL.txt">Protocol</a> · <a href="SUMMARY.json">Native evidence</a> · <a href="VERIFICATION.json">Verification</a> · <a href="../IVB and SMA200 Research 2026-10-02/Results.html">QQQ/TQQQ SMA200 research</a></p></section></body></html>'
 page=page.replace('through1October2026','through 1 October 2026').replace('Real-tick2026','Real-tick 2026')
 (ROOT/'Results.html').write_text(page,encoding='utf-8');(ROOT/'REPORT.md').write_text('# IVB US100 quote-count proxy\n\n'+decision['status']+'\n\n| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+'\n'.join('| '+' | '.join(map(str,x))+' |' for x in results)+'\n\n'+'\n'.join('- '+x for x in caveats)+'\n',encoding='utf-8');print(results)
if __name__=='__main__':main()
