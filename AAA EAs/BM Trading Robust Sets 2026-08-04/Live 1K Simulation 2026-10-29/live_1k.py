"""Owner 2026-10-29: the best EAs on a $1,000 LIVE account, fixed $50 risk per trade — expected daily / weekly income, max closed DD, and
what the account could be after one month. Python/numba replay of the same frozen native ledgers as funded_v1 (funded_sim.py) — NOT a native
combined run, NOT a forecast.
Portfolios: P9 = funded_v1's 9 EAs (Nasdaq DI ON); TOP2 = XAU RSI VWAP + Nasdaq 5M (the only two that passed both recent-window screens 2026-09-30).
Sizing: fixed dollar risk per trade (no compounding), lot step 0.01, minimum 0.01.
  MAIN (owner 2026-10-29 "risk 50$ or use lowest lot") = round DOWN to the step; if that is under 0.01 lot, open 0.01 lot.
  MIN  = always 0.01 lot (the lowest lot), whatever the stop.
  UP   = the normal Calyx BAT rule (round UP, minimum lot if needed), shown for reference.
NASCAP cases: the production Nasdaq 5M EA sizes only as % of equity, hard-capped at 1% (MathMin(InpRiskPercent,1.00)), so on $1k its
  trades risk min($ target, 1% of balance) ~= $10; the other EAs keep the $ target. This is what the current EX5 can actually do.
No firm rules, no guard, no daily stop: every signal is taken. Margin is NOT modelled (leverage-dependent).
Bust, two readings (trading stops there): PESSIMISTIC = stop-marked equity (balance minus every open stop) <= $0;
  CLOSED = closed balance <= $0. Real equity lies between (no intratrade prices in the ledgers).
Costs = the tester's commission + swap in the ledgers; +0.10R per trade shown as a stress.
MC = 4-week blocks resampled from 2021-10 -> 2026-10 (seed 20261029); history = every weekday start.
python live_1k.py -> LIVE_1K.json / LIVE_1K.md
"""
import json, sys
from pathlib import Path
import numpy as np
from numba import njit

R = Path(__file__).resolve().parent
sys.path.insert(0, str(R.parent / 'Funded V1 Build 2026-10-28'))
import funded_sim as f  # noqa: E402

START_BAL = 1000.0; SEED = 20261029
PORTS = {'P9 (funded_v1 9 EAs)': f.PORTS['DI ON'], 'TOP2 (RSI VWAP + Nasdaq 5M)': ['xau-rsi-vwap', 'nasdaq-5m-candle-momentum']}
CASES = [('$50 or lowest lot', 50.0, 2, 0.0, 0), ('$50 or lowest lot, Nasdaq capped 1% (current EX5)', 50.0, 2, 0.0, 1),
         ('$50 or lowest lot, +0.10R cost', 50.0, 2, 0.10, 0), ('Always 0.01 lot', 0.0, 3, 0.0, 0),
         ('$25 or lowest lot', 25.0, 2, 0.0, 0), ('$50 round UP (BAT rule)', 50.0, 1, 0.0, 0)]
NAS = ('nasdaq-5m-candle-momentum', 'nasdaq-5m-di-off')


@njit(cache=False)
def kernel(et, ek, ej, epd, lane, sym, ur, un, on, cap1, t0, t_end, rdol, mode, cost_r, start, pess):
    n = len(ur); lots = np.zeros(n); rk = np.zeros(n)
    bal = start; open_total = 0.0; peak = start; dd_c = 0.0; dd_s = 0.0; min_bal = start; bust = 0; bust_day = -1.0
    trades = 0; skipped = 0; wins = 0; gross_w = 0.0; gross_l = 0.0; risk_sum = 0.0; max_open = 0.0
    aday = -1; day_pnl = 0.0; worst_day = 0.0; best_day = 0.0; awk = -1; week_pnl = 0.0; worst_week = 0.0; days = 0; win_days = 0
    for e in range(len(et)):
        t = et[e]
        if t < t0: continue
        if t >= t_end: break
        pd = epd[e]
        if pd != aday:
            if aday != -1:
                if day_pnl < worst_day: worst_day = day_pnl
                if day_pnl > best_day: best_day = day_pnl
                if day_pnl > 0.005: win_days += 1
                days += 1
            wk = (pd + 3) // 7
            if wk != awk:
                if awk != -1 and week_pnl < worst_week: worst_week = week_pnl
                week_pnl = 0.0; awk = wk
            aday = pd; day_pnl = 0.0
        j = ej[e]
        if ek[e] == 1:
            if not on[lane[j]]: continue
            tgt = rdol
            if cap1[lane[j]] and 0.01 * bal < tgt: tgt = 0.01 * bal
            raw = tgt / ur[j] if mode != 3 else 0.01
            if mode == 3:
                l = 0.01
            elif mode == 2:
                l = np.floor(raw / 0.01 + 1e-9) * 0.01
                if l < 0.01: l = 0.01
            elif mode == 1:
                l = np.ceil(raw / 0.01 - 1e-9) * 0.01
                if l < 0.01: l = 0.01
            else:
                l = np.floor(raw / 0.01 + 1e-9) * 0.01
                if l < 0.01:
                    skipped += 1; continue
            lots[j] = l; rk[j] = l * ur[j]; open_total += rk[j]; risk_sum += rk[j]
            if open_total > max_open: max_open = open_total
        else:
            if lots[j] <= 0: continue
            pnl = lots[j] * (un[j] - cost_r * ur[j]); lots[j] = 0.0; open_total -= rk[j]
            bal += pnl; day_pnl += pnl; week_pnl += pnl; trades += 1
            if pnl > 0: wins += 1; gross_w += pnl
            else: gross_l -= pnl
            if bal > peak: peak = bal
            if peak - bal > dd_c: dd_c = peak - bal
            if bal < min_bal: min_bal = bal
        eq_s = bal - open_total
        if peak - eq_s > dd_s: dd_s = peak - eq_s
        if (pess == 1 and eq_s <= 0.0) or bal <= 0.0:
            bust = 1; bust_day = (t - t0) / 86400.0; break
    if day_pnl < worst_day: worst_day = day_pnl
    if day_pnl > best_day: best_day = day_pnl
    if week_pnl < worst_week: worst_week = week_pnl
    if aday != -1: days += 1
    out = np.zeros(20)
    out[0] = bal; out[1] = bal - start; out[2] = trades; out[3] = skipped; out[4] = dd_c; out[5] = dd_s; out[6] = min_bal; out[7] = bust; out[8] = bust_day
    out[9] = worst_day; out[10] = best_day; out[11] = worst_week; out[12] = wins; out[13] = gross_w; out[14] = gross_l; out[15] = risk_sum / max(trades + 0.0, 1.0)
    out[16] = max_open; out[17] = days; out[18] = win_days
    return out


def run(paths, members, days, rdol, mode, cost_r, pess=1, nascap=0):
    on = np.array([k in members for k in f.KEYS]); cap1 = np.array([bool(nascap) and k in NAS for k in f.KEYS])
    return np.array([kernel(*ev[:7], ev[7], on, cap1, t0, t0 + days * f.DAY, rdol, mode, cost_r, START_BAL, pess) for t0, ev in paths])


def summary(o, days):
    q = lambda v, p: round(float(np.percentile(v, p)), 0)  # noqa: E731
    pnl = o[:, 1]; weeks = days / 7; tr = o[:, 2]
    pf = o[:, 13].sum() / max(o[:, 14].sum(), 1e-9)
    return dict(paths=len(o), days=days, pnl_mean=round(float(pnl.mean()), 0), pnl_median=q(pnl, 50), pnl_p10=q(pnl, 10), pnl_p90=q(pnl, 90), pnl_p5=q(pnl, 5),
                end_median=q(o[:, 0], 50), loss_share=round(float((pnl < 0).mean()), 3), below_500=round(float((o[:, 6] < 500).mean()), 3),
                bust=round(float(o[:, 7].mean()), 4), bust_day_median=round(float(np.median(o[o[:, 7] == 1, 8])), 0) if (o[:, 7] == 1).any() else None,
                week_mean=round(float(pnl.mean() / weeks), 0), week_median=round(float(np.median(pnl) / weeks), 0), day_mean=round(float(pnl.mean() / days), 1),
                trade_day_mean=round(float(pnl.mean() / max(np.median(o[:, 17]), 1)), 1),
                dd_closed_median=q(o[:, 4], 50), dd_closed_p90=q(o[:, 4], 90), dd_closed_max=round(float(o[:, 4].max()), 0),
                dd_stop_median=q(o[:, 5], 50), dd_stop_p90=q(o[:, 5], 90), worst_day_p5=q(o[:, 9], 5), worst_day=round(float(o[:, 9].min()), 0),
                worst_week_p5=q(o[:, 11], 5), best_day_median=q(o[:, 10], 50),
                trades=round(float(tr.mean()), 1), trades_month=round(float(tr.mean() / (days / 30.4375)), 1), trades_day=round(float(tr.mean() / days), 2),
                skipped=round(float(o[:, 3].mean()), 1), win_rate=round(float(o[:, 12].sum() / max(tr.sum(), 1)), 3), pf=round(float(pf), 2),
                avg_risk=round(float(np.median(o[:, 15])), 1), max_open_risk_median=q(o[:, 16], 50), max_open_risk_p90=q(o[:, 16], 90),
                win_days_share=round(float(np.median(o[:, 18] / np.maximum(o[:, 17], 1))), 3))


def main():
    hz = {'1 month': 30, '3 months': 91, '1 year': 365}
    mc = {k: f.mc_paths('all', 5000 if d <= 30 else 2000, d, SEED + d) for k, d in hz.items()}
    hist = {k: f.hist_paths('all', d) for k, d in hz.items()}
    seg = {s: f.mc_paths(s, 3000, 30, SEED + 7 + i) for i, s in enumerate(('dev', 'val', 'oos'))}
    out = dict(start_balance=START_BAL, split=f.SEG, ledgers=dict(rows=len(f.ROWS), start=f.START, end=f.END), results={})
    for pname, mem in PORTS.items():
        for cname, rdol, mode, cost, nc in CASES:
            res = {}
            for k, d in hz.items():
                res[f'mc {k}'] = summary(run(mc[k], mem, d, rdol, mode, cost, 1, nc), d)
                res[f'mc {k}']['bust_closed'] = summary(run(mc[k], mem, d, rdol, mode, cost, 0, nc), d)['bust']
                res[f'hist {k}'] = summary(run(hist[k], mem, d, rdol, mode, cost, 1, nc), d)
            for s, p in seg.items():
                res[f'mc 1 month {s}'] = summary(run(p, mem, 30, rdol, mode, cost, 1, nc), 30)
            out['results'][f'{pname}|{cname}'] = dict(portfolio=pname, case=cname, **res)
            m = res['mc 1 month']; y = res['mc 1 year']
            print(pname, cname, '1m mean', m['pnl_mean'], 'med', m['pnl_median'], 'p10/p90', m['pnl_p10'], m['pnl_p90'], 'bust', m['bust'], '| 1y mean', y['pnl_mean'],
                  'ddC med', y['dd_closed_median'], 'p90', y['dd_closed_p90'], 'bust', y['bust'], flush=True)
    (R / 'LIVE_1K.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    usd = lambda v: '-' if v is None else (f'-${-v:,.0f}' if v < 0 else f'${v:,.0f}')  # noqa: E731
    pct = lambda v: f'{100 * v:.1f}%'  # noqa: E731
    md = ['# $1,000 live account, fixed dollar risk per trade (generated by live_1k.py)', '',
          f"Replay of frozen native ledgers {f.START} → {f.END}; MC = resampled 4-week blocks; history = every weekday start. No guard; margin not modelled. In-sample, NOT a forecast.", '']
    for k in hz:
        md += [f'## {k}', '', '| Portfolio | Sizing | P&L mean (MC / hist) | Median | p10 – p90 | Per week (mean) | Per day (mean) | Losing paths | Fell below $500 | Bust closed – stop-marked | Closed DD median / p90 / worst | Stop-marked DD p90 | Worst day p5 | Trades (/month, /day) | Win rate / PF | Avg risk |',
               '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for v in out['results'].values():
            m, h = v[f'mc {k}'], v[f'hist {k}']
            md.append(f"| {v['portfolio']} | {v['case']} | {usd(m['pnl_mean'])} / {usd(h['pnl_mean'])} | {usd(m['pnl_median'])} | {usd(m['pnl_p10'])} – {usd(m['pnl_p90'])} | {usd(m['week_mean'])} | "
                      f"{usd(m['day_mean'])} | {pct(m['loss_share'])} | {pct(m['below_500'])} | {pct(m['bust_closed'])} – {pct(m['bust'])} | {usd(m['dd_closed_median'])} / {usd(m['dd_closed_p90'])} / {usd(m['dd_closed_max'])} | "
                      f"{usd(m['dd_stop_p90'])} | {usd(m['worst_day_p5'])} | {m['trades']} ({m['trades_month']}, {m['trades_day']}) | {pct(m['win_rate'])} / {m['pf']} | {usd(m['avg_risk'])} |")
        md.append('')
    md += ['## 1 month by market period (MC)', '', '| Portfolio | Sizing | Dev 2021-23 mean / median | Validation 2023-24 | OOS 2024-26 |', '|---|---|---:|---:|---:|']
    for v in out['results'].values():
        cells = [f"{usd(v[f'mc 1 month {s}']['pnl_mean'])} / {usd(v[f'mc 1 month {s}']['pnl_median'])}" for s in ('dev', 'val', 'oos')]
        md.append(f"| {v['portfolio']} | {v['case']} | " + ' | '.join(cells) + ' |')
    (R / 'LIVE_1K.md').write_text('\n'.join(md) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
