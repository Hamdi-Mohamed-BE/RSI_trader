from rsi_divergence_bot.backtest import DailyLossGuard
from rsi_divergence_bot.config import AppConfig, RiskConfig
from rsi_divergence_bot.daily_risk import daily_loss_setup_risk_cap
from rsi_divergence_bot.decision import evaluate_trade_signal, filter_settings_for_profile
from rsi_divergence_bot.strategy import Signal


class _FixedEquityClient:
    def __init__(self, per_leg_risk: float = 544.4):
        self.per_leg_risk = per_leg_risk

    def money_for_distance(self, _symbol, _volume, _price_distance):
        return self.per_leg_risk


def _signal(*, lot: float = 0.08, risk_distance: float = 1.361, legs: int = 3) -> Signal:
    return Signal(
        setup_id="xag-test",
        symbol="XAGUSD-VIP",
        market_key="XAGUSD-VIP",
        name="Silver VIP",
        side="sell",
        time="2026-04-06T09:40:00+00:00",
        entry=71.78,
        sl=73.141,
        tps=[70.0, 69.0, 68.0][:legs],
        lot_per_leg=lot,
        risk_distance=risk_distance,
        session="test",
        reason="test",
    )


def _config() -> AppConfig:
    return AppConfig.model_validate(
        {
            "risk": {
                "use_daily_loss_guard": True,
                "max_daily_loss_pct": 15.0,
                "use_risk_filter": False,
            },
            "symbols": [
                {
                    "symbol": "XAGUSD-VIP",
                    "name": "Silver VIP",
                    "lot_per_leg": 0.08,
                    "sl_atr_mult": 1.0,
                }
            ],
        }
    )


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
    ts = 1_704_067_200
    guard.check_entry(_FixedEquityClient(), ts)
    guard.balance = 840.0
    allowed, loss, loss_limit = guard.check_entry(_FixedEquityClient(), ts + 60)
    assert allowed is False
    assert loss == 160.0
    assert loss_limit == 150.0


def test_daily_loss_guard_resets_limit_on_new_utc_day():
    guard = DailyLossGuard(1000.0, 15.0)
    day_one = 1_704_067_200  # 2024-01-01 00:00:00 UTC
    day_two = 1_704_153_600  # 2024-01-02 00:00:00 UTC

    guard.balance = 840.0
    allowed, _, _ = guard.check_entry(_FixedEquityClient(), day_one)
    assert allowed is True

    guard.balance = 900.0
    allowed, loss, loss_limit = guard.check_entry(_FixedEquityClient(), day_two)
    assert allowed is True
    assert loss == 0.0
    assert loss_limit == 135.0


def test_daily_loss_guard_uses_day_start_not_intraday_high():
    guard = DailyLossGuard(1000.0, 15.0)
    guard.balance = 1800.0
    ts = 1_704_067_200
    allowed, _, _ = guard.check_entry(_FixedEquityClient(), ts)
    assert allowed is True

    guard.balance = 1530.0
    allowed, loss, loss_limit = guard.check_entry(_FixedEquityClient(), ts + 3600)
    assert loss == 270.0
    assert loss_limit == 270.0
    assert allowed is False


def test_daily_loss_setup_risk_cap():
    assert daily_loss_setup_risk_cap(1037.97, 15.0) == 155.70


def test_evaluate_trade_signal_blocks_setup_risk_above_daily_cap():
    config = _config()
    decision = evaluate_trade_signal(
        _FixedEquityClient(),
        config,
        _signal(),
        config.symbols[0],
        filters=filter_settings_for_profile("backtest"),
        day_start_balance=1037.97,
    )
    assert decision.allowed is False
    assert decision.code == "daily_loss_guard"
    assert round(decision.risk_usd, 2) == 1633.2


def test_evaluate_trade_signal_allows_setup_risk_under_daily_cap():
    config = _config()
    decision = evaluate_trade_signal(
        _FixedEquityClient(per_leg_risk=50.0),
        config,
        _signal(lot=0.08, risk_distance=1.361, legs=3),
        config.symbols[0],
        filters=filter_settings_for_profile("backtest"),
        day_start_balance=1037.97,
    )
    assert decision.allowed is True
    assert decision.risk_usd == 150.0


def test_evaluate_trade_signal_skips_daily_cap_when_guard_disabled():
    config = _config()
    config = config.model_copy(update={"risk": config.risk.model_copy(update={"use_daily_loss_guard": False})})
    decision = evaluate_trade_signal(
        _FixedEquityClient(),
        config,
        _signal(),
        config.symbols[0],
        filters=filter_settings_for_profile("backtest"),
        day_start_balance=1037.97,
    )
    assert decision.allowed is True
