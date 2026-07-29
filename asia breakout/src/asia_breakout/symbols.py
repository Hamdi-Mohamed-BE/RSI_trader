from __future__ import annotations

import re


def normalize_symbol(value: str) -> str:
    """Remove broker punctuation while retaining the instrument code."""
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def symbol_match_score(instrument: str, broker_symbol: str) -> int | None:
    """Score how closely a broker symbol represents a canonical instrument."""
    canonical = normalize_symbol(instrument)
    candidate = normalize_symbol(broker_symbol)
    if not canonical or not candidate:
        return None
    if broker_symbol.upper() == instrument.upper():
        return 10_000
    if candidate == canonical:
        return 9_000
    extra = len(candidate) - len(canonical)
    if candidate.startswith(canonical):
        return 8_000 - max(extra, 0)
    if candidate.endswith(canonical):
        return 7_500 - max(extra, 0)
    if canonical in candidate:
        return 7_000 - max(extra, 0)
    return None


def canonical_for_symbol(symbol: str, instruments: tuple[str, ...]) -> str | None:
    matches = [
        (score, instrument)
        for instrument in instruments
        if (score := symbol_match_score(instrument, symbol)) is not None
    ]
    if not matches:
        return None
    return max(matches, key=lambda item: (item[0], len(item[1])))[1]
