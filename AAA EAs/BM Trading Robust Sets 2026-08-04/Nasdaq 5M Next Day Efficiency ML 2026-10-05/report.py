"""Offline comparison report; no production website changes."""
from pathlib import Path
import html,json,math
import pandas as pd
import numpy as np
R=Path(__file__).resolve().parent
rows=[json.loads(p.read_text()) for p in sorted((R/'native').glob('*/results.json'))]
results={x['tag']:x for x in rows}
model=json.loads((R/'MODEL.json').read_text());weights=json.loads((R/'weights.json').read_text())
def esc(x):return html.escape(str(x))
def num(x,d=2):return '—' if x is None else f'{x:,.{d}f}'
def chart(window):
 series=[];colors=['#7eacff','#7bf5c9','#f9c474'];labels=['Current DI-on','Logistic ER gate','Previous ER control']
 for i,case in enumerate(['BASE','ML','LAG']):
  path=R/'native'/f'{window}_{case}'/'equity.csv'
  if not path.exists():continue
  df=pd.read_csv(path);series.append((df,colors[i],labels[i]))
 if not series:return ''
 xmin=min(d.epoch.min() for d,_,_ in series);xmax=max(d.epoch.max() for d,_,_ in series)
 ymin=min(d.equity.min() for d,_,_ in series);ymax=max(d.equity.max() for d,_,_ in series)
 pad=max(100,(ymax-ymin)*.08);ymin-=pad;ymax+=pad
 def xy(t,v):return 85+900*(t-xmin)/max(1,xmax-xmin),310-230*(v-ymin)/max(1,ymax-ymin)
 svg='<svg viewBox="0 0 1060 385" role="img" aria-label="'+window+' sampled floating equity comparison">'
 for k in range(5):
  v=ymin+(ymax-ymin)*k/4;x,y=xy(xmin,v)
  svg+=f'<line x1="85" y1="{y:.2f}" x2="985" y2="{y:.2f}" stroke="#25403a"/><text x="75" y="{y+4:.2f}" text-anchor="end" fill="#aac4bb">$'+num(v,0)+'</text>'
 for k in range(5):
  t=xmin+(xmax-xmin)*k/4;x,y=xy(t,ymin);label=pd.Timestamp(t,unit='s',tz='UTC').strftime('%d %b %y')
  anchor='start' if k==0 else 'end' if k==4 else 'middle'
  svg+=f'<text x="{x:.2f}" y="340" text-anchor="{anchor}" fill="#aac4bb">{label}</text>'
 for i,(d,color,label) in enumerate(series):
  step=max(1,len(d)//1800);view=pd.concat([d.iloc[::step],d.iloc[[-1]]]).drop_duplicates()
  points=' '.join(f'{x:.2f},{y:.2f}' for x,y in [xy(t,v) for t,v in zip(view.epoch,view.equity)])
  svg+=f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/><line x1="{85+i*295}" y1="35" x2="{110+i*295}" y2="35" stroke="{color}" stroke-width="3"/><text x="{118+i*295}" y="39" fill="{color}">{label}</text>'
 return '<div class="plot">'+svg+'</svg></div>'
def table(window):
 content='<div class="scroll"><table><thead><tr>'+''.join('<th>'+x+'</th>' for x in ['Version','Trades','Net return','Net PF','Win rate','Equity DD','MT5 Sharpe','Daily equity Sharpe','Win / loss run','Net $/trade'])+'</tr></thead><tbody>'
 for case,label in [('BASE','Current DI-on'),('ML','Logistic ER gate'),('LAG','Previous ER control')]:
  x=results.get(window+'_'+case)
  if not x:continue
  m=x['metrics'];cells=[label,str(m['trades']),num(m['return_pct'])+'%',num(m['net_pf'],3),num(m['win_rate_pct'],1)+'%',num(m['equity_dd_pct'])+'%',num(m['sharpe_ratio']),num(m['daily_equity_sharpe']),f"{m['max_win_streak']} / {m['max_loss_streak']}",'$'+num(m['expectancy'])]
  content+='<tr>'+''.join('<td>'+c+'</td>' for c in cells)+'</tr>'
 return content+'</tbody></table></div>'
def cohorts(window):
 trades=results[window+'_BASE']['trades'];v=[]
 for state in [True,False]:
  ts=[t for t in trades if t['ml_allow']==state];vals=[t['net_profit'] for t in ts]
  v.append(dict(prediction='High: gate would allow' if state else 'Low: gate would skip',trades=len(ts),mean_net=float(np.mean(vals)) if vals else None,total_net=sum(vals),win_rate=100*sum(x>0 for x in vals)/len(vals) if vals else None))
 return v
summary=[]
for window in ['3M','6M','2Y']:
 for case in ['BASE','ML','LAG']:
  x=results.get(window+'_'+case)
  if x:summary.append(dict(window=window,version=case,start=x['start'],end_exclusive=x['end_exclusive'],**x['metrics']))
pd.DataFrame(summary).to_csv(R/'SUMMARY.csv',index=False)
(R/'SUMMARY.json').write_text(json.dumps(dict(comparison=summary,baseline_entry_cohorts={w:cohorts(w) for w in ['3M','6M','2Y']}),indent=2))
base=results['6M_BASE']['metrics'];ml=results['6M_ML']['metrics']
recent_base=results['3M_BASE']['metrics'];recent_ml=results['3M_ML']['metrics']
outcome='Mixed results: six-month gains did not survive the latest three months.' if recent_ml['return_pct']<recent_base['return_pct'] else 'Exploratory results only: prediction skill and robustness still need validation.'
body=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Nasdaq 5M · Next-day efficiency gate</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#07120f;color:#eefaf5;font-family:Segoe UI,Arial,sans-serif;line-height:1.6}}main{{max-width:1260px;margin:auto;padding:44px 24px 80px}}h1{{font-size:clamp(32px,5vw,56px);line-height:1.12;margin:12px 0 22px}}h2{{font-size:26px;margin:0 0 14px}}h3{{font-size:19px}}p{{color:#abc9bd}}a{{color:#80f4cc}}.tag{{font:12px Consolas,monospace;color:#80f4cc;letter-spacing:2px}}.panel{{padding:24px;border:1px solid #294038;background:#0c1c16;border-radius:18px;margin:24px 0}}.notice{{border-color:#807138;background:#211f10}}.scroll,.plot{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;white-space:nowrap;font-size:14px}}th,td{{text-align:right;padding:13px 12px;border-bottom:1px solid #294038}}th:first-child,td:first-child{{text-align:left}}th{{color:#98b8a9;font-size:12px}}td:first-child{{font-weight:600}}.plot svg{{width:100%;min-width:900px;font:13px Segoe UI,Arial,sans-serif}}details{{border-top:1px solid #294038;margin:16px 0;padding-top:12px}}summary{{cursor:pointer;color:#80f4cc}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.mini{{padding:16px;background:#071610;border:1px solid #294038;border-radius:12px}}.value{{font-size:27px;font-weight:700}}.small{{font-size:13px;color:#a2bdb1}}li{{margin-bottom:8px}}@media(max-width:650px){{main{{padding:24px 14px}}.panel{{padding:18px}}.grid{{grid-template-columns:1fr}}}}
</style></head><body><main>
<div class="tag">CALYX · ISOLATED RESEARCH · 05 OCT 2026</div><h1>Does tomorrow’s efficiency<br>help Nasdaq opening momentum?</h1>
<p>Exact current BAT entry and management rules, with an independent 15-feature logistic-regression gate. No production bot, installer or live account changed.</p>
<div class="panel notice"><h2>{outcome}</h2><p>The creator did not publish the 15 features, target definition or weights. This is a transparent reconstruction, not a reproduction of their claimed results. Historical simulation is not a return forecast.</p></div>
<div class="grid"><div class="mini"><div class="tag">TRAINING</div><div class="value">2020–2023</div><span class="small">965 complete target sessions; training median defines “high”.</span></div>
<div class="mini"><div class="tag">UNSEEN MODEL DATA</div><div class="value">2 years</div><span class="small">05 Oct 2024–04 Oct 2026. No refit or threshold tuning.</span></div>
<div class="mini"><div class="tag">FROZEN ENTRY GATE</div><div class="value">P(high ER) ≥ 50%</div><span class="small">Entries only. Existing positions remain managed normally.</span></div></div>
'''
for window,title,start in [('3M','Last 3 months','05 July 2026'),('6M','Last 6 months','05 April 2026'),('2Y','Two-year model holdout','05 October 2024')]:
 x=results[window+'_BASE'];body+=f'<section class="panel"><div class="tag">{esc(start)} — 04 OCTOBER 2026</div><h2>{title}</h2><p>$10,000 initial balance; 1% intended equity risk per entry; USTEC / Exness. Each window starts flat. Broker spread, commission, swap and 150ms delay included. Quality: {esc(x["native"]["history_quality"])}.</p>'+table(window)+chart(window)
 body+='<p class="small">Chart: sampled five-minute floating equity, not a shared portfolio. Equity DD in the table is native MT5 relative floating-equity drawdown. MT5 Sharpe and our daily-equity annualized Sharpe use different methods and must not be interchanged. Test-end liquidation counts: '+', '.join(c+' '+str(results[window+'_'+c]['end_liquidations']) for c in ['BASE','ML','LAG'])+'.</p>'
 body+='<details><summary>Baseline trades split by the model’s forecast</summary><p class="small">Diagnostic cohorts of ORIGINAL baseline entries only. These are not the gated EA backtests above: skipping entries can free later trades and change sizing.</p><div class="scroll"><table><tr><th>Forecast</th><th>Trades</th><th>Mean net $/trade</th><th>Win rate</th><th>Net P&amp;L</th></tr>'
 for c in cohorts(window):body+='<tr>'+''.join('<td>'+v+'</td>' for v in [c['prediction'],str(c['trades']),'$'+num(c['mean_net']),num(c['win_rate'],1)+'%','$'+num(c['total_net'])])+'</tr>'
 body+='</table></div></details><details><summary>Native reports, trade ledgers and gate audit</summary><ul>'
 for case in ['BASE','ML','LAG']:
  folder='native/'+window+'_'+case+'/'
  body+='<li>'+case+': '+', '.join(f'<a href="{folder+file}">{label}</a>' for file,label in [('report.htm','native MT5 report'),('trades.csv','trade breakdown CSV'),('gates.csv','entry gate audit'),('equity.csv','sampled equity CSV')])+'</li>'
 body+='</ul></details></section>'
body+='<section class="panel"><h2>Does the model predict efficiency?</h2><p>AUC 0.50 is chance ranking. Positive Brier skill means better probability error than the training-prevalence forecast; negative is worse. No row below was used to choose a new probability threshold.</p><div class="scroll"><table><tr><th>Period</th><th>Sessions</th><th>AUC</th><th>Brier skill</th><th>ER allowed</th><th>ER skipped</th></tr>'
for name,label in [('train','Training'),('calibration_no_tuning','2024 diagnostic; no tuning'),('unseen_2y','2Y unseen'),('unseen_6m','6M unseen'),('unseen_3m','3M unseen')]:
 s=model['score'][name];body+='<tr>'+''.join('<td>'+v+'</td>' for v in [label,str(s['n']),num(s['auc'],3),num(100*s['brier_skill'],2)+'%',num(s['mean_er_allowed'],3),num(s['mean_er_blocked'],3)])+'</tr>'
body+='</table></div></section><section class="panel"><h2>What was recreated</h2><ul><li>Target: regular-session net absolute move divided by the full absolute M5 closing-price path (0–1), excluding the overnight gap.</li><li>Only complete prior sessions supply features; forecasts for holidays/short sessions still use the most recent completed prior session. No same-day session outcome enters a prediction.</li><li>Standardized logistic regression, C=1 / L2, cutoff 0.50; no selection against recent trade profits. Previous-day ER ≥ the training target median is the simple control.</li><li>Current EA: completed 09:30 NY M5 candle versus EMA12, DI14 confirmation, 0.60% price stop, no TP, ATR6 trail after +1R; overnight/weekend holding and broker minimum-lot rounding unchanged.</li><li>Adaptive BAT portfolio guards and 0.25× sizing are OFF in this single-EA comparison. The ML holdout is unseen by this MODEL, not proof that the pre-existing EA was never optimized on recent history.</li><li>Before 01 Jan 2026 this broker lacks real ticks; MT5 uses generated ticks. Recent 3M/6M runs use real ticks. No claim of two unseen years of real-tick validation.</li></ul><details><summary>The fifteen measurements and fitted standardized coefficients</summary><div class="scroll"><table><tr><th>Feature (prior complete session)</th><th>Coefficient</th></tr>'
for f,c in zip(weights['features'],weights['coef']):body+=f'<tr><td>{esc(f)}</td><td>{num(c,4)}</td></tr>'
body+='</table></div><p class="small">Coefficients are associations, not causal evidence or trade direction signals.</p></details></section>'
body+='<section class="panel"><h2>Verification and evidence</h2><p>Research gate OFF reproduces the shipped binary exactly: 43 positions, times, prices, volumes, costs, net P&amp;L and native metrics over the recent 3 months. Every instrumented deal is checked against its native MT5 report. All forecast availability times precede the relevant entry. A future-price perturbation leaves all earlier features unchanged.</p><p><a href="PROTOCOL.md">Frozen protocol</a> · <a href="MODEL.json">Model diagnostics</a> · <a href="weights.json">Frozen weights</a> · <a href="PARITY.json">Off-switch parity</a> · <a href="verification.json">Verification</a> · <a href="SUMMARY.csv">Full comparison CSV</a></p><p class="small">Method references: <a href="https://scikit-learn.org/stable/common_pitfalls.html">Scikit-learn data leakage guidance</a> and <a href="https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html">LogisticRegression</a>. Report is offline; production website was not changed.</p></section>'
body+='</main></body></html>'
(R/'Results.html').write_text(body,encoding='utf-8')
print('WROTE Results.html + SUMMARY CSV / JSON',flush=True)
