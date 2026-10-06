"""Self-contained offline raw-results report. No public catalogue updates."""
import base64,html,io,gzip,math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import native
R=native.ROOT
LABELS={'USTEC':'US100','US30':'US30','UK100':'UK100','XAUUSD':'Gold','BTCUSD':'BTC'}
def table(headers,rows):
 return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def number(x,d=2):return '—' if x is None else f'{x:.{d}f}'
def wilson(w,n):
 if n==0:return '—'
 z=1.96;p=w/n;den=1+z*z/n;mid=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
 return f'{100*(mid-half):.1f}–{100*(mid+half):.1f}%'
def main():
 rows=native.load(R/'SUMMARY.json');v=native.load(R/'VERIFICATION.json');by={r['stage']:r for r in rows};tables=[];details=[];direction=[]
 for row in rows:
  s=row['stats'];d=native.ledger(row);wins=int((d.net_profit>0).sum())
  tables.append([LABELS[row['stage'].rsplit('-',1)[0]],row['stage'].rsplit('-',1)[1],f"{s['return_pct']:+.2f}%",number(s['pf'],3),number(s['win_pct'],1)+'%',s['trades'],number(s['equity_dd_pct'])+'%',number(s['balance_dd_pct'])+'%',number(s['sharpe']),f"{s['max_win_streak']} / {s['max_loss_streak']}",number(s['mean_R'],3),wilson(wins,len(d))])
  details.append([row['stage'],row['native_metrics']['history_quality'],row['net']['signals'],row['net']['skips'],row['net']['entry_fail'],row['net']['close_fail'],row['net']['boundary'],row['net']['carryovers'],f"${s['commission']:.2f}",f"${s['swap']:.2f}"])
  for side,label in [(1,'Long'),(-1,'Short')]:
   x=d[d.side==side];pos=x.net_profit[x.net_profit>0].sum();neg=-x.net_profit[x.net_profit<0].sum()
   direction.append([row['stage'],label,len(x),f"${x.net_profit.sum():+.2f}",number(float(pos/neg) if neg>0 else None,3),number(float((x.net_profit>0).mean()*100) if len(x) else None,1)+'%'])
 plt.rcParams.update({'figure.facecolor':'#071511','axes.facecolor':'#0d2019','axes.edgecolor':'#365347','text.color':'#effbf5','axes.labelcolor':'#bfdbcd','xtick.color':'#bfdbcd','ytick.color':'#bfdbcd','grid.color':'#365347'})
 plots=[]
 for symbol,label in LABELS.items():
  fig,axes=plt.subplots(2,2,figsize=(13,7),sharex='col',gridspec_kw={'height_ratios':[2,1]})
  for col,window in enumerate(['1y','3m']):
   row=by[symbol+'-'+window];d=native.ledger(row).sort_values(['close_epoch','position_id']);date=[pd.Timestamp(row['start'].replace('.','-'))]+list(pd.to_datetime(d.close_epoch,unit='s'));bal=np.r_[10000,10000+d.net_profit.cumsum().to_numpy()];peak=np.maximum.accumulate(bal);dd=100*(peak-bal)/peak
   axes[0,col].plot(date,bal,color='#77f5c8',lw=1.4);axes[0,col].axhline(10000,color='#aecbbd',lw=.6,ls='--');axes[0,col].set_title(label+' — '+window);axes[0,col].set_ylabel('Closed position balance USD')
   axes[1,col].fill_between(date,-dd,0,color='#ff8c79',alpha=.65);axes[1,col].set_ylabel('Closed balance DD %')
   for ax in axes[:,col]:ax.grid(alpha=.25)
  fig.suptitle('Raw EMA + anchored VWAP pullback | independent $10,000 account | 0.5% requested risk\nPartials attributed at final position close. Table shows separate native floating-equity drawdown.');fig.autofmt_xdate();fig.tight_layout();name=symbol+'-curves.png';fig.savefig(R/name,dpi=125);plt.close(fig);plots.append((label,name))
 css='body{background:#071511;color:#effbf5;font:16px/1.55 system-ui;max-width:1400px;margin:auto;padding:32px}h1{font-size:clamp(32px,4vw,54px);line-height:1.15}h2,a{color:#77f5c8}p,li{color:#bfdbcd}section{background:#0d2019;border:1px solid #365347;border-radius:18px;padding:24px;margin:24px 0}.warning{border-color:#ad7e3a}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:11px;border-bottom:1px solid #365347;text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}img{width:100%;height:auto}.tag{color:#77f5c8;letter-spacing:2px;font-size:12px}'
 limits=[
 'Mechanical adaptation of a discretionary STOCK strategy to broker CFDs and BTC. It does not reproduce stock/theme selection, first-pullback judgement, minute-precise anchors or subjective exits. No parameters were optimized.',
 'Each asset/window starts independently at$10,000 with no inherited positions, not a shared portfolio. The3month run is a fresh start, not just a slice of the1year ledger.0.5%balance risk is a requested initial-stop budget; fees, adverse fills and gaps can exceed it. Minimum-lot rounding isDOWN; unaffordable trades are skipped.',
 'Isolated Exness-MT5Trial16 research terminal; active account isExness-MT5Trial15 and was not changed. Native Model4 requested with150ms delay and recorded spread/commission/swap. History-quality percentages include400days of no-trading warmup. Inspect per-run real-tick start dates in SUMMARY.json; pre-2026 ticks may be generated. No measured extra-cost stress yet.',
 'AVWAP is a broker tick-volume, completed-H1 typical-price proxy anchored at a confirmed D1 pivot, not exchange trade volume. Daily EMA/ATR features and anchors use only information available before entry.',
 'Same NY09:30–11:30 weekday entry window on all assets; UK100 is not tested at the London open. This is intentional baseline comparability, not an asset-specific session optimization.',
 'Daily9EMA runner exit plus20%-original-volume trims at3R/5R. Shorts use the same management, unlike the discretionary faster covering in the interview. Small volume can prevent valid partial exits.',
 'A position can have multiple exit deals; win rate, PF and trade counts here use NET completed positions, not winning exit-deal counts. Closed charts attribute all costs/partials to final close; native equity DD includes the actual floating path.',
 'One-year and three-month windows overlap. The recent window is not independent validation. Raw profit alone is not a promotion/pass/payout claim. No long-history pipeline or Monte Carlo requested or run here.',
 'End-of-test liquidations and carryovers are counted in the coverage table, not removed. A long runner near the boundary may affect net outcomes.',
 'UK30 is absent from the connected broker symbol list; no fake result or UK100 substitution. All live charts, BATs, website catalogue, FTMO presets and remote Git remain unchanged.'
 ]
 best=max((r for r in rows if r['stage'].endswith('-1y')),key=lambda r:r['stats']['net'])
 conclusion=f"Highest raw one-year net return: {LABELS[best['stage'].rsplit('-',1)[0]]} ({best['stats']['return_pct']:+.2f}%). This ranks this frozen adaptation only, not the original trader or a verified live edge."
 headers=['Asset','Window','Net return','Net PF','Win rate','Positions','Equity DD','Closed DD','Closed Sharpe','Max win/loss run','Mean net R','Win-rate95% CI']
 doc='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calyx | Raw EMA AVWAP pullback</title><style>'+css+'</style></head><body><p class="tag">CALYX RESEARCH · RAW · UNOPTIMISED</p><h1>EMA + anchored VWAP pullback</h1><p>One year: 4 October 2025–3 October 2026. Three months: 4 July 2026–3 October 2026. End-exclusive 4 October 2026.</p><p>Broker: Exness-MT5Trial16 isolated research terminal. Five independent $10,000 accounts.</p><section class="warning"><h2>Research interpretation, not an exact replication</h2><p>'+html.escape(conclusion)+'</p><p>UK30 unavailable. Not installed into any trading account.</p></section><section><h2>Frozen rules</h2><p>Completed daily EMA9/21 trend, confirmed swing-point H1 tick-volume AVWAP, EMA confluence, intraday rejection and prior-bar breakout. Risk 0.5%, day-extreme stop with 2.5% price-distance cap, 3R/5R partials, daily 9EMA runner exit.</p><a href="PROTOCOL.txt">Full assumptions and protocol</a></section><section><h2>Raw results</h2>'+table(headers,tables)+'</section>'
 for label,name in plots:doc+='<section><h2>'+label+'</h2><img alt="'+label+' independent balance and drawdown" src="data:image/png;base64,'+base64.b64encode((R/name).read_bytes()).decode()+'"></section>'
 doc+='<section><h2>Long vs short</h2>'+table(['Window','Direction','Positions','Net USD','PF','Win rate'],direction)+'</section><section><h2>Native coverage and execution</h2>'+table(['Window','History quality','Triggered signals','Skips','Entry errors','Close errors','Boundary positions','Overnight positions','Commission','Swap'],details)+'</section><section><h2>Verification</h2><p>Independent reconstruction of confirmed anchors, H1 AVWAP, daily EMA/ATR, directional setups and entry timing. '+str(sum(z['positions_verified'] for z in v))+' position observations checked across overlapping tests.</p><a href="VERIFICATION.json">Verification details</a> · <a href="SUMMARY.json">Frozen native results and tick notes</a></section><section><h2>Limitations</h2><ul>'+''.join('<li>'+html.escape(x)+'</li>' for x in limits)+'</ul></section></body></html>'
 (R/'Results.html').write_text(doc,encoding='utf-8')
 (R/'REPORT.md').write_text('# Raw EMA + anchored VWAP pullback\n\n'+conclusion+'\n\n| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+'\n'.join('| '+' | '.join(map(str,x))+' |' for x in tables)+'\n\n'+'\n'.join('- '+x for x in limits)+'\n',encoding='utf-8')
 native.save(R/'REPORT DATA.json',dict(results=tables,coverage=details,direction=direction,limitations=limits,conclusion=conclusion))
 native.save(R/'DECISION.json',dict(stage='RAW_RESEARCH_ONLY',decision='REVISE_RAW_RULES_BEFORE_PROMOTION',most_promising_one_year='XAUUSD',recent_three_months_all_negative=all(x['stats']['net']<0 for x in rows if x['stage'].endswith('-3m')),uk30='UNAVAILABLE_NO_SUBSTITUTE',optimization=False,full_pipeline=False,live_eas_changed=False,website_catalog_changed=False,github_pushed=False,all_verification_passed=all(x['passed'] for x in v),protocol_sha=native.sha(R/'PROTOCOL.txt'),source_sha=native.sha(R/'EA/Main.mqh')))
 print(conclusion);print(tables)
if __name__=='__main__':main()
