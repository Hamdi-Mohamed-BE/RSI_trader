import unittest

from rsi_divergence_bot.config import AppConfig, MT5Config, SymbolConfig, TelegramSignalsConfig
from rsi_divergence_bot.symbols import (
    DEFAULT_BROKER_SYMBOL_SUFFIX,
    normalize_broker_symbol_suffix,
    mt5_symbol_candidates,
    market_key,
)


def _config(suffix: str = "-VIP") -> AppConfig:
    return AppConfig(
        telegram_signals=TelegramSignalsConfig(),
        mt5=MT5Config(broker_symbol_suffix=suffix),
        symbols=[SymbolConfig(symbol="EURUSD-VIP", name="EURUSD", lot_per_leg=0.25)],
    )


class Mt5SymbolCandidatesTests(unittest.TestCase):
    def test_default_vip(self) -> None:
        self.assertEqual(mt5_symbol_candidates("EURUSD"), ["EURUSD-VIP", "EURUSDVIP", "EURUSD"])
        self.assertEqual(
            mt5_symbol_candidates("EURUSD", DEFAULT_BROKER_SYMBOL_SUFFIX),
            ["EURUSD-VIP", "EURUSDVIP", "EURUSD"],
        )

    def test_std_from_config(self) -> None:
        suffix = _config("-STD").mt5.broker_symbol_suffix
        self.assertEqual(suffix, "-STD")
        self.assertEqual(mt5_symbol_candidates("CHFJPY", suffix), ["CHFJPY-STD", "CHFJPYSTD", "CHFJPY"])

    def test_std_without_dash(self) -> None:
        suffix = _config("std").mt5.broker_symbol_suffix
        self.assertEqual(suffix, "-STD")
        self.assertEqual(mt5_symbol_candidates("GBPUSD", suffix)[0], "GBPUSD-STD")

    def test_empty_suffix(self) -> None:
        suffix = _config("").mt5.broker_symbol_suffix
        self.assertEqual(suffix, "")
        self.assertEqual(mt5_symbol_candidates("EURUSD", suffix), ["EURUSD"])

    def test_normalize_broker_symbol_suffix(self) -> None:
        self.assertEqual(normalize_broker_symbol_suffix("std"), "-STD")
        self.assertEqual(normalize_broker_symbol_suffix("-vip"), "-VIP")


    def test_legacy_yaml_key_name(self) -> None:
        config = AppConfig.model_validate(
            {
                "mt5": {"RSI_BOT_BROKER_SYMBOL_SUFFIX": "-STD"},
                "symbols": [SymbolConfig(symbol="EURUSD-VIP", name="EURUSD", lot_per_leg=0.25).model_dump()],
            }
        )
        self.assertEqual(config.mt5.broker_symbol_suffix, "-STD")
        self.assertEqual(mt5_symbol_candidates("EURUSD", config.mt5.broker_symbol_suffix)[0], "EURUSD-STD")

    def test_append_suffix_disabled(self) -> None:
        from rsi_divergence_bot.symbols import preferred_broker_symbol

        self.assertEqual(preferred_broker_symbol("BTCUSD", "-VIP", append_suffix=False), "BTCUSD")
        self.assertEqual(preferred_broker_symbol("BTCUSD", "-VIP", append_suffix=True), "BTCUSD-VIP")

    def test_market_key_normalizes_attached_broker_suffix(self) -> None:
        self.assertEqual(market_key("CADJPYm"), "CADJPY")
        self.assertEqual(market_key("US30m"), "US30")


if __name__ == "__main__":
    unittest.main()
