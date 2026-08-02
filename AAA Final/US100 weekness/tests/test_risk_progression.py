from nasdaq_weakness.backtest import _stats
from nasdaq_weakness.models import Trade
from datetime import datetime, timezone


def _trade(day: int, result: float) -> Trade:
    stamp = datetime(2026, 1, day, tzinfo=timezone.utc)
    return Trade("US100", f"2026-01-{day:02d}", "S2B", "SELL_LIMIT", stamp,
                 stamp, 100, 110, 100 - 10 * result, 83, 1, result, "TEST")


def test_progression_uses_loss_streak_and_resets_after_win():
    trades = [_trade(1, -1), _trade(2, -1), _trade(3, 1), _trade(4, -1)]
    stats = _stats(trades, 0.5, 10_000, progression_enabled=True,
                   progression_multiplier=1.6, progression_max_pct=None)
    expected = 10_000 * 0.995 * 0.992 * 1.0128 * 0.995
    assert abs(stats.ending_balance - expected) < 1e-6
