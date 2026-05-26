from __future__ import annotations

import logging
from collections import deque
from pathlib import Path


LOG_BUFFER: deque[str] = deque(maxlen=500)
LOG_FILE: Path | None = None


class RingBufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        LOG_BUFFER.append(self.format(record))


def setup_logging(log_file: str | Path) -> logging.Logger:
    global LOG_FILE
    path = Path(log_file).resolve()
    LOG_FILE = path
    path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("rsi_bot")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    buffer_handler = RingBufferHandler()
    buffer_handler.setFormatter(fmt)
    logger.addHandler(buffer_handler)

    return logger


def recent_logs(limit: int = 100) -> list[str]:
    if limit <= 0:
        return []
    if LOG_FILE and LOG_FILE.exists():
        try:
            return _tail_lines(LOG_FILE, limit)
        except OSError:
            pass
    return list(LOG_BUFFER)[-limit:]


def _tail_lines(path: Path, limit: int, chunk_size: int = 256 * 1024) -> list[str]:
    """Read only the last chunk of a log file instead of loading it entirely."""
    with path.open("rb") as handle:
        handle.seek(0, 2)
        size = handle.tell()
        if size <= 0:
            return []
        offset = max(0, size - chunk_size)
        handle.seek(offset)
        data = handle.read()
    text = data.decode("utf-8", errors="replace")
    if offset > 0:
        text = text.split("\n", 1)[-1]
    lines = text.splitlines()
    return lines[-limit:]
