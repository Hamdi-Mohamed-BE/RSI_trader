from rsi_divergence_bot.backtest import mt5_trade_symbol
from rsi_divergence_bot.config import AppConfig, MT5Config, RiskConfig, SymbolConfig


def _config(*symbols: SymbolConfig) -> AppConfig:
    return AppConfig(
        mt5=MT5Config(is_demo=False),
        risk=RiskConfig(default_forex_lot=0.25),
        symbols=list(symbols),
    )


def test_mt5_trade_symbol_uses_live_name_from_settings():
    cfg = SymbolConfig(
        symbol="BTCUSD",
        name="Bitcoin",
        demo_symbol="BTCUSDm",
        live_symbol="BTCUSD-VIP",
        lot_per_leg=0.1,
    )
    config = _config(cfg)
    assert mt5_trade_symbol(cfg, config) == "BTCUSD-VIP"


def test_mt5_trade_symbol_uses_demo_name_when_demo_account():
    cfg = SymbolConfig(
        symbol="BTCUSD",
        name="Bitcoin",
        demo_symbol="BTCUSDm",
        live_symbol="BTCUSD-VIP",
        lot_per_leg=0.1,
    )
    config = _config(cfg)
    config.mt5.is_demo = True
    assert mt5_trade_symbol(cfg, config) == "BTCUSDm"
