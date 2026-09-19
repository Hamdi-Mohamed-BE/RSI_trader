"""Independent audit of the raw native reports, fills, rules and observer replay.

No terminal connection, price download, order submission or strategy mutation.
"""
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import csv, hashlib, json, math

ROOT=Path(__file__).resolve().parent
FMT='%Y.%m.%d %H:%M:%S'
def readcsv(p):
    with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def close(a,b,tol=.011):
    assert abs(float(a)-float(b))<=tol,(a,b,tol)
def money(d):return sum(float(d[k]) for k in ('profit','commission','swap','fee'))
def stamp(s):return datetime.strptime(s,FMT)
def save(p,obj):p.write_text(json.dumps(obj,indent=2,allow_nan=False),encoding='utf-8')

def audit(r):
    tag=r['tag'];folder=ROOT/'Audit'
    ev=readcsv(folder/f'{tag}-events.csv');deals=readcsv(folder/f'{tag}-deals.csv')
    replay=readcsv(ROOT/'Audit Replay'/'Audit'/f'{tag}-events.csv')
    replay_deals=readcsv(ROOT/'Audit Replay'/'Audit'/f'{tag}-deals.csv')
    # Additional logging must not change a single execution or cash ledger cell.
    assert deals==replay_deals,(tag,'observer changed executions')
    checks=['observer replay has identical complete deal ledger']
    ts=json.loads((folder/f'{tag}-trades.json').read_text())
    baskets=json.loads((folder/f'{tag}-baskets.json').read_text())
    trade_deals=[d for d in deals if d['symbol']=='XAUUSD']
    deposit=[d for d in deals if int(d['type'])==2]
    assert len(deposit)==1
    close(deposit[0]['profit'],3000)
    close(3000+sum(money(d) for d in trade_deals),r['final_balance'])
    close(sum(t['net'] for t in ts),r['net_profit'])
    close(sum(b['net'] for b in baskets),r['net_profit'])
    for field in ('commission','swap'):
        close(sum(float(d[field]) for d in trade_deals),r[field])
    assert len(ts)==r['trades']
    wins=[t['net'] for t in ts if t['net']>0];loss=[t['net'] for t in ts if t['net']<0]
    close(100*len(wins)/len(ts),r['net_win_rate'])
    close(sum(wins)/-sum(loss),r['net_pf'])
    checks.append('deposit, trade count, gross/net P&L, fees, win rate and PF reconcile')
    bybasket=defaultdict(list)
    for t in ts:
        bybasket[t['basket']].append(t)
        expected=t['volume']*100*(t['close_price']-t['open_price'])
        close(expected,t['profit'],.02)
        close(t['profit']+t['commission']+t['swap']+t['fee'],t['net'])
    prev_close=None
    for bid,group in sorted(bybasket.items()):
        group.sort(key=lambda t:t['leg_index'])
        for idx,t in enumerate(group):
            assert t['leg_index']==idx
            close(t['volume'],.02*2**idx,1e-8)
        start=min(t['open_time'] for t in group)
        if prev_close:assert start>=prev_close
        prev_close=max(t['close_time'] for t in group)
    checks.append('every leg matches 100 oz/lot price P&L and exact doubling; baskets do not overlap')
    requests=defaultdict(list);fills=[];capped=set();closed=[]
    for e in ev:
        kind=e['event'];day=e['day'];n=int(e['legs'])
        if kind=='buy_request':
            close(e['quote'],e['ask'],1e-8)
            close(e['lots'],.02*2**n,1e-8)
            if n:
                close(e['trigger'],float(e['first_entry'])-10*n,1e-8)
                assert float(e['ask'])<=float(e['trigger'])+1e-8
            else:
                assert day not in capped
                assert float(e['daily_cash_pnl'])<300
                assert int(e['positions'])==0
            requests[e['basket']].append(e)
        elif kind=='buy_filled':
            request=requests[e['basket']][-1]
            close(e['lots'],request['lots'],1e-8)
            assert int(e['legs'])==int(request['legs'])+1
            fills.append(e)
        elif kind=='exit_trigger':
            expected=float(e['first_entry'])+(10 if n==1 else 0)
            close(e['trigger'],expected,1e-8)
            close(e['quote'],e['bid'],1e-8)
            assert float(e['bid'])>=expected-1e-8
        elif kind=='basket_closed':
            assert int(e['positions'])==0
            closed.append(e)
        elif kind=='daily_target':
            assert float(e['daily_cash_pnl'])>=300
            assert int(e['positions'])==0
            capped.add(day)
        assert kind not in ('unsupported','unexpected_flat','close_error'),(tag,e)
        close(float(e['balance'])-float(e['day_start_balance']),e['daily_cash_pnl'])
    assert len(fills)==len(ts)
    lookup={(t['basket'],t['leg_index']):t for t in ts}
    for f in fills:
        t=lookup[(int(f['basket']),int(f['legs'])-1)]
        close(f['fill'],t['open_price'],1e-8)
        close(f['lots'],t['volume'],1e-8)
    checks.append('ask-based add triggers, actual fills, bid-based exits and daily $300 flat-only cutoff verified')
    running=3000.;flat_milestone=None
    for b in baskets:
        running+=b['net']
        matches=[e for e in closed if int(e['basket'])==b['basket']]
        if matches:
            assert len(matches)==1
            close(matches[0]['balance'],running)
            if running>=6000 and flat_milestone is None:flat_milestone=matches[0]['time']
    assert flat_milestone==r['first_flat_6000']
    native_so=[d for d in trade_deals if int(d['reason'])==6]
    assert native_so and native_so[0]['time']==r['first_stopout']
    insolvencies=[e for e in replay if e['event']=='observed_nonpositive_equity']
    assert len(insolvencies)==1
    insolvency=insolvencies[0]
    assert float(insolvency['equity'])<=0 and float(insolvency['total_lots'])>0
    # Check observed equity independently at the first nonpositive quote.
    live=[t for t in ts if t['open_time']<=insolvency['time']<=t['close_time']]
    marked_profit=sum(round(100*t['volume']*(float(insolvency['bid'])-t['open_price']),2) for t in live)
    open_swap=sum(t['swap'] for t in live)
    close(float(insolvency['balance'])+marked_profit+open_swap,insolvency['equity'],.05)
    assert insolvency['time']<=r['first_stopout']
    cutoff_success=bool(flat_milestone and flat_milestone<insolvency['time'])
    checks.append('flat $6000 milestone independently reconstructed and compared with first nonpositive equity, not just delayed stop-out')
    checkpoints=[e for e in replay if e['event']=='dd_over_100_record']
    maximum_record=max(float(e['detail'].split('dd_pct=')[1]) for e in checkpoints)
    close(maximum_record,r['tick_observed_max_equity_dd_pct'],1e-6)
    # Native report's real-tick percentage covers requested history, not necessarily the shortened executed interval.
    assert any('real ticks begin from 2026.01.01' in s for s in r['quality_journal'])
    quality='real ticks (native report 100%)' if r['actual_first_tick']>='2026.01.01' else 'generated ticks: execution ended before available real ticks begin 2026-01-01'
    s=r['summary']
    assert float(s['contract_size'])==100 and float(s['leverage'])==2000
    assert float(s['margin_mode'])==2 and float(s['stopout_mode'])==0 and float(s['stopout'])==0
    close(r['max_total_lots'],.02*(2**r['max_legs']-1),1e-8)
    checks.append('native account specification, exposure, per-tick DD and actual tick coverage checked')
    out={'period':r['period'],'checks':checks,'check_count':len(checks),'passed':True,
         'native_stopout_exit_deals':len(native_so),
         'residual_test_end_exit_deals':sum('end of test' in d['comment'].lower() for d in trade_deals),
         'actual_execution_tick_quality':quality,
         'first_nonpositive_equity':insolvency['time'],'equity_at_first_nonpositive':float(insolvency['equity']),
         'elapsed_days_to_nonpositive_equity':(stamp(insolvency['time'])-stamp(r['actual_first_tick'])).total_seconds()/86400,
         'secured_3000_before_nonpositive_equity':cutoff_success,
         'native_stopout_delay_seconds':(stamp(r['first_stopout'])-stamp(insolvency['time'])).total_seconds(),
         'first_flat_6000_balance':next((float(e['balance']) for e in closed if e['time']==flat_milestone),None),
         'native_dd_pct':r['max_equity_dd_pct'],'per_tick_dd_pct':r['tick_observed_max_equity_dd_pct']}
    print(json.dumps(out,indent=2))
    return out

if __name__=='__main__':
    original=json.loads((ROOT/'results.json').read_text())
    assert hashlib.sha256((ROOT/'EA'/'XAU Doubling Grid Raw.mq5').read_bytes()).hexdigest()==original['source_sha256']
    results=[audit(r) for r in original['rows']]
    save(ROOT/'verification.json',{'status':'PASS_WITH_MODEL_LIMITATIONS','rows':results,
         'limitations':['Native stop-out lags first nonpositive equity in these runs; no recovery after insolvency is accepted as safe survival.',
                        'Static native 1:2000 leverage; historical equity-based and high-margin broker changes are not reconstructed.',
                        'Three older executed intervals use generated ticks, not a complete historical real-tick record.',
                        'No negative-balance protection or withdrawals; native negative balances do not establish personal debt.']})
