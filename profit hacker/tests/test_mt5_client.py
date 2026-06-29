from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from profit_hacker_bot.models import Direction, EntryType, OrderPlan
from profit_hacker_bot.mt5_client import MT5Client


class FakeMT5:
    SYMBOL_TRADE_MODE_DISABLED = 0
    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_PENDING = 5
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_PLACED = 10008
    TRADE_RETCODE_DONE_PARTIAL = 10010
    TRADE_RETCODE_INVALID_FILL = 10030
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    ORDER_TYPE_BUY_STOP = 4
    ORDER_TYPE_SELL_STOP = 5
    ORDER_TIME_GTC = 0
    ORDER_FILLING_FOK = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2

    def __init__(self) -> None:
        self.send_requests: list[dict] = []
        self.results = [
            SimpleNamespace(retcode=10030, comment="Unsupported filling mode", order=0, deal=0),
            SimpleNamespace(retcode=10009, comment="Done", order=123, deal=456),
        ]
        self.gbp_info = SimpleNamespace(
            name="GBPUSDm",
            visible=True,
            trade_mode=1,
            digits=5,
            filling_mode=3,
        )

    def symbol_info(self, symbol: str):
        return self.gbp_info if symbol == "GBPUSDm" else None

    def symbol_select(self, symbol: str, enabled: bool) -> bool:
        return symbol == "GBPUSDm" and enabled

    def symbols_get(self):
        return [self.gbp_info]

    def symbol_info_tick(self, symbol: str):
        return SimpleNamespace(ask=1.3200, bid=1.3198)

    def order_send(self, request: dict):
        self.send_requests.append(request)
        return self.results.pop(0)

    def last_error(self):
        return (0, "ok")


def settings(**overrides):
    values = {
        "symbol_map": {},
        "auto_discover_symbols": True,
        "mt5_magic": 1303328644,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class MT5ClientTests(unittest.TestCase):
    def test_unavailable_configured_self_map_falls_back_to_suffix_discovery(self) -> None:
        fake = FakeMT5()
        client = MT5Client(settings(symbol_map={"GBPUSD": "GBPUSD"}))
        client.connected = True

        with patch("profit_hacker_bot.mt5_client.mt5", fake):
            resolved = client.resolve_broker_symbol("GBPUSD")

        self.assertEqual(resolved, "GBPUSDm")

    def test_retries_only_after_unsupported_filling_mode(self) -> None:
        fake = FakeMT5()
        client = MT5Client(settings())
        client.connected = True
        plan = OrderPlan(
            symbol="GBPUSDm",
            direction=Direction.SELL,
            entry_type=EntryType.MARKET,
            volume=0.01,
            stop_loss=1.3234,
            take_profit=1.3140,
            break_even_trigger=1.3182,
            comment="PH:29390:1",
        )

        with patch("profit_hacker_bot.mt5_client.mt5", fake):
            result = client.place_order(plan)

        self.assertEqual(result.ticket, 123)
        self.assertEqual(
            [request["type_filling"] for request in fake.send_requests],
            [fake.ORDER_FILLING_FOK, fake.ORDER_FILLING_IOC],
        )


if __name__ == "__main__":
    unittest.main()
