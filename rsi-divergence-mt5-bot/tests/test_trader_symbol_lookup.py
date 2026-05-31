from rsi_divergence_bot.config import AppConfig, BotRuntimeConfig, MT5Config, RiskConfig, SymbolConfig
from rsi_divergence_bot.trader import TradeExecutor


def test_symbol_cfg_lookup_accepts_settings_mt5_name():
    symbol_cfg = SymbolConfig(
        symbol="BTCUSD",
        name="Bitcoin",
        demo_symbol="BTCUSDm",
        live_symbol="BTCUSD-VIP",
        lot_per_leg=0.1,
    )
    config = AppConfig(
        mt5=MT5Config(is_demo=False),
        bot=BotRuntimeConfig(),
        risk=RiskConfig(),
        symbols=[symbol_cfg],
    )
    executor = TradeExecutor(config, client=None, state=None, logger=None)  # type: ignore[arg-type]
    assert executor._symbol_cfg("BTCUSD-VIP") is symbol_cfg
    assert executor._symbol_cfg("BTCUSD") is symbol_cfg
