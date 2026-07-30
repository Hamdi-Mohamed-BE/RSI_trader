from __future__ import annotations

from dataclasses import asdict
import math
from typing import Iterable

import numpy as np
import pandas as pd

from .models import Skip, Trade


TRADE_COLUMNS = [
    "strategy", "side", "entry_time", "entry", "stop", "target", "volume",
    "risk_cash", "exit_time", "exit", "pnl", "exit_reason", "spread_cost",
    "slippage_cost", "mae", "mfe", "holding_minutes", "metadata",
]


def trades_frame(trades: Iterable[Trade]) -> pd.DataFrame:
    records = []
    for t in trades:
        row = asdict(t)
        row["holding_minutes"] = t.holding_minutes
        records.append(row)
    return pd.DataFrame(records, columns=TRADE_COLUMNS)


def skips_frame(skips: Iterable[Skip]) -> pd.DataFrame:
    return pd.DataFrame([asdict(s) for s in skips], columns=["date", "strategy", "reason"])


def _streak(values: list[bool], wanted: bool) -> int:
    best = current = 0
    for value in values:
        current = current + 1 if value is wanted else 0
        best = max(best, current)
    return best


def metrics(df: pd.DataFrame, starting_balance: float) -> dict[str, float | int | str]:
    if df.empty:
        return {
            "starting_balance": starting_balance, "ending_balance": starting_balance,
            "net_profit": 0.0, "gross_profit": 0.0, "gross_loss": 0.0,
            "profit_factor": 0.0, "win_rate": 0.0, "trades": 0,
            "max_balance_dd": 0.0, "max_equity_dd": 0.0, "max_dd_pct": 0.0,
        }
    ordered = df.sort_values("exit_time").copy()
    pnl = ordered["pnl"].astype(float)
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gp = float(wins.sum())
    gl = float(losses.sum())
    pf: float | str = gp / abs(gl) if gl < 0 else ("inf" if gp > 0 else 0.0)
    equity = starting_balance + pnl.cumsum()
    peaks = np.maximum.accumulate(np.r_[starting_balance, equity.values])
    eqv = np.r_[starting_balance, equity.values]
    dd = peaks - eqv
    dd_pct = np.divide(dd, peaks, out=np.zeros_like(dd), where=peaks != 0) * 100
    returns = pnl / np.maximum(starting_balance, equity.shift(1).fillna(starting_balance))
    downside = returns[returns < 0]
    sharpe = float(returns.mean() / returns.std(ddof=1) * math.sqrt(252)) if len(returns) > 2 and returns.std(ddof=1) else 0.0
    sortino = float(returns.mean() / downside.std(ddof=1) * math.sqrt(252)) if len(downside) > 1 and downside.std(ddof=1) else 0.0
    bools = (pnl > 0).tolist()
    achieved_rr = float((wins.mean() / abs(losses.mean()))) if len(wins) and len(losses) else 0.0
    max_dd = float(dd.max())
    net = float(pnl.sum())
    return {
        "starting_balance": starting_balance,
        "ending_balance": float(equity.iloc[-1]),
        "net_profit": net,
        "gross_profit": gp,
        "gross_loss": gl,
        "profit_factor": pf,
        "win_rate": float((pnl > 0).mean() * 100),
        "max_balance_dd": max_dd,
        "max_equity_dd": max_dd,
        "max_dd_pct": float(dd_pct.max()),
        "average_win": float(wins.mean()) if len(wins) else 0.0,
        "average_loss": float(losses.mean()) if len(losses) else 0.0,
        "achieved_reward_risk": achieved_rr,
        "expected_payoff": float(pnl.mean()),
        "trades": int(len(df)),
        "longest_win_streak": _streak(bools, True),
        "longest_loss_streak": _streak(bools, False),
        "largest_win": float(pnl.max()),
        "largest_loss": float(pnl.min()),
        "recovery_factor": net / max_dd if max_dd else 0.0,
        "sharpe": sharpe,
        "sortino": sortino,
        "average_holding_minutes": float(df["holding_minutes"].mean()),
        "spread_cost": float(df["spread_cost"].sum()),
        "slippage_cost": float(df["slippage_cost"].sum()),
    }


def monthly(df: pd.DataFrame, starting_balance: float) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    data = df.copy()
    data["exit_time"] = pd.to_datetime(data["exit_time"], utc=True)
    data["month"] = data["exit_time"].dt.strftime("%Y-%m")
    rows = []
    balance = starting_balance
    for month, group in data.groupby("month", sort=True):
        m = metrics(group, balance)
        wins = int((group["pnl"] > 0).sum())
        losses = int((group["pnl"] < 0).sum())
        rows.append(
            {
                "Month": month,
                "Trades": len(group),
                "Wins": wins,
                "Losses": losses,
                "Win Rate": m["win_rate"],
                "Gross Profit": m["gross_profit"],
                "Gross Loss": m["gross_loss"],
                "Net Profit": m["net_profit"],
                "Profit Factor": m["profit_factor"],
                "Max DD": m["max_balance_dd"],
                "Return %": float(m["net_profit"]) / balance * 100 if balance else 0,
            }
        )
        balance += float(m["net_profit"])
    return pd.DataFrame(rows)
