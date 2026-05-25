from __future__ import annotations

import unittest

from rsi_divergence_bot.playwright_runtime import playwright_runtime_error


class PlaywrightRuntimeTests(unittest.TestCase):
    def test_greenlet_error_message_mentions_reinstall(self) -> None:
        message = playwright_runtime_error(ImportError("DLL load failed while importing _greenlet"))
        self.assertIn("greenlet", message.lower())
        self.assertIn("playwright", message.lower())


if __name__ == "__main__":
    unittest.main()
