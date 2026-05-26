import tempfile
import unittest
from pathlib import Path

from rsi_divergence_bot.logging_utils import _tail_lines, recent_logs


class RecentLogsTests(unittest.TestCase):
    def test_tail_lines_reads_last_lines_without_full_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bot.log"
            lines = [f"line-{index}" for index in range(5000)]
            path.write_text("\n".join(lines), encoding="utf-8")
            tail = _tail_lines(path, 3)
            self.assertEqual(tail, ["line-4997", "line-4998", "line-4999"])

    def test_recent_logs_uses_tail_reader(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bot.log"
            path.write_text("\n".join(f"entry-{index}" for index in range(200)), encoding="utf-8")
            import rsi_divergence_bot.logging_utils as logging_utils

            original = logging_utils.LOG_FILE
            try:
                logging_utils.LOG_FILE = path
                tail = recent_logs(5)
            finally:
                logging_utils.LOG_FILE = original
            self.assertEqual(tail, ["entry-195", "entry-196", "entry-197", "entry-198", "entry-199"])


if __name__ == "__main__":
    unittest.main()
