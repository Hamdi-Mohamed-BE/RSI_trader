import pandas as pd
import pytest

from asia_breakout.portfolio import simulate_portfolio


def _trade(instrument: str, entry: str, exit_: str, pnl_r: float) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "instrument": instrument,
                "entry_time": entry,
                "exit_time": exit_,
                "pnl_r": pnl_r,
            }
        ]
    )


def test_exposure_cap_skips_entry_until_risk_is_released() -> None:
    trades = {
        "A": _trade("A", "2026-01-01 09:00Z", "2026-01-01 10:00Z", 1.0),
        "B": _trade("B", "2026-01-01 09:05Z", "2026-01-01 10:05Z", 1.0),
        "C": _trade("C", "2026-01-01 09:10Z", "2026-01-01 10:10Z", 1.0),
    }
    result, audit = simulate_portfolio(
        trades,
        starting_balance=1_000.0,
        risk_pct=3.0,
        exposure_cap_pct=6.0,
        priority=("A", "B", "C"),
    )
    assert result.accepted_trades == 2
    assert result.skipped_signals == 1
    assert result.max_planned_exposure_pct == 6.0
    assert (audit["portfolio_status"] == "skipped_cap").sum() == 1


def test_same_bar_entry_and_exit_releases_exposure() -> None:
    trades = {
        "A": _trade("A", "2026-01-01 09:00Z", "2026-01-01 09:00Z", 0.5),
        "B": _trade("B", "2026-01-01 09:01Z", "2026-01-01 10:00Z", 1.0),
    }
    result, audit = simulate_portfolio(
        trades,
        starting_balance=1_000.0,
        risk_pct=3.0,
        exposure_cap_pct=3.0,
        priority=("A", "B"),
    )
    assert result.accepted_trades == 2
    assert result.skipped_signals == 0
    accepted = audit[audit["portfolio_status"] == "accepted"]
    assert accepted["portfolio_balance_after_exit"].notna().all()


def test_progression_uses_closed_results_not_future_or_entry_order() -> None:
    trades = {
        "A": pd.DataFrame(
            [
                {
                    "entry_time": "2026-01-01 09:00Z",
                    "exit_time": "2026-01-01 10:00Z",
                    "pnl_r": -1.0,
                },
                {
                    "entry_time": "2026-01-01 10:01Z",
                    "exit_time": "2026-01-01 11:00Z",
                    "pnl_r": 1.7,
                },
                {
                    "entry_time": "2026-01-01 11:01Z",
                    "exit_time": "2026-01-01 12:00Z",
                    "pnl_r": 1.7,
                },
            ]
        ),
    }
    result, audit = simulate_portfolio(
        trades,
        starting_balance=1_000.0,
        risk_pct=0.5,
        exposure_cap_pct=10.0,
        priority=("A",),
        progression_multiplier=1.6,
    )
    accepted = audit[audit["portfolio_status"] == "accepted"].sort_values(
        "entry_time"
    )
    assert accepted["portfolio_risk_pct"].tolist() == pytest.approx(
        [0.5, 0.8, 0.5]
    )
    assert result.accepted_trades == 3


def test_progression_cap_is_checked_against_actual_concurrent_exposure() -> None:
    trades = {
        "A": pd.DataFrame(
            [
                {
                    "entry_time": "2026-01-01 09:00Z",
                    "exit_time": "2026-01-01 09:10Z",
                    "pnl_r": -1.0,
                },
                {
                    "entry_time": "2026-01-01 09:11Z",
                    "exit_time": "2026-01-01 10:00Z",
                    "pnl_r": 1.7,
                },
            ]
        ),
        "B": _trade("B", "2026-01-01 09:12Z", "2026-01-01 10:00Z", 1.7),
    }
    result, _ = simulate_portfolio(
        trades,
        starting_balance=1_000.0,
        risk_pct=0.5,
        exposure_cap_pct=1.0,
        priority=("A", "B"),
        progression_multiplier=1.6,
    )
    assert result.accepted_trades == 2
    assert result.skipped_signals == 1
    assert result.max_planned_exposure_pct == pytest.approx(0.8)
