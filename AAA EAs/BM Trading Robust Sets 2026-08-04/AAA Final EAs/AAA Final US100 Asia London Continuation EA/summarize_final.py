from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
RESEARCH = ROOT / "Research"
OUT = RESEARCH / "final-review"
OUT.mkdir(parents=True, exist_ok=True)


def metrics(frame: pd.DataFrame, slippage_each_side: float = 0.0) -> dict:
    stop_distance = (frame["entry"] - frame["initial_stop"]).abs()
    r = frame["result_r"].astype(float) - (2.0 * slippage_each_side / stop_distance)
    equity = 10_000.0 * (1.0 + 0.01 * r).cumprod()
    peak = equity.cummax()
    drawdown = (peak - equity) / peak
    gains = r[r > 0].sum()
    losses = -r[r < 0].sum()
    return {
        "trades": int(len(r)),
        "wins": int((r > 0).sum()),
        "losses": int((r <= 0).sum()),
        "win_rate_pct": float((r > 0).mean() * 100.0),
        "profit_factor": float(gains / losses) if losses else None,
        "mean_r": float(r.mean()),
        "net_r": float(r.sum()),
        "return_pct": float((equity.iloc[-1] / 10_000.0 - 1.0) * 100.0),
        "max_closed_balance_dd_pct": float(drawdown.max() * 100.0),
        "final_balance": float(equity.iloc[-1]),
    }


def direction_metrics(frame: pd.DataFrame) -> dict:
    return {side.lower(): metrics(part) for side, part in frame.groupby("side")}


def iid_bootstrap(frame: pd.DataFrame, seed: int = 84102026, samples: int = 50_000) -> dict:
    rng = np.random.default_rng(seed)
    r = frame["result_r"].to_numpy(dtype=float)
    sampled = rng.choice(r, size=(samples, len(r)), replace=True)
    returns = (np.prod(1.0 + sampled * 0.01, axis=1) - 1.0) * 100.0
    return {
        "method": "iid trade bootstrap; diagnostic only, not a forecast",
        "samples": samples,
        "probability_positive_pct": float((returns > 0).mean() * 100.0),
        "return_pct_p05": float(np.quantile(returns, 0.05)),
        "return_pct_median": float(np.quantile(returns, 0.50)),
        "return_pct_p95": float(np.quantile(returns, 0.95)),
    }


def load(relative: str) -> pd.DataFrame:
    frame = pd.read_csv(RESEARCH / relative)
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.sort_values("date").reset_index(drop=True)


exness = load("reports-exact-20-points/trades.csv")
mex = load("reports-cross-broker-mexatlantic/trades.csv")

summary = {
    "fixed_configuration": {
        "instrument": "US100 cash CFD",
        "threshold_index_points": 20.0,
        "threshold_broker_ticks_at_0_01": 2000,
        "signal": "Asia and London individually aligned; first New York M15 extreme within 20 points of the same-side Asia extreme",
        "entry": "New York opening-range breakout after 09:45, no later than 10:30 America/New_York",
        "stop": "max(1.25 x first New York M15 range, 20 index points)",
        "target_r": 2.0,
        "trailing": "none",
        "hard_exit": "16:00 America/New_York",
        "risk_pct_of_equity": 1.0,
    },
    "exness_ustec": {
        "period": f"{exness.date.min().date()} to {exness.date.max().date()}",
        "base": metrics(exness),
        "directions": direction_metrics(exness),
        "stress": {str(s): metrics(exness, s) for s in (0.5, 1.0, 2.0)},
        "bootstrap": iid_bootstrap(exness),
    },
    "mexatlantic_ut100": {
        "period": f"{mex.date.min().date()} to {mex.date.max().date()}",
        "base": metrics(mex),
        "directions": direction_metrics(mex),
        "stress": {str(s): metrics(mex, s) for s in (0.5, 1.0, 2.0)},
        "bootstrap": iid_bootstrap(mex, seed=84102027),
    },
}

(OUT / "results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

fig, ax = plt.subplots(figsize=(13, 7))
for name, frame, color in (
    ("Exness USTEC (2019-2026)", exness, "#00a6d6"),
    ("MEXAtlantic UT100 (2022-2026, unchanged settings)", mex, "#f19c2b"),
):
    eq = 10_000.0 * (1.0 + frame["result_r"].astype(float) * 0.01).cumprod()
    dates = pd.concat([pd.Series([frame.date.min()]), frame.date], ignore_index=True)
    values = np.concatenate(([10_000.0], eq.to_numpy()))
    ax.step(dates, values, where="post", label=name, color=color, linewidth=2.0)
ax.axhline(10_000.0, color="#777777", linewidth=0.8)
ax.set_title("US100 Asia-London Continuation — Fixed 20-point Rule\n1% equity risk per trade; broker-recorded M1 spreads")
ax.set_ylabel("Closed balance (USD)")
ax.set_xlabel("Trade date")
ax.grid(alpha=0.25)
ax.legend(loc="upper left")
fig.tight_layout()
fig.savefig(OUT / "cross-broker-equity.png", dpi=180)
plt.close(fig)

print(json.dumps(summary, indent=2))
