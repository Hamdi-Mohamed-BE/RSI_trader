"""Independent arithmetic, position-level robustness, and research-only report."""
from pathlib import Path
import csv, gzip, hashlib, html, importlib.util, json, math, re
import numpy as np
import pandas as pd

R=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('pipeline_stats',R.parent.parent/'Calyx Research Pipeline/calyx_pipeline.py')
stats=importlib.util.module_from_spec(sp)
import sys
sys.modules[sp.name]=stats
sp.loader.exec_module(stats)

def read(p):return json.loads((R/p).read_text(encoding='utf-8'))
def save(p,data):(R/p).write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf-8')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pf(x):
    up=np.maximum(x,0).sum(axis=-1);down=-np.minimum(x,0).sum(axis=-1)
    return np.divide(up,down,out=np.zeros_like(up),where=down>0)
def mcloss(x):
    run=np.zeros(len(x),dtype=int);high=run.copy()
    for j in range(x.shape[1]):
        run=np.where(x[:,j]<0,run+1,0);high=np.maximum(high,run)
    return high
def pathstats(x):
    eq=np.concatenate([np.ones((len(x),1)),np.cumprod(1+x,axis=1)],axis=1)
    peak=np.maximum.accumulate(eq,axis=1)
    dd=np.max(1-eq/peak,axis=1)*100
    result=(eq[:,-1]-1)*100
    return dict(return_p05_pct=float(np.quantile(result,.05)),return_p50_pct=float(np.quantile(result,.5)),
      return_p95_pct=float(np.quantile(result,.95)),positive_paths_pct=float(np.mean(result>0)*100),
      closed_dd_p50_pct=float(np.quantile(dd,.5)),closed_dd_p95_pct=float(np.quantile(dd,.95)),
      pf_p05=float(np.quantile(pf(x),.05)),pf_p50=float(np.quantile(pf(x),.5)),
      loss_streak_p50=float(np.quantile(mcloss(x),.5)),loss_streak_p95=float(np.quantile(mcloss(x),.95)))

def independent(q):
    ts=q['trades'];x=np.array([t['net'] for t in ts]);m=q['metrics']
    assert abs(float(x.sum())-m['net_profit'])<.001
    assert len(x)==m['trades'] and int((x>0).sum())==m['wins']
    assert stats.streaks(x.tolist())==(m['win_streak'],m['loss_streak'])
    if len(x) and np.any(x<0):assert abs(float(pf(x))-m['pf'])<1e-10
    assert q['deal_audit']['all_exported_deals_match_native_report']
    assert not any(q['counters'][k] for k in ['order_failed','close_failed','modify_failed'])
    if len(x):assert abs(sum(t['gross']+t['commission']+t['swap']+t['fee'] for t in ts)-x.sum())<.001
    assert digest(R/'native'/q['case']/'report.htm')==q['report_sha256']
    return True

def position_returns(q):
    # One concurrent position, equity-sized risk; partials counted in whole position.
    balance=10000.;values=[];ordered=sorted(q['trades'],key=lambda x:x['open_epoch'])
    for t in ordered:
        assert balance>0
        values.append(t['net']/balance);balance+=t['net']
    assert abs(balance-10000-q['metrics']['net_profit'])<.001
    return np.array(values)

def daily_equity(q):
    df=pd.read_csv(R/'native'/q['case']/'equity.csv')
    ser=pd.Series(df.equity.to_numpy(),index=pd.to_datetime(df.epoch,unit='s',utc=True))
    daily=ser.resample('D').last().ffill();daily=daily[daily.index.weekday<5]
    return daily, daily.pct_change().dropna().to_list()

def measured_slippage(q):
    text=gzip.decompress((R/'native'/q['case']/'journal.txt.gz').read_bytes()).decode()
    quote=None;bydeal={}
    for line in text.splitlines():
        m=re.search(r'market (buy|sell) [\d.]+ XAUUSD[^\r\n]*\(([\d.]+) / ([\d.]+) / [\d.]+\)',line)
        if m:quote=(m[1],float(m[2]),float(m[3]))
        m=re.search(r'deal #(\d+) (buy|sell) [\d.]+ XAUUSD at ([\d.]+) done',line)
        if m and quote and m[2]==quote[0]:
            bydeal[int(m[1])]=dict(requested=quote[2] if quote[0]=='buy' else quote[1],fill=float(m[3]),side=quote[0])
            quote=None
    with (R/'native'/q['case']/'deals.csv').open(encoding='utf-8-sig') as f:
        entries=[d for d in csv.DictReader(f) if int(d['entry'])==0]
    observations=[]
    for d in entries:
        match=bydeal.get(int(d['deal']))
        if not match:continue
        assert abs(match['fill']-float(d['price']))<1e-8
        adverse=(match['fill']-match['requested'])*(1 if match['side']=='buy' else -1)
        observations.append(dict(deal=int(d['deal']),position=int(d['position_id']),adverse_price=adverse,
          extra_cash=max(adverse,0)*float(d['volume'])*100))
    return dict(matched_entries=len(observations),total_entries=len(entries),
      adverse_price_p50=float(np.median([x['adverse_price'] for x in observations])) if observations else None,
      adverse_price_p95=float(np.quantile([x['adverse_price'] for x in observations],.95)) if observations else None,
      note='Gold contract 100oz/lot; journal quote versus matching entry fill. Entry only; no fabricated exit spread.',observations=observations)

def robustness(q,trials):
    x=position_returns(q);rng=np.random.default_rng(20261005);paths=10000;size=len(x)
    blocks=rng.integers(0,size,(paths,math.ceil(size/5)))
    ix=((blocks[:,:,None]+np.arange(5))%size).reshape(paths,-1)[:,:size]
    boot=pathstats(x[ix]);shuffled=np.array([rng.permutation(x) for _ in range(paths)])
    shuffle=pathstats(shuffled)
    omit={}
    for fraction in [.1,.2]:
        keep=size-round(size*fraction)
        samples=np.array([x[np.sort(rng.choice(size,keep,replace=False))] for _ in range(paths)])
        omit[str(fraction)]=pathstats(samples)
    daily,returns=daily_equity(q)
    sharp=stats.sharpe_statistics(returns,trials,252)
    low,high=stats.wilson_interval(q['metrics']['wins'],size)
    slip=measured_slippage(q);extra={s['position']:s['extra_cash'] for s in slip['observations']}
    stress=[]
    for t in q['trades']:
        # One extra copy of actually paid commissions/fees/swaps and observed adverse entry fill.
        penalty=abs(t['commission'])+abs(t['fee'])+max(-t['swap'],0)+extra.get(t['position_id'],0)
        stress.append(t['net']-penalty)
    return dict(paths=paths,block_length=5,bootstrap=boot,shuffle=shuffle,omission=omit,
       win_rate_wilson95_pct=[low*100,high*100],sharpe_statistics=sharp,
       slippage_measurement=slip,extra_recorded_cost_stress=dict(net_profit=round(sum(stress),2),
           return_pct=sum(stress)/100,pf=stats.profit_factor(stress),win_rate=sum(v>0 for v in stress)/size*100),
       limits='Whole-position closed-return proxy, resampled at historical proportional sizing. No simulated floating equity, margin, exact broker lot recalculation, elapsed days or FTMO pass probability. Extra-cost test is weak if observed slippage is near zero. Deflated Sharpe is a trial-count approximation; prior broader strategy searches are not fully counted.')

def fmt(v,dec=2):return '—' if v is None else f'{v:,.{dec}f}'
def row(label,r):
    m=r['metrics'];nat=r['native']
    return '<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in [label,m['trades'],fmt(m['win_rate'],1)+'%',fmt(m['pf'],3),fmt(m['return_pct'])+'%',fmt(nat['equity_dd_pct'])+'%',fmt(m['sharpe_daily_equity']),f"{m['win_streak']} / {m['loss_streak']}",fmt(m['trades_month']),nat['history_quality']])+'</tr>'
HEAD='<tr><th>Version / period</th><th>Trades</th><th>Net wins</th><th>PF</th><th>Return</th><th>Equity DD</th><th>Daily Sharpe</th><th>Win / loss run</th><th>Trades / month</th><th>History</th></tr>'
def table(rows):return '<div class="scroll"><table><thead>'+HEAD+'</thead><tbody>'+''.join(rows)+'</tbody></table></div>'
def graph(series,title):
    pts=[v for _,pairs in series for _,v in pairs];lo=min(pts);hi=max(pts);pad=max((hi-lo)*.08,10);lo-=pad;hi+=pad
    alltime=[t for _,pairs in series for t,_ in pairs];a=min(alltime);b=max(alltime)
    elements=[]
    for i,(label,pairs) in enumerate(series):
        path=' '.join(('M' if j==0 else 'L')+f'{70+(t-a)/(b-a)*870:.1f},{270-(v-lo)/(hi-lo)*225:.1f}' for j,(t,v) in enumerate(pairs))
        elements.append(f'<path d="{path}" fill="none" stroke="{["#9dadba","#77f5c4"][i%2]}" stroke-width="2"/>')
    for y in np.linspace(lo,hi,5):
        py=270-(y-lo)/(hi-lo)*225
        elements.append(f'<path d="M70,{py:.1f} H940" stroke="#24433b"/><text x="64" y="{py+4:.1f}" text-anchor="end">{y:,.0f}</text>')
    for t in np.linspace(a,b,5):
        px=70+(t-a)/(b-a)*870
        date=pd.Timestamp(t,unit='s',tz='UTC').strftime('%b %Y')
        elements.append(f'<text x="{px:.1f}" y="294" text-anchor="middle">{date}</text>')
    legend=' · '.join(html.escape(s[0]) for s in series)
    return f'<h3>{title}</h3><p>{legend}</p><svg viewBox="0 0 980 310" role="img" aria-label="{html.escape(title)}"><title>{html.escape(title)}</title>'+''.join(elements)+'</svg>'

def main():
    comparison=read('COMPARISON.json');selection=read('SELECTION.json');search=read('SEARCH RESULTS.json')
    allq=[];verification=[]
    for r in search:
        q=read('native/'+r['case']+'/results.json');independent(q);allq.append(q);verification.append(r['case'])
    prior=R.parent/'LTA Original Optimization 2026-10-05/SEARCH RESULTS.json'
    old=json.loads(prior.read_text()) if prior.exists() else []
    ids={r['parameter_id'] for r in search+old};trials=len(ids)
    # Report both settings and actual model/window runs; don't disguise many attempts.
    robust={}
    for r in comparison:
        if r['period']=='1Y':robust[r['variant']]=robustness(read('native/'+r['case']+'/results.json'),trials)
    save('ROBUSTNESS.json',robust)
    hashes=read('frozen.json');unchanged=all(digest(R.parent/p)==v for p,v in hashes['production'].items())
    assert unchanged
    save('VERIFICATION.json',dict(independent_checked=len(verification),checked_cases=verification,distinct_settings=trials,
       successful_R2_runs=len(search),successful_R1_runs=len(old),rejected_R1_runs=1,production_hashes_unchanged=True,
       parity=read('PARITY.json'),qualified_validation=selection['qualified_validation']))
    parts=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LTA optimisation · research only</title><style>body{background:#081511;color:#e8f5ef;font:16px/1.6 system-ui;margin:0}main{max-width:1250px;padding:36px 24px;margin:auto}h1{font-size:42px;line-height:1.15}h2{margin-top:44px}p{color:#b2c6bd}a{color:#77f5c4}.notice{padding:18px;border:1px solid #a5894d;background:#1c2118;border-radius:12px}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:14px}th,td{text-align:right;padding:12px;border-bottom:1px solid #24433b;white-space:nowrap}th:first-child,td:first-child{text-align:left}th{color:#98b6a9}code,pre{background:#132720;padding:8px;white-space:pre-wrap;overflow-wrap:anywhere}svg{width:100%;height:auto}svg text{fill:#b2c6bd;font:12px system-ui}details{padding:18px 0;border-bottom:1px solid #24433b}summary{cursor:pointer;color:#77f5c4}@media(max-width:600px){main{padding:24px 14px}h1{font-size:30px}}</style><main><p>CALYX · RESEARCH ONLY · 5 OCTOBER 2026</p><h1>LTA Volume Profile<br>Original-rule optimisation</h1><div class="notice">No deployed EA, BAT, website cache, live chart or account was changed. One EA only; stop here for user review. Selection used older development/validation data, not the recent tests. All history may have appeared in earlier research; not an untouched holdout.</div>']
    parts.append(f'<p>{trials} distinct settings; {len(search)} completed R2 native runs. R1 preliminary screens retained and excluded. USD10,000 · intended 1% equity risk/trade · Exness XAUUSD · 150ms. Broker minimum/upward lot rounding can exceed requested risk.</p>')
    p=selection['candidate']['validation']['parameters']
    parts.append('<h2>Frozen candidate</h2><p>Validation qualification: '+str(selection['qualified_validation'])+'. Optimisation is bounded staged search, not exhaustive. Original Safe macro/profile logic remains.</p><pre>'+html.escape(json.dumps({k:v for k,v in p.items() if v!=read('SEARCH RESULTS.json')[0]['parameters'].get(k)},indent=2))+'</pre>')
    parts.append('<h2>Current versus frozen candidate</h2><p>Windows end 2026-10-05 exclusive. 1Y: 2025-10-05; 6M: 2026-04-05; 3M: 2026-07-05; 3Y: 2023-10-05; 5Y: 2021-10-05. Older stress ends 2021-10-05, starts 2019-10-05. Each replay resets USD10,000; periods are overlapping and not additive. Equity DD from native MT5; Sharpe from sampled daily floating equity.</p>')
    parts.append(table([row(r['variant']+' · '+r['period'],r) for r in comparison]))
    recent=[r for r in comparison if r['period']=='1Y'];curves=[];dds=[]
    for r in recent:
        q=read('native/'+r['case']+'/results.json');daily,_=daily_equity(q)
        curves.append((r['variant'],[(t.timestamp(),float(v)) for t,v in daily.items()]))
        dd=100*(daily/daily.cummax()-1)
        dds.append((r['variant'],[(t.timestamp(),float(v)) for t,v in dd.items()]))
    parts.append(graph(curves,'Recent year · sampled floating equity (USD)'))
    parts.append(graph(dds,'Recent year · daily-close equity drawdown (%)'))
    parts.append('<h2>Selection before recent tests</h2><p>Development: 2021-10-05–2024-10-05. Validation: 2024-10-05–2025-10-05. Model4 finalist replays; real ticks are not available over all older history. Screens: Model0 generated every tick, not OHLC. At least 60 development trades and PF≥1.10; validation ≥20 trades and PF≥1.15. Prefer ≥50% wins/PF≥1.20. Stable neighbouring settings required.</p>')
    finals=read('NATIVE FINALISTS.json');parts.append(table([row(f'Finalist {i+1} · '+kind,r[kind]) for i,r in enumerate(finals) for kind in ['development','validation']]))
    for check in read('PLATEAUS.json'):
        parts.append(f'<p>Plateau {check["finalist"]["parameter_id"]}: {fmt(check["positive_fraction"]*100,1)}% profitable neighbours, median PF {fmt(check["median_pf"],3)}; pass {check["passed"]}.</p>')
    parts.append('<h2>10,000-path robustness · recent year</h2><p>Whole-position proportional closed-return resampling, block length5. Not floating-equity/margin simulations or forecasts. Shuffling estimates ordering risk, not return edge. Random omission keeps original order of retained trades. Deflated Sharpe is only a trial-count approximation; broader historical searches are uncounted.</p>')
    for label,v in robust.items():
        b=v['bootstrap'];parts.append(f'<h3>{label}</h3><p>Bootstrap profit paths {fmt(b["positive_paths_pct"],1)}%; return P5 / median / P95 {fmt(b["return_p05_pct"])} / {fmt(b["return_p50_pct"])} / {fmt(b["return_p95_pct"])}%; closed DD P95 {fmt(b["closed_dd_p95_pct"])}%; PF P5 {fmt(b["pf_p05"],3)}. Win-rate Wilson95% interval {fmt(v["win_rate_wilson95_pct"][0],1)}–{fmt(v["win_rate_wilson95_pct"][1],1)}%.</p><details><summary>Shuffle, omissions, extra recorded-cost stress and Sharpe adjustment</summary><pre>'+html.escape(json.dumps({k:val for k,val in v.items() if k not in ['slippage_measurement','bootstrap']},indent=2))+'</pre><p>'+html.escape(v['slippage_measurement']['note'])+f' Matched {v["slippage_measurement"]["matched_entries"]}/{v["slippage_measurement"]["total_entries"]}; adverse entry price P95 {fmt(v["slippage_measurement"]["adverse_price_p95"],4)}.</p></details>')
    parts.append('<h2>All development screens</h2><p>Selection bias matters: do not confuse the best retrospectively selected result with proven future returns.</p>')
    for file in sorted(R.glob('stage-*.json')):
        stage=json.loads(file.read_text());parts.append('<details><summary>'+html.escape(stage['stage'])+f' · {stage["tested"]} settings</summary>')
        rows=[next(r for r in search if r['case']==c) for c in stage['all_cases']]
        parts.append(table([row(r['parameter_id'],r) for r in rows]))
        parts.append('<pre>'+html.escape(json.dumps([r['parameters'] for r in stage['carry']],indent=2))+'</pre></details>')
    parts.append('<h2>Verification and caveats</h2><p>Every position ledger reconciles costs and final cash to native report; partials are not separate wins. Exact current-Safe parity passed. Reports, journals, settings, exports, hashes, frozen protocol and stage selections are retained beside this report. R2 repaired only test-end export and corrected screen model selection.</p><p><a href="https://www.metatrader5.com/en/terminal/help/start_advanced/start">MT5 official model settings</a> · <a href="https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation">Real/generated tick limitations</a></p><p>Research candidate only. No automatic deployment, no claim of guaranteed profit, no FTMO pass/payout prediction. Next EA awaits user review.</p></main></html>')
    (R/'Results.html').write_text(''.join(parts),encoding='utf-8')
    print(json.dumps(dict(distinct_settings=trials,qualified_validation=selection['qualified_validation'],production_unchanged=unchanged,report=str(R/'Results.html'))))

if __name__=='__main__':main()
