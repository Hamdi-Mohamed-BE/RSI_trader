import json

import numpy as np
import pandas as pd

import nasdaq_intraday_backtest as engine


def saved_summary() -> dict:
    return json.loads((engine.OUT / "summary.json").read_text(encoding="utf-8"))


def saved_ledger() -> pd.DataFrame:
    return pd.read_csv(engine.OUT / "intraday_unseen_trades.csv")


def test_one_trade_per_session_and_flat_by_close() -> None:
    ledger = saved_ledger()
    entry = pd.to_datetime(ledger["entry_et"], utc=True).dt.tz_convert("America/New_York")
    exit_time = pd.to_datetime(ledger["exit_et"], utc=True).dt.tz_convert("America/New_York")
    assert len(ledger) == entry.dt.date.nunique()
    assert set(entry.dt.hour) == {11}
    assert (entry.dt.date == exit_time.dt.date).all()
    assert (exit_time.dt.hour <= 15).all()


def test_saved_metrics_reconcile_to_trade_ledger() -> None:
    ledger = saved_ledger()
    summary = saved_summary()["sealed_2026_test"]
    calculated = engine.stats(ledger["r_multiple"].to_numpy(float), session_days=144)
    for key in (
        "trades",
        "profit_factor",
        "win_rate_pct",
        "max_drawdown_pct",
        "total_return_pct",
        "net_r",
        "avg_r",
        "active_days_pct",
        "profitable_all_days_pct",
    ):
        assert np.isclose(calculated[key], summary[key])


def test_sealed_period_never_enters_candidate_tables() -> None:
    development = pd.read_csv(engine.OUT / "development_leaderboard.csv", nrows=1)
    validation = pd.read_csv(engine.OUT / "validation_shortlist.csv", nrows=1)
    assert not any("test" in column.lower() for column in development.columns)
    assert not any("test" in column.lower() for column in validation.columns)
