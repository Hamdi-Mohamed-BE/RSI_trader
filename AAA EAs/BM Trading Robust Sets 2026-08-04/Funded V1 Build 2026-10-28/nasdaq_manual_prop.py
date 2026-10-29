"""Owner 2026-10-29: trade ONLY the Nasdaq 5M signals manually at a fixed $500 risk per trade on a FundedNext Stellar 1-Step challenge —
how many days to get funded? Rules as in fundednext_compare.py (owner screenshots 2026-10-29): +10% target, daily loss 3% of the day-start
balance (UTC day; assumption), max loss 6% STATIC, min 2 trading days. No guard (manual): every Nasdaq 5M signal is taken at $500,
fractional lots (USTEC ~ $106 per lot at the stop, so 0.01-lot rounding is negligible). Breach = pessimistic (open trade at its stop).
RETRY model: after a breach a new account (new fee) starts the next UTC day on the same path, until funded or day 365.
Manual execution (late fills, missed signals) is NOT modelled: the ledger is the EA's tester fills.
Ledgers: production Nasdaq 5M DI ON (full-eas RISK_ROWS) and DI OFF (Best Prop retest), 2021-10 -> 2026-10. In-sample, NOT a forecast.
python nasdaq_manual_prop.py -> NASDAQ_MANUAL_PROP.json / .md
"""
import json
from pathlib import Path
import numpy as np
from numba import njit
import funded_sim as f

R = Path(__file__).resolve().parent
SIZES = {'$25K': (25000.0, 199.99), '$50K': (50000.0, 247.99), '$100K': (100000.0, 549.99)}   # fees: 50K = owner screenshot; others list (approx.)
LANES = {'DI ON': 'nasdaq-5m-candle-momentum', 'DI OFF': 'nasdaq-5m-di-off'}
RISK = 500.0; HORIZON = 365


@njit(cache=False)
def chain(et, ek, ej, epd, lane, ur, un, lane_on, t0, t_end, size, rdol, target, daily, maxloss):
    n = len(ur); lots = np.zeros(n)
    bal = size; anchor = size; aday = -1; tdays = 0; traded = False; attempts = 1; trades = 0; att_trades = 0
    open_risk = 0.0; rk = np.zeros(n); blocked_until = -1; funded_day = -1.0; first_end = -1.0; first_code = 0
    for e in range(len(et)):
        t = et[e]
        if t < t0: continue
        if t >= t_end: break
        pd = epd[e]
        if pd != aday:
            if traded: tdays += 1
            traded = False; aday = pd; anchor = bal
        if pd <= blocked_until: continue
        j = ej[e]
        if lane[j] != lane_on: continue
        if ek[e] == 1:
            lots[j] = rdol / ur[j]; rk[j] = rdol; open_risk += rdol; traded = True
        else:
            if lots[j] <= 0: continue
            pnl = lots[j] * un[j]; lots[j] = 0.0; open_risk -= rk[j]; bal += pnl; traded = True; trades += 1; att_trades += 1
            if bal >= size * (1.0 + target) and tdays + 1 >= 2:
                funded_day = (t - t0) / 86400.0
                if first_end < 0: first_end = funded_day; first_code = 1
                break
        eq = bal - open_risk
        if eq <= size - maxloss * size or eq <= anchor - daily * size:
            if first_end < 0: first_end = (t - t0) / 86400.0; first_code = 2
            attempts += 1; bal = size; anchor = size; tdays = 0; traded = False; open_risk = 0.0; att_trades = 0
            for k in range(n): lots[k] = 0.0
            blocked_until = pd                          # the new account starts the next day
    out = np.zeros(6)
    out[0] = funded_day; out[1] = 1.0 if funded_day >= 0 else 0.0
    out[2] = first_code; out[3] = first_end; out[4] = trades; out[5] = attempts
    return out


def run(paths, lane_key, size):
    lane_on = f.KEYS.index(lane_key)
    return np.array([chain(ev[0], ev[1], ev[2], ev[3], ev[4], ev[6], ev[7], lane_on, t0, t0 + HORIZON * f.DAY, size, RISK, 0.10, 0.03, 0.06) for t0, ev in paths])


def summary(o, fee):
    fd = o[:, 0]; ok = fd >= 0; first_pass = o[:, 2] == 1; first_breach = o[:, 2] == 2
    med = lambda v: round(float(np.median(v)), 0) if len(v) else None  # noqa: E731
    att = o[:, 5]
    return dict(paths=len(o), first_attempt_pass=round(float(first_pass.mean()), 3), first_attempt_breach=round(float(first_breach.mean()), 3),
                first_attempt_open=round(float((o[:, 2] == 0).mean()), 3), first_attempt_pass_day_median=med(o[first_pass, 3]),
                first_attempt_breach_day_median=med(o[first_breach, 3]),
                funded_within_30=round(float((ok & (fd <= 30)).mean()), 3), funded_within_60=round(float((ok & (fd <= 60)).mean()), 3),
                funded_within_90=round(float((ok & (fd <= 90)).mean()), 3), funded_within_180=round(float((ok & (fd <= 180)).mean()), 3),
                funded_within_365=round(float(ok.mean()), 3), days_to_funded_median=med(fd[ok]), days_to_funded_p25=round(float(np.percentile(fd[ok], 25)), 0) if ok.any() else None,
                days_to_funded_p75=round(float(np.percentile(fd[ok], 75)), 0) if ok.any() else None,
                accounts_bought_mean=round(float(att.mean()), 2), accounts_bought_median=med(att), fees_mean=round(float(att.mean() * fee), 0),
                accounts_if_funded_mean=round(float(att[ok].mean()), 2) if ok.any() else None, trades_mean=round(float(o[:, 4].mean()), 1))


def main():
    mc = f.mc_paths('all', 3000, HORIZON, f.SEED + 21); hist = f.hist_paths('all', HORIZON)
    seg = {s: f.mc_paths(s, 2000, HORIZON, f.SEED + 22 + i) for i, s in enumerate(('dev', 'val', 'oos'))}
    out = {}
    for di, lane_key in LANES.items():
        for sz, (size, fee) in SIZES.items():
            key = f'{di}|{sz}'
            out[key] = dict(di=di, size=sz, fee=fee, risk_pct=round(100 * RISK / size, 2), mc=summary(run(mc, lane_key, size), fee), hist=summary(run(hist, lane_key, size), fee),
                            **{s: summary(run(p, lane_key, size), fee) for s, p in seg.items()})
            m = out[key]['mc']; print(key, 'first pass', m['first_attempt_pass'], 'breach', m['first_attempt_breach'], 'median days', m['days_to_funded_median'],
                                        '<=30', m['funded_within_30'], '<=90', m['funded_within_90'], 'accounts', m['accounts_bought_mean'], flush=True)
    (R / 'NASDAQ_MANUAL_PROP.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    pct = lambda v: f'{100 * v:.0f}%'  # noqa: E731
    md = ['# Nasdaq 5M only, $500 per trade, FundedNext Stellar 1-Step (generated by nasdaq_manual_prop.py)', '',
          'Retry after a breach on the same timeline, up to 365 days. MC = 3,000 resampled paths (history in brackets). In-sample, NOT a forecast.', '',
          '| DI | Account (risk %) | 1st attempt pass / breach / still open | 1st attempt pass day (median) | Funded ≤ 30 / 60 / 90 / 180 d (incl. retries) | Median days to funded (p25–p75) | Accounts bought (mean) | Fees (mean) | Trades to the end |',
          '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for v in out.values():
        m, h = v['mc'], v['hist']
        md.append(f"| {v['di']} | {v['size']} ({v['risk_pct']}%) | {pct(m['first_attempt_pass'])} / {pct(m['first_attempt_breach'])} / {pct(m['first_attempt_open'])} ({pct(h['first_attempt_pass'])} pass hist) | "
                  f"{m['first_attempt_pass_day_median']} | {pct(m['funded_within_30'])} / {pct(m['funded_within_60'])} / {pct(m['funded_within_90'])} / {pct(m['funded_within_180'])} | "
                  f"{m['days_to_funded_median']} ({m['days_to_funded_p25']}–{m['days_to_funded_p75']}) [hist {h['days_to_funded_median']}] | {m['accounts_bought_mean']} | ${m['fees_mean']:,.0f} | {m['trades_mean']} |")
    md += ['', '## By market period (MC, median days to funded / funded ≤ 90 d)', '', '| DI | Account | 2021-23 | 2023-24 | 2024-26 |', '|---|---|---:|---:|---:|']
    for v in out.values():
        md.append(f"| {v['di']} | {v['size']} | " + ' | '.join(f"{v[s]['days_to_funded_median']} d / {pct(v[s]['funded_within_90'])}" for s in ('dev', 'val', 'oos')) + ' |')
    (R / 'NASDAQ_MANUAL_PROP.md').write_text('\n'.join(md) + '\n', encoding='utf-8'); print('\n'.join(md))


if __name__ == '__main__':
    main()
