import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from rsi_divergence_bot.config import MT5Config
from rsi_divergence_bot.mt5_algo_trading import ensure_algo_trading, patch_experts_ini, _read_ini_bytes


class Mt5AlgoTradingTests(unittest.TestCase):
    def test_patch_experts_ini_sets_account_and_allow_live(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ini_path = Path(tmp) / "config" / "common.ini"
            ini_path.parent.mkdir(parents=True)
            ini_path.write_text("[Experts]\nAccount=1\nAllowLiveTrading=0\n", encoding="utf-8")

            changed = patch_experts_ini(ini_path)
            self.assertTrue(changed)
            text = ini_path.read_text(encoding="utf-8")
            self.assertIn("Account=0", text.replace(" ", ""))
            self.assertIn("AllowLiveTrading=1", text.replace(" ", ""))

    def test_patch_experts_ini_reads_and_writes_utf16_le(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ini_path = Path(tmp) / "config" / "common.ini"
            ini_path.parent.mkdir(parents=True)
            content = "[Experts]\r\nAccount=1\r\nAllowLiveTrading=0\r\n"
            ini_path.write_bytes(b"\xff\xfe" + content.encode("utf-16-le"))

            changed = patch_experts_ini(ini_path)
            self.assertTrue(changed)
            raw = ini_path.read_bytes()
            self.assertTrue(raw.startswith(b"\xff\xfe"))
            text = raw[2:].decode("utf-16-le")
            self.assertIn("Account=0", text.replace(" ", ""))
            self.assertIn("AllowLiveTrading=1", text.replace(" ", ""))

    def test_read_ini_bytes_detects_utf16_le(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ini_path = Path(tmp) / "common.ini"
            ini_path.write_bytes(b"\xff\xfe" + "[Experts]\n".encode("utf-16-le"))
            text, encoding = _read_ini_bytes(ini_path)
            self.assertEqual(encoding, "utf-16-le")
            self.assertIn("[Experts]", text)

    def test_ensure_algo_trading_skips_when_disabled_in_config(self) -> None:
        client = MagicMock()
        client.mt5.terminal_info.return_value = MagicMock(
            trade_allowed=False,
            tradeapi_disabled=False,
            data_path="C:/tmp/mt5",
            _asdict=lambda: {
                "trade_allowed": False,
                "tradeapi_disabled": False,
                "data_path": "C:/tmp/mt5",
            },
        )
        config = MT5Config(auto_enable_algo_trading=False)
        self.assertTrue(ensure_algo_trading(client, config=config))

    def test_ensure_algo_trading_noop_when_already_enabled(self) -> None:
        client = MagicMock()
        client.mt5.terminal_info.return_value = MagicMock(
            trade_allowed=True,
            tradeapi_disabled=False,
            _asdict=lambda: {"trade_allowed": True, "tradeapi_disabled": False},
        )
        config = MT5Config(auto_enable_algo_trading=True)
        self.assertTrue(ensure_algo_trading(client, config=config))


if __name__ == "__main__":
    unittest.main()
