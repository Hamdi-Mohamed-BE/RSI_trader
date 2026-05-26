from __future__ import annotations

import unittest

from rsi_divergence_bot.config import (
    AiTradeReviewConfig,
    AppConfig,
    BotRuntimeConfig,
    RiskConfig,
    SymbolConfig,
    update_ai_trade_review,
)


def _config() -> AppConfig:
    return AppConfig(
        bot=BotRuntimeConfig(
            ai_trade_review=AiTradeReviewConfig(
                enabled=False,
                use_in_backtest=False,
                min_confidence=0.55,
            )
        ),
        risk=RiskConfig(),
        symbols=[SymbolConfig(symbol="EURUSD", name="Euro", lot_per_leg=0.1)],
    )


class UpdateAiTradeReviewTests(unittest.TestCase):
    def test_update_ai_trade_review_fields(self) -> None:
        config = _config()
        update_ai_trade_review(
            config,
            enabled=True,
            use_in_backtest=True,
            min_confidence=0.8,
        )
        review = config.bot.ai_trade_review
        self.assertTrue(review.enabled)
        self.assertTrue(review.use_in_backtest)
        self.assertEqual(review.min_confidence, 0.8)

    def test_update_ai_trade_review_rejects_invalid_confidence(self) -> None:
        config = _config()
        with self.assertRaises(ValueError):
            update_ai_trade_review(config, min_confidence=1.5)


if __name__ == "__main__":
    unittest.main()
