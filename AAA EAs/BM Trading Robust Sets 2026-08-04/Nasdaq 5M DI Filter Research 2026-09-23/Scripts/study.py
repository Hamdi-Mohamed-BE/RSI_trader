import json
import numpy as np
import pandas as pd

HOLDOUT_START = pd.Timestamp("2026-05-01")


def stats(tr: pd.DataFrame, start=10000.0):
    """Compound each trade's native per-trade equity return (1% risk basis)."""
    tr = tr.sort_values("entry_time")
    eq = start
    pnl = []
    curve = [start]
    for rf in tr.return_fraction:
        p = eq * rf
        pnl.append(p)
        eq += p
        curve.append(eq)
    pnl = np.array(pnl)
    curve = np.array(curve)
    peak = np.maximum.accumulate(curve)
    dd = ((peak - curve) / peak).max() * 100 if len(curve) else 0
    wins = pnl > 0
    def streak(mask):
        best = cur = 0
        for m in mask:
            cur = cur + 1 if m else 0
            best = max(best, cur)
        return best
    gp, gl = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    return {
        "trades": int(len(pnl)),
        "wins": int(wins.sum()),
        "losses": int((pnl < 0).sum()),
        "win_rate_pct": round(100 * wins.mean(), 2) if len(pnl) else 0,
        "profit_factor": round(gp / gl, 3) if gl > 0 else float("inf"),
        "return_pct": round((eq / start - 1) * 100, 2),
        "net_usd": round(eq - start, 2),
        "max_closed_dd_pct": round(dd, 2),
        "max_win_streak": streak(pnl > 0),
        "max_loss_streak": streak(pnl < 0),
        "avg_R": round(tr.R.mean(), 3) if len(pnl) else 0,
        "sum_R": round(tr.R.sum(), 2),
        "avg_win_R": round(tr.R[tr.R > 0].mean(), 3),
        "avg_loss_R": round(tr.R[tr.R < 0].mean(), 3),
        "largest_win_usd": round(pnl.max(), 2),
        "largest_loss_usd": round(pnl.min(), 2),
        "long_trades": int((tr.dir > 0).sum()),
        "short_trades": int((tr.dir < 0).sum()),
    }


def candidates(t: pd.DataFrame):
    c = {}
    for tf in ("m5", "h1", "d1"):
        a, s, di = t[f"adx_{tf}"], t[f"adx_{tf}_slope3"], t[f"di_{tf}"]
        for k in (15, 20, 25, 30):
            c[f"ADX_{tf.upper()} >= {k}"] = a >= k
        c[f"ADX_{tf.upper()} rising (3 bars)"] = s > 0
        c[f"ADX_{tf.upper()} >= 20 and rising"] = (a >= 20) & (s > 0)
        c[f"DI_{tf.upper()} agrees with trade"] = di == t.dir
        c[f"DI_{tf.upper()} agrees and ADX >= 20"] = (di == t.dir) & (a >= 20)
    for tf in ("h1", "d1"):
        c[f"ADX_{tf.upper()} <= 25 (inverse check)"] = t[f"adx_{tf}"] <= 25
    return c
