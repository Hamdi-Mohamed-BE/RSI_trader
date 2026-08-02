import pytest

from asia_breakout.risk import next_loss_streak, progressed_risk_pct


def test_exact_loss_progression_and_live_cap() -> None:
    assert progressed_risk_pct(0.5, 0, 1.6) == pytest.approx(0.5)
    assert progressed_risk_pct(0.5, 1, 1.6) == pytest.approx(0.8)
    assert progressed_risk_pct(0.5, 2, 1.6) == pytest.approx(1.28)
    assert progressed_risk_pct(0.5, 4, 1.6, 2.0) == pytest.approx(2.0)


def test_streak_resets_only_after_a_closed_win() -> None:
    streak = next_loss_streak(0, -1.0)
    assert next_loss_streak(streak, 0.0) == 1
    assert next_loss_streak(streak, 1.7) == 0
