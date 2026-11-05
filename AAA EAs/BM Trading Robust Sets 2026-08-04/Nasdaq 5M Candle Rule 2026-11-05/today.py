"""Owner 2026-11-05: today's trade for every Nasdaq 5M version, the open RR and where the stop could be. READ ONLY: attaches to the normal MT5 only if it is already running and reads USTEC M5 bars and the current tick; it
never reads positions, never sends or changes an order, and never starts a terminal. Bar-level replay of the EA's rules (nas.py VERSIONS) from 2026-09-01: 09:30 New York signal bar, EMA12, MT5 iADX(14) +DI / -DI, MT5 iATR(14) as a simple average of true range,
entry at the next bar open (ask for longs), one trade per New York date, no entry while the version still holds a position; stop, target and 15:55 session close checked bar by bar with the stop tested first; ATR x 6 trail from +1R off the best price since entry.
A simulation of each version, not the owner's live positions. Accuracy is measured against the native October ledgers. -> TODAY.json"""
import gzip, json, re, sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

H = Path(__file__).resolve().parent; NY = ZoneInfo('America/New_York'); TERMINAL = r'C:\Program Files\MetaTrader 5\terminal64.exe'
ATR6, P60, FIXED = dict(stop='atr', mult=6.0, tp=0, trail=True, session=False), dict(stop='pct', pct=0.60, tp=0, trail=True, session=False), dict(stop='atr', mult=4.0, tp=2.5, trail=False, session=True)
DYN = dict(stop='atr', mult=4.0, tp=0, trail=True, session=True)      # the 50-20 step needs a target, and this preset has none, so only the ATR trail and the session close act
V = {}
for rule in ('EMA', 'CANDLE'):
    for name, m in (('ATR6', ATR6), ('P60', P60), ('FIXED', FIXED)):
        for di in (True, False): V[f"{rule}_{name}_{'DION' if di else 'DIOFF'}"] = dict(m, rule=rule, di=di)
V['EMA_DYN_DIOFF'] = dict(DYN, rule='EMA', di=False)


def indicators(b):
    n = len(b); ema = [b[0]['close']] * n; atr = [0.0] * n; pdi = [0.0] * n; mdi = [0.0] * n; tr = [b[0]['high'] - b[0]['low']] * n; a12, a14 = 2 / 13, 2 / 15
    for i in range(1, n):
        h, l, c, pc = b[i]['high'], b[i]['low'], b[i]['close'], b[i - 1]['close']; ema[i] = ema[i - 1] + a12 * (c - ema[i - 1]); tr[i] = max(h - l, abs(h - pc), abs(l - pc))
        p, m = max(h - b[i - 1]['high'], 0.0), max(b[i - 1]['low'] - l, 0.0)
        if p > m: m = 0.0
        elif m > p: p = 0.0
        else: p = m = 0.0
        ps, ms = (100 * p / tr[i], 100 * m / tr[i]) if tr[i] else (0.0, 0.0)
        pdi[i] = pdi[i - 1] + a14 * (ps - pdi[i - 1]); mdi[i] = mdi[i - 1] + a14 * (ms - mdi[i - 1])
        atr[i] = sum(tr[max(0, i - 13):i + 1]) / min(14, i + 1)
    return ema, atr, pdi, mdi


def walk(bars, ind, c, point, start, tick, now):
    ema, atr, pdi, mdi = ind; pos = None; closed = []; traded = set(); today = now.astimezone(NY).date(); note = None
    for i in range(1, len(bars)):
        b = bars[i]; t = datetime.fromtimestamp(b['time'], timezone.utc); ny = t.astimezone(NY); spread = b['spread'] * point; live = i == len(bars) - 1
        if pos and not live:
            buy = pos['dir'] > 0; lo, hi = b['low'], b['high'] + spread
            if c['session'] and (ny.hour, ny.minute) >= (15, 55) and ny.date() >= pos['ny_date'] : ex, why = (b['open'] if buy else b['open'] + spread), 'session close'
            elif (buy and lo <= pos['sl']) or (not buy and hi >= pos['sl']): ex, why = pos['sl'], 'stop'
            elif pos['tp'] and ((buy and b['high'] >= pos['tp']) or (not buy and b['low'] + spread <= pos['tp'])): ex, why = pos['tp'], 'target'
            else: ex = None
            if ex is not None:
                closed.append(dict(pos, exit=ex, exit_time=t.isoformat(), why=why, r=round(pos['dir'] * (ex - pos['entry']) / pos['risk'], 2))); pos = None
            else:
                pos['best'] = max(pos['best'], b['high']) if buy else min(pos['best'], b['low'])
                if c['trail']:
                    fav = (pos['best'] - pos['entry']) if buy else (pos['entry'] - pos['best'] - spread)
                    if fav >= pos['risk']:
                        cand = pos['best'] - 6 * atr[i] if buy else pos['best'] + 6 * atr[i]
                        if (buy and cand > pos['sl']) or (not buy and cand < pos['sl']): pos['sl'] = cand
        sig = datetime.fromtimestamp(bars[i - 1]['time'], timezone.utc).astimezone(NY)
        if (sig.hour, sig.minute) != (9, 30) or t < start or sig.date() in traded: continue
        if pos:
            if sig.date() == today: note = f"today's signal skipped: still holding the {pos['open_time'][:10]} trade"
            continue
        s = bars[i - 1]; x = s['close'] - (ema[i - 1] if c['rule'] == 'EMA' else s['open']); d = 1 if x > 0 else -1 if x < 0 else 0
        if d == 0: continue
        if c['di'] and not (pdi[i - 1] > mdi[i - 1] if d > 0 else mdi[i - 1] > pdi[i - 1]):
            if sig.date() == today: note = f"today's signal ({'long' if d > 0 else 'short'}) blocked by DI"
            traded.discard(sig.date()); continue
        entry = b['open'] + spread if d > 0 else b['open']; dist = c['mult'] * atr[i - 1] if c['stop'] == 'atr' else entry * c['pct'] / 100; sl = entry - d * dist
        pos = dict(dir=d, entry=entry, risk=dist, sl=sl, initial_sl=sl, tp=entry + d * c['tp'] * dist if c['tp'] else 0, best=entry, open_time=t.isoformat(), ny_date=sig.date()); traded.add(sig.date())
    return pos, closed, note


def main():
    import MetaTrader5 as mt5
    assert mt5.initialize(path=TERMINAL, timeout=60000), mt5.last_error()
    term, acc = mt5.terminal_info(), mt5.account_info(); assert Path(term.path).resolve() == Path(TERMINAL).parent.resolve(), term.path
    info = mt5.symbol_info('USTEC'); assert info is not None, 'USTEC not on this terminal'
    rates = mt5.copy_rates_from_pos('USTEC', mt5.TIMEFRAME_M5, 0, 18000); tick = mt5.symbol_info_tick('USTEC'); server = acc.server; point = info.point; mt5.shutdown()
    assert rates is not None and tick is not None; bars = [{k: (float(r[k]) if k != 'time' else int(r[k])) for k in ('time', 'open', 'high', 'low', 'close', 'spread')} for r in rates]
    now = datetime.now(timezone.utc); offset = round((tick.time - now.timestamp()) / 3600); assert offset == 0, f'server clock offset {offset}h: replay assumes UTC bars'
    start = datetime(2026, 9, 1, tzinfo=timezone.utc); ind = indicators(bars); atr_now = ind[1][-1]; out = dict(server=server, bid=tick.bid, ask=tick.ask, tick_utc=datetime.fromtimestamp(tick.time, timezone.utc).isoformat(), atr=round(atr_now, 2), versions={}, parity={})
    print(f"server {server}; bid {tick.bid} ask {tick.ask} at {out['tick_utc']}; M5 ATR(14) {atr_now:.1f}; first bar {datetime.fromtimestamp(bars[0]['time'], timezone.utc).date()}", flush=True)
    for v, c in V.items():
        pos, closed, note = walk(bars, ind, c, point, start, tick, now)
        p = H / f'native/nw-USTEC-{v}-all/trades.json.gz'
        if p.exists():
            N = [t for t in json.loads(gzip.open(p).read()) if '2026-09-08' <= t['open_time'] < '2026-10-30']; S = [t for t in closed if '2026-09-08' <= t['open_time'][:10] < '2026-10-30']
            nk = {(t['open_time'][:10], 1 if t['side'] == 'Long' else -1): t for t in N}; sk = {(t['open_time'][:10], t['dir']): t for t in S}; both = nk.keys() & sk.keys()
            ep = [abs(sk[k]['entry'] - nk[k]['open_price']) for k in both]
            out['parity'][v] = dict(native=len(nk), replay=len(sk), same_day_side=len(both), median_entry_gap=round(sorted(ep)[len(ep) // 2], 2) if ep else None)
        rec = dict(note=note, closed_today=[dict(side='long' if t['dir'] > 0 else 'short', entry=round(t['entry'], 2), exit=round(t['exit'], 2), why=t['why'], r=t['r']) for t in closed if t['exit_time'][:10] == now.date().isoformat()])
        if pos:
            d = pos['dir']; cur = tick.bid if d > 0 else tick.ask; rr = d * (cur - pos['entry']) / pos['risk']; trail_from = pos['entry'] + d * pos['risk']
            rec['open'] = dict(side='long' if d > 0 else 'short', opened=pos['open_time'][:16], entry=round(pos['entry'], 2), initial_sl=round(pos['initial_sl'], 2), risk_pts=round(pos['risk'], 1), sl_now=round(pos['sl'], 2), tp=round(pos['tp'], 2) if pos['tp'] else None, open_rr=round(rr, 2),
                               locked_rr=round(d * (pos['sl'] - pos['entry']) / pos['risk'], 2), best=round(pos['best'], 2), trail_starts=round(trail_from, 2) if c['trail'] else None, stop_if_trailing_now=round(pos['best'] - d * 6 * atr_now, 2) if c['trail'] else None)
        out['versions'][v] = rec; print(v, json.dumps(rec), flush=True)
    print('PARITY', json.dumps(out['parity']), flush=True)
    (H / 'TODAY.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
