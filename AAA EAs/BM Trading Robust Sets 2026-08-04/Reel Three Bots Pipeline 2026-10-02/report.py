"""Static scientific plots plus offline evidence report. Does not edit website data."""
from search import *
import html
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

NAMES={'A':'DE30 · Range breakout','B':'Gold · ATR candle breakout','C':'Gold · Donchian breakout'}
plt.rcParams.update({'figure.facecolor':'#071511','axes.facecolor':'#0c1d17','axes.edgecolor':'#305047','text.color':'#eef9f1','axes.labelcolor':'#c6e5d7','xtick.color':'#c6e5d7','ytick.color':'#c6e5d7','grid.color':'#264039','font.size':10})

def readable_settings(m,c):
    if not c:return '<p>No development finalist met the frozen minimum requirements.</p>'
    entry=['Original execution','Completed-bar confirmation','Limit offset','Stop offset'][c['entry']]
    if c['stop']==0:stop=f"Range-width multiple {c['sl']}" if m=='A' else f"{c['sl']}% of {'signal close' if m=='B' else 'entry price'}"
    elif c['stop']==1:stop=f"{c['sl']}% of entry price"
    elif c['stop']==2:stop=f"{c['sl']} × ATR14"
    else:stop=('Five-bar swing' if c['stop']==3 else '20-bar structure')+' plus 0.1 × ATR14 buffer'
    trail={0:'None',1:'Break even',2:'ATR distance',3:'Price-percentage distance',4:'EMA20',5:'Five-bar swing',6:'Chandelier 3 × ATR',7:'Step-lock',9:'Original Donchian trailing'}[c['trail']]
    session=['All','Asia','London','New York','London / New York overlap','New York open'][c['session']]
    direction=['Both','Long only','Short only'][c['direction']]
    filt=['None','EMA200 bias and slope','H4 EMA50','ADX14 minimum','DI agreement','ATR percentile regime','Spread ≤ 0.1 × ATR','D1 EMA50','ADX14 plus DI agreement'][c['filter']]
    if c['filter'] in [3,8]:filt+=f" ≥ {c['adx_min']}"
    exit_rule={0:'Fixed target / configured management',1:f"Time exit after {c['hold']} signal bars",3:'Close 50% at +1R when broker lot constraints permit, then manage the remainder to its target'}[c['exit']]
    trailing_detail='arms at +0.5% price movement, follows at 0.1% of entry price' if c['trail']==9 else f"arm {c['start']}R, distance setting {c['dist']}"
    text=f"Signal: {c['tf']}-minute bars. Entry: {entry}. Stop: {stop}. Target: {str(c['rr'])+'R' if c['rr'] else 'no fixed target'}. Exit: {exit_rule}. Trailing: {trail}, {trailing_detail}. Session: {session}. Direction: {direction}. Filter: {filt}. Maximum positions: {c['maxpos']}."
    if m=='A':text+=f" Range: {c['range_start']}:00–{c['range_end']}:00 seasonal UTC+2/+3 reference clock; flat setting {c['range_flat']}:00."
    if m=='B':text+=f" Signal range > {c['p2']} × ATR({c['atr_period']}); close within outer {100*c['p3']:g}% of signal range."
    if m=='C':text+=f" Channel: {c['p1']} completed {c['channel_tf']}-minute bars; midpoint reset."
    return '<p>'+html.escape(text)+'</p>'

def raw_gate_details(g):
    reasons=[]
    for per in ['3y','5y']:
        r=g['runs'][per];s=r['stats'];n=r['net']
        if not r['clean']:reasons.append(f"{per}: execution gate failed ({', '.join(k+'='+str(n[k]) for k in FAIL_KEYS if n[k]) or 'stop-out/runtime check'}).")
        if s['trades']<30:reasons.append(f"{per}: fewer than 30 trades.")
        if s['net']<=0:reasons.append(f"{per}: non-positive net return.")
        if (s['pf'] or 0)<1.15:reasons.append(f"{per}: PF {s['pf']} below 1.15.")
    s=g['runs']['5y']['stats'];mean=s['net']/max(1,s['trades'])
    if g['control_median_mean'] is None or (s['pf'] or 0)<=g['control_median_pf'] or mean<=g['control_median_mean']:reasons.append('Did not outperform both median control PF and mean closed-trade cash P/L.')
    return '<p>'+html.escape(' '.join(reasons) or 'Passed the frozen raw gate.')+f" Median control PF: {g['control_median_pf']:.3f}. Controls are timing/risk matched, not exact fill/occupancy matches.</p>"

def plot(name,title,filename):
    p=OUT/name/'0-trace.csv.gz'
    if not p.exists():return ''
    d=pd.read_csv(io.BytesIO(gzip.decompress(p.read_bytes())));t=pd.to_datetime(d.epoch,unit='s')
    fig,ax=plt.subplots(2,1,figsize=(12,6.5),sharex=True,gridspec_kw={'height_ratios':[3,1]});ax[0].plot(t,d.balance,color='#72ecc1',label='Shared balance' if name.startswith('combo') else 'Balance',lw=1.3);ax[0].plot(t,d.equity,color='#ffcc77',alpha=.65,lw=.7,label='Floating equity (5-minute samples)');ax[0].set_title(title,loc='left',pad=12);ax[0].set_ylabel('USD');ax[0].legend(loc='upper left',facecolor='#0c1d17',labelcolor='#eef9f1');ax[0].grid(alpha=.5)
    peak=np.maximum.accumulate(np.r_[10000,d.equity.to_numpy()])[1:];dd=(peak-d.equity)/peak*100;ax[1].fill_between(t,-dd,0,color='#f27e88',alpha=.7);ax[1].set_ylabel('Equity DD %');ax[1].grid(alpha=.5);fig.autofmt_xdate();fig.tight_layout();fig.savefig(ROOT/filename,dpi=140);plt.close(fig)
    return f'<img src="{filename}" alt="{html.escape(title)}">'

def table(rows):
    heads=['Window','Version','Return','PF','Win rate','Native equity DD','Daily closed-P/L Sharpe','Trades','/ month','/ weekday','Win / loss streak','Test-end closures','History quality']
    out='<div class="scroll"><table><thead><tr>'+''.join(f'<th>{h}</th>' for h in heads)+'</tr></thead><tbody>'
    for label,version,r in rows:
        s=r['stats'];n=r.get('native_metrics') or {};values=[label,version,f"{s['return_pct']:+.2f}%",s['pf'],f"{s['win_pct']}%",f"{r['net']['equity_dd_pct']:.2f}%",s['sharpe'],s['trades'],s['trades_per_month'],s['trades_per_day'],f"{s['max_win_streak']} / {s['max_loss_streak']}",r['net'].get('boundary',0),n.get('history_quality','See native logs')]
        out+='<tr>'+''.join(f'<td>{html.escape(str(x))}</td>' for x in values)+'</tr>'
    return out+'</tbody></table></div>'

def mc_card(a):
    b=a.get('bootstrap',{});s=a.get('sharpe',{});c=a.get('cost_stress') or {}
    fail=', '.join(k for k,v in a.get('gates',{}).items() if not v)
    return f'''<div class="box"><h3>Robustness · {a.get('verdict')}</h3><p>10,000 paths · five-trade/five-day block resampling · closed P/L only.</p><p>Return P5 / median / P95: {b.get('return_p05_pct',0):+.2f}% / {b.get('return_p50_pct',0):+.2f}% / {b.get('return_p95_pct',0):+.2f}% · PF P5 {b.get('profit_factor_p05',0):.2f} · Profitable paths {b.get('probability_profit_pct',0):.1f}%</p><p>Deflated Sharpe screen: {s.get('deflated_sharpe_pct',0):.2f}% · Extra observed-spread stress PF: {c.get('pf','unavailable')}.</p><p class="warn">Failed gates: {html.escape(fail or 'none')}</p><details><summary>Complete audit / resampling / trade-removal evidence</summary><pre>{html.escape(json.dumps(a,indent=2))}</pre></details></div>'''

def main():
    frozen=load(ROOT/'FROZEN PICKS.json');raw=load(ROOT/'RAW GATES.json');comb=load(ROOT/'COMBINATIONS.json');audit=load(ROOT/'ROBUSTNESS.json');trials=load(ROOT/'TRIAL ACCOUNTING.json');parts=[]
    for m in 'ABC':
        p=frozen[m];parts.append(f'<section><h2>{NAMES[m]}</h2><p>Raw gate: {raw[m]["gate"]}. Exploratory selection: {p["verdict"]}. Final status: {p.get("final_verdict","research only")}.</p>')
        parts.append(raw_gate_details(raw[m]))
        parts.append(readable_settings(m,p.get('parameters')))
        hold_block=ROOT/f'HOLDOUT-BLOCK-{m}.json'
        if hold_block.exists():parts.append('<p class="warn">Older holdout unavailable under the frozen history/warm-up requirements. No replacement dates or invented observations were used.</p><details><summary>Native holdout diagnostic</summary><pre>'+html.escape(json.dumps(load(hold_block),indent=2))+'</pre></details>')
        rows=[]
        for per in WEB:
            rows.append((per,'Original rules',raw[m]['runs'][per]))
            if p.get('periods'):rows.append((per,'Frozen exploratory',p['periods'][per]))
        if p.get('validation'):rows.append(('Validation','Frozen exploratory',p['validation']))
        if p.get('periods',{}).get('holdout'):rows.append(('Older holdout','Frozen exploratory',p['periods']['holdout']))
        parts.append(table(rows))
        for per in ['1y','5y']:parts.append(plot(f'raw-{m}-{per}-m4',f'{NAMES[m]} · {per} · original rules',f'{m}-raw-{per}.png'))
        if f'raw-{m}-5y-m4' in audit:parts.append('<h3>Original-rule robustness</h3>'+mc_card(audit[f'raw-{m}-5y-m4']))
        if p.get('periods'):
            parts.append('<h3>Frozen exploratory version</h3>')
            for per in ['1y','5y']:parts.append(plot(f'frozen-{m}-{per}',f'{NAMES[m]} · {per} · frozen exploratory',f'{m}-{per}.png'))
            if f'frozen-{m}-5y' in audit:parts.append(mc_card(audit[f'frozen-{m}-5y']))
            if f'frozen-{m}-holdout' in audit:parts.append(mc_card(audit[f'frozen-{m}-holdout']))
        stages=load(ROOT/f'STAGES-{m}.json');plateau=load(ROOT/f'PLATEAUS-{m}.json')
        parts.append(f'<details><summary>Frozen settings / staged search / plateau evidence</summary><pre>{html.escape(json.dumps(dict(settings=p.get("parameters"),stages=[dict(stage=s["stage"],cases=s["cases"],best=s["leaders"][0]["stats"]) for s in stages],plateau=plateau),indent=2))}</pre></details></section>')
    parts.append('<p>Trade counts and win rates aggregate all fills and partial exits by position ID, including commission, swap and fees. A partial exit is not counted as a separate winning trade. Sharpe uses zero-filled calendar-day closed P/L; it is not the MT5 per-deal Sharpe statistic.</p>')
    for label,p in comb.items():
        parts.append(f'<section><h2>Actual shared portfolio · {html.escape(label)}</h2><p>One $10,000 balance; 1% of current shared balance per entry. Native multicurrency execution, not an overlay of independent equity curves. Members: {" + ".join(p["members"])}.</p>')
        if label=='all-exploratory':parts.append('<p class="warn">This comparison includes rejected research candidates. It is not a qualified or recommended trading portfolio.</p>')
        hold_audit=audit.get(f'combo-{label}-holdout',{})
        if label!='raw-baseline' and ('holdout' not in p['periods'] or not hold_audit.get('data_evidence',{}).get('passed',False)):
            parts.append('<p class="warn">Shared older-holdout evidence is invalid/unavailable under the frozen history and required-indicator checks. DE30 lacks the full warm-up and its required ATR/ADX handles failed. Its absence must not be presented as a valid three-bot test. Any retained holdout row is diagnostic only.</p>')
        parts.append(table([(per,'Invalid diagnostic — missing module/history' if not audit.get(f'combo-{label}-{per}',{}).get('data_evidence',{}).get('passed',True) else 'Shared account',r) for per,r in p['periods'].items()]))
        for per in ['6m','1y','5y']:parts.append(plot(f'combo-{label}-{per}',f'Shared portfolio · {label} · {per}',f'portfolio-{label}-{per}.png'))
        for per in ['5y','holdout']:
            if f'combo-{label}-{per}' in audit:parts.append(mc_card(audit[f'combo-{label}-{per}']))
        parts.append('</section>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calyx · Three ideas pipeline</title><style>body{background:#071511;color:#eef9f1;font:16px system-ui;margin:auto;max-width:1450px;padding:35px}h1{font-size:46px;letter-spacing:-1.5px}h2{font-size:29px}p{color:#b9d6ca;line-height:1.6}section,.box{background:#0c1d17;border:1px solid #2a463c;border-radius:17px;padding:24px;margin:25px 0}img{width:100%;border-radius:10px}table{border-collapse:collapse;font-size:14px;width:100%}th,td{padding:12px;border-bottom:1px solid #2a463c;text-align:left;white-space:nowrap}th{color:#72ecc1}.scroll{overflow:auto}.warn{color:#ffcc77}pre{white-space:pre-wrap;max-height:650px;overflow:auto;font-size:12px}summary{color:#72ecc1;cursor:pointer}a{color:#72ecc1}</style><header><p>CALYX · RESEARCH ONLY · 2 OCTOBER 2026</p><h1>Three ideas. Full evidence.<br>No hidden failures.</h1><p>DE30 range breakout · Gold ATR candle breakout · Gold Donchian breakout</p></header>'''
    page+=f'''<div class="box warn">Exploratory optimisation was explicitly authorised despite raw-gate failures. A high development return is not a qualification. {trials['passes']:,} native case attempts are counted conservatively for DSR. No production or live-account changes were made.</div><p>Development: Oct 2021–Apr 2024. Validation: Apr 2024–Oct 2025. Older holdout: Oct 2019–Apr 2021. Recent year has already been viewed, so is not untouched. Six-month/1y/3y/5y windows overlap and are historical context. Model 1 search → Model 4 frozen checks with 150 ms delay and broker costs. Real ticks begin Jan 2026; older ticks are generated. History quality can include pre-entry warm-up. Leverage 1:2000 is research configuration, not an FTMO account model.</p><p>Charts use five-minute equity samples; worst-tick native equity drawdown is in the tables. Monte Carlo, trade removal and reshuffles use closed P/L, not margin/floating-equity replay. Their probabilities are conditional historical resampling, not forecasts or FTMO pass/payout estimates.</p>'''+''.join(parts)+'''<footer><p>Evidence files: RAW GATES.json · FROZEN PICKS.json · ROBUSTNESS.json · COMBINATIONS.json · OVERLAP.json · TRIAL ACCOUNTING.json. Every native batch retains frozen inputs, source, compile log, report, position ledger and journal.</p></footer></html>'''
    (ROOT/'Pipeline Results.html').write_text(page,encoding='utf-8')
    summary={m:dict(name=NAMES[m],raw_gate=raw[m]['gate'],verdict=frozen[m].get('final_verdict'),native_verdict=frozen[m]['verdict'],periods={k:v['stats'] for k,v in frozen[m].get('periods',{}).items() if v}) for m in 'ABC'}
    save(ROOT/'SUMMARY.json',summary|dict(shared={k:{p:v['stats'] for p,v in x['periods'].items()} for k,x in comb.items()},shared_data_validity={k:{p:audit.get(f'combo-{k}-{p}',{}).get('data_evidence',{}) for p in x['periods']} for k,x in comb.items()},trials=trials));status('REPORT COMPLETE')

if __name__=='__main__':main()
