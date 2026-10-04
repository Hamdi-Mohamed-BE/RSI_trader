"""Native comparison tables/curves and descriptive robustness; no forecasts."""
from pathlib import Path
import gzip,json,html
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def ledger(tag):return json.loads(gzip.decompress((R/'native'/tag/'trades.json.gz').read_bytes()))
def bootstrap(v):
    n=len(v)
    if n<20:return dict(trades=n,eligible=False,reason='Too few position trades')
    rng=np.random.default_rng(20261003);block=5;paths=10000
    idx=(rng.integers(0,n,size=(paths,(n+block-1)//block))[:,:,None]+np.arange(block))%n
    sample=v[idx.reshape(paths,-1)[:,:n]];gp=np.maximum(sample,0).sum(axis=1);gl=-np.minimum(sample,0).sum(axis=1)
    pf=np.divide(gp,gl,out=np.full(paths,np.nan),where=gl>0);finite=pf[np.isfinite(pf)];net=sample.sum(axis=1)
    shuffled=np.array([rng.permutation(v) for _ in range(paths)])
    balance=np.column_stack((np.full(paths,10000),10000+np.cumsum(shuffled,axis=1)));peak=np.maximum.accumulate(balance,axis=1)
    dd=np.max((peak-balance)/peak,axis=1)*100
    longest=np.zeros(paths,dtype=int);run=np.zeros(paths,dtype=int)
    for col in shuffled.T:run=np.where(col<0,run+1,0);longest=np.maximum(longest,run)
    omitted={}
    for rate in (.1,.2):
        amounts=(sample*(rng.random(sample.shape)>=rate)).sum(axis=1)
        omitted[str(rate)]=dict(net_p05=float(np.quantile(amounts,.05)),positive_fraction=float((amounts>0).mean()))
    return dict(paths=paths,block=block,seed=20261003,trades=n,pf_p05=float(np.quantile(finite,.05)) if len(finite) else None,
        pf_p95=float(np.quantile(finite,.95)) if len(finite) else None,no_loss_paths=int((gl==0).sum()),
        net_cash_p05=float(np.quantile(net,.05)),net_cash_p95=float(np.quantile(net,.95)),positive_fraction=float((net>0).mean()),
        shuffled_closed_dd_p95=float(np.quantile(dd,.95)),shuffled_loss_streak_p95=int(np.quantile(longest,.95)),skip_stress=omitted,
        caveat='Resamples historical NET CASH P/L, not fresh dynamic-sizing or floating-equity paths; not multiple-search corrected or independent OOS validation.')
def curve(result):
    rows=ledger(result['tag']);start=result['start'].replace('.','-');end=result['end_exclusive'].replace('.','-')
    daily=pd.Series([r['net_profit'] for r in rows],index=[r['close_time'][:10] for r in rows],dtype=float).groupby(level=0).sum()
    dates=pd.date_range(start,pd.Timestamp(end)-pd.Timedelta(days=1))
    return np.r_[10000,10000+np.cumsum(daily.reindex(dates.strftime('%Y-%m-%d'),fill_value=0).to_numpy())]
def svg(a,b):
    x=curve(a);y=curve(b);lo=min(x.min(),y.min());hi=max(x.max(),y.max());span=max(hi-lo,1)
    def line(v,color):
        pts=' '.join(f'{20+i/(len(v)-1)*760:.1f},{220-(z-lo)/span*190:.1f}' for i,z in enumerate(v))
        return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"/>'
    return f'<svg viewBox="0 0 800 250" role="img" aria-label="Reconstructed closed-position balance baseline versus tested filter"><text x="20" y="18" fill="#9bb7ae">${hi:,.0f}</text>'+line(x,'#91a5b3')+line(y,'#7ef7c7')+f'<text x="20" y="245" fill="#9bb7ae">${lo:,.0f} · gray baseline / green filter · closed-position balance, not floating equity</text></svg>'
def f(v,n=2):return '—' if v is None else f'{v:.{n}f}'
def table(results):
    header='<table><thead><tr><th>EA / filter</th><th>Window</th><th>Trades</th><th>/month</th><th>/weekday</th><th>Return</th><th>PF</th><th>Win%</th><th>Equity DD%</th><th>Closed DD%</th><th>Sharpe*</th><th>Win/Loss run</th></tr></thead><tbody>'
    for r in results:
        s=r['stats'];label='ORIGINAL baseline' if r['original'] else r['variant']
        win=f(s['win_pct'],1) if s['trades'] else '—'
        header+=f'<tr><td>{html.escape(r["label"])} · {label}</td><td>{r["window"]}</td><td>{s["trades"]}</td><td>{f(s["trades_month"])}</td><td>{f(s["trades_weekday"],3)}</td><td>{f(s["return_pct"])}%</td><td>{f(s["pf"],3)}</td><td>{win}</td><td>{f(s["equity_dd_pct"])}</td><td>{f(s["closed_dd_pct"])}</td><td>{f(s["sharpe"])}</td><td>{s["max_win_streak"]}/{s["max_loss_streak"]}</td></tr>'
    return header+'</tbody></table>'

def module_table(results):
    out='<table><thead><tr><th>3 Way year filter</th><th>Module</th><th>Positions</th><th>Net cash</th><th>Win%</th><th>PF</th></tr></thead><tbody>'
    for r in results:
        if r['ea']!='trio' or r['window']!='1y' or r['original']:continue
        positions=ledger(r['tag'])
        for module in sorted({x['module'] for x in positions}):
            v=np.array([x['net_profit'] for x in positions if x['module']==module]);gp=np.maximum(v,0).sum();gl=-np.minimum(v,0).sum()
            pf=float(gp/gl) if gl else None
            out+=f'<tr><td>{r["variant"]}</td><td>{module}</td><td>{len(v)}</td><td>${v.sum():,.2f}</td><td>{(v>0).mean()*100:.1f}</td><td>{f(pf,3)}</td></tr>'
    return out+'</tbody></table>'
def main():
    completed=(R/'SUMMARY.json').is_file();results=load(R/('SUMMARY.json' if completed else 'PROGRESS.json'))
    nominations=load(R/'NOMINATIONS.json');uncertainty={};decisions=[];panels=[]
    for key,n in nominations.items():
        rows=[r for r in results if r['ea']==key];base=next(r for r in rows if r['window']=='1y' and r['variant']=='BASE' and not r['original'])
        chosen=n['variant']
        alternatives=[r for r in rows if r['window']=='1y' and not r['original'] and r['variant']!='BASE' and r['stats']['pf'] is not None]
        display=chosen or (max(alternatives,key=lambda r:(r['stats']['pf'],r['stats']['trades']))['variant'] if alternatives else None)
        matches=[r for r in rows if r['variant']==display and not r['original']] if display else []
        long=[r for r in matches if r['window'] in ('3y','5y')]
        stable=bool(chosen and len(long)==2 and all(r['stats']['trades']>=30 and r['stats']['pf'] is not None and r['stats']['pf']>=1.15 and r['stats']['net']>0 for r in long))
        checks=[]
        for r in matches:
            original=next((x for x in rows if x['window']==r['window'] and (x['original'] or x['variant']=='BASE')),None)
            if original:
                checks.append(dict(window=r['window'],pf_change=None if r['stats']['pf'] is None or original['stats']['pf'] is None else r['stats']['pf']-original['stats']['pf'],return_change=r['stats']['return_pct']-original['stats']['return_pct'],dd_change=r['stats']['equity_dd_pct']-original['stats']['equity_dd_pct'],trades_before=original['stats']['trades'],trades_after=r['stats']['trades']))
                qualification='year nominee' if chosen else 'highest-PF arm — FAILED nomination gate, diagnostic only'
                panels.append(f'<section><h3>{html.escape(r["label"])} · {r["window"]} · {display}</h3><p>{qualification}</p>'+svg(original,r)+'</section>')
        recent=next((r for r in matches if r['window']=='3m'),None)
        relative=bool(stable and checks and all(c['pf_change'] is not None and c['pf_change']>=0 and c['return_change']>=0 and c['dd_change']<=0 for c in checks if c['window'] in ('3m','3y','5y')))
        decision='KEEP UNCHANGED — no eligible year improvement' if not chosen else ('Promising retrospective candidate only; needs independent validation' if relative else 'KEEP UNCHANGED — year nominee is mixed/weaker across quarter or longer history')
        year=next((r for r in matches if r['window']=='1y'),None)
        decisions.append(dict(ea=key,label=base['label'],nominee=chosen,display_filter=display,display_eligible=bool(chosen),baseline=base['stats'],year_display=year['stats'] if year else None,decision=decision,long_gate_passed=stable,consistent_relative_improvement=relative,window_changes=checks,three_month_trades=recent['stats']['trades'] if recent else None,promoted=False))
        for r in [base,*matches]:
            tr=ledger(r['tag']);v=np.array([x['net_profit'] for x in tr]);u=bootstrap(v)
            stress=sum(x['net_profit']-abs(x['commission'])-max(-x['swap'],0) for x in tr)
            u['extra_recorded_cost_cash_stress_net']=float(stress);u['stress_note']='Subtract an additional copy of each observed commission plus negative swap; diagnostic, not a new spread/slippage replay.'
            uncertainty[r['tag']]=u
    save(R/'DECISION.json',decisions);save(R/'UNCERTAINTY.json',uncertainty)
    rows=[r for r in results if r['window']=='1y' and not r['original']]
    other=[r for r in results if r['window']!='1y']
    warnings='Retrospective filter search, not an independently validated edge. Longer windows overlap the searched year. $10,000 start; 1% equity-risk target per trade (per module for 3 Way), not a shared 1% portfolio cap, with existing lot rounding, broker costs and 150ms delay. Real tick coverage: quarter 100%, year 75%, three years 25%, five years 15%; generated ticks fill missing broker history. 3 Way Gold counts completed positions, grouping partial exits—not partial-close deal win rate. For its reconstructed curves/Sharpe, partial profits are assigned to the final position-close date, not the actual intermediate realization date; native equity DD remains exact. Its prior independent-holdout failure remains unresolved. No shared portfolio/FTMO forecast. No production deployment.'
    status='Complete' if completed else 'Partial — research still running'
    items=''.join('<li>'+html.escape(d['label']+' — '+str(d['display_filter'])+(' (eligible year nominee)' if d['display_eligible'] else ' (ineligible; highest-PF diagnostic only)')+': '+d['decision'])+'</li>' for d in decisions)
    css='body{background:#07100f;color:#e8f8f0;font:14px system-ui;margin:30px auto;max-width:1450px;padding:0 20px}h1,h2,h3{color:#7ef7c7}p,li{line-height:1.7}section,.note{border:1px solid #2b493f;border-radius:14px;background:#0b1715;padding:20px;margin:20px 0}table{border-collapse:collapse;width:100%;font-size:12px}th,td{padding:10px;text-align:right;border-bottom:1px solid #294038}th:first-child,td:first-child{text-align:left}svg{width:100%;max-height:280px}.scroll{overflow:auto}a{color:#7ef7c7}'
    page=f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ADX / DI Next Five Review</title><style>{css}</style><h1>Calyx · ADX / DI next five</h1><p>{status} · native MT5 evidence · 37 predefined year configurations + 5 parity controls</p><div class="note">{warnings}</div><h2>Decision summary</h2><ul>{items}</ul><h2>One-year full comparison</h2><p>2025-10-02 to 2026-10-02 exclusive. A/B prefixes = filter only that 3 Way module, all other modules unchanged.</p><div class="scroll">{table(rows)}</div><h2>Fresh-start quarter and longer-window checks</h2><div class="scroll">{table(other)}</div><p>*Annualized daily closed-balance Sharpe, zero-P/L calendar days included. Equity DD is native and includes floating P/L. Curves exclude floating P/L.</p><h2>Individual baseline / nominee curves</h2>'+''.join(panels)+'<p>See UNCERTAINTY.json for 10,000-path descriptive cash bootstrap, shuffle and skip tests. These intervals do not correct for selecting the best of 37 configurations.</p></html>'
    page=page.replace('<h2>Fresh-start quarter and longer-window checks</h2>','<h2>3 Way module contribution</h2><p>A = momentum, B = breakout, C = turn of month. Modules share this EA\'s account equity, so sizing can change even for unfiltered modules. These are contribution totals, not separate module-account backtests.</p><div class="scroll">'+module_table(results)+'</div><h2>Fresh-start quarter and longer-window checks</h2>')
    if completed and len(decisions)==5:
        review='<section><h2>Practical review</h2><p>Gold ORB ADX ≥25 is the strongest longer-history risk-adjusted follow-up candidate: five-year PF 1.39 → 1.85, Sharpe 1.00 → 1.32 and native equity DD 7.42% → 5.59%. But its fresh-start quarter is worse (PF 0.93 → 0.70, return −0.61% → −1.33%). Investigate with forward paper/demo validation before any deployment; no filtered build is installed live.</p><p>XAU Weakness and 3 Way Gold have mixed/weaker longer-window comparisons. Sell Nasdaq and Squeeze fail the year trade-count gate (27 and 8 trades for their highest-PF arms). None of the five tested arms increased the observed maximum winning run. These conclusions do not prove the original EAs profitable live.</p></section>'
        page=page.replace('<h2>Decision summary</h2>',review+'<h2>Decision summary</h2>')
    (R/'Results.html').write_text(page,encoding='utf-8');print(json.dumps(decisions,indent=2))
if __name__=='__main__':main()
