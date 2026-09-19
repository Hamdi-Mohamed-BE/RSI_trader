"""Shared-account replay, NOT a new native FTMO tick backtest.

All dollars are USD. Source deal timestamps are treated as UTC (the cached
Exness schedules); FTMO loss resets and monthly grouping use Europe/Prague.
No EA, live account, website data or installer is modified by this research.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo
import numpy as np

OUT = Path(__file__).resolve().parent
CACHE = OUT.parents[1] / 'EA store/data/evidence-cache/v1/products'
UTC = timezone.utc
PRAGUE = ZoneInfo('Europe/Prague')
ACCOUNT = 100_000.0
START = datetime(2023, 9, 5, tzinfo=UTC)
END = datetime(2026, 9, 1, tzinfo=PRAGUE).astimezone(UTC)
NEWS = {'news-pulse-xau', 'news-pulse-xag'}
EAS = {
    'news-pulse-xau': ('News Pulse XAU', 'standard'),
    'news-pulse-xag': ('News Pulse XAG', 'standard'),
    'orb-volume-profile-volume-confirmed': ('ORB Volume Profile Confirmed', 'standard'),
    'xau-trend-progression': ('XAU Trend Progression', 'standard'),
    'usdjpy-london-open-momentum': ('USDJPY London Open Momentum', 'standard'),
    'us100-orb-new-york-m30': ('US100 ORB New York M30', 'standard'),
    'us100-h1-orb-13utc': ('US100 H1 ORB 13UTC', 'standard'),
    'ema3': ('EMA3 Safe', 'safe'),
    'xau-squeeze-momentum-standard': ('XAU Squeeze Momentum Standard', 'standard'),
    'xau-rsi-vwap': ('XAU RSI VWAP', 'standard'),
}
ADDED = {'ema3', 'xau-squeeze-momentum-standard', 'xau-rsi-vwap'}
LEV = {'XAUUSD': 9, 'XAGUSD': 9, 'USTEC': 15, 'USDJPY': 30}
CONTRACT = {'XAUUSD': 100, 'XAGUSD': 5000, 'USTEC': 1, 'USDJPY': 100000}


def dt(value):
    d = datetime.fromisoformat(value)
    return d.replace(tzinfo=UTC) if d.tzinfo is None else d.astimezone(UTC)


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def load():
    rows, audit = [], []
    for slug, (name, mode) in EAS.items():
        path = CACHE / slug / mode / '5y.trades.json'
        ledger = read(path)
        summary = read(path.with_name('5y.json'))
        metrics = summary.get('stats', {})
        audit.append({'slug': slug, 'name': name, 'mode': mode,
                      'available_from': summary['available_from'], 'available_to': summary['available_to'],
                      'ledger_trades': len(ledger), 'metrics': metrics,
                      'history_quality': summary.get('history_quality'),
                      'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        for n, row in enumerate(ledger):
            r = dict(row)
            r.update(slug=slug, name=name, news=slug in NEWS, uid=f'{slug}:{n}',
                     opened=dt(row['open_time']), closed=dt(row['close_time']))
            assert r['closed'] >= r['opened']
            # Cached MT5 timestamps have second resolution. A same-second
            # round trip must open before its own close, not remain orphaned.
            if r['closed'] == r['opened']:
                r['closed'] += timedelta(microseconds=1)
            r['volume'] = float(row['volume'])
            assert r['volume'] > 0
            r['source_risk'] = float(row['estimated_risk_cash'])
            r['base_pct'] = float(row['configured_risk_pct'])
            assert r['source_risk'] > 0 and r['base_pct'] > 0
            r['source_balance'] = r['source_risk'] / (r['base_pct'] / 100)
            r['symbol'] = 'USTEC' if row['symbol'].startswith(('USTEC', 'US100')) else row['symbol'].rstrip('r')
            assert r['symbol'] in LEV
            assert abs(float(r['gross_profit']) + float(r['commission']) + float(r['swap']) - float(r['net_profit'])) < 0.05
            rows.append(r)
    common_start = max(dt(a['available_from']) for a in audit)
    common_end = min(dt(a['available_to']) for a in audit)
    rows = [r for r in rows if common_start <= r['opened'] < common_end and r['closed'] < common_end]
    return rows, audit, common_start, common_end


ROWS, AUDIT, COMMON_START, COMMON_END = load()


def month(at):
    return at.astimezone(PRAGUE).strftime('%Y-%m')


def components(r, factor, stress):
    gross, commission, swap = (float(r[k]) * factor for k in ('gross_profit', 'commission', 'swap'))
    extra = 0.0
    if stress:
        # Scenario assumptions, NOT measured FTMO fill statistics or a fee quote.
        transformed = gross * ((.65 if gross > 0 else 1.25) if r['news'] else (.90 if gross > 0 else 1.10))
        extra += gross - transformed + r['source_risk'] * factor * (.15 if r['news'] else .02)
        if r['symbol'] != 'USTEC':
            commission = min(commission, -7.0 * r['volume'] * factor)
        swap = min(0.0, 2 * swap)  # double debits and remove positive credits
    return gross, commission, swap, extra


def margin(r, lots):
    notional = lots * CONTRACT[r['symbol']]
    if r['symbol'] != 'USDJPY':
        notional *= float(r['open_price'])
    return notional / LEV[r['symbol']]


def business_pause(at):
    d = at
    for _ in range(2):
        d += timedelta(days=1)
        while d.weekday() >= 5:
            d += timedelta(days=1)
    return d


def replay(rows, start, end, *, risk=.35, stress=True, challenge=False,
           enforce_envelope=False, detailed=True, stop_when_funded=False,
           buffer=2000.0, fixed_news=True):
    """One balance/margin pool; deterministic ties (close first, then slug).

    Close-only equity proxy is supplemented by a planned-stop envelope, NOT
    actual floating equity. No invented liquidation prices after a breach.
    Payouts: just before month end or first flat event thereafter, profits above
    initial+buffer only, at least 14 days after first trade/previous payout.
    Monthly payout is potential claim, not settlement in the bank.
    """
    balance = peak = ACCOUNT
    anchor = ACCOUNT
    active, streak = {}, defaultdict(int)
    counters = Counter()
    records, ticks, phases, withdrawals = [], [], [], []
    monthly = {}
    phase = 1 if challenge else 3
    ready, first_funded = start, None
    funded_at = None if challenge else start
    trading_days = set()
    halted = None
    pending_payout, last_payout = False, None
    max_dd = max_day = max_envelope_day = max_risk = max_margin = 0.0
    max_positions = 0
    min_balance = min_envelope = ACCOUNT
    envelope_first = None
    total_net = total_distribution = resets = 0.0
    events = []
    for i, r in enumerate(rows):
        if start <= r['opened'] < end and r['closed'] < end:
            events.extend([(r['opened'], 2, r['uid'], i), (r['closed'], 1, r['uid'], i)])
    # Explicit CE(S)T midnights, including ones without a trade.
    d = start.astimezone(PRAGUE).date()
    while True:
        moment = datetime.combine(d, datetime.min.time(), PRAGUE).astimezone(UTC)
        if moment > start and moment <= end and d.day == 1:
            events.append((moment - timedelta(microseconds=1), 4, '', -1))
        if moment >= end:
            break
        if moment >= start:
            events.append((moment, 0, '', -1))
        d += timedelta(days=1)
    events.sort()

    def bucket(at):
        key = month(at)
        if key not in monthly:
            monthly[key] = {'month': key, 'opened': 0, 'closed': 0, 'wins': 0, 'losses': 0,
                            'net': 0.0, 'gross': 0.0, 'commission': 0.0, 'swap': 0.0,
                            'extra_stress': 0.0, 'payout': 0.0, 'distribution': 0.0,
                            'start_balance': balance, 'end_balance': balance, 'reset_adjustment': 0.0,
                            'max_daily_loss': 0.0, 'max_envelope_daily_loss': 0.0,
                            'min_envelope': balance, 'phase': set(), 'rejected': 0,
                            'breach': None, 'ea': {s: {'opened': 0, 'closed': 0, 'net': 0.0} for s in EAS}}
        return monthly[key]

    def check(at, m):
        nonlocal peak, max_dd, max_day, max_envelope_day, min_balance, min_envelope
        nonlocal envelope_first, halted, max_positions, max_risk, max_margin
        peak = max(peak, balance)
        dd = (peak - balance) / peak * 100
        total_risk = sum(p['envelope'] for p in active.values())
        eq_proxy = balance - total_risk
        daily_loss = max(0.0, anchor - balance)
        envelope_loss = max(0.0, anchor - eq_proxy)
        max_dd = max(max_dd, dd)
        max_day = max(max_day, daily_loss)
        max_envelope_day = max(max_envelope_day, envelope_loss)
        min_balance = min(min_balance, balance)
        min_envelope = min(min_envelope, eq_proxy)
        max_positions = max(max_positions, len(active))
        max_risk = max(max_risk, sum(p['risk'] for p in active.values()))
        max_margin = max(max_margin, sum(p['margin'] for p in active.values()))
        m['max_daily_loss'] = max(m['max_daily_loss'], daily_loss)
        m['max_envelope_daily_loss'] = max(m['max_envelope_daily_loss'], envelope_loss)
        m['min_envelope'] = min(m['min_envelope'], eq_proxy)
        reason = 'daily loss' if daily_loss > 5000.0 + 1e-8 else ('total loss' if balance < 90000.0 - 1e-8 else None)
        warning = 'daily stop envelope' if envelope_loss > 5000.0 + 1e-8 else ('total stop envelope' if eq_proxy < 90000.0 - 1e-8 else None)
        if warning and envelope_first is None:
            envelope_first = {'at': at.isoformat(), 'reason': warning, 'balance': balance, 'proxy_equity': eq_proxy, 'daily_anchor': anchor, 'phase': phase}
        if reason or (enforce_envelope and warning):
            halted = {'at': at.isoformat(), 'reason': reason or warning, 'balance': balance,
                      'proxy_equity': eq_proxy, 'phase': phase, 'open_positions': len(active)}
            m['breach'] = halted['reason']
        if detailed:
            ticks.append({'at': at.isoformat(), 'balance': round(balance, 2), 'envelope': round(eq_proxy, 2),
                          'daily_floor': round(anchor - 5000, 2), 'phase': phase})

    for at, kind, uid, i in events:
        m = bucket(at)
        m['phase'].add('Failed' if halted else ('Funded' if phase == 3 else f'Phase {phase}'))
        if halted:
            m['end_balance'] = balance
            continue
        if kind == 0:
            anchor = balance
        elif kind == 4:
            pending_payout = True
        elif kind == 2:
            r = rows[i]
            reason = None
            if at < ready:
                reason = 'phase review pause'
            elif not r['news'] and balance - anchor <= -1000:
                reason = 'normal daily entry stop'
            target = .75 if r['news'] and fixed_news else risk
            if not r['news']:
                dd = (peak - balance) / peak * 100
                target *= .25 if dd >= 7 else .5 if dd >= 4 else 1
                target *= .25 if streak[r['slug']] >= 5 else .5 if streak[r['slug']] >= 3 else 1
            ideal_factor = balance / r['source_balance'] * target / r['base_pct']
            lots = max(.01, math.ceil(r['volume'] * ideal_factor / .01 - 1e-9) * .01)
            factor = lots / r['volume']
            risk_cash = r['source_risk'] * factor
            required_margin = margin(r, lots)
            if not reason and not r['news'] and sum(p['risk'] for p in active.values()) + risk_cash > 3000 + 1e-8:
                reason = 'normal shared risk cap'
            # Reserve 20% of conservative equity, not just nominal balance.
            safe_equity = balance - sum(p['envelope'] for p in active.values())
            if not reason and sum(p['margin'] for p in active.values()) + required_margin > max(0, safe_equity) * .8:
                reason = 'shared Swing margin reserve'
            if reason:
                counters[reason] += 1
                counters['rejected:' + r['slug']] += 1
                m['rejected'] += 1
                continue
            gross, commission, swap, extra = components(r, factor, stress)
            entry_fee = commission * .5
            balance += entry_fee
            total_net += entry_fee
            m['net'] += entry_fee
            m['commission'] += entry_fee
            m['ea'][r['slug']]['net'] += entry_fee
            # Hold full initial target stop even after trailing; conservative
            # path scenario only. Gap multiplier and unpaid costs included.
            env = risk_cash * ((1.25 if r['news'] else 1.10) if stress else 1)
            env += max(0, -commission*.5) + max(0, -swap) + risk_cash * ((.15 if r['news'] else .02) if stress else 0)
            active[uid] = dict(r=r, factor=factor, risk=risk_cash, margin=required_margin,
                               gross=gross, commission=commission, swap=swap, extra=extra,
                               entry_fee=entry_fee, envelope=env, phase=phase, lots=lots)
            trading_days.add(at.astimezone(PRAGUE).date())
            if phase == 3 and first_funded is None:
                first_funded = at
            counters['accepted:' + r['slug']] += 1
            m['opened'] += 1
            m['ea'][r['slug']]['opened'] += 1
        else:
            p = active.pop(uid, None)
            if p is None:
                continue
            r = p['r']
            remainder = p['gross'] + p['commission']*.5 + p['swap'] - p['extra']
            full_net = remainder + p['entry_fee']
            balance += remainder
            total_net += remainder
            for key, val in [('net', remainder), ('gross', p['gross']), ('commission', p['commission']*.5),
                             ('swap', p['swap']), ('extra_stress', p['extra'])]:
                m[key] += val
            m['ea'][r['slug']]['net'] += remainder
            m['ea'][r['slug']]['closed'] += 1
            m['closed'] += 1
            m['wins'] += full_net > 0
            m['losses'] += full_net < 0
            streak[r['slug']] = streak[r['slug']] + 1 if full_net < 0 else 0 if full_net > 0 else streak[r['slug']]
            counters['closed'] += 1
            counters['wins'] += full_net > 0
            counters['gross_wins'] += max(0, full_net)
            counters['gross_losses'] += max(0, -full_net)
            if detailed:
                records.append({'slug': r['slug'], 'name': r['name'], 'opened': r['opened'].isoformat(), 'closed': at.isoformat(),
                                'phase': p['phase'], 'volume': round(p['lots'], 2), 'net': round(full_net, 6),
                                'gross': p['gross'], 'commission': p['commission'], 'swap': p['swap'],
                                'extra_stress': p['extra'], 'planned_risk': p['risk'], 'margin': p['margin']})
        check(at, m)
        if halted:
            m['end_balance'] = balance
            continue
        if phase < 3 and not active and len(trading_days) >= 4 and balance >= ACCOUNT * (1.10 if phase == 1 else 1.05):
            phases.append({'phase': phase, 'passed_at': at.isoformat(), 'balance': balance,
                           'entry_days': len(trading_days), 'elapsed_days': (at-start).days+1})
            adjustment = ACCOUNT - balance
            resets += adjustment
            m['reset_adjustment'] += adjustment
            balance = peak = anchor = ACCOUNT
            phase += 1
            ready = business_pause(at)
            streak.clear()
            trading_days.clear()
            pending_payout = False
            if phase == 3:
                funded_at = ready
                first_funded = None
                if stop_when_funded:
                    m['end_balance'] = balance
                    break
        if phase == 3 and pending_payout and not active and first_funded is not None:
            eligible_date = max(first_funded + timedelta(days=14), (last_payout + timedelta(days=14)) if last_payout else first_funded)
            profit_to_split = max(0.0, balance - ACCOUNT - buffer)
            if at >= eligible_date and profit_to_split >= 20:
                total_distribution += profit_to_split
                # Removing paid profit is an external cash flow, not a loss.
                balance -= profit_to_split
                anchor -= profit_to_split
                peak = max(balance, peak - profit_to_split)
                payout = .8 * profit_to_split
                withdrawals.append({'at': at.isoformat(), 'payout': payout, 'distribution': profit_to_split})
                m['payout'] += payout
                m['distribution'] += profit_to_split
                pending_payout = False
                last_payout = at
                if detailed:
                    ticks.append({'at': at.isoformat(), 'balance': round(balance, 2), 'envelope': round(balance, 2),
                                  'daily_floor': round(anchor - 5000, 2), 'phase': phase})
        m['end_balance'] = balance

    assert abs(ACCOUNT + total_net + resets - total_distribution - balance) < 1e-5
    if not halted and not stop_when_funded:
        assert not active, 'Every selected source trade closes before the window end'
    for m in monthly.values():
        m['phase'] = ' / '.join(sorted(m['phase']))
        assert abs(m['start_balance'] + m['net'] + m['reset_adjustment'] - m['distribution'] - m['end_balance']) < 1e-5, m
        assert abs(m['gross'] + m['commission'] + m['swap'] - m['extra_stress'] - m['net']) < 1e-5
        assert abs(sum(e['net'] for e in m['ea'].values()) - m['net']) < 1e-5
    assert abs(sum(m['net'] for m in monthly.values()) - total_net) < 1e-5
    assert not withdrawals or all(w['payout'] > 0 for w in withdrawals)
    if halted and detailed:
        assert all(dt(r['closed']) <= dt(halted['at']) for r in records)
        assert all(dt(w['at']) <= dt(halted['at']) for w in withdrawals)
    return {'risk': risk, 'news_risk': .75 if fixed_news else risk, 'stress': stress, 'challenge': challenge, 'enforce_envelope': enforce_envelope,
            'funded_at': funded_at.isoformat() if funded_at else None, 'phases': phases,
            'breach': halted, 'first_envelope_warning': envelope_first,
            'balance': balance, 'net': total_net, 'payout': total_distribution*.8,
            'distribution': total_distribution, 'reset_adjustment': resets,
            'closed_trades': counters['closed'], 'win_rate': 100*counters['wins']/max(1,counters['closed']),
            'profit_factor': counters['gross_wins']/counters['gross_losses'] if counters['gross_losses'] else None,
            'max_closed_drawdown_pct': max_dd, 'max_closed_daily_loss': max_day,
            'max_envelope_daily_loss': max_envelope_day, 'min_balance': min_balance,
            'min_envelope': min_envelope, 'max_positions': max_positions,
            'max_open_risk': max_risk, 'max_margin': max_margin,
            'open_at_stop': len(active), 'counters': dict(counters),
            'monthly': list(monthly.values()) if detailed else [],
            'trades': records, 'curve': ticks, 'withdrawals': withdrawals}


def synthetic(rng, horizon=730):
    """Joint four-week moving-block resampling, keeping every EA together.

    Entire trades travel with their opening block; positions retain durations
    across joins. Independent sampled joins can create artificial overlaps.
    This is a conditional resampling diagnostic, not an OOS probability.
    """
    week0 = COMMON_START - timedelta(days=COMMON_START.weekday())
    week0 = week0.replace(hour=0, minute=0, second=0)
    n_weeks = (COMMON_END - week0).days // 7
    dest0 = datetime(2027, 1, 4, tzinfo=UTC)
    out, n = [], 0
    for dest_week in range(0, math.ceil(horizon/7), 4):
        source_week = int(rng.integers(0, n_weeks-3))
        lo = week0 + timedelta(weeks=source_week)
        hi = lo + timedelta(weeks=4)
        shift = dest0 + timedelta(weeks=dest_week) - lo
        for r in ROWS:
            if lo <= r['opened'] < hi:
                rr = dict(r)
                rr['opened'] += shift
                rr['closed'] += shift
                rr['uid'] = f'sim:{n}'
                n += 1
                out.append(rr)
    return out, dest0, dest0 + timedelta(days=horizon)


def monte_carlo(n=1000):
    rng = np.random.default_rng(20260913)
    groups = {k: [] for k in ['source', 'stressed', 'stop_envelope', 'lower_news_source', 'lower_news_stressed', 'lower_news_stop_envelope']}
    for i in range(n):
        rows, start, end = synthetic(rng)
        for key in groups:
            result = replay(rows, start, end, risk=.35, stress=not key.endswith('source'), challenge=True,
                            enforce_envelope=key.endswith('stop_envelope'), detailed=False,
                            stop_when_funded=True, fixed_news=not key.startswith('lower_news_'))
            status = 'breach' if result['breach'] else 'passed' if result['funded_at'] else 'unfinished'
            groups[key].append({'status': status, 'days': (dt(result['phases'][-1]['passed_at'])-start).days + 1 if result['funded_at'] else None,
                                'reason': result['breach']['reason'] if result['breach'] else None})
        if (i+1) % 100 == 0:
            print(f'Monte Carlo {i+1}/{n}', flush=True)
    result = {}
    for key, values in groups.items():
        counts = Counter(r['status'] for r in values)
        passed_days = [r['days'] for r in values if r['status']=='passed']
        p = counts['passed']/n
        # Wilson interval measures sampling uncertainty, NOT model error.
        z = 1.96
        center = (p+z*z/(2*n))/(1+z*z/n)
        half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
        result[key] = {'trials': n, **{k: counts[k] for k in ['passed','breach','unfinished']},
                       'pass_pct': 100*p, 'wilson95_pct': [100*(center-half),100*(center+half)],
                       'median_days_if_passed': median(passed_days) if passed_days else None,
                       'p10_p90_days_if_passed': np.percentile(passed_days,[10,90]).tolist() if passed_days else None,
                       'breach_reasons': dict(Counter(r['reason'] for r in values if r['reason'])),
                       'inverse_pass_probability': 1/p if p else None}
    return result


def compact(r):
    return {k:v for k,v in r.items() if k not in ['monthly','trades','curve','withdrawals']}


def main():
    assert 'news-pulse-btc' not in EAS and len(EAS) == 10
    runs = {}
    for challenge in [False, True]:
        for name, stress, envelope in [('source',False,False),('stressed',True,False),('stop-envelope',True,True)]:
            key = ('challenge-' if challenge else 'funded-') + name
            runs[key] = replay(ROWS, START, END, stress=stress, challenge=challenge, enforce_envelope=envelope)
            print(key, json.dumps(compact(runs[key])), flush=True)
        key = ('challenge-' if challenge else 'funded-') + 'lower-news'
        runs[key] = replay(ROWS, START, END, stress=True, challenge=challenge, fixed_news=False)
    sensitivity = []
    for risk in [.25,.35,.5]:
        for added in [False,True]:
            subset = ROWS if added else [r for r in ROWS if r['slug'] not in ADDED]
            r = replay(subset, START, END, risk=risk, detailed=False)
            sensitivity.append({'eas': 10 if added else 7, **compact(r)})
    lower_news = replay(ROWS, START, END, risk=.35, fixed_news=False, detailed=False)
    data = {'account': ACCOUNT, 'from': START.isoformat(), 'to_exclusive': END.isoformat(),
            'source_from': COMMON_START.isoformat(), 'source_to_exclusive': COMMON_END.isoformat(),
            'generated_at': datetime.now(UTC).isoformat(), 'source_audit': AUDIT,
            'eas': [{'slug': s, 'name': n, 'mode': m, 'added': s in ADDED, 'news': s in NEWS} for s,(n,m) in EAS.items()],
            'risk': {'regular_pct': .35, 'news_pct': .75, 'normal_daily_entry_stop_usd': 1000,
                     'normal_open_risk_cap_usd': 3000, 'payout_buffer': 2000, 'reward_share': .8,
                     'asset_leverage': LEV, 'margin_reserve_pct': 20},
            'runs': runs, 'sensitivity': sensitivity, 'lower_news_risk_sensitivity': compact(lower_news)}
    if '--no-mc' in __import__('sys').argv and (OUT/'results.json').exists():
        previous = read(OUT/'results.json')
        if 'monte_carlo' in previous:
            data['monte_carlo'] = previous['monte_carlo']
    (OUT/'results.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    if '--no-mc' not in __import__('sys').argv:
        data['monte_carlo'] = monte_carlo()
        (OUT/'results.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    for key,r in runs.items():
        with (OUT/f'{key}-monthly.csv').open('w', newline='', encoding='utf-8-sig') as f:
            flat = [{k:v for k,v in m.items() if k != 'ea'} for m in r['monthly']]
            writer = csv.DictWriter(f, fieldnames=list(flat[0]))
            writer.writeheader(); writer.writerows(flat)
    print('All ledger, monthly, cash-flow and post-breach invariants passed.', flush=True)


if __name__ == '__main__':
    main()
