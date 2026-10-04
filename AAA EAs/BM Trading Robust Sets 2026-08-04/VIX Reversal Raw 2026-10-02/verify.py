"""Separate array-based reconstruction; does not import the primary engine."""
from pathlib import Path
import json, math
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent

def independently_rebuild(d,start,end,bps):
    dates=d.index;op=d.open.to_numpy();hi=d.high.to_numpy();lo=d.low.to_numpy();cl=d.close.to_numpy()
    vc=d.v_close.to_numpy();vl=d.v_low.to_numpy();n=len(d)
    mean=np.array([np.mean(vc[i-20:i]) if i>=20 else np.nan for i in range(n)])
    prev=np.r_[cl[0],cl[:-1]];tr=np.maximum(hi-lo,np.maximum(abs(hi-prev),abs(lo-prev)))
    atr=np.full(n,np.nan);atr[13]=np.mean(tr[:14])
    for i in range(14,n):atr[i]=(13*atr[i-1]+tr[i])/14
    signal=np.zeros(n,dtype=bool);arm=None;oldspike=False
    for i in range(n):
        if arm is not None:
            if 0<i-arm<=5 and vc[i]<vl[i-1] and vc[i]<vc[i-1]:signal[i]=True;arm=None
            elif i-arm>=5:arm=None
        spike=vc[i]>=25 and vc[i]>=1.25*mean[i]
        if spike and not oldspike:arm=i
        oldspike=spike
    np.testing.assert_allclose(atr,d.atr,equal_nan=True,atol=1e-9)
    cash=10000.;position=None;due=None;result=[];equity=[];fee=bps/10000
    ids=np.where((dates>=pd.Timestamp(start))&(dates<pd.Timestamp(end)))[0]
    def exit_candidate(i,p,due_reason):
        if op[i]<=p['stop']:return op[i],'gap_stop'
        if op[i]>=p['target']:return p['target'],'gap_target'
        if due_reason:return op[i],due_reason
        if lo[i]<=p['stop']:return p['stop'],'stop'
        if hi[i]>=p['target']:return p['target'],'target'
        return None,None
    for i in ids:
        closed=False
        if position:
            px,why=exit_candidate(i,position,due)
            if why:
                cash+=position['q']*px*(1-fee)
                result.append((position['entry'],i,position['q'],px,why,cash-position['before'],cash))
                position=None;due=None;closed=True
        if not position and not closed and i>ids[0] and signal[i-1]:
            dist=2*atr[i-1];before=cash;q=min(math.floor(before*.01/dist+1e-10),math.floor(before/(op[i]*(1+fee))+1e-10))
            if q>0:
                cash-=q*op[i]*(1+fee);position={'entry':i,'q':q,'stop':op[i]-dist,'target':op[i]+2*dist,'before':before,'mean':mean[i-1]}
                px,why=exit_candidate(i,position,None)
                if why:
                    cash+=q*px*(1-fee);result.append((i,i,q,px,why,cash-before,cash));position=None
        if position:
            if i-position['entry']+1>=10:due='time'
            elif vc[i]<=position['mean']:due='vix_mean'
        equity.append(cash+(position['q']*cl[i] if position else 0))
    return result,equity,signal

def main():
    d=pd.read_csv(ROOT/'data/joined.csv',parse_dates=['date']).set_index('date')
    rows=json.loads((ROOT/'SUMMARY.json').read_text());out=[];total=0
    for r in rows:
        folder=ROOT/'runs'/r['key']
        try:trades=pd.read_csv(folder/'trades.csv')
        except pd.errors.EmptyDataError:trades=pd.DataFrame()
        eq=pd.read_csv(folder/'equity.csv')
        rebuilt,e,signals=independently_rebuild(d,r['start'],r['end_exclusive'],r['execution_bps_each_side'])
        assert len(rebuilt)==len(trades)==r['trades']
        np.testing.assert_allclose(e,eq.equity,atol=1e-6,rtol=0)
        for actual,(entry,exit_,qty,price,reason,profit,balance) in zip(trades.itertuples(),rebuilt):
            assert int(actual.entry_index)==entry and int(actual.exit_index)==exit_ and int(actual.qty)==qty and actual.exit_reason==reason
            assert signals[entry-1] and actual.signal_date<actual.entry_date
            assert abs(actual.exit_price-price)<1e-7 and abs(actual.net_profit-profit)<1e-7 and abs(actual.balance_after-balance)<1e-7
            assert abs(actual.initial_risk-qty*2*d.atr.iloc[entry-1])<1e-7
        # Past signals remain unchanged when all later data is removed.
        _,_,prefix=independently_rebuild(d.iloc[:len(d)-30],r['start'],min(pd.Timestamp(r['end_exclusive']),d.index[-31]+pd.Timedelta(days=1)),r['execution_bps_each_side'])
        assert np.array_equal(signals[:len(prefix)],prefix)
        total+=len(trades);out.append({'key':r['key'],'closed_trades_verified':len(trades),'daily_equity_rows_verified':len(eq),'max_equity_reconstruction_error':float(np.max(abs(np.array(e)-eq.equity.to_numpy()))),'pass':True})
    (ROOT/'VERIFICATION.json').write_text(json.dumps({'independent_array_engine':True,'total_overlapping_closed_trades_verified':total,'runs':out,'all_pass':True},indent=2),encoding='utf-8')
    print('PASS independent reconstruction: '+str(total)+' overlapping closed trades, '+str(len(out))+' runs.')
if __name__=='__main__':main()
