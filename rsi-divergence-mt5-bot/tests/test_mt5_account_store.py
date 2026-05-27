import tempfile
import unittest
from pathlib import Path

from rsi_divergence_bot.mt5_account_store import Mt5AccountStore


class Mt5AccountStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.store = Mt5AccountStore(Path(self.tempdir.name) / "mt5_accounts.db")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_add_list_and_runtime_defaults(self) -> None:
        account = self.store.add_account(
            name="VIP",
            login=10001,
            password="secret",
            server="Broker-Server",
            symbol_suffix="-VIP",
        )
        self.assertEqual(account.name, "VIP")
        self.assertEqual(account.symbol_suffix, "-VIP")
        self.assertTrue(account.is_demo)
        self.assertTrue(account.is_primary)
        payload = self.store.runtime_payload()
        self.assertEqual(payload["trading_mode"], "parallel")
        self.assertEqual(payload["active_account_id"], account.id)
        self.assertEqual(payload["enabled_count"], 1)

    def test_trading_mode_and_active_account(self) -> None:
        first = self.store.add_account(
            name="VIP",
            login=10001,
            password="secret",
            server="Broker-Server",
            symbol_suffix="-VIP",
        )
        second = self.store.add_account(
            name="STD",
            login=10002,
            password="secret2",
            server="Broker-Server",
            symbol_suffix="-STD",
        )
        self.store.set_trading_mode("single")
        self.store.set_active_account_id(second.id)
        self.assertEqual(self.store.trading_mode(), "single")
        self.assertEqual(self.store.active_account_id(), second.id)
        enabled = self.store.enabled_accounts()
        self.assertEqual(len(enabled), 2)
        self.store.update_account(first.id, enabled=False)
        self.assertEqual(len(self.store.enabled_accounts()), 1)

    def test_delete_primary_promotes_next(self) -> None:
        first = self.store.add_account(
            name="VIP",
            login=10001,
            password="secret",
            server="Broker-Server",
            is_primary=True,
        )
        second = self.store.add_account(
            name="STD",
            login=10002,
            password="secret2",
            server="Broker-Server",
        )
        self.store.delete_account(first.id)
        promoted = self.store.get_account(second.id)
        self.assertIsNotNone(promoted)
        assert promoted is not None
        self.assertTrue(promoted.is_primary)

    def test_is_demo_defaults_true_and_can_update(self) -> None:
        account = self.store.add_account(
            name="Live",
            login=10003,
            password="secret",
            server="Broker-Server",
            is_demo=False,
        )
        self.assertFalse(account.is_demo)
        updated = self.store.update_account(account.id, is_demo=True)
        self.assertTrue(updated.is_demo)


if __name__ == "__main__":
    unittest.main()
