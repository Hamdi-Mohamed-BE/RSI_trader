from rsi_divergence_bot.config import SymbolConfig, default_symbol_lot, symbol_asset_group
from rsi_divergence_bot.symbols import crypto_aliases_for, market_key


def _symbol(symbol: str, name: str) -> SymbolConfig:
    return SymbolConfig(symbol=symbol, name=name, lot_per_leg=0.01)


def test_symbol_groups_for_settings_sections():
    assert symbol_asset_group(_symbol("BTCUSD", "Bitcoin")) == "crypto"
    assert symbol_asset_group(_symbol("XAUUSD-VIP", "Gold")) == "metals"
    assert symbol_asset_group(_symbol("EURUSD-VIP", "EURUSD")) == "forex"
    assert symbol_asset_group(_symbol("CL-OIL-VIP", "Oil")) == "commodities"


def test_crypto_defaults_and_aliases_cover_added_symbols():
    assert market_key("XRPUSD-VIP") == "XRPUSD"
    assert default_symbol_lot(_symbol("XRPUSD", "Ripple")) == 0.10
    assert default_symbol_lot(_symbol("BNBUSD", "Binance Coin")) == 0.30
    assert {"XRP", "RIPPLE", "XRPUSD"} <= crypto_aliases_for("XRPUSD")
