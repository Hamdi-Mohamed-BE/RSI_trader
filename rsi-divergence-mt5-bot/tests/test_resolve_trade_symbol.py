from rsi_divergence_bot.config import AppConfig, MT5Config, RiskConfig, SymbolConfig
from rsi_divergence_bot.symbols import resolve_trade_symbol


def _config(*symbols: SymbolConfig) -> AppConfig:
    return AppConfig(
        mt5=MT5Config(broker_symbol_suffix="-VIP", append_broker_symbol_suffix=True),
        risk=RiskConfig(default_forex_lot=0.25),
        symbols=list(symbols),
    )


def test_resolve_trade_symbol_uses_demo_name_for_demo_account():
    config = _config(
        SymbolConfig(
            symbol="BTCUSD",
            name="Bitcoin",
            demo_symbol="BTCUSD-STD",
            live_symbol="BTCUSD-VIP",
            lot_per_leg=0.1,
        )
    )
    assert resolve_trade_symbol("BTCUSD", config, is_demo=True) == "BTCUSD-STD"
    assert resolve_trade_symbol("BTCUSD", config, is_demo=False) == "BTCUSD-VIP"


def test_resolve_trade_symbol_preserves_demo_symbol_case():
    config = _config(
        SymbolConfig(
            symbol="BTCUSD",
            name="Bitcoin",
            demo_symbol="BTCUSDm",
            live_symbol="BTCUSD-VIP",
            lot_per_leg=0.1,
        )
    )
    assert resolve_trade_symbol("BTCUSD", config, is_demo=True) == "BTCUSDm"
    assert resolve_trade_symbol("btcusdm", config, is_demo=True) == "BTCUSDm"


def test_resolve_trade_symbol_falls_back_to_suffix_for_unknown_symbol():
    config = _config(
        SymbolConfig(
            symbol="BTCUSD",
            name="Bitcoin",
            demo_symbol="BTCUSD-STD",
            live_symbol="BTCUSD-VIP",
            lot_per_leg=0.1,
        )
    )
    assert resolve_trade_symbol("EURUSD", config, is_demo=True, append_suffix=True) == "EURUSD-VIP"
    assert resolve_trade_symbol("EURUSD", config, is_demo=True, append_suffix=False) == "EURUSD"
