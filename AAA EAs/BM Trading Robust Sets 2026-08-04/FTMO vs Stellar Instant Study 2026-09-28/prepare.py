"""Audit exact current signal ledger and build minute-level per-lot equity paths."""
from pathlib import Path
import importlib.util, json, hashlib, math, gzip
from datetime import datetime, timezone
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
OLD=BASE/'FTMO Fourteen EA Study 2026-09-27'
CACHE=BASE.parent/'EA store/data/evidence-cache/v1'
BEGIN=int(datetime(2025,9,27,tzinfo=timezone.utc).timestamp())
END=int(datetime(2026,9,25,tzinfo=timezone.utc).timestamp())
SYMBOLS=['XAUUSD','USTEC','USDJPY']
CORE=['gold-overnight-value-area','nasdaq-5m-candle-momentum','nasdaq-overnight','usdjpy-london-open-momentum']
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def dt(v):return datetime.fromisoformat(v).replace(tzinfo=timezone.utc).timestamp()
def main():
    spec=importlib.util.spec_from_file_location('old_audit',OLD/'prepare.py')
    prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)
    pkg=read(BASE/'FTMO Thirteen EA Deployment 2026-09-27/PACKAGE.json')
    frozen=read(OLD/'FROZEN.json');data=read(OLD/'prepared.json')
    keys=[e['slug'] for e in pkg['entries']];assert len(keys)==13 and 'news-pulse-xau' not in keys
    meta=read(CACHE/'source-runs/nasdaq-5m-candle-momentum/dynamic/1y.meta.json')
    selection=read(BASE/'Nasdaq 5M DI ATR Deployment 2026-09-28/SELECTION.json')
    assert meta['expert_sha256']==selection['expert_sha'] and meta['settings_sha256']==selection['settings_sha']
    report=CACHE/'source-runs/nasdaq-5m-candle-momentum/dynamic/1y.htm'
    assert sha(report)==meta['source_report_sha256']
    orders=prep.orders(report)
    nas=[]
    for r in read(CACHE/'products/nasdaq-5m-candle-momentum/dynamic/1y.trades.json'):
        op=dt(r['open_time']);cl=dt(r['close_time']);found=orders[(op,r['symbol'],r['side'])];assert len(found)==1
        stop=found[0]['stop'];sgn=1 if r['side']=='Long' else -1
        # Entry slippage changes fill-to-stop risk; use the native order SL, not an invented exact 0.60% fill distance.
        assert sgn*(r['open_price']-stop)>0 and found[0]['target']==0, (r['number'],stop,found)
        nas.append(dict(r,key='nasdaq-5m-candle-momentum',op=op,cl=cl,news=False,stop=stop,
                        unit_risk=abs(r['open_price']-stop),unit_gross=r['gross_profit']/r['volume'],
                        unit_comm=r['commission']/r['volume'],unit_swap=r['swap']/r['volume']))
    data['rows']['nasdaq-5m-candle-momentum']=nas
    mismatches=[]
    for p in pkg['entries']:
        src=selection if p['slug']=='nasdaq-5m-candle-momentum' else next(x for x in frozen['entries'] if x['slug']==p['slug'])
        for k,v in src['inputs'].items():
            if k in p['inputs'] and str(v)!=str(p['inputs'][k]) and k not in ['InpRiskPercent','InpFixedRiskMoney','InpAdaptivePortfolioControls','InpWriteAudit']:
                mismatches.append([p['slug'],k,v,p['inputs'][k]])
    assert not mismatches,mismatches
    rows=[r for key in keys for r in data['rows'][key] if BEGIN<=r['op']<END and r['cl']<END]
    rows.sort(key=lambda r:(r['op'],r['key'],r['number']))
    rates={};rateaudit={}
    for sym in SYMBOLS:
        frame=pd.read_csv(ROOT/'data'/f'{sym}-M1.csv.gz')
        assert frame.time.is_monotonic_increasing and not frame.time.duplicated().any()
        a=frame.to_numpy();rates[sym]=a
        rateaudit[sym]=dict(bars=len(a),start=int(a[0,0]),end=int(a[-1,0]),median_spread=float(np.median(a[:,6])),
                            max_gap_minutes=float(np.max(np.diff(a[:,0]))/60))
    # Columns: open minute,close minute,key,symbol,unit initial risk,entry price,unit gross,
    # native commission,native swap,path offset,path length,side,known-news,quickstrike
    matrix=[];paths_close=[];paths_low=[];gaps=[];reconcile=[]
    events=np.array(sorted({p['epoch'] for p in data['placements']}))
    offset=0
    for rid,r in enumerate(rows):
        sym=r['symbol'];a=rates[sym];sgn=1 if r['side']=='Long' else -1;contract=100 if sym=='XAUUSD' else 100000 if sym=='USDJPY' else 1
        op=int(math.ceil(r['op']/60));cl=max(op+1,int(math.ceil(r['cl']/60)))
        stamps=np.arange(op,cl)*60
        idx=np.searchsorted(a[:,0],stamps,side='right')-1
        assert np.min(idx)>=0
        chosen=a[idx]
        stale=stamps-chosen[:,0]
        # Stale weekend bars are carried forward; quantify all missing timestamps.
        gaps.append(int(np.sum(stale>=60)))
        point=.001 if sym in ('XAUUSD','USDJPY') else .01
        spread=chosen[:,6]*point
        close=chosen[:,4]+(spread if sgn<0 else 0)
        bad=chosen[:,3] if sgn>0 else chosen[:,2]+spread
        # Last minute can contain quotes after the recorded exit; do not use its extremes.
        close[-1]=r['close_price'];bad[-1]=min(r['open_price'],r['close_price']) if sgn>0 else max(r['open_price'],r['close_price'])
        if r['op']%60:
            bad[0]=min(r['open_price'],close[0]) if sgn>0 else max(r['open_price'],close[0])
        conv=close if sym=='USDJPY' else 1
        cp=sgn*(close-r['open_price'])*contract/conv
        lp=sgn*(bad-r['open_price'])*contract/(bad if sym=='USDJPY' else 1)
        cp[-1]=r['unit_gross'];lp=np.minimum(lp,cp)
        # A native position cannot generally persist far below its original SL; audit, don't silently clamp.
        reconcile.append(dict(id=rid,ea=r['key'],min_r=float(lp.min()/r['unit_risk']),
                              native_cash_error=abs(r['gross_profit']+r['commission']+r['swap']-r['net_profit']),
                              duration_minutes=cl-op,missing_minutes=gaps[-1]))
        near=any(np.min(np.abs(events-t))<=300 for t in (r['op'],r['cl'])) if len(events) else False
        matrix.append([op,cl,keys.index(r['key']),SYMBOLS.index(sym),r['unit_risk'],r['open_price'],r['unit_gross'],r['unit_comm'],r['unit_swap'],offset,len(cp),sgn,int(near),int(r['cl']-r['op']<30)])
        paths_close.append(cp.astype(np.float32));paths_low.append(lp.astype(np.float32));offset+=len(cp)
    mat=np.asarray(matrix,dtype=np.float64)
    np.savez_compressed(ROOT/'prepared.npz',trades=mat,close=np.concatenate(paths_close),low=np.concatenate(paths_low))
    save(ROOT/'rows.json',rows)
    excluded={k:sum(not (BEGIN<=r['op']<END and r['cl']<END) for r in data['rows'][k]) for k in keys}
    audit=dict(start=BEGIN,end=END,keys=keys,core=CORE,count=len(rows),counts={k:sum(r['key']==k for r in rows) for k in keys},
               nasdaq_version=selection['version'],nasdaq_source=meta,paths_minutes=offset,rates=rateaudit,
               excluded_boundary_rows=excluded,known_calendar_events=len(events),known_news_trades=int(mat[:,12].sum()),
               quickstrike_trades=int(mat[:,13].sum()),max_native_cash_error=max(x['native_cash_error'] for x in reconcile),
               minimum_r=min(x['min_r'] for x in reconcile),worst_path_rows=sorted(reconcile,key=lambda x:x['min_r'])[:20],
               source_hashes={str(p):sha(p) for p in [ROOT/'PROTOCOL.md',OLD/'prepared.json',OLD/'DATA_AUDIT.json',report,
                   CACHE/'products/nasdaq-5m-candle-momentum/dynamic/1y.trades.json',BASE/'FTMO Thirteen EA Deployment 2026-09-27/PACKAGE.json']})
    save(ROOT/'AUDIT.json',audit)
    print(json.dumps({k:audit[k] for k in ['count','counts','paths_minutes','minimum_r','known_news_trades','quickstrike_trades','excluded_boundary_rows','rates']}),flush=True)
if __name__=='__main__':main()
