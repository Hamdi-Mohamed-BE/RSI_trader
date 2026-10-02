"""Shared closed-trade metrics (site definitions). Used for ranking, reporting and the PROP objective."""
from datetime import datetime, timezone
import math
import numpy as np
import pandas as pd

DEPOSIT = 10_000.0


def ts(d):
    return datetime.strptime(d, '%Y.%m.%d').replace(tzinfo=timezone.utc)


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
    avg = lambda v: round(float(np.mean(v)), 2) if v else None  # noqa: E731
    return avg(runs[True]), avg(runs[False]), max(runs[True], default=0), max(runs[False], default=0)


def stats(trades, start, end, start_balance=DEPOSIT, equity_dd=None):
    """trades: DataFrame with close_epoch, position_id, net_profit, actual_risk, side, swap, commission, module."""
    s, e = ts(start), ts(end)
    d = trades[(trades.close_epoch >= s.timestamp()) & (trades.close_epoch < e.timestamp())] if len(trades) else trades
    d = d.sort_values(['close_epoch', 'position_id']) if len(d) else d
    p = d.net_profit.to_numpy(dtype=float) if len(d) else np.array([])
    days = (e - s).days
    weekdays = int(np.busday_count(s.date(), e.date()))
    gp, gl = p[p > 0].sum(), -p[p < 0].sum()
    bal = start_balance + np.cumsum(p)
    peak = np.maximum.accumulate(np.concatenate([[start_balance], bal]))
    bdd = float(((peak[1:] - bal) / peak[1:]).max() * 100) if len(p) else 0.0
    idx = pd.date_range(s.date(), e.date(), freq='D', inclusive='left')
    daily = pd.Series(0.0, index=idx)
    if len(p):
        day = pd.to_datetime(d.close_epoch, unit='s').dt.normalize()
        daily = daily.add(pd.Series(p, index=day.values).groupby(level=0).sum(), fill_value=0.0).reindex(idx, fill_value=0.0)
    eq = start_balance + daily.cumsum()
    r = daily / eq.shift(1).fillna(start_balance)
    sd = r.std(ddof=0)
    sharpe = float(r.mean() / sd * math.sqrt(365)) if len(p) >= 10 and sd > 0 else None
    months = pd.period_range(s.replace(tzinfo=None), (e - pd.Timedelta(seconds=1)).replace(tzinfo=None), freq='M')
    if len(p):
        by_month = pd.Series(p, index=pd.to_datetime(d.close_epoch, unit='s').dt.to_period('M').values).groupby(level=0).sum()
    else:
        by_month = pd.Series(dtype=float)
    consistency = float((by_month.reindex(months, fill_value=0) > 0).mean() * 100) if len(months) else None
    aw, al, mw, ml = streaks(p)
    R = (d.net_profit / d.actual_risk).to_numpy() if len(p) else np.array([])
    return dict(trades=int(len(p)), trades_per_month=round(len(p) / (days / 30.4375), 2), trades_per_day=round(len(p) / max(weekdays, 1), 3),
                return_pct=round(float(p.sum() / start_balance * 100), 2), net=round(float(p.sum()), 2),
                pf=round(float(gp / gl), 3) if gl else (99.0 if gp > 0 else None), win_pct=round(float((p > 0).mean() * 100), 1) if len(p) else None,
                consistency_pct=round(consistency, 1) if consistency is not None else None,
                avg_win_streak=aw, avg_loss_streak=al, max_win_streak=mw, max_loss_streak=ml,
                sharpe=round(sharpe, 2) if sharpe is not None else None, balance_dd_pct=round(bdd, 2),
                equity_dd_pct=None if equity_dd is None else round(float(equity_dd), 2), mean_R=round(float(R.mean()), 3) if len(R) else None,
                long_trades=int((d.side > 0).sum()) if len(p) else 0, short_trades=int((d.side < 0).sum()) if len(p) else 0,
                swap=round(float(d.swap.sum()), 2) if len(p) else 0.0, commission=round(float(d.commission.sum()), 2) if len(p) else 0.0)
