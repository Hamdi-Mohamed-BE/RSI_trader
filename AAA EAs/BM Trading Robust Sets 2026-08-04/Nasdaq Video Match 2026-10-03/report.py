from pathlib import Path
import base64,gzip,html,json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
ORDER=['CURRENT','EMA_ONLY','VIDEO_ATR','VIDEO_ATR_DI','SYMMETRIC_ATR','VIDEO_MA']
DESCRIPTIONS={
 'CURRENT':'Our selected DI14 + EMA12 entry, ATR6 trail from +1R; no candle-body requirement.',
 'EMA_ONLY':'Our ATR exits, no DI and no candle-body requirement.',
 'VIDEO_ATR':'Literal video entry: bullish long above EMA12; short below EMA12; DI off. Our ATR exit assumed.',
 'VIDEO_ATR_DI':'Literal video entry with DI14 retained; same ATR exit.',
 'SYMMETRIC_ATR':'Bullish long / bearish short with EMA12; DI off. Symmetric short rule is an assumption.',
 'VIDEO_MA':'Literal entry without DI; closed-bar EMA200 trail from +0.5R. Exit formula is an assumption.'}
COLORS=['#f0f6ee','#58c9eb','#72edbe','#b4dd55','#d6a4f2','#ffa96e']
WINDOW_LABELS={'available':'Available history • Aug 2019 – Oct 2026','5y':'Last five years','1y':'Last year','3m':'Last three months'}
plt.rcParams.update({'figure.facecolor':'#091813','axes.facecolor':'#091813','axes.edgecolor':'#395b49','axes.labelcolor':'#d2e8dc','xtick.color':'#a4bfb0','ytick.color':'#a4bfb0','text.color':'#e8f6ee','grid.color':'#355341','font.size':10})
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def ledger(row):return pd.DataFrame(json.loads(gzip.decompress((ROOT/'native'/row['manifest']['key']/'trades.json.gz').read_bytes())))
def fmt(v,n=2):return '—' if v is None or (isinstance(v,float) and not np.isfinite(v)) else f'{v:,.{n}f}'
def picture(p):return '<img alt="'+html.escape(p.stem)+'" src="data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode()+'">'
def sharpe_calendar(d,start,end):
 cal=pd.date_range(start.replace('.','-'),pd.Timestamp(end.replace('.','-'))-pd.Timedelta(days=1)).strftime('%Y-%m-%d')
 # Include all UTC dates, including any Sunday reopening exits. Nontrading dates
 # are zero; annualisation uses calendar days, not 252 on a seven-day calendar.
 daily=d.assign(date=d.close_time.str[:10]).groupby('date').net_profit.sum().reindex(cal,fill_value=0).to_numpy()
 assert abs(daily.sum()-d.net_profit.sum())<.12
 before=10000+np.r_[0,np.cumsum(daily)[:-1]];returns=daily/before
 return float(returns.mean()/returns.std(ddof=1)*np.sqrt(365.2425))
def main():
 rows=load(ROOT/'SUMMARY.json');audit=load(ROOT/'VERIFICATION.json');assert audit['complete'] and audit['comparison_runs']==24
 normalized=[];notes=[]
 for row in rows:
  m=row['manifest'];st=row['stats'];d=ledger(row);s=sharpe_calendar(d,m['start'],m['end'])
  check=next(c for c in audit['checks'] if c['key']==m['key'])
  clean_stats={k:v for k,v in st.items() if k!='daily_cash_sharpe'}
  v=d.net_profit.to_numpy();avgwin=float(v[v>0].mean());avgloss=float(v[v<0].mean())
  normalized.append(dict(window=m['window'],variant=m['variant'],**clean_stats,daily_return_sharpe=s,avg_net_win=avgwin,avg_net_loss=avgloss,avg_net_win_loss_ratio=avgwin/-avgloss,cost_share_of_gross_profit_pct=-(st['commission']+st['swap'])/st['gross']*100 if st['gross']>0 else None,stop_modify_rejections=row['known_stop_modify_rejections'],stop_modification_rejection_reasons=check['stop_modification_rejection_reasons'],delayed_entries=check['delayed_entries']))
 for window in WINDOW_LABELS:
  fig,(ax,bx)=plt.subplots(2,1,figsize=(13,8),gridspec_kw={'height_ratios':[3,1]},sharex=True)
  for variant,color in zip(ORDER,COLORS):
   r=next(x for x in rows if x['manifest']['window']==window and x['manifest']['variant']==variant);d=ledger(r);dates=pd.to_datetime([r['manifest']['start'].replace('.','-')+'T00:00:00']+d.close_time.tolist());equity=np.r_[10000,10000+d.net_profit.cumsum()];peak=np.maximum.accumulate(equity);dd=(peak-equity)/peak*100
   ax.plot(dates,equity,color=color,lw=1.4 if variant=='CURRENT' else 1.1,label=variant);bx.plot(dates,-dd,color=color,lw=.8,alpha=.9)
  ax.set_title(WINDOW_LABELS[window]+' • independent native accounts, identical 1% sizing policy');ax.set_ylabel('Closing balance • USD');ax.grid(alpha=.3);ax.legend(loc='upper left',ncol=3,fontsize=9,facecolor='#0c2418',labelcolor='#e8f6ee');bx.set_ylabel('Closed DD %');bx.grid(alpha=.3);fig.tight_layout();fig.savefig(ROOT/f'comparison-{window}.png',dpi=155);plt.close(fig)
 current=next(x for x in normalized if x['window']=='available' and x['variant']=='CURRENT');literal=next(x for x in normalized if x['window']=='available' and x['variant']=='VIDEO_ATR');best_pf=max((x for x in normalized if x['window']=='available'),key=lambda x:x['pf']);best_return=max((x for x in normalized if x['window']=='available'),key=lambda x:x['return_pct'])
 decision=dict(requested_lookback_years=9,available_feed_start='2019-07-16',trade_start_after_warmup='2019-08-01',end_exclusive='2026-10-02',tested_configurations=6,actual_trading_years=(pd.Timestamp('2026-10-02')-pd.Timestamp('2019-08-01')).days/365.2425,primary='VIDEO_ATR',primary_delta_return_pp=literal['return_pct']-current['return_pct'],primary_delta_pf=literal['pf']-current['pf'],primary_delta_win_pp=literal['win_pct']-current['win_pct'],primary_delta_dd_pp=literal['equity_dd_pct']-current['equity_dd_pct'],best_long_history_pf_variant=best_pf['variant'],best_long_history_return_variant=best_return['variant'],exact_vendor_replication=False,pipeline_approved=False,production_changed=False,raw_comparison_only=True)
 md=['# Nasdaq video rule matching — 2026-10-03','','Nine years were requested, but this Exness USTEC feed begins 2019-07-16. The comparison trades from 2019-08-01 after warmup, through 2026-10-01: approximately 7.17 years. No missing years were fabricated.','','All versions: $10,000, 1% equity risk target, existing upward lot rounding (can exceed target), 0.60% price stop, no TP, overnight/weekend holding, one position, native Model 4, 150ms delay, broker commission and swap.','','## Six frozen versions','']
 md += ['- **'+k+'**: '+DESCRIPTIONS[k] for k in ORDER]
 sections=[]
 for window in WINDOW_LABELS:
  md+=['','## '+WINDOW_LABELS[window],'','| Version | Return | Net PF | Net win | Equity DD | Trades | Trades/month / weekday | Daily Sharpe | Max W/L |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
  table='<table><thead><tr>'+''.join('<th>'+x+'</th>' for x in ['Version','Return','Net PF','Net win','Equity DD','Trades','Month / weekday','Daily Sharpe','Max W/L'])+'</tr></thead><tbody>'
  current_win=next(x for x in normalized if x['window']==window and x['variant']=='CURRENT')
  for variant in ORDER:
   z=next(x for x in normalized if x['window']==window and x['variant']==variant)
   cells=[variant,fmt(z['return_pct'])+'%',fmt(z['pf'],3),fmt(z['win_pct'])+'%',fmt(z['equity_dd_pct'])+'%',str(z['trades']),fmt(z['trades_month'])+' / '+fmt(z['trades_weekday'],3),fmt(z['daily_return_sharpe']),f"{z['max_win_streak']} / {z['max_loss_streak']}"]
   table+='<tr>'+''.join('<td>'+html.escape(x)+'</td>' for x in cells)+'</tr>';md.append('| '+' | '.join(cells)+' |')
  table+='</tbody></table>'
  detail='<table><thead><tr>'+''.join('<th>'+x+'</th>' for x in ['Version','Δ return pp','Δ PF','Δ win pp','Δ equity DD pp','Avg/max hold h','Overnight / weekend','Commission / swap','Avg W/L streak'])+'</tr></thead><tbody>'
  for variant in ORDER:
   z=next(x for x in normalized if x['window']==window and x['variant']==variant)
   cells=[variant,fmt(z['return_pct']-current_win['return_pct']),fmt(z['pf']-current_win['pf'],3),fmt(z['win_pct']-current_win['win_pct']),fmt(z['equity_dd_pct']-current_win['equity_dd_pct']),fmt(z['avg_hold_hours'])+' / '+fmt(z['max_hold_hours']),str(z['overnight_positions'])+' / '+str(z['weekend_positions']),'$'+fmt(z['commission'])+' / $'+fmt(z['swap']),fmt(z['avg_win_streak'])+' / '+fmt(z['avg_loss_streak'])]
   detail+='<tr>'+''.join('<td>'+html.escape(x)+'</td>' for x in cells)+'</tr>'
  detail+='</tbody></table>'
  sections.append('<section id="'+window+'"'+('' if window=='available' else ' hidden')+'><h2>'+WINDOW_LABELS[window]+'</h2><div class="box scroll">'+table+'</div>'+picture(ROOT/f'comparison-{window}.png')+'<details><summary>Differences vs current, costs and holding</summary><div class="box scroll">'+detail+'</div></details></section>')
  md+=['','Changes versus CURRENT:']
  for variant in ORDER[1:]:
   z=next(x for x in normalized if x['window']==window and x['variant']==variant);md.append(f"- {variant}: return {z['return_pct']-current_win['return_pct']:+.2f} pp; PF {z['pf']-current_win['pf']:+.3f}; win rate {z['win_pct']-current_win['win_pct']:+.2f} pp; equity DD {z['equity_dd_pct']-current_win['equity_dd_pct']:+.2f} pp.")
 yearly=[]
 for variant in ORDER:
  row=next(x for x in rows if x['manifest']['window']=='available' and x['manifest']['variant']==variant);d=ledger(row);d['year']=pd.to_datetime(d.close_time).dt.year;balance=10000.0
  for year,g in d.groupby('year',sort=True):
   v=g.net_profit.to_numpy();profit=float(v.sum());loss=-float(v[v<0].sum())
   yearly.append(dict(variant=variant,year=int(year),closing_trade_return_pct=profit/balance*100,net=profit,starting_closed_balance=balance,trades=len(g),net_win_pct=float((v>0).mean()*100),net_pf=float(v[v>0].sum()/loss) if loss else None));balance+=profit
 yearnote='Available-history runs only. Yearly returns are grouped by trade close date on each continuous account, not fresh yearly backtests. 2019 and 2026 are partial years; open P&L is not included.'
 md+=['','## Year-by-year closing-trade returns','',yearnote,'','| Year | '+' | '.join(ORDER)+' |','|---|'+'---:|'*len(ORDER)]
 yearsection='<h2>Where did performance change?</h2><p>'+yearnote+'</p><div class="box scroll"><table><thead><tr><th>Year</th>'+''.join('<th>'+v+'</th>' for v in ORDER)+'</tr></thead><tbody>'
 for year in sorted({x['year'] for x in yearly}):
  cells=[str(year)]+[fmt(next(x for x in yearly if x['variant']==v and x['year']==year)['closing_trade_return_pct'])+'%' for v in ORDER]
  md.append('| '+' | '.join(cells)+' |');yearsection+='<tr>'+''.join('<td>'+c+'</td>' for c in cells)+'</tr>'
 yearsection+='</tbody></table></div>'
 sections.append(yearsection)
 (ROOT/'YEARLY.json').write_text(json.dumps(yearly,indent=2))
 limitations='The 0.60% initial stop comes from the older supplied clip, not the current transcript. ATR6/+1R and EMA200/+0.5R are assumed exits, not known vendor settings. A bearish short candle is tested separately because the transcript explicitly requires a bullish body only for longs. Their 982%, 57%, PF 1.29 and 1,448 trades are advertised figures that were not independently verified, and their nine-year claim cannot be reproduced on this feed. Different position sizing or contract prices can alter return and PF. Older ticks are generated, not a nine-year real-tick test. These six configurations and recent windows were retrospectively compared; none is an untouched holdout or approved production winner. No daily loss cap or FTMO portfolio has been simulated here. Existing stop-modification rejections during market-closed intervals are counted, not mistaken for fills; the prior protective stop remains. Charts show independent closing balances, not a shared portfolio or floating equity; table equity DD comes from native MT5.'
 limitations=limitations.replace('Existing stop-modification rejections during market-closed intervals are counted, not mistaken for fills; the prior protective stop remains.','Existing stop-modification rejections (market closed, invalid stops and any unmapped return codes) are counted, not mistaken for fills; the prior protective stop remains. Rejection reasons are retained per case in VERIFICATION.json and METRICS.json. Results reflect the inherited trailing implementation, not a repaired execution engine.')
 limitations+=' Real-tick history quality for CURRENT: '+', '.join(w+' '+next(x for x in normalized if x['window']==w and x['variant']=='CURRENT')['history_quality'] for w in WINDOW_LABELS)+'.'
 limitations+=' Costs are those charged by the native tester; historical changes to broker contract specifications or fee schedules were not separately reconstructed. The legacy cash-Sharpe diagnostic in the raw runner outputs is not used in this report; the displayed calendar-day return calculation includes all closing trades.'
 delayed=current['delayed_entries']
 if delayed:limitations+=' The inherited entry logic has no stale-signal timeout. '+str(len(delayed))+' long-history CURRENT entry was delayed beyond 09:35 NY: '+', '.join(x['fill'] for x in delayed)+'. Its 09:30 signal and actual execution were recorded; no timing fix was introduced into this frozen comparison.'
 conclusion=f"On available history, the literal VIDEO_ATR version changes return by {decision['primary_delta_return_pp']:+.2f} percentage points, net PF by {decision['primary_delta_pf']:+.3f}, net win rate by {decision['primary_delta_win_pp']:+.2f} points and max equity DD by {decision['primary_delta_dd_pp']:+.2f} points versus CURRENT. Best long-history PF among these fixed candidates: {best_pf['variant']}; best return: {best_return['variant']}. These are descriptive ranks, not statistical proof or authorisation to replace the current EA."
 md+=['','## Conclusion','',conclusion,'','## Limits','',limitations,'','## Verification','','Nine unit tests passed; original EX5 vs default-off research copy parity was checked trade-for-trade. Every completed signal, fill, candle body, EMA/DI condition, net P&L, commission, swap and streak was independently audited. No live terminal, installer, website or client EA was changed. Daily Sharpe uses realised calendar-day returns, zero nontrading days and sqrt(365.2425), including Sunday reopening exits. It is not the native MT5 report Sharpe or a forecast.']
 md=[line.replace('Nine unit tests','Ten unit tests') for line in md]
 (ROOT/'REPORT.md').write_text('\n'.join(md),encoding='utf-8');(ROOT/'METRICS.json').write_text(json.dumps(normalized,indent=2));(ROOT/'DECISION.json').write_text(json.dumps(decision,indent=2))
 definitions='<div class="box">'+''.join('<p><strong>'+k+'</strong> — '+html.escape(DESCRIPTIONS[k])+'</p>' for k in ORDER)+'</div>'
 page='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calyx • Nasdaq video comparison</title><style>body{margin:0;background:#07140e;color:#e6f5ed;font:15px system-ui;line-height:1.65}main{max-width:1300px;margin:auto;padding:40px 24px}h1{font-size:44px;line-height:1.15}h2{margin-top:32px}p{color:#b4cdbd}.tag{color:#6eecc1;font-size:12px;letter-spacing:.15em}.box{padding:20px;background:#102219;border:1px solid #2d4a39;border-radius:14px;margin:18px 0}.warning{background:#292a18;border:1px solid #968336;padding:18px;border-radius:12px;color:#ffe799}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:12px;white-space:nowrap;text-align:right;border-bottom:1px solid #2b4333}th{color:#81b497}td:first-child,th:first-child{text-align:left}img{width:100%;height:auto;border-radius:12px;margin:15px 0}select{padding:12px;color:#e6f5ed;background:#102b1b;border:1px solid #5b9572;border-radius:8px;font:inherit}summary{cursor:pointer;color:#70edba}strong{color:#e6f5ed}[hidden]{display:none!important}</style></head><body><main><div class="tag">CALYX • SIX FROZEN VERSIONS • NATIVE MT5 RESEARCH</div><h1>Same Nasdaq entry idea.<br>Different exits. Different results.</h1><p>Nine years requested. Exness USTEC history starts July 2019; trading comparison starts 1 August 2019 after warmup and ends 1 October 2026.</p><div class="warning">RECONSTRUCTION, NOT AN EXACT VENDOR REPLICA • Stop and trailing settings are incomplete. No production change or FTMO approval.</div><p>All versions: $10,000, 1% equity risk target, existing upward lot rounding, 0.60% price stop, no take-profit, overnight/weekend holds, one position. Native Model 4 with 150ms delay, commission and swap included.</p><h2>What changed?</h2>'''+definitions+'<label for="window">Evidence window </label><select id="window">'+''.join('<option value="'+k+'">'+v+'</option>' for k,v in WINDOW_LABELS.items())+'</select>'+''.join(sections)+'<h2>Did matching improve it?</h2><p>'+html.escape(conclusion)+'</p><h2>What we cannot conclude</h2><p>'+html.escape(limitations)+'</p><div class="box"><h2>Verified, but not promoted</h2><p>Nine unit tests; default-off parity against the original production binary; independent trade, clock, body/EMA/DI, P&L and cost checks. Daily Sharpe is calendar-day realised-return Sharpe, not MT5’s native calculation. No new risk setting was chosen to chase the advertised return.</p></div></main><script>document.getElementById("window").addEventListener("change",e=>{document.querySelectorAll("section").forEach(s=>s.hidden=s.id!==e.target.value);});</script></body></html>'
 page=page.replace('Nine unit tests','Ten unit tests')
 (ROOT/'Results.html').write_text(page,encoding='utf-8');print('\n'.join(md))
if __name__=='__main__':main()
