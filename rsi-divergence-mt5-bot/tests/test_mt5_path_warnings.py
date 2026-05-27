import unittest

from rsi_divergence_bot.mt5_account_pool import mt5_path_warnings


class Mt5PathWarningsTests(unittest.TestCase):
    def test_no_warning_for_single_account(self) -> None:
        from rsi_divergence_bot.mt5_account_store import Mt5AccountRecord

        one = Mt5AccountRecord(
            id=1,
            name="VIP",
            login=1,
            password="x",
            server="srv",
            symbol_suffix="-VIP",
            mt5_path=None,
            enabled=True,
            is_primary=True,
            created_at="",
            updated_at="",
        )
        self.assertEqual(mt5_path_warnings([one], "C:\\MT5\\terminal64.exe"), [])

    def test_warn_when_paths_match(self) -> None:
        from rsi_divergence_bot.mt5_account_store import Mt5AccountRecord

        shared_path = "C:\\MT5\\A\\terminal64.exe"
        accounts = [
            Mt5AccountRecord(
                id=1,
                name="VIP",
                login=1,
                password="x",
                server="srv",
                symbol_suffix="-VIP",
                mt5_path=shared_path,
                enabled=True,
                is_primary=True,
                created_at="",
                updated_at="",
            ),
            Mt5AccountRecord(
                id=2,
                name="STD",
                login=2,
                password="x",
                server="srv",
                symbol_suffix="-STD",
                mt5_path=shared_path,
                enabled=True,
                is_primary=False,
                created_at="",
                updated_at="",
            ),
        ]
        warnings = mt5_path_warnings(accounts, None)
        self.assertEqual(len(warnings), 1)
        self.assertIn("VIP", warnings[0])
        self.assertIn("STD", warnings[0])


if __name__ == "__main__":
    unittest.main()
