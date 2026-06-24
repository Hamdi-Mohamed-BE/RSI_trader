from rsi_divergence_bot.config import AppConfig, SymbolConfig, TelegramSignalsConfig
from rsi_divergence_bot.manual_trade import resolve_symbol, resolve_symbol_for_telegram


class FakeMT5Client:
    def __init__(self, symbols: set[str]):
        self.symbols = {symbol.upper() for symbol in symbols}

    def symbol_info(self, symbol: str):
        return {"name": symbol} if symbol.upper() in self.symbols else None

    def tick(self, symbol: str):
        return {"bid": 1.0, "ask": 1.1} if symbol.upper() in self.symbols else None


def _config() -> AppConfig:
    return AppConfig(
        telegram_signals=TelegramSignalsConfig(),
        symbols=[
            SymbolConfig(
                symbol="USDCAD-VIP",
                name="USDCAD",
                lot_per_leg=0.5,
            )
        ],
    )


def test_resolve_symbol_for_telegram_uses_existing_alias():
    config = _config()
    cfg, auto_registered = resolve_symbol_for_telegram("USDCAD", config, FakeMT5Client(set()))
    assert cfg is not None
    assert cfg.symbol == "USDCAD-VIP"
    assert auto_registered is False


def test_resolve_symbol_for_telegram_auto_registers_vip_symbol():
    config = _config()
    client = FakeMT5Client({"CHFJPY-VIP"})
    cfg, auto_registered = resolve_symbol_for_telegram("CHFJPY", config, client)
    assert cfg is not None
    assert cfg.symbol == "CHFJPY-VIP"
    assert cfg.lot_per_leg == 0.25
    assert auto_registered is True
    assert resolve_symbol("CHFJPY", config) is cfg
