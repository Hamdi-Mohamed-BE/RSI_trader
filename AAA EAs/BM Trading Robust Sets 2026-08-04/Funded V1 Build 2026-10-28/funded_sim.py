"""funded_v1 expected-value simulation (owner 2026-10-28). Python/numba replay of frozen native ledgers — NOT a native combined run, NOT a forecast.
Firm model = Leveraged $50k reward account, rules as answered by the firm on 2026-10-27:
  max loss 6% ($3,000) trailing the highest CLOSED balance; LOCKED at the initial $50,000 once the floor reaches it (account +6%) and after
  any payout; daily loss 3% of the day reference at 00:00 UTC (model: balance at the UTC day start; the live reference is the higher of
  balance / equity, which the ledger cannot know); reward 14 days after the start and then every 14 days, needs >= 3 days with closed profit
  >= 0.5% ($250) in the period and best day < 20% of the period profit; 80% share.
  ASSUMPTION (confirm with Leveraged): a payout may be partial. Because the floor stays at $50,000 after a payout, the model withdraws only
  the profit above $50,000 + cushion, so the account keeps trading room (cushion $3,000 = the same room as a fresh account; $1,500 shown too).
Guard = the funded_v1 defaults (CalyxFundedGuard.mqh): risk = min(risk %, 5% of room above the floor), cut to fit open 2% / symbol 1.5% /
  daily loss 2% (today's closed loss + open stops) / buffer 0.25%; skipped under 0.05%; no new entries once the day's CLOSED profit >= 0.75%
  (the live guard closes everything at +0.75% equity: the ledger has no intratrade marks, so that close is not modelled).
Breach = pessimistic: every open position at its full stop.
python funded_sim.py   -> FUNDED_SIM.json, FUNDED_SIM.md
"""
import gzip, importlib.util, json, math, random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import numpy as np
from numba import njit

R = Path(__file__).resolve().parent; B = R.parent
SIZE = 50000.0; DAY = 86400.0; BLOCK = 28; SEED = 20261028; MC_N = 1000
ds = importlib.util.spec_from_file_location('ds', B.parent / 'Calyx Research Pipeline/data_split.py'); D = importlib.util.module_from_spec(ds); ds.loader.exec_module(D)
START, END = '2021-10-06', '2026-10-05'          # the long-history signal ledgers end 2026-10-06 exclusive
SPLIT = D.research_split(START, END)
SEG = {'dev': (SPLIT['development']['start'], SPLIT['development']['end_exclusive']), 'val': (SPLIT['validation']['start'], SPLIT['validation']['end_exclusive']),
       'oos': (SPLIT['oos']['start'], SPLIT['oos']['end_exclusive']), 'all': (START, END)}
GUARD = dict(taper=0.05, maxopen=0.02, persym=0.015, dstop=0.02, buffer=0.0025, dwin=0.0075, minrisk=0.0005)
RISKS = (0.3, 0.5, 0.75, 1.0)


def utc_ts(d): return datetime.combine(date.fromisoformat(d) if isinstance(d, str) else d, datetime.min.time(), tzinfo=timezone.utc).timestamp()


def load_rows():
    raw = json.loads((B / 'Portfolio Long History All ORB05 2026-10-14/RISK_ROWS.json').read_text(encoding='utf-8'))['full-eas']
    keep = {'ema3', '3-way-gold', 'xau-orb-london-ny-overlap-m30', 'dmc-fresh-reaction-us100', 'dmc-current-xau', 'xau-rsi-vwap', 'nasdaq-5m-candle-momentum',
            'gold-overnight-value-area'}   # owner 2026-10-28: Gold Overnight added (9 EAs)
    rows = [(r['op'], r['cl'], r['key'], r['symbol'], r['unit_risk'], r['unit_gross'] + r['unit_comm'] + r['unit_swap']) for r in raw
            if r['key'] in keep and r['unit_risk'] > 0 and r['op'] < r['cl']]
    for c in json.loads((B / 'Best Prop Portfolio Retest 2026-10-20/INPUTS-DI_OFF.json').read_text(encoding='utf-8'))['candidates']:
        if c['ea'] == 'nasdaq-5m-candle-momentum' and not c['end_censored']:
            rows.append((c['op'], c['cl'], 'nasdaq-5m-di-off', c['symbol'], c['unit_risk'], c['unit_gross'] + c['unit_commission'] + c['unit_swap']))
    vc = json.loads((R / 'VOLCONF_05R_ROWS.json').read_text(encoding='utf-8'))
    rows += [(r['op'], r['cl'], 'orb-volume-profile-volume-confirmed', 'XAUUSD', r['unit_risk'], r['unit_net']) for r in vc['rows']]
    hi = utc_ts(END)
    rows = sorted([r for r in rows if r[0] >= utc_ts(START) and r[1] < hi + 30 * DAY], key=lambda r: (r[0], r[1]))
    return rows


ROWS = load_rows()
KEYS = sorted({r[2] for r in ROWS}); SYMS = sorted({r[3] for r in ROWS})
A = dict(op=np.array([r[0] for r in ROWS]), cl=np.array([r[1] for r in ROWS]), lane=np.array([KEYS.index(r[2]) for r in ROWS], np.int64),
         sym=np.array([SYMS.index(r[3]) for r in ROWS], np.int64), ur=np.array([r[4] for r in ROWS]), un=np.array([r[5] for r in ROWS]))
BASE8 = ['ema3', '3-way-gold', 'orb-volume-profile-volume-confirmed', 'xau-orb-london-ny-overlap-m30', 'dmc-fresh-reaction-us100', 'dmc-current-xau', 'xau-rsi-vwap',
         'gold-overnight-value-area']
PORTS = {'DI ON': BASE8 + ['nasdaq-5m-candle-momentum'], 'DI OFF': BASE8 + ['nasdaq-5m-di-off']}


def events(idx, shift):
    op = A['op'][idx] + shift; cl = A['cl'][idx] + shift; n = len(idx)
    t = np.concatenate([op, cl]); k = np.concatenate([np.ones(n, np.int64), np.zeros(n, np.int64)]); j = np.concatenate([np.arange(n), np.arange(n)])
    o = np.lexsort((j, k, t)); t = t[o]
    return (t, k[o], j[o], np.floor(t / DAY).astype(np.int64), A['lane'][idx], A['sym'][idx], A['ur'][idx], A['un'][idx])


@njit(cache=False)
def kernel(et, ek, ej, epd, lane, sym, ur, un, on, nsym, t0, t_end, rdol, taper, maxopen, persym, dstop, buffer, dwin, minrisk, cushion, share, firm_daily, trail):
    n = len(ur); lots = np.zeros(n); rk = np.zeros(n); sym_open = np.zeros(nsym)
    size = 50000.0; bal = size; peak = size; locked = False; floor = size - trail
    anchor = bal; aday = -1; awk = -1; open_total = 0.0; nactive = 0; code = 0; end_t = t_end
    paid = 0.0; npay = 0; first_pay = -1.0; start_pd = -1; last_pay_pd = -1; prof_days = 0; max_day = 0.0; period_profit = 0.0
    day_pnl = 0.0; week_pnl = 0.0; worst_day = 0.0; worst_week = 0.0; cum = 0.0; cpeak = 0.0; dd_c = 0.0; dd_s = 0.0; trades = 0
    cur = 0; clen = 0; maxw = 0; maxl = 0; sw = 0; cw = 0; sl = 0; cl_ = 0; win_days = 0; loss_days = 0; days = 0; lock_day = -1.0
    for e in range(len(et)):
        t = et[e]
        if t < t0: continue
        if t >= t_end: break
        pd = epd[e]
        if pd != aday:
            if aday != -1:
                if day_pnl < worst_day: worst_day = day_pnl
                if day_pnl >= 0.005 * size: prof_days += 1
                if day_pnl > max_day: max_day = day_pnl
                period_profit += day_pnl; days += 1
                if day_pnl > 0.005: win_days += 1
                elif day_pnl < -0.005: loss_days += 1
            wk = (pd + 3) // 7
            if wk != awk:
                if awk != -1 and week_pnl < worst_week: worst_week = week_pnl
                week_pnl = 0.0; awk = wk
            day_pnl = 0.0; aday = pd; anchor = bal
            if start_pd < 0: start_pd = pd; last_pay_pd = pd
            if pd - last_pay_pd >= 14:
                amount = bal - (size + cushion)
                if amount > 0 and prof_days >= 3 and period_profit > 0 and max_day < 0.2 * period_profit:
                    paid += share * amount; bal -= amount; npay += 1; locked = True; floor = size; anchor = bal
                    last_pay_pd = pd; prof_days = 0; max_day = 0.0; period_profit = 0.0
                    if first_pay < 0: first_pay = (t - t0) / 86400.0
            if nactive == 0 and bal - floor - buffer < minrisk:
                code = 2; end_t = t; break
        j = ej[e]
        if ek[e] == 1:
            if not on[lane[j]]: continue
            if dwin > 0 and day_pnl >= dwin: continue
            room = bal - open_total - floor
            risk = rdol
            if taper > 0 and taper * room < risk: risk = taper * room
            fit = min(maxopen - open_total, persym - sym_open[sym[j]], dstop - (anchor - (bal - open_total)), room - buffer)
            if fit < risk: risk = fit
            if risk < minrisk: continue
            lots[j] = risk / ur[j]; rk[j] = risk; open_total += risk; sym_open[sym[j]] += risk; nactive += 1
        else:
            if lots[j] <= 0: continue
            pnl = lots[j] * un[j]; lots[j] = 0.0; open_total -= rk[j]; sym_open[sym[j]] -= rk[j]; nactive -= 1
            bal += pnl; day_pnl += pnl; week_pnl += pnl; cum += pnl; trades += 1
            s = 1 if pnl > 0.005 else (-1 if pnl < -0.005 else 0)
            if s != 0:
                if s == cur: clen += 1
                else:
                    if cur == 1: sw += clen; cw += 1
                    elif cur == -1: sl += clen; cl_ += 1
                    cur = s; clen = 1
                if cur == 1 and clen > maxw: maxw = clen
                if cur == -1 and clen > maxl: maxl = clen
            if bal > peak:
                peak = bal
                if not locked:
                    floor = peak - trail
                    if floor >= size:
                        floor = size; locked = True
                        if lock_day < 0: lock_day = (t - t0) / 86400.0
            if cum > cpeak: cpeak = cum
            if cpeak - cum > dd_c: dd_c = cpeak - cum
        if cpeak - (cum - open_total) > dd_s: dd_s = cpeak - (cum - open_total)
        eq = bal - open_total
        if eq < floor or eq < anchor - firm_daily * anchor:
            code = 1; end_t = t; break
    if day_pnl < worst_day: worst_day = day_pnl
    if week_pnl < worst_week: worst_week = week_pnl
    if cur == 1: sw += clen; cw += 1
    elif cur == -1: sl += clen; cl_ += 1
    out = np.zeros(20)
    out[0] = code; out[1] = (end_t - t0) / 86400.0; out[2] = paid; out[3] = npay; out[4] = first_pay; out[5] = trades; out[6] = cum
    out[7] = dd_c; out[8] = dd_s; out[9] = worst_day; out[10] = worst_week; out[11] = maxw; out[12] = maxl
    out[13] = sw / cw if cw > 0 else 0.0; out[14] = sl / cl_ if cl_ > 0 else 0.0; out[15] = bal; out[16] = lock_day; out[17] = win_days; out[18] = loss_days; out[19] = days
    return out


def mc_paths(seg, n, days, seed):
    a, b = SEG[seg]; m = date.fromisoformat(a); m += timedelta(days=(7 - m.weekday()) % 7); end = date.fromisoformat(b); mons = []
    while m + timedelta(days=BLOCK) <= end: mons.append(m); m += timedelta(days=7)
    idx = {m: np.searchsorted(A['op'], [utc_ts(m), utc_ts(m) + BLOCK * DAY]) for m in mons}
    rng = random.Random(seed); t0 = utc_ts(date(2030, 1, 7)); out = []
    for _ in range(n):
        ids, sh = [], []
        for k in range(math.ceil(days / BLOCK) + 1):
            s = mons[rng.randrange(len(mons))]; lo, hi = idx[s]; ids.append(np.arange(lo, hi)); sh.append(np.full(hi - lo, t0 + k * BLOCK * DAY - utc_ts(s)))
        out.append((t0, events(np.concatenate(ids), np.concatenate(sh))))
    return out


def hist_paths(seg, days):
    a, b = SEG[seg]; ev = events(np.nonzero((A['op'] >= utc_ts(a)) & (A['op'] < utc_ts(b)))[0], 0.0); out = []; d = date.fromisoformat(a)
    while utc_ts(d) + days * DAY <= utc_ts(b):
        if d.weekday() < 5: out.append((utc_ts(d), ev))
        d += timedelta(days=1)
    return out


def simulate(paths, members, r, days, cushion=3000.0, share=0.8, cost_r=0.0, g=GUARD):
    on = np.array([k in members for k in KEYS])
    res = []
    for t0, ev in paths:
        un = ev[7] - cost_r * ev[6] if cost_r else ev[7]         # cost stress: subtract cost_r x unit risk per trade
        res.append(kernel(*ev[:7], un, on, len(SYMS), t0, t0 + days * DAY, r / 100 * SIZE, g['taper'], g['maxopen'] * SIZE, g['persym'] * SIZE,
                          g['dstop'] * SIZE, g['buffer'] * SIZE, g['dwin'] * SIZE, g['minrisk'] * SIZE, cushion, share, 0.03, 0.06 * SIZE))
    return np.array(res)


def summary(o, days):
    q = lambda v, p: round(float(np.percentile(v, p)), 0)  # noqa: E731
    weeks = days / 7; br = o[:, 0] == 1; fr = o[:, 0] == 2; paid_w = o[:, 2] / weeks
    alive = o[:, 1]; months = alive / 30.4375
    return dict(paths=len(o), horizon_days=days, payout_week_mean=round(float(paid_w.mean()), 0), payout_week_median=q(paid_w, 50), payout_week_p10=q(paid_w, 10),
                payout_week_p90=q(paid_w, 90), payout_month_mean=round(float(o[:, 2].mean() / (days / 30.4375)), 0), total_paid_mean=round(float(o[:, 2].mean()), 0),
                total_paid_median=q(o[:, 2], 50), payouts_mean=round(float(o[:, 3].mean()), 2), no_payout=round(float((o[:, 3] == 0).mean()), 3),
                first_payout_day_median=round(float(np.median(o[o[:, 4] >= 0, 4])), 0) if (o[:, 4] >= 0).any() else None,
                locked_share=round(float((o[:, 16] >= 0).mean()), 3), lock_day_median=round(float(np.median(o[o[:, 16] >= 0, 16])), 0) if (o[:, 16] >= 0).any() else None,
                breach=round(float(br.mean()), 4), breach_days_mean=round(float(o[br, 1].mean()), 0) if br.any() else None, freeze=round(float(fr.mean()), 4),
                days_alive_median=round(float(np.median(alive)), 0),
                worst_day=round(float(o[:, 9].min()), 0), worst_day_p5=q(o[:, 9], 5), worst_week=round(float(o[:, 10].min()), 0), worst_week_p5=q(o[:, 10], 5),
                dd_closed_median=q(o[:, 7], 50), dd_closed_worst=round(float(o[:, 7].max()), 0), dd_stop_worst=round(float(o[:, 8].max()), 0),
                win_streak_avg=round(float(np.median(o[:, 13])), 2), loss_streak_avg=round(float(np.median(o[:, 14])), 2),
                win_streak_max=float(o[:, 11].max()), loss_streak_max=float(o[:, 12].max()),
                winning_days_share=round(float(np.median(o[:, 17] / np.maximum(o[:, 19], 1))), 3),
                trades_per_month=round(float(np.median(o[:, 5] / np.maximum(months, 1e-9))), 1), trades_per_day=round(float(np.median(o[:, 5] / np.maximum(alive, 1e-9))), 2),
                gross_profit_week_mean=round(float((o[:, 6] / np.maximum(alive / 7, 1e-9)).mean()), 0))


def main():
    out = dict(rows=len(ROWS), keys=KEYS, split=SEG, guard=GUARD, results={})
    mc3 = mc_paths('all', MC_N, 3 * 364, SEED + 1); mc1 = mc_paths('all', MC_N, 365, SEED + 2); hist = hist_paths('all', 365)
    seg1 = {s: mc_paths(s, MC_N, 365, SEED + 3) for s in ('dev', 'val', 'oos')}
    for name, mem in PORTS.items():
        for r in RISKS:
            res = dict(mc3=summary(simulate(mc3, mem, r, 3 * 364), 3 * 364), mc1=summary(simulate(mc1, mem, r, 365), 365), hist1=summary(simulate(hist, mem, r, 365), 365),
                       mc3_cushion1500=summary(simulate(mc3, mem, r, 3 * 364, cushion=1500.0), 3 * 364),
                       mc3_cost010=summary(simulate(mc3, mem, r, 3 * 364, cost_r=0.10), 3 * 364),
                       **{f'{s}_1y': summary(simulate(p, mem, r, 365), 365) for s, p in seg1.items()})
            out['results'][f'{name}|{r}'] = dict(portfolio=name, risk=r, **res)
            m = res['mc3']; print(name, r, 'week', m['payout_week_mean'], 'p10/p90', m['payout_week_p10'], m['payout_week_p90'], 'breach', m['breach'], 'freeze', m['freeze'], flush=True)
    (R / 'FUNDED_SIM.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
