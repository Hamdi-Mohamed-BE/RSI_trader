import pandas as pd

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
