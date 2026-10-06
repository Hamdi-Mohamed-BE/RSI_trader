"""Offline pipeline evidence: raw, optimised trio, frozen candidate and rejection."""
from pathlib import Path
from datetime import datetime,timedelta
import csv,html,json,math
import numpy as np
import runner as n
R=n.R
def load(name):return json.loads((R/name).read_text())
def esc(x):return html.escape(str(x))
def f(x,d=2):return 'N/A' if x is None else f'{float(x):,.{d}f}'
def pct(x,d=1):return 'N/A' if x is None else f(x,d)+'%'
def money(x):return ('−' if x<0 else '+' if x>0 else '')+'$'+f(abs(x))
def table(head,rows):
    return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def window(r):
    a=r.get('start',r.get('manifest',{}).get('start'));b=r.get('end_exclusive',r.get('manifest',{}).get('end_exclusive'))
    return a.replace('.','-')+' → '+(datetime.strptime(b,'%Y.%m.%d')-timedelta(days=1)).strftime('%Y-%m-%d')
def meta(r):
    return r.get('manifest',r)
def rate(r):
    m=meta(r);a=datetime.strptime(m['start'],'%Y.%m.%d');b=datetime.strptime(m['end_exclusive'],'%Y.%m.%d')
    months=(b-a).days/30.4375;weekdays=len(n.pd.date_range(a,b-timedelta(days=1),freq='B'));count=r['net_metrics']['trades']
    return f(count/months)+' / month · '+f(count/weekdays,3)+' / weekday'
def statrow(label,r):
    m=r['net_metrics'];nt=r['native']
    return [label,window(r),m['trades'],rate(r),f(m['return_pct'])+'%',f(m['net_pf'],3),pct(m['win_rate_pct']),f(nt['equity_dd_pct'])+'%',f(nt['sharpe_ratio']),str(m['max_win_streak'])+' / '+str(m['max_loss_streak']),nt['history_quality']]
HEAD=['Version / window','Exact dates inclusive','Trades','Frequency','Net return','Net PF','Net WR','Native equity DD','MT5 Sharpe','Max W / L','History quality']
def graph(paths,label,start_label,end_label,dollars=True):
    allvals=[v for _,pts in paths for _,v in pts];allx=[x for _,pts in paths for x,_ in pts]
    lo=min(allvals);hi=max(allvals);pad=max(1,(hi-lo)*.08);lo-=pad;hi+=pad;xa=min(allx);xb=max(allx)
    if xb==xa:xb=xa+1
    def x(v):return 88+(v-xa)/(xb-xa)*962
    def y(v):return 20+(hi-v)/(hi-lo)*235
    svg='<svg role="img" aria-label="'+esc(label)+'" viewBox="0 0 1080 295"><title>'+esc(label)+'</title>'
    for i in range(5):
        val=lo+(hi-lo)*i/4;yy=y(val);s='$'+f(val,0) if dollars else f(val,1)+'%'
        svg+=f'<line x1="88" y1="{yy:.2f}" x2="1050" y2="{yy:.2f}" stroke="#284b3b"/><text x="4" y="{yy+4:.2f}">{s}</text>'
    for color,pts in paths:
        d=f'M{x(pts[0][0]):.2f},{y(pts[0][1]):.2f}'
        for t,v in pts[1:]:d+=f'H{x(t):.2f}V{y(v):.2f}'
        svg+=f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.4"/>'
    return svg+f'<text x="88" y="286">{esc(start_label)}</text><text x="1050" y="286" text-anchor="end">{esc(end_label)}</text></svg>'
def points(r):
    m=meta(r);a=datetime.strptime(m['start'],'%Y.%m.%d').timestamp();b=datetime.strptime(m['end_exclusive'],'%Y.%m.%d').timestamp()
    pts=[(a,10000)]+[(datetime.fromisoformat(x['time']).timestamp(),x['balance']) for x in r['ledger']]
    pts.append((b,10000+r['net_metrics']['net_profit']));return pts
def comparechart(raw,trio,final):
    return graph([('#fa909c',points(raw)),('#84f5c5',points(trio)),('#87b8ff',points(final))],'Actual native shared-account cash balances; excludes floating equity',meta(raw)['start'],'End exclusive '+meta(raw)['end_exclusive'])
def fan(m):
    q=m['fan']
    return graph([('#fa909c',list(zip(q['step'],q['p05']))),('#84f5c5',list(zip(q['step'],q['p50']))),('#87b8ff',list(zip(q['step'],q['p95'])))],'Closed-balance Monte Carlo fan: 5th, median and 95th percentiles; not a forecast','Day 0','End of resampled window')
def histogram(m):
    values=np.array(m['returns']);counts,edges=np.histogram(values,bins=24);scale=max(counts)
    svg='<svg role="img" aria-label="Monte Carlo return histogram" viewBox="0 0 1080 265"><title>Return histogram: 500 display samples from 10,000 paths</title>'
    for i,count in enumerate(counts):
        x=70+i*40;h=count/scale*190;col='#fa909c' if (edges[i]+edges[i+1])/2<0 else '#84f5c5'
        svg+=f'<rect x="{x}" y="{220-h:.1f}" width="35" height="{h:.1f}" fill="{col}"/>'
    return svg+f'<text x="70" y="252">{f(edges[0])}%</text><text x="1050" y="252" text-anchor="end">{f(edges[-1])}%</text></svg>'
def detail(r,label):
    m=r['net_metrics'];rows=[]
    for module in [1,2,3]:
        mm=r.get('module_metrics',{}).get(str(module),n.raw.metrics([t for t in r['trades'] if t['module']==module]))
        rows.append([n.raw.LABELS[module],mm['trades'],money(mm['net_profit']),pct(mm['win_rate_pct']),f(mm['net_pf'],3),str(mm['max_win_streak'])+' / '+str(mm['max_loss_streak'])])
    body='<h3>'+esc(label)+' module contributions</h3><p>One shared account, not independent module backtests. Removing a module can change sizing, overlap and the shared losing-streak brake.</p>'+table(['Module','Trades','Net contribution','Net WR','Net PF','Max W / L'],rows)
    clean=[{k:v for k,v in t.items() if not isinstance(v,(dict,list))} for t in r['trades']]
    filename=r.get('tag','')+'-positions.csv'
    if clean:
        with (R/filename).open('w',newline='',encoding='utf-8-sig') as file:
            w=csv.DictWriter(file,fieldnames=list(clean[0]));w.writeheader();w.writerows(clean)
        body+='<p><a href="'+filename+'">Download complete positions CSV</a></p>'
    body+='<details><summary>Every complete position · '+str(m['trades'])+' trades</summary>'+table(['Module','Side','Entry UTC','Exit UTC','Lots','Hours','Net P&L','Exit'],[[t['module_name'],t['side'],t['open_time'],t['close_time'],f(t['volume'],3),f(t['hold_hours']),money(t['net_profit']),t['exit_comment']] for t in r['trades']])+'</details>'
    return body
def main():
    audit=load('AUDIT.json');final=load('FINAL RESULTS.json');trio=load('OPTIMISED TRIO DIAGNOSTIC.json');frozen=load('FROZEN FINAL.json');history=load('SEARCH HISTORY.json');rows=load('SEARCH RESULTS.json')
    raw={p:json.loads((R/'native'/p/'results.json').read_text()) for p in ['5Y','3Y','1Y','6M','3M','XAG1Y']}
    # Every shown ledger must end at the independently reconciled native result.
    for r in list(final.values())+list(trio.values())+list(raw.values()):
        assert abs(sum(t['net_profit'] for t in r['trades'])-r['net_metrics']['net_profit'])<.05
    page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>UK100 full pipeline · Calyx research</title><style>
    :root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#06140e;color:#e5f3ed;font:16px/1.65 Arial,sans-serif}main{max-width:1500px;margin:auto;padding:36px 24px}h1{font-size:clamp(32px,5vw,62px);line-height:1.12;margin:20px 0}h2{font-size:26px}h3{font-size:20px}p{color:#b9d4c6}a{color:#84f5c5}.eyebrow{font:12px monospace;letter-spacing:2px;color:#84f5c5}.card{background:#0b2117;border:1px solid #284b3b;border-radius:18px;padding:24px;margin:24px 0}.warning{border-color:#88783b;background:#252b13;color:#ffe49a}.rejected{color:#fa909c}.scroll{max-width:100%;overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;padding:12px;border-bottom:1px solid #284b3b;white-space:nowrap}th{color:#84f5c5;background:#153525}.grid{display:grid;grid-template-columns:1fr 1fr;gap:22px;min-width:0}.grid>div{min-width:0}svg{display:block;width:100%;height:auto}svg text{fill:#b9d4c6;font:13px Arial}summary{cursor:pointer;color:#84f5c5;padding:14px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}.small{font-size:13px}.pill{display:inline-block;border:1px solid #284b3b;padding:5px 12px;border-radius:30px;font:12px monospace}.pass{color:#84f5c5}.fail{color:#fa909c}nav{display:flex;gap:20px;flex-wrap:wrap}details{margin:12px 0} @media(max-width:760px){main{padding:22px 14px}.card{padding:18px}.grid{grid-template-columns:1fr}h2{font-size:23px}}
    </style></head><body><main><div class="eyebrow">CALYX · IDEA 03 · FULL RESEARCH PIPELINE · EXPLORATORY</div><h1>UK100.<br>Optimised, but not validated.</h1><span class="pill rejected">REJECT · NO DEPLOYMENT</span><p>Native Exness UK100 CFD simulations on one shared $10,000 account. Planned risk is 1% of current equity per entry; risk can stack across modules. Broker costs, native lot limits and 150 ms execution delay included.</p><div class="card warning">Independent prototype inspired by QuantLab’s public three-module concept—not its proprietary rules or a verified reproduction. Raw long-history gates failed; exploratory optimisation continued at your explicit instruction. The latest year/quarter were already viewed and are NOT untouched holdouts.</div><nav><a href="#comparison">Comparisons</a><a href="#rules">Frozen settings</a><a href="#search">Full search</a><a href="#validation">Validation</a><a href="#mc">Monte Carlo</a><a href="#risk">Risk & silver</a><a href="#evidence">Evidence</a></nav>'''
    page+='<section class="card" id="comparison"><h2>Raw versus optimised · exact native shared accounts</h2><p>Red: raw H1 trio. Green: optimised H4 trio retaining all three modules. Blue: frozen validation-selected H4 candidate with drop recovery disabled. Each window starts fresh and flat; these are native accounts, not added independent ledgers.</p>'
    stats=[]
    for phase in ['5Y','3Y','1Y','6M','3M']:
        for label,r in [('Raw '+phase,raw[phase]),('Optimised trio '+phase,trio[phase]),('Frozen reduced '+phase,final[phase])]:stats.append(statrow(label,r))
    page+=table(HEAD,stats)
    page+='<p>The annual trio improves PF and drawdown but earns only 1.45% from 14 trades. Its recent quarter loses 0.45%. The frozen reduced candidate earns just$5.87 across 11 annual trades and fails its earlier reserve. Low drawdown is partly a result of very low activity and wide stops—not evidence of a profitable edge.</p><div class="grid"><div><h3>Five-year actual closed balance</h3>'+comparechart(raw['5Y'],trio['5Y'],final['5Y'])+'</div><div><h3>Latest-year actual closed balance</h3>'+comparechart(raw['1Y'],trio['1Y'],final['1Y'])+'</div></div><p class="small">Graphs show actual deal-timed closed balances including entry charges. Floating equity is not drawn; the table reports native MT5 equity drawdown separately. Model 4 requests real ticks where available; older history is mostly generated ticks. Native MT5 Sharpe is reproduced, not an independently annualised daily Sharpe.</p>'+detail(trio['1Y'],'Optimised trio · latest year')+detail(final['1Y'],'Frozen reduced candidate · latest year')+'</section>'
    page+='<section class="card" id="rules"><h2>Frozen research settings · not installed</h2>'+table(['Component','Setting'],[
        ['Signal timeframe','H4; completed candles only'],
        ['Modules','Monday dip + long trend pullback; drop module disabled in the validation-selected version. Trio alternative retains drop.'],
        ['Entry','Arm a buy after the closed signal; enter when executable quote retests signal close −0.5× signal ATR14. Expire after 6 clock hours, day change, pause or outside entry session.'],
        ['Monday signal','Monday only; prior completed close ≤ last completed broker-Friday D1 close −0.5× prior ATR; bullish signal closes above prior high.'],
        ['Trend signal','EMA50 > EMA200 and EMA50 rising; previous close ≤ prior EMA20, signal bullish and closes above its completed EMA20.'],
        ['Stop / target','Initial stop 4× signal ATR14; target2R for frozen reduced candidate. Trio alternative uses the preregistered development-selected targets.'],
        ['ATR trail','Starts at +1R; follows executable quote by 1× latest completed signal-timeframe ATR14. Stop moves only favourably, respecting broker restrictions.'],
        ['Time exit','48 clock hours, next broker-permitted tick; can extend through market closures.'],
        ['Session / days','08:00–16:00 London, DST-aware; no Friday entries. Exits still active on Friday.'],
        ['ADX / DI','None selected. Tested strength15/20/25/30, DI and combinations; did not improve the registered development shortlist with adequate count.'],
        ['Risk / limits','1% equity per entry, lots rounded down; max3 shared slots, one position and one new entry per module/day. Only two modules enabled in the frozen version.'],
        ['Losing-streak defence','Three complete net losing positions pause new entries 24 hours; existing positions keep exits.'],
        ['Minimum lot','Skip if broker minimum lot cannot fit budget. Never force higher risk.'],
        ['Sizing caution','The 1% is planned stop cash, not a guarantee after gaps, fees or changing conversion prices.']])
    page+='<details><summary>Exact frozen input values</summary><pre>'+esc(json.dumps(frozen['inputs'],indent=2))+'</pre></details><p><a href="FINAL RESEARCH ONLY.set">Research-only SET</a> · <a href="EA/Calyx UK100 Pipeline Research.mq5">Tester-only source</a></p></section>'
    page+='<section class="card" id="search"><h2>Full staged development search</h2><p>'+str(audit['development_search_configurations'])+' recorded development setting combinations; '+str(audit['unique_configurations'])+' including controls/risk variants used for the multiple-testing penalty. Counts are conservative: inactive and numerically equivalent setting records are not treated as independent evidence. Screening is native Model 1 OHLC; finalists use native Model 4 confirmations. No recent or reserve results selected the preset.</p>'+table(['Stage','Cases in stage','Best screen PF','Return','Trades','Equity DD'],[[h['stage'],h['cases'],f(h['selected'][0]['net_metrics']['net_pf'],3),f(h['selected'][0]['net_metrics']['return_pct'])+'%',h['selected'][0]['net_metrics']['trades'],f(h['selected'][0]['equity_dd_pct'])+'%'] for h in history])
    page+='<p>Search included M1/M3/M5/M15/M30/H1/H4/D1; next-open, confirmation, retest and breakout entries; signal thresholds; ATR, signal/swing, price-percent and fixed-price stops; static, breakeven, ATR/percent/MA/swing/chandelier/dynamic 50–20 management; fixed 0.5–6R, no target+trail, time/session and partial exits; sessions/weekdays; direction; ADX/DI, HTF, volatility/spread filters; holding limits, slots, entries/day, loss pauses and module subsets. No point-in-time news blackout data was supplied, so none was invented.</p>'
    page+='<details><summary>Every inspected development configuration · '+str(len(rows))+' records</summary>'+table(['ID','Stage','Frame','Entry','Stop','Manage','Exit','TP R','Session','Direction','Filter','Modules','Trades','Return','PF','WR','Native DD'],[[r['id'],r['stage'],n.FRAMES[int(r['inputs']['InpSignalTimeframe'])],r['inputs']['InpEntryMode'],r['inputs']['InpStopMode'],r['inputs']['InpManagement'],r['inputs']['InpExitMode'],r['inputs']['InpTrendTargetR'],r['inputs']['InpSessionMode'],r['inputs']['InpDirection'],r['inputs']['InpFilter'],''.join(str(i+1) for i,k in enumerate(['InpEnableDrop','InpEnableMonday','InpEnableTrend']) if r['inputs'][k]=='true'),r['net_metrics']['trades'],f(r['net_metrics']['return_pct'])+'%',f(r['net_metrics']['net_pf'],3),pct(r['net_metrics']['win_rate_pct']),f(r['export_stats']['equity_dd_pct'])+'%'] for r in rows])+'</details><p><a href="SEARCH PLAN.json">Preregistered search choices</a> · <a href="SEARCH RESULTS.json">All results and complete-position ledgers</a> · <a href="FINALISTS.json">Neighbour plateau counts</a></p></section>'
    page+='<section class="card" id="validation"><h2>Native validation and earlier reserve</h2>'
    validation=load('VALIDATION RESULTS.json')
    page+=table(HEAD,[statrow('Selected development',next(v['development'] for v in validation if v['id']==frozen['id'])),statrow('Selected validation',next(v['validation'] for v in validation if v['id']==frozen['id'])),statrow('Earlier reserved test',final['HOLD'])])
    page+='<p>All three native validation finalists returned the same $52.67 across 11 positions. The tie selected the lower-R reduced candidate before inspecting recent or reserve results. Validation sample is below 30. The earlier reserved period 2019-10-04–2021-09-26 lost 3.31%, PF 0.454, from 18 positions; it has 0% real ticks and therefore cannot establish a high-quality independent holdout. No retuning followed.</p>'+graph([('#84f5c5',points(final['HOLD']))],'Earlier reserve actual cash balance','2019-10-04','2021-09-27 exclusive')
    page+='<h3>Calendar-year contributions inside the five-year frozen account</h3><p>2021 and 2026 are partial years. These are chronological diagnostic slices, not fresh yearly tests or nested walk-forward validation.</p>'+table(['Year','Trades','Net contribution','PF','WR','Max W / L'],[[x['year'],x['trades'],money(x['net_profit']),f(x['net_pf'],3),pct(x['win_rate_pct']),str(x['max_win_streak'])+' / '+str(x['max_loss_streak'])] for x in audit['calendar_years']])
    page+='<h3>Signal-free controls · validation</h3><p>Three preregistered random seeds, same chosen session, exits, sizing, slot and loss-pause rules. Frequencies are approximate, not exactly matched; samples are tiny. No statistical superiority is established.</p>'+table(HEAD,[statrow('Random seed '+r['inputs']['InpControlSeed'],r) for r in load('CONTROLS.json')])+'</section>'
    page+='<section class="card" id="mc"><h2>Monte Carlo · 10,000 paths, not payout forecasts</h2><p>Five-day closed-balance blocks preserve some temporal clustering; the common audit also bootstraps complete-position PF in five-position blocks. Floating equity, future margin, dynamic lot rounding and the actual broker execution path are NOT re-simulated. A low closed-P&L breach rate cannot certify FTMO compliance.</p>'
    mcs=[('Frozen · reserve',audit['monte_carlo']['HOLD']),('Frozen · latest year',audit['monte_carlo']['1Y']),('Frozen · quarter',audit['monte_carlo']['3M']),('Trio · latest year',audit['optimised_trio_monte_carlo'])]
    page+=table(['Sample','Profit probability','Return P05','Median','Return P95','Closed DD median','Closed DD P95'],[[name,f(m['probability_profit_pct'],1)+'%',f(m['return_p05_pct'])+'%',f(m['return_median_pct'])+'%',f(m['return_p95_pct'])+'%',f(m['max_closed_dd_median_pct'])+'%',f(m['max_closed_dd_p95_pct'])+'%'] for name,m in mcs])
    page+='<div class="grid"><div><h3>Frozen annual closed-balance fan</h3><p>Red P05 · green median · blue P95.</p>'+fan(audit['monte_carlo']['1Y'])+'</div><div><h3>Annual return distribution</h3><p>500 display samples; statistics above use all 10,000 paths.</p>'+histogram(audit['monte_carlo']['1Y'])+'</div></div>'
    common=audit['common_audits']['1Y'];cm=common['metrics'];mc=audit['monte_carlo']['1Y']
    page+=table(['Annual uncertainty / stress','Measured result'],[['Win-rate95% Wilson interval',' – '.join(f(v,1)+'%' for v in cm['win_rate_wilson_95_pct'])],['Annualised closed-balance daily Sharpe',f(cm['annualized_sharpe'])],['Deflated Sharpe probability',f(cm['deflated_sharpe_pct'],2)+'%'],['Five-position bootstrap PF P05',f(common['bootstrap']['profit_factor_p05'],3)],['Trade-order shuffle closed DD P95',f(mc['shuffle_dd_p95_pct'])+'%'],['Shuffle losing streak P95',f(mc['shuffle_loss_streak_p95'],0)],['Measured extra execution-cost sensitivity','$'+f(audit['measured_cost_stress']['extra_usd_per_position'],3)+' per complete position'],['Annual after that extra cost',money(common['cost_stress']['net_profit'])+' · PF '+f(common['cost_stress']['profit_factor'],3)]])
    page+='<p>Extra cost is another copy of the observed P95 cash difference between pre-order quote and delayed fill—not a guessed spread. Independent wider-spread/commission stress remains missing.</p>'+table(['Missed entries','Profit probability','Return P05','Median'],[[str(x['skip_pct'])+'%',f(x['probability_profit_pct'],1)+'%',f(x['return_p05_pct'])+'%',f(x['return_median_pct'])+'%'] for x in mc['missed_trades']])+'</section>'
    page+='<section class="card" id="risk"><h2>Risk variants and mandatory silver transfer</h2><p>Frozen signals unchanged. These are separate native annual runs, not linearly scaled returns. Risk choices were not used to create or select an edge.</p>'+table(HEAD,[statrow('Risk '+r['inputs']['InpRiskPercent']+'%',r) for r in load('RISK COMPARISON.json')])+table(HEAD,[statrow('XAG raw frozen logic',raw['XAG1Y']),statrow('XAG selected frozen preset',final['XAG1Y'])])
    page+='<p>Silver raw lost 17.85%. The selected wide-stop preset generated no fills: four minimum-lot risk skips. This is a genuine frozen portability failure/insufficient exposure at $10k, not a profitable 0% result. The code did not exceed selected risk to force a trade.</p>'+graph([('#fa909c',points(raw['XAG1Y'])),('#87b8ff',points(final['XAG1Y']))],'Silver transfer actual balances: raw versus no-fill wide-stop preset','2025-10-04','2026-10-04 exclusive')+'</section>'
    page+='<section class="card" id="evidence"><h2>Pipeline gates and what was deliberately not promoted</h2>'+table(['Gate','Result'],[[key,'PASS' if value else 'FAIL / INCOMPLETE'] for key,value in audit['gates'].items()])+table(['Deferred stage','Reason'],list(audit['deferred'].items()))
    page+='<p>Completed: unchanged raw 6m/1y/3y/5y evidence, silver transfer, full staged exploratory search, neighbours, native development/validation, one frozen earlier reserve, viewed recent diagnostics, controls, native risk comparisons, complete-cost/position-ID reconciliation and Monte Carlo. The prerequisite failures stop forward-test certification, FTMO pass/payout modelling, portfolio promotion and production changes.</p><p><a href="PLAN.txt">Pipeline plan</a> · <a href="VALIDATION PLAN.json">Validation freeze</a> · <a href="FROZEN FINAL.json">Frozen choice</a> · <a href="AUDIT.json">Audit and simulation evidence</a> · <a href="FINAL SUMMARY.csv">Summary CSV including XAG</a> · <a href="../Results.html">Previous raw report</a></p><p>Public concept: <a href="https://api-quantlab.com/algorithmen/uk100-premium">QuantLab UK100 three-module description</a>. All numerical thresholds are ours. Live MT5, BATs, website and Git remotes were not changed. This report does not evaluate QuantLab’s private executable.</p></section></main></body></html>'
    (R/'Results.html').write_text(page,encoding='utf-8')
    print('Offline report built: raw/trio/frozen comparisons, native ledgers, full search, reserve, Monte Carlo, controls, risk and silver.')
if __name__=='__main__':main()
