"""Generated from the saved pure offline guard replay; no trading imports. Rebuild via build_portfolio_catalog.py."""
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
PRAGUE=ZoneInfo('Europe/Prague')
CAPITAL=10000.0
DAY=86400
SPECS={'XAUUSD':(100,15),'XAGUSD':(5000,15),'USTEC':(1,15),'USDJPY':(100000,30),'EURUSD':(100000,30),'BTCUSD':(1,1),'ETHUSD':(10,1)}
def iso(t):return datetime.fromtimestamp(t,timezone.utc).isoformat() if t is not None else None
def rounded(v):return max(0.,math.floor(v/.01+1e-10)*.01)
def costs(row,stress=False):
    g,comm,swap,extra=base_costs(row,stress)
    if row['symbol']=='XAUUSD':comm=min(comm,-.000014*100*(row['open_price']+row['close_price']))
    elif row['symbol']=='USDJPY':comm=min(comm,-10.)
    return g,comm,swap,extra
def entry_charge(row,commission,extra):
    if row['symbol']=='XAUUSD':return -max(3.5,-row['unit_comm']/2,.000014*100*row['open_price'])-extra/2
    if row['symbol']=='USDJPY':return -max(5.,-row['unit_comm']/2)-extra/2
    return (commission-extra)/2

def base_costs(r, stress=False):
    sym = r['symbol']
    contract = SPECS[sym][0]
    g = r['unit_gross']
    c = r['unit_comm']
    s = r['unit_swap']
    if sym in ('BTCUSD', 'ETHUSD'):
        c = min(c, -0.000325 * contract * (r['open_price'] + r['close_price']))
    else:
        c = min(c, -(47.5 if sym == 'XAGUSD' else 0.7 if sym == 'USTEC' else 7.0))
    extra = 0.0
    if stress:
        news = r['news']
        g *= 0.9 if g > 0 else 1.1
        slip = {'XAUUSD': 1.0 if news else 0.2, 'XAGUSD': 0.04, 'USTEC': 2.0, 'EURUSD': 0.0002, 'USDJPY': 0.02, 'BTCUSD': 30.0, 'ETHUSD': 3.0}[sym]
        extra = slip * contract / (r['open_price'] if sym == 'USDJPY' else 1.0)
        s = min(s * 2, 0.0)
        if r['cl'] - r['op'] > DAY:
            notional = contract * (1 if sym == 'USDJPY' else r['open_price'])
            s = min(s, -notional * 0.00015 * math.ceil((r['cl'] - r['op']) / DAY))
    return (g, c, s, extra)

def business(t, n):
    d = datetime.fromtimestamp(t, timezone.utc)
    while n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d.timestamp()

def margin(sym, lot, price):
    contract, lev = SPECS[sym]
    return lot * contract * (1 if sym == 'USDJPY' else price) / lev

def replay(rows, places, start, end, *, news_risk=10.0, stress=False, guards=True, challenge=True, detail=False, risk_mode='fixed', risk_value=50.0, daily_mode='off', daily_value=0.0):
    events = []
    for i, r in enumerate(rows):
        r['_costs'] = costs(r, stress)
        events.append((r['op'], 1, i))
        if r['cl'] < end:
            events.append((r['cl'], 2, i))
    pi = {(p['key'], p['epoch']): i for i, p in enumerate(places)}
    for i, p in enumerate(places):
        events.append((p['op'], 0, i))
        if p['until'] < end:
            events.append((p['until'], 3, i))
    day = datetime.fromtimestamp(start, PRAGUE).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    while day.timestamp() < end:
        events.append((day.timestamp(), -1, 0))
        day += timedelta(days=1)
    events.append((end - 0.001, 4, 0))
    events.sort(key=lambda e: (e[0], -1 if e[1] == 2 else e[1], e[2]))
    bal = peak = anchor = CAPITAL
    phase = 1 if challenge else 3
    ready = start
    active = {}
    pending = {}
    days = set()
    counts = Counter()
    by = defaultdict(Counter)
    log = []
    passes = []
    first = funded = request = receipt = breach = None
    reward = dd = daily = closeddd = maxmargin = maxrisk = 0.0
    custom_day_stopped = False
    today_count = 0
    max_daily_entries = 0
    today_losses = 0
    ws = ls = mw = ml = 0
    last_entry = start
    expired = None

    def held():
        return list(active.values()) + list(pending.values())

    def envelope():
        return sum((p['env'] for p in active.values()))

    def gate(t, slots=1):
        if custom_day_stopped:
            return 'custom_closed_daily_stop'
        if t < ready:
            return 'phase_wait'
        if challenge and phase < 3 and (bal >= CAPITAL * (1.1 if phase == 1 else 1.05)) and (len(days) >= 4):
            return 'target_wait'
        if guards and today_count + len(pending) + slots > 7:
            return 'daily_trade_limit'
        if guards and today_losses >= 3:
            return 'three_losses_stop'
        return None

    def admit(sym, marg, risk, entryfee, env):
        current = held()
        totalrisk = sum((p['risk'] for p in current))
        totalmargin = sum((p['margin'] for p in current))
        if totalmargin + marg > (bal - envelope()) * (0.8 if guards else 1.0):
            return 'margin'
        if guards:
            if totalrisk + risk > 225:
                return 'open_risk'
            group = 'metals' if sym in ('XAUUSD', 'XAGUSD') else sym
            if sum((p['risk'] for p in current if p['group'] == group)) + risk > 150:
                return 'correlated_risk'
            if anchor - bal + sum((p['env'] for p in current)) + env - entryfee > 300:
                return 'daily_budget'
            if bal - sum((p['env'] for p in current)) - env + entryfee < 9200:
                return 'total_loss_buffer'
        return None
    for t, kind, i in events:
        if kind == -1:
            anchor = bal
            today_count = today_losses = 0
            custom_day_stopped = False
        elif kind == 0:
            p = places[i]
            reason = gate(t, 2)
            if reason:
                counts[reason] += 1
                continue
            sym = p['symbol']
            contract = SPECS[sym][0]
            riskunit = p['sl'] * contract
            lot = rounded(news_risk / riskunit)
            if lot < 0.01:
                counts['news_min_lot_over_budget'] += 1
                continue
            risk = lot * riskunit
            assert risk <= news_risk + 1e-07
            marg = margin(sym, lot, max(p['buy'], p['sell']))
            fee = (max(7.0, 1.4e-05 * 100 * (p['buy'] + p['sell'])) if sym == 'XAUUSD' else 47.5 if sym == 'XAGUSD' else 7.0) * lot
            if sym == 'BTCUSD':
                fee = 0.000325 * lot * (p['buy'] + p['sell'])
            env = risk * (2 if stress else 1.25)
            reason = admit(sym, 2 * marg, 2 * risk, -fee, 2 * env)
            if reason:
                counts['news_' + reason + '_rejected'] += 1
                continue
            for side in ('Long', 'Short'):
                pending[i, side] = dict(lot=lot, risk=risk, margin=marg, env=env, key=p['key'], group='metals' if sym in ('XAUUSD', 'XAGUSD') else sym)
            counts['news_baskets'] += 1
        elif kind == 1:
            r = rows[i]
            key = r['key']
            g, c, s, x = r['_costs']
            sym = r['symbol']
            if not r.get('order_compatible', True):
                counts['unsupported_pending_order'] += 1
                continue
            if r['news']:
                pidx = pi.get((key, r['event']))
                p = pending.pop((pidx, r['side']), None)
                if p is None:
                    counts['news_not_admitted_fills'] += 1
                    continue
                p['actual_risk'] = r.get('actual_unit_risk', r['unit_risk']) * p['lot']
                p['env'] = max(p['env'], p['actual_risk'] * (2 if stress else 1.25))
            else:
                reason = gate(t)
                if reason:
                    counts[reason] += 1
                    continue
                if any((p.get('lane', p['key']) == r.get('lane', key) for p in active.values())):
                    counts['same_ea_overlap'] += 1
                    continue
                budget = min(50.0, risk_value if risk_mode == 'fixed' else bal * risk_value / 100.0) * r.get('risk_weight', 1.0)
                lot = rounded(budget / r['unit_risk'])
                if lot < 0.01:
                    counts['min_lot_over_budget'] += 1
                    continue
                risk = lot * r['unit_risk']
                marg = margin(sym, lot, r['open_price'])
                assert risk <= budget + 1e-07
                env = risk * (1.25 * (1.25 if stress else 1.0)) + 5.0
                reason = admit(sym, marg, risk, entry_charge(r, c, x) * lot, env)
                if reason:
                    counts[reason + '_rejected'] += 1
                    continue
                p = dict(lot=lot, risk=risk, margin=marg, env=env, key=key, lane=r.get('lane', key), group='metals' if sym in ('XAUUSD', 'XAGUSD') else sym)
            fee = entry_charge(r, c, x) * p['lot']
            bal += fee
            p.update(phase=phase, opened=t, entryfee=fee)
            active[i] = p
            today_count += 1
            last_entry = t
            counts['opened'] += 1
            by[key]['opened'] += 1
            days.add(datetime.fromtimestamp(t, PRAGUE).date())
            max_daily_entries = max(max_daily_entries, today_count)
            if phase == 3 and first is None:
                first = t
        elif kind == 2 and i in active:
            p = active.pop(i)
            r = rows[i]
            g, c, s, x = r['_costs']
            lot = p['lot']
            delta = (g + s + c - x) * lot - p['entryfee']
            bal += delta
            net = delta + p['entryfee']
            counts['closed'] += 1
            by[r['key']]['trades'] += 1
            by[r['key']]['net'] += net
            by[r['key']]['wins'] += net > 0
            by[r['key']]['positive'] += max(0, net)
            by[r['key']]['negative'] += max(0, -net)
            today_losses += net < 0
            ws = ws + 1 if net > 0 else 0
            ls = ls + 1 if net < 0 else 0
            mw = max(mw, ws)
            ml = max(ml, ls)
            if detail:
                log.append(dict(ea=r['key'], phase=p['phase'], open=iso(p['opened']), close=iso(t), lots=lot, initial_risk=p['risk'], actual_fill_stop_risk=p.get('actual_risk', p['risk']), gross_profit=g * lot, commission=c * lot, swap=s * lot, stress_cost=x * lot, net_profit=net, balance=bal))
        elif kind == 3:
            for side in ('Long', 'Short'):
                pending.pop((i, side), None)
        custom_limit = daily_value if daily_mode == 'fixed' else anchor * daily_value / 100.0
        if daily_mode != 'off' and anchor - bal >= custom_limit:
            custom_day_stopped = True
        eq = bal - envelope()
        peak = max(peak, bal)
        dd = max(dd, 100 * (peak - eq) / peak)
        closeddd = max(closeddd, 100 * (peak - bal) / peak)
        daily = max(daily, anchor - eq)
        maxmargin = max(maxmargin, sum((p['margin'] for p in held())))
        maxrisk = max(maxrisk, sum((p['risk'] for p in held())))
        if eq < 9000 - 1e-08 or eq < anchor - 500 - 1e-08:
            breach = t
            break
        if challenge and phase < 3 and (not active) and (not pending) and (len(days) >= 4) and (bal >= CAPITAL * (1.1 if phase == 1 else 1.05)):
            passes.append(dict(phase=phase, time=iso(t), balance=bal, trading_days=len(days)))
            phase += 1
            ready = business(t, 2 if phase == 2 else 5)
            if phase == 3:
                funded = ready
            bal = peak = anchor = CAPITAL
            days = set()
            last_entry = ready
        if challenge and phase == 3 and (first is not None) and (not active) and (not pending) and (t >= first + 14 * DAY) and (bal >= 10025):
            request = t
            receipt = business(t, 4)
            reward = 0.8 * (bal - CAPITAL)
            break
        if False:
            expired = t
            break
    wins = sum((v['wins'] for v in by.values()))
    trades = counts['closed']
    pos = sum((v['positive'] for v in by.values()))
    neg = sum((v['negative'] for v in by.values()))
    return dict(funded=funded is not None and funded < end, payout=receipt is not None and receipt < end, eligible=request is not None and request < end, breach=breach is not None, inactive=expired is not None, funded_at=iso(funded), request_at=iso(request), receipt_at=iso(receipt), breach_at=iso(breach), reward=reward, balance=bal, phase=phase, passes=passes, trades=trades, win_rate=100 * wins / trades if trades else 0, pf=pos / neg if neg else None, open_positions=len(active), pending_orders=len(pending), unclosed_entry_costs=sum((p['entryfee'] for p in active.values())), reserve_equity=bal - envelope(), model_dd_pct=dd, closed_dd_pct=closeddd, worst_daily_usd=daily, max_margin=maxmargin, max_open_risk=maxrisk, max_daily_entries=max_daily_entries, max_win_streak=mw, max_loss_streak=ml, counts=dict(counts), by_ea=dict(by), log=log)
