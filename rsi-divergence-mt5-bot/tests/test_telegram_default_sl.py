import time
import unittest
from unittest.mock import MagicMock, patch

from rsi_divergence_bot.config import AppConfig, SymbolConfig, TelegramChannelConfig, TelegramSignalsConfig
from rsi_divergence_bot.telegram_signals import ParsedTelegramSignal, PendingSlWatch, TelegramSignalsBot
from rsi_divergence_bot.trade_geometry import (
    default_stop_loss_one_to_one,
    synthetic_stop_loss_reference_tp,
)


def _config(**overrides) -> AppConfig:
    telegram = TelegramSignalsConfig(
        channels=[TelegramChannelConfig(name="Test", url="https://t.me/test")],
        sl_refresh_seconds=60,
        **{k: v for k, v in overrides.items() if k in TelegramSignalsConfig.model_fields},
    )
    return AppConfig(
        telegram_signals=telegram,
        symbols=[SymbolConfig(symbol="XAUUSD-VIP", name="XAUUSD", lot_per_leg=0.08)],
    )


class DefaultStopLossTests(unittest.TestCase):
    def test_sell_one_to_one(self) -> None:
        self.assertEqual(default_stop_loss_one_to_one("sell", 4550.0, 4543.0), 4557.0)

    def test_buy_one_to_one(self) -> None:
        self.assertEqual(default_stop_loss_one_to_one("buy", 100.0, 106.0), 94.0)

    def test_reference_tp_prefers_second(self) -> None:
        self.assertEqual(synthetic_stop_loss_reference_tp([4547.0, 4543.0, 4539.0]), 4543.0)

    def test_reference_tp_falls_back_to_first(self) -> None:
        self.assertEqual(synthetic_stop_loss_reference_tp([4547.0]), 4547.0)


class TelegramMissingSlTests(unittest.TestCase):
    def test_place_uses_synthetic_sl_when_missing(self) -> None:
        config = _config()
        config.bot.dry_run = True
        client = MagicMock()
        client.tick.return_value = {"bid": 4550.0, "ask": 4550.5}
        state = MagicMock()
        state.is_telegram_trade_processed.return_value = False
        logger = MagicMock()
        bot = TelegramSignalsBot(config, client, state, logger)
        parsed = ParsedTelegramSignal(
            symbol="XAUUSD",
            action="sell",
            entry=4550.0,
            stop_loss=None,
            tps=[4547.0, 4543.0, 4539.0],
        )
        channel = TelegramChannelConfig(name="Test", url="https://t.me/test")
        result = bot._place_parsed_signal(
            parsed,
            source_id="abc123",
            channel=channel,
            message_id="abc123",
            message_key="mid-1",
        )
        self.assertEqual(result["status"], "paper")
        self.assertEqual(result["sl"], 4557.0)
        self.assertTrue(result["sl_synthetic"])
        self.assertTrue(result["sl_pending_refresh"])
        self.assertEqual(result["message_id"], "abc123")
        self.assertEqual(result["tickets"], [])
        self.assertIn("mid-1", bot._pending_sl_watches)

    def test_refresh_updates_open_trades_when_message_gains_sl(self) -> None:
        config = _config()
        config.bot.dry_run = False
        client = MagicMock()
        state = MagicMock()
        logger = MagicMock()
        bot = TelegramSignalsBot(config, client, state, logger)
        channel = TelegramChannelConfig(name="Test", url="https://t.me/test")
        watch = PendingSlWatch(
            message_id="msg1",
            message_key="mid-1",
            channel=channel,
            setup_id="telegram:msg1",
            tickets=[101, 102],
            symbol="XAUUSD-VIP",
            side="sell",
            synthetic_sl=4557.0,
            started_at=time.monotonic(),
            expires_at=time.monotonic() + 60,
        )
        bot._pending_sl_watches["mid-1"] = watch

        bubble = MagicMock()
        bubble.key = "mid-1"
        bubble.text = "XAUUSD SELL SL 4560 TP 4547 4543"
        bubble.timestamp = time.time()
        page = MagicMock()

        state.find_telegram_message_by_key.return_value = {
            "text": "XAUUSD SELL TP 4547 4543",
            "parsed": {"tps": [4547.0, 4543.0]},
            "result": {"entry_price": 4550.0},
        }
        state.read.return_value = {
            "setups": [
                {
                    "setup_id": "telegram:msg1",
                    "symbol": "XAUUSD-VIP",
                    "side": "sell",
                    "tickets": [101, 102],
                    "tps": [4547.0, 4543.0],
                    "entry_price": 4550.0,
                }
            ]
        }

        parsed = ParsedTelegramSignal(
            symbol="XAUUSD",
            action="sell",
            stop_loss=4560.0,
            tps=[4547.0, 4543.0],
        )
        update_result = {
            "status": "updated",
            "reason": "telegram message updated with stop loss",
            "sl": 4560.0,
            "tickets": [{"ticket": 101}, {"ticket": 102}],
        }

        with patch.object(bot, "_capture_chat_html", return_value=("<html></html>", "test")):
            with patch("rsi_divergence_bot.telegram_signals.parse_all_bubbles", return_value=([bubble], MagicMock())):
                with patch.object(bot.parser, "parse", return_value=parsed):
                    with patch.object(bot.executor, "apply_sl_update", return_value=update_result) as apply_sl:
                        bot._refresh_pending_sl_watches(page, channel)

        apply_sl.assert_called_once()
        self.assertNotIn("mid-1", bot._pending_sl_watches)


if __name__ == "__main__":
    unittest.main()
