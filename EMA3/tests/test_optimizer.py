from datetime import datetime, timezone

import pandas as pd

from ema3_backtest.backtest import pivot_signals
from ema3_backtest.optimize import ExitConfig, simulate


UTC = timezone.utc


def test_pivot_is_executed_only_after_right_side_confirmation() -> None:
    rows = []
    for index in range(14):
        rows.append(
            {
                "time": pd.Timestamp(datetime(2026, 1, 1, tzinfo=UTC))
                + pd.Timedelta(hours=4 * index),
                "open": 100.0,
                "high": 110.0 + abs(index - 6),
                "low": 90.0 + abs(index - 6),
                "close": 100.0,
                "spread": 0,
            }
        )
    signals = pivot_signals(pd.DataFrame(rows), distance=6)
    buy = next(signal for signal in signals if signal["side"] == "buy")
    assert buy["pivot_idx"] == 6
    assert buy["confirmed_idx"] == 12
    assert buy["execute_idx"] == 13


def test_fixed_two_r_target(monkeypatch) -> None:
    frame = _sample_frame()
    monkeypatch.setattr(
        "ema3_backtest.optimize.pivot_signals",
        lambda *_: [
            {"side": "buy", "pivot_idx": 0, "confirmed_idx": 0, "execute_idx": 1}
        ],
    )
    trades = simulate(
        frame,
        "TEST",
        point=0.01,
        distance=6,
        start=frame.at[1, "time"].to_pydatetime(),
        end=(frame.at[2, "time"] + pd.Timedelta(hours=4)).to_pydatetime(),
        config=ExitConfig("fixed", target_r=2.0),
    )
    assert len(trades) == 1
    assert trades[0].exit_reason == "target"
    assert trades[0].result_r == 2.0


def test_trailing_change_is_effective_from_next_bar(monkeypatch) -> None:
    frame = _sample_frame()
    frame.loc[1, ["high", "close"]] = [111.0, 111.0]
    frame.loc[2, ["open", "high", "low", "close"]] = [110.0, 112.0, 105.0, 108.0]
    monkeypatch.setattr(
        "ema3_backtest.optimize.pivot_signals",
        lambda *_: [
            {"side": "buy", "pivot_idx": 0, "confirmed_idx": 0, "execute_idx": 1}
        ],
    )
    trades = simulate(
        frame,
        "TEST",
        point=0.01,
        distance=6,
        start=frame.at[1, "time"].to_pydatetime(),
        end=(frame.at[2, "time"] + pd.Timedelta(hours=4)).to_pydatetime(),
        config=ExitConfig("trail", trail_start_r=1.0, trail_distance_r=0.5),
    )
    assert len(trades) == 1
    assert trades[0].exit_reason == "stop"
    assert trades[0].result_r == 0.6


def test_second_same_direction_signal_adds_second_leg(monkeypatch) -> None:
    frame = _sample_frame()
    frame.loc[1, ["high", "close"]] = [101.0, 100.0]
    frame.loc[2, ["open", "high", "low", "close"]] = [101.0, 102.0, 100.0, 101.0]
    monkeypatch.setattr(
        "ema3_backtest.optimize.pivot_signals",
        lambda *_: [
            {"side": "buy", "pivot_idx": 0, "confirmed_idx": 0, "execute_idx": 1},
            {"side": "buy", "pivot_idx": 0, "confirmed_idx": 1, "execute_idx": 2},
        ],
    )
    trades = simulate(
        frame,
        "TEST",
        point=0.01,
        distance=6,
        start=frame.at[1, "time"].to_pydatetime(),
        end=(frame.at[2, "time"] + pd.Timedelta(hours=4)).to_pydatetime(),
        config=ExitConfig("trail", trail_start_r=10.0, trail_distance_r=1.0),
        max_same_direction_legs=2,
    )
    assert len(trades) == 2
    assert len({trade.entry_time for trade in trades}) == 2


def _sample_frame() -> pd.DataFrame:
    start = pd.Timestamp(datetime(2026, 1, 1, tzinfo=UTC))
    return pd.DataFrame(
        [
            {
                "time": start,
                "open": 95.0,
                "high": 96.0,
                "low": 90.0,
                "close": 95.0,
                "spread": 0,
            },
            {
                "time": start + pd.Timedelta(hours=4),
                "open": 100.0,
                "high": 121.0,
                "low": 99.0,
                "close": 110.0,
                "spread": 0,
            },
            {
                "time": start + pd.Timedelta(hours=8),
                "open": 110.0,
                "high": 112.0,
                "low": 109.0,
                "close": 111.0,
                "spread": 0,
            },
        ]
    )
