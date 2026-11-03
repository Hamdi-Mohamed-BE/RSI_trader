"""4-EA version (owner 2026-11-03, second request: + Gold Overnight Value Area, fixed-money mode $80). Base text:
Owner 2026-11-03: "i will have 2k into real funds ... use the 5m nasdaq and rsi vwap and ema3 only ... risk 80$ per trade ...
simulate expected return on that account per month". Research only (Python replay), nothing installed.

Sources: the five-year native Model 4 long-history runs, 2021-10-06 -> 2026-10-06 (each trade's filled initial stop, recorded
commission / swap / spread, and 5-minute floating marks): XAU RSI VWAP and EMA3 from Portfolio Long History All ORB05 2026-10-14,
Nasdaq 5M with the deployed ATR(14)x6 stop (DI ON and DI OFF) from Prop Portfolio Selection 2026-11-03/native.py.
Sizing:
  FIXED80  every entry = $80 to its initial stop; lots = 80 / (stop loss per lot), rounded UP to 0.01 (Calyx standard), minimum 0.01.
  AS_EA    what the EAs do today at a 4% request: RSI VWAP and EMA3 4% of equity (uncapped), Nasdaq 5M capped at 1% of equity in code.
  FIXED40  $40 per trade (2%) for comparison.
Account $2,000, no guard, margin not modelled (small lots on Exness leverage). Same-EA overlaps are kept as in the native run.
python sim.py  (run from EA store: uv run --with pandas --with numpy python "<this>")"""
import importlib.util, json, math, random, statistics, sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

R = Path(__file__).resolve().parent; B = R.parent
spec = importlib.util.spec_from_file_location('prop_select', B / 'Prop Portfolio Selection 2026-11-03/prop_select.py')
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
START = 2000.0; STEP = MIN = 0.01
SEG = {'2021-23 (dev)': (date(2021, 10, 6), date(2023, 10, 6)), '2023-24 (val)': (date(2023, 10, 6), date(2024, 10, 6)),
       'last 2 years': (date(2024, 10, 6), date(2026, 10, 6)), 'last 12 months': (date(2025, 10, 6), date(2026, 10, 6)),
       'all 5 years': (date(2021, 10, 6), date(2026, 10, 6))}


def rows(di):
    src = S.sources(); cache = {}; begin, end = S.PR.midnight(S.P.DATA_START), S.PR.midnight(S.P.DATA_END); out = []
    for slug, key in (('xau-rsi-vwap', S.F('xau-rsi-vwap')), ('ema3', S.F('ema3')), ('gold-overnight-value-area', S.F('gold-overnight-value-area')), (S.NAS, S.A6_ON if di == 'ON' else S.A6_OFF)):
        for c in S.member_candidates(slug, key, begin, end, cache, src)[0]:
            if c['end_censored']: continue
            out.append(dict(ea=slug, op=c['op'], cl=c['cl'], unit=c['unit_risk'], net_lot=c['unit_gross'] + c['unit_commission'] + c['unit_swap'],
                            marks=[(m[0], m[1]) for m in c['marks']]))
    return sorted(out, key=lambda r: r['op'])


def lots_for(money, unit):
    return max(MIN, math.ceil(money / unit / STEP - 1e-9) * STEP)


def replay(trs, mode):
    """Chronological replay with closed balance and floating equity from the owned marks."""
    ev = []
    for i, r in enumerate(trs):
        ev.append((r['op'], 1, i)); ev.append((r['cl'], 0, i))
        for t, f in r['marks']: ev.append((t, 2, i, f))
    ev.sort(key=lambda e: (e[0], e[1]))
    bal = START; open_ = {}; peak_eq = START; eqdd = 0.0; peak_b = START; bdd = 0.0; out = []; low = START
    for e in ev:
        t, k, i = e[0], e[1], e[2]; r = trs[i]
        if k == 1:
            eq = bal + sum(v['lots'] * v['f'] for v in open_.values())
            if mode == 'FIXED80': money = 80.0
            elif mode == 'FIXED40': money = 40.0
            else: money = 80.0 if r['ea'] == 'gold-overnight-value-area' else eq * (0.01 if r['ea'] == S.NAS else 0.04)
            if eq <= 0: continue
            open_[i] = dict(lots=lots_for(money, r['unit']), f=0.0)
        elif k == 2 and i in open_:
            open_[i]['f'] = e[3]
        elif k == 0 and i in open_:
            p = open_.pop(i); pnl = p['lots'] * r['net_lot']; bal += pnl
            out.append(dict(ea=r['ea'], cl=r['cl'], pnl=pnl, risk=p['lots'] * r['unit']))
            peak_b = max(peak_b, bal); bdd = max(bdd, peak_b - bal)
        eq = bal + sum(v['lots'] * v['f'] for v in open_.values()); low = min(low, eq)
        peak_eq = max(peak_eq, eq); eqdd = max(eqdd, peak_eq - eq)
    return out, dict(final=bal, closed_dd_usd=round(bdd, 0), equity_dd_usd=round(eqdd, 0), lowest_equity=round(low, 0))


def month_key(ep): d = datetime.fromtimestamp(ep, timezone.utc); return (d.year, d.month)


def seg_stats(trs, a, b):
    ts = [x for x in trs if a <= datetime.fromtimestamp(x['cl'], timezone.utc).date() < b]
    months = []; d = date(a.year, a.month, 1)
    while d < b:
        months.append((d.year, d.month)); d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    by = defaultdict(float)
    for x in ts: by[month_key(x['cl'])] += x['pnl']
    m = [by[k] for k in months]
    wd = sum(1 for i in range((b - a).days) if (a + timedelta(days=i)).weekday() < 5)
    p = [x['pnl'] for x in ts]; gp, gl = sum(v for v in p if v > 0), -sum(v for v in p if v < 0)
    return dict(months=len(m), mean=round(statistics.mean(m), 0), median=round(statistics.median(m), 0), worst=round(min(m), 0), best=round(max(m), 0),
                losing_share=round(sum(v < 0 for v in m) / len(m), 2), total=round(sum(p), 0), trades=len(ts),
                per_month=round(len(ts) / len(m), 1), per_day=round(len(ts) / wd, 2), pf=round(gp / gl, 2) if gl else None,
                win=round(100 * sum(v > 0 for v in p) / len(p), 1) if p else None, avg_risk=round(statistics.mean(x['risk'] for x in ts), 1) if ts else None)


def mc(trs, paths=4000, months=12, seed=20261103):
    """4-week blocks of the five-year closed-trade P&L, 13 blocks per year; balance path from $2,000."""
    first = min(x['cl'] for x in trs); blocks = defaultdict(list)
    for x in sorted(trs, key=lambda x: x['cl']): blocks[int((x['cl'] - first) // (28 * 86400))].append(x['pnl'])
    allb = [blocks.get(i, []) for i in range(max(blocks) + 1)]; rng = random.Random(seed); res = []
    nb = round(months * 13 / 12)
    for _ in range(paths):
        bal = peak = START; dd = 0.0; low = START; firstm = None
        for j in range(nb):
            for v in rng.choice(allb):
                bal += v; peak = max(peak, bal); dd = max(dd, peak - bal); low = min(low, bal)
            if j == 0: firstm = bal - START
        res.append((bal - START, dd, low, firstm))
    q = lambda v, p: sorted(v)[int(p * (len(v) - 1))]  # noqa: E731
    tot = [r[0] for r in res]; dds = [r[1] for r in res]; lows = [r[2] for r in res]; m1 = [r[3] for r in res]
    return dict(year_total_p10=round(q(tot, .1)), year_total_p50=round(q(tot, .5)), year_total_p90=round(q(tot, .9)),
                year_mean=round(statistics.mean(tot)), per_month_mean=round(statistics.mean(tot) / 12), p_year_loss=round(sum(v < 0 for v in tot) / len(tot), 2),
                first_4weeks_p10=round(q(m1, .1)), first_4weeks_p50=round(q(m1, .5)), first_4weeks_p90=round(q(m1, .9)),
                closed_dd_p50=round(q(dds, .5)), closed_dd_p95=round(q(dds, .95)), p_below_1000=round(sum(v < 1000 for v in lows) / len(lows), 3),
                p_below_1500=round(sum(v < 1500 for v in lows) / len(lows), 3))


out = {}
for di in ('ON', 'OFF'):
    trs = rows(di)
    for mode in ('FIXED80', 'AS_EA', 'FIXED40'):
        led, path = replay(trs, mode)
        out[f'{mode}|DI {di}'] = dict(path=path, segments={k: seg_stats(led, *v) for k, v in SEG.items()}, mc=mc(led) if mode != 'AS_EA' else None,
                                      by_ea={ea: seg_stats([x for x in led if x['ea'] == ea], *SEG['all 5 years']) for ea in ('xau-rsi-vwap', 'ema3', 'gold-overnight-value-area', S.NAS)})
        s = out[f'{mode}|DI {di}']['segments']['all 5 years']; print(mode, di, s, path, flush=True)
(R / 'RESULTS-4EA.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
