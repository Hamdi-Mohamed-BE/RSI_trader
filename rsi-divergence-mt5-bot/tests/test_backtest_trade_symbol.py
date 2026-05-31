from rsi_divergence_bot.config import AppConfig, MT5Config, RiskConfig, SymbolConfig, apply_settings_mt5_symbol
from rsi_divergence_bot.symbols import settings_mt5_symbol_from_config
from rsi_divergence_bot.strategy import Signal
from datetime import datetime, timezone


def _config(*symbols: SymbolConfig) -> AppConfig:
    return AppConfig(
        mt5=MT5Config(is_demo=False),
        risk=RiskConfig(default_forex_lot=0.25),
        symbols=list(symbols),
    )


def test_settings_mt5_symbol_uses_live_name_from_settings():
    cfg = SymbolConfig(
        symbol="BTCUSD",
        name="Bitcoin",
        demo_symbol="BTCUSDm",
        live_symbol="BTCUSD-VIP",
        lot_per_leg=0.1,
    )
    config = _config(cfg)
    assert settings_mt5_symbol_from_config(cfg, config) == "BTCUSD-VIP"


def test_settings_mt5_symbol_uses_demo_name_when_demo_account():
    cfg = SymbolConfig(
        symbol="BTCUSD",
        name="Bitcoin",
        demo_symbol="BTCUSDm",
        live_symbol="BTCUSD-VIP",
        lot_per_leg=0.1,
    )
    config = _config(cfg)
    config.mt5.is_demo = True
    assert settings_mt5_symbol_from_config(cfg, config) == "BTCUSDm"


def test_apply_settings_mt5_symbol_rewrites_signal_symbol():
    cfg = SymbolConfig(
        symbol="BTCUSD",
        name="Bitcoin",
        demo_symbol="BTCUSDm",
        live_symbol="BTCUSD-VIP",
        lot_per_leg=0.1,
    )
    config = _config(cfg)
    signal = Signal(
        setup_id="abc",
        symbol="BTCUSD",
        market_key="BTCUSD",
        name="Bitcoin",
        side="buy",
        time=datetime.now(timezone.utc),
        entry=1.0,
        sl=0.9,
        tps=[1.1],
        lot_per_leg=0.1,
        risk_distance=0.1,
        session="",
        reason="test",
    )
    updated = apply_settings_mt5_symbol(signal, cfg, config)
    assert updated.symbol == "BTCUSD-VIP"
