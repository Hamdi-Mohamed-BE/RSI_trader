from datetime import datetime, timezone

import pytest

from amd_bot.engine import Trade, metrics


def trade(pnl_r: float, minute: int) -> Trade:
    stamp = datetime(2026, 1, 1, 0, minute, tzinfo=timezone.utc).isoformat()
    return Trade(
        symbol="XAUUSD",
        session_date="2026-01-01",
        phase="london_fade",
        side="buy",
        signal_time=stamp,
        entry_time=stamp,
        exit_time=datetime(2026, 1, 1, 0, minute + 1, tzinfo=timezone.utc).isoformat(),
        entry=100.0,
        initial_stop=99.0,
        final_stop=99.0,
        target=101.7,
        exit_price=100.0 + pnl_r,
        initial_risk=1.0,
        pnl_r=pnl_r,
        mae_r=0.0,
        exit_reason="target" if pnl_r > 0 else "stop",
        stop_locked=False,
        asia_high=101.0,
        asia_low=99.0,
        asia_range=2.0,
    )


def test_progression_increases_after_losses_and_resets_after_win() -> None:
    result = metrics(
        "XAUUSD",
        [trade(-1.0, 0), trade(-1.0, 2), trade(1.7, 4), trade(-1.0, 6)],
        1000.0,
        0.5,
        progression_enabled=True,
        progression_multiplier=1.6,
        progression_max_pct=None,
    )
    assert result["max_risk_used_pct"] == pytest.approx(1.28)


def test_progression_can_be_capped_for_live_sizing() -> None:
    result = metrics(
        "XAUUSD",
        [trade(-1.0, 0), trade(-1.0, 2), trade(-1.0, 4), trade(-1.0, 6)],
        1000.0,
        0.5,
        progression_enabled=True,
        progression_multiplier=1.6,
        progression_max_pct=1.0,
    )
    assert result["max_risk_used_pct"] == 1.0
