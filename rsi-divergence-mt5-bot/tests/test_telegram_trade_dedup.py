from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from rsi_divergence_bot.config import AppConfig, SymbolConfig, TelegramChannelConfig, TelegramSignalsConfig
from rsi_divergence_bot.state import StateStore
from rsi_divergence_bot.telegram_signals import (
    ParsedTelegramSignal,
    TelegramSignalsBot,
    _looks_like_trade_update,
    telegram_trade_fingerprint,
)


def _channel() -> TelegramChannelConfig:
    return TelegramChannelConfig(name="FOREX USA MASTER", url="https://web.telegram.org/k/#@FOREXUSAMASTER1")


def _config() -> AppConfig:
    return AppConfig(
        telegram_signals=TelegramSignalsConfig(
            channels=[_channel()],
        ),
        symbols=[SymbolConfig(symbol="XAUUSD-VIP", name="XAUUSD", lot_per_leg=0.08)],
    )


class TelegramTradeFingerprintTests(unittest.TestCase):
    def test_fingerprint_is_stable_for_same_ai_values(self) -> None:
        channel = _channel()
        parsed = ParsedTelegramSignal(
            symbol="XAUUSD",
            action="buy",
            stop_loss=4500.0,
            tps=[4516.0, 4520.0],
            confidence=0.91,
        )
        first = telegram_trade_fingerprint(channel, parsed)
        second = telegram_trade_fingerprint(channel, parsed)
        self.assertEqual(first, second)

    def test_fingerprint_changes_when_trade_values_change(self) -> None:
        channel = _channel()
        base = ParsedTelegramSignal(
            symbol="XAUUSD",
            action="buy",
            stop_loss=4500.0,
            tps=[4516.0],
            confidence=0.9,
        )
        changed = ParsedTelegramSignal(
            symbol="XAUUSD",
            action="buy",
            stop_loss=4500.0,
            tps=[4518.0],
            confidence=0.9,
        )
        self.assertNotEqual(
            telegram_trade_fingerprint(channel, base),
            telegram_trade_fingerprint(channel, changed),
        )


class TelegramTradeUpdateDetectionTests(unittest.TestCase):
    def test_detects_reply_profit_update(self) -> None:
        text = """
FOREX USA MASTER .||. XAUUSD BUY NOW ( 4513) ✅ .||. TARGET 1 ( 4516) ✅ .||.
buy 0.35 4508.762 4515.133 222.99
buy 0.35 4508.647 4515.133 227.01
2ND ENTRY 70 PIPS DONE
"""
        self.assertTrue(_looks_like_trade_update(text))

    def test_does_not_flag_fresh_signal(self) -> None:
        text = "FOREX USA MASTER .||. XAUUSD BUY NOW (4513) ✅ .||. TARGET 1 (4516) ✅ .||. SL 4500"
        self.assertFalse(_looks_like_trade_update(text))


class TelegramTradeDedupTests(unittest.TestCase):
    def test_duplicate_trade_hash_is_skipped(self) -> None:
        config = _config()
        config.bot.dry_run = True
        client = MagicMock()
        client.tick.return_value = {"bid": 4510.0, "ask": 4510.5}
        with tempfile.TemporaryDirectory() as tmp:
            state = StateStore(str(Path(tmp) / "state.json"))
            logger = MagicMock()
            bot = TelegramSignalsBot(config, client, state, logger)
            parsed = ParsedTelegramSignal(
                symbol="XAUUSD",
                action="buy",
                stop_loss=4500.0,
                tps=[4516.0],
                confidence=0.95,
            )
            channel = _channel()
            trade_hash = telegram_trade_fingerprint(channel, parsed)
            state.mark_telegram_trade_processed(trade_hash, {"status": "placed", "symbol": "XAUUSD"})

            result = bot._place_parsed_signal(parsed, source_id="msg-1", channel=channel, trade_hash=trade_hash)

            self.assertEqual(result["status"], "skipped")
            self.assertIn("duplicate trade", str(result.get("reason")))


if __name__ == "__main__":
    unittest.main()
