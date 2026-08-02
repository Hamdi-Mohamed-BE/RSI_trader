from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import time
from typing import Iterator

import MetaTrader5 as mt5


@dataclass(frozen=True, slots=True)
class PortfolioDecision:
    allowed: bool
    current_risk_pct: float
    proposed_risk_pct: float
    cap_risk_pct: float


def _risk_by_magic() -> dict[int, float]:
    values: dict[int, float] = {}
    raw = os.getenv("SELECTED_XAU_MAGIC_RISKS", "").strip()
    for item in raw.split(","):
        if not item.strip():
            continue
        magic_text, risk_text = item.split(":", 1)
        values[int(magic_text.strip())] = float(risk_text.strip())
    return values


def _active_reserved_risk_pct(risk_by_magic: dict[int, float]) -> float:
    positions = mt5.positions_get()
    orders = mt5.orders_get()
    if positions is None or orders is None:
        raise RuntimeError(
            f"Could not read MT5 portfolio exposure: {mt5.last_error()}"
        )
    active_magics = {
        int(getattr(item, "magic", 0))
        for item in (*positions, *orders)
        if int(getattr(item, "magic", 0)) in risk_by_magic
    }
    return sum(risk_by_magic[magic] for magic in active_magics)


@contextmanager
def selected_xau_entry_guard(
    proposed_risk_pct: float,
) -> Iterator[PortfolioDecision]:
    cap = float(os.getenv("SHARED_XAU_RISK_CAP_PCT", "0"))
    risk_by_magic = _risk_by_magic()
    if cap <= 0 or not risk_by_magic:
        yield PortfolioDecision(True, 0.0, proposed_risk_pct, cap)
        return

    root = Path(__file__).resolve().parents[3]
    lock_path = root / "runtime" / "selected-xau-portfolio.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor: int | None = None
    deadline = time.monotonic() + 10.0
    while descriptor is None:
        try:
            descriptor = os.open(
                lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR
            )
        except FileExistsError:
            try:
                if time.time() - lock_path.stat().st_mtime > 120:
                    lock_path.unlink(missing_ok=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    "Timed out waiting for the shared XAU risk lock"
                )
            time.sleep(0.1)

    try:
        current = _active_reserved_risk_pct(risk_by_magic)
        yield PortfolioDecision(
            current + proposed_risk_pct <= cap + 1e-9,
            current,
            proposed_risk_pct,
            cap,
        )
    finally:
        os.close(descriptor)
        lock_path.unlink(missing_ok=True)
