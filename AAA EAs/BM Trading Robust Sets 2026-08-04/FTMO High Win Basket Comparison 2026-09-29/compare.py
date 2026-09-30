"""Offline, fixed-rule portfolio comparison; deliberately no terminal/trading imports."""
from pathlib import Path
from datetime import datetime, timezone
import json, math, gzip, hashlib, sys, importlib.util, time, ast
from collections import Counter
import numpy as np

ROOT=Path(__file__).resolve().parent; BASE=ROOT.parent
OLD=BASE/'Daily Equity Controls Audit 2026-09-29'
CACHE=BASE.parent/'EA store/data/evidence-cache/v1'
sys.path.insert(0,str(OLD))
from simulate import run, specs, clock, FIELDS
from payout_followup import lifecycle, summarize, CASES, DAY

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(name,x):(ROOT/name).write_text(json.dumps(x,indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def epoch(s):return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()

modspec=importlib.util.spec_from_file_location('native_orders',BASE/'FTMO Fourteen EA Study 2026-09-27/prepare.py')
parser=importlib.util.module_from_spec(modspec);modspec.loader.exec_module(parser)
def read_report(p):
    raw=gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
    for enc in ('utf-16','utf-8-sig','cp1252'):
        try:s=raw.decode(enc)
        except UnicodeError:continue
        if 'Initial Deposit' in s:return s
    raise ValueError(f'Cannot decode native report {p}')
parser.orders.__globals__['_read_report']=read_report
tree=ast.parse((BASE.parent/'EA store/app/mt5_evidence_jobs.py').read_text(encoding='utf-8-sig'))
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_native_trades')
exec(compile(ast.Module(body=[node],type_ignores=[]),'native_trade_parser','exec'),parser.ns)

receipts=[]
def audited_rows(raw, report, source, key, symbol):
    orders=parser.orders(report); rows=[]
    contract=100 if symbol=='XAUUSD' else 1
    for t in raw:
        op,cl=epoch(t['open_time']),epoch(t['close_time'])
        match=orders.get((op,t['symbol'],t['side']),[])
        assert len(match)==1,(key,t['number'],len(match))
        sl=match[0]['stop'];side=1 if t['side']=='Long' else -1
        assert sl>0 and side*(t['open_price']-sl)>0
        assert abs(t['gross_profit']+t['commission']+t['swap']-t['net_profit'])<.03
        implied=side*(t['close_price']-t['open_price'])*contract*t['volume']
        assert abs(implied-t['gross_profit'])<max(.05,abs(implied)*.005),(key,t['number'],implied,t['gross_profit'])
        rows.append(dict(t,key=key,symbol=symbol,op=op,cl=cl,stop=sl,contract=contract,
            unit_risk=abs(t['open_price']-sl)*contract,unit_gross=t['gross_profit']/t['volume'],
            unit_comm=t['commission']/t['volume'],unit_swap=t['swap']/t['volume'],news=False,ftmo=True))
    assert len({(r['op'],r['side']) for r in rows})==len(rows)
    receipts.append(dict(key=key,trades=len(rows),source=str(source),source_sha=sha(source),report=str(report),report_sha=sha(report)))
    return rows

def cache_rows(slug,mode,key,symbol):
    src=CACHE/'products'/slug/mode/'1y.trades.json'
    rep=CACHE/'source-runs'/slug/mode/'1y.htm'
    cached=read(src);native=parser.ns['_native_trades'](rep,key)
    assert len(cached)==len(native)
    for a,b in zip(cached,native):
        assert all(a[k]==b[k] for k in ('open_time','close_time','side','volume','open_price','close_price','net_profit'))
    return audited_rows(native,rep,src,key,symbol)

def prepare():
    audit=read(OLD/'recent-AUDIT.json');z=np.load(OLD/'recent-prepared.npz')
    origin=audit['start'];end=int(epoch('2026-09-01T00:00:00')//60)-1
    length=end-origin+1
    data={k:z[k][:,:length] for k in ('prices','opens','fresh')}
    current=read(OLD/'recent-ROWS.json')
    assert len(current)==972 and len({r['key'] for r in current})==13
    basekeys=['gold-overnight-value-area','nasdaq-overnight','xau-rsi-vwap','nasdaq-5m-candle-momentum']
    core=[r for r in current if r['key'] in basekeys+['ema3']]
    high=[r for r in current if r['key'] in basekeys]
    high+=cache_rows('orb-volume-profile-high-win-0-75r','standard','orb-vp-075r','XAUUSD')
    high+=cache_rows('ema3','safe','ema3-safe','XAUUSD')
    high+=cache_rows('xau-squeeze-momentum-standard','safe','xau-squeeze-safe','XAUUSD')
    research=BASE/'US100 H1 ORB ADX RR1 Research 2026-09-23'
    src=research/'native/trades.json';rr=read(src)['H1-RR1-adx25'];raw=[]
    for i,t in enumerate(rr):
        raw.append(dict(number=i+1,symbol='USTEC',side='Long' if t['side']=='buy' else 'Short',
            open_time=t['entry'].replace('.','-',2).replace(' ','T'),close_time=t['exit'].replace('.','-',2).replace(' ','T'),
            open_price=t['entry_price'],close_price=t['exit_price'],volume=t['vol'],net_profit=t['net'],
            commission=t['comm'],swap=t['swap'],gross_profit=t['net']-t['comm']-t['swap']))
    rep=Path(read(research/'NATIVE_RESULTS.json')['H1-RR1-adx25']['report'])
    if not rep.exists():rep=Path(str(rep)+'.gz')
    high+=audited_rows(raw,rep,src,'us100-h1-orb-rr1-adx25','USTEC')
    keys=sorted({r['key'] for r in current+high});syms=audit['symbols']
    groups={};source_counts={}
    for name,rows in [('Current13',current),('CurrentCore5',core),('HighWin8',high)]:
        rows=sorted([r for r in rows if origin*60<=r['op']<(end+1)*60],key=lambda r:(r['op'],r['key'],r['number']))
        matrix=[]
        for r in rows:
            op=math.ceil(r['op']/60);cl=max(op+1,math.ceil(r['cl']/60))
            matrix.append([op,cl,keys.index(r['key']),syms.index(r['symbol']),r['unit_risk'],r['open_price'],
                r['unit_gross'],r['unit_comm'],r['unit_swap'],1 if r['side']=='Long' else -1,0,1,r['close_price'],r['op']])
        groups[name]=np.asarray(matrix)
        source_counts[name]=dict(Counter(r['key'] for r in rows))
        save(name+'-ROWS.json',rows)
    assert len(source_counts['HighWin8'])==8
    original=z['trades'];clipped=original[(original[:,0]>=origin)&(original[:,13]<(end+1)*60)]
    mapped=clipped.copy()
    for row in mapped:row[2]=keys.index(audit['keys'][int(row[2])])
    assert np.array_equal(mapped,groups['Current13']), 'Current13 reconstruction changed'
    save('SOURCE_AUDIT.json',dict(start=origin,end=end,start_utc=datetime.fromtimestamp(origin*60,timezone.utc).isoformat(),
        end_utc=datetime.fromtimestamp(end*60,timezone.utc).isoformat(),days=(end-origin+1)/DAY,
        keys=keys,source_counts=source_counts,additional_sources=receipts,
        source_current13_sha=sha(OLD/'recent-ROWS.json'),source_price_sha=sha(OLD/'recent-prepared.npz'),
        source_engine_sha=sha(OLD/'simulate.py'),protocol_sha=sha(ROOT/'PROTOCOL.md'),
        current13_matrix_identical_after_key_mapping=True))
    return data,groups,origin,end,keys

def extra_metrics(logs,tr,keys):
    # Exit logs are already chronological; order of simultaneous exits is engine order.
    w=l=mw=ml=0
    for x in logs[:,4]:
        w=w+1 if x>0 else 0;l=l+1 if x<0 else 0;mw=max(mw,w);ml=max(ml,l)
    by={}
    for log in logs:
        key=keys[int(tr[int(log[0]),2])]
        if key not in by:by[key]=dict(trades=0,net=0.,wins=0)
        by[key]['trades']+=1;by[key]['net']+=float(log[4]);by[key]['wins']+=int(log[4]>0)
    return dict(max_win_streak=mw,max_loss_streak=ml,by_ea=by)

def main():
    tic=time.time();data,groups,start,end,keys=prepare();sp=specs();days=clock(start,end)
    cfgs=[dict(name='A loss2 goal4',loss=200,target=400,cap=0),dict(name='B risk2.5 goal4',loss=0,target=400,cap=250)]
    results=[];pathsout=[]
    # Regression against previous full-period result before new comparison.
    z=np.load(OLD/'recent-prepared.npz');a=read(OLD/'recent-AUDIT.json')
    vals,*_=run(z['trades'],z['prices'],z['opens'],z['fresh'],sp,a['start'],a['end'],clock(a['start'],a['end']),True,200,400,0,False,False,False)
    prior=next(x for x in read(OLD/'RESULTS.json') if x['id']=='recent-FTMO13-1-0-A_loss2_goal4')['metrics']
    diff=max(abs(float(v)-prior[f]) for f,v in zip(FIELDS,vals));assert diff<1e-7,diff
    save('REGRESSION.json',dict(max_metric_difference=diff,passed=True))
    first=int(epoch('2025-09-29T00:00:00')//60);starts=list(range(first,end-30*DAY+1,7*DAY))
    for name,tr in groups.items():
        for ci,cfg in enumerate(cfgs):
            for case in CASES if ci==0 else CASES[:2]:
                v,logs,daily,curve=run(tr,data['prices'],data['opens'],data['fresh'],sp,start,end,days,True,
                    cfg['loss'],cfg['target'],cfg['cap'],case['stress'],False,False,case['delay'],0.,0,0,case['haircut'])
                m=dict(zip(FIELDS,map(float,v)))
                m['profit_factor']=m['positive']/m['negative'] if m['negative'] else None
                m['win_rate']=100*m['wins']/m['trades'] if m['trades'] else None
                if m['open_at_end']==0:assert abs(m['balance']-10000.-logs[:,4].sum())<1e-6
                assert np.isfinite(v).all()
                assert np.all(logs[:,5]<=50.+1e-7)
                if cfg['cap']:assert m['max_open_risk']<=cfg['cap']+1e-7
                rid=f'{name}-{ci}-{case["name"].replace(" ","_")}'
                np.savez_compressed(ROOT/(rid+'.npz'),trades=tr,logs=logs,daily=daily,curve=curve)
                result=dict(id=rid,group=name,config=cfg,case=case,metrics=m,**extra_metrics(logs,tr,keys))
                results.append(result);save('RESULTS.json',results)
                d=dict(data,trades=tr)
                paths=[lifecycle(d,sp,days,start,s,min(end,s+180*DAY),cfg,case) for s in starts]
                ps=dict(group=name,config=cfg,case=case,summary=[summarize(paths,h) for h in (60,90,120,180)],paths=paths)
                pathsout.append(ps);save('LIFECYCLE.json',pathsout)
                print(json.dumps(dict(group=name,policy=cfg['name'],case=case['name'],ret=round(m['return_pct'],2),
                    pf=round(m['profit_factor'],3),win=round(m['win_rate'],2),dd=round(m['equity_dd_pct'],2),
                    seconds=round(time.time()-tic,1),h180=ps['summary'][-1]['counts'])),flush=True)
    save('CHECKS.json',dict(regression_max_difference=diff,current13_matrix_parity=True,rows=len(results),
        lifecycle_paths=sum(len(p['paths']) for p in pathsout),source_stop_cash_audits_passed=True,
        closed_balance_reconciliation_passed=True,risk_and_cap_checks_passed=True,all_values_finite=True))

if __name__=='__main__':main()
