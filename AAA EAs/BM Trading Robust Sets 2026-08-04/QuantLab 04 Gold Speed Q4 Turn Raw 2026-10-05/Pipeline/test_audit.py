"""Deterministic ledger and calendar regressions, no market/terminal access."""
import audit as a
import numpy as np
raw=a.raw
def d(deal,pos,entry,kind,time,volume,price,gross=0,commission=0):return dict(deal=deal,position_id=pos,order=deal,entry=entry,type=kind,epoch=time,volume=volume,price=price,gross=gross,commission=commission,swap=0,fee=0)
def e(pos,op,cl,v,cp,net,gross,commission):return dict(position_id=pos,module='A_SPEED' if pos==10 else 'B_Q4',open_epoch=op,close_epoch=cl,volume=v,open_price=100,close_price=cp,net_profit=net,gross_profit=gross,commission=commission,swap=0,fee=0,initial_sl=99,initial_tp=0,requested_risk=100,actual_risk=v)
deals=[d(1,10,0,0,1,1,100,commission=-.5),d(2,20,0,0,2,2,100,commission=-1),d(3,20,1,1,3,1,98,gross=-2),d(4,10,1,1,4,1,101,gross=1),d(5,20,1,1,5,1,103,gross=3)]
export=[e(10,1,4,1,101,.5,1,-.5),e(20,2,5,2,100.5,0,1,-1)]
trades,ledger=raw.reconstruct(deals,export)
assert [t['position_id'] for t in trades]==[10,20] and [t['net_profit'] for t in trades]==[.5,0] and ledger[-1]['balance']==10000.5
for bad in [deals[1:],deals+[deals[-1]]]:
    try:raw.reconstruct(bad,export)
    except (AssertionError,KeyError):pass
    else:raise AssertionError('Invalid native deal stream accepted')
r=dict(start='2026.01.01',end_exclusive='2026.01.05',ledger=[dict(time='2026-01-02T12:00:00',cash_flow=-1),dict(time='2026-01-04T12:00:00',cash_flow=2)],stats={'net':1})
dates,ret=a.daily(r);assert len(dates)==4 and ret[0]==0 and ret[1]==-.0001 and ret[2]==0 and abs(ret[3]-2/9999)<1e-12
assert abs(np.prod(1+ret)*10000-10001)<1e-8
for m in 'ABC':
    assert set(a.n.RAWCASE[m])==set(a.n.FIELDS)
    for stage in a.n.STAGES[m]:
        for patch in a.n.patches(stage,m):assert set(patch)<=set(a.n.FIELDS)
    neigh,axes=a.n.neighbours(m,a.n.RAWCASE[m]);assert len(axes)>=2 and len(neigh)>=9
assert a.n.to_date('2024.03.29')=='2024.03.29'
sample=dict(symbol='XAUUSD',start='2026.01.01',end_exclusive='2026.01.05',stats={'trades':1},native={'sharpe_ratio':.1,'history_quality':'100% real ticks'})
rows=a.summary_rows({'1Y':sample},dict(sample,symbol='XAGUSD'))
assert rows[0]['end_exclusive']=='2026.01.05' and rows[1]['symbol']=='XAGUSD' and rows[1]['window']=='XAG1Y'
print('Exact hedged/partial/unequal-volume costs, duplicate rejection, full-calendar cash returns, search axes and end-exclusive dates: PASS')
