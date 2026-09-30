"""Metrics, gate and balance graph for the Gold Trio raw study (reads native/*/run.json + trades/trace CSVs).

Definitions (stated once in REPORT.md):
- Trades/month = trades / (calendar days / 30.4375); trades/day = trades / weekdays in the window.
- Consistency = share of calendar months with positive net P/L (months with no trade count as not positive).
- Sharpe = site definition: mean / population stdev of daily closed-trade returns on the running closed balance,
  every calendar day counted, x sqrt(365), no risk-free rate.
- Balance DD = peak-to-trough of the closed-trade balance. Equity DD = the native MT5 report's relative equity DD
  (floating P/L included); it is only available for the whole run, not for a split/slice.
"""
from pathlib import Path
import gzip, json, math
from datetime import datetime, timezone
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / 'run-config.json').read_text())
DEPOSIT = CFG['deposit']


def load(tag):
    run = json.loads((ROOT / 'native' / tag / 'run.json').read_text())
    trades = pd.read_csv(ROOT / 'native' / tag / 'trades.csv.gz')
    trace = pd.read_csv(ROOT / 'native' / tag / 'trace.csv.gz')
    return run, trades, trace


def streaks(pnl):
    runs = {True: [], False: []}
    cur, n = None, 0
    for x in pnl:
        if x == 0:
            if cur is not None:
                runs[cur].append(n)
            cur, n = None, 0
            continue
        s = x > 0
        if s == cur:
            n += 1
        else:
            if cur is not None:
                runs[cur].append(n)
            cur, n = s, 1
    if cur is not None:
        runs[cur].append(n)
    avg = lambda v: round(float(np.mean(v)), 2) if v else None
    return avg(runs[True]), avg(runs[False]), max(runs[True], default=0), max(runs[False], default=0)


def metrics(trades, start, end, start_balance=DEPOSIT, equity_dd=None):
    """Closed-trade metrics for trades closing in [start, end); start_balance is the balance at `start`."""
    t0, t1 = start.timestamp(), end.timestamp()
    d = trades[(trades.close_epoch >= t0) & (trades.close_epoch < t1)].sort_values(['close_epoch', 'position_id'])
    p = d.net_profit.to_numpy()
    days = (end - start).days
    weekdays = int(np.busday_count(start.date(), end.date()))
    gp, gl = p[p > 0].sum(), -p[p < 0].sum()
    bal = start_balance + np.cumsum(p)
    peak = np.maximum.accumulate(np.concatenate([[start_balance], bal]))
    bdd = float(((peak[1:] - bal) / peak[1:]).max() * 100) if len(p) else 0.0
    # daily returns on the running closed balance, every calendar day
    idx = pd.date_range(start.date(), end.date(), freq='D', inclusive='left')
    daily = pd.Series(0.0, index=idx)
    if len(p):
        day = pd.to_datetime(d.close_epoch, unit='s').dt.normalize()
        daily = daily.add(pd.Series(p, index=day.values).groupby(level=0).sum(), fill_value=0.0).reindex(idx, fill_value=0.0)
    eq = start_balance + daily.cumsum()
    prev = eq.shift(1).fillna(start_balance)
    r = daily / prev
    sharpe = float(r.mean() / r.std(ddof=0) * math.sqrt(365)) if len(p) >= 10 and r.std(ddof=0) > 0 else None
    months = pd.period_range(start, end - pd.Timedelta(seconds=1), freq='M')
    by_month = pd.Series(p, index=pd.to_datetime(d.close_epoch, unit='s').dt.to_period('M').values).groupby(level=0).sum() if len(p) else pd.Series(dtype=float)
    consistency = float((by_month.reindex(months, fill_value=0) > 0).mean() * 100) if len(months) else None
    aw, al, mw, ml = streaks(p)
    R = (d.net_profit / d.actual_risk).to_numpy() if len(p) else np.array([])
    return dict(trades=int(len(p)), trades_per_month=round(len(p) / (days / 30.4375), 2), trades_per_day=round(len(p) / weekdays, 3),
                return_pct=round(float(p.sum() / start_balance * 100), 2), net=round(float(p.sum()), 2),
                pf=round(float(gp / gl), 3) if gl else None, win_pct=round(float((p > 0).mean() * 100), 1) if len(p) else None,
                consistency_pct=round(consistency, 1) if consistency is not None else None,
                avg_win_streak=aw, avg_loss_streak=al, max_win_streak=mw, max_loss_streak=ml,
                sharpe=round(sharpe, 2) if sharpe is not None else None, balance_dd_pct=round(bdd, 2),
                equity_dd_pct=equity_dd, mean_R=round(float(R.mean()), 3) if len(R) else None,
                long_trades=int((d.side > 0).sum()), short_trades=int((d.side < 0).sum()),
                long_net=round(float(d[d.side > 0].net_profit.sum()), 2), short_net=round(float(d[d.side < 0].net_profit.sum()), 2),
                swap=round(float(d.swap.sum()), 2), commission=round(float(d.commission.sum()), 2))


def window(run):
    s = datetime.strptime(run['start'], '%Y.%m.%d').replace(tzinfo=timezone.utc)
    e = datetime.strptime(run['end'], '%Y.%m.%d').replace(tzinfo=timezone.utc)
    return s, e


def summarise(tag):
    run, trades, trace = load(tag)
    s, e = window(run)
    full = metrics(trades, s, e, equity_dd=run['metrics'].get('equity_dd_pct'))
    last_start = e.replace(year=e.year - 1)
    before = trades[trades.close_epoch < last_start.timestamp()].net_profit.sum()
    last = metrics(trades, last_start, e, start_balance=DEPOSIT + before)
    modules = {m: metrics(trades[trades.module == m], s, e) for m in sorted(trades.module.unique())} if trades.module.nunique() > 1 else {}
    return dict(tag=tag, spec=run['spec'], flags=run['flags'], summaries=run['summaries'], full=full, last_12m=last, modules=modules,
                native_net=run['metrics']['net_profit'])


def gate(rows):
    by = {r['spec']['name']: r for r in rows}
    out = {}
    for name, ctrl in [('A-momentum', 'A-momentum-control'), ('B-breakout', 'B-breakout-control'), ('BQ4-breakout-q4', 'B-breakout-control'),
                       ('C-turn-of-month', 'C-turn-of-month-control')]:
        if name not in by or ctrl not in by:
            continue
        f, c = by[name]['full'], by[ctrl]['full']
        checks = dict(positive=f['net'] > 0, pf=(f['pf'] or 0) >= CFG['raw_gate']['pf'], trades=f['trades'] >= CFG['raw_gate']['min_trades'],
                      beats_control=(f['mean_R'] or -9) > (c['mean_R'] or -9), clean_execution=not any(by[name]['flags'].values()))
        out[name] = dict(passed=all(checks.values()), checks=checks, control=ctrl, mean_R=f['mean_R'], control_mean_R=c['mean_R'])
    return out


def graph(rows, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, figsize=(12, 9), sharex=True, gridspec_kw=dict(height_ratios=[3, 2]))
    ax = axes[0]
    for name in ['video-A+B+C', 'video-A+BQ4+C', 'website-A+D+B']:
        tag = f'{name}-3y-m{CFG["model"]}'
        if not (ROOT / 'native' / tag / 'run.json').exists():
            continue
        _, trades, trace = load(tag)
        t = pd.to_datetime(trace.time, unit='s')
        line = ax.plot(t, trace.balance, lw=1.6, label=f'{name} balance')[0]
        ax.plot(t, trace.equity, lw=.6, alpha=.45, color=line.get_color())
    ax.axhline(DEPOSIT, color='grey', lw=.7, ls='--')
    ax.set_ylabel('USD (thin line = equity)')
    ax.set_title('XAUUSD Gold Trio raw reproduction · native MT5 Model 4 · 3 years · 1% risk per module')
    ax.legend(loc='upper left', fontsize=8)
    ax = axes[1]
    for name in ['A-momentum', 'B-breakout', 'BQ4-breakout-q4', 'C-turn-of-month', 'D-ma-trend']:
        tag = f'{name}-3y-m{CFG["model"]}'
        if not (ROOT / 'native' / tag / 'run.json').exists():
            continue
        _, trades, _ = load(tag)
        d = trades.sort_values('close_epoch')
        ax.step(pd.to_datetime(d.close_epoch, unit='s'), DEPOSIT + d.net_profit.cumsum(), where='post', lw=1.2, label=name)
    ax.axhline(DEPOSIT, color='grey', lw=.7, ls='--')
    ax.set_ylabel('Closed balance, single module (USD)')
    ax.legend(loc='upper left', fontsize=8, ncol=3)
    fig.tight_layout()
    fig.savefig(path, dpi=130)


def main():
    rows = []
    for c in CFG['cases']:
        tag = f"{c['name']}-3y-m{CFG['model']}"
        if (ROOT / 'native' / tag / 'run.json').exists():
            rows.append(summarise(tag))
    result = dict(generated_at=datetime.now().isoformat(timespec='seconds'), rows=rows, gate=gate(rows))
    (ROOT / 'RESULTS.json').write_text(json.dumps(result, indent=2, default=str), encoding='utf-8')
    graph(rows, ROOT / 'balance.png')
    cols = ['trades', 'trades_per_month', 'trades_per_day', 'return_pct', 'pf', 'win_pct', 'consistency_pct', 'avg_win_streak', 'avg_loss_streak',
            'max_win_streak', 'max_loss_streak', 'sharpe', 'balance_dd_pct', 'equity_dd_pct', 'mean_R']
    for part in ['full', 'last_12m']:
        print(f'\n== {part}')
        print(pd.DataFrame([{**{'case': r['spec']['name']}, **{k: r[part][k] for k in cols}} for r in rows]).to_string(index=False))
    print(json.dumps(result['gate'], indent=1))


if __name__ == '__main__':
    main()
