"""Tiny in-process sliding-window rate limiter for the public simulator endpoint (single-process deployment)."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock

MAX_TRACKED_CLIENTS = 10_000


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self.limit = limit
        self.window = window_seconds
        self.clock = clock
        self._hits: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = self.clock()
        with self._lock:
            if len(self._hits) > MAX_TRACKED_CLIENTS:  # bound memory under abuse
                self._hits.clear()
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True
