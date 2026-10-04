from pathlib import Path
import base64,html,json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sma200 import ROOT,save
def table(headers,rows):return '<div class="table"><table><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</table></div>'
def main():
 rows=json.loads((ROOT/'ETF RESULTS.json').read_text());lock=json.loads((ROOT/'ETF DATA LOCK.json').read_text());bootstrap=json.loads((ROOT/'ETF BOOTSTRAP.json').read_text())
 plt.rcParams.update({'figure.facecolor':'#091713','axes.facecolor':'#0e211c','axes.edgecolor':'#315047','text.color':'#eef7f2','axes.labelcolor':'#bdcfca','xtick.color':'#bdcfca','ytick.color':'#bdcfca','grid.color':'#315047','font.size':10})
 fig,axes=plt.subplots(2,2,figsize=(14,8),sharex='col',gridspec_kw={'height_ratios':[2,1]})
 for col,symbol in enumerate(['QQQ','TQQQ']):
  for suffix,color in [('baseline','#72f6cb'),('cost-5bp','#ffbe7b')]:
   d=pd.read_csv(ROOT/'etf'/f'{symbol}-16y-{suffix}/equity.csv',parse_dates=['date']);axes[0,col].plot(d.date,d.equity,color=color,label='Next open'+(' +5bp/side' if suffix!='baseline' else ''),lw=1.2)
   axes[1,col].plot(d.date,-d.dd_pct,color=color,lw=.9)
  axes[0,col].set_yscale('log');axes[0,col].set_ylabel('Marked equity USD (log scale)');axes[0,col].set_title(symbol+' — own 200-day SMA');axes[0,col].legend();axes[1,col].set_ylabel('Daily close equity DD %')
  for a in axes[:,col]:a.grid(alpha=.25)
 fig.suptitle('Same daily SMA rule, independently cash-funded | $10,000 start\n2010-10-02 through2026-10-01 | unclosed final holding marked, not forced closed');fig.autofmt_xdate();fig.tight_layout();fig.savefig(ROOT/'etf-curves.png',dpi=140);plt.close(fig)
 stats=[]
 for r in rows:
  if r['key'].endswith('baseline'):stats.append([r['symbol']+' '+r['window'],f"${r['final_marked_equity']:,.2f}",f"{r['return_pct']:+,.2f}%",f"{r['cagr_pct']:.2f}%",f"{r['max_daily_close_equity_dd_pct']:.2f}%",r['closed_trades'],f"{r['win_pct']:.1f}%",f"{r['net_pf_closed_trades']:.3f}" if r['net_pf_closed_trades'] is not None else 'n/a',f"{r['sharpe_daily_252']:.2f}",f"{r['max_win_streak']}/{r['max_loss_streak']}"])
 sensitivities=[[r['key'],f"{r['return_pct']:+,.2f}%",f"{r['max_daily_close_equity_dd_pct']:.2f}%",r['closed_trades']] for r in rows if r['window']=='16y']
 bench=[[r['symbol'],f"{r['buy_hold']['return_pct']:+,.2f}%",f"{r['buy_hold']['max_daily_close_dd_pct']:.2f}%",f"{r['exposure_pct']:.1f}%"] for r in rows if r['key'].endswith('16y-baseline')]
 headers=['Fund / window','Final marked equity','Total return','CAGR','Close equity DD','Closed trades','Win rate','Closed PF','Sharpe','Max win/loss run']
 warnings=[
 'The quoted +210% QQQ /−87% TQQQ outcome was NOT reproduced under the stated rule and our explicit execution/data assumptions. Exact video dates, code, adjustment policy and fees were not supplied; this is not an accusation about its unseen implementation.',
 'TQQQ started in February2010 and its first valid 200-session average here is24November2010. We did not fabricate pre-inception prices or warmup. QQQ can trade from4October2010; TQQQ remains in cash until its first valid signal. The common-eligible comparison starts26November2010.',
 'Raw vendor open and close are split-adjusted. Adjusted close includes dividends; adj_close/close applied once to open creates a synthetic reinvested total-return series. No separate dividend/split application. Verify actual cash dividends, taxes, broker share rounding and corporate actions before deployment.',
 'One full cash-funded fund position, no extra margin leverage, shorts, stop-loss or profit target. TQQQ already targets3x DAILY Nasdaq100 performance. It is not3x the multi-year QQQ return. Zero cash interest; ETF expenses are embedded in market prices, not separately charged twice.',
 'Signal at completed daily close; execution next session open. Same-close sensitivity is optimistic timing, not an implementable promise.5bp each side is illustrative execution friction, not a measured broker calibration.',
 'Both final positions remain open. Total return/equity DD include their marked unrealized P&L; PF, win rate and streaks include CLOSED trades only. DD is daily close-to-close marked equity, not intraday drawdown.',
 'Whole-share rounding, liquidity limits, spread, tax, market impact and slippage are not fully simulated. Long-history percentage returns rely on full compounding and a favourable historical Nasdaq sample; do not use as payout/income forecasts.',
 '20,000 paired circular daily-return block samples of length20 diagnose historical return uncertainty, not a new strategy run or forecast. No pristine untouched holdout/parameter search; latest1/3/5-year windows overlap.',
 'This is low-frequency ETF investing, not an FTMO-compatible EA portfolio: last5years have only10 QQQ/14 TQQQ CLOSED trades. These win rates do not satisfy the user preference for high-win-rate scalping.',
 'IVB paid futures download was not started. The user subsequently requested an Exness US100 quote-count proxy, researched separately. Literal-source .els file is uncompiled and contains documented timing/EOD hazards. No active-EA/account/website/BAT changes or Git push.'
 ]
 caption='QQQ/TQQQ SMA200 — headline video result not reproduced'
 css='body{background:#091713;color:#eef7f2;font:16px/1.55 system-ui;max-width:1350px;margin:auto;padding:36px}h1{font-size:40px}h2,a{color:#72f6cb}p,li{color:#bfd2cb}section{background:#0e211c;border:1px solid #315047;border-radius:18px;padding:24px;margin:24px 0}table{border-collapse:collapse;width:100%;font-size:12px}th,td{padding:10px;text-align:right;border-bottom:1px solid #315047}th:first-child,td:first-child{text-align:left}.table{overflow:auto}img{width:100%}.warning{border-color:#987645}'
 img='data:image/png;base64,'+base64.b64encode((ROOT/'etf-curves.png').read_bytes()).decode()
 page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calyx | SMA200 ETF replication</title><style>'+css+'</style><body><h1>'+caption+'</h1><p>Same200-trading-day moving-average rule on each fund. Daily signals, next-open fills, independently compounded $10,000 cash accounts.</p><section class="warning"><p>TQQQ did not lose87% in this reproduction. Its baseline grew to about$1.10million, but suffered48.14% daily-close equity drawdown. QQQ grew to about$79,203 with25.75% drawdown. Historical results—not forecasts.</p></section><section><h2>Baseline windows</h2>'+table(headers,stats)+'</section><section><h2>Equity and drawdown</h2><img src="'+img+'" alt="Separate QQQ and TQQQ marked equity and drawdown"></section><section><h2>Execution sensitivities</h2>'+table(['Version','Total return','Close DD','Closed trades'],sensitivities)+'</section><section><h2>Buy-and-hold benchmark</h2>'+table(['Fund','Buy/hold total return','Buy/hold close DD','SMA exposure'],bench)+'</section><section><h2>Limits and verification</h2><p>Seven unit tests passed, including independent equity recurrence for every baseline day of both funds. Data hashes and200-session warmup locked. No parameter optimisation.</p><ul>'+''.join('<li>'+html.escape(v)+'</li>' for v in warnings)+'</ul><p><a href="ETF RESULTS.json">All results</a> · <a href="ETF BOOTSTRAP.json">Bootstrap diagnostics</a> · <a href="ETF DATA LOCK.json">Data audit</a> · <a href="PROTOCOL.txt">Protocol</a> · <a href="IVB Source Parity.els">IVB source-parity code (uncompiled)</a></p></section></body></html>'
 # Mechanical typography normalisation for prose-only labels.
 for a,b in [('Same200','Same 200'),('lose87%','lose 87%'),('about$','about $'),('suffered48','suffered 48'),('with25','with 25')]:page=page.replace(a,b)
 (ROOT/'Results.html').write_text(page,encoding='utf-8')
 md=['# '+caption,'','Historical simulation, not a forecast.','', '| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,r))+' |' for r in stats]+['','## Caveats','']+['- '+v for v in warnings]
 (ROOT/'REPORT.md').write_text('\n'.join(md)+'\n',encoding='utf-8');save(ROOT/'DECISION.json',{'video_headline_reproduced':False,'live_eligible':False,'low_closed_trade_count_recent':True,'no_paid_NQ_download':True,'IVB_Exness_proxy_separate':True,'no_deployment':True})
 print(json.dumps(stats,indent=2))
if __name__=='__main__':main()
