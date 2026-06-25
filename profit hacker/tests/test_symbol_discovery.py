from __future__ import annotations

import unittest
from types import SimpleNamespace

from profit_hacker_bot.symbol_discovery import choose_best_symbol, normalize_symbol


class SymbolDiscoveryTest(unittest.TestCase):
    def test_normalizes_suffixes_and_punctuation(self) -> None:
        self.assertEqual(normalize_symbol("NAS100.cash"), "NAS100CASH")
        self.assertEqual(normalize_symbol("#XAUUSDm"), "XAUUSDM")

    def test_prefers_same_symbol_with_suffix_over_alias(self) -> None:
        symbols = [
            SimpleNamespace(name="US100"),
            SimpleNamespace(name="NAS100.cash"),
        ]

        match = choose_best_symbol("NAS100", symbols)

        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.name, "NAS100.cash")

    def test_falls_back_to_common_alias(self) -> None:
        symbols = [
            SimpleNamespace(name="USTECm"),
            SimpleNamespace(name="GBPUSD"),
        ]

        match = choose_best_symbol("NAS100", symbols)

        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.name, "USTECm")

    def test_ignores_disabled_symbols(self) -> None:
        symbols = [
            SimpleNamespace(name="NAS100.cash", trade_mode=0),
            SimpleNamespace(name="NAS100m", trade_mode=1),
        ]

        match = choose_best_symbol("NAS100", symbols, disabled_trade_mode=0)

        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.name, "NAS100m")

    def test_returns_none_without_reasonable_match(self) -> None:
        symbols = [SimpleNamespace(name="EURUSD"), SimpleNamespace(name="GBPUSD")]

        self.assertIsNone(choose_best_symbol("NAS100", symbols))


if __name__ == "__main__":
    unittest.main()
