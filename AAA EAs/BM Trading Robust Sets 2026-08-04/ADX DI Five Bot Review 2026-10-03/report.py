"""Offline report: all variants and transparent closed-balance graphs. No website mutation."""
from pathlib import Path
from datetime import datetime
import gzip,html,json
from selection import choose
from verify import check_partial
R=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def f(x,d=2):return '—' if x is None else f'{x:.{d}f}'
def name(x,b):
 if x=='BASE':return 'Unchanged'
 return x.replace('DI_ONLY','DI only').replace('ADX20_DI',f'ADX {">=" if b["gate"]==1 else "<="}20 + DI').replace('ADX25_DI',f'ADX {">=" if b["gate"]==1 else "<="}25 + DI').replace('ADX20',f'ADX {">=" if b["gate"]==1 else "<="}20').replace('ADX25',f'ADX {">=" if b["gate"]==1 else "<="}25')
def plot(base,other):
 paths=[];allpoints=[]
 for z in (base,other):
  trades=json.loads(gzip.decompress((R/'native'/z['tag']/'trades.json.gz').read_bytes()));points=[(datetime(2025,10,2).timestamp(),10000)];bal=10000
  for t in trades:bal+=t['net_profit'];points.append((datetime.fromisoformat(t['close_time']).timestamp(),bal))
  points.append((datetime(2026,10,2).timestamp(),bal));allpoints+=points;paths.append(points)
 lo=min(y for _,y in allpoints);hi=max(y for _,y in allpoints);span=max(hi-lo,1);lo-=span*.1;hi+=span*.1
 start=datetime(2025,10,2).timestamp();end=datetime(2026,10,2).timestamp();parts=[]
 for points,color in zip(paths,('#7e99a0','#76f8c7')):
  xy=[(35+(x-start)/(end-start)*685,175-(y-lo)/(hi-lo)*140) for x,y in points]
  d='M'+f'{xy[0][0]:.2f},{xy[0][1]:.2f}'+''.join(f' H{x:.2f} V{y:.2f}' for x,y in xy[1:]);parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2"/>')
 return f'<svg viewBox="0 0 760 215" role="img" aria-label="Closed balance: unchanged versus highest filtered PF"><text x="35" y="20" fill="#9eb9bb">${hi:,.0f}</text><text x="35" y="199" fill="#9eb9bb">${lo:,.0f} · Oct 2025 → Oct 2026</text>{"".join(parts)}</svg>'
def main():
 results=load(R/'SUMMARY.json');assert len(results)==30
 verification=check_partial();assert verification['checked_cases']==35
 decisions=choose(results);(R/'DECISION.json').write_text(json.dumps(decisions,indent=2),encoding='utf-8')
 bots=load(R/'bots.json');index={x['tag']:x for x in results};parts=[];md=['# Five-EA ADX / DI comparison','', 'Native filter-only exploratory screen: 2 Oct 2025–1 Oct 2026. $10,000, 1% equity-risk target; separate runs, not a portfolio. 150 ms delay, broker costs. No live changes.','', 'Gold reports 75% real ticks, with real tick history beginning 1 Jan 2026; older part is generated. Same-year selection is not untouched validation.','']
 headers=['Variant','Return','PF','Win rate','Equity DD','Trades','/ month','/ weekday','Sharpe¹','W / L streak','Gate rejects','Trade Δ']
 for decision in decisions:
  key=decision['ea'];b=bots[key];rows=[x for x in results if x['ea']==key];base=index[decision['baseline']];best=index[decision['highest_filtered_pf']];selected=index[decision['selected']]
  md+=['## '+b['label'],'',f'Frozen screen selection: **{name(selected["variant"],b)}**. Highest filtered PF: {name(best["variant"],b)}. This is descriptive only.','', '| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|'];table=[]
  for z in rows:
   s=z['stats'];a=z['audit'];vals=[name(z['variant'],b),f(s['return_pct'])+'%',f(s['pf'],3),f(s['win_pct'],1)+'%',f(s['equity_dd_pct'])+'%',str(s['trades']),f(s['trades_month']),f(s['trades_weekday'],3),f(s['sharpe']),f'{s["max_win_streak"]} / {s["max_loss_streak"]}',str(a['rejected']),f'{s["trades"]-base["stats"]["trades"]:+d}']
   md.append('| '+' | '.join(vals)+' |');cl='selected' if z['tag']==decision['selected'] else '';table.append(f'<tr class="{cl}">'+''.join('<td>'+html.escape(x)+'</td>' for x in vals)+'</tr>')
  why=next((x['fails'] for x in decision['assessment'] if key+'-'+x['variant']==best['tag']),[])
  state='Passes the frozen descriptive screen; further validation required.' if decision['passes_descriptive_screen'] else 'No filtered version passes all frozen criteria; keep unchanged.'
  note='Highest-PF filter exclusions: '+('; '.join(why) or 'none under descriptive criteria')+'.'
  plotted=selected if decision['passes_descriptive_screen'] else best
  chart_label='selected candidate' if decision['passes_descriptive_screen'] else 'highest filtered PF (not selected)'
  parts.append(f'<section><h2>{html.escape(b["label"])}</h2><p>{html.escape(state)}</p><p>Selected: <strong>{html.escape(name(selected["variant"],b))}</strong> · Indicator: {b["period"] if key!="london" else "M15"}, ADX14, last completed bar.</p><div class="scroll"><table><thead><tr>'+''.join('<th>'+x+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join(table)+f'</tbody></table></div><p>{html.escape(note)}</p><h3>Closed balance: baseline vs {chart_label}</h3><p><span class="gray">■ Unchanged</span> · <span class="green">■ {html.escape(name(plotted["variant"],b))}</span> · Not a floating-equity graph.</p>{plot(base,plotted)}<p>Native history quality: {html.escape(base["stats"]["history_quality"])}. Original/copy parity: {base["stats"]["trades"]} identical trades.</p></section>')
  md+=['',note,'']
  # Export research-only SETs. These binaries deliberately refuse live initialization.
  setting=load(R/'native'/decision['selected']/'manifest.json')['inputs'];folder=R/'Selected Research Sets';folder.mkdir(exist_ok=True)
  (folder/(key+'.set')).write_text('\n'.join(k+'='+v for k,v in setting.items())+'\n',encoding='utf-8')
 md+=['## Interpretation','', 'Thirty searched settings, five original controls. Every trial is shown. No untouched out-of-sample test, no claim of proven edge or full-pipeline completion. Do not deploy these research binaries: they refuse non-tester initialization.','', '¹ Sharpe: annualized calendar-day closed-balance returns, including zero days, zero risk-free rate; not native trade-level Sharpe and not floating-equity Sharpe.','', 'Equity DD is native MT5 peak-to-trough relative drawdown. PF and win rate use net trade P&L including commission and swap. Gates rejected count candidate attempts on each resulting exposure path; trade Δ is the actual trade-count change, not a one-for-one filtered baseline subset. Upward/minimum lot rounding can exceed the 1% target.','', 'Selection criteria: >=30 trades, >=half baseline count, PF>=1.20 and >=baseline+0.05, positive net, return>=baseline, equity DD<=baseline. Otherwise retain BASE. Win streaks and higher win rate alone are not sufficient.','', f'Verified {verification["ledger_trades_crosschecked"]} ledger trades and {verification["entry_fills_crosschecked"]} entry fills. Original files unchanged.']
 uncertainty_file=R/'UNCERTAINTY.json'
 uncertainty_html=''
 if uncertainty_file.exists():
  uncertainty=load(uncertainty_file);uncertainty_rows=[]
  md+=['','## Conditional block-bootstrap uncertainty','','10,000 circular paths, five-trade blocks; historical net cash amounts. Not search-adjusted, not an untouched test, not prospective dynamic sizing. These intervals do not establish an improvement over baseline. Fewer than 20 trades: no meaningful interval reported.','','| Candidate | PF p05 | PF p95 | Net cash p05 |','|---|---:|---:|---:|']
  for decision in decisions:
   tag=decision['selected'];z=index[tag];u=uncertainty[tag]
   vals=[z['label']+' · '+name(z['variant'],bots[z['ea']]),f(u.get('pf_p05'),3),f(u.get('pf_p95'),3),'$'+f(u.get('net_cash_p05'))]
   md.append('| '+' | '.join(vals)+' |');uncertainty_rows.append('<tr>'+''.join('<td>'+html.escape(x)+'</td>' for x in vals)+'</tr>')
  uncertainty_html='<section><h2>Uncertainty, not a guarantee</h2><p>10,000 circular block-bootstrap paths, five-trade blocks, resampling historical net cash. These are NOT search-adjusted tests of improvement, prospective dynamic sizing or untouched out-of-sample validation. Very small samples are refused.</p><div class="scroll"><table><thead><tr><th>Candidate</th><th>PF p05</th><th>PF p95</th><th>Net cash p05</th></tr></thead><tbody>'+''.join(uncertainty_rows)+'</tbody></table></div></section>'
 md=[x.replace('Gold reports 75% real ticks','Both XAUUSD and USDJPY report 75% real ticks') for x in md]
 (R/'REPORT.md').write_text('\n'.join(md),encoding='utf-8')
 quality='; '.join(bots[k]['label']+': '+index[k+'-BASE']['stats']['history_quality'] for k in bots)
 doc='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Calyx · ADX / DI five-EA study</title><style>:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#081511;color:#e9f8f2;font:15px/1.65 system-ui}main{max-width:1400px;margin:auto;padding:45px 25px}h1{font-size:42px;line-height:1.15}h2{color:#76f8c7}p{color:#aec5c5}.brand{color:#76f8c7;letter-spacing:3px;font-size:12px}.warning{border:1px solid #84733c;background:#24271a;padding:18px;border-radius:12px}section{margin:28px 0;padding:24px;border:1px solid #274039;border-radius:18px;background:#0d1d18}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:10px 9px;border-bottom:1px solid #28413b;text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}.selected{background:#16362a}.green{color:#76f8c7}.gray{color:#7e99a0}svg{max-width:900px;width:100%;background:#091813;border-radius:12px}footer{padding:25px;color:#a4bdbc}</style><main><div class="brand">CALYX · RESEARCH EVIDENCE · OFFLINE</div><h1>Five bots.<br>ADX and DI, tested separately.</h1><p>2 October 2025–1 October 2026 · $10,000 per run · 1% equity-risk target · native MT5 Model 4 · 150ms delay · all 30 variants, five parity controls.</p><div class="warning">Exploratory screen, not a proven upgrade. Search and evaluation use the same year. Gold has partial real-tick coverage; first three months use generated ticks. No live terminals, installers or website settings were changed. These research binaries cannot run live.</div>'''+''.join(parts)+f'<footer><h2>Evidence and limits</h2><p>{html.escape(quality)}</p><p>PF / win rate are net of commission and swap. Equity DD is native relative floating-equity drawdown; charts show closed balance only. Sharpe¹ is annualized calendar-day closed-balance returns, including zero days (zero risk-free rate), not native trade-level Sharpe.</p><p>Gate rejects count attempted candidates on each variant’s own exposure path. Trade Δ compares actual trade count with baseline, not a direct rejected subset. Minimum/upward lot rounding can exceed the target risk. Separate runs are not a shared portfolio.</p><p>Screen requires ≥30 trades, ≥50% of baseline trades, PF≥1.20 and ≥baseline+0.05, positive net, return≥baseline and equity DD≤baseline. Passing this screen is not approval to deploy. Holdout / rolling tests, cost stress and Monte Carlo remain outstanding.</p><p>All five default-off parity checks passed. {verification["ledger_trades_crosschecked"]} trade records and {verification["entry_fills_crosschecked"]} entry fills crosschecked. Source, SET and original compiled hashes unchanged.</p></footer></main></html>'
 doc=doc.replace('Gold has partial real-tick coverage','All five runs have partial real-tick coverage').replace('<footer>',uncertainty_html+'<footer>')
 (R/'Results.html').write_text(doc,encoding='utf-8');print('Report, decisions, graphs, research SETs and verification saved.')
if __name__=='__main__':main()
