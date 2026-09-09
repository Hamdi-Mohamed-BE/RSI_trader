"""Independent structural and arithmetic checks for the raw OBV transfer."""
from __future__ import annotations

from pathlib import Path
import json
import math

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent


def metrics(values: np.ndarray) -> tuple[float, float]:
    total = math.expm1(float(values.sum())) * 100.0
    equity = np.exp(np.cumsum(values))
    full = np.r_[1.0, equity]
    drawdown = abs(float(np.min(full / np.maximum.accumulate(full) - 1.0))) * 100.0
    return total, drawdown


def main() -> None:
    universe = pd.read_csv(ROOT / "rule-universe.csv")
    selections = pd.read_csv(ROOT / "monthly-selections.csv")
    daily = pd.read_csv(ROOT / "portfolio-daily.csv", parse_dates=["date_utc"]).set_index("date_utc")
    summary = pd.read_csv(ROOT / "raw-summary.csv")
    trades = pd.read_csv(ROOT / "best1-trades.csv")
    metadata = json.loads((ROOT / "Data" / "metadata.json").read_text(encoding="utf-8"))

    assert len(universe) == 9_900
    assert set(universe.groupby("frequency").size()) == {2_475}
    assert (universe["p"] < universe["q"]).all()
    assert set(universe["frequency"]) == {"M10", "M30", "H1", "D1"}
    assert set(universe["band_pct"]) == {0.0, 0.01, 0.05}
    assert set(universe["delay"]) == {0, 2, 3, 4, 5}
    assert set(universe["hold"].astype(float)) == {6.0, 12.0, float("inf")}

    assert metadata["account_mode"] == "demo/read-only"
    assert metadata["first_utc"].startswith("2022-01-01")
    assert metadata["last_utc"].startswith("2026-08-31")
    assert metadata["bars"] == 490_205

    selection_month = pd.to_datetime(selections["month"], utc=True)
    train_start = pd.to_datetime(selections["train_start"], utc=True)
    train_end = pd.to_datetime(selections["train_end"], utc=True)
    assert (train_end < selection_month).all(), "lookahead detected"
    assert ((selection_month - train_start).dt.days >= 365).all()
    assert selections["selected_rule_ids"].str.split(";").map(len).isin({1, 50}).all()
    for ids in selections["selected_rule_ids"]:
        parsed = [int(value) for value in ids.split(";")]
        assert len(parsed) == len(set(parsed))
        assert min(parsed) >= 0 and max(parsed) < len(universe)

    assert daily.index.min().date().isoformat() == "2023-01-01"
    assert daily.index.max().date().isoformat() == "2026-08-31"
    assert np.isfinite(daily.to_numpy(dtype=float)).all()
    assert len(trades) > 0
    assert (pd.to_datetime(trades["exit_utc"], utc=True) >= pd.to_datetime(trades["entry_utc"], utc=True)).all()

    checked = 0
    for row in summary.itertuples(index=False):
        if row.strategy == "Buy and hold":
            column = f"buyhold_{row.cost_mode}"
        else:
            tokens = row.strategy.lower().replace(" / ", "_").replace(" ", "")
            column = f"{tokens}_{row.cost_mode}"
        total, drawdown = metrics(daily[column].to_numpy(dtype=float))
        assert abs(total - row.return_pct) < 1e-6
        assert abs(drawdown - row.max_drawdown_pct) < 1e-6
        checked += 1

    for prefix in ("best1_mean", "best1_sharpe", "best50_mean", "best50_sharpe", "buyhold"):
        broker_total = metrics(daily[f"{prefix}_broker"].to_numpy(dtype=float))[0]
        paper_total = metrics(daily[f"{prefix}_paper"].to_numpy(dtype=float))[0]
        assert broker_total >= paper_total

    result = {
        "status": "PASS",
        "rules_checked": int(len(universe)),
        "monthly_portfolios_checked": int(len(selections)),
        "summary_rows_recomputed": checked,
        "best1_closed_trades_checked": int(len(trades)),
        "no_lookahead": True,
        "paper_cost_never_better_than_broker_cost": True,
    }
    (ROOT / "VERIFICATION.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
