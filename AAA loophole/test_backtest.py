import json

import numpy as np
import pandas as pd

import nasdaq_loophole_backtest as engine


SELECTED = engine.Candidate(
    family="pullback_rsi",
    direction="long",
    regime_ma=100,
    atr_stop=3.0,
    max_hold=10,
    target_r=0.0,
    rsi_period=2,
    rsi_entry=5,
    rsi_exit=70,
)


def cached_nq() -> pd.DataFrame:
    data = pd.read_csv(engine.DATA_DIR / "NQ_F_daily.csv", index_col="date", parse_dates=True)
    return engine.prepare_indicators(data)


def test_compiled_selector_matches_detailed_trade_ledger() -> None:
    frame = cached_nq()
    start = int(frame.index.searchsorted(pd.Timestamp("2000-01-01"), side="left"))
    end = int(frame.index.searchsorted(pd.Timestamp("2020-12-31"), side="right") - 1)
    le, se, lx, sx = engine.candidate_signals(frame, SELECTED)
    fast_r, fast_entries = engine._fast_backtest_arrays(
        frame["open"].to_numpy(float),
        frame["high"].to_numpy(float),
        frame["low"].to_numpy(float),
        frame["close"].to_numpy(float),
        frame["atr14"].to_numpy(float),
        le.to_numpy(bool),
        se.to_numpy(bool),
        lx.to_numpy(bool),
        sx.to_numpy(bool),
        start,
        end,
        SELECTED.atr_stop,
        SELECTED.target_r,
        SELECTED.max_hold,
        0.5,
        0.62,
    )
    detailed = engine.backtest(frame, SELECTED, "2000-01-01", "2020-12-31")
    assert len(fast_r) == len(detailed)
    assert np.allclose(fast_r, detailed["r_multiple"].to_numpy(float), atol=1e-12)
    assert list(frame.index[fast_entries]) == list(pd.to_datetime(detailed["entry_date"]))


def test_saved_unseen_metrics_match_trade_ledger() -> None:
    summary = json.loads((engine.RESULTS_DIR / "summary.json").read_text(encoding="utf-8"))
    trades = pd.read_csv(engine.RESULTS_DIR / "nq_unseen_test_trades.csv")
    calculated = engine.metrics(trades)
    saved = summary["unseen_nq_test"]
    for key in ("trades", "profit_factor", "win_rate_pct", "total_return_pct", "net_r", "avg_r"):
        assert np.isclose(calculated[key], saved[key])


def test_no_test_columns_in_candidate_selection_table() -> None:
    leaderboard = pd.read_csv(engine.RESULTS_DIR / "candidate_leaderboard.csv", nrows=1)
    assert not any("test" in column.lower() for column in leaderboard.columns)
