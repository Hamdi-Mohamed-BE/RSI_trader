"""Offline evidence only; does not connect to MT5 or choose parameters."""
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import gzip, hashlib, json, math, re
import numpy as np
import pandas as pd

R = Path(__file__).resolve().parent
C = json.loads((R / 'config.json').read_text(encoding='utf-8'))
RESULTS = json.loads((R / 'RESULTS.json').read_text(encoding='utf-8'))
CALENDAR = json.loads((R / 'calendar.json').read_text(encoding='utf-8'))
NY = ZoneInfo('America/New_York')

def save(name, value):
    (R / name).write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def csv(row, suffix):
    return pd.read_csv(R / 'native' / row['stage'] / f"{row['index']}-{suffix}.csv.gz")

def stamp(epoch, ny=False):
    d = datetime.fromtimestamp(int(epoch), timezone.utc)
    return d.astimezone(NY).isoformat() if ny else d.isoformat()

def pf(values):
    loss = -sum(min(float(v), 0) for v in values)
    return sum(max(float(v), 0) for v in values) / loss if loss else None

def streaks(values):
    w = l = mw = ml = 0
    for v in values:
        w = w + 1 if v > 0 else 0
        l = l + 1 if v < 0 else 0
        mw, ml = max(mw, w), max(ml, l)
    return mw, ml

def wilson(wins, n):
    z = 1.959963984540054
    p = wins / n
    denominator = 1 + z*z/n
    centre = (p + z*z/(2*n)) / denominator
    width = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denominator
    return [100*(centre-width), 100*(centre+width)]

def group_stats(trades):
    values = [t['net_profit'] for t in trades]
    n = len(values)
    return dict(trades=n, net_usd=sum(values), pf=pf(values),
                win_rate_pct=sum(v > 0 for v in values)/n*100 if n else None,
                contribution_to_starting_balance_pct=sum(values)/100)

def daily_curve(row):
    df = csv(row, 'equity')
    assert df.epoch.is_monotonic_increasing
    df['day'] = pd.to_datetime(df.epoch, unit='s').dt.normalize()
    last = pd.Timestamp(row['native']['last_quote_epoch'], unit='s').normalize()
    days = pd.date_range(C['start'], last)
    end = df.groupby('day')[['balance', 'equity']].last().reindex(days).ffill().fillna(C['deposit'])
    ret = end.equity.pct_change().fillna(end.equity.iloc[0]/C['deposit']-1)
    sd = ret.std(ddof=1)
    sharpe = float(ret.mean()/sd*math.sqrt(365)) if sd > 0 else 0.0
    return end, sharpe

def enrich(row):
    dec = csv(row, 'decisions')
    entries = dec[dec.reason.str.startswith('entry_', na=False) & (dec.reason != 'entry_window_expired')]
    entries = entries[entries.reason.isin(['entry_displacement', 'entry_structure'])]
    trades = []
    for original in row['trades']:
        t = dict(original)
        match = entries[(entries.epoch-t['open_epoch']).abs() <= 1]
        assert len(match) == 1, ('Unmatched fill', row['stage'], t['position_id'])
        d = match.iloc[0]
        t.update(event_index=int(d.event_index), event=d.kind,
                 event_epoch=int(d.event_epoch), event_time_ny=stamp(d.event_epoch, True),
                 open_time_ny=stamp(t['open_epoch'], True), close_time_ny=stamp(t['close_epoch'], True),
                 signal=d.reason.removeprefix('entry_'), signal_bar_epoch=int(d.bar_epoch),
                 risk_budget_usd=float(d.risk_budget), risk_per_lot_usd=float(d.unit_loss),
                 intended_stop_risk_usd=float(d.lots*d.unit_loss),
                 pre_news_atr=float(d.pre_atr), fair_price=float(d.fair),
                 hold_minutes=(t['close_epoch']-t['open_epoch'])/60,
                 exit_label={3:'Time close', 4:'Stop loss', 5:'Target'}.get(t['exit_reason'], str(t['exit_reason'])),
                 realised_r=t['net_profit']/float(d.risk_budget),
                 fill_to_target_rr=abs(t['initial_tp']-t['open_price'])/abs(t['initial_sl']-t['open_price']))
        trades.append(t)
    assert len(entries) == len(trades)
    return trades, dec

def coverage(row):
    journal = gzip.decompress((R/'native'/row['stage']/'journal.txt.gz').read_bytes()).decode()
    symbol = row['stage'].removeprefix('raw-')
    starts = sorted(set(re.findall(re.escape(symbol)+r': ticks data begins from ([0-9.]+ [0-9:]+)', journal)))
    q = csv(row, 'quotes')
    entryq = q[q.entry == 0]
    q2026 = entryq[entryq.epoch >= pd.Timestamp('2026-01-01').timestamp()]
    good = q2026[(q2026.volume > 0) & (q2026.spread_cash >= 0)]
    median = float((good.spread_cash/good.volume).median()) if len(good) else None
    return dict(requested_start=C['start'], requested_end_exclusive=C['end_exclusive'],
                last_quote_utc=stamp(row['native']['last_quote_epoch']),
                real_tick_archive_starts=starts, generated_ticks_before_2026=True,
                model=4, history_quality_percentage='Not available in native fixed-case XML export',
                entry_quotes_2026=len(q2026), zero_spread_entry_quotes_2026=int((q2026.ask == q2026.bid).sum()),
                median_entry_spread_usd_per_lot_2026=median,
                all_2026_entry_quotes_zero_spread=bool(len(q2026) and (q2026.ask == q2026.bid).all()),
                failed_entries=int(row['native']['failed_entries']),
                failed_time_close_requests=int(row['native']['failed_updates']),
                open_positions_at_end=int(row['native']['open_position']),
                events_started=int(row['native']['events_seen']),
                limitations='Model 4 uses available real ticks, with generated fallback before the archive. Zero-spread news quotes are not reliable executable cost evidence. No 100% tick-quality or live replication claim.')

def analyse(key, row):
    trades, dec = enrich(row)
    daily, sharpe = daily_curve(row)
    p = [t['net_profit'] for t in trades]
    n = len(trades)
    wins = [v for v in p if v > 0]
    losses = [v for v in p if v < 0]
    mw, ml = streaks(p)
    metric = dict(trades=n, net_usd=sum(p), return_pct=sum(p)/100, pf=pf(p),
                  win_rate_pct=len(wins)/n*100, win_rate_wilson95_pct=wilson(len(wins), n),
                  max_floating_dd_pct=row['native']['equity_dd'],
                  max_balance_dd_pct=row['native']['balance_dd'], daily_equity_sharpe=sharpe,
                  sharpe_method='UTC calendar-day end equity returns, actual coverage only, sqrt(365), zero risk-free rate; not MT5 trade-level Sharpe',
                  win_streak=mw, loss_streak=ml, average_win_usd=sum(wins)/len(wins) if wins else None,
                  average_loss_usd=sum(losses)/len(losses) if losses else None,
                  mean_hold_minutes=float(np.mean([t['hold_minutes'] for t in trades])),
                  maximum_hold_minutes=max(t['hold_minutes'] for t in trades),
                  stop_losses_exceeding_budget=sum(-t['net_profit'] > t['risk_budget_usd']+.01 for t in trades if t['exit_reason']==4),
                  research_only=True, promoted_live=False)
    event_groups = {kind:group_stats([t for t in trades if t['event']==kind]) for kind in C['event_types']}
    period_groups = {}
    actual_end = pd.Timestamp(row['native']['last_quote_epoch'], unit='s').normalize() + pd.Timedelta(days=1)
    for label, months in [('Last 3 months', 3), ('Last 6 months', 6)]:
        start = actual_end-pd.DateOffset(months=months)
        ts = [t for t in trades if t['open_epoch'] >= start.timestamp()]
        period_groups[label] = dict(start=start.date().isoformat(), end_exclusive=actual_end.date().isoformat(), **group_stats(ts))
    for year in [2025,2026]:
        period_groups[str(year)] = group_stats([t for t in trades if datetime.fromtimestamp(t['open_epoch'],timezone.utc).year==year])
    stress = []
    for extra_r in [0.025, 0.05, 0.10, 0.20]:
        cash = [t['net_profit']-extra_r*t['risk_budget_usd'] for t in trades]
        stress.append(dict(extra_cost_r_per_trade=extra_r, net_usd=sum(cash), return_pct=sum(cash)/100,
                           pf=pf(cash), win_rate_pct=sum(v>0 for v in cash)/n*100,
                           scope='Hypothetical additional execution cost in fractions of the intended cash-risk budget. Ledger-only subtraction, frozen lots. Not a widened-spread tick rerun or an estimate of actual news slippage.'))
    event_rows = []
    for i,event in enumerate(CALENDAR['events']):
        logs = dec[dec.event_index==i]
        ts = [t for t in trades if t['event_index']==i]
        if ts:
            reason = 'Traded: '+ts[0]['signal']
        else:
            meaningful = logs[~logs.reason.isin(['event_start','event_end','impulse_confirmed','pivot_confirmed'])]
            reason = meaningful.iloc[-1].reason if len(meaningful) else 'no qualifying reversal signal'
        event_rows.append(dict(index=i, event=event['kind'], release_ny=event['release_ny'],
                               release_utc=event['release_utc'], disposition=reason,
                               trades=len(ts), net_usd=sum(t['net_profit'] for t in ts)))
    return dict(name=key, metrics=metric, event_groups=event_groups, period_groups=period_groups,
                quality=coverage(row), cost_sensitivity=stress, trades=trades, events=event_rows,
                daily_curve=[dict(date=d.date().isoformat(), balance=float(v.balance), equity=float(v.equity)) for d,v in daily.iterrows()])

def build_summary():
    summary = {key:analyse(key,row) for key,row in RESULTS.items()}
    save('SUMMARY.json', summary)
    return summary

if __name__ == '__main__':
    s = build_summary()
    print(json.dumps({k:v['metrics'] for k,v in s.items()}, indent=2))
