import base64,gzip,html,io
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from native import ROOT,OUT,load,save,ledger

NAMES={1:'Value-area reclaim',2:'Weak-breakout fade',3:'Strong breakout',4:'Combined'}
ASSETS={'USTEC':'US100','XAUUSD':'Gold','BTCUSD':'Bitcoin'}
COLOURS={1:'#75f5cb',2:'#c9a8ff',3:'#ffbd74',4:'#72d8ff'}
def table(headers,rows):
 return '<div class="table"><table><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</table></div>'
def fmt(x,dec=2):return '—' if x is None else f'{x:.{dec}f}'
def keys(r):
 a,m,w=r['stage'].split('-');return a,int(m),w
def attributed(r):
 d=ledger(r).sort_values('open_epoch').reset_index(drop=True)
 s=pd.read_csv(io.BytesIO(gzip.decompress((OUT/r['stage']/'0-signals.csv.gz').read_bytes())))
 s=s[s.retcode==10009].sort_values('epoch').reset_index(drop=True)
 assert len(s)==len(d) and (d.open_epoch.to_numpy()>=s.epoch.to_numpy()).all()
 assert (d.open_epoch.to_numpy()-s.epoch.to_numpy()<60).all()
 assert list(d.module)==[ {1:'RECLAIM',2:'WEAK_FADE',3:'BREAKOUT'}[x] for x in s.module]
 d['profile_shape']=s['shape'];return d
def curve(r,ax,ddax):
 d=ledger(r).sort_values(['close_epoch','position_id']);module=int(r['parameters']['module'])
 dates=[pd.Timestamp(r['start'].replace('.','-'))]+list(pd.to_datetime(d.close_epoch,unit='s'))+[pd.Timestamp(r['end'].replace('.','-'))]
 b=np.r_[10000,10000+d.net_profit.cumsum().to_numpy()];b=np.r_[b,b[-1]];peak=np.maximum.accumulate(b)
 ax.step(dates,b,where='post',label=NAMES[module],color=COLOURS[module],lw=1.3,alpha=.9)
 ddax.step(dates,-100*(peak-b)/peak,where='post',color=COLOURS[module],lw=1)

def main():
 rows=load(ROOT/'SUMMARY.json');verified=load(ROOT/'SUMMARY VERIFICATION.json');audits=load(ROOT/'AUDIT SUMMARY.json');by={r['stage']:r for r in rows}
 plt.rcParams.update({'figure.facecolor':'#091713','axes.facecolor':'#0e211c','axes.edgecolor':'#315047','text.color':'#eef7f2','axes.labelcolor':'#bdcfca','xtick.color':'#bdcfca','ytick.color':'#bdcfca','grid.color':'#315047','font.size':10})
 pictures=[]
 for window in ['1y','6m']:
  fig,axes=plt.subplots(2,3,figsize=(17,8),sharex='col',gridspec_kw={'height_ratios':[2,1]})
  for c,asset in enumerate(ASSETS):
   for module in NAMES:curve(by[f'{asset}-{module}-{window}'],axes[0,c],axes[1,c])
   axes[0,c].set_title(ASSETS[asset]+' — independent versions');axes[0,c].set_ylabel('Closed balance USD');axes[1,c].set_ylabel('Closed balance DD %');axes[0,c].legend(fontsize=8)
   axes[0,c].axhline(10000,color='#8ca59c',lw=.7,ls='--')
   for ax in axes[:,c]:ax.grid(alpha=.25)
  fig.suptitle('PBD tick-volume profile proxy | '+('last year, mixed real/generated execution ticks' if window=='1y' else 'latest 6 months; see native tick evidence')+'\n$10k each | 1% requested balance risk | NOT a shared portfolio | through 1 Oct 2026')
  fig.autofmt_xdate();fig.tight_layout();name='pbd-'+window+'-curves.png';fig.savefig(ROOT/name,dpi=140);plt.close(fig);pictures.append((name,'Closing-balance comparison — '+window))
 fig,axes=plt.subplots(2,3,figsize=(17,8),sharex='col',gridspec_kw={'height_ratios':[2,1]})
 for c,asset in enumerate(ASSETS):
  r=by[f'{asset}-4-1y'];t=pd.read_csv(io.BytesIO(gzip.decompress((OUT/r['stage']/'0-trace.csv.gz').read_bytes())));t['day']=pd.to_datetime(t.epoch,unit='s').dt.normalize()
  g=t.groupby('day').agg(low=('equity','min'),high=('equity','max'),balance=('balance','last'));peak=np.maximum.accumulate(np.r_[10000,t.equity.to_numpy()])[1:];t['dd']=100*(peak-t.equity)/peak;dd=t.groupby('day').dd.max()
  axes[0,c].fill_between(g.index,g.low,g.high,color='#72d8ff',alpha=.35);axes[0,c].plot(g.index,g.balance,color='#72d8ff',lw=1);axes[0,c].set_title(ASSETS[asset]+' combined modules');axes[0,c].set_ylabel('Equity USD')
  axes[1,c].fill_between(dd.index,-dd,0,color='#ff927b',alpha=.6);axes[1,c].set_ylabel('Sampled equity DD %')
  for ax in axes[:,c]:ax.grid(alpha=.25)
 fig.suptitle('Combined within each asset, NOT combined across accounts\nDaily min/max from once/minute floating-equity samples; exact native equity DD in table');fig.autofmt_xdate();fig.tight_layout();name='pbd-floating.png';fig.savefig(ROOT/name,dpi=140);plt.close(fig);pictures.append((name,'Sampled floating equity — combined modules'))
 headers=['Asset','Version','Return','Net PF','Win rate','Equity DD','Trades','Closed Sharpe','Max W/L run','Tick quality']
 result_tables={}
 for window in ['1y','6m']:
  result_tables[window]=[]
  for asset in ASSETS:
   for module in NAMES:
    r=by[f'{asset}-{module}-{window}'];s=r['stats']
    result_tables[window].append([ASSETS[asset],NAMES[module],f"{s['return_pct']:+.2f}%",'No losses' if s.get('pf_no_losses') else fmt(s['pf'],3),fmt(s['win_pct'],1)+'%',fmt(s['equity_dd_pct'])+'%',s['trades'],fmt(s['sharpe']),f"{s['max_win_streak']}/{s['max_loss_streak']}",r['native_metrics']['history_quality']])
 vby={x['stage']:x for x in verified};profile_rows=[];shape_rows=[]
 for asset in ASSETS:
  v=vby[f'{asset}-4-1y'];p=v['profile_counts'];profile_rows.append([ASSETS[asset],v['profile_days'],p['P'],p['b'],p['D'],p['other'],v['real_volume_nonzero_bars'],v['failed_entries'],v['carryovers'],v['boundary_closes']])
  d=attributed(by[f'{asset}-4-1y'])
  for label,shapes in [('P/b clip core',[1,-1]),('D extension',[0])]:
   x=d[d.profile_shape.isin(shapes)];gp=float(x.net_profit[x.net_profit>0].sum());gl=float(-x.net_profit[x.net_profit<0].sum())
   shape_rows.append([ASSETS[asset],label,len(x),f"${x.net_profit.sum():+,.2f}",fmt(gp/gl if gl else None,3),fmt(float((x.net_profit>0).mean()*100) if len(x) else None,1)+'%'])
 auditrows=[]
 for stage,a in audits.items():
  asset,module,_=stage.split('-');b=a['bootstrap'];stress=a['illustrative_stress'];auditrows.append([ASSETS[asset],NAMES[int(module)],a['verdict'],fmt(a['metrics']['deflated_sharpe_pct'],1)+'%',fmt(b.get('profit_factor_p05'),3),fmt(b.get('return_p05_pct'))+'%',fmt(stress['pf'],3)])
 risk=max(v['max_filled_risk_to_budget'] for v in verified if v['max_filled_risk_to_budget'] is not None)
 caveats=[
 'This is our frozen operationalisation of an incomplete clip, not a verified champion model. The D balance/reclaim rules are an explicit extension; the clip did not define them. It does not establish that P/b shapes imply aggressive buyers/sellers.',
 'All three Exness CFDs use broker quote tick-volume counts. Historical M1 real_volume is zero in every exported profile input. The profile spreads each M1 count uniformly over its high-low interval, not actual exchange volume-at-price. A real-tick execution-quality label does not fix this signal-data limitation.',
 'Profile freezes 09:30–10:30 New York, 64 bins and 70% value area. P/b require POC/centroid skew and directional net movement; D requires a centred distribution. Other days are excluded. Identical NY window for all assets; Bitcoin also trades weekends. This does NOT promise a setup every day.',
 'Reclaim targets the opposite value-area edge; weak P/b breakout fade targets POC; high-activity breakout targets 2R. M5 signals, causal next-tick fills, prior ATR14/prior20 activity, stop buffer .1 ATR, entry before 15:30 and flat at 16:00/pre-close. No optimisation, trailing or break-even.',
 'Each asset/version has an independent $10,000 balance with 1% requested balance risk, floor lot step and no minimum-lot override. Combined means modules share a single position slot on ONE asset; the three asset accounts are NOT a shared portfolio. Do not sum their percentages into a portfolio backtest.',
 'The last-year window is 2 Oct 2025–1 Oct 2026; latest6m is a fresh independent-start account over 2 Apr–1 Oct 2026, not a clipped compounded ledger. Windows overlap and are not untouched holdouts. Native tick coverage/quality and cost details are preserved in raw evidence.',
 'Exact native equity DD includes open positions. Closed-balance charts omit floating losses; the separate floating chart samples once/minute and is not a complete tick path. Closed Sharpe is based on daily realized balance changes with calendar-day annualisation; it is not an intraday equity Sharpe.',
 f'Independent Python reconstruction checked {sum(v["positions"] for v in verified):,} positions across overlapping runs and {sum(v["profile_m1_bars"] for v in verified):,} exported M1 inputs, plus every profile classification and signal. It shares the broker history source, not a second data vendor. Max filled stop-risk / requested budget {risk:.3f}×; fills, fees and gaps can exceed nominal risk.',
 '10,000 block5 bootstrap paths and DSR12 are historical diagnostics, not forward probabilities or FTMO pass/payout forecasts. Twelve current candidates and prior profile/strategy idea selection create bias. Measured extra-cost stress, random controls, pristine holdout and prospective demo are absent; 0.05R extra-cost sensitivity is illustrative only.',
 'Sparse weak-fade trades, no-loss samples and high winning streaks are not reliable evidence of an edge. No live deployment, active-account change, website/BAT update, paid data or Git push.'
 ]
 candidates=[]
 for asset in ASSETS:
  for module in NAMES:
   y=by[f'{asset}-{module}-1y']['stats'];m=by[f'{asset}-{module}-6m']['stats']
   if all(s['trades']>=30 and s['net']>0 and s['pf'] is not None and s['pf']>=1.2 for s in [y,m]):candidates.append(dict(asset=asset,module=NAMES[module],status='RAW WATCHLIST ONLY'))
 decision=dict(status='RAW WATCHLIST ONLY' if candidates else 'NO VERSION CLEARS BOTH RAW PF1.20 / POSITIVE / N30 SCREENS',raw_watchlist=candidates,live_eligible=False,optimisation_started=False,active_eas_changed=False,exchange_volume=False)
 save(ROOT/'DECISION.json',decision)
 css='body{background:#091713;color:#eef7f2;font:16px/1.55 system-ui;max-width:1400px;margin:auto;padding:36px}h1{font-size:42px}h2,a{color:#72f6cb}p,li{color:#bfd2cb}section{background:#0e211c;border:1px solid #315047;border-radius:18px;padding:24px;margin:24px 0}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:10px;text-align:right;border-bottom:1px solid #315047}th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left}.table{overflow:auto}img{width:100%}.warning{border-color:#987645}pre{white-space:pre-wrap;color:#bfd2cb}'
 page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calyx | PBD profile research</title><style>'+css+'</style><body><h1>PBD — three markets, four raw versions</h1><p>Exness CFD tick-volume proxy · $10,000 each · 1% requested risk · through 1 October 2026</p><section class="warning"><h2>'+html.escape(decision['status'])+'</h2><p>Historical simulation, not a forecast. Broker tick activity is not exchange money or aggressor delta. No live changes.</p><pre>'+html.escape(str(candidates))+'</pre></section>'
 for window,title in [('1y','Last year — mixed tick execution coverage'),('6m','Latest six months — fresh $10k start')]:page+='<section><h2>'+title+'</h2>'+table(headers,result_tables[window])+'</section>'
 for name,title in pictures:page+='<section><h2>'+title+'</h2><img src="data:image/png;base64,'+base64.b64encode((ROOT/name).read_bytes()).decode()+'" alt="'+html.escape(title)+'"></section>'
 page+='<section><h2>What actually occurred — combined, last year</h2>'+table(['Asset','Profile days','P','b','D','Other','Real-volume bars','Failed entries','Carryovers','End-test closes'],profile_rows)+'</section><section><h2>Which profile rules contributed?</h2><p>Attribution within the combined run, NOT independent P/b-only or D-only backtests. Trade sizes depend on the complete combined balance path.</p>'+table(['Asset','Profile group','Trades','Net contribution','Net PF','Win rate'],shape_rows)+'</section><section><h2>Raw statistical diagnostics</h2>'+table(['Asset','Version','Verdict','DSR','Bootstrap PF p05','Return p05','Illustrative +0.05R cost PF'],auditrows)+'</section><section><h2>Rules, evidence and limitations</h2><ul>'+''.join('<li>'+html.escape(x)+'</li>' for x in caveats)+'</ul><p>Volume context: <a href="https://www.tradingview.com/support/solutions/43000502040-volume-profile-indicators-basic-concepts/">TradingView documentation</a></p><p><a href="PROTOCOL.txt">Frozen detailed rules</a> · <a href="SUMMARY.json">Native results</a> · <a href="SUMMARY VERIFICATION.json">Independent verification</a></p><details><summary>Full frozen protocol</summary><pre>'+html.escape((ROOT/'PROTOCOL.txt').read_text())+'</pre></details></section></body></html>'
 (ROOT/'Results.html').write_text(page,encoding='utf-8')
 md='# PBD Exness CFD profile proxy — raw results\n\n'+decision['status']+'\n'
 for window in ['1y','6m']:md+='\n## '+window+'\n\n| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+'\n'.join('| '+' | '.join(map(str,x))+' |' for x in result_tables[window])+'\n'
 md+='\n## Profile attribution within combined runs (not standalone)\n\n| Asset | Profile group | Trades | Net contribution | PF | Win rate |\n|---|---|---|---|---|---|\n'+'\n'.join('| '+' | '.join(map(str,x))+' |' for x in shape_rows)+'\n'
 md+='\n## Limitations\n\n'+'\n'.join('- '+x for x in caveats)+'\n';(ROOT/'REPORT.md').write_text(md,encoding='utf-8');print(md[:8000]);print(decision)
if __name__=='__main__':main()
