from __future__ import annotations

import re


BROKER_SUFFIXES = {
    "VIP",
    "STD",
    "STANDARD",
    "ECN",
    "RAW",
    "PRO",
    "MINI",
    "MICRO",
    "CRP",
    "CASH",
}


def market_key(symbol: str) -> str:
    """Return a stable market key while preserving real broker symbols elsewhere."""
    value = re.sub(r"\s+", "", symbol.strip().upper())
    while True:
        match = re.search(r"([._-])([A-Z0-9]+)$", value)
        if not match or match.group(2) not in BROKER_SUFFIXES:
            return value
        value = value[: match.start()]


def same_market(left: str, right: str) -> bool:
    return market_key(left) == market_key(right)
