"""Independent rule/ledger audit of native output. Does not create or resimulate fills."""
from collections import Counter
from datetime import datetime
import gzip, json, math, re
import numpy as np
import pandas as pd
import run

ROOT = run.ROOT
DTYPE = np.dtype([(k, '<i8') for k in ('now', 'bar', 'hbar')]+
                 [(k, '<f8') for k in ('r1', 'r2', 'h1', 'h2', 'h3', 'atr', 'hclose', 'ema', 'hm', 'close')]+
                 [(k, '<i4') for k in ('side', 'result', 'long_age', 'short_age')])
assert DTYPE.itemsize == 120


def fields(line):
    return dict(re.findall(r'(\w+)=([^ ]+)', line))


def expected(a, variant):
    side = np.zeros(len(a), dtype=int)
    crossup = (a['h1'] > 0) & (a['h2'] <= 0)
    crossdn = (a['h1'] < 0) & (a['h2'] >= 0)
    if variant in (0, 3):
        buy = (a['hclose'] > a['ema']) & (a['hm'] > 0) & (a['h1'] > a['h2']) & (a['h2'] > a['h3'])
        sell = (a['hclose'] < a['ema']) & (a['hm'] < 0) & (a['h1'] < a['h2']) & (a['h2'] < a['h3'])
        if variant == 0:
            buy &= (a['r2'] <= 40) & (a['r1'] > 40)
            sell &= (a['r2'] >= 60) & (a['r1'] < 60)
    elif variant == 1:
        buy = (a['long_age'] >= 1) & (a['long_age'] <= 8) & (a['r1'] > 30) & crossup
        sell = (a['short_age'] >= 1) & (a['short_age'] <= 8) & (a['r1'] < 70) & crossdn
    else:
        buy, sell = crossup, crossdn
    assert not np.any(buy & sell)
    side[buy] = 1; side[sell] = -1
    return side


def indicator_checks(a):
    """Rebuild RSI and native MACD from closed prices after initialization burn-in."""
    if len(a) <= 1000:return dict(checked_m15_bars=0)
    close=pd.Series(a['close']);fast=close.ewm(span=12,adjust=False).mean();slow=close.ewm(span=26,adjust=False).mean()
    main=fast-slow;hist=(main-main.rolling(9).mean()).to_numpy()
    change=close.diff();gains=change.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    losses=(-change.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    rsi=(100-100/(1+gains/losses)).to_numpy()
    hist_error=float(np.max(np.abs(hist[1000:]-a['h1'][1000:])))
    rsi_error=float(np.nanmax(np.abs(rsi[1000:]-a['r1'][1000:])))
    assert hist_error < max(1e-8,float(np.max(np.abs(a['close'])))*1e-10), ('MACD reconstruction',hist_error)
    assert rsi_error < 1e-7, ('RSI reconstruction',rsi_error)
    checks=dict(checked_m15_bars=len(a)-1000,max_hist_error=hist_error,max_rsi_error=rsi_error)
    h=a[np.r_[True,np.diff(a['hbar'])!=0]]
    if len(h)>2500:
        prices=pd.Series(h['hclose'])
        ema=prices.ewm(span=200,adjust=False).mean().to_numpy()
        hmain=(prices.ewm(span=12,adjust=False).mean()-prices.ewm(span=26,adjust=False).mean()).to_numpy()
        ema_error=float(np.max(np.abs(ema[2500:]-h['ema'][2500:])))
        main_error=float(np.max(np.abs(hmain[2500:]-h['hm'][2500:])))
        tolerance=max(1e-8,float(np.max(np.abs(h['hclose'])))*1e-9)
        assert ema_error<tolerance and main_error<tolerance, ('H1 reconstruction',ema_error,main_error)
        checks.update(checked_h1_bars=len(h)-2500,max_h1_ema_error=ema_error,max_h1_macd_error=main_error)
    return checks


def check(path):
    r = json.loads((path/'run.json').read_text()); a = np.frombuffer(gzip.decompress((path/'audit.bin.gz').read_bytes()), dtype=DTYPE)
    trades = json.loads((path/'trades.json').read_text()); orders = json.loads((path/'orders.json').read_text())
    assert len(a), (path.name, 'empty decision audit')
    assert np.all(np.diff(a['bar']) > 0), (path.name, 'duplicate/nonchronological bar')
    assert all(np.all(np.isfinite(a[k])) for k in ('r1', 'r2', 'h1', 'h2', 'h3', 'atr', 'ema'))
    assert np.all((a['r1'] >= 0) & (a['r1'] <= 100)) and np.all(a['atr'] > 0)
    assert np.array_equal(expected(a, run.CFG['variants'][r['variant']]), a['side']), (path.name, 'rule mismatch')
    fresh = (a['now'] >= a['bar']+900) & (a['now'] < a['bar']+960) & (a['hbar']+3600 <= a['bar']+900)
    assert np.array_equal(a['result'] == 8, ~fresh), (path.name, 'freshness/H1 mismatch')
    assert np.all(a['result'][(a['side'] == 0) & fresh] == 0)
    assert np.all((a['result'][(a['side'] != 0) & fresh] >= 1) & (a['result'][(a['side'] != 0) & fresh] <= 7))
    # Reconstruct both arms from RSI readings and entry consumption, independently
    # of the EA's age counters. Missing-bar cases require a separate explanation.
    summary = fields(r['summary'][0]); assert int(summary['missing']) == 0, (path.name, 'missing indicators')
    lastlong = lastshort = -1000000
    for i, row in enumerate(a):
        if row['r1'] <= 30: lastlong = i
        if row['r1'] >= 70: lastshort = i
        for native_age, previous in ((row['long_age'], lastlong), (row['short_age'], lastshort)):
            if native_age <= 8 or i-previous <= 8: assert native_age == i-previous, (path.name, 'arm state mismatch', i)
        if row['result'] == 7:
            if row['side'] > 0: lastlong = -1000000
            else: lastshort = -1000000
    assert len(orders) == len(trades) == int(np.sum(a['result'] == 7)) == int(summary['orders'])
    assert int(summary['signals']) == int(np.sum((a['side'] != 0) & fresh))
    bybar = {int(o['bar']): o for o in orders}; byorder = {str(t['order']): t for t in trades}
    spec = fields(r['symbol_spec'][0]); tick = float(spec['tick']); step = float(spec['step']); minimum = float(spec['min'])
    for row in a[a['result'] == 7]:
        o = bybar[int(row['bar'])]; t = byorder[o['order']]; side = int(o['side'])
        assert side == row['side'] and int(o['at']) == row['now']
        assert t['open_msc'] >= int(o['at'])*1000
        assert abs(t['volume']-float(o['lots'])) < 1e-7 and t['volume'] >= minimum-1e-8
        assert abs(t['volume']/step-round(t['volume']/step)) < 1e-6
        distance = side*(float(o['entry'])-float(o['sl']))
        assert distance > 0 and abs(distance-2*row['atr']) <= tick/2+1e-7
        assert abs(side*(float(o['tp'])-float(o['entry']))-distance*run.CFG['rr']) <= tick/2+1e-7
        assert abs(float(o['fill'])-t['open_price']) < 1e-7
    assert max(Counter(t['open_time'][:10] for t in trades).values(), default=0) <= 2
    chronological = sorted(trades, key=lambda t:t['open_msc'])
    assert all(x['close_msc'] <= y['open_msc'] for x, y in zip(chronological, chronological[1:])), 'Overlapping positions'
    exits = [fields(l) for l in r['time_exits']]
    assert all(int(x['held']) >= 16 for x in exits)
    gross = sum(t['net_profit'] for t in trades)
    assert abs(gross-r['metrics']['net_profit']) < max(.12, len(trades)*.01)
    return dict(case=path.name, decision_bars=len(a), closed_positions=len(trades), time_exits=len(exits),
                fresh_signals=int(np.sum(fresh & (a['side'] != 0))), outcomes=dict(Counter(map(int, a['result']))), indicators=indicator_checks(a), ok=True)


def helper_tests():
    a = np.zeros(1, DTYPE)
    a['r2']=40; a['r1']=41; a['h1']=1; a['h2']=.5; a['h3']=0; a['hclose']=2; a['ema']=1; a['hm']=1
    assert expected(a, 0)[0] == 1
    a['r1']=40; assert expected(a, 0)[0] == 0 and expected(a, 3)[0] == 1
    a['r1']=31; a['h2']=0; a['long_age']=8; assert expected(a, 1)[0] == 1
    a['long_age']=9; assert expected(a, 1)[0] == 0
    a['long_age']=0; assert expected(a, 1)[0] == 0
    a['h1']=0; assert expected(a, 2)[0] == 0
    a['r2']=60; a['r1']=59; a['h1']=-1; a['h2']=-.5; a['h3']=0; a['hclose']=1; a['ema']=2; a['hm']=-1
    assert expected(a, 0)[0] == -1
    a['r1']=60; assert expected(a, 0)[0] == 0 and expected(a, 3)[0] == -1
    a['r1']=69; a['h2']=0; a['short_age']=8; assert expected(a, 1)[0] == -1
    a['short_age']=9; assert expected(a, 1)[0] == 0
    return 10


def main():
    tests = helper_tests(); checked = []
    version = dict(verifier=run.sha(ROOT/'verify.py'),runner=run.sha(ROOT/'run.py'))
    prior = json.loads((ROOT/'VERIFICATION.json').read_text()) if (ROOT/'VERIFICATION.json').exists() else {}
    cached = {x['case']:x for x in prior.get('cases',[])} if prior.get('verification_code') == version else {}
    for p in sorted((ROOT/'native').glob('*/run.json')):
        fingerprints={name:run.sha(p.parent/name) for name in ('run.json','audit.bin.gz','trades.json','orders.json','deals.csv')}
        old=cached.get(p.parent.name)
        item=old if old and old.get('evidence_hashes')==fingerprints else check(p.parent)
        item['evidence_hashes']=fingerprints;checked.append(item)
    result = dict(helper_tests=tests, completed_cases=len(checked), decision_bars=sum(x['decision_bars'] for x in checked),
                  closed_positions=sum(x['closed_positions'] for x in checked), cases=checked,
                  verification_code=version,
                  limitation='Rules/clock/arms/ledgers/geometry audited; M15 RSI/MACD reconstructed after 1,000-bar burn-in; H1 EMA200/MACD reconstructed after 2,500 unique-bar burn-in where available. ATR uses native snapshots, not an independent reconstruction. This cannot guarantee broker execution.')
    run.save(ROOT/'VERIFICATION.json', result)
    print(json.dumps({k:v for k,v in result.items() if k != 'cases'}), flush=True)


if __name__ == '__main__': main()
