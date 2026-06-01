from __future__ import annotations

import unittest

from rsi_divergence_bot.manual_trade import parse_manual_trade
from rsi_divergence_bot.config import AppConfig, BotRuntimeConfig, RiskConfig, SymbolConfig
from rsi_divergence_bot.telegram_entry import (
    EntryZone,
    extract_entry_zone_from_line,
    resolve_telegram_execution,
)
from rsi_divergence_bot.telegram_signals import fallback_parse_telegram_signal


def _config() -> AppConfig:
    return AppConfig(
        bot=BotRuntimeConfig(),
        risk=RiskConfig(),
        symbols=[SymbolConfig(symbol="XAUUSD-VIP", name="Gold", lot_per_leg=0.08)],
    )


class TelegramEntryTests(unittest.TestCase):
    def test_shorthand_entry_zone(self) -> None:
        zone = EntryZone.from_prices(4540, 35)
        self.assertEqual(zone.low, 4535.0)
        self.assertEqual(zone.high, 4540.0)

    def test_full_entry_zone(self) -> None:
        zone = EntryZone.from_prices(4394, 4397)
        self.assertEqual(zone.low, 4394.0)
        self.assertEqual(zone.high, 4397.0)

    def test_buy_above_zone_uses_limit(self) -> None:
        decision = resolve_telegram_execution(
            "buy",
            bid=4551.0,
            ask=4552.0,
            zone=EntryZone(low=4535.0, high=4540.0),
        )
        self.assertEqual(decision.order_kind, "buy_limit")
        self.assertEqual(decision.entry_price, 4540.0)
        self.assertIn("above entry zone", decision.reason)

    def test_buy_in_zone_uses_market(self) -> None:
        decision = resolve_telegram_execution(
            "buy",
            bid=4537.0,
            ask=4538.0,
            zone=EntryZone(low=4535.0, high=4540.0),
        )
        self.assertEqual(decision.order_kind, "market")
        self.assertEqual(decision.entry_price, 4538.0)
        self.assertIn("inside entry zone", decision.reason)

    def test_sell_below_zone_uses_limit(self) -> None:
        decision = resolve_telegram_execution(
            "sell",
            bid=4390.0,
            ask=4391.0,
            zone=EntryZone(low=4394.0, high=4397.0),
        )
        self.assertEqual(decision.order_kind, "sell_limit")
        self.assertEqual(decision.entry_price, 4394.0)
        self.assertIn("below entry zone", decision.reason)

    def test_fallback_parses_gold_buy_now_range(self) -> None:
        message = """Gold buy now 4540/35
Tp 4545
Tp 4550
Tp 4555/4560/4565
SL 4520"""
        parsed = fallback_parse_telegram_signal(message, _config())
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.action, "buy")
        self.assertEqual(parsed.symbol, "XAUUSD")
        self.assertEqual(parsed.entry_low, 4535.0)
        self.assertEqual(parsed.entry_high, 4540.0)
        self.assertEqual(parsed.tps, [4545.0, 4550.0, 4555.0, 4560.0, 4565.0])

    def test_manual_trade_parses_gold_buy_now(self) -> None:
        plan = parse_manual_trade(
            """Gold buy now 4540/35
Tp 4545
SL 4520""",
            _config(),
        )
        self.assertEqual(plan.side, "buy")
        self.assertEqual(plan.entry_low, 4535.0)
        self.assertEqual(plan.entry_high, 4540.0)

    def test_extract_entry_zone_from_line(self) -> None:
        zone = extract_entry_zone_from_line("Gold buy now 4540/35")
        self.assertIsNotNone(zone)
        assert zone is not None
        self.assertEqual((zone.low, zone.high), (4535.0, 4540.0))


if __name__ == "__main__":
    unittest.main()
