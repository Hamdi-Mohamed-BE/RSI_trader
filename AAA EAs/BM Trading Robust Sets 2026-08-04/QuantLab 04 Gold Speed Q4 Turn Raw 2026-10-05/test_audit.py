"""Regression tests for native hedged mapping and cost attribution, independent of results."""
import run
def d(deal,pos,entry,kind,time,volume,price,gross=0,commission=0):
 return dict(deal=deal,position_id=pos,order=deal,entry=entry,type=kind,epoch=time,volume=volume,price=price,gross=gross,commission=commission,swap=0,fee=0)
deals=[d(1,10,0,0,1,1,100,commission=-.5),d(2,20,0,0,2,2,100,commission=-1),d(3,20,1,1,3,1,98,gross=-2),d(4,10,1,1,4,1,101,gross=1),d(5,20,1,1,5,1,103,gross=3)]
def e(pos,op,cl,v,cp,net,gross,commission):
 return dict(position_id=pos,module='A_SPEED' if pos==10 else 'B_Q4',open_epoch=op,close_epoch=cl,volume=v,open_price=100,close_price=cp,net_profit=net,gross_profit=gross,commission=commission,swap=0,fee=0,initial_sl=99,initial_tp=0,requested_risk=100,actual_risk=v)
export=[e(10,1,4,1,101,.5,1,-.5),e(20,2,5,2,100.5,0,1,-1)]
trades,ledger=run.reconstruct(deals,export)
assert [t['position_id'] for t in trades]==[10,20]
assert [t['net_profit'] for t in trades]==[.5,0] and ledger[-1]['balance']==10000.5
assert trades[1]['close_price']==100.5 and trades[1]['last_exit_deal']==5
for bad in [deals[1:],deals+[deals[-1]]]:
 try:run.reconstruct(bad,export)
 except (AssertionError,KeyError):pass
 else:raise AssertionError('Missing entry/duplicate deal accepted')
print('Exact hedged mapping, partial exits, out-of-order closes, unequal lots, entry costs, native cash balance and invalid-input rejection: PASS')

