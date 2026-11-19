"""Owner 2026-11-19: "if I bought this account by October start, show me breakdown day by day till today".
$10k FTMO 1-Step bought 2026-10-01: challenge at 0.75% risk, then the funded account at 0.5% (owner plan), Best 1-Step 10 EAs, Nasdaq 5M x0.75.
Trades = native Model-4 runs (study.py, $10k, 1% each, real ticks, 2026-10-01 -> tester data end 2026-11-18 23:59 UTC; trades still open then are
closed by the tester at the last price = floating value, flagged). Lots re-sized for $10k: volume x (risk / 1%) rounded DOWN to 0.01, skipped below 0.01
(the guard sizes from the saved starting balance and rounds down). Minute equity from M1 bars (worst price of each bar: long low, short high + spread).
FTMO 1-Step (RULES.md of Multi Firm Funded 2026-11-17): daily loss 3% ($300) from the balance at 00:00 Prague, equity-tested; max loss 10% trailing the
highest Prague-midnight balance, locked at the initial balance; target +10% with best day <= 50% of total profit (checked at end of day, closed balance);
funded account starts 4 days after the pass (sim.py convention), first reward request >= 14 days later, 90% split, best-day rule per cycle.
Not modelled: the guard's own limits (daily reserve 2.5%, caps), weekend flat, news guard, commissions beyond the native ones. python account.py bars | run"""
import gzip, json, math, sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np

H = Path(__file__).resolve().parent; TERM = H.parent / '_Backtests/MT5-DMC-20260811/terminal64.exe'
SYMS = ('XAUUSD', 'USTEC', 'USDJPY', 'UK100'); A = datetime(2026, 9, 30, tzinfo=timezone.utc); E = datetime(2026, 11, 19, tzinfo=timezone.utc)
SIZE = 10_000.0; RISK_CH, RISK_F = 0.0075, 0.005; NAS = 'nasdaq-5m-candle-momentum'; NAS_F = 0.75
SHORT = {NAS: 'NAS', 'usdjpy-london-open-momentum': 'JPY', '3-way-gold': '3WG', 'ema3': 'EMA3', 'us100-selective-orb-v3': 'SEL', 'xau-rsi-vwap': 'RSI',
         'orb-volume-profile-volume-confirmed': 'ORBVC', 'overnight-bias-orb': 'ONB', 'uk100-monday-dip': 'UK', 'asia-breakout': 'ASIA'}


def bars():
    import MetaTrader5 as mt5
    assert mt5.initialize(path=str(TERM), portable=True, timeout=120000), mt5.last_error()
    try:
        assert 'MT5-DMC-20260811' in mt5.terminal_info().path, 'not the isolated research terminal'
        (H / 'bars').mkdir(exist_ok=True)
        for s in SYMS:
            mt5.symbol_select(s, True); r = mt5.copy_rates_range(s, mt5.TIMEFRAME_M1, A, E); assert r is not None and len(r), (s, mt5.last_error())
            np.savez_compressed(H / 'bars' / f'{s}_M1.npz', time=r['time'], high=r['high'], low=r['low'], spread=r['spread'], point=mt5.symbol_info(s).point)
            print(s, len(r), datetime.fromtimestamp(int(r['time'][0]), timezone.utc), '->', datetime.fromtimestamp(int(r['time'][-1]), timezone.utc), flush=True)
    finally:
        mt5.shutdown()


def ts(s): return int(datetime.fromisoformat(s[:19]).replace(tzinfo=timezone.utc).timestamp())


def prague_day(t):   # CEST (UTC+2) until 2026-10-25 01:00 UTC, then CET (UTC+1)
    off = 1 if t >= int(datetime(2026, 10, 25, 1, tzinfo=timezone.utc).timestamp()) else 2
    return (datetime.fromtimestamp(t, timezone.utc) + timedelta(hours=off)).date()


def load_trades():
    T = []
    for p in sorted((H / 'native').glob('nw-*/trades.json.gz')):
        key = p.parent.name[3:]
        for t in json.loads(gzip.open(p).read()):
            d = 1 if t['side'] == 'Long' else -1; move = (t['close_price'] - t['open_price']) * d
            T.append(dict(key=key, ea=SHORT[key], sym=t['symbol'], d=d, o=ts(t['open_time']), c=ts(t['close_time']), op=t['open_price'], vol=t['volume'],
                          net=t['net_profit'], vpu=(t['gross_profit'] / move / t['volume']) if abs(move) > 1e-9 else None,
                          end_of_test='end of test' in str(t.get('exit_comment', ''))))
    for x in T:                                   # money per price unit per lot from other trades of the symbol when a trade closed flat
        if x['vpu'] is None: x['vpu'] = float(np.median([y['vpu'] for y in T if y['sym'] == x['sym'] and y['vpu']]))
    return sorted(T, key=lambda x: x['o'])


def run():
    B = {s: dict(np.load(H / 'bars' / f'{s}_M1.npz')) for s in SYMS}; T = load_trades()
    grid = np.arange(int(A.timestamp()) + 86400, int(E.timestamp()), 60)        # from 2026-10-01 00:00 UTC
    state = 'challenge'; bal = SIZE; start_day_bal = SIZE; hwm = SIZE; ready = None; fund_start = None; next_pay = None
    days, dp, cycle_dp, open_ = {}, [], [], []
    events = []; i_trade = 0; cur_day = None; cycle_start_bal = SIZE; payouts = []
    def risk_now(): return RISK_CH if state == 'challenge' else RISK_F
    def floating(t):
        f = 0.0
        for x in open_:
            b = B[x['sym']]; j = np.searchsorted(b['time'], t // 60 * 60, 'right') - 1
            if j < 0 or b['time'][j] < x['o'] // 60 * 60: continue
            pt = float(b['point']); worst = (b['low'][j] - x['op']) if x['d'] > 0 else (x['op'] - b['high'][j] - b['spread'][j] * pt)
            f += worst * x['vpu'] * x['lots']
        return f
    for t in grid:
        t = int(t); d = prague_day(t)
        if d != cur_day:                                            # Prague midnight: close the previous day
            if cur_day is not None:
                rec = days[cur_day]; rec['end_bal'] = round(bal, 2)
                if state in ('challenge', 'funded'):
                    hwm = max(hwm, bal)
                if state == 'challenge': dp.append(rec['pnl'])
                if state == 'funded': cycle_dp.append(rec['pnl'])
                if state == 'challenge':
                    prof = bal - SIZE; best = max([x for x in dp] + [0.0])
                    rec['best_day_share'] = round(100 * best / prof, 1) if prof > 0 else None
                    if prof >= 0.10 * SIZE and best <= 0.5 * prof:
                        state = 'passed'; ready = cur_day + timedelta(days=4); rec['note'] = 'CHALLENGE PASSED (+10%, best day <= 50%)'; events.append((str(cur_day), 'passed', round(bal, 2)))
                        open_ = []
                elif state == 'funded' and d >= next_pay:
                    prof = bal - cycle_start_bal; best = max(cycle_dp + [0.0])
                    if prof > 0 and best <= 0.5 * prof:
                        pay = round(0.9 * prof, 2); payouts.append((str(d), pay)); rec['note'] = (rec.get('note', '') + f' reward request ${pay:,.0f} (90% of ${prof:,.0f})').strip()
                        events.append((str(d), 'payout', pay)); bal = cycle_start_bal = SIZE; hwm = SIZE; cycle_dp = []; next_pay = d + timedelta(days=14)
            cur_day = d; start_day_bal = bal
            if state == 'passed' and d >= ready:
                state = 'funded'; fund_start = d; bal = cycle_start_bal = start_day_bal = hwm = SIZE; next_pay = d + timedelta(days=14); cycle_dp = []
                events.append((str(d), 'funded start', SIZE))
            days[d] = dict(day=str(d), phase=state, start_bal=round(bal, 2), closed=0, pnl=0.0, eas=defaultdict(float), min_eq=bal, skipped=0, note='')
            if state == 'funded' and d == fund_start: days[d]['note'] = 'FUNDED account starts at $10,000 (0.5% risk)'
        rec = days[d]
        while i_trade < len(T) and T[i_trade]['o'] <= t:              # open trades whose entry is at or before this minute
            x = dict(T[i_trade]); i_trade += 1
            if state not in ('challenge', 'funded'): continue
            k = risk_now() / 0.01 * (NAS_F if x['key'] == NAS else 1.0)
            lots = math.floor(x['vol'] * k / 0.01 + 1e-9) * 0.01
            if lots < 0.01: rec['skipped'] += 1; continue
            x['lots'] = lots; x['pnl'] = x['net'] * lots / x['vol']; x['phase'] = state; open_.append(x)
        for x in [x for x in open_ if x['c'] <= t]:                    # closes
            open_.remove(x); bal += x['pnl']; rec['closed'] += 1; rec['pnl'] += x['pnl']; rec['eas'][x['ea'] + ('*' if x['end_of_test'] else '')] += x['pnl']
        if state in ('challenge', 'funded'):
            eq = bal + floating(t); rec['min_eq'] = min(rec['min_eq'], eq)
            floor = min(hwm - 0.10 * SIZE, SIZE)
            if start_day_bal - eq >= 0.03 * SIZE or eq <= floor:
                why = 'daily loss 3%' if start_day_bal - eq >= 0.03 * SIZE else 'max loss 10%'
                rec['note'] = f'BREACH ({why}) at {datetime.fromtimestamp(t, timezone.utc):%H:%M} UTC'; events.append((str(d), 'breach ' + why, round(eq, 2))); state = 'breached'; open_ = []
        # day P&L list for the best-day rule (closed P&L per Prague day)
    out_days = []
    for d in sorted(days):
        r = days[d]
        if r['closed'] == 0 and r['skipped'] == 0 and not r['note'] and r['phase'] not in ('challenge', 'funded'): continue
        out_days.append(dict(day=r['day'], weekday=datetime.fromisoformat(r['day']).strftime('%a'), phase=r['phase'], closed=r['closed'], skipped=r['skipped'],
                             pnl=round(r['pnl'], 2), end_bal=r.get('end_bal', round(bal, 2)), worst_intraday=round(r['min_eq'] - r['start_bal'], 2),
                             daily_room_left=round(0.03 * SIZE + (r['min_eq'] - r['start_bal']), 2), eas={k: round(v, 2) for k, v in sorted(r['eas'].items(), key=lambda z: -abs(z[1]))},
                             note=r['note']))
    res = dict(account='FTMO 1-Step $10,000 bought 2026-10-01', challenge_risk=RISK_CH, funded_risk=RISK_F, nasdaq_factor=NAS_F, data_end='2026-11-18 23:59 UTC',
               events=events, payouts=payouts, final_state=state, final_balance=round(bal, 2), open_at_end=[(x['ea'], x['phase']) for x in open_], days=out_days)
    (H / 'ACCOUNT.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
    print(json.dumps({k: v for k, v in res.items() if k != 'days'}, indent=1))
    for r in out_days:
        print(f"{r['day']} {r['weekday']} {r['phase']:<9} n={r['closed']} skip={r['skipped']} pnl={r['pnl']:+8.2f} bal={r['end_bal']:9.2f} worst={r['worst_intraday']:+8.2f} {dict(r['eas'])} {r['note']}")


if __name__ == '__main__':
    {'bars': bars, 'run': run}[sys.argv[1]]()
