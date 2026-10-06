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
def full(record):
    return read('native/'+record['case']+('/disqualified-results.json' if record.get('disqualified') else '/results.json'))
def save(p,data):(R/p).write_text(json.dumps(stats.json_safe(data),indent=2,allow_nan=False),encoding='utf-8')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pf(x):
    up=np.maximum(x,0).sum(axis=-1);down=-np.minimum(x,0).sum(axis=-1)
    return np.divide(up,down,out=np.where(up>0,np.inf,0.),where=down>0)
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
      pf_p05=float(np.quantile(pf(eq[:,:-1]*x),.05)),pf_p50=float(np.quantile(pf(eq[:,:-1]*x),.5)),
      win_streak_p50=float(np.quantile(mcloss(-x),.5)),win_streak_p95=float(np.quantile(mcloss(-x),.95)),
      loss_streak_p50=float(np.quantile(mcloss(x),.5)),loss_streak_p95=float(np.quantile(mcloss(x),.95)))

def independent(q):
    ts=q['trades'];x=np.array([t['net'] for t in ts]);m=q['metrics']
    assert abs(float(x.sum())-m['net_profit'])<.001
    assert len(x)==m['trades'] and int((x>0).sum())==m['wins']
    assert stats.streaks(x.tolist())==(m['win_streak'],m['loss_streak'])
    if len(x) and np.any(x<0):assert abs(float(pf(x))-m['pf'])<1e-10
    assert q['deal_audit']['all_exported_deals_match_native_report']
    # Verify the 100oz/lot conversion used for observed quote cost stress.
    for t in ts:
        side=1 if t['side']=='Long' else -1
        assert abs(side*(t['close_price']-t['open_price'])*t['volume']*100-t['gross'])<.031,'Gold contract mismatch'
        assert abs(abs(t['open_price']-t['sl'])*t['volume']*100-t['actual_risk'])<.031,'Stop-risk conversion mismatch'
    if not q.get('disqualified'):
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
            bydeal[int(m[1])]=dict(requested=quote[2] if quote[0]=='buy' else quote[1],fill=float(m[3]),side=quote[0],spread=max(quote[2]-quote[1],0))
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
          extra_cash=max(adverse,0)*float(d['volume'])*100,extra_spread_cash=match['spread']*float(d['volume'])*100,spread_price=match['spread']))
    return dict(matched_entries=len(observations),total_entries=len(entries),
      adverse_price_p50=float(np.median([x['adverse_price'] for x in observations])) if observations else None,
      adverse_price_p95=float(np.quantile([x['adverse_price'] for x in observations],.95)) if observations else None,
      spread_price_p50=float(np.median([x['spread_price'] for x in observations])) if observations else None,
      spread_price_p95=float(np.quantile([x['spread_price'] for x in observations],.95)) if observations else None,
      note='Gold contract 100oz/lot; recorded bid/ask spread and adverse quote-to-fill move at matched entries. One extra observed entry spread only; no fabricated exit spread.',observations=observations)

def robustness(q,trials):
    if q.get('disqualified'):return dict(paths=10000,status='execution_rejected',limits='Execution-rejected replay: descriptive realised metrics are retained, but no qualifying Monte Carlo result is claimed.')
    x=position_returns(q);rng=np.random.default_rng(20261005);paths=10000;size=len(x)
    if size==0:return dict(paths=paths,status='insufficient_data',limits='No executed whole positions; bootstrap and win-rate uncertainty cannot be estimated.')
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
    slip=measured_slippage(q);extra={s['position']:s['extra_cash']+s['extra_spread_cash'] for s in slip['observations']}
    stress=[]
    for t in q['trades']:
        # One extra copy of paid costs, observed entry spread and adverse entry fill.
        penalty=abs(t['commission'])+abs(t['fee'])+max(-t['swap'],0)+extra.get(t['position_id'],0)
        stress.append(t['net']-penalty)
    return dict(paths=paths,block_length=5,bootstrap=boot,shuffle=shuffle,omission=omit,
       win_rate_wilson95_pct=[low*100,high*100],sharpe_statistics=sharp,
       slippage_measurement=slip,extra_recorded_cost_stress=dict(net_profit=round(sum(stress),2),
           return_pct=sum(stress)/100,pf=stats.profit_factor(stress),win_rate=sum(v>0 for v in stress)/size*100),
       limits='Whole-position closed-return proxy, resampled at historical proportional sizing. No simulated floating equity, margin, exact broker lot recalculation, elapsed days or FTMO pass probability. Extra-cost test is weak if observed slippage is near zero. Deflated Sharpe is a trial-count approximation; prior broader strategy searches are not fully counted.')

def fmt(v,dec=2):return '—' if v is None else str(v) if isinstance(v,str) else f'{v:,.{dec}f}'
def verdict(comparison,selection):
    candidate=[r for r in comparison if r['variant']=='CANDIDATE']
    recent={r['period']:r for r in candidate}
    failures=[]
    if not selection['qualified_validation']:failures.append('The older native validation gate failed.')
    for period in ['1Y','6M','3M']:
        r=recent.get(period)
        if not r:continue
        m=r['metrics']
        if r.get('disqualified'):failures.append(period+': execution-rejected replay.')
        elif m['trades']==0:failures.append(period+': no executed positions.')
        elif m['net_profit']<=0 or (m.get('pf') or 0)<=1:failures.append(period+': loss or PF no better than 1.')
    one=recent.get('1Y')
    if one and one['metrics']['trades']:
        m=one['metrics']
        if (m.get('win_rate') or 0)<50:failures.append('Recent-year net win rate is below the preferred 50% screen.')
        if (m.get('pf') or 0)<1.20:failures.append('Recent-year PF is below the preferred 1.20 screen.')
        if m['win_streak']<=m['loss_streak']:failures.append('The longest recent-year winning run does not exceed the losing run.')
    if failures:
        return '<h2>Outcome: no replacement recommendation</h2><div class="notice">'+html.escape(' '.join(failures))+' No deployed changes. This is an exploratory comparison, not a qualified live replacement.</div>'
    return '<h2>Outcome: research candidate for review</h2><div class="notice">The frozen candidate met the listed recent-year preference screens. It remains retrospective research, not a deployment decision or future-return forecast. No deployed changes.</div>'
def describe(p):
    modules=[name for key,name in [('InpUseEM1DoubleWick','double wick'),('InpUseEM2InternalSwing','internal swing'),('InpUseEM3CME','CME'),('InpUseEM4Continuation','continuation')] if p[key]]
    stops=['original structural distance','ATR14 simple mean TR','price percentage'][p['InpOptStopMode']]
    if p['InpOptStopMode']==1:stops+=' × '+fmt(p['InpOptStopATR'])
    if p['InpOptStopMode']==2:stops+=' '+fmt(p['InpOptStopPricePct'])+'%'
    stops+=' × '+fmt(p['InpOptStopFactor'])
    mg=['original management','breakeven','ATR trail','50% partial + breakeven'][p['InpOptManage']]
    if p['InpOptManage']>0:mg+=' from '+fmt(p['InpOptTriggerR'])+'R'
    if p['InpOptManage']==2:mg+=' at '+fmt(p['InpOptTrailATR'])+'ATR distance'
    if p['InpUseDynamicTrailingSL']:mg='M15-close step lock: trigger50% of target, lock20% of target'
    side='both' if p['InpAllowLongs'] and p['InpAllowShorts'] else 'long only' if p['InpAllowLongs'] else 'short only'
    session=['all','Asia fixed preset (broker00–08)','London fixed preset (broker07–12)','NY fixed preset (broker13–21)','overlap fixed preset (broker13–16)'][p['InpResearchSession']]
    filt=('ADX14 ≥'+fmt(p['InpOptADXMin'],0) if p['InpOptADXMin']>0 else 'ADX off')+(' + DI direction' if p['InpOptDI'] else ', DI off')
    timeframe='H1' if p['InpExecutionTF']==60 else f'M{p["InpExecutionTF"]}'
    days=['none','Monday','Friday','Monday + Friday'][p['InpOptSkipDays']]
    return timeframe+' signals · '+', '.join(modules)+f' · target{fmt(p["InpRewardRisk"])}R · {stops} · {mg} · {session} · {side} · {filt} · daily max {p["InpOptMaxTrades"] or "original"}, excluded days: {days}'
def row(label,r):
    m=r['metrics'];nat=r['native']
    if r.get('disqualified'):label='REJECTED · '+label
    return '<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in [label,m['trades'],fmt(m['win_rate'],1)+'%',fmt(m['pf'],3),fmt(m['return_pct'])+'%',fmt(nat['equity_dd_pct'])+'%',fmt(m['sharpe_daily_equity']),f"{m['win_streak']} / {m['loss_streak']}",fmt(m['trades_month']),nat['history_quality']])+'</tr>'
HEAD='<tr><th>Version / period</th><th>Trades</th><th>Net wins</th><th>PF</th><th>Return</th><th>Equity DD</th><th>Daily Sharpe</th><th>Win / loss run</th><th>Trades / month</th><th>History</th></tr>'
def table(rows):return '<div class="scroll"><table><thead>'+HEAD+'</thead><tbody>'+''.join(rows)+'</tbody></table></div>'
def graph(series,title):
    pts=[v for _,pairs in series for _,v in pairs];lo=min(pts);hi=max(pts)
    pad=max((hi-lo)*.08,max(abs(lo),abs(hi),1)*.002);lo-=pad;hi+=pad
    decimals=1 if max(abs(lo),abs(hi))<20 else 0
    alltime=[t for _,pairs in series for t,_ in pairs];a=min(alltime);b=max(alltime)
    elements=[]
    for i,(label,pairs) in enumerate(series):
        path=' '.join(('M' if j==0 else 'L')+f'{70+(t-a)/(b-a)*870:.1f},{270-(v-lo)/(hi-lo)*225:.1f}' for j,(t,v) in enumerate(pairs))
        elements.append(f'<path d="{path}" fill="none" stroke="{["#9dadba","#dfbc7b","#77f5c4"][i%3]}" stroke-width="2"/>')
    for y in np.linspace(lo,hi,5):
        py=270-(y-lo)/(hi-lo)*225
        elements.append(f'<path d="M70,{py:.1f} H940" stroke="#24433b"/><text x="64" y="{py+4:.1f}" text-anchor="end">{y:,.{decimals}f}</text>')
    for t in np.linspace(a,b,5):
        px=70+(t-a)/(b-a)*870
        date=pd.Timestamp(t,unit='s',tz='UTC').strftime('%b %Y')
        elements.append(f'<text x="{px:.1f}" y="294" text-anchor="middle">{date}</text>')
    legend=' · '.join('<span style="color:'+['#9dadba','#dfbc7b','#77f5c4'][i%3]+'">■ '+html.escape(s[0])+'</span>' for i,s in enumerate(series))
    return f'<h3>{title}</h3><p>{legend}</p><svg viewBox="0 0 980 310" role="img" aria-label="{html.escape(title)}"><title>{html.escape(title)}</title>'+''.join(elements)+'</svg>'

def main():
    comparison=read('COMPARISON.json');selection=read('SELECTION.json');search=read('SEARCH RESULTS.json')
    expected={(w,v) for w in ['1Y','6M','3M','3Y','5Y','OLDER'] for v in ['CURRENT','CANDIDATE']}
    assert len(comparison)==len(expected) and {(r['period'],r['variant']) for r in comparison}==expected,'Native confirmations are incomplete'
    chosen=selection['candidate']['validation']['parameters']
    reference=next(r['parameters'] for r in search if r['case'].startswith('PARITY-'))
    assert all(r['model']==4 and r['parameters']==(reference if r['variant']=='CURRENT' else chosen) for r in comparison),'A confirmation differs from the frozen selection'
    allq=[];verification=[]
    for r in search:
        file='disqualified-results.json' if r.get('disqualified') else 'results.json'
        q=read('native/'+r['case']+'/'+file);independent(q);allq.append(q);verification.append(r['case'])
        assert float(q['inputs']['InpResearchBrokerUtcOffsetMinutes'])==0
    old=[];rejected=0;archive_runs={}
    for folder in ['LTA Original Optimization 2026-10-05','LTA Original Optimization R2 2026-10-05','LTA Original Optimization R3 2026-10-05']:
        prior=R.parent/folder/'SEARCH RESULTS.json'
        rows=json.loads(prior.read_text()) if prior.exists() else []
        old+=rows;archive_runs[folder]=len(rows)
        rejected+=len(list((R.parent/folder/'rejections').glob('*.json')))
    # JSON 3 and 3.0 are the same MT5 setting; do not inflate the trial count.
    def signature(record):
        p={k:(float(v) if isinstance(v,(int,float)) and not isinstance(v,bool) else v) for k,v in record['parameters'].items()}
        return json.dumps(p,sort_keys=True)
    ids={signature(r) for r in search+old};trials=len(ids)
    # Report both settings and actual model/window runs; don't disguise many attempts.
    robust={}
    for r in comparison:
        if r['period']=='1Y':robust[r['variant']]=robustness(full(r),trials)
    save('ROBUSTNESS.json',robust)
    hashes=read('frozen.json');unchanged=all(digest(R.parent/p)==v for p,v in hashes['production'].items())
    assert unchanged
    save('VERIFICATION.json',dict(independent_checked=len(verification),checked_cases=verification,distinct_settings=trials,
       successful_current_runs=sum(not x.get('disqualified') for x in search),execution_rejected_current=sum(bool(x.get('disqualified')) for x in search),prior_archived_runs=archive_runs,rejected_archived_runs=rejected,production_hashes_unchanged=True,
       parity=read('PARITY.json'),verified_session_offset_minutes=0,qualified_validation=selection['qualified_validation']))
    parts=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LTA optimisation · research only</title><style>body{background:#081511;color:#e8f5ef;font:16px/1.6 system-ui;margin:0}main{max-width:1250px;padding:36px 24px;margin:auto}h1{font-size:42px;line-height:1.15}h2{margin-top:44px}p{color:#b2c6bd}a{color:#77f5c4}.notice{padding:18px;border:1px solid #a5894d;background:#1c2118;border-radius:12px}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:14px}th,td{text-align:right;padding:12px;border-bottom:1px solid #24433b;white-space:nowrap}th:first-child,td:first-child{text-align:left}th{color:#98b6a9}code,pre{background:#132720;padding:8px;white-space:pre-wrap;overflow-wrap:anywhere}svg{width:100%;height:auto}svg text{fill:#b2c6bd;font:12px system-ui}details{padding:18px 0;border-bottom:1px solid #24433b}summary{cursor:pointer;color:#77f5c4}@media(max-width:600px){main{padding:24px 14px}h1{font-size:30px}}</style><main><p>CALYX · RESEARCH ONLY · 5 OCTOBER 2026</p><h1>LTA Volume Profile<br>Original-rule optimisation</h1><div class="notice">No deployed EA, BAT, website cache, live chart or account was changed. One EA only; stop here for user review. Selection used older development/validation data, not the recent tests. All history may have appeared in earlier research; not an untouched holdout.</div>']
    parts.append(f'<p>{trials} distinct settings; {len(search)} audited current native runs, including {sum(bool(x.get("disqualified")) for x in search)} execution-rejected settings excluded before ranking. {len(old)} earlier harness runs and {rejected} failed/incomplete runs retained and excluded. USD10,000 · intended 1% equity risk/trade · Exness XAUUSD · 150ms. Broker minimum/upward lot rounding can exceed requested risk.</p>')
    p=selection['candidate']['validation']['parameters']
    parts.append('<p>Current configured reference: unchanged Recommended Safe M15 from the BAT configuration; this does not verify the inputs currently attached to a live chart. Frozen candidate: '+html.escape(describe(p))+'.</p>')
    parts.append(verdict(comparison,selection))
    parts.append('<h2>Frozen candidate</h2><p>Validation qualification: '+str(selection['qualified_validation'])+'. Optimisation is bounded staged search, not exhaustive. Original Safe macro/profile logic remains. Parameters show timeframe minutes; actual MT5 H1 input encoding is16385. Verified inherited session offset0: broker-clock Asia00–08, London07–12, NY13–21, overlap13–16. These are fixed clock presets, not verified exchange/DST sessions. An earlier protocol note assumed the include default180; actual native inputs remained0 throughout (see OBSERVED SETTINGS.md).</p><pre>'+html.escape(json.dumps({k:v for k,v in p.items() if v!=read('SEARCH RESULTS.json')[0]['parameters'].get(k)},indent=2))+'</pre>')
    parts.append('<h2>Current versus frozen candidate</h2><p>Windows end 2026-10-05 exclusive. 1Y: 2025-10-05; 6M: 2026-04-05; 3M: 2026-07-05; 3Y: 2023-10-05; 5Y: 2021-10-05. Older stress ends 2021-10-05, starts 2019-10-05. Each replay resets USD10,000; periods are overlapping and not additive. Equity DD from native MT5; Sharpe from sampled daily floating equity.</p>')
    parts.append(table([row(r['variant']+' · '+r['period'],r) for r in comparison]))
    recent=[r for r in comparison if r['period']=='1Y'];curves=[];dds=[]
    for r in recent:
        q=full(r);daily,_=daily_equity(q)
        be_losses=[t for t in q['trades'] if t.get('breakeven') and t['net']<0]
        if be_losses:
            mean=sum(t['net'] for t in be_losses)/len(be_losses)
            parts.append('<p>'+html.escape(r['variant'])+f': {len(be_losses)} of {q["metrics"]["losses"]} net losses followed a stop move to entry; mean net result ${fmt(mean)}. These remain losses after actual fill differences and costs; they are not counted as wins or flat trades.</p>')
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
        if v.get('status'):
            parts.append('<h3>'+html.escape(label)+'</h3><p>'+html.escape(v['limits'])+'</p>');continue
        b=v['bootstrap'];parts.append(f'<h3>{label}</h3><p>Bootstrap profit paths {fmt(b["positive_paths_pct"],1)}%; return P5 / median / P95 {fmt(b["return_p05_pct"])} / {fmt(b["return_p50_pct"])} / {fmt(b["return_p95_pct"])}%; closed DD P95 {fmt(b["closed_dd_p95_pct"])}%; PF P5 {fmt(b["pf_p05"],3)}. Win-rate Wilson95% interval {fmt(v["win_rate_wilson95_pct"][0],1)}–{fmt(v["win_rate_wilson95_pct"][1],1)}%.</p><details><summary>Shuffle, omissions, extra recorded-cost stress and Sharpe adjustment</summary><pre>'+html.escape(json.dumps({k:val for k,val in v.items() if k not in ['slippage_measurement','bootstrap']},indent=2))+'</pre><p>'+html.escape(v['slippage_measurement']['note'])+f' Matched {v["slippage_measurement"]["matched_entries"]}/{v["slippage_measurement"]["total_entries"]}; adverse entry price P95 {fmt(v["slippage_measurement"]["adverse_price_p95"],4)}.</p></details>')
    parts.append('<h2>All development screens</h2><p>Selection bias matters: do not confuse the best retrospectively selected result with proven future returns.</p>')
    for file in sorted(R.glob('stage-*.json')):
        stage=json.loads(file.read_text());parts.append('<details><summary>'+html.escape(stage['stage'])+f' · {stage["tested"]} settings</summary>')
        rows=[next(r for r in search if r['case']==c) for c in stage['all_cases']]
        parts.append(table([row(r['parameter_id'],r) for r in rows]))
        parts.append('<pre>'+html.escape(json.dumps([r['parameters'] for r in stage['carry']],indent=2))+'</pre></details>')
    failed_comparisons=[r for r in comparison if r.get('disqualified')]
    if failed_comparisons:
        parts.append('<h2>Execution gate warnings</h2><p>Rows marked REJECTED retain genuine reconciled realised results, but did not meet this study\'s strict zero order/close/modify rejection gate. A market-closed rejection is not an EA crash or a fabricated zero-result run.</p><div class="scroll"><table><tr><th>Replay</th><th>Recorded time</th><th>Failure</th><th>Broker result</th></tr>')
        for r in failed_comparisons:
            with (R/'native'/r['case']/'events.csv').open(encoding='utf-8-sig') as f:
                events=[e for e in csv.DictReader(f) if e['event'] in ['order_failed','close_failed','modify_failed']]
            for e in events:
                stamp=pd.Timestamp(int(e['epoch']),unit='s',tz='UTC').strftime('%Y-%m-%d %H:%M:%S')
                parts.append('<tr>'+''.join('<td>'+html.escape(s)+'</td>' for s in [r['variant']+' '+r['period'],stamp,e['event'],e['note']])+'</tr>')
        parts.append('</table></div>')
    parts.append('<h2>Verification and caveats</h2><p>Every position ledger reconciles costs and final cash to native report; partials are not separate wins. Exact current-Safe parity passed. Reports, journals, settings, exports, hashes, frozen protocol and stage selections are retained beside this report. Earlier harness revisions repaired final tester liquidation export, screening-mode labeling and H1 enum encoding; strategy selection thresholds were unchanged.</p><p><a href="https://www.metatrader5.com/en/terminal/help/start_advanced/start">MT5 official model settings</a> · <a href="https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation">Real/generated tick limitations</a></p><p>Research candidate only. No automatic deployment, no claim of guaranteed profit, no FTMO pass/payout prediction. Next EA awaits user review.</p></main></html>')
    (R/'Results.html').write_text(''.join(parts),encoding='utf-8')
    print(json.dumps(dict(distinct_settings=trials,qualified_validation=selection['qualified_validation'],production_unchanged=unchanged,report=str(R/'Results.html'))))

if __name__=='__main__':main()
