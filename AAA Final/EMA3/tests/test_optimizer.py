from datetime import datetime, timezone

import pandas as pd
import pytest

from ema3_backtest.backtest import pivot_signals
from ema3_backtest.optimize import (
    ExitConfig,
    RTrade,
    filtered_pivot_signals,
    compounded_journal,
    metrics,
    simulate,
)


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


def test_trailing_exit_respects_hard_target_cap(monkeypatch) -> None:
    frame = _sample_frame()
    frame.loc[1, ["high", "close"]] = [118.0, 116.0]
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
        config=ExitConfig(
            "trail", trail_start_r=1.0, trail_distance_r=0.5, target_cap_r=1.7
        ),
    )
    assert len(trades) == 1
    assert trades[0].exit_reason == "target"
    assert trades[0].result_r == 1.7


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


def test_ruined_account_cannot_recover_from_negative_equity() -> None:
    base = {
        "symbol": "TEST",
        "config": "fixed_2R",
        "side": "buy",
        "pivot_time": "2026-01-01T00:00:00+00:00",
        "entry_time": "2026-01-01T04:00:00+00:00",
        "exit_time": "2026-01-01T08:00:00+00:00",
        "entry": 100.0,
        "initial_stop": 99.0,
        "exit": 0.0,
        "exit_reason": "gap",
        "bars_held": 1,
    }
    catastrophic = RTrade(**base, result_r=-200.0)
    impossible_recovery = RTrade(
        **{**base, "exit_time": "2026-01-01T12:00:00+00:00"},
        result_r=500.0,
    )
    result = metrics(
        [catastrophic, impossible_recovery], risk_pct=1.0, starting_balance=1_000.0
    )
    assert result["ending_balance"] == 0.0
    assert result["max_drawdown_pct"] == 100.0
    assert result["processed_trades"] == 1
    assert result["ruined"] is True


def test_uncapped_loss_progression_uses_exact_point_five_sequence() -> None:
    base = {
        "symbol": "TEST",
        "config": "fixed_1.7R",
        "side": "buy",
        "pivot_time": "2026-01-01T00:00:00+00:00",
        "entry_time": "2026-01-01T04:00:00+00:00",
        "entry": 100.0,
        "initial_stop": 99.0,
        "exit": 99.0,
        "exit_reason": "stop",
        "bars_held": 1,
    }
    results = [-1.0, -1.0, -1.0, 1.7, -1.0]
    trades = [
        RTrade(
            **base,
            exit_time=f"2026-01-0{index + 2}T08:00:00+00:00",
            result_r=result,
        )
        for index, result in enumerate(results)
    ]
    journal = compounded_journal(
        trades,
        risk_pct=0.5,
        starting_balance=1_000.0,
        progression_enabled=True,
        progression_multiplier=1.6,
        max_risk_pct=None,
    )
    assert journal["applied_risk_pct"].tolist() == pytest.approx(
        [0.5, 0.8, 1.28, 2.048, 0.5]
    )
    stats = metrics(
        trades,
        risk_pct=0.5,
        starting_balance=1_000.0,
        progression_enabled=True,
        progression_multiplier=1.6,
        max_risk_pct=None,
    )
    assert stats["maximum_applied_risk_pct"] == pytest.approx(2.048)


def test_loss_progression_live_style_cap_is_enforced() -> None:
    base = {
        "symbol": "TEST",
        "config": "fixed_1.7R",
        "side": "buy",
        "pivot_time": "2026-01-01T00:00:00+00:00",
        "entry_time": "2026-01-01T04:00:00+00:00",
        "entry": 100.0,
        "initial_stop": 99.0,
        "exit": 99.0,
        "exit_reason": "stop",
        "bars_held": 1,
    }
    trades = [
        RTrade(
            **base,
            exit_time=f"2026-01-0{index + 2}T08:00:00+00:00",
            result_r=-1.0,
        )
        for index in range(5)
    ]
    journal = compounded_journal(
        trades,
        risk_pct=0.5,
        progression_enabled=True,
        progression_multiplier=1.6,
        max_risk_pct=1.28,
    )
    assert journal["applied_risk_pct"].tolist() == [0.5, 0.8, 1.28, 1.28, 1.28]


def test_ema200_slope_filter_keeps_only_trend_aligned_signal(monkeypatch) -> None:
    frame = pd.DataFrame(
        {
            "time": pd.date_range("2026-01-01", periods=220, freq="4h", tz="UTC"),
            "open": [100.0 + index for index in range(220)],
            "high": [101.0 + index for index in range(220)],
            "low": [99.0 + index for index in range(220)],
            "close": [100.0 + index for index in range(220)],
            "spread": [0] * 220,
        }
    )
    monkeypatch.setattr(
        "ema3_backtest.optimize.pivot_signals",
        lambda *_: [
            {"side": "buy", "pivot_idx": 200, "confirmed_idx": 210, "execute_idx": 211},
            {"side": "sell", "pivot_idx": 200, "confirmed_idx": 210, "execute_idx": 211},
        ],
    )
    signals = filtered_pivot_signals(
        frame, distance=5, signal_filter="ema200_slope", ema_slope_bars=6
    )
    assert [signal["side"] for signal in signals] == ["buy"]


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
