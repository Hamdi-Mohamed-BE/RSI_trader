"""Offline full pipeline report; never modifies production evidence."""
from pathlib import Path
from datetime import datetime,timezone
import csv,gzip,html,json,math,shutil
import search as n
R=n.ROOT
def esc(x):return html.escape(str(x))
def num(x,d=2):return 'N/A' if x is None else f'{x:,.{d}f}'
def pct(x):return 'N/A' if x is None else f'{x:+.2f}%'

def rate(x,d=1):return 'N/A' if x is None else f'{x:,.{d}f}%'
def table(head,rows,css=''):
    def line(x,tag):return '<tr>'+''.join(f'<{tag}>{esc(v)}</{tag}>' for v in x)+'</tr>'
    return '<div class="scroll"><table class="'+esc(css)+'"><thead>'+line(head,'th')+'</thead><tbody>'+''.join(line(x,'td') for x in rows)+'</tbody></table></div>'
def graph(title,series,caption,start,end):
 W=1100;H=300;L=84;T=22;B=34;RR=22
 vs=[v for _,p,_ in series for _,v in p]+[10000];lo=min(vs);hi=max(vs);pad=max(20,(hi-lo)*.08);lo-=pad;hi+=pad
 first=datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp();last=datetime.fromisoformat(end).replace(tzinfo=timezone.utc).timestamp()
 def x(t):return L+(t-first)/(last-first)*(W-L-RR)
 def y(v):return T+(hi-v)/(hi-lo)*(H-T-B)
 svg=f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(title)}">'
 for i in range(5):
  v=lo+(hi-lo)*i/4;yy=y(v);svg+=f'<line x1="{L}" y1="{yy:.1f}" x2="{W-RR}" y2="{yy:.1f}" stroke="#294337"/><text x="{L-9}" y="{yy+4:.1f}" text-anchor="end">USD {v:,.0f}</text>'
 for label,p,color in series:
  if len(p)>1300:p=p[::max(1,len(p)//1250)]+[p[-1]]
  points=[(first,10000)]+p
  if 'cash' in label.lower():
   stepped=[points[0]]
   for t,v in points[1:]:stepped.extend([(t,stepped[-1][1]),(t,v)])
   stepped.append((last,stepped[-1][1]));points=stepped
  coords=' '.join(f'{x(t):.2f},{y(v):.2f}' for t,v in points)
  svg+=f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2.2"/>'
 svg+=f'<text x="{L}" y="{H-5}">{esc(start)}</text><text x="{W-RR}" y="{H-5}" text-anchor="end">{esc(end)} exclusive</text></svg>'
 keys=' '.join(f'<span style="color:{c}">● {esc(label)}</span>' for label,_,c in series)
 return f'<section class="panel graph"><h2>{esc(title)}</h2><p>{esc(caption)}</p>{svg}<div class="legend">{keys}</div></section>'
STYLE="*{box-sizing:border-box}body{margin:0;background:#07110e;color:#eafff5;font:16px/1.6 \"Segoe UI\",Arial,sans-serif}main{max-width:1350px;margin:auto;padding:50px 28px}h1{font-size:clamp(34px,5vw,60px);line-height:1.12;letter-spacing:-1.5px}h2{font-size:24px;line-height:1.25;margin:0 0 15px}h3{margin:4px 0 10px}.kicker{color:#8dffd4;font-size:12px;letter-spacing:2px}p{color:#adc4ba}.panel{margin:22px 0;padding:25px;border:1px solid #294337;border-radius:18px;background:#0c1a15}.alert{background:#242310;border-color:#716b28;color:#ffeb9a}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.card{padding:20px;border:1px solid #294337;border-radius:14px;background:#0d1c17}.card strong{display:block;font-size:28px;color:#8dffd4}.scroll{max-width:100%;overflow-x:auto}table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums;font-size:13px;white-space:nowrap}th,td{padding:12px 10px;text-align:right;border-bottom:1px solid #294337}th:first-child,td:first-child{text-align:left}th{color:#8dffd4;font-size:11px;text-transform:uppercase}td{color:#d1e7dc}svg{display:block;width:100%;height:auto}svg text{fill:#adc4ba;font:12px \"Segoe UI\",Arial}.legend{display:flex;gap:22px;flex-wrap:wrap;font-size:13px}a{color:#8dffd4}details{margin:15px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;color:#adc4ba;font-size:13px}@media(max-width:750px){main{padding:26px 14px}.panel{padding:16px}.grid{grid-template-columns:1fr}h1{letter-spacing:-.6px}.legend{gap:8px}th,td{padding:9px 8px}}.card{min-width:0;overflow-wrap:anywhere}.grid{grid-template-columns:repeat(3,minmax(0,1fr))}@media(max-width:750px){.grid{grid-template-columns:minmax(0,1fr)}}"

STYLE += 'p,a,h2,.kicker{overflow-wrap:anywhere}.panel{min-width:0}.rules{table-layout:fixed;white-space:normal}.rules th,.rules td{text-align:left;vertical-align:top;overflow-wrap:anywhere}.rules th:first-child{width:18%}@media(max-width:750px){.rules{min-width:720px}}'


def main():
    a=n.load(R/'AUDIT.json');f=a['frozen'];ex=a['exact'];raw=n.load(n.RAW/'summary.json')['results'];trials=n.load(R/'SEARCH RESULTS.json')
    frozen=R/'Frozen';frozen.mkdir(exist_ok=True);folder=n.OUT/'final-1Y'
    for name,dest in [('GoldSpeedSearch.ex5','Gold Speed Research.ex5'),('GoldSpeedSearch.mq5','Gold Speed Research.mq5'),('Logic.mqh','Logic.mqh')]:shutil.copy2(folder/name,frozen/dest)
    vals=dict(InpCase=f['slots'][0],InpCase2=f['slots'][1] if len(f['slots'])>1 else -1,InpCase3=f['slots'][2] if len(f['slots'])>2 else -1,InpControl='false',InpRetryClosed='false',InpRiskPercent=1,InpSeed=20261005,InpTradeFrom='2021.10.05 00:00:00',InpTag='FROZEN-RESEARCH',InpMagic=1005040)
    (frozen/'Frozen Research.set').write_text('\n'.join(f'{k}={v}' for k,v in vals.items())+'\n',encoding='utf-8')
    body=f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Gold04 full research pipeline</title><style>{STYLE}</style></head><body><main><div class="kicker">CALYX · QUANTLAB IDEA 04 · 5 OCT 2026 · TESTER ONLY</div><h1>Gold. Fully examined.<br>A frozen research finalist.</h1><p>Speed momentum / seasonal breakout / month-turn. Public-idea reconstruction; all numerical rules ours.</p><section class="panel alert"><h2>{esc(a["verdict"].replace("_"," "))}</h2><p>“Best examined” is not “proven profitable”. No production, BAT, website, Git or live account change. Earlier confirmation has research-family reuse; recent windows were already viewed.</p></section>'
    body+='<p>Selection: '+esc(f.get('selected_variant','TUNED').replace('_',' '))+'. This refers to the Gold04 study, not the current deployed 3 Way Gold. Retaining the raw Gold04 model is not approval to deploy it.</p>'
    s=ex['1Y']['stats'];body+='<div class="grid">'+''.join(f'<div class="card">{esc(k)}<strong>{esc(v)}</strong>{esc(note)}</div>' for k,v,note in [('Last-year return',pct(s['return_pct']),str(s['trades'])+' complete net-cost positions'),('PF / win rate',num(s['pf'])+' / '+num(s['win_pct'],1)+'%',str(s['max_win_streak'])+' max win streak'),('Native equity DD',num(ex['1Y']['native']['equity_dd_pct'])+'%',str(a['trial_accounting']['total_native_passes'])+' native passes counted')])+'</div>'
    current_source=n.BASE/'3 Way Gold EA/3 Way Gold EA.mq5'
    current_set=n.BASE/'Selected Portfolio Settings 2026-09-01/25 3 Way Gold - BEST OPTIMISED - 1PCT PER MODULE.set'
    comparison=[
      ['Momentum','H4; fixed 24 bars; EMA50 slope + EMA200 bias; no Monday. 3 ATR stop.','H4; adaptive 6/24 bars based on volatility; EMA100 slope. 2.5 ATR stop.'],
      ['Breakout','M15; all months; 60-bar break at outer 10% of 960-bar range; UTC12–16; spread cap; 4 ATR stop.','H1; October–December only; 60-bar break at outer 10% of 480-bar range; 2 ATR stop.'],
      ['Month-turn','Last weekday to next-month weekday +2; no Monday; 2 D1 ATR stop; TP2.5R; BE from0.5R.','Same weekday schedule; 2 D1 ATR stop; no TP or breakeven.'],
      ['Entry / management','A/B pullback limits0.5 ATR; take50% at1R if legal lots permit; ATR trails: A1 ATR from0.5R, B1.5 ATR from1R.','A/B next-bar market entries; no partials; initial-stop-distance trails from1R.'],
      ['Sizing','Selected normal preset1% equity per module; broker step/minimum rounds UP, potentially exceeding cash risk.','1% equity per entry; floor lots and skip if minimum lot exceeds budget.']
    ]
    body+='<section class="panel"><h2>How this differs from current 3 Way Gold</h2><p>Same broad momentum + breakout + month-turn architecture, not three unrelated new edges. Current means the selected normal BAT preset and source on disk, not verified active chart inputs. FTMO market-entry wrapper is a separate variant.</p>'+table(['Component','Current selected 3 Way Gold','Gold04 raw / retained finalist'],comparison,css='rules')+'<p>No matched current-3-Way versus Gold04 head-to-head test was requested or run here. Return differences cannot establish superiority when sizing and entry conventions differ. Source SHA256: '+esc(n.sha(current_source))+'; selected SET SHA256: '+esc(n.sha(current_set))+'.</p></section>'
    head=['Window / dates excl.','Version','Trades','/month','/weekday','Return','Net PF','WR','Native EQDD','Native Sharpe','Max W/L','Tick quality']
    rows=[]
    for k in ['5Y','3Y','1Y','6M','3M']:
      rr=raw[k];m=rr['metrics'];nn=rr['native'];r=ex[k];ss=r['stats'];nn2=r['native']
      label=k+' '+r['start'].replace('.','-')+' → '+r['end_exclusive'].replace('.','-')
      rows.append([label,'Raw',m['trades'],num(m['trades_per_month']),num(m['trades_per_weekday'],3),pct(m['return_pct']),num(m['net_pf']),num(m['win_rate_pct'],1)+'%',num(nn['equity_dd_pct'])+'%',num(nn['sharpe_ratio']),str(m['max_win_streak'])+'/'+str(m['max_loss_streak']),nn['history_quality']])
      rows.append([label,'Frozen',ss['trades'],num(ss['trades_per_month']),num(ss['trades_per_day'],3),pct(ss['return_pct']),num(ss['pf']),num(ss['win_pct'],1)+'%',num(nn2['equity_dd_pct'])+'%',num(nn2['sharpe_ratio']),str(ss['max_win_streak'])+'/'+str(ss['max_loss_streak']),nn2['history_quality']])
    body+='<section class="panel"><h2>Raw versus frozen — shared native account</h2><p>Each test starts flat with one shared $10,000 balance, concurrent module margin and 1% equity risk per entry. Broker costs and 150ms delay. The original raw receipts precede a small broker-history update: parity replay matched all188 positions; original three-year forced boundary cash changed by '+num(n.load(R/'PARITY.json')['boundary_data_update_usd'])+' USD. Cross-window differences are not a continuous live account.</p>'+table(head,rows)+'<p>Native equity DD includes floating positions; plotted five-minute samples can miss intrabar extremes. Native Sharpe is not the independent annualised daily deal-cash Sharpe. Before2026 real ticks unavailable/generated.</p></section>'
    def cash(k):return [(d['epoch'],d['balance']) for d in ex[k]['ledger']]
    def equity(k):return [(d['time'],d['equity']) for d in ex[k]['equity_sample']]
    def rawcash(k):return [(d['epoch'],d['balance']) for d in n.load(n.RAW/'native'/k/'results.json')['ledger']]
    for k in ['5Y','1Y','3M']:
      r=ex[k];body+=graph(k+' — shared-account balance and floating samples',[('Frozen actual cash',cash(k),'#8dffd4'),('Frozen sampled equity',equity(k),'#88acff'),('Raw actual cash',rawcash(k),'#e5b3f5')],'Raw is an independent test, not an additional investment. Drawdowns in the tables use native tick statistics.',r['start'].replace('.','-'),r['end_exclusive'].replace('.','-'))
    phead=['Phase','Dates excl.','Trades','Return','PF','WR','EQDD','Annualised deal-cash Sharpe','DSR %','/month','Max W/L']
    body+='<section class="panel"><h2>Chronological selection and reserved confirmation</h2>'+table(phead,[[k,ex[k]['start']+' → '+ex[k]['end_exclusive'],ex[k]['stats']['trades'],pct(ex[k]['stats']['return_pct']),num(ex[k]['stats']['pf']),num(ex[k]['stats']['win_pct'])+'%',num(ex[k]['native']['equity_dd_pct'])+'%',num(a['common_audits'][k]['metrics']['annualized_sharpe']),num(a['common_audits'][k]['metrics']['deflated_sharpe_pct']),num(ex[k]['stats']['trades_per_month']),str(ex[k]['stats']['max_win_streak'])+'/'+str(ex[k]['stats']['max_loss_streak'])] for k in ['DEV','VAL','HOLD']])+'<p>DEV fast Model1 screens; table is frozen native Model4 reconfirmation. Validation selects module combination, not recent history. Earlier HOLD unused for this exact model, but related research used the era: not pristine globally untouched OOS. Latest-year/quarter diagnostics already seen.</p></section>'
    r=ex['HOLD'];body+=graph('Reserved earlier confirmation — one frozen version',[('Actual cash',cash('HOLD'),'#8dffd4'),('Sampled equity',equity('HOLD'),'#88acff')],'No retuning after this result.',r['start'].replace('.','-'),r['end_exclusive'].replace('.','-'))
    body+='<section class="panel"><h2>Frozen rules and module selection</h2><p>Selected modules: '+esc(' + '.join('ABC'[int(f['cases'][i]['module'])] for i in f['slots']))+'. Missing modules are not deployed/added. Timing remains broker UTC; NY session uses actual US DST.</p>'+table(['Module','TF minutes','Entry','Stop type / size','RR','Trail / start / dist','Session','Side','Filter / ADX','Logic p1/p2/p3/p4','Fast/speed/ATRmean'],[[m,p['tf'],p['entry'],str(p['stop'])+' / '+str(p['sl']),p['rr'],str(p['trail'])+' / '+str(p['start'])+' / '+str(p['dist']),p['session'],p['direction'],str(p['filter'])+' / '+str(p['adx']),'/'.join(str(p[k]) for k in ['p1','p2','p3','p4']),'/'.join(str(p[k]) for k in ['fast','speed','volavg'])] for m,p in [(('Tuned ' if i<3 else 'Raw ')+ 'ABC'[int(p['module'])],p) for i,p in enumerate(f['cases'])]])+'<details><summary>Parameter dictionary and exact settings</summary><p>Entry0=first next-bar market quote,1=next candle confirmation,2=ATR-offset limit,3=ATR-offset stop. Stops0=ATR,1=price%,2=5-bar swing,3=20-bar structure,4=fixed USD price distance,5=signal candle. Trail0=none,1=BE,2=initial distance,3=ATR,4=price%,5=EMA20,6=5-bar swing,7=20-bar chandelier,8=50–20 step. Filter0=none,1=EMA200,2=H4EMA50,3=ADX,4=ATRpercentile20–80,5=spread<=.1ATR,6=D1EMA50,7=DI,8=ADX+DI. Session0=all,1=AsiaUTC00–08,2=LondonUTC07–16,3=NY09:30–16,4=UTC12–16 overlap,5=NY09:30–11. Side0=both,1=long,2=short. No indicator is future-looking. Calendar month-turn excludes nonsensical directional-breakout variants. Our universe is bounded and staged, not a global exhaustive optimum.</p><pre>'+esc(json.dumps(f['cases'],indent=2))+'</pre></details><p><a href="Frozen/Frozen Research.set">Frozen research SET</a> · <a href="Frozen/Gold Speed Research.ex5">Tester-only compiled EA</a> · <a href="PROTOCOL.md">Preregistered research protocol</a> · <a href="FROZEN FINAL.json">Frozen decision receipt</a></p></section>'
    comb=[]
    for cc in f['combinations']:
      ss=cc['result']['stats'];comb.append(['+'.join('ABC'[int(f['cases'][i]['module'])] for i in cc['slots']),ss['trades'],pct(ss['return_pct']),num(ss['pf']),num(ss['win_pct'])+'%',num(cc['result']['net']['equity_dd_pct'])+'%',cc['qualified'],'SELECTED' if cc['slots']==f['slots'] else 'Not selected'])
    body+='<section class="panel"><h2>Shared module combinations — validation only</h2>'+table(['Modules','Trades','Return','PF','WR','EQDD','All prerequisites','Decision'],comb)+'</section>'
    mcrows=[]
    for k,mc in a['monte_carlo'].items():
      ca=a['common_audits'][k];boot=ca['bootstrap'];ci=ca['metrics']['win_rate_wilson_95_pct'];mcrows.append([k,mc.get('paths'),num(mc.get('trade_block_profit_probability_pct'))+'%',pct(mc.get('trade_block_return_p05_pct')),num(mc.get('trade_block_pf_p05')),num(mc.get('shuffle_closed_dd_p95_pct'))+'%',num(mc.get('daily_block_closed_dd_p95_pct'))+'%',num(ca['metrics']['deflated_sharpe_pct'])+'%',num(ci[0],1)+'–'+num(ci[1],1)+'%',ca['verdict']])
    body+='<section class="panel"><h2>Monte Carlo — 10,000 paths per window</h2>'+table(['Window','Paths','Five-trade Pprofit','ReturnP05','PFP05','ShuffleDDP95','Five-dayDDP95','DSR','Win-rate Wilson95%','Locked common verdict'],mcrows)+'<p>Trade-block PF/returns use cash outcomes; daily blocks preserve deal cash timing, including entry fees. These paths do not recreate margin, gaps, floating equity or risk-sized future orders. Shuffles cannot change total profit; they test sequencing risk only. DSR penalises all searched passes; probability is a model diagnostic, not a forecast. Wilson intervals assume independent binary outcomes; serial dependence can make them too narrow.</p>'+table(['Window','Missed %','Profit probability','ReturnP05','Median return'],[[k,r['skip_pct'],num(r['profit_probability_pct'])+'%',pct(r['return_p05_pct']),pct(r['median_return_pct'])] for k,mc in a['monte_carlo'].items() for r in mc.get('missed_trades',[])])+'</section>'
    fan=a['monte_carlo']['1Y'].get('fan')
    if fan:
      first=datetime.fromisoformat(ex['1Y']['start'].replace('.','-')).replace(tzinfo=timezone.utc).timestamp();series=[]
      for key,color in [('p05','#ff9999'),('p50','#8dffd4'),('p95','#88acff')]:series.append((key,[(first+i*86400,v) for i,v in enumerate(fan[key])],color))
      body+=graph('Last-year empirical daily block range',series,'Daily closed-cash resampling only. Not projected future equity or payout.',ex['1Y']['start'].replace('.','-'),ex['1Y']['end_exclusive'].replace('.','-'))
    body+='<section class="panel"><h2>Locked gates and deferred work</h2>'+table(['Gate','Outcome'],[[k,'PASS' if v else 'FAIL / missing'] for k,v in a['gates'].items()])+'<p>'+esc(json.dumps(a['measured_cost_stress']))+'</p>'+''.join('<p><strong>'+esc(k)+':</strong> '+esc(v)+'</p>' for k,v in a['deferred'].items())+'</section>'
    risks=[r for r in a['other'] if r['tag'].startswith('risk-')];silver=a['other'][-1]
    def rrow(r):
      s=r['stats'];return [r['symbol'],r['risk_pct'],s['trades'],pct(s['return_pct']),num(s['pf']),rate(s['win_pct']),num(r['native']['equity_dd_pct'])+'%',r['minlot_skips'],r['native']['history_quality']]
    body+='<section class="panel"><h2>Risk sensitivity and frozen silver transfer — latest year</h2><p>Risk does not select an edge. Each native account starts at $10,000; minimum-lot skips can produce nonlinear results.</p>'+table(['Symbol','Risk%','Trades','Return','PF','WR','EQDD','Min-lot skips','Quality'],[rrow(r) for r in risks]+[rrow(silver)])+'</section>'
    modules=[r for r in a['other'] if r['tag'].startswith('module-')]
    body+='<section class="panel"><h2>Each selected module alone — latest year</h2><p>Separate native $10,000 accounts at1% risk, not contributions to the shared account and not added together. Month-turn has no latest-year positions because legal minimum lots exceed the risk budget.</p>'+table(['Module test','Trades','Return','PF','WR','Native EQDD','Max W/L','Min-lot skips'],[[r['tag'],r['stats']['trades'],pct(r['stats']['return_pct']),num(r['stats']['pf']),num(r['stats']['win_pct'])+'%',num(r['native']['equity_dd_pct'])+'%',str(r['stats']['max_win_streak'])+'/'+str(r['stats']['max_loss_streak']),r['minlot_skips']] for r in modules])+'</section>'
    for r in modules:
      body+=graph(r['tag']+' — standalone account',[('Actual cash',[(d['epoch'],d['balance']) for d in r['ledger']],'#8dffd4'),('Sampled equity',[(d['time'],d['equity']) for d in r['equity_sample']],'#88acff')],'Independent module account. Not an overlay or additional portfolio result.',r['start'].replace('.','-'),r['end_exclusive'].replace('.','-'))
    controls=[r for r in a['other'] if r['tag'].startswith('control-')]
    body+='<section class="panel"><h2>Seeded direction / calendar controls</h2><p>One fixed diagnostic control per window, not a random-control distribution or proof of statistical superiority. A/B use seeded direction randomisation; C shifts its calendar entry to weekday10 with a corresponding weekday exit. Concurrent exposure and minimum-lot skips can change trade counts.</p>'+table(['Native test','Trades','Return','PF','WR','EQDD'],[[r['tag'],r['stats']['trades'],pct(r['stats']['return_pct']),num(r['stats']['pf']),num(r['stats']['win_pct'])+'%',num(r['native']['equity_dd_pct'])+'%'] for r in controls])+'</section>'
    body+='<section class="panel"><h2>Calendar-year contribution inside the native five-year account</h2>'+table(['Year','Trades','NetUSD','PF','WR','W/L'],[[r['year'],r['trades'],num(r['net_profit']),num(r['net_pf']),num(r['win_rate_pct'])+'%',str(r['max_win_streak'])+'/'+str(r['max_loss_streak'])] for r in a['calendar_years']])+'<p>Partial2021/2026. Not six separate annual backtests, and not nested walk-forward.</p></section>'
    stages=[];plats=[]
    for m in 'ABC':
      for s in n.load(R/f'STAGES-{m}.json'):
        rr=s['top'][0];ss=rr['stats'];stages.append([m,s['stage'],s['cases'],s['qualified'],ss['trades'],pct(ss['return_pct']),num(ss['pf']),num(ss['win_pct'])+'%',num(rr['net']['equity_dd_pct'])+'%'])
      for s in n.load(R/f'PLATEAU-{m}.json'):plats.append([m,', '.join(s['axes']),s['neighbours'],num(s['positive_fraction']*100)+'%',num(s['median_pf']),s['passed']])
    body+='<section class="panel"><h2>Full bounded search — every stage retained</h2>'+table(['Module','Stage','Cases','Eligible','Leader trades','Leader return','PF','WR','EQDD'],stages)+'<h3>Joint-neighbourhood plateaus</h3>'+table(['Module','Joint axes','Neighbours','Profitable%','Median PF','Pass'],plats)+'<p>Carry top 3 at each stage, not a guarantee of global optimum. All settings retained in the trial archive. Low-count module screens are exploratory; combined locked gate remains 30.</p><p><a href="IMPLEMENTATION NOTES.txt">Exact tested conventions and limitations</a> · <a href="SELECTION AMENDMENT.txt">Raw-benchmark selection receipt</a> · <a href="ALTERNATIVE PLAN.txt">Tuned comparator plan</a> · <a href="CONTROLLER RESTART.txt">Interrupted-run accounting</a></p></section>'
    if a.get('tuned_comparator'):
      comp=a['tuned_comparator'];rr=[]
      for k in ['5Y','3Y','1Y','6M','3M']:
        r=comp[k];ss=r['stats'];rr.append([k,r['start']+' → '+r['end_exclusive'],ss['trades'],num(ss['trades_per_month']),pct(ss['return_pct']),num(ss['pf']),num(ss['win_pct'])+'%',num(r['native']['equity_dd_pct'])+'%',num(r['native']['sharpe_ratio']),str(ss['max_win_streak'])+'/'+str(ss['max_loss_streak']),r['native']['history_quality']])
      rr=[row[:6]+[rate(comp[row[0]]['stats']['win_pct'])]+row[7:] for row in rr]
      body+='<section class="panel"><h2>Best tuned combination — native diagnostic, not promotion</h2><p>Frozen solely by shared validation score, but module-level validation prerequisites failed. Five-year and three-year windows overlap development/validation; the latest year was previously viewed. These are diagnostic backtests, not independent proof. They do not choose or retune the candidate. Compare to raw above; more parameters are not automatically an improvement.</p>'+table(['Window','Dates excl.','Trades','/month','Return','PF','WR','EQDD','NativeSharpe','W/L','Quality'],rr)+'</section>'
      body+=graph('Last year — tuned versus raw balance',[('Best tuned actual cash',[(d['epoch'],d['balance']) for d in comp['1Y']['ledger']],'#ffcb89'),('Raw actual cash',rawcash('1Y'),'#e5b3f5')],'Separate native shared-account runs, not a sum.',comp['1Y']['start'].replace('.','-'),comp['1Y']['end_exclusive'].replace('.','-'))
    ts=ex['1Y']['trades'];body+='<section class="panel"><h2>Every frozen trade — last year</h2>'+table(['#','Module','Side','OpenedUTC','ClosedUTC','Lots','NetUSD','Initial riskUSD','Holdhours'],[[t['number'],t['module'],t['side'],t['open_time'],t['close_time'],num(t['volume'],3),num(t['net_profit']),num(t['actual_risk']),num(t['hold_hours'])] for t in ts])+'</section>'
    allrows=[]
    for rr in trials:
      ss=rr['stats'];allrows.append([rr['stage'],rr['index'],rr['model'],ss['trades'],pct(ss['return_pct']),num(ss['pf']),num(ss['win_pct'])+'%',num(rr['net']['equity_dd_pct'])+'%',rr['clean'],json.dumps(rr['parameters'],sort_keys=True)])
    body+='<section class="panel"><details><summary>All native passes and rejected alternatives</summary>'+table(['Stage','Case','Model','Trades','Return','PF','WR','EQDD','Clean','Parameters'],allrows)+'</details><p><a href="FINAL SUMMARY.csv">All window metrics CSV</a> · <a href="SEARCH RESULTS.json">All tried passes JSON</a> · <a href="AUDIT.json">Exact ledgers, MC and gates JSON</a> · <a href="PARITY.json">Raw parity evidence</a></p></section>'
    body+='<section class="panel"><h2>Limits and provenance</h2>'+''.join('<p>'+esc(x)+'</p>' for x in a['limitations'])+'<p>Trial accounting: '+esc(json.dumps(a['trial_accounting']))+'. <a href="SILVER RETRY.txt">Failed infrastructure attempt and identical retry</a>.</p><p>Public module labels: <a href="https://api-quantlab.com/algorithmen/funded-xauusd-3x-momentum">QuantLab overview</a>; private settings unknown. No equivalence to vendor profits claimed. Stop here for your review.</p></section></main></body></html>'
    body=body.replace('N/A%','N/A')
    (R/'Results.html').write_text(body,encoding='utf-8');n.save(R/'verification.json',dict(exact_positions_verified=True,raw_parity=n.load(R/'PARITY.json'),native_reports=len(ex)+len(a['other'])+len(a.get('tuned_comparator',{})),native_passes=a['trial_accounting']['total_native_passes'],source_sha256=n.sha(n.EA/'Logic.mqh'),html_sha256=n.sha(R/'Results.html'),current_3_way_source_sha256=n.sha(current_source),current_3_way_selected_set_sha256=n.sha(current_set),tester_only=True,live_changes=False,deployment=False))
    print('Report generated',R/'Results.html')
if __name__=='__main__':main()
