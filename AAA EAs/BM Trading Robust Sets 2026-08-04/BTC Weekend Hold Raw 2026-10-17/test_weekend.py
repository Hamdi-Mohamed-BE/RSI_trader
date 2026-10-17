"""Synthetic, offline fixtures; no account, network or subprocess access."""
from datetime import datetime, timezone
import importlib.util
import math
from pathlib import Path
import sys

import numpy as np
import pytest


spec = importlib.util.spec_from_file_location("btc_weekend_raw", Path(__file__).with_name("run.py"))
study = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(study)


def epoch(value):
    return int(datetime.fromisoformat(value).timestamp())


def rates(rows):
    return np.array(rows, dtype=[("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"), ("close", "f8"), ("spread", "i4")])


@pytest.mark.parametrize("start,end,hours", [("2026-03-06T00:00:00+00:00", "2026-03-10T00:00:00+00:00", 47), ("2025-10-31T00:00:00+00:00", "2025-11-04T00:00:00+00:00", 49), ("2026-07-03T00:00:00+00:00", "2026-07-07T00:00:00+00:00", 48)])
def test_dst_uses_both_local_wall_clocks(start, end, hours):
    pairs = study.scheduled_weekends(epoch(start), epoch(end))
    assert len(pairs) == 1
    entry, exit_time = pairs[0]
    assert (exit_time - entry) / 3600 == hours
    assert datetime.fromtimestamp(entry, study.NY).hour == 17
    assert datetime.fromtimestamp(exit_time, study.NY).hour == 17


def test_missing_exact_bar_is_not_replaced_by_next_minute_or_last_price():
    target = epoch("2026-07-03T21:00:00+00:00")
    times = np.array([target - 60, target + 60])
    assert study.exact_index(times, target) is None
    assert study.exact_index(times, target + 60) == 1


def test_open_not_completed_close_is_used_and_spread_points_convert_to_dollars():
    entry, exit_time = study.scheduled_weekends(epoch("2026-07-03T00:00:00+00:00"), epoch("2026-07-07T00:00:00+00:00"))[0]
    array = rates([(entry, 100.0, 999.0, 1.0, 800.0, 200), (exit_time, 110.0, 999.0, 1.0, 2.0, 9000)])
    row = study.analyze_window(array, entry, exit_time + 60, include_trades=True)
    trade = row["trade_ledger"][0]
    assert trade["entry_ask_proxy"] == 102.0
    assert trade["exit_bid"] == 110.0
    assert trade["quantity_btc"] == pytest.approx(10000 / 102)
    assert trade["entry_spread_cost_usd"] == pytest.approx(20000 / 102)
    assert trade["pnl_usd"] == pytest.approx(10000 / 102 * 8)
    assert trade["gross_pnl_usd"] - trade["entry_spread_cost_usd"] == pytest.approx(trade["pnl_usd"])
    assert trade["entry_delay_seconds"] == trade["exit_delay_seconds"] == 0


def test_exit_outside_window_is_not_forced_closed_or_counted():
    entry, exit_time = study.scheduled_weekends(epoch("2026-07-03T00:00:00+00:00"), epoch("2026-07-07T00:00:00+00:00"))[0]
    array = rates([(entry, 100, 101, 99, 100, 100), (exit_time, 110, 111, 109, 110, 100)])
    row = study.analyze_window(array, entry, exit_time)
    assert row["trades"] == 0 and row["ending_balance_usd"] == 10000
    assert row["skipped"][0]["reason"] == "exit outside completed requested window"


def test_no_stop_loss_sizing_is_cash_allocated_and_fractional_not_percent_stop_risk():
    assert study.quantity_for_notional(9000, 100000, "cash", 10000) == pytest.approx(0.09)
    assert study.quantity_for_notional(9000, 100000, "fixed_reference", 10000) == pytest.approx(0.1)
    assert study.quantity_for_notional(9000, 100000, "cash", 10000) * 100000 <= 9000
    with pytest.raises(ValueError):
        study.quantity_for_notional(0, 100000, "cash", 10000)


def test_profit_factor_and_drawdown_include_starting_balance():
    assert study.profit_factor([100, -50, 0]) == 2
    assert study.profit_factor([100, 20]) is None
    assert study.profit_factor([]) is None
    dd = study.drawdown([10000, 9000, 11000, 8800])
    assert dd["usd"] == 2200
    assert dd["percent"] == pytest.approx(20)


def test_breakevens_reset_streaks_and_losses_are_not_wins():
    assert study.streaks([1, 2, 0, 3, -1, -2, -3, 0, -1]) == (2, 3)


def test_daily_sharpe_includes_zero_cash_calendar_days():
    start, end = epoch("2026-07-01T00:00:00+00:00"), epoch("2026-07-05T00:00:00+00:00")
    trades = [{"exit_epoch": epoch("2026-07-03T21:00:00+00:00"), "pnl_usd": 100}]
    stats = study.daily_cash_statistics(trades, start, end, 10000)
    assert stats["calendar_days"] == 4
    assert [day["pnl_usd"] for day in stats["daily_closed_curve"]] == [0, 0, 100, 0]
    expected = np.mean([0, 0, 0.01, 0]) / np.std([0, 0, 0.01, 0], ddof=1) * math.sqrt(365)
    assert stats["closed_cash_sharpe"] == pytest.approx(expected)


def test_swap_sensitivity_is_points_per_btc_not_a_percent_risk_input():
    entry, exit_time = study.scheduled_weekends(epoch("2026-07-03T00:00:00+00:00"), epoch("2026-07-07T00:00:00+00:00"))[0]
    array = rates([(entry, 100000, 100001, 99999, 100000, 100), (exit_time, 100000, 100001, 99999, 100000, 100)])
    result = study.analyze_window(array, entry, exit_time + 60, swap_charges=3, include_trades=True)
    row = result["trade_ledger"][0]
    assert row["modeled_financing_usd"] == pytest.approx(row["quantity_btc"] * -1863.7 * 0.01 * 3)
    assert row["pnl_usd"] == pytest.approx(-row["entry_spread_cost_usd"] + row["modeled_financing_usd"])
