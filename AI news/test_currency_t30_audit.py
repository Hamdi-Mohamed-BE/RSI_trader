from __future__ import annotations

import unittest

from currency_t30_audit import pair_prediction, usd_direction


class CurrencyDirectionMappingTests(unittest.TestCase):
    def test_usd_base_pair_follows_usd(self) -> None:
        self.assertEqual(pair_prediction("BUY", "base"), "BUY")
        self.assertEqual(usd_direction("SELL", "base"), "SELL")

    def test_usd_quote_pair_inverts_usd(self) -> None:
        self.assertEqual(pair_prediction("BUY", "quote"), "SELL")
        self.assertEqual(usd_direction("BUY", "quote"), "SELL")

    def test_uncertain_stays_uncertain(self) -> None:
        self.assertEqual(usd_direction("UNCERTAIN", "base"), "UNCERTAIN")
        self.assertEqual(usd_direction("UNCERTAIN", "quote"), "UNCERTAIN")


if __name__ == "__main__":
    unittest.main()
