from __future__ import annotations

import unittest
from unittest.mock import patch

from rsi_divergence_bot.config import AppConfig, BotRuntimeConfig, RiskConfig, SymbolConfig, TelegramSignalsConfig
from rsi_divergence_bot.telegram_signals import GeminiSignalParser, ParsedTelegramSignal


def _config(**telegram_overrides) -> AppConfig:
    telegram = TelegramSignalsConfig(**telegram_overrides)
    return AppConfig(
        bot=BotRuntimeConfig(),
        risk=RiskConfig(),
        telegram_signals=telegram,
        symbols=[SymbolConfig(symbol="EURUSD", name="Euro", lot_per_leg=0.1)],
    )


class TelegramSignalParserTests(unittest.TestCase):
    def test_llm_configured_with_openai_or_gemini(self) -> None:
        self.assertTrue(GeminiSignalParser.llm_configured(_config(openai_api_key="sk-test")))
        self.assertTrue(GeminiSignalParser.llm_configured(_config(gemini_api_key="gem-test")))
        self.assertFalse(GeminiSignalParser.llm_configured(_config()))

    @patch.object(GeminiSignalParser, "_parse_with_gemini")
    @patch.object(GeminiSignalParser, "_parse_with_openai")
    def test_openai_primary_gemini_fallback(self, openai_parse, gemini_parse) -> None:
        openai_parse.side_effect = RuntimeError("OpenAI down")
        gemini_parse.return_value = ParsedTelegramSignal(symbol="XAUUSD", action="buy", tps=[2400.0])

        parser = GeminiSignalParser(_config(openai_api_key="sk-test", gemini_api_key="gem-test"))
        parsed = parser.parse("BUY GOLD 2400")

        self.assertEqual(parsed.symbol, "XAUUSD")
        openai_parse.assert_called_once()
        gemini_parse.assert_called_once()

    @patch.object(GeminiSignalParser, "_parse_with_openai")
    def test_openai_success_skips_gemini(self, openai_parse) -> None:
        openai_parse.return_value = ParsedTelegramSignal(symbol="EURUSD", action="sell", tps=[1.08])

        parser = GeminiSignalParser(_config(openai_api_key="sk-test", gemini_api_key="gem-test"))
        parsed = parser.parse("SELL EURUSD 1.08")

        self.assertEqual(parsed.action, "sell")
        openai_parse.assert_called_once()


if __name__ == "__main__":
    unittest.main()
