import unittest

from rsi_divergence_bot.config import AppConfig, MT5Config, RiskConfig, SymbolConfig
from rsi_divergence_bot.manual_trade import parse_manual_trade


class ManualTradeSymbolCaseTests(unittest.TestCase):
    def test_parse_manual_trade_uses_demo_symbol_case(self) -> None:
        config = AppConfig(
            mt5=MT5Config(is_demo=True),
            risk=RiskConfig(default_forex_lot=0.25),
            symbols=[
                SymbolConfig(
                    symbol="BTCUSD",
                    name="Bitcoin",
                    demo_symbol="BTCUSDm",
                    live_symbol="BTCUSD-VIP",
                    lot_per_leg=0.1,
                )
            ],
        )
        plan = parse_manual_trade(
            "BTCUSDm SELL\nSL 73709\ntp 73518\n",
            config,
        )
        self.assertEqual(plan.symbol, "BTCUSDm")
        self.assertEqual(plan.side, "sell")


if __name__ == "__main__":
    unittest.main()
