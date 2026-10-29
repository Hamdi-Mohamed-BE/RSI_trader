"""Owner 2026-10-29: FundedNext CFD offers with funded_v1 (9 EAs) — Stellar 1-Step $50K ($247.99) vs Stellar Lite $50K ($183.99).
Rules from the owner's screenshots (fundednext.com, 2026-10-29), all STATIC drawdown, no consistency rule, max risk 3% at any time:
  Stellar 1-Step: one phase +10% ($5,000), daily 3% ($1,500), max 6% ($3,000), min 2 trading days; funded: same limits, first withdrawal
                  5 business days (~7 calendar days) after the funded start, then every 5 days; share 80% (95% shown as upside); fee
                  refunded at the 3rd reward.
  Stellar Lite:   phase 1 +8% ($4,000), phase 2 +4% ($2,000), daily 4% ($2,000), max 8% ($4,000), min 2 days; funded first withdrawal 10 days,
                  then every 10 days; 80%; fee refunded at the 3rd reward.
ASSUMPTIONS: daily loss from the day-start closed balance (UTC day); a phase passes on the first close at/above target after >= 2 trading days
(open trades dropped); the next account starts the next day; each withdrawal takes all profit above $50k (static floor, so room is unchanged);
fee refund (3rd reward) counted. Guard = funded_v1 sizing (risk % of $50k, cut to fit open 2% / daily soft stop 2% / buffer 0.25%).
Breach = every open position at its stop. Python replay of the frozen 9-EA ledgers (funded_sim.py) — in-sample, NOT a forecast.
python fundednext_compare.py -> FUNDEDNEXT_COMPARE.json / .md
"""
import json
from pathlib import Path
import numpy as np
from numba import njit
import funded_sim as f

R = Path(__file__).resolve().parent
OFFERS = {'Stellar 1-Step': dict(fee=247.99, t1=0.10, t2=0.0, daily=1500.0, maxloss=3000.0, first=7.0, every=5.0),
          'Stellar Lite': dict(fee=183.99, t1=0.08, t2=0.04, daily=2000.0, maxloss=4000.0, first=10.0, every=10.0)}


@njit(cache=False)
def kernel(et, ek, ej, epd, lane, sym, ur, un, on, nsym, t0, t_end, rdol, maxopen, dstop, buffer, minrisk, t1, t2, daily, maxloss, first, every, share):
    n = len(ur); lots = np.zeros(n); rk = np.zeros(n)
    size = 50000.0; bal = size; floor = size - maxloss; anchor = bal; aday = -1; open_total = 0.0
    phase = 1; nphases = 1 if t2 <= 0 else 2; tdays = 0; traded_today = False; code = 0; end_t = t_end
    funded_t = -1.0; next_pay = -1.0; first_pay_day = -1.0; first_pay = 0.0; npay = 0; third_day = -1.0
    paid30 = 0.0; paid60 = 0.0; paid90 = 0.0; paid180 = 0.0; skip_day = -1
    for e in range(len(et)):
        t = et[e]
        if t < t0: continue
        if t >= t_end: break
        pd = epd[e]
        if pd != aday:
            if traded_today: tdays += 1
            traded_today = False; aday = pd; anchor = bal
            if phase > nphases and next_pay > 0 and t >= next_pay:
                if bal > size:
                    amount = share * (bal - size); bal = size; anchor = bal; npay += 1
                    d = (t - t0) / 86400.0
                    if first_pay_day < 0: first_pay_day = d; first_pay = amount
                    if npay == 3: third_day = d
                    if d <= 30: paid30 += amount
                    if d <= 60: paid60 += amount
                    if d <= 90: paid90 += amount
                    if d <= 180: paid180 += amount
                next_pay = t + every * 86400.0
        if pd == skip_day: continue
        j = ej[e]
        if ek[e] == 1:
            if not on[lane[j]]: continue
            room = bal - open_total - floor
            risk = rdol
            fit = min(maxopen - open_total, dstop - (anchor - (bal - open_total)), room - buffer)
            if fit < risk: risk = fit
            if risk < minrisk: continue
            lots[j] = risk / ur[j]; rk[j] = risk; open_total += risk; traded_today = True
        else:
            if lots[j] <= 0: continue
            pnl = lots[j] * un[j]; lots[j] = 0.0; open_total -= rk[j]; bal += pnl; traded_today = True
            if phase <= nphases:
                target = size * (1.0 + (t1 if phase == 1 else t2))
                if bal >= target and tdays + 1 >= 2:
                    phase += 1; bal = size; anchor = size; open_total = 0.0; skip_day = pd; tdays = 0; traded_today = False
                    for k in range(n): lots[k] = 0.0
                    if phase > nphases: funded_t = t; next_pay = t + first * 86400.0
                    continue
        eq = bal - open_total
        if eq < floor or eq < anchor - daily:
            code = phase; end_t = t; break
    out = np.zeros(11)
    out[0] = code; out[1] = (funded_t - t0) / 86400.0 if funded_t > 0 else -1.0; out[2] = first_pay_day; out[3] = first_pay
    out[4] = paid30; out[5] = paid60; out[6] = paid90; out[7] = paid180; out[8] = npay; out[9] = third_day; out[10] = 1.0 if code > nphases else 0.0
    return out


def run(paths, members, r, offer, share):
    on = np.array([k in members for k in f.KEYS]); o = OFFERS[offer]
    return np.array([kernel(*ev[:7], ev[7], on, len(f.SYMS), t0, t0 + 180 * f.DAY, r / 100 * 50000, 0.02 * 50000, 0.02 * 50000, 0.0025 * 50000, 0.0005 * 50000,
                            o['t1'], o['t2'], o['daily'], o['maxloss'], o['first'], o['every'], share) for t0, ev in paths])


def summary(o, fee):
    funded = o[:, 1] >= 0; fp = o[:, 2] >= 0; refund = (o[:, 9] >= 0) & (o[:, 9] <= 180)
    med = lambda v: round(float(np.median(v)), 0) if len(v) else None  # noqa: E731
    return dict(funded=round(float(funded.mean()), 3), breach_challenge=round(float(((o[:, 0] > 0) & (o[:, 10] == 0)).mean()), 3),
                breach_funded=round(float((o[:, 10] == 1).mean()), 3), days_to_funded=med(o[funded, 1]),
                pay30=round(float((fp & (o[:, 2] <= 30)).mean()), 3), pay60=round(float((fp & (o[:, 2] <= 60)).mean()), 3), pay90=round(float((fp & (o[:, 2] <= 90)).mean()), 3),
                first_day=med(o[fp, 2]), first_amount=med(o[fp, 3]), paid30=round(float(o[:, 4].mean()), 0), paid90=round(float(o[:, 6].mean()), 0),
                paid180=round(float(o[:, 7].mean()), 0), ev180=round(float((o[:, 7] + refund * fee).mean()) - fee, 0),
                lose_fee_180=round(float((o[:, 7] + refund * fee < fee).mean()), 3))


def main():
    mc = f.mc_paths('all', f.MC_N, 180, f.SEED + 9); hist = f.hist_paths('all', 180); out = {}
    for offer, o in OFFERS.items():
        for r in (0.5, 1.0, 1.5):
            for share in (0.8, 0.95):
                if share == 0.95 and offer != 'Stellar 1-Step': continue
                key = f'{offer}|{r}|{share}'
                out[key] = dict(offer=offer, risk=r, share=share, mc=summary(run(mc, f.PORTS['DI ON'], r, offer, share), o['fee']),
                                hist=summary(run(hist, f.PORTS['DI ON'], r, offer, share), o['fee']))
                m = out[key]['mc']; print(key, 'funded', m['funded'], 'days', m['days_to_funded'], 'pay30', m['pay30'], 'pay60', m['pay60'], 'first', m['first_amount'], 'EV180', m['ev180'], flush=True)
    (R / 'FUNDEDNEXT_COMPARE.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    pct = lambda v: f'{100 * v:.0f}%'  # noqa: E731
    usd = lambda v: '-' if v is None else f'${v:,.0f}'  # noqa: E731
    md = ['# FundedNext Stellar 1-Step vs Stellar Lite ($50K) with funded_v1, Nasdaq DI ON (generated by fundednext_compare.py)', '',
          'Replay of the 9 EAs\' frozen ledgers 2021-10 → 2026-10, 180-day horizon; MC = 1,000 resampled paths / history = every weekday start. In-sample, NOT a forecast.', '',
          '| Offer | Risk | Share | Funded ≤ 180 d (MC / hist) | Breach challenge / funded (MC) | Median days to funded | Payout ≤ 30 d | ≤ 60 d | ≤ 90 d | First payout median (day / amount) | Paid by day 90 (mean) | Net after fee by day 180 (mean, incl. refund) | Fee lost (no net gain by day 180) |',
          '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for v in out.values():
        m, h = v['mc'], v['hist']
        md.append(f"| {v['offer']} | {v['risk']:g}% | {int(v['share'] * 100)}% | {pct(m['funded'])} / {pct(h['funded'])} | {pct(m['breach_challenge'])} / {pct(m['breach_funded'])} | {m['days_to_funded']} | "
                  f"{pct(m['pay30'])} | {pct(m['pay60'])} | {pct(m['pay90'])} | {m['first_day']} / {usd(m['first_amount'])} | {usd(m['paid90'])} | {usd(m['ev180'])} | {pct(m['lose_fee_180'])} |")
    (R / 'FUNDEDNEXT_COMPARE.md').write_text('\n'.join(md) + '\n', encoding='utf-8'); print('\n'.join(md))


if __name__ == '__main__':
    main()
