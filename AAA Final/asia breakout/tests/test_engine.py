from datetime import datetime, timezone

import pandas as pd

from asia_breakout.config import StrategyConfig
from asia_breakout.engine import EntrySignal, _exit_trade, backtest, calculate_metrics


def _frame() -> pd.DataFrame:
    times = pd.date_range("2026-01-01", periods=18 * 60, freq="1min", tz="UTC")
    close = [100.0] * len(times)
    frame = pd.DataFrame(
        {
            "time": times,
            "open": close,
            "high": [100.1] * len(times),
            "low": [99.9] * len(times),
            "close": close,
            "spread": [1] * len(times),
        }
    )
    return frame


def test_metrics_compound_three_percent() -> None:
    from asia_breakout.models import Trade

    base = dict(
        symbol="TEST",
        session_date=datetime(2026, 1, 1).date(),
        direction="buy",
        entry_mode="confirmed_close",
        stop_mode="midpoint",
        rr_target=2.0,
        entry_time="",
        exit_time="",
        entry=1.0,
        stop=0.9,
        target=1.2,
        exit_price=1.2,
        outcome="win",
        asian_high=1.0,
        asian_low=0.9,
        asian_range=0.1,
        adr=0.2,
        range_adr_fraction=0.5,
    )
    trades = [Trade(pnl_r=2.0, **base), Trade(pnl_r=-1.0, **{**base, "outcome": "loss"})]
    result = calculate_metrics(trades, "TEST", 1_000.0, 3.0)
    assert round(result.ending_balance, 2) == 1_028.20
    assert result.trades == 2
    assert result.win_rate_pct == 50.0


def test_backtest_rejects_missing_adr_warmup() -> None:
    result = backtest(
        _frame(),
        "TEST",
        0.01,
        StrategyConfig(adr_days=14),
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert result == []


def test_trailing_stop_updates_after_completed_m1_bar() -> None:
    frame = pd.DataFrame(
        {
            "time": pd.date_range(
                "2026-01-01 08:00",
                periods=2,
                freq="1min",
                tz="UTC",
            ),
            "open": [100.0, 101.5],
            "high": [102.0, 101.6],
            "low": [99.5, 100.5],
            "close": [101.5, 101.0],
            "spread": [0, 0],
        }
    )
    signal = EntrySignal(
        direction="buy",
        time=frame.iloc[0]["time"],
        entry=100.0,
        stop=99.0,
        target=105.0,
        start_index=0,
    )
    result = _exit_trade(
        frame,
        signal,
        StrategyConfig(
            rr=5.0,
            exit_mode="trailing",
            trail_start_r=1.0,
            trail_distance_r=1.0,
        ),
        point=0.01,
    )
    assert result[1] == 101.0
    assert result[2] == 1.0
