"""FTMO vs Exness 5-year streams -> the multi-firm FTMO engine (Multi Firm Funded 2026-11-17/sim.py + first_payout.py, frozen, VARIANT files).
Input: native5y/nw-<key>-<FEED>/trades.json.gz (run5y.py, Model 1, $100k, 1% of balance, package inputs).
Per trade: R unit = 1% of the balance at entry (deposit + trades closed before it); 5-minute marks from the feed's own M1 closes (shorts marked at bid + bar spread);
money per point per lot from the trade itself (gross / (move x volume)); Nasdaq 5M x0.75; same weekend / holiday flat transform as INPUTS_N75
(Best 1-Step Search 2026-11-11/weekend_flat.py); window 2021-10-07 -> 2026-10-06 (Prague midnights, = INPUTS_N75). 3 Way Gold = breakout module only (package).
Variants written to Multi Firm Funded 2026-11-17/:
  INPUTS_FX_EX.json  Exness prices (as tested)
  INPUTS_FX_FT.json  FTMO prices + FTMO commission (XAUUSD $3 / lot / side measured on the owner's FTMO deals; USDJPY $2.5 ASSUMED; US100 / UK100 $0)
  INPUTS_FX_FTS.json as FX_FT, swaps replaced by FTMO's CURRENT swap table (read 2026-11-24; old rates differed) - sensitivity only
python build5y.py"""
import gzip, importlib.util, json, os
from bisect import bisect_left, bisect_right
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np

H = Path(__file__).resolve().parent; B = H.parent; MF = B / 'Multi Firm Funded 2026-11-17'
spec = importlib.util.spec_from_file_location('c2m', H / 'compare2m.py'); C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)
spec = importlib.util.spec_from_file_location('wf', B / 'Best 1-Step Search 2026-11-11/weekend_flat.py'); W = importlib.util.module_from_spec(spec); spec.loader.exec_module(W)
N75 = json.loads((MF / 'INPUTS_N75.json').read_text(encoding='utf-8')); T0, T1 = N75['year_begin_epoch'], N75['year_end_exclusive_epoch']
COMM = {'XAUUSD': 3.0, 'USDJPY': 2.5, 'USTEC': 0.0, 'UK100': 0.0}
# FTMO swap table 2026-11-24 (points per lot per night; triple day: indices Friday, XAU / FX Wednesday). point: US100/UK100/XAU 0.01, USDJPY 0.001
FSWAP = {'USTEC': (-497.35, -140.21, 4, 0.01), 'UK100': (-265.71, 8.76, 4, 0.01), 'XAUUSD': (-53.52, -15.0, 2, 0.01), 'USDJPY': (1.74, -17.58, 2, 0.001)}
FT_FILE = {'USTEC': 'US100', 'XAUUSD': 'XAUUSD', 'USDJPY': 'USDJPY', 'UK100': 'UK100'}
dt = np.dtype([('t', '<i8'), ('o', '<f8'), ('h', '<f8'), ('l', '<f8'), ('c', '<f8'), ('v', '<i8'), ('s', '<i4')])
POINT = {'USTEC': 0.01, 'UK100': 0.01, 'XAUUSD': 0.01, 'USDJPY': 0.001}


def bars(canon, feed):
    if feed == 'EXNESS':
        a = np.load(H / 'exness' / f'{canon}_m1.npy'); return a[:, 0].astype(np.int64), a[:, 4], a[:, 6]
    a = np.fromfile(Path(os.environ['APPDATA']) / 'MetaQuotes/Terminal/Common/Files/CalyxFTMO' / f'{FT_FILE[canon]}_m1.bin', dtype=dt); return np.ascontiguousarray(a['t']), np.ascontiguousarray(a['c']), a['s'].astype(float)   # contiguous: searchsorted on a strided view copies every call


def epoch(s): return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())


def nights(op, cl, triple):
    """FTMO rollovers (server midnight = 21:00 UTC during US DST, else 22:00 UTC) in (op, cl], weekdays only, the triple day counted 3x."""
    n = 0; d = datetime.fromtimestamp(op, timezone.utc).date() - timedelta(days=1)
    while True:
        for h in (21, 22):
            r = int(datetime(d.year, d.month, d.day, h, tzinfo=timezone.utc).timestamp())
            if C_off(r) != (3 if h == 21 else 2): continue
            wd = datetime.fromtimestamp(r, timezone.utc).weekday()
            if op < r <= cl and wd < 5: n += 3 if wd == triple else 1
        d += timedelta(days=1)
        if int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp()) > cl: return n


def C_off(u):
    y = datetime.fromtimestamp(u, timezone.utc).year; d = datetime(y, 3, 1, tzinfo=timezone.utc)
    while d.weekday() != 6: d += timedelta(days=1)
    on = d + timedelta(days=7, hours=7); d = datetime(y, 11, 1, tzinfo=timezone.utc)
    while d.weekday() != 6: d += timedelta(days=1)
    return 3 if on.timestamp() <= u < (d + timedelta(hours=6)).timestamp() else 2


def candidates(feed, ftswap=False):
    out = []; info = {}
    for e in C.entries():
        key, canon = e['key'], e['canonical']; f = C.FACTOR.get(key, 1.0)
        T = json.loads(gzip.open(H / 'native5y' / f'nw-{key}-{feed}' / 'trades.json.gz').read())
        closes = sorted((epoch(t['close_time']), t['net_profit']) for t in T); cl_t = [c for c, _ in closes]; cum = np.cumsum([0.0] + [n for _, n in closes])
        bt, bc, bs = bars(canon, feed); n_in = 0; r_sum = 0.0
        for i, t in enumerate(sorted(T, key=lambda t: t['open_time'])):
            op, cl = epoch(t['open_time']), epoch(t['close_time'])
            if not (T0 <= op < T1): continue
            bal = 1e5 + cum[bisect_right(cl_t, op)]; risk = 0.01 * bal / f   # Nasdaq x0.75 = same trade at 0.75 of the risk -> R scaled by 0.75
            sgn = 1 if t['side'] == 'Long' else -1; vol = t['volume']; move = (t['close_price'] - t['open_price']) * sgn
            ppl = t['gross_profit'] / (move * vol) if abs(move) * vol > 0 and abs(move) > 5 * POINT[canon] else None
            if ppl is None or ppl <= 0: ppl = {'USTEC': 1.0, 'XAUUSD': 100.0, 'USDJPY': 1e5 / t['open_price'], 'UK100': 1.3}[canon]
            comm = t['commission'] - (2 * COMM[canon] * vol if feed == 'FTMO' else 0.0)
            swap = t['swap']
            if ftswap:
                sl, ss, tri, pt = FSWAP[canon]; swap = (sl if sgn > 0 else ss) * pt * ppl * nights(op, cl, tri) * vol   # points x point = price units, x money per price unit per lot
            ur = risk / vol
            marks = []; m = op + 300 - (op % 300)
            while m < min(cl, T1):
                j = int(np.searchsorted(bt, m, 'right')) - 1   # last M1 bar starting before the mark: its close = price at m
                if j >= 0 and bt[j] >= m - 600:
                    px = bc[j] + (0 if sgn > 0 else bs[j] * POINT[canon]); marks.append([m, (px - t['open_price']) * sgn * ppl])
                m += 300
            c = dict(id=f'{key}|{i}', ea=key, symbol=canon, op=op, cl=cl if cl < T1 else None, side=t['side'], open_price=t['open_price'], close_price=t['close_price'],
                     unit_risk=ur, source_volume=vol, entry_unit_cost=comm / vol, unit_gross=t['gross_profit'] / vol, unit_commission=comm / vol, unit_swap=swap / vol,
                     marks=marks, source_forced_close_epoch=None, end_censored=cl >= T1)
            if cl >= T1:   # still open at the window end: book at its last mark, as the source ledgers do
                c['unit_gross'] = marks[-1][1] if marks else 0.0
            out.append(c); n_in += 1; r_sum += (c['unit_gross'] + c['unit_commission'] + c['unit_swap']) / ur
        info[key] = dict(trades=n_in, raw_r=round(r_sum, 1))
    # weekend / holiday flat (same transform as the Best 1-Step streams)
    flat = []; cut = rem = 0
    for c in out:
        cls = W.sym_class(c['symbol']); cl = c['cl'] if c['cl'] is not None else T1
        if W.in_flat(c['op'], cls): rem += 1; continue
        fl = W.first_flat(c['op'], cl, cls)
        if fl is None: flat.append(c); continue
        x = dict(c); mk = [q for q in c['marks'] if q[0] < fl]; g = mk[-1][1] if mk else 0.0; frac = (fl - c['op']) / max(1, cl - c['op'])
        x.update(cl=fl, unit_gross=g, unit_swap=c['unit_swap'] * frac, marks=mk, end_censored=False, weekend_flat_cut=True, source_forced_close_epoch=fl); flat.append(x); cut += 1
    return flat, dict(per_ea_raw=info, removed_opened_in_window=rem, cut_at_flat=cut)


def R(c): return (c['unit_gross'] + c['unit_commission'] + c['unit_swap']) / c['unit_risk']


def summary(cands):
    per = {}
    for c in cands: per.setdefault(c['ea'], []).append(R(c))
    g = lambda L: dict(n=len(L), R=round(sum(L), 1), PF=round(sum(x for x in L if x > 0) / -sum(x for x in L if x < 0), 3) if any(x < 0 for x in L) else None, win=round(100 * sum(x > 0 for x in L) / len(L), 1))
    allr = [R(c) for c in cands]; return dict(total=g(allr), per_ea={k: g(v) for k, v in sorted(per.items())})


if __name__ == '__main__':
    meta = {k: v for k, v in N75.items() if k != 'candidates'}; rep = {'N75_reference': summary(N75['candidates'])}
    for name, feed, fs in (('FX_EX', 'EXNESS', False), ('FX_FT', 'FTMO', False), ('FX_FTS', 'FTMO', True)):
        if (MF / f'INPUTS_{name}.json').exists() and name in os.environ.get('SKIP', ''): rep[name] = dict(summary(json.loads((MF / f'INPUTS_{name}.json').read_text())['candidates'])); continue
        cands, info = candidates(feed, fs)
        (MF / f'INPUTS_{name}.json').write_text(json.dumps(dict(meta, candidates=cands, source=f'FTMO vs Exness 2026-11-24/build5y.py {feed} ftmo_swap={fs}'), separators=(',', ':')), encoding='utf-8')
        rep[name] = dict(summary(cands), build=info); print(name, rep[name]['total'], info['removed_opened_in_window'], info['cut_at_flat'], flush=True)
    (H / 'STREAMS_5Y.json').write_text(json.dumps(rep, indent=1), encoding='utf-8')
