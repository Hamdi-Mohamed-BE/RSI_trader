from rsi_divergence_bot.backtest import DailyLossGuard
from rsi_divergence_bot.config import RiskConfig


class _FixedEquityClient:
    pass


def test_risk_config_flag_disables_daily_loss_guard():
    cfg = RiskConfig(use_daily_loss_guard=False, max_daily_loss_pct=15.0)
    assert cfg.daily_loss_guard_active() is False
    assert cfg.effective_daily_loss_pct() is None


def test_risk_config_flag_enables_daily_loss_guard():
    cfg = RiskConfig(use_daily_loss_guard=True, max_daily_loss_pct=15.0)
    assert cfg.daily_loss_guard_active() is True
    assert cfg.effective_daily_loss_pct() == 15.0


def test_daily_loss_guard_disabled():
    guard = DailyLossGuard(1000.0, None)
    allowed, loss, loss_limit = guard.check_entry(_FixedEquityClient(), 1_700_000_000)
    assert allowed is True
    assert loss == 0.0
    assert loss_limit == 0.0


def test_daily_loss_guard_blocks_when_equity_below_limit():
    guard = DailyLossGuard(1000.0, 15.0)
    guard.balance = 840.0
    allowed, loss, loss_limit = guard.check_entry(_FixedEquityClient(), 1_700_000_000)
    assert allowed is False
    assert loss == 160.0
    assert loss_limit == 150.0


def test_daily_loss_guard_resets_limit_on_new_utc_day():
    guard = DailyLossGuard(1000.0, 15.0)
    guard.balance = 840.0
    day_one = 1_704_067_200  # 2024-01-01 00:00:00 UTC
    day_two = 1_704_153_600  # 2024-01-02 00:00:00 UTC

    blocked, _, _ = guard.check_entry(_FixedEquityClient(), day_one)
    assert blocked is False

    guard.balance = 900.0
    allowed, loss, loss_limit = guard.check_entry(_FixedEquityClient(), day_two)
    assert allowed is True
    assert loss == 0.0
    assert loss_limit == 135.0
