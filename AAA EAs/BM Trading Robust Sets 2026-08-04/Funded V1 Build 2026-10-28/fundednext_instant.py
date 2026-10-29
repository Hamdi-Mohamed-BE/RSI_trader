"""Owner 2026-10-29: which FundedNext CFD offer pays out within 30 days with funded_v1? The instant products (no challenge) with the same
9-EA ledgers and guard sizing as fundednext_compare.py. Rules from the owner's screenshots (fundednext.com, 2026-10-29):
  Stellar Instant ($2K $49.99 / $5K $119.99 / $10K $239.99 / $20K $479.99): no target, no daily loss limit, max loss 6% TRAILING, no
                  consistency rule, max risk 3% at any time, withdrawals on-demand / bi-weekly, share up to 80%.
  FNL:004 ($50K $149.99): rewards in 5 days, no daily loss limit, max loss 4% TRAILING, perpetual consistency 20%, no risk rule, 80% share,
                  max $1,200 per withdrawal, max 5 performance rewards.
UNKNOWN on the pages -> two readings of the trailing floor after a payout: REBASE (floor trails again from the post-payout balance) and LOCK
(floor locks at the start size once reached and after any payout, like Leveraged; then only profit above size + one trail is withdrawn).
Trailing = highest CLOSED balance (assumption). Withdrawals: Stellar Instant first possible on day 14 then every 14 days (bi-weekly; on-demand
day-7 shown as a sensitivity); FNL:004 every 5 days, best day < 20% of the period profit, capped $1,200, max 5.
Guard = funded_v1 defaults scaled to the account: risk % of size, taper 5% of room, open 2%, daily soft stop 2%, buffer 0.25%.
Fractional lots (small accounts like $2K-$5K cannot size this finely on real brokers). Breach = every open position at its stop.
In-sample replay, NOT a forecast. python fundednext_instant.py -> FUNDEDNEXT_INSTANT.json / .md
"""
import json
from pathlib import Path
import numpy as np
from numba import njit
import funded_sim as f

R = Path(__file__).resolve().parent
OFFERS = {'Stellar Instant 20K': dict(size=20000.0, fee=479.99, trail=0.06, first=14.0, every=14.0, cap=1e12, maxpay=1000, consistency=0.0),
          'Stellar Instant 10K': dict(size=10000.0, fee=239.99, trail=0.06, first=14.0, every=14.0, cap=1e12, maxpay=1000, consistency=0.0),
          'Stellar Instant 20K on-demand d7': dict(size=20000.0, fee=479.99, trail=0.06, first=7.0, every=7.0, cap=1e12, maxpay=1000, consistency=0.0),
          'FNL:004 50K': dict(size=50000.0, fee=149.99, trail=0.04, first=5.0, every=5.0, cap=1200.0, maxpay=5, consistency=0.2)}


@njit(cache=False)
def kernel(et, ek, ej, epd, lane, sym, ur, un, on, nsym, t0, t_end, size, rpct, trail, first, every, cap, maxpay, consistency, share, lock):
    n = len(ur); lots = np.zeros(n); rk = np.zeros(n)
    bal = size; peak = size; floor = size - trail * size; locked = False; anchor = bal; aday = -1; open_total = 0.0
    taper = 0.05; maxopen = 0.02 * size; dstop = 0.02 * size; buffer = 0.0025 * size; minrisk = 0.0005 * size; rdol = rpct * size
    code = 0; end_t = t_end; next_pay = t0 + first * 86400.0; npay = 0; first_day = -1.0; first_amt = 0.0
    paid30 = 0.0; paid90 = 0.0; paid180 = 0.0; day_pnl = 0.0; max_day = 0.0; period = 0.0
    for e in range(len(et)):
        t = et[e]
        if t < t0: continue
        if t >= t_end: break
        pd = epd[e]
        if pd != aday:
            if aday != -1:
                if day_pnl > max_day: max_day = day_pnl
                period += day_pnl
            day_pnl = 0.0; aday = pd; anchor = bal
            if t >= next_pay and npay < maxpay:
                base = size + (trail * size if lock else 0.0)
                gain = bal - base
                ok = gain > 0 and (consistency <= 0 or (period > 0 and max_day < consistency * period))
                if ok:
                    amount = min(cap, share * gain); bal -= amount / share; npay += 1; anchor = bal
                    d = (t - t0) / 86400.0
                    if first_day < 0: first_day = d; first_amt = amount
                    if d <= 30: paid30 += amount
                    if d <= 90: paid90 += amount
                    if d <= 180: paid180 += amount
                    max_day = 0.0; period = 0.0
                    if lock: locked = True; floor = size
                    else: peak = bal; floor = peak - trail * size
                next_pay = t + every * 86400.0
            if open_total == 0 and bal - floor - buffer < minrisk:
                code = 2; end_t = t; break
        j = ej[e]
        if ek[e] == 1:
            if not on[lane[j]]: continue
            room = bal - open_total - floor
            risk = rdol
            if taper * room < risk: risk = taper * room
            fit = min(maxopen - open_total, dstop - (anchor - (bal - open_total)), room - buffer)
            if fit < risk: risk = fit
            if risk < minrisk: continue
            lots[j] = risk / ur[j]; rk[j] = risk; open_total += risk
        else:
            if lots[j] <= 0: continue
            pnl = lots[j] * un[j]; lots[j] = 0.0; open_total -= rk[j]; bal += pnl; day_pnl += pnl
            if bal > peak:
                peak = bal
                if not locked:
                    floor = peak - trail * size
                    if lock and floor >= size: floor = size; locked = True
        if bal - open_total < floor:
            code = 1; end_t = t; break
    out = np.zeros(8)
    out[0] = code; out[1] = (end_t - t0) / 86400.0; out[2] = first_day; out[3] = first_amt; out[4] = paid30; out[5] = paid90; out[6] = paid180; out[7] = npay
    return out


def run(paths, offer, r, lock):
    o = OFFERS[offer]; on = np.array([k in f.PORTS['DI ON'] for k in f.KEYS])
    return np.array([kernel(*ev[:7], ev[7], on, len(f.SYMS), t0, t0 + 180 * f.DAY, o['size'], r / 100, o['trail'], o['first'], o['every'], o['cap'], o['maxpay'],
                            o['consistency'], 0.8, lock) for t0, ev in paths])


def summary(o, fee):
    fp = o[:, 2] >= 0; med = lambda v: round(float(np.median(v)), 0) if len(v) else None  # noqa: E731
    return dict(pay30=round(float((fp & (o[:, 2] <= 30)).mean()), 3), pay60=round(float((fp & (o[:, 2] <= 60)).mean()), 3), pay90=round(float((fp & (o[:, 2] <= 90)).mean()), 3),
                first_day=med(o[fp, 2]), first_amount=med(o[fp, 3]), first_amount_30=med(o[fp & (o[:, 2] <= 30), 3]),
                paid30=round(float(o[:, 4].mean()), 0), paid90=round(float(o[:, 5].mean()), 0), paid180=round(float(o[:, 6].mean()), 0),
                net30=round(float(o[:, 4].mean()) - fee, 0), net180=round(float(o[:, 6].mean()) - fee, 0), breach180=round(float((o[:, 0] == 1).mean()), 3),
                breach30=round(float(((o[:, 0] == 1) & (o[:, 1] <= 30)).mean()), 3), frozen=round(float((o[:, 0] == 2).mean()), 3))


def main():
    mc = f.mc_paths('all', f.MC_N, 180, f.SEED + 9); hist = f.hist_paths('all', 180); out = {}
    for offer, o in OFFERS.items():
        for r in (0.5, 1.0):
            for lock in (False, True):
                key = f'{offer}|{r}|{"lock" if lock else "rebase"}'
                out[key] = dict(offer=offer, risk=r, after_payout='lock' if lock else 'rebase', fee=o['fee'], mc=summary(run(mc, offer, r, lock), o['fee']),
                                hist=summary(run(hist, offer, r, lock), o['fee']))
                m = out[key]['mc']; print(key, 'pay30', m['pay30'], 'first', m['first_day'], m['first_amount'], 'net30', m['net30'], 'net180', m['net180'], 'breach', m['breach180'], flush=True)
    (R / 'FUNDEDNEXT_INSTANT.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    pct = lambda v: f'{100 * v:.0f}%'  # noqa: E731
    usd = lambda v: '-' if v is None else f'${v:,.0f}'  # noqa: E731
    md = ['# FundedNext instant accounts with funded_v1, Nasdaq DI ON (generated by fundednext_instant.py)', '',
          'Replay of the 9 EAs\' frozen ledgers 2021-10 → 2026-10, 180-day horizon, MC = 1,000 resampled paths (history in brackets). In-sample, NOT a forecast.', '',
          '| Offer | Risk | Floor after payout | Paid within 30 d (MC / hist) | ≤ 60 d | ≤ 90 d | First payout median: day / amount | Paid by day 30, mean − fee | Paid by day 180, mean − fee | Breach ≤ 30 d / ≤ 180 d | Frozen |',
          '|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for v in out.values():
        m, h = v['mc'], v['hist']
        md.append(f"| {v['offer']} (${v['fee']}) | {v['risk']:g}% | {v['after_payout']} | {pct(m['pay30'])} ({pct(h['pay30'])}) | {pct(m['pay60'])} | {pct(m['pay90'])} | "
                  f"{m['first_day']} / {usd(m['first_amount'])} | {usd(m['net30'])} | {usd(m['net180'])} | {pct(m['breach30'])} / {pct(m['breach180'])} | {pct(m['frozen'])} |")
    (R / 'FUNDEDNEXT_INSTANT.md').write_text('\n'.join(md) + '\n', encoding='utf-8'); print('\n'.join(md))


if __name__ == '__main__':
    main()
