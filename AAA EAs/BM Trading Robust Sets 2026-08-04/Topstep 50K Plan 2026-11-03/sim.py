"""Owner 2026-11-03: Topstep 50K Trading Combine ($49), pass in 2-3 weeks following the XAU RSI VWAP and Nasdaq 5M bots,
"tuned for day trader style", about $400 risk per trade. Research only (Python replay), nothing installed or traded.

Rules modelled (owner's numbers; verify on help.topstep.com before trading):
  start $50,000; profit target +$3,000; Maximum Loss Limit $2,000 trailing the highest END-OF-DAY balance, stops at $50,000;
  breached if intraday equity (incl. open trades) touches it; Daily Loss Limit $1,000 (day's realized + open P&L): positions are
  closed and no more trades that day (not a fail); consistency: best day <= 50% of total profit when passing (else keep trading);
  flat by 15:10 Chicago; trading day = 17:00 -> 16:00 Chicago; no entries 15:10-17:00 Chicago.
Signals: native MT5 Model 4 CFD runs, 2021-10-06 -> 2026-10-06 (each trade's filled initial stop + 5-minute floating marks):
  RSI   XAU RSI VWAP (H1)                       -> MGC (10 oz = 0.1 CFD lot), forced flat at 15:10 Chicago from the marks
  NAS   Nasdaq 5M, deployed ATR(14)x6 stop, DI ON -> MNQ ($2 / point), forced flat at 15:10 Chicago from the marks
  NASD  Nasdaq 5M day version P130_M6 (1.30% stop, no trail, closed 15:55 New York; Wide Stop Pipeline Model 4 run, 2019-26)
        -> MNQ; no floating marks, so intraday equity uses closed P&L only (optimistic for the MLL / DLL)
Contracts: round(risk budget / stop loss per contract), minimum 1; skip a signal if 1 contract risks more than 2x the budget.
Costs: CFD spread inside the prices; futures commission $1.50 per MNQ and $2.00 per MGC round turn; no swap (day-flat).
Counterfactual entries after a forced close are not reconstructed. python sim.py -> RESULTS.json / RESULTS.md"""
import gzip, importlib.util, json, math, statistics, sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

R = Path(__file__).resolve().parent; B = R.parent; CT = ZoneInfo('America/Chicago'); NY = ZoneInfo('America/New_York')
spec = importlib.util.spec_from_file_location('prop_select', B / 'Prop Portfolio Selection 2026-11-03/prop_select.py')
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
MULT = {'USTEC': 2.0, 'XAUUSD': 0.1}; COMM = {'USTEC': 1.50, 'XAUUSD': 2.00}
START, TARGET, MLL, DLL = 50000.0, 3000.0, 2000.0, 1000.0
DATA_END = datetime(2026, 10, 6, tzinfo=timezone.utc)


def flat_epoch(ep):
    """15:10 Chicago of the trading day that contains epoch ep (trading day ends 16:00 Chicago)."""
    t = datetime.fromtimestamp(ep, CT)
    d = t.date() if t.hour < 17 else t.date() + timedelta(days=1)
    while d.weekday() >= 5: d += timedelta(days=1)
    return datetime(d.year, d.month, d.day, 15, 10, tzinfo=CT).timestamp()


def blocked_entry(ep):
    t = datetime.fromtimestamp(ep, CT); m = t.hour * 60 + t.minute
    return 15 * 60 + 10 <= m < 17 * 60 or t.weekday() == 5 or (t.weekday() == 6 and m < 17 * 60) or (t.weekday() == 4 and m >= 15 * 60 + 10)


def long_rows(slug, key, symbol):
    src = S.sources(); cache = {}; begin, end = S.PR.midnight(S.P.DATA_START), S.PR.midnight(S.P.DATA_END); out = []
    for c in S.member_candidates(slug, key, begin, end, cache, src)[0]:
        if c['end_censored'] or blocked_entry(c['op']): continue
        fl = flat_epoch(c['op']); marks = [(m[0], m[1]) for m in c['marks']]
        if c['cl'] <= fl: close, gross = c['cl'], c['unit_gross']
        else:
            before = [f for t, f in marks if t <= fl]
            close, gross = fl, (before[-1] if before else 0.0); marks = [(t, f) for t, f in marks if t <= fl]
        out.append(dict(ea=slug, symbol=symbol, op=c['op'], cl=close, unit=c['unit_risk'] * MULT[symbol], gross=gross * MULT[symbol],
                        marks=[(t, f * MULT[symbol]) for t, f in marks], forced=c['cl'] > fl))
    return out


def day_rows():
    d = B / 'Nasdaq 5M Wide Stop Pipeline 2026-11-02/native/nw-USTEC-P130_M6_DION_M4-full'
    t = json.loads(gzip.decompress((d / 'trades.json.gz').read_bytes())); out = []
    for x in t:
        op = datetime.fromisoformat(x['open_time']).replace(tzinfo=timezone.utc).timestamp()
        cl = datetime.fromisoformat(x['close_time']).replace(tzinfo=timezone.utc).timestamp()
        if op < S.PR.midnight(S.P.DATA_START) or blocked_entry(op): continue
        out.append(dict(ea='nasdaq-day', symbol='USTEC', op=op, cl=cl, unit=0.013 * x['open_price'] * MULT['USTEC'],
                        gross=x['gross_profit'] / x['volume'] * MULT['USTEC'], marks=[], forced=False))
    return out


def tday(ep):
    t = datetime.fromtimestamp(ep, CT); d = t.date() if t.hour < 17 else t.date() + timedelta(days=1)
    while d.weekday() >= 5: d += timedelta(days=1)
    return d


def run(rows, budget, start_day, horizon_days):
    """One Combine attempt from start_day; returns outcome, trading days used, trades, days, profit."""
    begin = datetime(start_day.year, start_day.month, start_day.day, 17, 0, tzinfo=CT).timestamp() - 86400
    last = start_day; n_days = 1
    while n_days < horizon_days:
        last += timedelta(days=1)
        if last.weekday() < 5: n_days += 1
    stop_ep = datetime(last.year, last.month, last.day, 16, 0, tzinfo=CT).timestamp()
    tdays = lambda d: sum(1 for i in range((d - start_day).days + 1) if (start_day + timedelta(days=i)).weekday() < 5)  # noqa: E731
    trs = [r for r in rows if begin <= r['op'] < stop_ep]
    ev = []
    for i, r in enumerate(trs):
        ev.append((r['op'], 1, i, 0.0)); ev.append((r['cl'], 0, i, 0.0)); ev += [(t, 2, i, f) for t, f in r['marks']]
    ev.sort(key=lambda e: (e[0], e[1]))
    bal = START; eod_high = START; level = START - MLL; open_ = {}; day = None; day_start = START; days = []; dayp = defaultdict(float)
    locked = set(); ntr = 0; skipped = 0
    for t, k, i, f in ev:
        d = tday(t)
        if d != day:
            if day is not None:
                eod_high = max(eod_high, bal); level = min(START, eod_high - MLL); days.append(day)
            day = d; day_start = bal
        r = trs[i]
        if k == 1:
            if d in locked or i in open_: continue
            n = round(budget / r['unit'])
            if n < 1: n = 1
            if n * r['unit'] > 2 * budget: skipped += 1; continue
            open_[i] = dict(n=n, f=0.0); continue
        if i not in open_: continue
        if k == 2: open_[i]['f'] = f
        else:
            p = open_.pop(i); pnl = p['n'] * (r['gross'] - COMM[r['symbol']]); bal += pnl; dayp[d] += pnl; ntr += 1
        eq = bal + sum(v['n'] * v['f'] for v in open_.values())
        if eq <= level + 1e-9: return dict(outcome='fail', days=tdays(d), trades=ntr, profit=round(eq - START, 2), skipped=skipped)
        if eq - day_start <= -DLL and d not in locked:          # daily loss limit: flatten at the current marks, done for today
            for j, v in list(open_.items()):
                pnl = v['n'] * (v['f'] - COMM[trs[j]['symbol']]); bal += pnl; dayp[d] += pnl; ntr += 1; open_.pop(j)
            locked.add(d)
        prof = bal - START
        if not open_ and prof >= TARGET and max(dayp.values()) <= 0.5 * prof + 1e-9:
            return dict(outcome='pass', days=tdays(d), trades=ntr, profit=round(prof, 2), skipped=skipped)
    return dict(outcome='open', days=horizon_days, trades=ntr, profit=round(bal - START, 2), skipped=skipped)


def starts(a, b):
    d = a
    while d < b:
        if d.weekday() < 5: yield d
        d += timedelta(days=1)


SEG = {'2021-23': (date(2021, 10, 7), date(2023, 10, 6)), '2023-24': (date(2023, 10, 6), date(2024, 10, 6)),
       'last 2 years': (date(2024, 10, 6), date(2026, 7, 1)), 'all': (date(2021, 10, 7), date(2026, 7, 1))}


def summary(res):
    n = len(res); c = lambda o: sum(r['outcome'] == o for r in res) / n  # noqa: E731
    passed = [r['days'] for r in res if r['outcome'] == 'pass']
    return dict(n=n, pass_=round(c('pass'), 3), fail=round(c('fail'), 3), open=round(c('open'), 3),
                median_days_pass=statistics.median(passed) if passed else None, median_trades=statistics.median(r['trades'] for r in res))


if __name__ == '__main__':
    rsi = long_rows('xau-rsi-vwap', S.F('xau-rsi-vwap'), 'XAUUSD'); nas = long_rows(S.NAS, S.A6_ON, 'USTEC'); nasd = day_rows()
    PLANS = {'RSI + NAS (ATR6 stop, flat 15:10 CT)': rsi + nas, 'RSI + NAS day version (1.30% stop, close 15:55 NY)': rsi + nasd,
             'NAS only (ATR6, flat 15:10 CT)': nas, 'NAS day version only': nasd, 'RSI only': rsi}
    info = dict(rsi=dict(trades=len(rsi), forced=sum(r['forced'] for r in rsi)), nas=dict(trades=len(nas), forced=sum(r['forced'] for r in nas)), nasd=len(nasd))
    print(info, flush=True)
    out = dict(info=info, plans={})
    for name, rows in PLANS.items():
        rows = sorted(rows, key=lambda r: r['op'])
        for budget in (300, 400, 500, 600):
            for horizon in (10, 15, 60):
                key = f'{name}|${budget}|{horizon}d'; seg = {}
                for s, (a, b) in SEG.items():
                    seg[s] = summary([run(rows, budget, d, horizon) for d in starts(a, b)])
                out['plans'][key] = seg; print(key, seg['all'], seg['last 2 years']['pass_'], flush=True)
    (R / 'RESULTS.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
