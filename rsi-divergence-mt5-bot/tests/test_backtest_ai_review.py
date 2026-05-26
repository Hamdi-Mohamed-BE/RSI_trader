from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from rsi_divergence_bot.backtest import _execute_backtest_jobs, _SignalJob, _SymbolAccumulator
from rsi_divergence_bot.config import (
    AiTradeReviewConfig,
    AppConfig,
    BotRuntimeConfig,
    RiskConfig,
    SymbolConfig,
    TelegramSignalsConfig,
)
from rsi_divergence_bot.decision import TradeDecision, resolve_trade_filters
from rsi_divergence_bot.strategy import Signal
from rsi_divergence_bot.trade_ai_review import TradeAiReviewResult, backtest_ai_review_active


def _config(*, bot=None, telegram=None) -> AppConfig:
    bot_cfg = BotRuntimeConfig(**(bot or {}))
    telegram_cfg = TelegramSignalsConfig(**(telegram or {}))
    return AppConfig(
        bot=bot_cfg,
        risk=RiskConfig(),
        telegram_signals=telegram_cfg,
        symbols=[SymbolConfig(symbol="EURUSD", name="Euro", lot_per_leg=0.1, timeframe="M5")],
    )


def _signal() -> Signal:
    return Signal(
        setup_id="setup-1",
        symbol="EURUSD",
        market_key="EURUSD",
        name="Euro",
        side="buy",
        time=datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc),
        entry=1.08,
        sl=1.079,
        tps=[1.081],
        lot_per_leg=0.1,
        risk_distance=0.001,
        session="London",
        reason="bullish rsi divergence",
    )


class BacktestAiReviewTests(unittest.TestCase):
    def test_backtest_ai_review_active_respects_strategy_list(self) -> None:
        config = _config(
            bot={
                "strategy": "signal_full_with_tp_protection",
                "ai_trade_review": AiTradeReviewConfig(
                    enabled=True,
                    strategies=["signal_with_tp_protection"],
                ),
            }
        )
        self.assertFalse(backtest_ai_review_active(config, True))

    @patch("rsi_divergence_bot.backtest.simulate_full_trade")
    @patch("rsi_divergence_bot.backtest.TradeAiReviewer.review")
    def test_execute_backtest_jobs_skips_on_ai_reject(self, review_mock, simulate_mock) -> None:
        config = _config(
            bot={
                "strategy": "signal_full_with_tp_protection",
                "ai_trade_review": AiTradeReviewConfig(enabled=True, min_confidence=0.55),
            },
            telegram={"openai_api_key": "sk-test"},
        )
        review_mock.return_value = TradeAiReviewResult(
            approved=False,
            confidence=0.2,
            reason="Weak setup",
            provider="openai",
        )
        simulate_mock.return_value = {"pnl": 10.0, "exit_time": 1000, "exit_kind": "tp1"}

        import pandas as pd

        df = pd.DataFrame(
            {
                "time": [1, 2, 3],
                "open": [1.08, 1.081, 1.082],
                "high": [1.081, 1.082, 1.083],
                "low": [1.079, 1.08, 1.081],
                "close": [1.0805, 1.0815, 1.0825],
                "spread": [12, 12, 12],
            }
        )
        symbol_cfg = config.symbols[0]
        job = _SignalJob(
            scan_unix=2,
            entry_unix=2,
            symbol_cfg=symbol_cfg,
            df=df,
            row_index=0,
            signal=_signal(),
            point=0.00001,
        )
        accumulator = _SymbolAccumulator(symbol_cfg=symbol_cfg, raw_signals=1)
        client = MagicMock()
        client.money_for_distance.return_value = 10.0

        with patch("rsi_divergence_bot.backtest.evaluate_trade_signal") as evaluate:
            evaluate.return_value = TradeDecision(
                allowed=True,
                code="ok",
                reason="ok",
                risk_usd=10.0,
                spread=0.00012,
                spread_atr=0.1,
                tp1_distance=0.001,
                min_tp1_distance=0.0008,
            )
            _closed, _events, _balance, ai_stats = _execute_backtest_jobs(
                client,
                config,
                [job],
                {symbol_cfg.symbol: accumulator},
                config.bot.strategy,
                1000.0,
                resolve_trade_filters(config),
                use_ai_review=True,
            )

        self.assertEqual(ai_stats["reviewed"], 1)
        self.assertEqual(ai_stats["rejected"], 1)
        self.assertEqual(accumulator.skipped, 1)
        simulate_mock.assert_not_called()
        review_mock.assert_called_once()

    @patch("rsi_divergence_bot.backtest.simulate_full_trade")
    @patch("rsi_divergence_bot.backtest.TradeAiReviewer.review")
    def test_execute_backtest_jobs_trades_on_ai_approve(self, review_mock, simulate_mock) -> None:
        config = _config(
            bot={
                "strategy": "signal_full_with_tp_protection",
                "ai_trade_review": AiTradeReviewConfig(enabled=True, min_confidence=0.55),
            },
            telegram={"openai_api_key": "sk-test"},
        )
        review_mock.return_value = TradeAiReviewResult(
            approved=True,
            confidence=0.9,
            reason="Looks good",
            provider="openai",
        )
        simulate_mock.return_value = {"pnl": 12.0, "exit_time": 1000, "exit_kind": "tp1"}

        import pandas as pd

        df = pd.DataFrame(
            {
                "time": [1, 2, 3],
                "open": [1.08, 1.081, 1.082],
                "high": [1.081, 1.082, 1.083],
                "low": [1.079, 1.08, 1.081],
                "close": [1.0805, 1.0815, 1.0825],
                "spread": [12, 12, 12],
            }
        )
        symbol_cfg = config.symbols[0]
        job = _SignalJob(
            scan_unix=2,
            entry_unix=2,
            symbol_cfg=symbol_cfg,
            df=df,
            row_index=0,
            signal=_signal(),
            point=0.00001,
        )
        accumulator = _SymbolAccumulator(symbol_cfg=symbol_cfg, raw_signals=1)
        client = MagicMock()
        client.money_for_distance.return_value = 10.0

        with patch("rsi_divergence_bot.backtest.evaluate_trade_signal") as evaluate:
            evaluate.return_value = TradeDecision(
                allowed=True,
                code="ok",
                reason="ok",
                risk_usd=10.0,
                spread=0.00012,
                spread_atr=0.1,
                tp1_distance=0.001,
                min_tp1_distance=0.0008,
            )
            _execute_backtest_jobs(
                client,
                config,
                [job],
                {symbol_cfg.symbol: accumulator},
                config.bot.strategy,
                1000.0,
                resolve_trade_filters(config),
                use_ai_review=True,
            )

        self.assertEqual(len(accumulator.trade_logs), 1)
        simulate_mock.assert_called_once()
        review_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
