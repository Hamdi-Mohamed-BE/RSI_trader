from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from rsi_divergence_bot.config import (
    AiTradeReviewConfig,
    AppConfig,
    BotRuntimeConfig,
    RiskConfig,
    SymbolConfig,
    TelegramSignalsConfig,
)
from rsi_divergence_bot.decision import TradeDecision
from rsi_divergence_bot.strategy import Signal
from rsi_divergence_bot.trade_ai_review import (
    TradeAiReviewer,
    TradeAiReviewResult,
    ai_review_applies,
    build_review_payload,
    llm_configured,
)
from rsi_divergence_bot.trader import TradeExecutor


def _config(*, bot=None, telegram=None) -> AppConfig:
    bot_cfg = BotRuntimeConfig(**(bot or {}))
    telegram_cfg = TelegramSignalsConfig(**(telegram or {}))
    return AppConfig(
        bot=bot_cfg,
        risk=RiskConfig(),
        telegram_signals=telegram_cfg,
        symbols=[SymbolConfig(symbol="EURUSD", name="Euro", lot_per_leg=0.1)],
    )


def _signal() -> Signal:
    return Signal(
        setup_id="abc123",
        symbol="EURUSD",
        market_key="EURUSD",
        name="Euro",
        side="buy",
        time=datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc),
        entry=1.08,
        sl=1.079,
        tps=[1.081, 1.082],
        lot_per_leg=0.1,
        risk_distance=0.001,
        session="London",
        reason="bullish rsi divergence",
    )


def _decision() -> TradeDecision:
    return TradeDecision(
        allowed=True,
        code="ok",
        reason="ok",
        risk_usd=25.0,
        spread=0.00012,
        spread_atr=0.18,
        tp1_distance=0.001,
        min_tp1_distance=0.0008,
    )


class TradeAiReviewConfigTests(unittest.TestCase):
    def test_ai_review_applies_when_enabled_for_all_strategies(self) -> None:
        config = _config(bot={"ai_trade_review": AiTradeReviewConfig(enabled=True)})
        self.assertTrue(ai_review_applies(config))

    def test_ai_review_respects_strategy_list(self) -> None:
        config = _config(
            bot={
                "strategy": "signal_full_with_tp_protection",
                "ai_trade_review": AiTradeReviewConfig(
                    enabled=True,
                    strategies=["signal_with_tp_protection"],
                ),
            }
        )
        self.assertFalse(ai_review_applies(config))

    def test_llm_configured_uses_telegram_keys(self) -> None:
        config = _config(telegram={"openai_api_key": "sk-test"})
        self.assertTrue(llm_configured(config))

    def test_build_review_payload_includes_trade_context(self) -> None:
        config = _config(bot={"strategy": "signal_full_with_tp_protection"})
        payload = build_review_payload(config, _signal(), _decision(), live_price=1.0801)
        self.assertEqual(payload["strategy"], "signal_full_with_tp_protection")
        self.assertEqual(payload["live_price"], 1.0801)
        self.assertEqual(payload["risk_usd"], 25.0)


class TradeAiReviewerTests(unittest.TestCase):
    @patch.object(TradeAiReviewer, "_review_with_gemini")
    @patch.object(TradeAiReviewer, "_review_with_openai")
    def test_openai_primary_gemini_fallback(self, openai_review, gemini_review) -> None:
        openai_review.side_effect = RuntimeError("OpenAI down")
        gemini_review.return_value = TradeAiReviewResult(
            approved=True,
            confidence=0.8,
            reason="Structure looks valid",
        )

        reviewer = TradeAiReviewer(
            _config(telegram={"openai_api_key": "sk-test", "gemini_api_key": "gem-test"})
        )
        result = reviewer.review(_signal(), _decision())

        self.assertTrue(result.approved)
        self.assertEqual(result.provider, "gemini")
        openai_review.assert_called_once()
        gemini_review.assert_called_once()

    @patch.object(TradeAiReviewer, "_review_with_openai")
    def test_openai_success_skips_gemini(self, openai_review) -> None:
        openai_review.return_value = TradeAiReviewResult(
            approved=False,
            confidence=0.4,
            reason="Weak divergence",
        )

        reviewer = TradeAiReviewer(
            _config(telegram={"openai_api_key": "sk-test", "gemini_api_key": "gem-test"})
        )
        result = reviewer.review(_signal(), _decision())

        self.assertFalse(result.approved)
        self.assertEqual(result.provider, "openai")
        openai_review.assert_called_once()


class TradeExecutorAiReviewTests(unittest.TestCase):
    @patch.object(TradeAiReviewer, "review")
    def test_rejects_trade_when_ai_rejects(self, review_mock) -> None:
        config = _config(
            bot={
                "dry_run": False,
                "ai_trade_review": AiTradeReviewConfig(enabled=True, min_confidence=0.55),
            },
            telegram={"openai_api_key": "sk-test"},
        )
        client = MagicMock()
        client.money_for_distance.return_value = 10.0
        client.positions.return_value = []
        tick = MagicMock()
        tick.bid = 1.08
        tick.ask = 1.0801
        client.tick.return_value = tick
        state = MagicMock()
        state.is_seen.return_value = False
        logger = MagicMock()
        executor = TradeExecutor(config, client, state, logger)
        review_mock.return_value = TradeAiReviewResult(
            approved=False,
            confidence=0.3,
            reason="Overextended",
            provider="openai",
        )

        with patch("rsi_divergence_bot.trader.evaluate_trade_signal") as evaluate:
            evaluate.return_value = _decision()
            with patch("rsi_divergence_bot.trader.resolve_day_start_balance", return_value=10000.0):
                outcome = executor.place_signal(_signal())

        self.assertEqual(outcome, "skipped")
        state.mark_seen.assert_called_once_with("abc123")
        review_mock.assert_called_once()

    @patch.object(TradeAiReviewer, "review")
    def test_places_trade_when_ai_approves(self, review_mock) -> None:
        config = _config(
            bot={
                "dry_run": False,
                "strategy": "signal_full_with_tp_protection",
                "ai_trade_review": AiTradeReviewConfig(enabled=True, min_confidence=0.55),
            },
            telegram={"openai_api_key": "sk-test"},
        )
        client = MagicMock()
        client.money_for_distance.return_value = 10.0
        client.positions.return_value = []
        tick = MagicMock()
        tick.bid = 1.08
        tick.ask = 1.0801
        client.tick.return_value = tick
        client.send_market.return_value = {"retcode": 10009, "order": 123, "volume": 0.1}
        state = MagicMock()
        state.is_seen.return_value = False
        logger = MagicMock()
        executor = TradeExecutor(config, client, state, logger)
        review_mock.return_value = TradeAiReviewResult(
            approved=True,
            confidence=0.82,
            reason="Good setup",
            provider="openai",
        )

        with patch("rsi_divergence_bot.trader.evaluate_trade_signal") as evaluate:
            evaluate.return_value = _decision()
            with patch("rsi_divergence_bot.trader.resolve_day_start_balance", return_value=10000.0):
                with patch.object(executor, "_place_full_signal", return_value="placed") as place:
                    outcome = executor.place_signal(_signal())

        self.assertEqual(outcome, "placed")
        place.assert_called_once()
        review_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
