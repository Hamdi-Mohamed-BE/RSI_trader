"""Owner 2026-11-16 (screenshot of a prop "Pro - Lowest Profit Target" plan): P1 +6%, P2 +6%, daily loss 3%, max loss 6% static, min days 0, split up to 100%, fee $466.
Pass rate for Nasdaq 5M alone at 2%, Overnight Bias ORB alone at 2%, and both together at 1% each.

Streams (native MT5 Model 4, closed trades, R = net / (risk% x balance before the trade)):
  NAS = Nasdaq 5M production EX5 2488443f62a8 (REPLACE, ATR6, DI OFF = package default), Nasdaq 5M Trail Start 2026-11-12/native/nw-USTEC-TS1_DIOFF-all, 2019-07-16 -> 2026-11-12
  ONB = Overnight Bias ORB raw EA, Video ORB VWAP Ideas Raw 2026-11-09/native/nw-USTEC-ONB-all, 2019-07-16 -> 2026-11-10 (P4 / Best1Step wrapper parity 54/54)
Rules as modelled (ASSUMPTIONS where the card is silent):
  - risk % of the current closed balance per trade; trades taken as recorded (same entries/exits whatever the size).
  - target: closed balance >= +6% of the phase's start balance; phase 2 starts at the next 00:00 UTC after the phase-1 pass, fresh balance.
  - max loss 6% static of the start balance; daily loss 3% of the start balance, counted from the closed balance at 00:00 UTC.
  - OPTIMISTIC = closed balance only. PESSIMISTIC = every open trade also counted at its full stop (-1R) at all times (floating losses).
  - no time limit (card shows none); horizon 365 days. Weekend / overnight holding allowed (card silent). No news rule.
Evidence: HISTORY = a start every weekday 2019-07-16 -> 2025-11-12 (full 365-day horizon), MC = 2,000 paths of random 28-day calendar blocks, seed 20261116.
In-sample replay; backtest is not a forecast."""
import gzip, json, random, statistics, sys
from bisect import bisect_left
from datetime import datetime, timedelta, timezone
from pathlib import Path

H = Path(__file__).resolve().parent; B = H.parent
SRC = {'NAS': B / 'Nasdaq 5M Trail Start 2026-11-12/native/nw-USTEC-TS1_DIOFF-all/trades.json.gz',
       'ONB': B / 'Video ORB VWAP Ideas Raw 2026-11-09/native/nw-USTEC-ONB-all/trades.json.gz'}
T0 = datetime(2019, 7, 16, tzinfo=timezone.utc); TEND = datetime(2026, 11, 10, tzinfo=timezone.utc)
TARGET, DAILY, MAXL, HORIZON = 0.06, 0.03, 0.06, 365
CONFIGS = {'NAS 2%': {'NAS': 0.02}, 'ONB 2%': {'ONB': 0.02}, 'BOTH 1%+1%': {'NAS': 0.01, 'ONB': 0.01}}


def ts(s): return datetime.fromisoformat(s[:19]).replace(tzinfo=timezone.utc).timestamp()


def load():
    out = []
    for ea, p in SRC.items():
        T = sorted(json.loads(gzip.open(p).read()), key=lambda t: t['close_time']); bal = 1e4
        for t in T:
            r = t['net_profit'] / (0.01 * bal); bal += t['net_profit']
            o, c = ts(t['open_time']), ts(t['close_time'])
            if o < TEND.timestamp(): out.append((o, c, r, ea))
    out.sort(); return out


def phase(trades, start, risk, pess, deadline):
    """Run one phase from `start` (epoch). trades sorted by open. Returns ('pass'|'daily'|'max'|'time', end_epoch, n_trades)."""
    bal = 1.0; i = bisect_left(trades, (start,)); ev = []
    while i < len(trades) and trades[i][0] < deadline:
        o, c, r, ea = trades[i]; i += 1
        if ea in risk: ev.append((o, 0, c, r, ea)); ev.append((c, 1, o, r, ea))
    ev.sort(key=lambda e: (e[0], e[1]))
    openrisk = {}; day = None; daybal = 1.0; n = 0
    for t, kind, other, r, ea in ev:
        d = int(t // 86400)
        if d != day: day = d; daybal = bal
        key = (other, ea) if kind == 1 else (t, ea)
        if kind == 0:
            openrisk[key] = risk[ea] * bal; n += 1
        else:
            amt = openrisk.pop(key, None)
            if amt is None: continue
            bal += r * amt
            if bal <= 1 - MAXL: return 'max', t, n
            if daybal - bal >= DAILY: return 'daily', t, n
            if bal >= 1 + TARGET: return 'pass', t, n
        if pess and openrisk:
            worst = bal - sum(openrisk.values())
            if worst <= 1 - MAXL: return 'max', t, n
            if daybal - worst >= DAILY: return 'daily', t, n
    return 'time', deadline, n


def challenge(trades, start, risk, pess):
    end = start + HORIZON * 86400
    r1, t1, n1 = phase(trades, start, risk, pess, end)
    if r1 != 'pass': return dict(p1=r1, res=r1 if r1 != 'time' else 'time', days=None, n=n1)
    s2 = (int(t1 // 86400) + 1) * 86400
    r2, t2, n2 = phase(trades, s2, risk, pess, end)
    return dict(p1='pass', p1_days=(t1 - start) / 86400, res='pass' if r2 == 'pass' else r2, days=(t2 - start) / 86400 if r2 == 'pass' else None, n=n1 + n2,
                p2=r2)


def mc_paths(trades, n_paths, seed):
    rnd = random.Random(seed); blk = 28 * 86400; t0 = T0.timestamp(); nb = int((TEND.timestamp() - t0) // blk)
    by = [[] for _ in range(nb)]
    for o, c, r, ea in trades:
        k = int((o - t0) // blk)
        if 0 <= k < nb: by[k].append((o - t0 - k * blk, c - o, r, ea))
    need = HORIZON // 28 + 2; paths = []
    for _ in range(n_paths):
        tr = []
        for j in range(need):
            for off, dur, r, ea in by[rnd.randrange(nb)]:
                o = j * blk + off; tr.append((o, o + dur, r, ea))
        tr.sort(); paths.append(tr)
    return paths


def summarize(rows):
    n = len(rows); P = [x for x in rows if x['res'] == 'pass']; days = sorted(x['days'] for x in P)
    pct = lambda k: round(100 * k / n, 1)  # noqa: E731
    within = {d: pct(sum(1 for x in P if x['days'] <= d)) for d in (30, 60, 90, 180, 365)}
    p1 = [x for x in rows if x['p1'] == 'pass']
    return dict(starts=n, pass_both=pct(len(P)), within=within, fail_daily=pct(sum(1 for x in rows if x['res'] == 'daily')), fail_max=pct(sum(1 for x in rows if x['res'] == 'max')),
                not_done_365=pct(sum(1 for x in rows if x['res'] == 'time')), p1_pass=pct(len(p1)), p2_pass_given_p1=round(100 * len(P) / len(p1), 1) if p1 else None,
                median_days=round(statistics.median(days), 0) if days else None, p25_days=round(days[len(days) // 4], 0) if days else None,
                p75_days=round(days[3 * len(days) // 4], 0) if days else None, median_p1_days=round(statistics.median([x['p1_days'] for x in p1]), 0) if p1 else None,
                median_trades_to_pass=round(statistics.median([x['n'] for x in P]), 0) if P else None,
                fees_per_funded=round(100 / pct(len(P)), 2) if P else None)


def main():
    trades = load(); res = {}
    starts = []; d = T0
    while d < datetime(2025, 11, 12, tzinfo=timezone.utc):
        if d.weekday() < 5: starts.append(d.timestamp())
        d += timedelta(days=1)
    periods = {'2019-07..2021-12': (T0.timestamp(), datetime(2022, 1, 1, tzinfo=timezone.utc).timestamp()),
               '2022..2023': (datetime(2022, 1, 1, tzinfo=timezone.utc).timestamp(), datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp()),
               '2024..2025-11': (datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp(), datetime(2025, 11, 12, tzinfo=timezone.utc).timestamp())}
    paths = mc_paths(trades, 2000, 20261116)
    for name, risk in CONFIGS.items():
        res[name] = {}
        for mode, pess in (('optimistic', False), ('pessimistic', True)):
            rows = [challenge(trades, s, risk, pess) for s in starts]
            mc = [challenge(p, 0.0, risk, pess) for p in paths]
            res[name][mode] = dict(history=summarize(rows), mc=summarize(mc),
                                   by_period={k: summarize([r for s, r in zip(starts, rows) if a <= s < b]) for k, (a, b) in periods.items()})
            print(name, mode, 'HIST', res[name][mode]['history'], '\n   MC', res[name][mode]['mc'], flush=True)
    # stream facts
    facts = {}
    for ea in SRC:
        x = [t for t in trades if t[3] == ea]; months = (TEND - T0).days / 30.4375; w = [t[2] for t in x if t[2] > 0]; l = [t[2] for t in x if t[2] < 0]
        facts[ea] = dict(trades=len(x), per_month=round(len(x) / months, 1), per_day=round(len(x) / months / 21, 2), total_r=round(sum(t[2] for t in x), 1),
                         pf=round(sum(w) / -sum(l), 2), win=round(100 * len(w) / len(x), 1), worst_r=round(min(t[2] for t in x), 2))
    res['_streams'] = facts
    (H / 'RESULTS.json').write_text(json.dumps(res, indent=1), encoding='utf-8'); print(json.dumps(facts))


if __name__ == '__main__':
    main()
