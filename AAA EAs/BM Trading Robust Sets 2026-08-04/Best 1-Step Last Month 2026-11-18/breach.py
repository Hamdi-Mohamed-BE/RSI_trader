"""Owner 2026-11-18: "would this have breached an account?" Minute-by-minute equity of the last-month native trades (study.py) on ONE $100k account.
bars: M1 bars XAUUSD / USTEC / USDJPY / UK100 2026-10-17 -> 2026-11-18 from the ISOLATED research terminal (_Backtests/MT5-DMC-20260811, read-only
copy_rates_range, shut down afterwards) -> bars/*.npz.
check: each trade scaled from its native run ($10k, 1%) to the account (risk r of $100k; Nasdaq 5M x0.75). Open-trade P&L each minute at the WORST price of the bar
(long: bar low; short: bar high + bar spread), money per price unit from the trade's own gross / price move. Closed balance changes by net profit at the close.
Limits (RULES.md of Multi Firm Funded 2026-11-17 + email replies):
  FTMO 1-Step: daily 3% ($3,000) from the balance at 00:00 Prague; max loss 10% trailing the highest Prague-midnight balance, locked at the initial balance.
  FTMO 2-Step: daily 5% from the Prague-midnight balance; max loss 10% static.
  FundingPips: daily 5% from the higher of balance / equity at 00:00 UTC+3; max loss 10% static (hedging rule not checked here).
  The5ers HS: daily 5% from the higher of balance / equity at 00:00 server (ASSUMED UTC+2/+3 like FP -> UTC+3 used); max loss 10% static.
No guard, no weekend flat, no news closes (same as study.py). python breach.py bars | check"""
import gzip, json, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

H = Path(__file__).resolve().parent; TERM = H.parent / '_Backtests/MT5-DMC-20260811/terminal64.exe'
SYMS = ('XAUUSD', 'USTEC', 'USDJPY', 'UK100'); A = datetime(2026, 10, 17, tzinfo=timezone.utc); E = datetime(2026, 11, 18, tzinfo=timezone.utc)
FACTOR = {'nasdaq-5m-candle-momentum': 0.75}; SIZE = 100_000.0


def bars():
    import MetaTrader5 as mt5
    assert mt5.initialize(path=str(TERM), portable=True, timeout=120000), mt5.last_error()
    try:
        info = mt5.terminal_info(); assert info and 'MT5-DMC-20260811' in info.path, 'not the isolated research terminal'
        (H / 'bars').mkdir(exist_ok=True); meta = {}
        for s in SYMS:
            mt5.symbol_select(s, True); r = mt5.copy_rates_range(s, mt5.TIMEFRAME_M1, A, E); assert r is not None and len(r), (s, mt5.last_error())
            si = mt5.symbol_info(s); meta[s] = dict(point=si.point, bars=len(r))
            np.savez_compressed(H / 'bars' / f'{s}_M1.npz', time=r['time'], high=r['high'], low=r['low'], spread=r['spread'])
            print(s, len(r), datetime.fromtimestamp(int(r['time'][0]), timezone.utc), '->', datetime.fromtimestamp(int(r['time'][-1]), timezone.utc), flush=True)
        (H / 'bars' / 'meta.json').write_text(json.dumps(meta, indent=1))
    finally:
        mt5.shutdown()


def ts(s): return int(datetime.fromisoformat(s[:19]).replace(tzinfo=timezone.utc).timestamp())


def prague_offset(t):   # CEST (UTC+2) until the last Sunday of October 01:00 UTC, then CET (UTC+1)
    return 1 if t >= int(datetime(2026, 10, 25, 1, tzinfo=timezone.utc).timestamp()) else 2


def day_key(t, firm):
    off = prague_offset(t) if firm.startswith('FTMO') else 3
    return (datetime.fromtimestamp(t, timezone.utc) + timedelta(hours=off)).date().isoformat()


def check():
    meta = json.loads((H / 'bars' / 'meta.json').read_text()); B = {s: dict(np.load(H / 'bars' / f'{s}_M1.npz')) for s in SYMS}
    trades = []
    for p in (H / 'native').glob('nw-*/trades.json.gz'):
        key = p.parent.name[3:]
        for t in json.loads(gzip.open(p).read()):
            d = 1 if t['side'] == 'Long' else -1; move = (t['close_price'] - t['open_price']) * d
            trades.append(dict(key=key, sym=t['symbol'], d=d, o=ts(t['open_time']), c=ts(t['close_time']), op=t['open_price'], net=t['net_profit'], gross=t['gross_profit'],
                               vpu=(t['gross_profit'] / move) if abs(move) > 1e-9 else None, vol=t['volume']))
    # money per price unit per lot from other trades of the same symbol when a trade closed at its open price
    per_lot = {s: np.median([x['vpu'] / x['vol'] for x in trades if x['sym'] == s and x['vpu']]) for s in SYMS if any(x['sym'] == s for x in trades)}
    for x in trades:
        if x['vpu'] is None: x['vpu'] = per_lot[x['sym']] * x['vol']
    grid = np.arange(int(A.timestamp()), int(E.timestamp()) + 60, 60); n = len(grid)
    out = {}
    for risk in (0.0075, 0.005):
        scale = {x['key']: risk * SIZE / 100.0 * FACTOR.get(x['key'], 1.0) for x in trades}   # native $ at 1% of $10k = $100 per R
        closed = np.zeros(n); flt = np.zeros(n)
        for x in trades:
            f = scale[x['key']]        # account $ per native $: native 1R = $100, account 1R = risk x $100k
            ci = np.searchsorted(grid, x['c'], 'right'); closed[ci:] += x['net'] * f
            b = B[x['sym']]; pt = meta[x['sym']]['point']
            sel = (b['time'] >= x['o'] // 60 * 60) & (b['time'] < x['c'])
            if not sel.any(): continue
            tt = b['time'][sel]; worst = (b['low'][sel] - x['op']) if x['d'] > 0 else (x['op'] - b['high'][sel] - b['spread'][sel] * pt)
            pnl = worst * x['vpu'] * f
            gi = np.clip(np.searchsorted(grid, tt), 0, n - 1)
            acc = np.zeros(n); np.add.at(acc, gi, pnl); flt += acc
        bal = SIZE + closed; eq = bal + flt
        res = {}
        for firm, daily, basis, trail in (('FTMO 1-Step', 0.03, 'bal', True), ('FTMO 2-Step', 0.05, 'bal', False), ('FundingPips Standard', 0.05, 'max', False), ('The5ers High Stakes', 0.05, 'max', False)):
            days = np.array([day_key(int(t), firm) for t in grid]); worst_day = (0.0, None); hwm = SIZE; min_room = (1e18, None); start = None; cur = None
            for i in range(n):
                if days[i] != cur:
                    if cur is not None and trail: hwm = max(hwm, bal[i - 1])
                    cur = days[i]; start = bal[i] if basis == 'bal' else max(bal[i], eq[i])
                floor = min(hwm - 0.10 * SIZE, SIZE) if trail else SIZE * 0.90
                loss = start - eq[i]
                if loss > worst_day[0]: worst_day = (loss, cur, datetime.fromtimestamp(int(grid[i]), timezone.utc).isoformat()[:16])
                if eq[i] - floor < min_room[0]: min_room = (eq[i] - floor, datetime.fromtimestamp(int(grid[i]), timezone.utc).isoformat()[:16])
            res[firm] = dict(daily_limit=daily * SIZE, worst_daily_loss=round(worst_day[0], 0), worst_day=worst_day[1], at_utc=worst_day[2],
                             daily_headroom=round(daily * SIZE - worst_day[0], 0), daily_breach=bool(worst_day[0] >= daily * SIZE),
                             max_loss_min_room=round(min_room[0], 0), at=min_room[1], max_loss_breach=bool(min_room[0] <= 0))
        i_low = int(np.argmin(eq))
        out[f'{risk * 100:g}%'] = dict(firms=res, lowest_equity=round(float(eq[i_low]), 0), lowest_at=datetime.fromtimestamp(int(grid[i_low]), timezone.utc).isoformat()[:16],
                                       end_closed=round(float(bal[-1]), 0), end_equity=round(float(eq[-1]), 0))
    (H / 'BREACH.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); print(json.dumps(out, indent=1))


if __name__ == '__main__':
    {'bars': bars, 'check': check}[sys.argv[1]]()
