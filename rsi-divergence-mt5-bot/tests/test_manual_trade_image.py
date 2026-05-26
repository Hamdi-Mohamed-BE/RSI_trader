from __future__ import annotations

import unittest
from unittest.mock import patch

from rsi_divergence_bot.config import AppConfig, SymbolConfig, TelegramSignalsConfig
from rsi_divergence_bot.manual_trade_image import (
    ManualTradeImageParse,
    format_manual_trade_text,
    normalize_image_mime,
    parse_trade_image,
)


def _config(**telegram_overrides) -> AppConfig:
    return AppConfig(
        telegram_signals=TelegramSignalsConfig(**telegram_overrides),
        symbols=[SymbolConfig(symbol="BTCUSD", name="Bitcoin", lot_per_leg=0.01)],
    )


class ManualTradeImageTests(unittest.TestCase):
    def test_format_manual_trade_text(self) -> None:
        parsed = ManualTradeImageParse(
            symbol="BTCUSD",
            side="buy",
            stop_loss=77139,
            tps=[77451.0, 77529.0, 77608.0],
            lot=0.01,
            confidence=0.95,
        )
        text = format_manual_trade_text(parsed)
        self.assertIn("BTCUSD BUY", text)
        self.assertIn("SL 77139", text)
        self.assertIn("TP1 77451", text)
        self.assertIn("LOT 0.01", text)

    def test_normalize_image_mime(self) -> None:
        self.assertEqual(normalize_image_mime("image/jpg"), "image/jpeg")

    @patch("rsi_divergence_bot.manual_trade_image._parse_with_gemini")
    @patch("rsi_divergence_bot.manual_trade_image._parse_with_openai")
    def test_openai_primary_gemini_fallback(self, openai_parse, gemini_parse) -> None:
        openai_parse.side_effect = RuntimeError("OpenAI down")
        gemini_parse.return_value = ManualTradeImageParse(
            symbol="BTCUSD",
            side="buy",
            stop_loss=77139,
            tps=[77451.0],
            lot=0.01,
            confidence=0.9,
        )

        result = parse_trade_image(
            _config(openai_api_key="sk-test", gemini_api_key="gem-test"),
            b"fake-image-bytes",
            "image/png",
        )

        self.assertEqual(result.provider, "gemini")
        self.assertIn("BTCUSD BUY", result.text)
        openai_parse.assert_called_once()
        gemini_parse.assert_called_once()


if __name__ == "__main__":
    unittest.main()
