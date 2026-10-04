"""Offline shared-cash proxy replay. NOT native FTMO ticks or a guarded-EA validation.

Reads frozen cached standalone ledgers. The baseline is the current FTMO *roster*,
not a newly tested FTMO binary: e.g. 3-Way Gold's market-entry setting differs
from the standalone SET. Hourly reservations are hypothetical, never a loss cap.
No MT5 imports, terminal startup, account login or orders.
"""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse, ast, hashlib, json, math, random, statistics, sys
from collections import defaultdict

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
STORE=BASE.parent/'EA store'
sys.path.insert(0,str(STORE))
from app.prop_sim.ledger import load_ea
from app.catalog import get_product
from app.evidence_cache import CACHE_ROOT

sys.path.insert(0,str(BASE/'FTMO Fourteen EA Study 2026-09-27'))
import study as legacy

DAY=86400; WEEK=7*DAY; UTC=timezone.utc
def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def dt(value):
    d=datetime.fromisoformat(value.replace('Z','+00:00'))
    # Existing standalone cache convention: naive tester timestamps assumed UTC.
    return (d if d.tzinfo else d.replace(tzinfo=UTC)).timestamp()
def iso(t): return datetime.fromtimestamp(t,UTC).isoformat() if t is not None else None
def save(name,value): (ROOT/name).write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')

def inputs(path):
    return dict(line.split('=',1) for line in path.read_text(encoding='utf-8-sig').splitlines()
                if '=' in line and not line.startswith(';'))

def prepare():
    manifest=read(BASE/'FTMO Thirteen EA Deployment 2026-09-27/PACKAGE.json')
    release=read(BASE/'Hourly Profiles Deployment 2026-10-04/RELEASE.json')
    keys=[r['slug'] for r in manifest['entries']]
    assert len(keys)==14 and not manifest['news_enabled']
    references={r['slug']:r['historical_loss_points'] for r in release['entries']}
    rows=[]; dates=[]; sources=[]; differences=[]
    for key in keys+list(references):
        if key in references:
            mode='standard'; product=None
            summary=read(CACHE_ROOT/'products'/key/mode/'1y.json')
            begin=summary['stats']['from']; end=summary['stats']['to']
        else:
            profile,_=load_ea(key,'1y')
            mode=profile.mode; begin=str(profile.start); end=str(profile.end)
            product=get_product(key)
            ftmo=next(r for r in manifest['entries'] if r['slug']==key)['inputs']
            # Do not copy the website's recommended Safe choice into a FTMO
            # package that explicitly disables its regime filter.
            if mode=='safe' and ftmo.get('InpUseMarkovRegimeFilter')=='false':
                mode='standard'
                summary=read(CACHE_ROOT/'products'/key/mode/'1y.json')
                begin=summary['stats']['from']; end=summary['stats']['to']
            effective_path=(product.dynamic_set_source if mode=='dynamic' else product.safe_set_source if mode=='safe' else None) or product.set_source
            standalone=inputs(BASE/effective_path)
            # Record all actual differing shared inputs; many are only risk/magic/audit.
            different={k:{'ftmo':v,'standalone':standalone[k]} for k,v in ftmo.items()
                       if k in standalone and standalone[k]!=v and 'Risk' not in k and 'Magic' not in k
                       and not k.startswith(('FTMO','InpExpected','InpTester','InpWrite','InpCase'))}
            if different: differences.append({'slug':key,'inputs':different})
        dates.append((dt(begin),dt(end)+DAY))
        path=CACHE_ROOT/'products'/key/mode/'1y.trades.json'
        rr=read(path); accepted=0; invalid=0
        for raw in rr:
            volume=raw.get('volume',0); risk=raw.get('estimated_risk_cash')
            if volume<=0 or (key not in references and (risk is None or risk<=0)):
                invalid+=1; continue
            unitrisk=references[key] if key in references else float(risk)/volume
            symbol=str(raw['symbol']).rstrip('r')
            symbol='USTEC' if symbol in ('USTEC','US100','NAS100') else symbol
            op,cl=dt(raw['open_time']),dt(raw['close_time'])
            # Fees in these ledgers are negative cash charges; retain them.
            unitcomm=(raw.get('commission',0)+raw.get('fees',0))/volume
            gross=raw['gross_profit']/volume; swap=raw.get('swap',0)/volume
            assert abs((gross+unitcomm+swap)*volume-raw['net_profit'])<0.05
            rows.append(dict(key=key,symbol=symbol,news=False,op=op,cl=max(cl,op+.001),
                             unit_risk=unitrisk,unit_gross=gross,unit_comm=unitcomm,unit_swap=swap,
                             open_price=raw['open_price'],close_price=raw['close_price'],side=raw['side'],
                             hourly=key in references))
            accepted+=1
        sources.append(dict(slug=key,mode=mode,from_date=begin,to_date=end,path=str(path.relative_to(STORE)),
                            sha256=sha(path),raw_rows=len(rr),usable_rows=accepted,missing_risk_rows=invalid))
    start=max(x[0] for x in dates); end=min(x[1] for x in dates)
    # Admit only complete trades inside the common window, with no warm-start positions.
    rows=[r for r in rows if start<=r['op']<r['cl']<end]
    assert end-start>300*DAY and all(r['symbol'] in ('XAUUSD','USTEC','USDJPY','US30') for r in rows)
    return rows,keys,start,end,dict(ftmo_package_sha256=sha(BASE/'FTMO Thirteen EA Deployment 2026-09-27/PACKAGE.json'),
                                  hourly_release_sha256=sha(BASE/'Hourly Profiles Deployment 2026-10-04/RELEASE.json'),
                                  replay_source_sha256={str(p.relative_to(BASE)):sha(p) for p in
                                      (legacy.ROOT/'study.py',legacy.OLD/'simulate.py',legacy.OLD/'prepare.py',BASE/'FTMO Paper Application 2026-09-26/compare.py')},
                                  sources=sources,standalone_vs_ftmo_input_differences=differences)

def engine(stress=False,hourly_reserve=1):
    """Reuse the already checked lifecycle engine, with an explicit hourly proxy gate.

    Keeps 7 entries/day, 3 losses/day, $225 portfolio/$150 symbol reserve,
    $300 daily reserve, $9,200 total buffer, margin and closed-position phase gates.
    None of these estimated reservations bound a no-SL position's future equity.
    """
    ns=legacy.engine(50.)
    ns['SPECS']=dict(ns['SPECS'],US30=(1,15))
    src=(legacy.OLD/'simulate.py').read_text(encoding='utf-8-sig')
    tree=ast.parse((legacy.ROOT/'study.py').read_text())
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='engine')
    replacements=ast.literal_eval(next(n.value for n in fn.body if isinstance(n,ast.Assign)
                                   and any(isinstance(t,ast.Name) and t.id=='replacements' for t in n.targets)))
    for old,new in replacements.items():
        assert src.count(old)==1; src=src.replace(old,new)
    old="lot=rounded(RISK/r['unit_risk'])"
    new="budget=(bal*.005 if r.get('hourly') else RISK)\n                lot=(max(.01,rounded(budget/r['unit_risk'])) if r.get('hourly') else rounded(budget/r['unit_risk']))"
    assert src.count(old)==1; src=src.replace(old,new)
    src=src.replace("assert risk<=RISK+1e-7","assert r.get('hourly') or risk<=RISK+1e-7")
    src=src.replace("env=risk*(1.25 if stress else 1.)",f"env=risk*({hourly_reserve!r} if r.get('hourly') else (1.25 if stress else 1.))")
    # Close first on exact ties, matching the generic current ledger replay.
    src=src.replace('events.sort()','events.sort(key=lambda e:(e[0],-1 if e[1]==2 else e[1],e[2]))')
    nodes=[n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=='replay']
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'hourly_ftmo_proxy','exec'),ns)
    ns['costs']=costs
    return ns

def costs(r,stress=False):
    sym=r['symbol']; contract={'XAUUSD':100,'USDJPY':100000,'USTEC':1,'US30':1}[sym]
    g=r['unit_gross']; s=r['unit_swap']; c=r['unit_comm']; extra=0
    # Same explicit FTMO cost floors as the previous study; not FTMO historical quotes.
    floor=.7 if sym in ('USTEC','US30') else 10 if sym=='USDJPY' else max(7,.000014*100*(r['open_price']+r['close_price']))
    c=min(c,-floor)
    if stress:
        g*=.9 if g>0 else 1.1
        extra={'XAUUSD':.2,'USTEC':2.,'US30':2.,'USDJPY':.02}[sym]*contract/(r['open_price'] if sym=='USDJPY' else 1)
        s=min(2*s,0)
        if r['cl']-r['op']>DAY:
            s=min(s,-contract*(1 if sym=='USDJPY' else r['open_price'])*.00015*math.ceil((r['cl']-r['op'])/DAY))
    return g,c,s,extra

def metrics(result,start,end):
    log=result['log']; daily=defaultdict(float)
    for r in log: daily[r['close'][:10]]+=r['net_profit']
    weekdays=[]; day=datetime.fromtimestamp(start,UTC)
    while day.timestamp()<end:
        if day.weekday()<5: weekdays.append(daily[day.date().isoformat()]/10000)
        day+=timedelta(days=1)
    sd=statistics.stdev(weekdays) if len(weekdays)>1 else 0
    return dict(trades=result['trades'],return_pct=(result['balance']/10000-1)*100,
                closed_balance_dd_pct=result['closed_dd_pct'],proxy_reserve_dd_pct=result['model_dd_pct'],
                win_rate_pct=result['win_rate'],profit_factor=result['pf'],
                daily_closed_sharpe=statistics.mean(weekdays)/sd*math.sqrt(252) if sd else None,
                max_win_streak=result['max_win_streak'],max_loss_streak=result['max_loss_streak'],
                open_positions=result['open_positions'],unclosed_entry_costs=result['unclosed_entry_costs'],
                modeled_rule_breach=result['breach'],skipped=result['counts'])

def summary(results,start,end):
    n=len(results)
    def pct(key): return sum(bool(r[key]) for r in results)*100/n
    def quantile(key):
        values=sorted((dt(r[key])-start)/DAY for r in results if r[key] is not None and dt(r[key])<end)
        if not values:return None
        return dict(median=statistics.median(values),p25=values[round((len(values)-1)*.25)],p75=values[round((len(values)-1)*.75)])
    payouts=[r['reward'] for r in results if r['payout']]
    return dict(paths=n,funded_pct=pct('funded'),first_payout_pct=pct('payout'),proxy_breach_pct=pct('breach'),
                median_funded_calendar_days=quantile('funded_at'),median_first_payout_calendar_days=quantile('receipt_at'),
                median_first_reward_usd_if_paid=statistics.median(payouts) if payouts else None,
                expected_first_reward_usd=sum(payouts)/n,
                payout_by={str(h):sum(r['payout'] and dt(r['receipt_at'])<start+h*DAY for r in results)*100/n for h in (90,180,365)})

def unit_tests():
    t=dt('2026-10-05'); row=dict(key='test',symbol='US30',news=False,op=t+3600,cl=t+7200,
         unit_risk=611.53,unit_gross=100,unit_comm=-.63,unit_swap=0,open_price=45000,close_price=45100,side='Long',hourly=True)
    ns=engine(); r=ns['replay']([row.copy()],[],t,t+DAY,challenge=False,detail=True)
    assert r['trades']==1 and abs(r['log'][0]['lots']-.08)<1e-9
    assert abs(r['log'][0]['net_profit']-99.3*.08)<1e-8
    rr=[]
    for i in range(8):rr.append(dict(row,key=str(i),op=t+3600+i*4000,cl=t+3700+i*4000))
    r=ns['replay'](rr,[],t,t+DAY,challenge=False,detail=True)
    assert r['trades']==7 and r['counts']['daily_trade_limit']==1
    assert engine(hourly_reserve=10)['replay']([row.copy()],[],t,t+DAY,challenge=False)['trades']==0
    baseline=dict(row,hourly=False,unit_risk=1000)
    assert ns['replay']([baseline],[],t,t+DAY,challenge=False,detail=True)['log'][0]['lots']==.05
    return dict(local_sizing_gate_checks=5,legacy_lifecycle_checks=legacy.unit_tests())

def render(data):
    def n(x): return '—' if x is None else f'{x:.2f}'
    table=''; paths=''; stressed=''; curves=[]
    for case in data['cases']:
        m=case['historical']; s=case['bootstrap']
        table+=f"<tr><td>{case['label']}</td><td>{m['trades']}</td><td>{n(m['return_pct'])}%</td><td>{n(m['profit_factor'])}</td><td>{n(m['win_rate_pct'])}%</td><td>{n(m['closed_balance_dd_pct'])}%</td><td>{n(m['daily_closed_sharpe'])}</td></tr>"
        paths+=f"<tr><td>{case['label']}</td><td>{n(s['funded_pct'])}%</td><td>{n((s['median_funded_calendar_days'] or {}).get('median'))}</td><td>{n(s['first_payout_pct'])}%</td><td>{n((s['median_first_payout_calendar_days'] or {}).get('median'))}</td><td>${n(s['median_first_reward_usd_if_paid'])}</td></tr>"
        curves.append(dict(label=case['label'],series=case['balance_curve']))
    for case in data['sensitivities']:
        if not case.get('stress_costs') or 'bootstrap' not in case:continue
        m=case['historical'];s=case['bootstrap']
        stressed+=f"<tr><td>{case['label']}</td><td>{n(m['return_pct'])}%</td><td>{n(m['profit_factor'])}</td><td>{n(m['closed_balance_dd_pct'])}%</td><td>{n(s['first_payout_pct'])}%</td><td>{n((s['median_funded_calendar_days'] or {}).get('median'))}</td><td>{n((s['median_first_payout_calendar_days'] or {}).get('median'))}</td></tr>"
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><title>FTMO + hourly comparison</title><style>
    body{background:#061511;color:#e9f5ef;font:16px system-ui;max-width:1250px;margin:40px auto;padding:20px}h1{font-size:44px}p{line-height:1.7}table{width:100%;border-collapse:collapse;margin:25px 0}td,th{padding:14px;border-bottom:1px solid #294039;text-align:left}aside{border:1px solid #9d8938;padding:18px;color:#ffe895}svg{width:100%;background:#10211b;border-radius:18px}small{color:#aac7bc}a{color:#78efc2}button{padding:8px 14px;margin:5px;background:#143329;color:#9cffd5;border:1px solid #3b715c}</style>
    <h1>FTMO roster + hourly profiles</h1><p>Offline, shared-$10,000 proxy replay. Not a native FTMO backtest or a forecast.</p>
    <aside>The unchanged FTMO launcher requires a protective stop. These hourly EAs have none and remain excluded. The additions below are hypothetical reservations based on a historical loss—not bounded risk. Intratrade equity is unknown.</aside>
    <p>WINDOW · WINDOW_TEXT. Baseline: current 14-EA roster, cached standalone settings, $50 planned risk; hourly: 0.5% of current balance, assumed FTMO 0.01-lot step rounded down, 0.01 minimum. Shared cash, entry ordering, estimated margin and portfolio admission limits are modelled.</p>
    <h2>Historical closing ledger · reference costs</h2><table><tr><th>Portfolio</th><th>Trades</th><th>Return</th><th>PF</th><th>Win rate</th><th>Closed-balance DD</th><th>Daily closed Sharpe</th></tr>HISTORY</table>
    <svg id="curve" viewBox="0 0 1000 420" role="img" aria-label="Shared portfolio closed balance"></svg><div id="legend"></div>
    <h2>Paired Monte Carlo · first payout only</h2><p>PATH_TEXT joint four-week block bootstrap paths per portfolio; 365-calendar-day horizon. Same draws preserve within-block cross-EA timing. One-times historical-loss reservation; not a valid floating-equity bound.</p>
    <table><tr><th>Portfolio</th><th>Funded within 365d</th><th>Median days funded*</th><th>First payout within 365d</th><th>Median days paid*</th><th>Median first reward*</th></tr>PATHS</table>
    <p>*Medians are conditional on success. Model assumes 80% reward split, 14-day first request clock, 2/5 business-day handovers and 4 business-day processing. Only first reward is modelled, not yearly payout income. No fee refund included.</p>
    <h2>Execution and carry stress · same paired paths</h2><p>Gross wins reduced 10%, gross losses enlarged 10%, additional slippage and adverse carry. Still not measured floating equity or a future-loss bound.</p>
    <table><tr><th>Portfolio</th><th>Historical return</th><th>PF</th><th>Closed DD</th><th>First payout paths /365d</th><th>Median funded days*</th><th>Median paid days*</th></tr>STRESSED</table>
    <h2>Limitations</h2><p>The hourly selection and sizing references use the same recent evidence; no untouched holdout. Standalone settings can differ from FTMO inputs (see Results.json). Baseline planned risk is estimated from cached rows, not independently reconstructed initial order stops. Multi-module and partial-close state is simplified to one open cached trade per EA. Naive tester timestamps are treated as UTC. Historical costs are retained with explicit cost floors, not historical FTMO quotes. Missing warm-start trades are excluded. Margin uses simplified 1:15 index/metals, 1:30 FX; broker specifications can differ. Admission rejections can change future strategy state, which a cached-ledger replay cannot reproduce. No intratrade mark-to-market, margin-call, gap-exit or true live execution simulation. Reserve stress tests are scenarios, not a mathematical upper/lower bracket. Long-history hourly validation failed.</p>
    <p><a href="Results.json">Full results, sensitivity cases and source fingerprints</a> · <a href="https://ftmo.com/en/trading-objectives/">FTMO objectives</a></p>
    <script>const data=CURVES,colors=['#70e8b1','#f5c66e','#7cbdff','#ee95ce'];const svg=document.getElementById('curve'),legend=document.getElementById('legend');const all=data.flatMap(x=>x.series.map(p=>p[1]));const lo=Math.min(...all)-50,hi=Math.max(...all)+50;const days=WINDOW_DAYS;svg.innerHTML=[0,.25,.5,.75,1].map(q=>`<text x="15" y="${390-q*350}" fill="#aecbbb" font-size="14">$${Math.round(lo+q*(hi-lo))}</text><line x1="90" x2="970" y1="${385-q*350}" y2="${385-q*350}" stroke="#294039"/>`).join('');data.forEach((c,i)=>{const p=c.series.map(v=>`${90+v[0]/days*880},${385-(v[1]-lo)/(hi-lo)*350}`).join(' ');svg.innerHTML+=`<polyline id="p${i}" points="${p}" fill="none" stroke="${colors[i]}" stroke-width="2.4"/>`;const b=document.createElement('button');b.textContent=c.label;b.style.color=colors[i];b.onclick=()=>{const p=document.getElementById('p'+i);p.style.display=p.style.display==='none'?'':'none'};legend.appendChild(b)});</script></html>'''
    for a,b in {'WINDOW_TEXT':data['window']['from']+' to '+data['window']['to']+' ('+str(data['window']['calendar_days'])+' days)',
                'HISTORY':table,'PATHS':paths,'STRESSED':stressed,'PATH_TEXT':str(data['paths']),'CURVES':json.dumps(curves),
                'WINDOW_DAYS':str(data['window']['calendar_days'])}.items():html=html.replace(a,b)
    (ROOT/'Results.html').write_text(html,encoding='utf-8')

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--paths',type=int,default=1000)
    parser.add_argument('--refresh-report',action='store_true'); args=parser.parse_args()
    if args.refresh_report:
        data=read(ROOT/'Results.json'); _,_,start,end,provenance=prepare()
        assert len(data['cases'])==4 and len(data['sensitivities'])==20
        assert data['window']['from_date']==iso(start) and data['window']['end_exclusive']==iso(end)
        assert [(r['slug'],r['sha256']) for r in data['provenance']['sources']]==[(r['slug'],r['sha256']) for r in provenance['sources']]
        data['provenance']=provenance
        data['volume_policy']='Baseline: floor to 0.01, skip below min. Hourly: floor to 0.01 with 0.01 minimum fallback. FTMO specs assumed, not broker verified.'
        data['rules_reviewed_at']='2026-10-04'
        data['official_rules_sources']=['https://ftmo.com/en/trading-objectives/','https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/','https://ftmo.com/en/faq/what-is-the-swing-account-type-and-how-does-it-work/']
        save('Results.json',data);render(data)
        print('Report and provenance refreshed; all numerical replay results retained.');return
    checks=unit_tests(); rows,keys,start,end,provenance=prepare()
    configs=[('Current 14-EA roster',[]),('+ US30',['us30-hourly-profiles']),('+ US100',['us100-hourly-profiles']),
             ('+ Both hourly',['us30-hourly-profiles','us100-hourly-profiles'])]
    # Whole aligned four-week blocks, no circular invented data. Same samples for every comparison.
    poolstart=dt('2025-10-06'); target=dt('2026-10-05'); finish=target+365*DAY
    blockweeks=4; poolweeks=int((end-poolstart)//WEEK); count=poolweeks-blockweeks+1
    assert count>30
    rng=random.Random(20261004); samples=[[rng.randrange(count) for _ in range(math.ceil(365/28))] for _ in range(args.paths)]
    pool=[[] for _ in range(poolweeks)]
    for r in rows:
        j=int((r['op']-poolstart)//WEEK)
        if 0<=j<poolweeks:pool[j].append(r)
    samples_rows=[]
    ny=legacy.c.ZoneInfo('America/New_York')
    for sample in samples:
        out=[]
        for i,j in enumerate(sample):
            src=poolstart+j*WEEK; dest=target+i*blockweeks*WEEK
            # Keep local NY schedule; Prague day limits still reset with their own DST.
            off=dest-src+datetime.fromtimestamp(src+2*DAY,ny).utcoffset().total_seconds()-datetime.fromtimestamp(dest+2*DAY,ny).utcoffset().total_seconds()
            for week in pool[j:j+blockweeks]:
                for r in week:
                    if target<=r['op']+off<finish:out.append(dict(r,op=r['op']+off,cl=r['cl']+off))
        samples_rows.append(out)
    data=dict(status='Exploratory cached-ledger proxy; not native FTMO validation',paths=args.paths,seed=20261004,
              window=dict(from_date=iso(start),end_exclusive=iso(end),**{'from':iso(start)[:10],'to':iso(end-DAY)[:10]},calendar_days=round((end-start)/DAY)),
              checks=checks,provenance=provenance,unchanged_ftmo_launcher='Hourly profiles remain excluded; missing SL is rejected. No live terminal changed.',
              bootstrap_block_weeks=4,guard_policy='7 entries/day, 3 losses/day, 225 total /150 same-symbol, daily reserve300, total-equity reserve9200, estimated margin',
              assumptions='No measured floating equity. 1x/3x/10x hourly historical scenario reserve are NOT bounds. Fixed50 baseline; balance0.5% hourly. All rows estimated-stop sizing; not a new tested guarded build. 80% first reward; no annual recurring payout model; handovers2/5 and processing4 business days assumed.',cases=[],sensitivities=[])
    for label,add in configs:
        selected=set(keys+add); rr=[r for r in rows if r['key'] in selected]
        for stress in (False,True):
            ns=engine(stress); replay=ns['replay']
            hist=replay([dict(r) for r in rr],[],start,end,stress=stress,guards=True,challenge=False,detail=True)
            assert abs(sum(x['net_profit'] for x in hist['log'])+hist['unclosed_entry_costs']-(hist['balance']-10000))<1e-6
            result=[]
            for i,sample in enumerate(samples_rows):
                sr=[dict(r) for r in sample if r['key'] in selected]
                result.append(replay(sr,[],target,finish,stress=stress,guards=True))
                if (i+1)%250==0:print(f'{label}, stress={stress}: {i+1}/{args.paths}',flush=True)
            curve=[[0,10000]]+[[round((dt(x['close'])-start)/DAY,5),round(x['balance'],2)] for x in hist['log']]
            case=dict(label=label,added=add,stress_costs=stress,historical=metrics(hist,start,end),bootstrap=summary(result,target,finish),balance_curve=curve,
                      contributions=hist['by_ea'])
            if not stress:data['cases'].append(case)
            else:data['sensitivities'].append(case)
            for reserve in (3,10):
                hn=engine(stress,reserve)['replay']([dict(r) for r in rr],[],start,end,stress=stress,guards=True,challenge=False,detail=True)
                data['sensitivities'].append(dict(label=label,stress_costs=stress,hourly_reserve_multiple=reserve,historical=metrics(hn,start,end)))
            save('Results.json',data)
            print(json.dumps(dict(label=label,stress=stress,historical=case['historical'],bootstrap=case['bootstrap'])),flush=True)
    render(data);print('Complete. Offline only; no terminal or trading account changed.',flush=True)

if __name__=='__main__':main()
