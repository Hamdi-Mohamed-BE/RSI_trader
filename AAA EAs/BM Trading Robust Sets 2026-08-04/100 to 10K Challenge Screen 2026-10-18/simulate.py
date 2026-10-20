"""Finite, frozen $100 -> $10k historical cash challenge. Never trades."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from bisect import bisect_left
from collections import Counter
from itertools import combinations
import argparse
import hashlib
import json
import math
import statistics

ROOT = Path(__file__).resolve().parent
DAY = 86400


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n', encoding='utf-8')


def epoch(date):
    return datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp()


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat()


def weekly_starts(window, horizon=365):
    start, end = map(epoch, window)
    t = start
    while datetime.fromtimestamp(t, timezone.utc).weekday() != 0:
        t += DAY
    out = []
    while t + horizon * DAY <= end:
        out.append(t)
        t += 7 * DAY
    return out


def quantile(values, q):
    if not values:
        return None
    a = sorted(values)
    n = (len(a) - 1) * q
    lo = int(n)
    return a[lo] + (a[min(lo + 1, len(a)-1)] - a[lo]) * (n-lo)


def build_events(rows, keys):
    events = []
    for r in rows:
        if r['key'] not in keys:
            continue
        events.append((r['op'], 1, r['id'], 0, r, None))
        for f in r['flows']:
            if f['kind'] != 'entry':
                events.append((f['epoch'], 0, r['id'], int(f['deal_id']), r, f))
    return sorted(events, key=lambda e: e[:4])


def replay(events, symbols, risk_pct, start, end, detail=False, stress=False):
    """No outcome enters sizing/admission; only owned, past cash is booked."""
    cash, peak, maxdd = 100.0, 100.0, 0.0
    active, counts, closed, curve, decisions = {}, Counter(), [], [], []
    floor_time = hit_time = None
    today, day_anchor, paused = None, cash, False
    target, floor = 10000.0, 20.0
    risk_fraction = risk_pct / 100.0
    last_time = start
    times = [e[0] for e in events]
    first = bisect_left(times, start)

    def observe(t):
        nonlocal peak, maxdd, floor_time, today, day_anchor, paused, hit_time
        day = int(t // DAY)
        if day != today:
            today, day_anchor, paused = day, cash, False
        peak = max(peak, cash)
        maxdd = max(maxdd, (peak-cash) / peak * 100)
        if cash <= floor + 1e-9 and floor_time is None:
            floor_time = t
        if cash <= day_anchor * (1-min(2*risk_fraction, .30)) + 1e-9:
            paused = True
        if floor_time is None and not active and cash >= target:
            hit_time = t
        if detail:
            curve.append({'epoch':t, 'balance':cash, 'open_positions':len(active)})

    observe(start)
    for t, phase, ident, dealid, row, flow in events[first:]:
        if t >= end or hit_time is not None or (floor_time is not None and not active):
            break
        if row['op'] < start:
            continue  # Fresh account: never own pre-window positions.
        last_time = t
        # Calendar reset BEFORE this event; cash then reflects only prior events.
        day = int(t // DAY)
        if day != today:
            today, day_anchor, paused = day, cash, False
        if phase == 1:
            counts['candidates'] += 1
            spec = symbols[row['symbol']]
            budget = max(0., cash * risk_fraction)
            step = spec['volume_step']
            volume = math.floor(min(spec['volume_max'], budget / row['unit_risk']) / step + 1e-9) * step
            volume = round(max(0., volume), 8)
            old_risk = sum(p['risk'] for p in active.values())
            same_risk = sum(p['risk'] for p in active.values() if p['symbol'] == row['symbol'])
            risk = volume * row['unit_risk']
            spread = spec['spread_cash_per_lot'] if stress else 0.
            entry_unit = row['entry_unit_cash'] - spread
            entry_cash = round(entry_unit * volume, 2)
            margin = volume * row['margin_unit_proxy'] * (2 if stress else 1)
            protected = cash - old_risk - risk + min(0., entry_cash)
            reason = None
            if floor_time is not None:
                reason = 'floor_latched'
            elif cash >= target:
                reason = 'target_waiting_flat'
            elif paused:
                reason = 'daily_pause'
            elif volume < spec['volume_min'] - 1e-9:
                reason = 'minimum_lot'
            elif ident in active:
                reason = 'duplicate_position'
            elif old_risk + risk > cash * min(2*risk_fraction, .60) + 1e-7:
                reason = 'aggregate_risk'
            elif same_risk + risk > budget + 1e-7:
                reason = 'same_symbol_risk'
            elif protected <= 0 or sum(p['margin'] for p in active.values()) + margin > .8*protected + 1e-7:
                reason = 'margin_proxy'
            if reason:
                counts[reason] += 1
            else:
                assert risk <= budget + 1e-6
                active[ident] = dict(symbol=row['symbol'], lots=volume, risk=risk, margin=margin,
                                     fraction=1., net=entry_cash, op=t, key=row['key'], id=ident)
                cash = round(cash + entry_cash, 2)
                counts['opened'] += 1
            if detail:
                decisions.append(dict(epoch=t, id=ident, key=row['key'], decision=reason or 'opened',
                    budget=budget, volume=volume, planned_stop_risk=risk, margin_proxy=margin))
        elif ident in active:
            p = active[ident]
            extra = 0.
            if stress:
                extra = symbols[row['symbol']]['spread_cash_per_lot'] * flow['closed_volume_fraction']
                extra += max(0., -flow.get('swap_unit', 0.))
            value = round((flow['cash_unit'] - extra) * p['lots'], 2)
            p['net'] = round(p['net'] + value, 2)
            cash = round(cash + value, 2)
            p['fraction'] -= flow['closed_volume_fraction']
            if p['fraction'] <= 1e-7:
                closed.append(dict(id=ident, key=p['key'], op=p['op'], cl=t, lots=p['lots'],
                                   net=p['net'], risk=p['risk']))
                del active[ident]
        observe(t)
    status = 'hit' if hit_time is not None else 'floor' if floor_time is not None else 'timeout'
    counts['closed_positions'] = len(closed)
    out = dict(start=start, end_exclusive=end, status=status, ending_closed_cash=cash,
        open_positions=len(active), max_closed_dd_pct=maxdd, counts=dict(counts),
        hit_epoch=hit_time, hit_days=(hit_time-start)/DAY if hit_time is not None else None,
        floor_epoch=floor_time, last_event=last_time,
        no_admitted_positions=counts['opened']==0)
    if detail:
        wins = [p['net'] for p in closed if p['net']>0]
        losses = [p['net'] for p in closed if p['net']<0]
        ws = ls = mw = ml = 0
        for p in closed:
            ws = ws+1 if p['net']>0 else 0
            ls = ls+1 if p['net']<0 else 0
            mw, ml = max(mw,ws), max(ml,ls)
        out.update(closed_positions=closed, decisions=decisions, curve=curve,
            trade_stats=dict(trades=len(closed), win_rate_pct=100*len(wins)/len(closed) if closed else None,
                profit_factor=-sum(wins)/sum(losses) if losses else None,
                max_win_streak=mw, max_loss_streak=ml))
    return out


def summarize(attempts):
    n = len(attempts)
    hits = [a for a in attempts if a['status']=='hit']
    times = [a['hit_days'] for a in hits]
    fast = min(hits, key=lambda a:a['hit_days']) if hits else None
    return dict(starts=n, hits=len(hits), hit_pct=100*len(hits)/n,
        floor_pct=100*sum(a['status']=='floor' for a in attempts)/n,
        timeout_pct=100*sum(a['status']=='timeout' for a in attempts)/n,
        no_trade_pct=100*sum(a['no_admitted_positions'] for a in attempts)/n,
        median_hit_days=statistics.median(times) if times else None,
        all_start_median_days=(sorted(times)[(n-1)//2]+sorted(times)[n//2])/2 if len(hits)>n//2 else None,
        mean_capped_days=statistics.mean([a['hit_days'] if a['status']=='hit' else 365. for a in attempts]),
        ending_cash_p10=quantile([a['ending_closed_cash'] for a in attempts],.1),
        ending_cash_median=quantile([a['ending_closed_cash'] for a in attempts],.5),
        ending_cash_p90=quantile([a['ending_closed_cash'] for a in attempts],.9),
        median_closed_dd_pct=statistics.median(a['max_closed_dd_pct'] for a in attempts),
        worst_closed_dd_pct=max(a['max_closed_dd_pct'] for a in attempts),
        fastest=dict(start=fast['start'], hit_epoch=fast['hit_epoch'], days=fast['hit_days']) if fast else None,
        total_counts=dict(sum((Counter(a['counts']) for a in attempts), Counter())))


def config(keys, risk):
    keys = sorted(keys)
    return dict(id='+'.join(keys)+'@'+str(risk), keys=keys, risk_pct=risk)


def rank(c):
    s = c['summary']
    if s['hit_pct'] >= 50:
        return (0, s['median_hit_days'], -s['hit_pct'], s['median_closed_dd_pct'], c['id'])
    return (1, -s['hit_pct'], s['mean_capped_days'], -s['ending_cash_median'], c['id'])


def verify_freeze():
    f = read('FROZEN.json')
    for p, h in f['files'].items():
        assert digest(p)==h, 'Frozen file changed: '+p
    for p, h in read('INPUTS.json')['source_hashes'].items():
        assert digest(p)==h, 'Source changed: '+p


def freeze():
    assert not (ROOT/'DEVELOPMENT.json').exists() and not (ROOT/'RESULTS.json').exists()
    source = read('INPUTS.json')
    assert all(digest(p)==h for p,h in source['source_hashes'].items())
    paths = [ROOT/n for n in ['PLAN.json','BROKER.json','INPUTS.json','SOURCE AUDIT.json','prepare_sources.py','simulate.py']]
    save('FROZEN.json', dict(files={str(p):digest(p) for p in paths}, before_challenge_outcomes=True))
    print('FROZEN before challenge outcomes')


def develop():
    verify_freeze()
    assert not (ROOT/'SELECTION.json').exists() and not (ROOT/'RESULTS.json').exists()
    plan, source = read('PLAN.json'), read('INPUTS.json')
    rows, symbols = source['rows'], source['symbols']
    starts = weekly_starts(plan['development'])
    keys = sorted({r['key'] for r in rows})
    cache = {}
    completed = 0
    def evaluate(c):
        nonlocal completed
        k = tuple(c['keys'])
        if k not in cache:
            cache[k] = build_events(rows, set(k))
        aa = [replay(cache[k],symbols,c['risk_pct'],t,t+365*DAY) for t in starts]
        completed += 1
        if completed % 25 == 0:
            print(json.dumps({'stage':'development_progress','configurations_completed':completed}),flush=True)
        return dict(**c,summary=summarize(aa),attempts=aa)
    singles = [evaluate(config([key],r)) for key in keys for r in plan['risk_percentages']]
    best_by_family = {}
    family_map = {r['key']:r.get('variant_group',r['key']) for r in rows}
    for c in sorted(singles,key=rank):
        family = family_map[c['keys'][0]]
        best_by_family.setdefault(family,c)
    shortlist = [c['keys'][0] for c in sorted(best_by_family.values(),key=rank)[:8]]
    baskets = {tuple(sorted(k)) for size in (2,3) for k in combinations(shortlist,size)}
    named = source['metadata']['named_baskets']
    for members in named.values():
        if isinstance(members, dict):
            members = members.get('keys',members.get('members',[]))
        members = sorted(set(members).intersection(keys))
        if len(members)>1 and len({family_map[k] for k in members})==len(members):
            baskets.add(tuple(members))
    combos = [evaluate(config(k,r)) for k in sorted(baskets) for r in plan['risk_percentages']]
    save('DEVELOPMENT.json',dict(starts=starts,shortlist=shortlist,singles=singles,combos=combos,
        configuration_count=len(singles)+len(combos), frozen_sha256=digest(ROOT/'FROZEN.json')))
    locked = []
    for kind, cc in [('single',singles),('combo',combos)]:
        primary = min(cc,key=rank)
        most = min(cc,key=lambda c:(-c['summary']['hit_pct'],c['summary']['mean_capped_days'],-c['summary']['ending_cash_median'],c['id']))
        hit_configs = [c for c in cc if c['summary']['fastest']]
        lottery = min(hit_configs,key=lambda c:(c['summary']['fastest']['days'],-c['summary']['hit_pct'],c['id'])) if hit_configs else primary
        for label,c in [('primary',primary),('highest_hit_rate',most),('fastest_observed',lottery)]:
            locked.append(dict(kind=kind,role=label,qualified=c['summary']['hit_pct']>=50,
                id=c['id'],keys=c['keys'],risk_pct=c['risk_pct'],development=c['summary']))
    save('SELECTION.json',dict(status='LOCKED before evaluation',locked=locked,
        development_sha256=digest(ROOT/'DEVELOPMENT.json'),frozen_sha256=digest(ROOT/'FROZEN.json')))
    print(json.dumps(dict(stage='DEVELOPMENT',configurations=len(singles)+len(combos),starts=len(starts),locked=len(locked))))


def evaluate():
    verify_freeze()
    plan, source, selection = read('PLAN.json'), read('INPUTS.json'), read('SELECTION.json')
    assert selection['development_sha256']==digest(ROOT/'DEVELOPMENT.json')
    assert selection['frozen_sha256']==digest(ROOT/'FROZEN.json')
    assert not (ROOT/'RESULTS.json').exists()
    starts = weekly_starts(plan['evaluation'])
    results = []
    for c in {x['id']:x for x in selection['locked']}.values():
        events = build_events(source['rows'],set(c['keys']))
        for stress in (False,True):
            attempts = [replay(events,source['symbols'],c['risk_pct'],t,t+365*DAY,stress=stress) for t in starts]
            summary = summarize(attempts)
            # Detailed fastest path is retrospective. Also show a median-endpoint path.
            representative = sorted(attempts,key=lambda a:a['ending_closed_cash'])[len(attempts)//2]
            chosen_starts = {representative['start']}
            if summary['fastest']:
                chosen_starts.add(summary['fastest']['start'])
            details = [replay(events,source['symbols'],c['risk_pct'],t,t+365*DAY,True,stress) for t in sorted(chosen_starts)]
            results.append(dict(id=c['id'],keys=c['keys'],risk_pct=c['risk_pct'],cost='stress' if stress else 'recorded',
                                summary=summary,attempts=attempts,details=details))
    save('RESULTS.json',dict(status='COMPLETE research-only historical cash replay',results=results,
        plan_sha256=digest(ROOT/'PLAN.json'),inputs_sha256=digest(ROOT/'INPUTS.json'),
        frozen_sha256=digest(ROOT/'FROZEN.json'),selection_sha256=digest(ROOT/'SELECTION.json'),
        historical_fraction_not_future_probability=True,no_live_changes=True))
    print(json.dumps(dict(stage='EVALUATION',starts=len(starts),comparisons=len(results),sha256=digest(ROOT/'RESULTS.json'))))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('stage',choices=['freeze','develop','evaluate'])
    {'freeze':freeze,'develop':develop,'evaluate':evaluate}[parser.parse_args().stage]()
