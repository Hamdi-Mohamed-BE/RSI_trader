"""Item 4a: per-EA kill-switch thresholds from a day-block bootstrap of each EA's cached native evidence.

Thresholds are in R (one planned initial-stop risk). They are what the owner pre-commits to BEFORE live trading:
- WATCH  = 95th percentile of the bootstrapped 63-trading-day (≈3-month) drawdown / losing streak;
- KILL   = the larger of the 99th percentile and the worst value actually seen in any 63-trading-day window of the
           evidence (streak: worst ever), so an EA is never switched off for something its own history already contained.
The live monitor compares rolling live R against them. A KILL flag recommends switching the EA off; the owner decides.

uv run python ".../_Ops Monitor/kill_switch.py"   ->  output/KILL_SWITCHES.json + .md
"""
from datetime import date, timedelta

from common import OUT, day_block_bootstrap, evidence_trades, now_utc, products, roster, save
from robustness import longest_losing_streak, max_drawdown

PATHS, BLOCK, SEED = 10000, 5, 20261020
HORIZONS = {'1m': 21, '3m': 63}


def calendar(first: str, last: str, weekends: bool) -> list[str]:
    d, end, out = date.fromisoformat(first[:10]), date.fromisoformat(last[:10]), []
    while d <= end:
        if weekends or d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def main():
    phases = roster(); rows = []
    for slug, p in products().items():
        trades, meta, mode = [], None, None
        for period in ('5y', '3y', '1y'):
            trades, meta, mode = evidence_trades(slug, period)
            if len([t for t in trades if t.get('estimated_r') is not None]) >= 30:
                break
        rt = [t for t in trades if t.get('estimated_r') is not None]
        row = dict(slug=slug, label=p.label, phase=phases.get(slug, '-'), mode=mode, evidence_period=(meta or {}).get('period'),
                   evidence_window=period, trades=len(rt))
        if len(rt) < 30:
            row.update(status='INSUFFICIENT_EVIDENCE', note='fewer than 30 R-measured trades in the cache; no threshold set')
            rows.append(row); continue
        rt.sort(key=lambda t: t['close_time'])
        crypto = p.canonical.upper().startswith(('BTC', 'ETH'))
        cal = calendar(rt[0]['close_time'], rt[-1]['close_time'], crypto)
        rs = [float(t['estimated_r']) for t in rt]
        hist_streak = longest_losing_streak(rs)
        # like-for-like with the 63-day bootstrap: worst drawdown inside any 63-calendar-trading-day window of history
        by_day = {}
        for t in rt:
            by_day.setdefault(t['close_time'][:10], []).append(float(t['estimated_r']))
        hist_dd = max(max_drawdown([v for d in cal[i:i + HORIZONS['3m']] for v in by_day.get(d, [])])
                      for i in range(max(1, len(cal) - HORIZONS['3m'] + 1)))
        full_dd = max_drawdown(rs)
        boot = {k: day_block_bootstrap(rt, h, value='estimated_r', paths=PATHS, block_days=BLOCK, seed=SEED, calendar_days=cal)
                for k, h in HORIZONS.items()}
        b3 = boot['3m']
        row.update(status='SET', trades_per_month=round(len(rt) / max(1, len(cal)) * (30.4375 if crypto else 21.74), 2),
                   history_max_dd_r=round(hist_dd, 2), history_full_window_max_dd_r=round(full_dd, 2), history_longest_losing_streak=hist_streak,
                   watch=dict(drawdown_r=b3['max_drawdown']['p95'], losing_streak=b3['losing_streak']['p95'], worst_day_r=b3['worst_day']['p05']),
                   kill=dict(drawdown_r=round(max(b3['max_drawdown']['p99'], hist_dd), 2),
                             losing_streak=max(int(b3['losing_streak']['p99']), hist_streak),
                             worst_day_r=round(min(b3['worst_day']['p01'], min(rs)), 2)),
                   bootstrap=boot, r_is_estimate=True)
        rows.append(row)
    save('KILL_SWITCHES.json', dict(generated_utc=now_utc().isoformat(), method=__doc__.strip(), paths=PATHS, block_days=BLOCK, seed=SEED, rows=rows))
    order = {'live': 0, 'paused': 1, 'review': 2}
    md = ['# Per-EA kill-switch thresholds', '', f'Generated {now_utc():%Y-%m-%d %H:%M} UTC. Method: day-block bootstrap ({PATHS:,} paths, '
          f'{BLOCK}-day blocks, seed {SEED}) of each EA\'s cached native trades in R (estimated from planned initial-stop risk). '
          'WATCH = 95th percentile of the ≈3-month (63 trading days) drawdown / losing streak; KILL = max(99th percentile, worst seen in '
          'any 63-trading-day window of the evidence; streak: worst ever). Full-window max DD is in the JSON. Multiply R by the live risk % to get account %: at 1% risk, 10R ≈ 10% of balance.', '',
          'These are pre-commitments, not forecasts: a KILL flag recommends switching the EA off and reviewing it; the owner decides.', '',
          '| Phase | EA | Evidence | Trades | /month | Hist worst 3-month DD R | Hist max losing streak | WATCH DD R | KILL DD R | WATCH streak | KILL streak | KILL worst day R |',
          '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in sorted(rows, key=lambda r: (order.get(r['phase'], 3), r['label'])):
        if r['status'] != 'SET':
            md.append(f"| {r['phase']} | {r['label']} | {r.get('evidence_window') or '—'} | {r['trades']} | — | — | — | — | — | — | — | — |"); continue
        md.append(f"| {r['phase']} | {r['label']} | {r['evidence_window']} | {r['trades']} | {r['trades_per_month']} | {r['history_max_dd_r']} | "
                  f"{r['history_longest_losing_streak']} | {r['watch']['drawdown_r']} | **{r['kill']['drawdown_r']}** | {r['watch']['losing_streak']:g} | "
                  f"**{r['kill']['losing_streak']}** | {r['kill']['worst_day_r']} |")
    missing = [r['label'] for r in rows if r['status'] != 'SET']
    md += ['', f"No threshold (under 30 R-measured trades or no cache): {', '.join(missing) or 'none'}."]
    (OUT / 'KILL_SWITCHES.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print(f"{sum(r['status'] == 'SET' for r in rows)} thresholds set; missing: {missing}")


if __name__ == '__main__':
    main()
