"""Position-ID accounting, independent native reconciliation and offline portfolio report."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from collections import defaultdict
from html.parser import HTMLParser
import csv,gzip,hashlib,html,io,json,math,re,statistics
R=Path(__file__).resolve().parent;B=R.parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def at(ms):return datetime.fromtimestamp(float(ms)/1000,timezone.utc).isoformat(timespec='milliseconds')
def raw(folder,suffix):return list(csv.DictReader(io.StringIO(gzip.decompress((folder/(suffix+'.csv.gz')).read_bytes()).decode('utf-8-sig'))))
def stats(trades):
 ps=[t['net_profit'] for t in trades];gw=sum(p for p in ps if p>0);gl=-sum(p for p in ps if p<0)
 w=l=mw=ml=0
 for t in sorted(trades,key=lambda t:(t['close_time_msc'],t['last_deal'])):
  if t['net_profit']>0:w+=1;l=0
  elif t['net_profit']<0:l+=1;w=0
  else:w=l=0
  mw=max(mw,w);ml=max(ml,l)
 return dict(trades=len(ps),wins=sum(p>0 for p in ps),losses=sum(p<0 for p in ps),flats=sum(p==0 for p in ps),win_rate_pct=100*sum(p>0 for p in ps)/len(ps) if ps else None,profit_factor=gw/gl if gl else None,net_profit=round(sum(ps),2),contribution_pct=round(sum(ps)/100,4),max_win_streak=mw,max_loss_streak=ml,avg_win=gw/sum(p>0 for p in ps) if any(p>0 for p in ps) else None,avg_loss=-gl/sum(p<0 for p in ps) if any(p<0 for p in ps) else None,avg_trade=statistics.mean(ps) if ps else None,best_trade=max(ps) if ps else None,worst_trade=min(ps) if ps else None,commission=round(sum(t['commission'] for t in trades),2),swap=round(sum(t['swap'] for t in trades),2),fees=round(sum(t['fees'] for t in trades),2),boundary_exits=sum(t['boundary_exit'] for t in trades),boundary_net=round(sum(t['net_profit'] for t in trades if t['boundary_exit']),2),mean_hold_hours=statistics.mean(t['hold_hours'] for t in trades) if trades else None)
class Rows(HTMLParser):
 def __init__(self):super().__init__();self.rows=[];self.current=None;self.cell=None
 def handle_starttag(self,tag,attrs):
  if tag=='tr':self.current=[]
  if tag=='td' and self.current is not None:self.cell=[]
 def handle_data(self,s):
  if self.cell is not None:self.cell.append(s)
 def handle_endtag(self,tag):
  if tag=='td' and self.cell is not None:self.current.append(' '.join(''.join(self.cell).split()));self.cell=None
  if tag=='tr' and self.current is not None:self.rows.append(self.current);self.current=None
def number(x):return float(x.replace(' ','').replace(',',''))
def ledger(folder,config):
 deals=raw(folder,'deals');groups=defaultdict(list)
 for d in deals:groups[int(d['position_id'])].append(d)
 bymagic={int(e['inputs']['InpMagic']):e for e in config['entries']};trades=[]
 for pid,ds in groups.items():
  ds.sort(key=lambda d:(int(d['time_msc']),int(d['ticket'])));ins=[d for d in ds if int(d['entry'])==0];outs=[d for d in ds if int(d['entry']) in (1,3)]
  assert ins and outs and len(ins)+len(outs)==len(ds),(pid,'missing entry/exit')
  vi=sum(float(d['volume']) for d in ins);vo=sum(float(d['volume']) for d in outs);assert abs(vi-vo)<1e-8
  magic=int(ins[0]['magic']);e=bymagic[magic];assert all(d['symbol']==e['symbol'] for d in ds)
  assert all(int(d['magic']) in (magic,0) for d in ds)
  fields={k:sum(float(d[k]) for d in ds) for k in ('profit','commission','swap','fee')}
  op=sum(float(d['price'])*float(d['volume']) for d in ins)/vi;cl=sum(float(d['price'])*float(d['volume']) for d in outs)/vo
  net=round(sum(fields.values()),2);ot=int(ins[0]['time_msc']);ct=int(outs[-1]['time_msc']);sl=float(ins[0]['initial_sl']);hourly=e['key'].startswith('H')
  assert sl==0 if hourly else sl>0
  budget_reference=vi*(float(e['inputs']['InpHistoricalLossPoints']) if hourly else abs(op-sl)*(100 if e['symbol']=='XAUUSD' else 1))
  trades.append(dict(position_id=pid,magic=magic,key=e['key'],ea=e['label'],symbol=e['symbol'],side='Long' if int(ins[0]['type'])==0 else 'Short',volume=vi,open_time=at(ot),close_time=at(ct),open_time_msc=ot,close_time_msc=ct,open_price=op,close_price=cl,initial_sl=sl,initial_tp=float(ins[0]['initial_tp']),gross_profit=round(fields['profit'],2),commission=round(fields['commission'],2),swap=round(fields['swap'],2),fees=round(fields['fee'],2),net_profit=net,hold_hours=(ct-ot)/3600000,last_deal=int(outs[-1]['ticket']),entry_comment=ins[0]['comment'],exit_comment=outs[-1]['comment'],boundary_exit=any('end of test' in d['comment'].lower() for d in outs),sizing_reference_cash=budget_reference,sizing_reference_not_loss_cap=hourly))
 trades.sort(key=lambda t:(t['close_time_msc'],t['last_deal']))
 # Independently reconcile native report deal tickets and cash; never FIFO by symbol.
 rb=gzip.decompress((folder/'report.htm.gz').read_bytes());body=rb.decode('utf-16') if rb[:2] in (b'\xff\xfe',b'\xfe\xff') else rb.decode('utf-8-sig')
 p=Rows();p.feed(body);native_deals={int(r[1]):r for r in p.rows if len(r)>=13 and re.fullmatch(r'\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}',r[0]) and r[3].lower() in ('buy','sell') and r[4].lower() in ('in','out','out by')}
 assert set(native_deals)=={int(d['ticket']) for d in deals},'Native deal ticket mismatch'
 for d in deals:
  r=native_deals[int(d['ticket'])];assert r[2]==d['symbol'];assert abs(number(r[5])-float(d['volume']))<1e-8;assert abs(number(r[6])-float(d['price']))<.00001
  for col,key in ((8,'commission'),(9,'swap'),(10,'profit')):assert abs(number(r[col])-float(d[key]))<.011
  native_time=datetime.strptime(r[0],'%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc);assert native_time.timestamp()==int(d['time_msc'])//1000
 result=read(folder/'results.json');s=stats(trades)
 assert len(trades)==result['native']['trades'];assert abs(s['net_profit']-result['native']['net_profit'])<.02
 # Native profitable-trade count classifies nonnegative gross movement, including flat fills.
 # Fully net winners can be fewer after commissions/carry; keep both definitions explicit.
 gross_cash=[sum(float(d['profit']) for d in ds) for ds in groups.values()]
 native_wr=100*sum(x>=0 for x in gross_cash)/len(gross_cash)
 native_pf=s['profit_factor']
 assert abs(native_wr-result['native']['win_rate_pct'])<.011,(native_wr,result['native'])
 assert abs(native_pf-result['native']['profit_factor'])<.011,(native_pf,result['native'])
 return trades,deals,result,dict(position_id_pairing=True,positions=len(trades),raw_deals=len(deals),native_ticket_price_volume_time_and_costs_reconciled=True,native_cash_and_exit_metric_definitions_reconciled=True,net_position_win_rate=s['win_rate_pct'],native_exit_win_rate=native_wr,net_position_pf=s['profit_factor'],native_exit_pf=native_pf)
def cash_metrics(deals,start,end):
 daily=defaultdict(float);monthly=defaultdict(float)
 for d in deals:
  t=at(d['time_msc']);v=sum(float(d[k]) for k in ('profit','commission','swap','fee'));daily[t[:10]]+=v;monthly[t[:7]]+=v
 bal=10000;peak=10000;dd=0;returns=[];curve=[];day=datetime.fromisoformat(start).replace(tzinfo=timezone.utc);last=datetime.fromisoformat(end).replace(tzinfo=timezone.utc)
 while day<last:
  v=daily[day.date().isoformat()];returns.append(v/bal);bal+=v;peak=max(peak,bal);dd=max(dd,(peak-bal)/peak*100);curve.append([day.date().isoformat(),round(bal,2)]);day+=timedelta(days=1)
 sd=statistics.stdev(returns);sharpe=statistics.mean(returns)/sd*math.sqrt(365) if sd else None
 months=[];bal=10000
 for month in sorted(monthly):
  v=monthly[month];months.append(dict(month=month,start_balance=round(bal,2),net_profit=round(v,2),return_pct=v/bal*100,end_balance=round(bal+v,2)));bal+=v
 return dict(daily_cash_sharpe=sharpe,daily_balance_dd_pct=dd,daily_curve=curve,months=months)
def render(data):
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 import matplotlib.dates as md
 f=R/'native/combined';curve=raw(f,'curve');dates=[datetime.strptime(x['minute'],'%Y.%m.%d %H:%M:%S') if not x['minute'].isdigit() else datetime.fromtimestamp(int(x['minute']),timezone.utc).replace(tzinfo=None) for x in curve]
 eq=[float(x['equity_next']) for x in curve];bal=[float(x['balance_next']) for x in curve]
 plt.rcParams.update({'figure.facecolor':'#071811','axes.facecolor':'#0b2119','axes.labelcolor':'#def6e8','text.color':'#def6e8','xtick.color':'#a8c7b7','ytick.color':'#a8c7b7','axes.edgecolor':'#406554','grid.color':'#264538'})
 fig,ax=plt.subplots(figsize=(13,5.5));ax.plot(dates,eq,color='#6cbaff',lw=.8,label='Shared floating equity');ax.plot(dates,bal,color='#80f5b7',lw=1.3,label='Shared balance');ax.axhline(10000,color='#78877e',ls='--',lw=.7);ax.set_title('Five EAs on one account · 1% target/scenario sizing · 7 Jul–6 Oct 2026');ax.set_ylabel('USD');ax.grid(alpha=.45);ax.xaxis.set_major_formatter(md.DateFormatter('%d %b'));ax.legend(facecolor='#10291d',labelcolor='#def6e8');fig.tight_layout();fig.savefig(R/'shared-equity.png',dpi=150);plt.close(fig)
 def n(x,d=2):return '—' if x is None else f'{x:,.{d}f}'
 total=data['combined'];summary=total['summary'];native=total['native'];per=''
 for e in data['attribution']:
  s=e['summary'];per+=f"<tr><td>{html.escape(e['label'])}</td><td>{s['trades']}</td><td>{n(s['win_rate_pct'],1)}%</td><td>{n(s['profit_factor'])}</td><td>${n(s['net_profit'])}</td><td>{s['contribution_pct']:+.2f}%</td><td>{s['max_win_streak']} / {s['max_loss_streak']}</td><td>{n(s['avg_win'])} / {n(s['avg_loss'])}</td></tr>"
 months=''.join(f"<tr><td>{m['month']}</td><td>${n(m['start_balance'])}</td><td>${n(m['net_profit'])}</td><td>{m['return_pct']:+.2f}%</td><td>${n(m['end_balance'])}</td></tr>" for m in data['cash']['months'])
 controls=''.join(f"<tr><td>{html.escape(e['label'])}</td><td>{e['summary']['trades']}</td><td>{n(e['summary']['win_rate_pct'],1)}%</td><td>{n(e['summary']['profit_factor'])}</td><td>{e['summary']['contribution_pct']:+.2f}%</td><td>{n(e['native']['floating_dd_relative_pct'])}%</td></tr>" for e in data['standalone'])
 ledger=''
 for t in total['trades']:
  ledger+=f"<tr><td>{html.escape(t['ea'])}</td><td>{t['open_time']}</td><td>{t['close_time']}</td><td>{t['side']}</td><td>{t['volume']:.2f}</td><td>{n(t['open_price'],3)}</td><td>{n(t['close_price'],3)}</td><td>${n(t['net_profit'])}</td><td>{html.escape(t['exit_comment']) or 'Timed/signal close'}</td></tr>"
 cards=''.join(f'<section><small>{label}</small><strong>{value}</strong></section>' for label,value in [('Combined return',f"{summary['contribution_pct']:+.2f}%"),('Final balance',f"${n(native['final_balance'])}"),('Closed positions',str(summary['trades'])),('Win rate',n(summary['win_rate_pct'],1)+'%'),('Net position PF',n(summary['profit_factor'])),('Native equity DD',n(native['floating_dd_relative_pct'])+'%'),('MT5 Sharpe',n(native['sharpe_ratio'])),('Max win / loss streak',f"{summary['max_win_streak']} / {summary['max_loss_streak']}")])
 body=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Five EA Shared Portfolio · Last Three Months</title><style>body{{background:#071811;color:#e4f8ed;font:15px system-ui;max-width:1350px;margin:35px auto;padding:20px}}h1{{font-size:38px}}p,li{{line-height:1.7}}small{{color:#aacbbb}}strong{{display:block;font-size:28px;margin-top:10px}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:15px}}section{{padding:20px;background:#10261c;border:1px solid #315441;border-radius:12px}}aside{{border:1px solid #ba9943;background:#2b2515;color:#ffe6a1;padding:18px;line-height:1.7}}table{{border-collapse:collapse;width:100%;margin:20px 0}}th,td{{padding:12px;border-bottom:1px solid #2a4836;text-align:left}}.scroll{{overflow:auto}}img{{width:100%;border-radius:12px}}a{{color:#79f0b2}}@media(max-width:750px){{.cards{{grid-template-columns:repeat(2,1fr)}}}}</style></head><body>
 <h1>Five EAs · one shared account</h1><p>US30 Hourly · US100 Hourly · Nasdaq 5M Momentum + DI · RSI VWAP Gold · EMA3 Gold.<br>7 July–6 October 2026 inclusive · $10,000 starting balance · 1% target/scenario sizing per trade.</p>
 <aside>Native MT5 multi-symbol, hedging-account test: one balance, floating equity, simultaneous positions, broker lot steps and recorded costs. Hourly sizing uses 611.53 US30 / 358.71 US100 historical loss points; these bots have NO stop-loss. Their 1% setting is a sizing scenario, not a maximum loss. Other bots retain current minimum-lot/round-up behavior, so actual initial stop exposure can exceed 1%. There is no combined 1% portfolio cap.</aside>
 <div class="cards">{cards}</div><h2>Shared balance and floating equity</h2><img src="shared-equity.png" alt="Five EAs shared balance and floating equity over the latest three months">
 <p>Cash net: ${n(summary['net_profit'])}; commission ${n(summary['commission'])}, swap ${n(summary['swap'])}, fees ${n(summary['fees'])}. Closed-balance drawdown {n(native['balance_dd_relative_pct'])}%. Daily calendar cash-return Sharpe {n(data['cash']['daily_cash_sharpe'])} (365-day annualization; not the MT5 Sharpe). Dispatcher-observed equity drawdown {n(data['audit']['measured_dd'])}%; maximum simultaneous positions {data['audit']['max_positions']}.</p>
 <h2>Each EA's contribution inside the shared account</h2><p>These dollar contributions sum exactly to the combined result. Contribution % divides by the original $10,000; it is not a separately compounded standalone return.</p><div class="scroll"><table><thead><tr><th>EA</th><th>Trades</th><th>Win rate</th><th>Net PF</th><th>Net contribution</th><th>Contribution %</th><th>Max W / L streak</th><th>Average win / loss $</th></tr></thead><tbody>{per}</tbody></table></div>
 <h2>Monthly account cash movements</h2><p>July begins on the 7th; October ends on the 6th. Cash movements include entry fees on their actual deal dates and differ slightly from grouping whole-trade profits by close month.</p><table><thead><tr><th>Month</th><th>Starting balance</th><th>Net cash movement</th><th>Month return</th><th>Ending balance</th></tr></thead><tbody>{months}</tbody></table>
 <h2>Standalone controls · not added together</h2><p>Same module rules, same dates and fresh $10,000 for each. The shared account sizes from combined equity/balance, so its result is not the sum of these compounded returns.</p><table><thead><tr><th>EA alone</th><th>Trades</th><th>Win rate</th><th>Net PF</th><th>Return</th><th>Native equity DD</th></tr></thead><tbody>{controls}</tbody></table>
 <h2>Execution, boundary and validity</h2><p>Requested real-tick mode; native history quality: {html.escape(native['history_quality'])}. 150ms modeled order delay; 1:2000 tester leverage. No optimizer, changed filters, news bots, adaptive governor or FTMO guards. Positions start flat. {summary['boundary_exits']} position(s), net ${n(summary['boundary_net'])}, were closed by the tester at the end boundary rather than their strategy exit. Actual live account history was not used.</p>
 <p>The frozen production sources are mechanically namespaced into a research-only dispatcher. The primary XAUUSD ticks plus a 5-second timer dispatch new quotes for the three symbols; this is not five independently attached chart tick handlers and can affect fill timing. Standalone controls and the production Nasdaq parity check are recorded in VERIFICATION.json. Broker history, historical spreads/carry and hypothetical delays do not predict live execution.</p>
 <p>Hourly entry hours and historical-loss references were selected using data overlapping this period. This is a current-configuration retrospective, NOT untouched out-of-sample evidence or a forecast. No live EAs, BATs, website pages or Git-tracked production files were changed.</p>
 <details><summary>All {summary['trades']} closed positions · timestamps UTC</summary><div class="scroll"><table><thead><tr><th>EA</th><th>Entry UTC</th><th>Exit UTC</th><th>Side</th><th>Lots</th><th>Entry</th><th>Exit</th><th>Net $</th><th>Exit</th></tr></thead><tbody>{ledger}</tbody></table></div></details>
 <p><a href="Results.json">Complete results</a> · <a href="VERIFICATION.json">Independent reconciliation</a> · <a href="CONFIG.json">Frozen settings and source fingerprints</a></p></body></html>'''
 (R/'Results.html').write_text(body,encoding='utf-8')
 assert body.count('<tr>')==len(data['attribution'])+len(data['cash']['months'])+len(data['standalone'])+len(total['trades'])+4
 save(R/'HTML-QA.json',dict(passed=True,bytes=(R/'Results.html').stat().st_size,positions=len(total['trades']),tables=4,graph_sha256=sha(R/'shared-equity.png')))
def main():
 config=read(R/'CONFIG.json');checks=[]
 for e in config['entries']:
  assert sha(B/e['source'])==e['source_sha256'];assert sha((B/e['source']).with_suffix('.ex5'))==e['binary_sha256'];assert sha(B/e['preset'])==e['preset_sha256']
  for path,s in e['dependencies'].items():assert sha(B/path)==s
 trades,deals,result,check=ledger(R/'native/combined',config);checks.append(dict(case='combined',**check));s=stats(trades)
 attribution=[dict(key=e['key'],label=e['label'],summary=stats([t for t in trades if t['key']==e['key']])) for e in config['entries']]
 assert abs(sum(x['summary']['net_profit'] for x in attribution)-s['net_profit'])<.01
 alone=[]
 for e in config['entries']:
  ts,ds,r,c=ledger(R/'native'/(e['key']+'-alone'),config);checks.append(dict(case=e['key']+'-alone',**c));alone.append(dict(key=e['key'],label=e['label'],summary=stats(ts),native=r['native'],trades=ts))
 # Exact production Nasdaq baseline already tested for these dates in the duration study.
 original=read(B/'Nasdaq Opening Candle Duration Comparison 2026-10-07/native/3m-M5-PRODUCTION/results.json');n5=next(x for x in alone if x['key']=='N5')
 assert original['manifest']['binary_sha256']==next(e['binary_sha256'] for e in config['entries'] if e['key']=='N5')
 keys=('side','volume','open_price','close_price','gross_profit','commission','swap','net_profit','initial_sl','initial_tp')
 def normalized(t):return {k:round(t[k],6) if isinstance(t[k],float) else t[k] for k in keys}|{'open_time':t['open_time'][:19],'close_time':t['close_time'][:19]}
 parity=[normalized(t) for t in original['trades']]==[normalized(t) for t in n5['trades']]
 # Record timing deviations honestly; do not silently relabel them exact parity.
 diffs=[]
 for i,(a,b) in enumerate(zip(original['trades'],n5['trades'])):
  aa,bb=normalized(a),normalized(b)
  if aa!=bb:diffs.append(dict(index=i,production=aa,adapter=bb))
 assert len(original['trades'])==len(n5['trades']),'Nasdaq signal count changed'
 assert all(a['side']==b['side'] and a['open_time'][:16]==b['open_time'][:16] for a,b in zip(original['trades'],n5['trades'])),'Nasdaq entry signal changed'
 parity_result=dict(exact_trade_for_trade=parity,production_positions=len(original['trades']),adapter_positions=len(n5['trades']),same_signal_minutes_and_direction=True,differences=diffs)
 audit_match=re.search(r'measured_dd=([\d.]+) max_positions=(\d+)',result['audit'][0]);assert audit_match
 audit=dict(measured_dd=float(audit_match[1]),max_positions=int(audit_match[2]))
 cash=cash_metrics(deals,config['start'],config['end_exclusive']);data=dict(window=dict(start=config['start'],end_exclusive=config['end_exclusive'],last_complete_date='2026-10-06'),deposit=10000,risk_percent=1,combined=dict(summary=s,native=result['native'],trades=trades,warnings=result['warnings'],tick_notes=result['tick_notes']),attribution=attribution,standalone=alone,cash=cash,audit=audit,nasdaq_production_parity=parity_result,limitations=['No SL on hourly; historical-loss sizing is not a risk cap','Production minimum-lot/ceil policies can exceed 1% actual stop exposure','Current-configuration in-sample retrospective','Native multi-symbol dispatcher is not five independent chart handlers','Flat start and native end-boundary liquidation','No live deployment changed'])
 save(R/'Results.json',data);save(R/'VERIFICATION.json',dict(passed=True,cases=checks,nasdaq_production_parity=parity_result,source_dependencies_and_presets_unchanged=True,shared_contributions_reconcile=True,no_optimizer=True,no_live_terminal_changed=True));render(data)
 print(json.dumps(dict(combined=s,native=result['native'],attribution=attribution,months=cash['months'],audit=audit,production_parity=parity_result),indent=2))
if __name__=='__main__':main()
