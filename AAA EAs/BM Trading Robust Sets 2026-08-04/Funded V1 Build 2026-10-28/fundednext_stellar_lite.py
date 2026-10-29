"""Owner 2026-10-29: FundedNext Stellar Lite $50K ($183.99) — can funded_v1 reach a payout within a month, and how much?
Rules from the owner's screenshot (fundednext.com, 2026-10-29): 2-step challenge, phase 1 target $4,000 (8%), phase 2 $2,000 (4%), min 2 trading
days per phase, daily loss $2,000 (4%), max loss $4,000 (8%) STATIC, news allowed; funded: same limits, 80% share, first withdrawal 10 days after
the funded start, then every 10 days, no consistency rule, max risk 3% at any time.
ASSUMPTIONS: daily loss measured from the day-start closed balance (UTC day); a phase passes on the first close with balance >= target after
>= 2 trading days (open trades are dropped at that moment); the next account starts the next day; each withdrawal takes all profit above $50k.
Guard = funded_v1 sizing: risk % of $50k, cut to fit open 2% (< 3% max risk) / daily soft stop 2% / buffer 0.25% above the static floor.
Breach = every open position at its stop. Python replay of the same frozen 9-EA ledgers as funded_sim.py — in-sample, NOT a forecast.
python fundednext_stellar_lite.py -> FUNDEDNEXT_STELLAR_LITE.json / .md
"""
import json
from pathlib import Path
import numpy as np
from numba import njit
import funded_sim as f

R = Path(__file__).resolve().parent
FEE = 183.99


@njit(cache=False)
def kernel(et, ek, ej, epd, lane, sym, ur, un, on, nsym, t0, t_end, rdol, maxopen, dstop, buffer, minrisk):
    n = len(ur); lots = np.zeros(n); rk = np.zeros(n)
    size = 50000.0; bal = size; floor = size - 4000.0; anchor = bal; aday = -1; open_total = 0.0; nactive = 0
    phase = 1; tdays = 0; traded_today = False; code = 0; end_t = t_end
    p1_day = -1.0; p2_day = -1.0; funded_t = -1.0; next_pay = -1.0; first_pay_day = -1.0; first_pay = 0.0
    paid30 = 0.0; paid60 = 0.0; paid90 = 0.0; paid180 = 0.0; paid = 0.0; skip_day = -1
    for e in range(len(et)):
        t = et[e]
        if t < t0: continue
        if t >= t_end: break
        pd = epd[e]
        if pd != aday:
            if traded_today: tdays += 1
            traded_today = False; aday = pd; anchor = bal
            if phase == 3 and next_pay > 0 and t >= next_pay:
                if bal > size:
                    amount = 0.8 * (bal - size); paid += amount; bal = size; anchor = bal
                    d = (t - t0) / 86400.0
                    if first_pay_day < 0: first_pay_day = d; first_pay = amount
                    if d <= 30: paid30 += amount
                    if d <= 60: paid60 += amount
                    if d <= 90: paid90 += amount
                    if d <= 180: paid180 += amount
                next_pay = t + 10 * 86400.0
        if pd == skip_day: continue                     # the day a phase passed: the next account starts the next day
        j = ej[e]
        if ek[e] == 1:
            if not on[lane[j]]: continue
            room = bal - open_total - floor
            risk = rdol
            fit = min(maxopen - open_total, dstop - (anchor - (bal - open_total)), room - buffer)
            if fit < risk: risk = fit
            if risk < minrisk: continue
            lots[j] = risk / ur[j]; rk[j] = risk; open_total += risk; nactive += 1; traded_today = True
        else:
            if lots[j] <= 0: continue
            pnl = lots[j] * un[j]; lots[j] = 0.0; open_total -= rk[j]; nactive -= 1; bal += pnl; traded_today = True
            if phase < 3:
                target = size * (1.08 if phase == 1 else 1.04)
                if bal >= target and tdays + 1 >= 2:
                    d = (t - t0) / 86400.0
                    if phase == 1: p1_day = d
                    else: p2_day = d
                    phase += 1; bal = size; anchor = size; open_total = 0.0; nactive = 0; skip_day = pd; tdays = 0; traded_today = False
                    for k in range(n): lots[k] = 0.0
                    if phase == 3: funded_t = t; next_pay = t + 10 * 86400.0
                    continue
        eq = bal - open_total
        if eq < floor or eq < anchor - 2000.0:
            code = phase; end_t = t; break
    out = np.zeros(12)
    out[0] = code; out[1] = (end_t - t0) / 86400.0; out[2] = p1_day; out[3] = p2_day; out[4] = (funded_t - t0) / 86400.0 if funded_t > 0 else -1.0
    out[5] = first_pay_day; out[6] = first_pay; out[7] = paid30; out[8] = paid60; out[9] = paid90; out[10] = paid180; out[11] = paid
    return out


def run(paths, members, r, days):
    on = np.array([k in members for k in f.KEYS])
    return np.array([kernel(*ev[:7], ev[7], on, len(f.SYMS), t0, t0 + days * f.DAY, r / 100 * 50000, 0.02 * 50000, 0.02 * 50000, 0.0025 * 50000, 0.0005 * 50000)
                     for t0, ev in paths])


def summary(o):
    pass1 = o[:, 2] >= 0; funded = o[:, 4] >= 0; fp = o[:, 5] >= 0
    q = lambda v: round(float(np.median(v)), 0) if len(v) else None  # noqa: E731
    return dict(paths=len(o), pass_phase1=round(float(pass1.mean()), 3), funded=round(float(funded.mean()), 3),
                breach_phase1=round(float((o[:, 0] == 1).mean()), 3), breach_phase2=round(float((o[:, 0] == 2).mean()), 3), breach_funded=round(float((o[:, 0] == 3).mean()), 3),
                days_to_funded_median=q(o[funded, 4]), payout_within_30=round(float((fp & (o[:, 5] <= 30)).mean()), 3), payout_within_60=round(float((fp & (o[:, 5] <= 60)).mean()), 3),
                payout_within_90=round(float((fp & (o[:, 5] <= 90)).mean()), 3), first_payout_day_median=q(o[fp, 5]), first_payout_median=q(o[fp, 6]),
                paid_mean_30=round(float(o[:, 7].mean()), 0), paid_mean_60=round(float(o[:, 8].mean()), 0), paid_mean_90=round(float(o[:, 9].mean()), 0),
                paid_mean_180=round(float(o[:, 10].mean()), 0), ev_180=round(float(o[:, 10].mean()) - FEE, 0))


def main():
    mc = f.mc_paths('all', f.MC_N, 180, f.SEED + 9); hist = f.hist_paths('all', 180); out = {}
    for name in ('DI ON', 'DI OFF'):
        for r in (0.5, 1.0, 1.5):
            out[f'{name}|{r}'] = dict(portfolio=name, risk=r, mc=summary(run(mc, f.PORTS[name], r, 180)), hist=summary(run(hist, f.PORTS[name], r, 180)))
            m = out[f'{name}|{r}']['mc']; print(name, r, 'funded', m['funded'], 'days', m['days_to_funded_median'], 'pay<=30', m['payout_within_30'], 'pay<=60', m['payout_within_60'],
                                                'first pay', m['first_payout_median'], 'EV180', m['ev_180'], flush=True)
    (R / 'FUNDEDNEXT_STELLAR_LITE.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    pct = lambda v: f'{100 * v:.0f}%'  # noqa: E731
    usd = lambda v: '-' if v is None else f'${v:,.0f}'  # noqa: E731
    md = ['# FundedNext Stellar Lite $50K with funded_v1 (generated by fundednext_stellar_lite.py)', '',
          'Replay of the 9 EAs\' frozen ledgers 2021-10 → 2026-10; MC = 1,000 resampled 180-day paths; history = every weekday start. In-sample, NOT a forecast.', '',
          '| DI | Risk | Pass phase 1 | Funded (both phases) | Breach P1 / P2 / funded | Median days to funded | Payout ≤ 30 days | ≤ 60 | ≤ 90 | First payout (median day / amount) | Paid by day 90 (mean) | Paid by day 180 − $183.99 fee (mean) |',
          '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for v in out.values():
        for src in ('mc', 'hist'):
            m = v[src]
            md.append(f"| {v['portfolio']} ({'MC' if src == 'mc' else 'history'}) | {v['risk']:g}% | {pct(m['pass_phase1'])} | {pct(m['funded'])} | {pct(m['breach_phase1'])} / {pct(m['breach_phase2'])} / {pct(m['breach_funded'])} | "
                      f"{m['days_to_funded_median']} | {pct(m['payout_within_30'])} | {pct(m['payout_within_60'])} | {pct(m['payout_within_90'])} | {m['first_payout_day_median']} / {usd(m['first_payout_median'])} | "
                      f"{usd(m['paid_mean_90'])} | {usd(m['ev_180'])} |")
    (R / 'FUNDEDNEXT_STELLAR_LITE.md').write_text('\n'.join(md) + '\n', encoding='utf-8'); print('\n'.join(md))


if __name__ == '__main__':
    main()
