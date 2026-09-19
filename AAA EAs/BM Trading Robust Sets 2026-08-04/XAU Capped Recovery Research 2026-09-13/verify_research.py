from pathlib import Path
from collections import defaultdict
from datetime import datetime
import csv,hashlib,json,math,unittest

ROOT=Path(__file__).resolve().parent
def read(p):
    with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def close(a,b,tol=.02):assert abs(float(a)-float(b))<=tol,(a,b,tol)
def planned_stop(balance,target,lot,weighted,swap=0):return (target-balance-swap+100*weighted)/(100*lot)

class RiskArithmetic(unittest.TestCase):
    def test_initial_stop_includes_commission(self):
        sl=planned_stop(2999.94,2940,.01,3000*.01)
        self.assertAlmostEqual(sl,2940.06)
    def test_equal_additions_tighten_stop(self):
        first=planned_stop(2999.94,2940,.01,30)
        second=planned_stop(2999.88,2940,.02,30+29.9)
        third=planned_stop(2999.82,2940,.03,30+29.9+29.8)
        self.assertLess(first,second);self.assertLess(second,third)
        self.assertAlmostEqual(third,2970.06)
    def test_daily_budget_is_tighter_after_loss(self):
        # After a $60 loss, a $90 daily limit leaves only $30 for next basket.
        target=max(2940-60,3000-90)
        self.assertEqual(target,2910)
    def test_swap_cost_tightens_sl(self):
        self.assertGreater(planned_stop(2999.94,2940,.01,30,-5),planned_stop(2999.94,2940,.01,30,0))
    def test_capped_doubling_not_infinite(self):
        self.assertAlmostEqual(sum(.01*2**i for i in range(3)),.07)

def verify(r):
    tag=r['tag'];p=r['parameters'];folder=ROOT/'Audit'
    assert hashlib.sha256((ROOT/'EA'/'XAU Capped Recovery.mq5').read_bytes()).hexdigest()==r['source_sha256']
    if r.get('native_report_sha256'):
        assert hashlib.sha256((ROOT/'Backtest Reports'/f'{tag}.htm').read_bytes()).hexdigest()==r['native_report_sha256']
    else:
        assert r.get('native_optimization')
    ev=read(folder/f'{tag}-events.csv');ds=read(folder/f'{tag}-deals.csv')
    ts=json.loads((folder/f'{tag}-trades.json').read_text());bs=json.loads((folder/f'{tag}-baskets.json').read_text())
    trading=[d for d in ds if d['symbol']=='XAUUSD']
    close(sum(sum(float(d[k]) for k in ('profit','commission','swap','fee')) for d in trading),r['net_profit'],.06)
    close(3000+r['net_profit'],r['final_balance'],.06)
    assert len(ts)==r['trades']
    for t in ts:
        close(t['volume'],p['InpLot']*p['InpMultiplier']**t['leg_index'],1e-7)
        close(t['profit'],100*t['volume']*(t['close_price']-t['open_price']),.02)
        close(t['net'],t['profit']+t['commission']+t['swap']+t['fee'])
        assert t['leg_index']<p['InpMaxLegs']
    bybasket=defaultdict(list)
    for t in ts:bybasket[t['basket']].append(t)
    previous_end=None;rolling=3000.;milestone=None
    for b in bs:
        g=bybasket[b['basket']]
        assert len(g)<=p['InpMaxLegs']
        if previous_end:assert b['open_time']>=previous_end
        previous_end=b['close_time'];rolling+=b['net']
        close(sum(t['net'] for t in g),b['net'])
        close(rolling,b['end_balance'],.06)
        if b['reason']!='test_end' and rolling>=6000 and milestone is None:milestone=b['close_time']
    assert milestone==r['first_flat_6000'],(tag,'milestone mismatch',milestone,r['first_flat_6000'])
    assert int(float(r['summary']['max_legs']))<=p['InpMaxLegs']
    assert r['max_lots']<=sum(p['InpLot']*p['InpMultiplier']**i for i in range(p['InpMaxLegs']))+1e-8
    locks=set();fills={};last_stop={};stop_budget_overshoot=[];fatal_events=[]
    for e in ev:
        kind=e['event'];bid=int(e['basket']);n=int(e['legs']);day=e['day']
        if kind=='daily_loss_lock':locks.add(day)
        if kind=='buy_request':
            assert day not in locks
            close(e['volume'],p['InpLot']*p['InpMultiplier']**n,1e-7)
            close(e['price'],e['ask'],1e-7)
            if n:
                close(e['trigger'],float(e['first_entry'])-float(e['gap'])*n,1e-7)
                assert float(e['ask'])<=float(e['trigger'])+1e-7
            else:
                assert int(e['positions'])==0
                if p['InpDailyProfit']>0:assert float(e['balance'])-float(e['day_start_balance'])<p['InpDailyProfit']
        if kind=='buy_filled':
            fills[(bid,n-1)]=e
            if bid in last_stop:assert float(e['common_sl'])>=last_stop[bid]-1e-6
            last_stop[bid]=float(e['common_sl'])
        if kind=='basket_closed' and float(e['basket_pnl'])<-p['InpBasketLoss']-.05:
            stop_budget_overshoot.append({'time':e['time'],'net':float(e['basket_pnl']),'overshoot':-float(e['basket_pnl'])-p['InpBasketLoss']})
        if kind=='stop_sync_failed':fatal_events.append(e)
        close(float(e['equity'])-float(e['basket_start_balance']),e['basket_pnl'])
        close(float(e['equity'])-float(e['day_start_balance']),e['daily_pnl'])
    assert len(fills)==len(ts),(tag,'missing fill events')
    for failure in fatal_events:
        closures=[e for e in ev if e['event']=='basket_closed' and e['basket']==failure['basket'] and e['time']>=failure['time']]
        assert closures and int(closures[0]['positions'])==0,(tag,'failed protection did not flatten basket',failure)
        assert not any(e['event']=='buy_filled' and e['basket']==failure['basket'] and e['time']>failure['time'] for e in ev),(tag,'added after stop-update failure')
    for t in ts:
        e=fills[(t['basket'],t['leg_index'])];close(e['price'],t['open_price'],1e-7);close(e['volume'],t['volume'],1e-7)
    # Fixed-path cost sensitivity, not a native rerun: an additional entry spread,
    # another copy of commission + negative swap, and $0.50/oz at entry and exit.
    extra_spread=sum((float(fills[(t['basket'],t['leg_index'])]['ask'])-float(fills[(t['basket'],t['leg_index'])]['bid']))*100*t['volume'] for t in ts)
    extra_commission=-sum(min(t['commission'],0) for t in ts)
    extra_swap=-sum(min(t['swap'],0) for t in ts)
    extra_slippage=sum(2*.50*100*t['volume'] for t in ts)
    stress=r['net_profit']-extra_spread-extra_commission-extra_swap-extra_slippage
    out={'tag':tag,'reused_from':r.get('reused_from'),'passed':True,'native_path_reconciled':True,'fill_rules_checked':len(ts),
         'observed_stop_overshoots':len(stop_budget_overshoot),'largest_stop_overshoot':max((x['overshoot'] for x in stop_budget_overshoot),default=0),
         'stop_sync_failures':len(fatal_events),'failed_stop_updates_all_flattened':True,'fixed_path_cost_stress_net':round(stress,2),
         'extra_spread_cost':round(extra_spread,2),'extra_commission':round(extra_commission,2),'extra_swap':round(extra_swap,2),'extra_slippage':round(extra_slippage,2)}
    return out

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(RiskArithmetic)
    passed=unittest.TextTestRunner(verbosity=2).run(suite)
    assert passed.wasSuccessful()
    results=[verify(json.loads(f.read_text())) for f in sorted((ROOT/'Runs').glob('*.json'))]
    (ROOT/'verification.json').write_text(json.dumps({'unit_tests':passed.testsRun,'results':results},indent=2),encoding='utf-8')
    print(json.dumps({'result_records_verified':len(results),'unique_native_runs_verified':sum(not r['reused_from'] for r in results),'stop_sync_failures':sum(r['stop_sync_failures'] for r in results)},indent=2))
